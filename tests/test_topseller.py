"""TopSellerスクレイパーテスト

- カテゴリ検出
- 重量抽出
- 価格抽出
- DBマッピング
- 商品ID抽出
"""

import pytest

from src.scraper.topseller import (
    TopSellerClient,
    _detect_category,
    extract_price,
    extract_weight_g,
)


class TestCategoryDetection:
    """カテゴリ検出テスト"""

    def test_tenugui(self):
        assert _detect_category("和柄手ぬぐい 富士山") == "tenugui"

    def test_furoshiki(self):
        assert _detect_category("大判風呂敷 70cm") == "furoshiki"

    def test_knife(self):
        assert _detect_category("三徳包丁 165mm") == "knife"

    def test_incense(self):
        assert _detect_category("京都のお香セット") == "incense"

    def test_washi(self):
        assert _detect_category("友禅和紙 千代紙") == "washi"

    def test_unknown(self):
        assert _detect_category("よくわからない商品") is None

    def test_description_fallback(self):
        """商品名にないがdescriptionにある場合"""
        assert _detect_category("柄物クロス", "手ぬぐい生地使用") == "tenugui"


class TestWeightExtraction:
    """重量抽出テスト"""

    def test_basic_g(self):
        assert extract_weight_g("重さ：約50g") == 50

    def test_weight_colon(self):
        assert extract_weight_g("重量:100g") == 100

    def test_gram_unit(self):
        assert extract_weight_g("約50グラム") == 50

    def test_kg(self):
        assert extract_weight_g("約0.5kg") == 500

    def test_none_input(self):
        assert extract_weight_g(None) is None

    def test_no_weight(self):
        assert extract_weight_g("サイズ: 30cm x 90cm") is None


class TestPriceExtraction:
    """価格抽出テスト"""

    def test_yen_symbol(self):
        assert extract_price("¥1,000") == 1000

    def test_en_suffix(self):
        assert extract_price("500円") == 500

    def test_comma_separated(self):
        assert extract_price("¥12,345") == 12345

    def test_price_label(self):
        assert extract_price("価格：2000") == 2000

    def test_none_input(self):
        assert extract_price(None) is None

    def test_no_price(self):
        assert extract_price("在庫あり") is None


class TestProductIdExtraction:
    """商品ID抽出テスト"""

    def test_product_path(self):
        client = TopSellerClient()
        assert client._extract_product_id(
            "https://top-seller.jp/product/12345"
        ) == "12345"

    def test_items_path(self):
        client = TopSellerClient()
        assert client._extract_product_id(
            "https://top-seller.jp/items/67890"
        ) == "67890"

    def test_trailing_number(self):
        client = TopSellerClient()
        assert client._extract_product_id(
            "https://top-seller.jp/shop/99999"
        ) == "99999"

    def test_empty_url(self):
        client = TopSellerClient()
        assert client._extract_product_id("") == ""


class TestMapToDb:
    """DBマッピングテスト"""

    def test_basic_mapping(self):
        client = TopSellerClient()
        result = client.map_to_db({
            "name": "和柄手ぬぐい 富士山",
            "price": 500,
            "product_url": "https://top-seller.jp/product/12345",
            "product_id": "12345",
            "image_urls": ["https://example.com/img1.jpg"],
            "spec_text": "重さ：約50g",
        })

        assert result["supplier"] == "topseller"
        assert result["supplier_product_id"] == "TS-12345"
        assert result["name_ja"] == "和柄手ぬぐい 富士山"
        assert result["category"] == "tenugui"
        assert result["wholesale_price_jpy"] == 500
        assert result["weight_g"] == 50
        assert result["shop_name"] == "TopSeller"
        assert len(result["image_urls"]) == 1

    def test_mapping_without_price(self):
        client = TopSellerClient()
        result = client.map_to_db({
            "name": "お香セット",
            "product_id": "999",
        })

        assert result["supplier_product_id"] == "TS-999"
        assert result["wholesale_price_jpy"] is None
        assert result["category"] == "incense"

    def test_mapping_empty_id(self):
        client = TopSellerClient()
        result = client.map_to_db({
            "name": "テスト商品",
            "product_id": "",
        })
        assert result["supplier_product_id"] == ""


class TestSearchUrl:
    """検索URL構築テスト"""

    def test_keyword_search(self):
        client = TopSellerClient()
        url = client._build_search_url("手ぬぐい", None, 1)
        assert "keyword=手ぬぐい" in url

    def test_pagination(self):
        client = TopSellerClient()
        url = client._build_search_url(None, None, 3)
        assert "page=3" in url

    def test_no_params(self):
        client = TopSellerClient()
        url = client._build_search_url(None, None, 1)
        assert url == "https://top-seller.jp"
