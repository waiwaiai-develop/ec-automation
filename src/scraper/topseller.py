"""TopSeller スクレイパー

Playwrightを使用してTopSellerから商品情報を収集。
TopSellerはAPIを提供しないため、Webスクレイピングで取得。

対象URL: https://top-seller.jp
商品ページ構造を解析してDB保存用のデータにマッピング。
"""

import os
import re
from typing import Any, Dict, List, Optional

_CONFIG_PATH = os.path.join(
    os.path.dirname(__file__), "..", "..", "config", "config.yaml"
)

# TopSellerカテゴリマッピング
TOPSELLER_CATEGORIES = {
    "手ぬぐい": "tenugui",
    "てぬぐい": "tenugui",
    "風呂敷": "furoshiki",
    "ふろしき": "furoshiki",
    "包丁": "knife",
    "ナイフ": "knife",
    "刃物": "knife",
    "お香": "incense",
    "線香": "incense",
    "香立": "incense",
    "和紙": "washi",
    "千代紙": "washi",
    "折り紙": "washi",
}


def _detect_category(name, description=""):
    # type: (str, str) -> Optional[str]
    """商品名・説明からカテゴリを推定"""
    text = "{} {}".format(name, description).lower()
    for keyword, category in TOPSELLER_CATEGORIES.items():
        if keyword in text:
            return category
    return None


def extract_weight_g(text):
    # type: (Optional[str]) -> Optional[int]
    """テキストから重量(g)を抽出

    対応パターン:
      - 重さ：約50g / 重量:100g / 約50グラム
      - 0.5kg / 約0.3kg
    """
    if not text:
        return None

    # kgパターン（先にチェック）
    kg_match = re.search(
        r"約?\s*(\d+(?:\.\d+)?)\s*(?:kg|キログラム)", text, re.IGNORECASE
    )
    if kg_match:
        return int(float(kg_match.group(1)) * 1000)

    # gパターン
    g_patterns = [
        r"重[さ量][：:]\s*約?\s*(\d+(?:\.\d+)?)\s*(?:g|グラム)",
        r"重[さ量]\s+約?\s*(\d+(?:\.\d+)?)\s*(?:g|グラム)",
        r"約?\s*(\d+(?:\.\d+)?)\s*(?:g|グラム)(?!\w)",
    ]
    for pattern in g_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            value = float(match.group(1))
            if value > 0:
                return int(value)
    return None


def extract_price(text):
    # type: (Optional[str]) -> Optional[int]
    """テキストから価格(円)を抽出

    対応パターン: ¥1,000 / 1000円 / 1,000円(税込) / 価格: 500
    """
    if not text:
        return None

    patterns = [
        r"[¥￥]\s*([0-9,]+)",
        r"([0-9,]+)\s*円",
        r"価格[：:]\s*([0-9,]+)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            price_str = match.group(1).replace(",", "")
            try:
                return int(price_str)
            except ValueError:
                pass
    return None


class TopSellerClient:
    """TopSeller Webスクレイパー

    Playwrightを使って商品ページをスクレイピング。
    ログイン不要の公開商品ページのみ対象。
    """

    def __init__(self, base_url=None):
        # type: (Optional[str]) -> None
        self.base_url = base_url or "https://top-seller.jp"

    def scrape_products(
        self,
        keyword=None,      # type: Optional[str]
        category=None,      # type: Optional[str]
        max_pages=3,        # type: int
    ):
        # type: (...) -> List[Dict[str, Any]]
        """商品一覧ページをスクレイピング

        Args:
            keyword: 検索キーワード
            category: カテゴリ指定
            max_pages: 最大スクレイピングページ数

        Returns:
            商品データリスト（map_to_db形式）
        """
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            raise RuntimeError(
                "Playwrightが未インストールです。"
                "pip install playwright && playwright install chromium"
            )

        products = []

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()

            for page_num in range(1, max_pages + 1):
                url = self._build_search_url(keyword, category, page_num)

                try:
                    page.goto(url, timeout=30000)
                    page.wait_for_load_state("networkidle", timeout=15000)
                except Exception:
                    break

                # 商品カード要素を取得
                items = page.query_selector_all(
                    ".product-item, .item-card, [class*='product']"
                )

                if not items:
                    break

                for item in items:
                    try:
                        product = self._parse_product_card(item, page)
                        if product:
                            products.append(product)
                    except Exception:
                        continue

            browser.close()

        return products

    def scrape_product_detail(self, product_url):
        # type: (str) -> Optional[Dict[str, Any]]
        """商品詳細ページをスクレイピング

        Args:
            product_url: 商品ページURL

        Returns:
            商品データdict（map_to_db形式）
        """
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            raise RuntimeError(
                "Playwrightが未インストールです。"
                "pip install playwright && playwright install chromium"
            )

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()

            try:
                page.goto(product_url, timeout=30000)
                page.wait_for_load_state("networkidle", timeout=15000)
            except Exception:
                browser.close()
                return None

            product = self._parse_detail_page(page, product_url)
            browser.close()
            return product

    def _build_search_url(self, keyword, category, page_num):
        # type: (Optional[str], Optional[str], int) -> str
        """検索URLを構築"""
        url = self.base_url
        params = []

        if keyword:
            params.append("keyword={}".format(keyword))
        if category:
            params.append("category={}".format(category))
        if page_num > 1:
            params.append("page={}".format(page_num))

        if params:
            url += "/search?" + "&".join(params)

        return url

    def _parse_product_card(self, element, page):
        # type: (Any, Any) -> Optional[Dict[str, Any]]
        """商品カード要素から情報を抽出"""
        name = ""
        price = None
        product_url = ""
        image_url = ""

        # 商品名
        name_el = element.query_selector(
            "h3, h4, .product-name, .item-name, [class*='name']"
        )
        if name_el:
            name = (name_el.inner_text() or "").strip()

        if not name:
            return None

        # 価格
        price_el = element.query_selector(
            ".price, .item-price, [class*='price']"
        )
        if price_el:
            price = extract_price(price_el.inner_text())

        # URL
        link_el = element.query_selector("a[href]")
        if link_el:
            href = link_el.get_attribute("href") or ""
            if href.startswith("/"):
                product_url = self.base_url + href
            elif href.startswith("http"):
                product_url = href

        # 画像
        img_el = element.query_selector("img[src]")
        if img_el:
            image_url = img_el.get_attribute("src") or ""
            if image_url.startswith("/"):
                image_url = self.base_url + image_url

        # IDをURLから抽出
        product_id = self._extract_product_id(product_url)

        return self.map_to_db({
            "name": name,
            "price": price,
            "product_url": product_url,
            "product_id": product_id,
            "image_urls": [image_url] if image_url else [],
        })

    def _parse_detail_page(self, page, url):
        # type: (Any, str) -> Optional[Dict[str, Any]]
        """詳細ページから情報を抽出"""
        name = ""
        description = ""
        price = None
        spec_text = ""
        image_urls = []

        # 商品名
        name_el = page.query_selector(
            "h1, .product-title, .item-title, [class*='title']"
        )
        if name_el:
            name = (name_el.inner_text() or "").strip()

        if not name:
            return None

        # 説明文
        desc_el = page.query_selector(
            ".product-description, .item-description, "
            "[class*='description'], .detail-text"
        )
        if desc_el:
            description = (desc_el.inner_text() or "").strip()

        # 価格
        price_el = page.query_selector(
            ".price, .product-price, [class*='price']"
        )
        if price_el:
            price = extract_price(price_el.inner_text())

        # スペック（サイズ・重量など）
        spec_el = page.query_selector(
            ".spec, .product-spec, [class*='spec'], "
            ".detail-table, table"
        )
        if spec_el:
            spec_text = (spec_el.inner_text() or "").strip()

        # 画像
        img_elements = page.query_selector_all(
            ".product-image img, .gallery img, "
            "[class*='image'] img, .detail-img img"
        )
        for img in img_elements[:10]:
            src = img.get_attribute("src") or ""
            if src and not src.endswith(".svg"):
                if src.startswith("/"):
                    src = self.base_url + src
                image_urls.append(src)

        # メイン画像がなければog:imageを試す
        if not image_urls:
            og_img = page.query_selector("meta[property='og:image']")
            if og_img:
                content = og_img.get_attribute("content") or ""
                if content:
                    image_urls.append(content)

        product_id = self._extract_product_id(url)

        return self.map_to_db({
            "name": name,
            "description": description,
            "price": price,
            "product_url": url,
            "product_id": product_id,
            "image_urls": image_urls,
            "spec_text": spec_text,
        })

    def _extract_product_id(self, url):
        # type: (str) -> str
        """URLから商品IDを抽出"""
        if not url:
            return ""
        # /product/12345 や /items/12345 パターン
        match = re.search(r"/(?:product|item|goods|detail)[s]?/(\w+)", url)
        if match:
            return match.group(1)
        # 末尾の数字
        match = re.search(r"/(\d+)/?$", url)
        if match:
            return match.group(1)
        return ""

    def map_to_db(self, item):
        # type: (Dict[str, Any]) -> Dict[str, Any]
        """スクレイピング結果をDBカラムにマッピング"""
        name = item.get("name", "")
        description = item.get("description", "")
        spec_text = item.get("spec_text", "")

        product_id = item.get("product_id", "")
        supplier_product_id = "TS-{}".format(product_id) if product_id else ""

        return {
            "supplier": "topseller",
            "supplier_product_id": supplier_product_id,
            "name_ja": name,
            "description_ja": description,
            "category": _detect_category(name, description),
            "wholesale_price_jpy": item.get("price"),
            "weight_g": extract_weight_g(spec_text),
            "image_urls": item.get("image_urls", []),
            "stock_status": "in_stock",
            "product_url": item.get("product_url", ""),
            "supplier_id": "",
            "shop_name": "TopSeller",
            "spec_text": spec_text,
            "reference_price_jpy": None,
            "netsea_category_id": None,
            "direct_send_flag": None,
            "image_copy_flag": None,
            "deal_net_shop_flag": None,
            "deal_net_auction_flag": None,
        }
