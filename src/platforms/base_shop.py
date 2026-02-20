"""BASE API クライアント

BASE（https://thebase.com）のAPI連携。
ブランド構築用サブチャネル。
BasePlatformClientインターフェースを実装。
"""

import json
import os
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import httpx

from src.auth.oauth_manager import OAuthTokenManager
from src.platforms.base_client import BasePlatformClient

# BASE API エンドポイント
BASE_API_URL = "https://api.thebase.in/1"


class BaseShopClient(BasePlatformClient):
    """BASE APIクライアント"""

    def __init__(self):
        self.token_manager = OAuthTokenManager("base")
        self.api_url = BASE_API_URL

    @property
    def platform_name(self) -> str:
        return "base"

    def _headers(self) -> Dict[str, str]:
        """認証ヘッダーを構築"""
        token = self.token_manager.get_valid_token()
        return {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

    def create_listing(self, product: Dict[str, Any],
                       listing_data: Dict[str, Any]) -> Dict[str, Any]:
        """BASE商品登録

        Args:
            product: DBのproductsテーブルの行データ
            listing_data: {
                "title_en": str,      # BASEでは日本語タイトルも可
                "title_ja": str,
                "description_en": str,
                "description_ja": str,
                "price_jpy": int,     # BASEは円建て
                "stock": int,
            }
        """
        # BASEは日本語対応なので日本語タイトルを優先
        title = listing_data.get("title_ja") or listing_data.get("title_en", "")
        description = listing_data.get("description_ja") or listing_data.get("description_en", "")
        price = listing_data.get("price_jpy", 0)

        body = {
            "title": title[:100],  # BASE上限
            "detail": description,
            "price": price,
            "stock": listing_data.get("stock", 5),
            "visible": 1,  # 公開
        }

        response = httpx.post(
            f"{self.api_url}/items/add",
            headers=self._headers(),
            json=body,
            timeout=30,
        )
        response.raise_for_status()
        result = response.json().get("item", {})

        item_id = str(result.get("item_id", ""))

        # 画像アップロード
        image_urls = product.get("image_urls")
        if isinstance(image_urls, str):
            image_urls = json.loads(image_urls)
        if image_urls:
            self._upload_images(item_id, image_urls)

        return {
            "platform_listing_id": item_id,
            "status": "active",
            "url": result.get("detail_url", ""),
        }

    def _upload_images(self, item_id: str, image_urls: List[str]) -> None:
        """商品画像をアップロード"""
        for url in image_urls[:5]:  # BASE上限5枚
            try:
                img_response = httpx.get(url, timeout=15)
                if img_response.status_code != 200:
                    continue

                headers = {"Authorization": f"Bearer {self.token_manager.get_valid_token()}"}
                files = {"image": ("image.jpg", img_response.content, "image/jpeg")}
                httpx.post(
                    f"{self.api_url}/items/add_image",
                    headers=headers,
                    data={"item_id": item_id},
                    files=files,
                    timeout=30,
                )
            except Exception:
                continue

    def update_listing(self, platform_listing_id: str,
                       updates: Dict[str, Any]) -> Dict[str, Any]:
        """商品を更新"""
        updated_fields = []
        body = {"item_id": int(platform_listing_id)}

        if "title_ja" in updates or "title_en" in updates:
            body["title"] = (updates.get("title_ja") or updates.get("title_en", ""))[:100]
            updated_fields.append("title")
        if "description_ja" in updates or "description_en" in updates:
            body["detail"] = updates.get("description_ja") or updates.get("description_en", "")
            updated_fields.append("description")
        if "price_jpy" in updates:
            body["price"] = updates["price_jpy"]
            updated_fields.append("price_jpy")
        if "stock" in updates:
            body["stock"] = updates["stock"]
            updated_fields.append("stock")

        if len(body) <= 1:  # item_idのみ
            return {"success": True, "updated_fields": []}

        response = httpx.post(
            f"{self.api_url}/items/edit",
            headers=self._headers(),
            json=body,
            timeout=30,
        )
        response.raise_for_status()

        return {"success": True, "updated_fields": updated_fields}

    def deactivate_listing(self, platform_listing_id: str) -> Dict[str, Any]:
        """商品を非公開"""
        response = httpx.post(
            f"{self.api_url}/items/edit",
            headers=self._headers(),
            json={
                "item_id": int(platform_listing_id),
                "visible": 0,
            },
            timeout=30,
        )
        response.raise_for_status()
        return {"success": True, "status": "paused"}

    def activate_listing(self, platform_listing_id: str) -> Dict[str, Any]:
        """商品を再公開"""
        response = httpx.post(
            f"{self.api_url}/items/edit",
            headers=self._headers(),
            json={
                "item_id": int(platform_listing_id),
                "visible": 1,
            },
            timeout=30,
        )
        response.raise_for_status()
        return {"success": True, "status": "active"}

    def get_orders(self, since: Optional[datetime] = None) -> List[Dict[str, Any]]:
        """注文を取得"""
        if since is None:
            since = datetime.utcnow() - timedelta(hours=24)

        response = httpx.get(
            f"{self.api_url}/orders",
            headers=self._headers(),
            params={"limit": 50},
            timeout=30,
        )
        response.raise_for_status()
        data = response.json()

        orders = []
        for order in data.get("orders", []):
            ordered_at_str = order.get("ordered", "")
            # sinceフィルタ（BASE APIにはフィルタパラメータが限定的）
            if ordered_at_str:
                try:
                    ordered_at = datetime.fromisoformat(ordered_at_str)
                    if ordered_at < since:
                        continue
                except (ValueError, TypeError):
                    pass

            items = []
            for item in order.get("order_items", []):
                items.append({
                    "platform_listing_id": str(item.get("item_id", "")),
                    "quantity": item.get("amount", 1),
                    "title": item.get("title", ""),
                })

            total_price = float(order.get("total", 0))

            orders.append({
                "platform_order_id": str(order.get("unique_key", "")),
                "buyer_country": "JP",  # BASEは国内販売が主
                "items": items,
                "sale_price_usd": total_price / 150.0,  # JPY→USD概算
                "platform_fees_usd": 0.0,
                "shipping_cost_usd": 0.0,
                "ordered_at": ordered_at_str,
                "status": order.get("dispatch_status", "unpaid"),
            })

        return orders

    def upload_tracking(self, platform_order_id: str,
                        tracking_number: str,
                        carrier: str) -> Dict[str, Any]:
        """追跡番号をアップロード"""
        response = httpx.post(
            f"{self.api_url}/orders/edit_status",
            headers=self._headers(),
            json={
                "order_item_id": platform_order_id,
                "status": "dispatched",
                "tracking_number": tracking_number,
            },
            timeout=30,
        )
        response.raise_for_status()
        return {"success": True}
