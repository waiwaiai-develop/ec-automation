"""Etsy API v3 クライアント

Etsyは1ステップでリスティング作成可能（POSTのみ）。
craft supplies / handmade カテゴリ限定。
BasePlatformClientインターフェースを実装。
"""

import json
import os
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import httpx

from src.auth.oauth_manager import OAuthTokenManager
from src.platforms.base_client import BasePlatformClient

# Etsy API v3 エンドポイント
ETSY_BASE_URL = "https://openapi.etsy.com/v3/application"

# Etsy "who_made" / "when_made" / "is_supply" 定数
# ドロップシッピングなので "someone_else" + "made_to_order" が安全
DEFAULT_WHO_MADE = "someone_else"
DEFAULT_WHEN_MADE = "2020_2025"
DEFAULT_IS_SUPPLY = False


class EtsyClient(BasePlatformClient):
    """Etsy API v3 クライアント"""

    def __init__(self):
        self.token_manager = OAuthTokenManager("etsy")
        self.shop_id = os.environ.get("ETSY_SHOP_ID", "")
        self.api_key = os.environ.get("ETSY_API_KEY", "")

    @property
    def platform_name(self) -> str:
        return "etsy"

    def _headers(self) -> Dict[str, str]:
        """認証ヘッダーを構築"""
        token = self.token_manager.get_valid_token()
        return {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "x-api-key": self.api_key,
        }

    def _ensure_shop_id(self) -> str:
        """shop_idを確認・取得"""
        if self.shop_id:
            return self.shop_id

        # トークンからshop_idを取得
        response = httpx.get(
            f"{ETSY_BASE_URL}/users/me",
            headers=self._headers(),
            timeout=30,
        )
        response.raise_for_status()
        user_data = response.json()
        user_id = user_data.get("user_id")

        # ユーザーのショップを取得
        response = httpx.get(
            f"{ETSY_BASE_URL}/users/{user_id}/shops",
            headers=self._headers(),
            timeout=30,
        )
        response.raise_for_status()
        shops = response.json().get("results", [])
        if not shops:
            raise ValueError("Etsyショップが見つかりません。先にショップを作成してください。")

        self.shop_id = str(shops[0]["shop_id"])
        return self.shop_id

    def create_listing(self, product: Dict[str, Any],
                       listing_data: Dict[str, Any]) -> Dict[str, Any]:
        """Etsy リスティング作成（1ステップPOST）

        Args:
            product: DBのproductsテーブルの行データ
            listing_data: {
                "title_en": str,
                "description_en": str,
                "price_usd": float,
                "tags": list,
                "taxonomy_id": int,     # Etsyのタクソノミー ID
                "shipping_profile_id": int,
                "quantity": int,
            }
        """
        shop_id = self._ensure_shop_id()

        # タグは最大13個、各タグ最大20文字
        tags = listing_data.get("tags", [])
        tags = [t[:20] for t in tags[:13]]

        body = {
            "title": listing_data["title_en"][:140],  # Etsy上限140文字
            "description": listing_data["description_en"],
            "price": listing_data["price_usd"],
            "quantity": listing_data.get("quantity", 5),
            "who_made": DEFAULT_WHO_MADE,
            "when_made": DEFAULT_WHEN_MADE,
            "is_supply": DEFAULT_IS_SUPPLY,
            "tags": tags,
            "state": "draft",  # まずドラフトで作成、画像追加後にアクティブ化
        }

        # タクソノミーID（カテゴリ）
        taxonomy_id = listing_data.get("taxonomy_id")
        if taxonomy_id:
            body["taxonomy_id"] = taxonomy_id

        # 配送プロファイル
        shipping_profile_id = listing_data.get("shipping_profile_id")
        if shipping_profile_id:
            body["shipping_profile_id"] = shipping_profile_id

        response = httpx.post(
            f"{ETSY_BASE_URL}/shops/{shop_id}/listings",
            headers=self._headers(),
            json=body,
            timeout=30,
        )
        response.raise_for_status()
        result = response.json()

        listing_id = str(result["listing_id"])

        # 画像アップロード
        image_urls = product.get("image_urls")
        if isinstance(image_urls, str):
            image_urls = json.loads(image_urls)
        if image_urls:
            self._upload_images(shop_id, listing_id, image_urls)

        return {
            "platform_listing_id": listing_id,
            "status": "draft",
            "url": result.get("url", f"https://www.etsy.com/listing/{listing_id}"),
        }

    def _upload_images(self, shop_id: str, listing_id: str,
                       image_urls: List[str]) -> None:
        """リスティングに画像をアップロード（URL経由）"""
        for url in image_urls[:10]:  # Etsy上限10枚
            try:
                # 画像をダウンロード
                img_response = httpx.get(url, timeout=15)
                if img_response.status_code != 200:
                    continue

                # multipart/form-dataでアップロード
                headers = {
                    "Authorization": f"Bearer {self.token_manager.get_valid_token()}",
                    "x-api-key": self.api_key,
                }
                files = {"image": ("image.jpg", img_response.content, "image/jpeg")}
                response = httpx.post(
                    f"{ETSY_BASE_URL}/shops/{shop_id}/listings/{listing_id}/images",
                    headers=headers,
                    files=files,
                    timeout=30,
                )
                # 画像アップロード失敗は致命的ではないのでログのみ
            except Exception:
                continue

    def update_listing(self, platform_listing_id: str,
                       updates: Dict[str, Any]) -> Dict[str, Any]:
        """リスティングを更新"""
        shop_id = self._ensure_shop_id()
        updated_fields = []

        body = {}
        if "title_en" in updates:
            body["title"] = updates["title_en"][:140]
            updated_fields.append("title_en")
        if "description_en" in updates:
            body["description"] = updates["description_en"]
            updated_fields.append("description_en")
        if "price_usd" in updates:
            body["price"] = updates["price_usd"]
            updated_fields.append("price_usd")
        if "tags" in updates:
            body["tags"] = [t[:20] for t in updates["tags"][:13]]
            updated_fields.append("tags")

        if not body:
            return {"success": True, "updated_fields": []}

        response = httpx.put(
            f"{ETSY_BASE_URL}/shops/{shop_id}/listings/{platform_listing_id}",
            headers=self._headers(),
            json=body,
            timeout=30,
        )
        response.raise_for_status()

        return {"success": True, "updated_fields": updated_fields}

    def deactivate_listing(self, platform_listing_id: str) -> Dict[str, Any]:
        """リスティングを非公開（state=inactive）"""
        shop_id = self._ensure_shop_id()

        response = httpx.put(
            f"{ETSY_BASE_URL}/shops/{shop_id}/listings/{platform_listing_id}",
            headers=self._headers(),
            json={"state": "inactive"},
            timeout=30,
        )
        response.raise_for_status()

        return {"success": True, "status": "paused"}

    def activate_listing(self, platform_listing_id: str) -> Dict[str, Any]:
        """リスティングを再公開（state=active）"""
        shop_id = self._ensure_shop_id()

        response = httpx.put(
            f"{ETSY_BASE_URL}/shops/{shop_id}/listings/{platform_listing_id}",
            headers=self._headers(),
            json={"state": "active"},
            timeout=30,
        )
        response.raise_for_status()

        return {"success": True, "status": "active"}

    def get_orders(self, since: Optional[datetime] = None) -> List[Dict[str, Any]]:
        """注文を取得"""
        shop_id = self._ensure_shop_id()

        if since is None:
            since = datetime.utcnow() - timedelta(hours=24)

        # UNIXタイムスタンプに変換
        min_created = int(since.timestamp())

        response = httpx.get(
            f"{ETSY_BASE_URL}/shops/{shop_id}/receipts",
            headers=self._headers(),
            params={
                "min_created": min_created,
                "limit": 50,
            },
            timeout=30,
        )
        response.raise_for_status()
        data = response.json()

        orders = []
        for receipt in data.get("results", []):
            items = []
            for transaction in receipt.get("transactions", []):
                items.append({
                    "platform_listing_id": str(transaction.get("listing_id", "")),
                    "quantity": transaction.get("quantity", 1),
                    "title": transaction.get("title", ""),
                })

            # 価格情報（Etsyはセント単位の場合がある）
            total = receipt.get("grandtotal", {})
            total_price = float(total.get("amount", 0)) / max(total.get("divisor", 100), 1)

            # 配送先国
            country = receipt.get("country_iso", "")

            orders.append({
                "platform_order_id": str(receipt.get("receipt_id", "")),
                "buyer_country": country,
                "items": items,
                "sale_price_usd": total_price,
                "platform_fees_usd": 0.0,  # Etsyはレシートに手数料を含めない
                "shipping_cost_usd": 0.0,
                "ordered_at": datetime.fromtimestamp(
                    receipt.get("created_timestamp", 0)
                ).isoformat(),
                "status": receipt.get("status", "open"),
            })

        return orders

    def upload_tracking(self, platform_order_id: str,
                        tracking_number: str,
                        carrier: str) -> Dict[str, Any]:
        """追跡番号をアップロード"""
        shop_id = self._ensure_shop_id()

        # Etsy配送キャリアコードマッピング
        carrier_map = {
            "Japan Post": "japan-post",
            "EMS": "japan-post",
            "DHL": "dhl",
            "FedEx": "fedex",
        }
        carrier_code = carrier_map.get(carrier, "other")

        response = httpx.post(
            f"{ETSY_BASE_URL}/shops/{shop_id}/receipts/{platform_order_id}/tracking",
            headers=self._headers(),
            json={
                "tracking_code": tracking_number,
                "carrier_name": carrier_code,
            },
            timeout=30,
        )
        response.raise_for_status()
        return {"success": True}
