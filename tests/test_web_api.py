"""WebダッシュボードAPIエンドポイントのテスト

外部API（NETSEA, eBay, Claude）はモックで代替。
Flaskテストクライアントを使用。
"""

import json
import os
import tempfile

import pytest

from src.db.database import Database
from src.dashboard.web import create_app


@pytest.fixture
def app_and_db():
    """テスト用Flask appとDBを作成"""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    database = Database(db_path=db_path)
    database.init_tables()
    database.seed_data()

    app = create_app(db_path=db_path)
    app.config["TESTING"] = True

    yield app, database

    os.unlink(db_path)
    for ext in ["-journal", "-wal", "-shm"]:
        p = db_path + ext
        if os.path.exists(p):
            os.unlink(p)


@pytest.fixture
def client(app_and_db):
    """Flaskテストクライアント"""
    app, _ = app_and_db
    return app.test_client()


@pytest.fixture
def db(app_and_db):
    """テスト用DB"""
    _, database = app_and_db
    return database


def _insert_sample_product(db, name="テスト手ぬぐい", pid="TEST-001"):
    """テスト用商品を挿入"""
    return db.upsert_product({
        "supplier": "netsea",
        "supplier_product_id": pid,
        "name_ja": name,
        "category": "tenugui",
        "wholesale_price_jpy": 500,
        "weight_g": 50,
        "stock_status": "in_stock",
        "direct_send_flag": "Y",
        "image_copy_flag": "Y",
        "deal_net_shop_flag": "Y",
    })


class TestPageRoutes:
    """ページルートの基本テスト"""

    def test_index_page(self, client):
        resp = client.get("/")
        assert resp.status_code == 200

    def test_products_page(self, client):
        resp = client.get("/products")
        assert resp.status_code == 200

    def test_product_detail_not_found(self, client):
        resp = client.get("/products/99999")
        assert resp.status_code == 404

    def test_product_detail_found(self, client, db):
        pid = _insert_sample_product(db)
        resp = client.get("/products/{}".format(pid))
        assert resp.status_code == 200

    def test_listings_page(self, client):
        resp = client.get("/listings")
        assert resp.status_code == 200

    def test_orders_page(self, client):
        resp = client.get("/orders")
        assert resp.status_code == 200


class TestImportNetseaUrl:
    """NETSEA URL登録テスト"""

    def test_empty_url(self, client):
        resp = client.post("/api/products/import-netsea-url",
                           data=json.dumps({"url": ""}),
                           content_type="application/json")
        assert resp.status_code == 400
        data = resp.get_json()
        assert "error" in data

    def test_invalid_url(self, client):
        resp = client.post("/api/products/import-netsea-url",
                           data=json.dumps({"url": "https://example.com/foo"}),
                           content_type="application/json")
        assert resp.status_code == 400
        data = resp.get_json()
        assert "無効なNETSEA URL" in data["error"]

    def test_valid_url_mock(self, client, db, monkeypatch):
        """正常系: NETSEAクライアントをモックしてURL登録"""
        import src.scraper.netsea as netsea_mod

        # 元のmap_to_dbメソッドへの参照を保持
        real_map_to_db = netsea_mod.NetseaClient.map_to_db

        class MockNetseaClient:
            def __init__(self, token=None):
                pass
            def get_items(self, supplier_ids, **kwargs):
                return [{
                    "product_id": "89526",
                    "product_name": "テスト手ぬぐい",
                    "supplier_id": "79841",
                    "shop_name": "テストショップ",
                    "set": [{"price": 500}],
                    "spec_size": "重さ：約50g",
                    "description": "テスト説明",
                }]
            def map_to_db(self, item):
                return real_map_to_db(self, item)

        monkeypatch.setattr(netsea_mod, "NetseaClient", MockNetseaClient)

        resp = client.post("/api/products/import-netsea-url",
                           data=json.dumps({"url": "https://www.netsea.jp/shop/79841/89526"}),
                           content_type="application/json")

        data = resp.get_json()
        assert resp.status_code == 200
        assert data["success"] is True
        assert data["product_id"] > 0


class TestBulkDelete:
    """一括削除テスト"""

    def test_empty_ids(self, client):
        resp = client.post("/api/products/bulk-delete",
                           data=json.dumps({"product_ids": []}),
                           content_type="application/json")
        assert resp.status_code == 400

    def test_delete_products(self, client, db):
        id1 = _insert_sample_product(db, "商品A", "DEL-001")
        id2 = _insert_sample_product(db, "商品B", "DEL-002")

        resp = client.post("/api/products/bulk-delete",
                           data=json.dumps({"product_ids": [id1, id2]}),
                           content_type="application/json")
        data = resp.get_json()
        assert resp.status_code == 200
        assert data["deleted"] == 2

        # 削除されていることを確認
        assert db.get_product(id1) is None
        assert db.get_product(id2) is None


class TestBulkSetFlags:
    """出品フラグ一括設定テスト"""

    def test_empty_flags(self, client):
        resp = client.post("/api/products/bulk-set-flags",
                           data=json.dumps({"product_ids": [1], "flags": {}}),
                           content_type="application/json")
        assert resp.status_code == 400

    def test_set_flags(self, client, db):
        id1 = _insert_sample_product(db, "商品C", "FLAG-001")

        resp = client.post("/api/products/bulk-set-flags",
                           data=json.dumps({
                               "product_ids": [id1],
                               "flags": {"list_on_ebay": 1}
                           }),
                           content_type="application/json")
        data = resp.get_json()
        assert resp.status_code == 200
        assert data["updated"] == 1

        # フラグが設定されていることを確認
        product = db.get_product(id1)
        assert product["list_on_ebay"] == 1


class TestUpdateProduct:
    """商品更新テスト"""

    def test_update_name_en(self, client, db):
        pid = _insert_sample_product(db, "商品D", "UPD-001")

        resp = client.post("/api/products/{}/update".format(pid),
                           data=json.dumps({"name_en": "Test Tenugui"}),
                           content_type="application/json")
        data = resp.get_json()
        assert resp.status_code == 200
        assert data["success"] is True

        product = db.get_product(pid)
        assert product["name_en"] == "Test Tenugui"

    def test_update_name_ja(self, client, db):
        pid = _insert_sample_product(db, "商品D2", "UPD-JA-001")

        resp = client.post("/api/products/{}/update".format(pid),
                           data=json.dumps({
                               "name_ja": "更新後の商品名",
                               "description_ja": "更新後の説明文"
                           }),
                           content_type="application/json")
        data = resp.get_json()
        assert resp.status_code == 200
        assert data["success"] is True

        product = db.get_product(pid)
        assert product["name_ja"] == "更新後の商品名"
        assert product["description_ja"] == "更新後の説明文"

    def test_update_not_found(self, client):
        resp = client.post("/api/products/99999/update",
                           data=json.dumps({"name_en": "Test"}),
                           content_type="application/json")
        assert resp.status_code == 404

    def test_update_invalid_field(self, client, db):
        pid = _insert_sample_product(db, "商品E", "UPD-002")

        resp = client.post("/api/products/{}/update".format(pid),
                           data=json.dumps({"invalid_field": "xxx"}),
                           content_type="application/json")
        assert resp.status_code == 400


class TestGenerateListing:
    """AI商品説明生成テスト"""

    def test_generate_not_found(self, client):
        resp = client.post("/api/products/99999/generate",
                           data=json.dumps({}),
                           content_type="application/json")
        assert resp.status_code == 404

    def test_generate_mock(self, client, db, monkeypatch):
        """AI生成をモックしてテスト"""
        pid = _insert_sample_product(db, "AI生成テスト", "GEN-001")

        def mock_generate(product, model=None):
            return {
                "title": "Japanese Tenugui Hand Towel",
                "description": "Beautiful hand towel from Japan",
                "tags": ["tenugui", "japanese"],
                "item_specifics": {"Material": "Cotton"},
            }

        import src.ai.description_generator as desc_mod
        monkeypatch.setattr(desc_mod, "generate_full_listing", mock_generate)

        resp = client.post("/api/products/{}/generate".format(pid),
                           data=json.dumps({}),
                           content_type="application/json")
        data = resp.get_json()
        assert resp.status_code == 200
        assert data["title"] == "Japanese Tenugui Hand Towel"
        assert len(data["tags"]) == 2

    def test_generate_ja_mock(self, client, db, monkeypatch):
        """日本語AI生成をモックしてテスト"""
        pid = _insert_sample_product(db, "日本語AI生成テスト", "GEN-JA-001")

        def mock_generate_ja(product, model=None):
            return {
                "title_ja": "職人手作り 和柄手ぬぐい",
                "description_ja": "日本の伝統的な手ぬぐいです。",
            }

        import src.ai.description_generator as desc_mod
        monkeypatch.setattr(desc_mod, "generate_description_ja", mock_generate_ja)

        resp = client.post("/api/products/{}/generate-ja".format(pid),
                           data=json.dumps({}),
                           content_type="application/json")
        data = resp.get_json()
        assert resp.status_code == 200
        assert data["title_ja"] == "職人手作り 和柄手ぬぐい"
        assert "手ぬぐい" in data["description_ja"]

    def test_generate_ja_not_found(self, client):
        resp = client.post("/api/products/99999/generate-ja",
                           data=json.dumps({}),
                           content_type="application/json")
        assert resp.status_code == 404


class TestBanCheck:
    """BANチェックテスト"""

    def test_ban_check_safe(self, client, db):
        pid = _insert_sample_product(db, "安全な手ぬぐい", "BAN-001")

        resp = client.post("/api/products/{}/ban-check".format(pid),
                           data=json.dumps({}),
                           content_type="application/json")
        data = resp.get_json()
        assert resp.status_code == 200
        assert data["passed"] is True

    def test_ban_check_knife(self, client, db):
        """包丁は配送制限あり（BANチェック自体は通過、除外国が設定される）"""
        pid = db.upsert_product({
            "supplier": "netsea",
            "supplier_product_id": "BAN-KNIFE",
            "name_ja": "テスト包丁",
            "category": "knife",
            "wholesale_price_jpy": 3000,
        })

        resp = client.post("/api/products/{}/ban-check".format(pid),
                           data=json.dumps({}),
                           content_type="application/json")
        data = resp.get_json()
        assert resp.status_code == 200
        assert "GB" in data["excluded_countries"]
        assert "IE" in data["excluded_countries"]

    def test_ban_check_not_found(self, client):
        resp = client.post("/api/products/99999/ban-check",
                           data=json.dumps({}),
                           content_type="application/json")
        assert resp.status_code == 404


class TestProfitCalculation:
    """利益計算テスト"""

    def test_profit_calculation(self, client, db):
        pid = _insert_sample_product(db, "利益テスト", "PROFIT-001")

        resp = client.post("/api/products/{}/profit".format(pid),
                           data=json.dumps({"sale_usd": 18.0, "platform": "ebay"}),
                           content_type="application/json")
        data = resp.get_json()
        assert resp.status_code == 200
        assert data["success"] is True
        assert "profit_usd" in data
        assert "profit_margin" in data
        assert isinstance(data["profitable"], bool)

    def test_profit_no_price(self, client, db):
        pid = _insert_sample_product(db, "利益テスト2", "PROFIT-002")

        resp = client.post("/api/products/{}/profit".format(pid),
                           data=json.dumps({"platform": "ebay"}),
                           content_type="application/json")
        assert resp.status_code == 400

    def test_profit_no_wholesale(self, client, db):
        """卸値未設定の場合はエラー"""
        pid = db.upsert_product({
            "supplier": "netsea",
            "supplier_product_id": "PROFIT-NO-PRICE",
            "name_ja": "卸値なし商品",
        })

        resp = client.post("/api/products/{}/profit".format(pid),
                           data=json.dumps({"sale_usd": 18.0}),
                           content_type="application/json")
        assert resp.status_code == 400


class TestDatabaseMethods:
    """Database層の新メソッドテスト"""

    def test_update_product(self, db):
        pid = _insert_sample_product(db, "更新テスト", "DB-UPD-001")
        result = db.update_product(pid, {"name_en": "Updated Name"})
        assert result is True
        product = db.get_product(pid)
        assert product["name_en"] == "Updated Name"

    def test_update_product_invalid_field(self, db):
        pid = _insert_sample_product(db, "更新テスト2", "DB-UPD-002")
        result = db.update_product(pid, {"nonexistent": "value"})
        assert result is False

    def test_delete_products(self, db):
        id1 = _insert_sample_product(db, "削除A", "DB-DEL-001")
        id2 = _insert_sample_product(db, "削除B", "DB-DEL-002")
        deleted = db.delete_products([id1, id2])
        assert deleted == 2
        assert db.get_product(id1) is None

    def test_delete_products_with_listings(self, db):
        """リスティング付き商品の削除"""
        pid = _insert_sample_product(db, "削除+リスティング", "DB-DEL-003")
        db.create_listing({
            "product_id": pid,
            "platform": "ebay",
            "title_en": "Test",
            "status": "draft",
        })
        deleted = db.delete_products([pid])
        assert deleted == 1
        # リスティングも削除されている
        listings = db.get_listings(product_id=pid)
        assert len(listings) == 0

    def test_delete_empty_list(self, db):
        deleted = db.delete_products([])
        assert deleted == 0

    def test_update_product_flags(self, db):
        id1 = _insert_sample_product(db, "フラグA", "DB-FLAG-001")
        id2 = _insert_sample_product(db, "フラグB", "DB-FLAG-002")

        updated = db.update_product_flags(
            [id1, id2], {"list_on_ebay": 1, "list_on_base": 1}
        )
        assert updated == 2

        p1 = db.get_product(id1)
        p2 = db.get_product(id2)
        assert p1["list_on_ebay"] == 1
        assert p1["list_on_base"] == 1
        assert p2["list_on_ebay"] == 1

    def test_update_flags_empty(self, db):
        updated = db.update_product_flags([], {"list_on_ebay": 1})
        assert updated == 0

    def test_update_flags_invalid(self, db):
        id1 = _insert_sample_product(db, "フラグC", "DB-FLAG-003")
        updated = db.update_product_flags([id1], {"invalid_flag": 1})
        assert updated == 0
