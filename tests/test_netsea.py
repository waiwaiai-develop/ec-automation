"""NETSEAクライアント テスト

weight_g抽出の単体テスト（API不要、純粋関数テスト）。
カテゴリ推定テスト。
DBマッピングテスト。
"""

import pytest

from src.scraper.netsea import NetseaClient, extract_weight_g, _detect_category


class TestExtractWeightG:
    """重量抽出テスト — 様々な日本語パターンに対応"""

    def test_standard_format(self):
        """標準形式: 重さ：約50g"""
        assert extract_weight_g("重さ：約50g") == 50

    def test_colon_format(self):
        """コロン形式: 重量:100g"""
        assert extract_weight_g("重量:100g") == 100

    def test_katakana_gram(self):
        """カタカナ: 約50グラム"""
        assert extract_weight_g("約50グラム") == 50

    def test_with_spaces(self):
        """スペース入り: 重さ 約 50 g"""
        assert extract_weight_g("重さ 約 50 g") == 50

    def test_bare_grams(self):
        """単純形式: 50g"""
        assert extract_weight_g("50g") == 50

    def test_kg_format(self):
        """kg形式: 0.5kg → 500"""
        assert extract_weight_g("0.5kg") == 500

    def test_kg_with_approx(self):
        """約kg形式: 約0.3kg → 300"""
        assert extract_weight_g("約0.3kg") == 300

    def test_full_width_g(self):
        """全角ｇ: 50ｇ"""
        assert extract_weight_g("50ｇ") == 50

    def test_embedded_in_spec(self):
        """スペック文中: サイズ：約90×35cm / 重さ：約50g / 素材：綿100%"""
        text = "サイズ：約90×35cm / 重さ：約50g / 素材：綿100%"
        assert extract_weight_g(text) == 50

    def test_decimal_grams(self):
        """小数グラム: 重量:150.5g → 150"""
        assert extract_weight_g("重量:150.5g") == 150

    def test_none_input(self):
        """None入力"""
        assert extract_weight_g(None) is None

    def test_empty_string(self):
        """空文字列"""
        assert extract_weight_g("") is None

    def test_no_weight_info(self):
        """重量情報なし"""
        assert extract_weight_g("サイズ：約90×35cm / 素材：綿100%") is None

    def test_integer_kg(self):
        """整数kg: 1kg → 1000"""
        assert extract_weight_g("1kg") == 1000

    def test_large_weight(self):
        """大きい重量: 重さ：約300g"""
        assert extract_weight_g("重さ：約300g") == 300


class TestDetectCategory:
    """カテゴリ推定テスト"""

    def test_tenugui(self):
        assert _detect_category("和柄手ぬぐい 富士山") == "tenugui"

    def test_furoshiki(self):
        assert _detect_category("風呂敷 大判 70cm") == "furoshiki"

    def test_knife(self):
        assert _detect_category("三徳包丁 ステンレス") == "knife"

    def test_incense(self):
        assert _detect_category("白檀のお香 スティック") == "incense"

    def test_washi(self):
        assert _detect_category("千代紙セット 20枚入") == "washi"

    def test_unknown(self):
        """該当カテゴリなし"""
        assert _detect_category("ランダム商品") is None

    def test_description_fallback(self):
        """商品名に情報がなくても説明文で判定"""
        assert _detect_category("日本伝統工芸品", "手拭いとしても使える布") == "tenugui"


class TestMapToDb:
    """NETSEAフィールド → DBカラムのマッピングテスト"""

    def test_basic_mapping(self):
        """基本的なマッピング"""
        client = NetseaClient.__new__(NetseaClient)  # __init__をスキップ

        netsea_item = {
            "item_id": "12345",
            "item_name": "和柄手ぬぐい 桜",
            "description": "綿100%の手ぬぐい",
            "spec_size": "サイズ：約90×35cm / 重さ：約50g",
            "images": [
                {"url": "https://example.com/img1.jpg"},
                {"url": "https://example.com/img2.jpg"},
            ],
            "sets": [
                {"price": 600},
                {"price": 500},
                {"price": 700},
            ],
        }

        result = client.map_to_db(netsea_item)

        assert result["supplier"] == "netsea"
        assert result["supplier_product_id"] == "12345"
        assert result["name_ja"] == "和柄手ぬぐい 桜"
        assert result["category"] == "tenugui"
        assert result["wholesale_price_jpy"] == 500  # 最安SKU
        assert result["weight_g"] == 50
        assert len(result["image_urls"]) == 2

    def test_min_price_from_sets(self):
        """sets内の最安価格を卸値とする"""
        client = NetseaClient.__new__(NetseaClient)

        netsea_item = {
            "item_id": "99999",
            "item_name": "テスト商品",
            "sets": [
                {"price": 1500},
                {"price": 800},
                {"price": 1200},
            ],
        }

        result = client.map_to_db(netsea_item)
        assert result["wholesale_price_jpy"] == 800

    def test_missing_weight(self):
        """重量情報なし → weight_g = None"""
        client = NetseaClient.__new__(NetseaClient)

        netsea_item = {
            "item_id": "11111",
            "item_name": "テスト",
            "spec_size": "サイズ：約90×35cm",
        }

        result = client.map_to_db(netsea_item)
        assert result["weight_g"] is None
