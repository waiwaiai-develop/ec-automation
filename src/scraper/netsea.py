"""NETSEA REST APIクライアント

公式API（https://api.netsea.jp/buyer/v1）を使用。
Playwrightスクレイピング不要で、認可されたデータパイプラインを構築。

認証: Bearer token（.envのNETSEA_API_TOKEN）
"""

import json
import os
import re
from typing import Any, Dict, List, Optional

import httpx
import yaml

# 設定ファイル読み込み
_CONFIG_PATH = os.path.join(
    os.path.dirname(__file__), "..", "..", "config", "config.yaml"
)


def _load_config() -> dict:
    """config.yamlを読み込み"""
    try:
        with open(_CONFIG_PATH, encoding="utf-8") as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        return {"netsea": {"base_url": "https://api.netsea.jp/buyer/v1"}}


def extract_weight_g(spec_text: Optional[str]) -> Optional[int]:
    """spec_size等のテキストから重量(g)を正規表現で抽出

    対応パターン:
      - 重さ：約50g → 50
      - 重量:100g → 100
      - 約50グラム → 50
      - 重さ 約 50 g → 50
      - 50g → 50
      - 0.5kg → 500
      - 約0.3kg → 300

    Returns:
        重量(g)。抽出できない場合はNone（0ではない）
    """
    if not spec_text:
        return None

    # kg パターン（先にチェック — gパターンより優先）
    kg_pattern = r"約?\s*(\d+(?:\.\d+)?)\s*(?:kg|キログラム|ｋｇ)"
    kg_match = re.search(kg_pattern, spec_text, re.IGNORECASE)
    if kg_match:
        return int(float(kg_match.group(1)) * 1000)

    # g パターン
    g_patterns = [
        r"重[さ量][：:]\s*約?\s*(\d+(?:\.\d+)?)\s*(?:g|グラム|ｇ)",
        r"重[さ量]\s+約?\s*(\d+(?:\.\d+)?)\s*(?:g|グラム|ｇ)",
        r"約?\s*(\d+(?:\.\d+)?)\s*(?:g|グラム|ｇ)(?!\w)",
    ]

    for pattern in g_patterns:
        match = re.search(pattern, spec_text, re.IGNORECASE)
        if match:
            value = float(match.group(1))
            if value > 0:
                return int(value)

    return None


def _detect_category(name: str, description: str = "") -> Optional[str]:
    """商品名・説明からカテゴリを推定"""
    text = f"{name} {description}".lower()

    category_keywords = {
        "tenugui": ["手ぬぐい", "手拭", "てぬぐい"],
        "furoshiki": ["風呂敷", "ふろしき"],
        "knife": ["包丁", "ナイフ", "刃物"],
        "incense": ["お香", "線香", "香立", "インセンス"],
        "washi": ["和紙", "千代紙", "折り紙"],
    }

    for category, keywords in category_keywords.items():
        for kw in keywords:
            if kw in text:
                return category

    return None


class NetseaClient:
    """NETSEA REST APIクライアント"""

    def __init__(self, token: Optional[str] = None):
        config = _load_config()
        netsea_config = config.get("netsea", {})

        self.base_url = netsea_config.get(
            "base_url", "https://api.netsea.jp/buyer/v1"
        )
        self.default_limit = netsea_config.get("default_limit", 50)
        self.max_limit = netsea_config.get("max_limit", 100)
        self.token = token or os.getenv("NETSEA_API_TOKEN", "")

        if not self.token:
            raise ValueError(
                "NETSEA_API_TOKENが未設定です。"
                "config/.envにトークンを設定してください。"
            )

    def _headers(self) -> Dict[str, str]:
        """認証ヘッダー"""
        return {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/json",
        }

    async def _get(
        self, path: str, params: Optional[dict] = None
    ) -> Dict[str, Any]:
        """GETリクエスト（共通処理）"""
        url = f"{self.base_url}{path}"
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(
                url, headers=self._headers(), params=params
            )
            resp.raise_for_status()
            return resp.json()

    async def search_products(
        self,
        keyword: str,
        limit: Optional[int] = None,
        offset: int = 0,
    ) -> Dict[str, Any]:
        """商品検索

        Args:
            keyword: 検索キーワード（日本語）
            limit: 取得件数（デフォルト: config設定値）
            offset: オフセット（ページネーション）

        Returns:
            APIレスポンス（items, total_count等）
        """
        limit = min(limit or self.default_limit, self.max_limit)
        params = {
            "keyword": keyword,
            "limit": limit,
            "offset": offset,
        }
        return await self._get("/items", params=params)

    async def get_product(self, product_id: str) -> Dict[str, Any]:
        """商品詳細を取得"""
        return await self._get(f"/items/{product_id}")

    async def get_categories(self) -> List[Dict[str, Any]]:
        """カテゴリ一覧を取得"""
        result = await self._get("/categories")
        return result.get("categories", result if isinstance(result, list) else [])

    def map_to_db(self, netsea_item: Dict[str, Any]) -> Dict[str, Any]:
        """NETSEAのAPIレスポンスをDBカラムにマッピング

        NETSEA APIのフィールド名は推定（実際のAPI仕様に合わせて調整が必要）。
        """
        name = netsea_item.get("item_name", netsea_item.get("name", ""))
        description = netsea_item.get("description", "")
        spec_size = netsea_item.get("spec_size", "")

        # 画像URL
        images = netsea_item.get("images", [])
        if isinstance(images, list) and images:
            # 各画像がdictなら"url"キーを取得、文字列ならそのまま
            image_urls = [
                img["url"] if isinstance(img, dict) else img for img in images
            ]
        else:
            image_urls = []

        # セット内の最安価格を卸値とする
        sets = netsea_item.get("sets", [])
        wholesale_price = None
        if sets:
            prices = [
                s.get("price", s.get("wholesale_price"))
                for s in sets
                if s.get("price") or s.get("wholesale_price")
            ]
            if prices:
                wholesale_price = min(p for p in prices if p is not None)
        if wholesale_price is None:
            wholesale_price = netsea_item.get(
                "wholesale_price", netsea_item.get("price")
            )

        # 在庫状態
        stock = netsea_item.get("stock_status", netsea_item.get("stock"))
        if isinstance(stock, int):
            stock_status = "in_stock" if stock > 0 else "out_of_stock"
        elif isinstance(stock, str):
            stock_status = stock
        else:
            stock_status = "in_stock"

        return {
            "supplier": "netsea",
            "supplier_product_id": str(
                netsea_item.get("item_id", netsea_item.get("id", ""))
            ),
            "name_ja": name,
            "description_ja": description,
            "category": _detect_category(name, description),
            "wholesale_price_jpy": (
                int(wholesale_price) if wholesale_price else None
            ),
            "weight_g": extract_weight_g(
                f"{spec_size} {netsea_item.get('spec_weight', '')}"
            ),
            "image_urls": image_urls,
            "stock_status": stock_status,
        }

    async def search_and_map(
        self,
        keyword: str,
        limit: Optional[int] = None,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """検索してDBマッピング済みリストを返す"""
        result = await self.search_products(keyword, limit, offset)

        items = result.get("items", result if isinstance(result, list) else [])
        return [self.map_to_db(item) for item in items]
