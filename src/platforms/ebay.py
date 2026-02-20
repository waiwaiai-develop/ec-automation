"""eBay Inventory API クライアント

eBayの3ステップ出品フロー:
  1. inventory_item (SKU作成)
  2. offer (マーケットプレイスへの出品条件設定)
  3. publish (公開)

BasePlatformClientインターフェースを実装。
"""

import json
import os
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import httpx

from src.auth.oauth_manager import OAuthTokenManager
from src.platforms.base_client import BasePlatformClient

# eBay API エンドポイント
EBAY_ENDPOINTS = {
    "sandbox": {
        "inventory": "https://api.sandbox.ebay.com/sell/inventory/v1",
        "fulfillment": "https://api.sandbox.ebay.com/sell/fulfillment/v1",
    },
    "production": {
        "inventory": "https://api.ebay.com/sell/inventory/v1",
        "fulfillment": "https://api.ebay.com/sell/fulfillment/v1",
    },
}

# 包丁の配送除外国（刃物規制）
KNIFE_EXCLUDED_COUNTRIES = ["GB", "IE"]


class EbayClient(BasePlatformClient):
    """eBay Inventory APIクライアント"""

    def __init__(self, sandbox: bool = True):
        self.sandbox = sandbox
        env = "sandbox" if sandbox else "production"
        self.endpoints = EBAY_ENDPOINTS[env]
        self.token_manager = OAuthTokenManager("ebay", sandbox=sandbox)
        self.marketplace_id = os.environ.get("EBAY_MARKETPLACE_ID", "EBAY_US")

    @property
    def platform_name(self) -> str:
        return "ebay"

    def _headers(self) -> Dict[str, str]:
        """認証ヘッダーを構築"""
        token = self.token_manager.get_valid_token()
        return {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Content-Language": "en-US",
        }

    def _make_sku(self, product: Dict[str, Any]) -> str:
        """商品からSKUを生成"""
        supplier = product.get("supplier", "unknown")
        product_id = product.get("supplier_product_id", str(product.get("id", "0")))
        return f"DS-{supplier.upper()}-{product_id}"

    def create_listing(self, product: Dict[str, Any],
                       listing_data: Dict[str, Any]) -> Dict[str, Any]:
        """eBay 3ステップ出品: inventory_item → offer → publish

        Args:
            product: DBのproductsテーブルの行データ
            listing_data: {
                "title_en": str,
                "description_en": str,
                "price_usd": float,
                "category_id": str,  # eBayカテゴリID
                "tags": list,
                "condition": str,    # "NEW" (デフォルト)
                "excluded_countries": list,
                "shipping_cost_usd": float,
            }
        """
        sku = self._make_sku(product)

        # Step 1: inventory_item 作成
        self._create_or_update_inventory_item(sku, product, listing_data)

        # Step 2: offer 作成
        offer_id = self._create_offer(sku, listing_data)

        # Step 3: publish
        listing_id = self._publish_offer(offer_id)

        return {
            "platform_listing_id": listing_id,
            "offer_id": offer_id,
            "sku": sku,
            "status": "active",
            "url": f"https://www.ebay.com/itm/{listing_id}",
        }

    def _create_or_update_inventory_item(self, sku: str,
                                          product: Dict[str, Any],
                                          listing_data: Dict[str, Any]) -> None:
        """Step 1: inventory_item を作成/更新"""
        # 画像URLの処理
        image_urls = product.get("image_urls")
        if isinstance(image_urls, str):
            image_urls = json.loads(image_urls)
        if not image_urls:
            image_urls = []

        body = {
            "availability": {
                "shipToLocationAvailability": {
                    "quantity": 5,  # ドロップシッピング: 常に在庫ありとして表示
                }
            },
            "condition": listing_data.get("condition", "NEW"),
            "product": {
                "title": listing_data["title_en"][:80],
                "description": listing_data["description_en"],
                "imageUrls": image_urls[:12],  # eBay上限12枚
            },
        }

        # 重量情報があればpackageWeightAndSizeに追加
        weight_g = product.get("weight_g")
        if weight_g:
            body["packageWeightAndSize"] = {
                "weight": {
                    "value": weight_g / 1000,  # kg変換
                    "unit": "KILOGRAM",
                }
            }

        response = httpx.put(
            f"{self.endpoints['inventory']}/inventory_item/{sku}",
            headers=self._headers(),
            json=body,
            timeout=30,
        )
        response.raise_for_status()

    def _create_offer(self, sku: str,
                      listing_data: Dict[str, Any]) -> str:
        """Step 2: offer を作成"""
        excluded = listing_data.get("excluded_countries", [])

        body = {
            "sku": sku,
            "marketplaceId": self.marketplace_id,
            "format": "FIXED_PRICE",
            "listingDuration": "GTC",  # Good 'Til Cancelled
            "pricingSummary": {
                "price": {
                    "value": str(listing_data["price_usd"]),
                    "currency": "USD",
                }
            },
            "listingPolicies": {
                "fulfillmentPolicyId": os.environ.get("EBAY_FULFILLMENT_POLICY_ID", ""),
                "paymentPolicyId": os.environ.get("EBAY_PAYMENT_POLICY_ID", ""),
                "returnPolicyId": os.environ.get("EBAY_RETURN_POLICY_ID", ""),
            },
        }

        # カテゴリID
        category_id = listing_data.get("category_id")
        if category_id:
            body["categoryId"] = category_id

        # 配送除外国
        if excluded:
            body["shipToLocationExclusions"] = {
                "countryExclusions": excluded,
            }

        response = httpx.post(
            f"{self.endpoints['inventory']}/offer",
            headers=self._headers(),
            json=body,
            timeout=30,
        )
        response.raise_for_status()
        return response.json()["offerId"]

    def _publish_offer(self, offer_id: str) -> str:
        """Step 3: offer を公開"""
        response = httpx.post(
            f"{self.endpoints['inventory']}/offer/{offer_id}/publish",
            headers=self._headers(),
            timeout=30,
        )
        response.raise_for_status()
        return response.json()["listingId"]

    def update_listing(self, platform_listing_id: str,
                       updates: Dict[str, Any]) -> Dict[str, Any]:
        """リスティングを更新（offer経由で価格・説明等を変更）"""
        updated_fields = []

        # SKUが分かる場合はinventory_itemも更新
        sku = updates.get("sku")
        if sku:
            inventory_updates = {}
            if "title_en" in updates or "description_en" in updates:
                inventory_updates["product"] = {}
                if "title_en" in updates:
                    inventory_updates["product"]["title"] = updates["title_en"][:80]
                    updated_fields.append("title_en")
                if "description_en" in updates:
                    inventory_updates["product"]["description"] = updates["description_en"]
                    updated_fields.append("description_en")

            if inventory_updates:
                response = httpx.put(
                    f"{self.endpoints['inventory']}/inventory_item/{sku}",
                    headers=self._headers(),
                    json=inventory_updates,
                    timeout=30,
                )
                response.raise_for_status()

        # offer更新（価格等）
        offer_id = updates.get("offer_id")
        if offer_id and "price_usd" in updates:
            offer_body = {
                "pricingSummary": {
                    "price": {
                        "value": str(updates["price_usd"]),
                        "currency": "USD",
                    }
                }
            }
            response = httpx.put(
                f"{self.endpoints['inventory']}/offer/{offer_id}",
                headers=self._headers(),
                json=offer_body,
                timeout=30,
            )
            response.raise_for_status()
            updated_fields.append("price_usd")

        return {"success": True, "updated_fields": updated_fields}

    def deactivate_listing(self, platform_listing_id: str) -> Dict[str, Any]:
        """リスティングを非公開（在庫切れ: quantity=0）"""
        # inventory_itemのquantityを0にして非公開化
        # listing_idからSKUを取得する必要があるため、offerから取得
        # 簡易実装: eBay APIのwithdraw offerを使用
        sku = self._get_sku_from_listing(platform_listing_id)
        if sku:
            body = {
                "availability": {
                    "shipToLocationAvailability": {
                        "quantity": 0,
                    }
                }
            }
            response = httpx.put(
                f"{self.endpoints['inventory']}/inventory_item/{sku}",
                headers=self._headers(),
                json=body,
                timeout=30,
            )
            response.raise_for_status()

        return {"success": True, "status": "paused"}

    def activate_listing(self, platform_listing_id: str) -> Dict[str, Any]:
        """リスティングを再公開（在庫復活: quantity=5）"""
        sku = self._get_sku_from_listing(platform_listing_id)
        if sku:
            body = {
                "availability": {
                    "shipToLocationAvailability": {
                        "quantity": 5,
                    }
                }
            }
            response = httpx.put(
                f"{self.endpoints['inventory']}/inventory_item/{sku}",
                headers=self._headers(),
                json=body,
                timeout=30,
            )
            response.raise_for_status()

        return {"success": True, "status": "active"}

    def _get_sku_from_listing(self, listing_id: str) -> Optional[str]:
        """listing_idからSKUを逆引き（offerを検索）"""
        response = httpx.get(
            f"{self.endpoints['inventory']}/offer",
            headers=self._headers(),
            params={"marketplace_id": self.marketplace_id},
            timeout=30,
        )
        if response.status_code != 200:
            return None

        offers = response.json().get("offers", [])
        for offer in offers:
            if offer.get("listing", {}).get("listingId") == listing_id:
                return offer.get("sku")
        return None

    def get_orders(self, since: Optional[datetime] = None) -> List[Dict[str, Any]]:
        """注文を取得（Fulfillment API）"""
        if since is None:
            since = datetime.utcnow() - timedelta(hours=24)

        # ISO 8601フォーマット
        since_str = since.strftime("%Y-%m-%dT%H:%M:%S.000Z")

        response = httpx.get(
            f"{self.endpoints['fulfillment']}/order",
            headers=self._headers(),
            params={
                "filter": f"creationdate:[{since_str}..]",
                "limit": "50",
            },
            timeout=30,
        )
        response.raise_for_status()
        data = response.json()

        orders = []
        for order in data.get("orders", []):
            items = []
            total_price = 0.0
            total_fees = 0.0

            for item in order.get("lineItems", []):
                items.append({
                    "platform_listing_id": item.get("legacyItemId", ""),
                    "quantity": item.get("quantity", 1),
                    "title": item.get("title", ""),
                })
                total_price += float(item.get("total", {}).get("value", 0))

            # 手数料計算（orderPaymentSummary）
            fee_summary = order.get("totalFeeBasisAmount", {})
            if fee_summary:
                total_fees = float(fee_summary.get("value", 0))

            # 配送先国
            ship_to = order.get("fulfillmentStartInstructions", [{}])
            country = ""
            if ship_to:
                addr = ship_to[0].get("shippingStep", {}).get(
                    "shipTo", {}
                ).get("contactAddress", {})
                country = addr.get("countryCode", "")

            orders.append({
                "platform_order_id": order.get("orderId", ""),
                "buyer_country": country,
                "items": items,
                "sale_price_usd": total_price,
                "platform_fees_usd": total_fees,
                "shipping_cost_usd": 0.0,  # 別途計算
                "ordered_at": order.get("creationDate", ""),
                "status": order.get("orderFulfillmentStatus", "NOT_STARTED"),
            })

        return orders

    def upload_tracking(self, platform_order_id: str,
                        tracking_number: str,
                        carrier: str) -> Dict[str, Any]:
        """追跡番号をアップロード"""
        body = {
            "lineItems": [
                {
                    "lineItemId": "0",  # 全品目に適用
                    "quantity": 1,
                }
            ],
            "shippingCarrierCode": carrier,
            "trackingNumber": tracking_number,
        }

        response = httpx.post(
            f"{self.endpoints['fulfillment']}/order/{platform_order_id}/shipping_fulfillment",
            headers=self._headers(),
            json=body,
            timeout=30,
        )
        response.raise_for_status()
        return {"success": True}
