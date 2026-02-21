"""NETSEA REST APIクライアント

公式API（https://api.netsea.jp/buyer/v1）を使用。
認証: Bearer token（.envのNETSEA_API_TOKEN）

API仕様:
  - POST /items: 商品取得（supplier_ids必須、form-encoded）
  - GET /categories: カテゴリ一覧
  - GET /suppliers: サプライヤー一覧

注意:
  - POST /items は必ず form-encoded で送信（JSONだとエラー）
  - supplier_ids はカンマ区切り文字列
  - category_id でカテゴリ絞り込み可能
  - レスポンスは最大100件
"""

import os
import re
from typing import Any, Dict, List, Optional

import httpx
import yaml

# 設定ファイル読み込み
_CONFIG_PATH = os.path.join(
    os.path.dirname(__file__), "..", "..", "config", "config.yaml"
)

# よく使うカテゴリID（NETSEAカテゴリ体系）
CATEGORY_IDS = {
    "tenugui": 21205,     # 手ぬぐい
    "incense": 31801,     # お香・線香
    "kitchen": 20134,     # 鍋・調理器具（包丁含む）
    "origami": 21516,     # おりがみ
}


def _load_config() -> dict:
    """config.yamlを読み込み"""
    try:
        with open(_CONFIG_PATH, encoding="utf-8") as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        return {"netsea": {"base_url": "https://api.netsea.jp/buyer/v1"}}


def extract_weight_g(spec_text):
    # type: (Optional[str]) -> Optional[int]
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


def _detect_category(name, description=""):
    # type: (str, str) -> Optional[str]
    """商品名・説明からカテゴリを推定"""
    text = "{} {}".format(name, description).lower()

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
    """NETSEA REST APIクライアント

    API制約:
      - POST /items は supplier_ids（必須）をform-encodedで送信
      - category_id でカテゴリ絞り込み可能
      - レスポンスは最大100件
    """

    def __init__(self, token=None):
        # type: (Optional[str]) -> None
        config = _load_config()
        netsea_config = config.get("netsea", {})

        self.base_url = netsea_config.get(
            "base_url", "https://api.netsea.jp/buyer/v1"
        )
        self.token = token or os.getenv("NETSEA_API_TOKEN", "")

        if not self.token:
            raise ValueError(
                "NETSEA_API_TOKENが未設定です。"
                "config/.envにトークンを設定してください。"
            )

    def _headers(self):
        # type: () -> Dict[str, str]
        """認証ヘッダー"""
        return {
            "Authorization": "Bearer {}".format(self.token),
            "Accept": "application/json",
        }

    def get_items(
        self,
        supplier_ids,       # type: Any
        category_id=None,   # type: Optional[int]
        keyword=None,       # type: Optional[str]
    ):
        # type: (...) -> List[Dict[str, Any]]
        """サプライヤーIDから商品を取得

        Args:
            supplier_ids: サプライヤーID（int, str, またはリスト）
            category_id: NETSEAカテゴリID（オプション）
            keyword: ローカルキーワードフィルター（商品名で絞り込み）

        Returns:
            商品リスト（APIレスポンスのdata配列）

        Raises:
            ValueError: APIエラー時
        """
        # supplier_idsをカンマ区切り文字列に変換
        if isinstance(supplier_ids, (list, tuple)):
            ids_str = ",".join(str(sid) for sid in supplier_ids)
        else:
            ids_str = str(supplier_ids)

        # form-encodedでPOST（JSONではエラーになる）
        form_data = {"supplier_ids": ids_str}
        if category_id is not None:
            form_data["category_id"] = str(category_id)

        resp = httpx.post(
            "{}/items".format(self.base_url),
            data=form_data,
            headers=self._headers(),
            timeout=30.0,
        )
        resp.raise_for_status()
        result = resp.json()

        # APIエラーチェック
        error = result.get("error")
        if error and error.get("code", 0) != 0:
            raise ValueError(
                "NETSEA APIエラー: code={}, subcode={}, {}".format(
                    error["code"],
                    error.get("subcode", ""),
                    error.get("message", ""),
                )
            )

        items = result.get("data", [])

        # ローカルキーワードフィルター（API側にはキーワード検索機能なし）
        if keyword:
            kw_lower = keyword.lower()
            items = [
                i for i in items
                if kw_lower in i.get("product_name", "").lower()
            ]

        return items

    def get_categories(self):
        # type: () -> List[Dict[str, Any]]
        """カテゴリ一覧を取得"""
        resp = httpx.get(
            "{}/categories".format(self.base_url),
            headers=self._headers(),
            timeout=30.0,
        )
        resp.raise_for_status()
        result = resp.json()
        if isinstance(result, list):
            return result
        return result.get("categories", [])

    def get_suppliers(self, limit=100, offset=0):
        # type: (int, int) -> List[Dict[str, Any]]
        """サプライヤー一覧を取得"""
        resp = httpx.get(
            "{}/suppliers".format(self.base_url),
            params={"limit": limit, "offset": offset},
            headers=self._headers(),
            timeout=30.0,
        )
        resp.raise_for_status()
        result = resp.json()
        return result.get("data", [])

    def map_to_db(self, netsea_item):
        # type: (Dict[str, Any]) -> Dict[str, Any]
        """NETSEAのAPIレスポンスをDBカラムにマッピング

        実APIフィールド: product_name, product_id, set[], image_url_1〜10
        旧テスト互換: item_name, item_id, sets[], images[]
        """
        # 商品名（実API=product_name, 旧=item_name/name）
        name = netsea_item.get(
            "product_name",
            netsea_item.get("item_name", netsea_item.get("name", ""))
        )
        description = netsea_item.get("description", "")
        spec_size = netsea_item.get("spec_size", "")

        # 画像URL（実API: image_url_1〜image_url_10）
        image_urls = []
        for i in range(1, 11):
            url = netsea_item.get("image_url_{}".format(i), "")
            if url:
                image_urls.append(url)
        # 旧形式フォールバック
        if not image_urls:
            images = netsea_item.get("images", [])
            if isinstance(images, list):
                image_urls = [
                    img["url"] if isinstance(img, dict) else img
                    for img in images
                ]

        # セット内の最安価格を卸値とする（実API: "set", 旧: "sets"）
        sets = netsea_item.get("set", netsea_item.get("sets", []))
        wholesale_price = None
        if sets:
            prices = [
                s.get("price") for s in sets
                if s.get("price") is not None
            ]
            if prices:
                wholesale_price = min(prices)
        if wholesale_price is None:
            wholesale_price = netsea_item.get(
                "wholesale_price", netsea_item.get("price")
            )

        # 在庫状態（実API: set[].sold_out_flag）
        if sets and any("sold_out_flag" in s for s in sets):
            any_in_stock = any(
                s.get("sold_out_flag") != "Y" for s in sets
            )
            stock_status = "in_stock" if any_in_stock else "out_of_stock"
        else:
            stock = netsea_item.get("stock_status", netsea_item.get("stock"))
            if isinstance(stock, int):
                stock_status = "in_stock" if stock > 0 else "out_of_stock"
            elif isinstance(stock, str):
                stock_status = stock
            else:
                stock_status = "in_stock"

        # 商品ID（実API: product_id, 旧: item_id/id）
        product_id = netsea_item.get(
            "product_id",
            netsea_item.get("item_id", netsea_item.get("id", ""))
        )

        # 参考上代（定価）— set内の最安reference_price
        reference_price = None
        if sets:
            ref_prices = [
                s.get("reference_price") for s in sets
                if s.get("reference_price") is not None
            ]
            if ref_prices:
                reference_price = min(ref_prices)
        if reference_price is None:
            reference_price = netsea_item.get("reference_price")

        return {
            "supplier": "netsea",
            "supplier_product_id": str(product_id),
            "name_ja": name,
            "description_ja": description,
            "category": _detect_category(name, description),
            "wholesale_price_jpy": (
                int(wholesale_price) if wholesale_price else None
            ),
            "weight_g": extract_weight_g(spec_size),
            "image_urls": image_urls,
            "stock_status": stock_status,
            "product_url": netsea_item.get("product_url", ""),
            "supplier_id": str(netsea_item.get("supplier_id", "")),
            "shop_name": netsea_item.get("shop_name", ""),
            "spec_text": spec_size,
            "reference_price_jpy": (
                int(reference_price) if reference_price else None
            ),
            "netsea_category_id": netsea_item.get("category_id"),
            "direct_send_flag": netsea_item.get("direct_send_flag"),
            "image_copy_flag": netsea_item.get("image_copy_flag"),
            "deal_net_shop_flag": netsea_item.get("deal_net_shop_flag"),
            "deal_net_auction_flag": netsea_item.get("deal_net_auction_flag"),
        }

    def get_items_and_map(
        self,
        supplier_ids,       # type: Any
        category_id=None,   # type: Optional[int]
        keyword=None,       # type: Optional[str]
    ):
        # type: (...) -> List[Dict[str, Any]]
        """商品を取得してDBマッピング済みリストを返す"""
        items = self.get_items(
            supplier_ids,
            category_id=category_id,
            keyword=keyword,
        )
        return [self.map_to_db(item) for item in items]
