"""データベーステスト

- スキーマ冪等性（2回実行してもエラーなし）
- upsert動作（新規挿入 + 更新）
- シードデータ
- 統計取得
- ブランドブラックリスト検査
- 配送制限取得
"""

import os
import tempfile

import pytest

from src.db.database import Database


@pytest.fixture
def db():
    """テスト用の一時DBを作成"""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    database = Database(db_path=db_path)
    database.init_tables()

    yield database

    # クリーンアップ
    os.unlink(db_path)
    journal = db_path + "-journal"
    if os.path.exists(journal):
        os.unlink(journal)
    wal = db_path + "-wal"
    if os.path.exists(wal):
        os.unlink(wal)
    shm = db_path + "-shm"
    if os.path.exists(shm):
        os.unlink(shm)


class TestSchemaIdempotency:
    """スキーマ冪等性テスト"""

    def test_init_tables_twice(self, db):
        """テーブル作成を2回実行してもエラーにならない"""
        tables1 = db.init_tables()
        tables2 = db.init_tables()
        assert tables1 == tables2
        assert len(tables1) == 7  # 7テーブル（sync_log追加）

    def test_seed_data_idempotent(self, db):
        """シードデータを2回投入しても重複しない"""
        counts1 = db.seed_data()
        counts2 = db.seed_data()

        # 2回目は0件追加（既存データ維持）
        assert counts2["country_restrictions"] == 0
        assert counts2["brand_blacklist"] == 0

        # 1回目は実際にデータが入っている
        assert counts1["country_restrictions"] > 0
        assert counts1["brand_blacklist"] > 0


class TestUpsertProduct:
    """商品upsertテスト"""

    def test_insert_new_product(self, db):
        """新規商品の挿入"""
        product = {
            "supplier": "netsea",
            "supplier_product_id": "NETSEA-001",
            "name_ja": "和柄手ぬぐい 富士山",
            "category": "tenugui",
            "wholesale_price_jpy": 500,
            "weight_g": 50,
            "image_urls": ["https://example.com/img1.jpg"],
            "stock_status": "in_stock",
        }
        product_id = db.upsert_product(product)
        assert product_id > 0

        # DBから取得して確認
        products = db.get_products(supplier="netsea")
        assert len(products) == 1
        assert products[0]["name_ja"] == "和柄手ぬぐい 富士山"
        assert products[0]["wholesale_price_jpy"] == 500
        assert products[0]["weight_g"] == 50

    def test_upsert_updates_existing(self, db):
        """既存商品の更新（同じsupplier_product_id）"""
        product_v1 = {
            "supplier": "netsea",
            "supplier_product_id": "NETSEA-002",
            "name_ja": "風呂敷 大判",
            "wholesale_price_jpy": 1000,
        }
        id1 = db.upsert_product(product_v1)

        # 価格変更
        product_v2 = {
            "supplier": "netsea",
            "supplier_product_id": "NETSEA-002",
            "name_ja": "風呂敷 大判（特価）",
            "wholesale_price_jpy": 800,
        }
        id2 = db.upsert_product(product_v2)

        # 同じIDが返る
        assert id1 == id2

        # 更新されている
        products = db.get_products()
        assert len(products) == 1
        assert products[0]["name_ja"] == "風呂敷 大判（特価）"
        assert products[0]["wholesale_price_jpy"] == 800

    def test_weight_null_not_zero(self, db):
        """weight_gが不明の場合はNULL（0ではない）"""
        product = {
            "supplier": "netsea",
            "supplier_product_id": "NETSEA-003",
            "name_ja": "お香セット",
            "weight_g": None,
        }
        db.upsert_product(product)

        products = db.get_products()
        assert products[0]["weight_g"] is None


class TestBrandBlacklist:
    """ブランドブラックリストテスト"""

    def test_detect_blacklisted_brand(self, db):
        """ブラックリストブランドの検出"""
        db.seed_data()

        matches = db.is_brand_blacklisted("Beautiful Shun Kitchen Knife Set")
        assert len(matches) >= 1
        assert any(m["brand_name"] == "Shun" for m in matches)

    def test_no_match_for_safe_text(self, db):
        """安全なテキストはマッチしない"""
        db.seed_data()

        matches = db.is_brand_blacklisted("Japanese Cotton Tenugui Hand Towel")
        assert len(matches) == 0


class TestCountryRestrictions:
    """国別配送制限テスト"""

    def test_knife_restrictions(self, db):
        """包丁のUK/IE配送制限"""
        db.seed_data()

        restrictions = db.get_country_restrictions("knife")
        country_codes = [r["country_code"] for r in restrictions]
        assert "GB" in country_codes
        assert "IE" in country_codes

    def test_tenugui_no_restrictions(self, db):
        """手ぬぐいには配送制限なし"""
        db.seed_data()

        restrictions = db.get_country_restrictions("tenugui")
        assert len(restrictions) == 0


class TestStats:
    """統計テスト"""

    def test_empty_stats(self, db):
        """空DBの統計"""
        stats = db.get_stats()
        assert stats["products"] == 0
        assert stats["listings"] == 0

    def test_stats_after_insert(self, db):
        """商品追加後の統計"""
        db.upsert_product({
            "supplier": "netsea",
            "supplier_product_id": "NETSEA-100",
            "name_ja": "テスト商品",
        })

        stats = db.get_stats()
        assert stats["products"] == 1


class TestMarketData:
    """マーケットデータテスト"""

    def test_insert_market_data(self, db):
        """マーケットデータの挿入"""
        data_id = db.insert_market_data({
            "keyword": "japanese tenugui",
            "total_results": 1500,
            "avg_price_usd": 15.50,
            "min_price_usd": 5.00,
            "max_price_usd": 45.00,
            "median_price_usd": 12.00,
            "avg_shipping_usd": 3.50,
            "sample_size": 50,
        })
        assert data_id > 0

        stats = db.get_stats()
        assert stats["ebay_market_data"] == 1
