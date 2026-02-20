"""eBay Browse API クライアント

OAuth 2.0 Client Credentials フローで認証し、
Browse API v1で商品検索 → 価格統計集約を行う。

デフォルトはsandbox。本番はEPN承認後に切替。
"""

import os
import statistics
from typing import Any, Dict, List, Optional

import httpx
import yaml

_CONFIG_PATH = os.path.join(
    os.path.dirname(__file__), "..", "..", "config", "config.yaml"
)


def _load_config() -> dict:
    try:
        with open(_CONFIG_PATH, encoding="utf-8") as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        return {}


class EbayBrowseClient:
    """eBay Browse API v1 クライアント"""

    def __init__(self, sandbox: bool = True):
        config = _load_config()
        env_key = "sandbox" if sandbox else "production"
        ebay_config = config.get("ebay", {}).get(env_key, {})

        self.browse_url = ebay_config.get(
            "browse_url",
            "https://api.sandbox.ebay.com/buy/browse/v1"
            if sandbox
            else "https://api.ebay.com/buy/browse/v1",
        )
        self.auth_url = ebay_config.get(
            "auth_url",
            "https://api.sandbox.ebay.com/identity/v1/oauth2/token"
            if sandbox
            else "https://api.ebay.com/identity/v1/oauth2/token",
        )
        self.marketplace_id = config.get("ebay", {}).get(
            "marketplace_id", "EBAY_US"
        )

        self.client_id = os.getenv("EBAY_CLIENT_ID", "")
        self.client_secret = os.getenv("EBAY_CLIENT_SECRET", "")
        self._access_token: Optional[str] = None

        if not self.client_id or not self.client_secret:
            raise ValueError(
                "EBAY_CLIENT_ID / EBAY_CLIENT_SECRET が未設定です。"
                "config/.envに設定してください。"
            )

    async def _authenticate(self) -> str:
        """OAuth 2.0 Client Credentials フローでアクセストークン取得"""
        if self._access_token:
            return self._access_token

        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                self.auth_url,
                data={
                    "grant_type": "client_credentials",
                    "scope": "https://api.ebay.com/oauth/api_scope",
                },
                auth=(self.client_id, self.client_secret),
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            resp.raise_for_status()
            data = resp.json()
            self._access_token = data["access_token"]
            return self._access_token

    async def search(
        self,
        keyword: str,
        limit: int = 50,
        sort: str = "BEST_MATCH",
        min_price: Optional[float] = None,
        max_price: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Browse API で商品検索

        Args:
            keyword: 検索キーワード（英語推奨）
            limit: 取得件数（最大200）
            sort: ソート順（BEST_MATCH, PRICE, NEWLY_LISTED等）
            min_price: 最低価格フィルタ（USD）
            max_price: 最高価格フィルタ（USD）

        Returns:
            APIレスポンス（itemSummaries, total等）
        """
        token = await self._authenticate()

        params: Dict[str, Any] = {
            "q": keyword,
            "limit": min(limit, 200),
            "sort": sort,
        }

        # 価格フィルタ
        filters = []
        if min_price is not None:
            filters.append(f"price:[{min_price}..],priceCurrency:USD")
        if max_price is not None:
            filters.append(f"price:[..{max_price}],priceCurrency:USD")
        if filters:
            params["filter"] = ",".join(filters)

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(
                f"{self.browse_url}/item_summary/search",
                params=params,
                headers={
                    "Authorization": f"Bearer {token}",
                    "X-EBAY-C-MARKETPLACE-ID": self.marketplace_id,
                    "Accept": "application/json",
                },
            )
            resp.raise_for_status()
            return resp.json()

    async def keyword_research(
        self,
        keyword: str,
        limit: int = 50,
    ) -> Dict[str, Any]:
        """キーワードリサーチ: 検索 → 価格統計集約

        Returns:
            {
                keyword, total_results, sample_size,
                avg_price_usd, min_price_usd, max_price_usd,
                median_price_usd, avg_shipping_usd,
                top_items: [{title, price, shipping, seller, condition}]
            }
        """
        data = await self.search(keyword, limit=limit)

        items = data.get("itemSummaries", [])
        total = data.get("total", 0)

        if not items:
            return {
                "keyword": keyword,
                "total_results": total,
                "sample_size": 0,
                "avg_price_usd": None,
                "min_price_usd": None,
                "max_price_usd": None,
                "median_price_usd": None,
                "avg_shipping_usd": None,
                "top_items": [],
            }

        # 価格を抽出
        prices = []
        shipping_costs = []
        top_items = []

        for item in items:
            price_info = item.get("price", {})
            price_val = price_info.get("value")
            if price_val:
                try:
                    prices.append(float(price_val))
                except (ValueError, TypeError):
                    pass

            # 送料
            shipping_options = item.get("shippingOptions", [])
            if shipping_options:
                ship_cost = shipping_options[0].get("shippingCost", {})
                ship_val = ship_cost.get("value")
                if ship_val:
                    try:
                        shipping_costs.append(float(ship_val))
                    except (ValueError, TypeError):
                        pass

            # 上位商品（表示用）
            if len(top_items) < 10:
                top_items.append(
                    {
                        "title": item.get("title", ""),
                        "price": price_val,
                        "shipping": (
                            shipping_options[0]
                            .get("shippingCost", {})
                            .get("value")
                            if shipping_options
                            else None
                        ),
                        "seller": item.get("seller", {}).get(
                            "username", ""
                        ),
                        "condition": item.get("condition", ""),
                        "item_web_url": item.get("itemWebUrl", ""),
                    }
                )

        result = {
            "keyword": keyword,
            "total_results": total,
            "sample_size": len(prices),
            "avg_price_usd": (
                round(statistics.mean(prices), 2) if prices else None
            ),
            "min_price_usd": round(min(prices), 2) if prices else None,
            "max_price_usd": round(max(prices), 2) if prices else None,
            "median_price_usd": (
                round(statistics.median(prices), 2) if prices else None
            ),
            "avg_shipping_usd": (
                round(statistics.mean(shipping_costs), 2)
                if shipping_costs
                else None
            ),
            "top_items": top_items,
        }

        return result
