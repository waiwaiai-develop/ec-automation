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


class TestGetJsonApis:
    """GET JSON APIテスト"""

    def test_api_dashboard(self, client):
        """GET /api/dashboard — 統計データ取得"""
        resp = client.get("/api/dashboard")
        assert resp.status_code == 200
        data = resp.get_json()
        assert "stats" in data
        assert "daily_summary" in data
        assert "date" in data["daily_summary"]

    def test_api_products_list(self, client, db):
        """GET /api/products — 商品リスト取得"""
        _insert_sample_product(db, "APIテスト商品A", "API-001")
        _insert_sample_product(db, "APIテスト商品B", "API-002")

        resp = client.get("/api/products")
        assert resp.status_code == 200
        data = resp.get_json()
        assert "products" in data
        assert "categories" in data
        assert "total" in data
        assert data["total"] >= 2

    def test_api_products_filter_category(self, client, db):
        """GET /api/products?category= — カテゴリフィルター"""
        _insert_sample_product(db, "手ぬぐいAPI", "API-CAT-001")

        resp = client.get("/api/products?category=tenugui")
        assert resp.status_code == 200
        data = resp.get_json()
        for p in data["products"]:
            assert p["category"] == "tenugui"

    def test_api_products_filter_ds_only(self, client, db):
        """GET /api/products?ds_only=1 — DS対応フィルター"""
        _insert_sample_product(db, "DS対応API", "API-DS-001")

        resp = client.get("/api/products?ds_only=1")
        assert resp.status_code == 200
        data = resp.get_json()
        for p in data["products"]:
            assert p["direct_send_flag"] == "Y"

    def test_api_product_detail(self, client, db):
        """GET /api/products/<id> — 商品詳細取得"""
        pid = _insert_sample_product(db, "詳細APIテスト", "API-DETAIL-001")

        resp = client.get("/api/products/{}".format(pid))
        assert resp.status_code == 200
        data = resp.get_json()
        assert "product" in data
        assert "images" in data
        assert "profit_info" in data
        assert "listings" in data
        assert data["product"]["name_ja"] == "詳細APIテスト"

    def test_api_product_detail_not_found(self, client):
        """GET /api/products/<id> — 存在しない商品"""
        resp = client.get("/api/products/99999")
        assert resp.status_code == 404
        data = resp.get_json()
        assert "error" in data

    def test_api_listings_list(self, client, db):
        """GET /api/listings — リスティング一覧"""
        pid = _insert_sample_product(db, "リスティングAPIテスト", "API-LIST-001")
        db.create_listing({
            "product_id": pid,
            "platform": "ebay",
            "title_en": "Test Listing",
            "status": "active",
            "price_usd": 25.0,
        })

        resp = client.get("/api/listings")
        assert resp.status_code == 200
        data = resp.get_json()
        assert "listings" in data
        assert "total" in data
        assert data["total"] >= 1

    def test_api_listings_filter_platform(self, client, db):
        """GET /api/listings?platform= — プラットフォームフィルター"""
        pid = _insert_sample_product(db, "出品フィルターテスト", "API-LIST-FLT-001")
        db.create_listing({
            "product_id": pid,
            "platform": "ebay",
            "title_en": "eBay Listing",
            "status": "active",
        })

        resp = client.get("/api/listings?platform=ebay")
        assert resp.status_code == 200
        data = resp.get_json()
        for l in data["listings"]:
            assert l["platform"] == "ebay"

    def test_api_orders_list(self, client):
        """GET /api/orders — 注文一覧"""
        resp = client.get("/api/orders")
        assert resp.status_code == 200
        data = resp.get_json()
        assert "orders" in data
        assert "total" in data

    def test_api_spa_fallback(self, client):
        """SPA fallback — /app にアクセスするとHTMLが返る（ビルド済みの場合は200）"""
        resp = client.get("/app")
        # ビルド済みなら200、未ビルドなら404
        assert resp.status_code in (200, 404)
        if resp.status_code == 200:
            assert b"html" in resp.data.lower()

    def test_api_spa_subroute_fallback(self, client):
        """SPA fallback — /app/products など存在しないパスでもindex.htmlを返す"""
        resp = client.get("/app/products")
        # ビルド済みなら200（SPA fallback）、未ビルドなら404
        assert resp.status_code in (200, 404)


class TestSnsApi:
    """SNS投稿APIテスト"""

    def test_sns_posts_empty(self, client):
        """GET /api/sns/posts — 空の一覧"""
        resp = client.get("/api/sns/posts")
        assert resp.status_code == 200
        data = resp.get_json()
        assert "posts" in data
        assert "total" in data
        assert data["total"] == 0

    def test_sns_create_post(self, client):
        """POST /api/sns/posts — 投稿保存"""
        resp = client.post("/api/sns/posts",
                           data=json.dumps({
                               "platform": "twitter",
                               "body": "テスト投稿です",
                               "hashtags": "#test",
                           }),
                           content_type="application/json")
        data = resp.get_json()
        assert resp.status_code == 200
        assert data["success"] is True
        assert data["post"]["platform"] == "twitter"
        assert data["post"]["status"] == "draft"

    def test_sns_create_invalid_platform(self, client):
        """POST /api/sns/posts — 無効なプラットフォーム"""
        resp = client.post("/api/sns/posts",
                           data=json.dumps({
                               "platform": "facebook",
                               "body": "テスト",
                           }),
                           content_type="application/json")
        assert resp.status_code == 400

    def test_sns_create_empty_body(self, client):
        """POST /api/sns/posts — 本文が空"""
        resp = client.post("/api/sns/posts",
                           data=json.dumps({
                               "platform": "twitter",
                               "body": "",
                           }),
                           content_type="application/json")
        assert resp.status_code == 400

    def test_sns_create_exceeds_char_limit(self, client):
        """POST /api/sns/posts — 文字数制限超過"""
        resp = client.post("/api/sns/posts",
                           data=json.dumps({
                               "platform": "twitter",
                               "body": "x" * 281,
                           }),
                           content_type="application/json")
        assert resp.status_code == 400
        data = resp.get_json()
        assert "文字制限" in data["error"]

    def test_sns_create_with_product(self, client, db):
        """POST /api/sns/posts — 商品紐付き"""
        pid = _insert_sample_product(db, "SNSテスト商品", "SNS-001")
        resp = client.post("/api/sns/posts",
                           data=json.dumps({
                               "platform": "instagram",
                               "body": "商品紹介投稿",
                               "product_id": pid,
                           }),
                           content_type="application/json")
        data = resp.get_json()
        assert resp.status_code == 200
        assert data["post"]["product_id"] == pid

    def test_sns_publish(self, client, db):
        """POST /api/sns/posts/<id>/publish — 投稿実行"""
        post_id = db.create_sns_post({
            "platform": "twitter",
            "body": "公開テスト",
            "status": "draft",
        })

        resp = client.post("/api/sns/posts/{}/publish".format(post_id),
                           data=json.dumps({}),
                           content_type="application/json")
        data = resp.get_json()
        assert resp.status_code == 200
        assert data["success"] is True

        # ステータスがpostedに変わっている
        post = db.get_sns_post(post_id)
        assert post["status"] == "posted"
        assert post["posted_at"] is not None

    def test_sns_publish_not_found(self, client):
        """POST /api/sns/posts/<id>/publish — 存在しない投稿"""
        resp = client.post("/api/sns/posts/99999/publish",
                           data=json.dumps({}),
                           content_type="application/json")
        assert resp.status_code == 404

    def test_sns_delete(self, client, db):
        """POST /api/sns/posts/<id>/delete — 投稿削除"""
        post_id = db.create_sns_post({
            "platform": "threads",
            "body": "削除テスト",
            "status": "draft",
        })

        resp = client.post("/api/sns/posts/{}/delete".format(post_id),
                           data=json.dumps({}),
                           content_type="application/json")
        data = resp.get_json()
        assert resp.status_code == 200
        assert data["success"] is True

        # 削除されている
        assert db.get_sns_post(post_id) is None

    def test_sns_delete_not_found(self, client):
        """POST /api/sns/posts/<id>/delete — 存在しない投稿"""
        resp = client.post("/api/sns/posts/99999/delete",
                           data=json.dumps({}),
                           content_type="application/json")
        assert resp.status_code == 404

    def test_sns_generate(self, client, db):
        """POST /api/sns/generate — AI投稿文生成（スタブ）"""
        pid = _insert_sample_product(db, "AI SNSテスト", "SNS-GEN-001")

        resp = client.post("/api/sns/generate",
                           data=json.dumps({
                               "product_id": pid,
                               "platform": "twitter",
                           }),
                           content_type="application/json")
        data = resp.get_json()
        assert resp.status_code == 200
        assert data["success"] is True
        assert len(data["body"]) > 0
        assert len(data["hashtags"]) > 0

    def test_sns_generate_no_product(self, client):
        """POST /api/sns/generate — product_id未指定"""
        resp = client.post("/api/sns/generate",
                           data=json.dumps({"platform": "twitter"}),
                           content_type="application/json")
        assert resp.status_code == 400

    def test_sns_generate_not_found(self, client):
        """POST /api/sns/generate — 存在しない商品"""
        resp = client.post("/api/sns/generate",
                           data=json.dumps({
                               "product_id": 99999,
                               "platform": "twitter",
                           }),
                           content_type="application/json")
        assert resp.status_code == 404

    def test_sns_posts_filter_platform(self, client, db):
        """GET /api/sns/posts?platform= — プラットフォームフィルター"""
        db.create_sns_post({"platform": "twitter", "body": "X投稿"})
        db.create_sns_post({"platform": "instagram", "body": "IG投稿"})

        resp = client.get("/api/sns/posts?platform=twitter")
        assert resp.status_code == 200
        data = resp.get_json()
        for p in data["posts"]:
            assert p["platform"] == "twitter"

    def test_sns_posts_filter_status(self, client, db):
        """GET /api/sns/posts?status= — ステータスフィルター"""
        db.create_sns_post({"platform": "twitter", "body": "下書き", "status": "draft"})
        db.create_sns_post({"platform": "twitter", "body": "投稿済み", "status": "posted"})

        resp = client.get("/api/sns/posts?status=draft")
        assert resp.status_code == 200
        data = resp.get_json()
        for p in data["posts"]:
            assert p["status"] == "draft"

    def test_sns_posts_filter_date_range(self, client, db):
        """GET /api/sns/posts?date_from=&date_to= — 日付範囲フィルター"""
        db.create_sns_post({
            "platform": "twitter", "body": "2月の投稿",
            "status": "scheduled", "scheduled_at": "2026-02-15T10:00:00",
        })
        db.create_sns_post({
            "platform": "instagram", "body": "3月の投稿",
            "status": "scheduled", "scheduled_at": "2026-03-05T10:00:00",
        })

        resp = client.get("/api/sns/posts?date_from=2026-02-01&date_to=2026-03-01")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["total"] >= 1
        for p in data["posts"]:
            assert p["scheduled_at"] >= "2026-02-01"
            assert p["scheduled_at"] < "2026-03-01"

    def test_sns_posts_filter_date_range_empty(self, client, db):
        """GET /api/sns/posts?date_from=&date_to= — 該当なしの日付範囲"""
        db.create_sns_post({
            "platform": "twitter", "body": "範囲外投稿",
            "status": "scheduled", "scheduled_at": "2026-01-10T10:00:00",
        })

        resp = client.get("/api/sns/posts?date_from=2026-06-01&date_to=2026-07-01")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["total"] == 0
