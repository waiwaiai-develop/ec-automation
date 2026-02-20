"""BANフィルターテスト

安全商品/VeRO商品/包丁制限/禁止語/複合リスクをテスト。
実DBを使用（テスト用tmpファイル）。
"""

import pytest

from src.ai.ban_filter import check_ban_risk, check_prohibited_keywords
from src.db.database import Database


@pytest.fixture
def db(tmp_path):
    """テスト用DB（シードデータ込み）"""
    database = Database(str(tmp_path / "test.db"))
    database.init_tables()
    database.seed_data()
    return database


# --- check_prohibited_keywords ---

class TestProhibitedKeywords:
    """禁止語検出テスト"""

    def test_clean_text(self):
        """安全なテキスト → 空リスト"""
        result = check_prohibited_keywords(
            "Beautiful Japanese tenugui cotton towel, Made in Japan"
        )
        assert result == []

    def test_dropship_detected(self):
        """'dropship' → 検出"""
        result = check_prohibited_keywords("We dropship from Japan")
        assert len(result) == 1
        assert result[0]["keyword"] == "dropship"
        assert result[0]["severity"] == "high"

    def test_replica_detected(self):
        """'replica' → 検出"""
        result = check_prohibited_keywords("High quality replica knife")
        assert len(result) == 1
        assert result[0]["keyword"] == "replica"

    def test_multiple_keywords(self):
        """複数禁止語 → 全て検出"""
        result = check_prohibited_keywords(
            "Wholesale dropshipping fake items"
        )
        assert len(result) >= 3  # wholesale, dropshipping, fake

    def test_case_insensitive(self):
        """大文字小文字を無視"""
        result = check_prohibited_keywords("DROPSHIP from warehouse")
        assert len(result) >= 1

    def test_empty_text(self):
        """空テキスト → 空リスト"""
        assert check_prohibited_keywords("") == []
        assert check_prohibited_keywords(None) == []


# --- check_ban_risk ---

class TestBanRisk:
    """BANリスク総合判定テスト"""

    def test_safe_tenugui(self, db):
        """安全な手ぬぐい → safe=True, risk=none"""
        product = {
            "name_ja": "日本製 手ぬぐい 富士山柄",
            "name_en": "Japanese Cotton Tenugui Towel Mt Fuji",
            "category": "tenugui",
            "wholesale_price_jpy": 400,
            "weight_g": 50,
        }
        result = check_ban_risk(product, db, sale_price_usd=15.00)
        assert result["safe"] is True
        assert result["risk_level"] == "none"
        assert result["issues"] == []
        assert result["excluded_countries"] == []

    def test_vero_brand_detected(self, db):
        """VeROブランド（Shun）→ safe=False, risk=high"""
        product = {
            "name_ja": "Shun Classic 包丁 三徳",
            "category": "knife",
            "wholesale_price_jpy": 8000,
        }
        result = check_ban_risk(product, db)
        assert result["safe"] is False
        assert result["risk_level"] == "high"
        assert any(
            i["type"] == "brand_blacklist" for i in result["issues"]
        )

    def test_knife_country_restrictions(self, db):
        """包丁 → GB/IE配送禁止"""
        product = {
            "name_ja": "関孫六 三徳包丁",
            "category": "knife",
            "wholesale_price_jpy": 3000,
            "weight_g": 300,
        }
        result = check_ban_risk(product, db)
        assert "GB" in result["excluded_countries"]
        assert "IE" in result["excluded_countries"]
        assert any(
            i["type"] == "country_restriction" for i in result["issues"]
        )

    def test_low_margin_warning(self, db):
        """利益率 < 25% → 利益率警告"""
        product = {
            "name_ja": "手ぬぐい 高級品",
            "category": "tenugui",
            "wholesale_price_jpy": 1500,
            "weight_g": 50,
        }
        result = check_ban_risk(product, db, sale_price_usd=15.00)
        assert any(
            i["type"] == "low_margin" for i in result["issues"]
        )
        # low_marginはmedium severity → safe=False
        assert result["risk_level"] == "medium"

    def test_combined_risks(self, db):
        """複合リスク: VeROブランド + 国制限 + 禁止語"""
        product = {
            "name_ja": "Shun replica 包丁",
            "category": "knife",
            "wholesale_price_jpy": 5000,
        }
        result = check_ban_risk(product, db)
        assert result["safe"] is False
        assert result["risk_level"] == "high"
        # ブランド + 国制限 + 禁止語の3種類
        issue_types = {i["type"] for i in result["issues"]}
        assert "brand_blacklist" in issue_types
        assert "country_restriction" in issue_types
        assert "prohibited_keyword" in issue_types

    def test_no_category(self, db):
        """カテゴリなし → 国制限チェックなし、他は通常動作"""
        product = {
            "name_ja": "テスト商品",
        }
        result = check_ban_risk(product, db)
        assert result["excluded_countries"] == []

    def test_profit_check_skipped_without_price(self, db):
        """sale_price未指定 → 利益率チェックスキップ"""
        product = {
            "name_ja": "手ぬぐい",
            "category": "tenugui",
            "wholesale_price_jpy": 1500,
            "weight_g": 50,
        }
        result = check_ban_risk(product, db)  # sale_price_usd指定なし
        assert not any(
            i["type"] == "low_margin" for i in result["issues"]
        )
