"""商品リサーチ機能テスト

- DBテーブル（research_sessions, research_matches）CRUD
- リサーチサービス層（ヒストグラム、日本セラー検出、スコアリング）
- Webルート・APIエンドポイント
"""

import json
import os
import tempfile

import pytest

from src.db.database import Database
from src.research.research_service import (
    _build_price_histogram,
    _calc_competition_score,
    _calc_demand_score,
    _calc_margin_score,
    _count_japan_sellers,
)


@pytest.fixture
def db():
    """テスト用の一時DBを作成"""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    database = Database(db_path=db_path)
    database.init_tables()

    yield database

    os.unlink(db_path)
    for ext in ["-journal", "-wal", "-shm"]:
        p = db_path + ext
        if os.path.exists(p):
            os.unlink(p)


@pytest.fixture
def app(db):
    """テスト用Flaskアプリ"""
    from src.dashboard.web import create_app
    app = create_app(db_path=db.db_path)
    app.config["TESTING"] = True
    return app


@pytest.fixture
def client(app):
    """テスト用HTTPクライアント"""
    return app.test_client()


# --- DB CRUD テスト ---

class TestResearchSessionCRUD:
    """リサーチセッションCRUD"""

    def test_create_and_get_session(self, db):
        """セッションの作成と取得"""
        session_id = db.create_research_session({
            "keyword": "japanese tenugui",
            "total_results": 1500,
            "avg_price_usd": 15.50,
            "min_price_usd": 5.00,
            "max_price_usd": 45.00,
            "median_price_usd": 12.00,
            "avg_shipping_usd": 3.50,
            "sample_size": 50,
            "japan_seller_count": 3,
            "top_items_json": [{"title": "test", "price": "15.00"}],
            "price_dist_json": [{"range": "$5-$10", "count": 5}],
            "status": "completed",
        })
        assert session_id > 0

        session = db.get_research_session(session_id)
        assert session is not None
        assert session["keyword"] == "japanese tenugui"
        assert session["total_results"] == 1500
        assert session["avg_price_usd"] == 15.50
        assert session["japan_seller_count"] == 3
        assert session["status"] == "completed"

        # JSONカラムをパース
        top_items = json.loads(session["top_items_json"])
        assert len(top_items) == 1
        assert top_items[0]["title"] == "test"

    def test_get_sessions_list(self, db):
        """セッション一覧取得"""
        db.create_research_session({"keyword": "tenugui"})
        db.create_research_session({"keyword": "furoshiki"})
        db.create_research_session({"keyword": "tenugui cloth"})

        # 全件
        sessions = db.get_research_sessions()
        assert len(sessions) == 3

        # キーワード絞り込み
        sessions = db.get_research_sessions(keyword="tenugui")
        assert len(sessions) == 2

    def test_delete_session(self, db):
        """セッション削除（関連マッチングも削除）"""
        session_id = db.create_research_session({"keyword": "test"})
        db.create_research_match({
            "session_id": session_id,
            "netsea_name_ja": "テスト商品",
            "total_score": 5.0,
        })

        # 削除前
        matches = db.get_research_matches(session_id)
        assert len(matches) == 1

        # 削除
        result = db.delete_research_session(session_id)
        assert result is True

        # 削除後
        assert db.get_research_session(session_id) is None
        assert len(db.get_research_matches(session_id)) == 0


class TestResearchMatchCRUD:
    """リサーチマッチングCRUD"""

    def test_create_and_get_matches(self, db):
        """マッチングの作成と取得"""
        session_id = db.create_research_session({"keyword": "test"})

        db.create_research_match({
            "session_id": session_id,
            "netsea_product_id": "P001",
            "netsea_name_ja": "和柄手ぬぐい",
            "wholesale_price_jpy": 500,
            "suggested_price_usd": 15.00,
            "profit_usd": 5.50,
            "profit_margin": 0.37,
            "profitable": True,
            "demand_score": 3.2,
            "margin_score": 7.4,
            "competition_score": 2.5,
            "total_score": 9.47,
            "direct_send_flag": "Y",
            "image_copy_flag": "Y",
            "deal_net_shop_flag": "Y",
        })
        db.create_research_match({
            "session_id": session_id,
            "netsea_product_id": "P002",
            "netsea_name_ja": "風呂敷",
            "total_score": 3.0,
        })

        matches = db.get_research_matches(session_id)
        assert len(matches) == 2
        # スコア降順
        assert matches[0]["total_score"] > matches[1]["total_score"]
        assert matches[0]["netsea_name_ja"] == "和柄手ぬぐい"


# --- サービス層テスト ---

class TestPriceHistogram:
    """価格分布ヒストグラムテスト"""

    def test_empty_prices(self):
        """空の価格リスト"""
        result = _build_price_histogram([])
        assert result == []

    def test_single_price(self):
        """単一価格"""
        result = _build_price_histogram([10.0])
        assert len(result) == 1
        assert result[0]["count"] == 1

    def test_multiple_prices(self):
        """複数価格のヒストグラム"""
        prices = [5, 10, 12, 15, 20, 25, 30, 40]
        result = _build_price_histogram(prices, buckets=4)
        assert len(result) > 0
        # 全価格がカウントに含まれる
        total = sum(b["count"] for b in result)
        assert total == len(prices)


class TestJapanSellerDetection:
    """日本セラー検出テスト"""

    def test_detect_japan_sellers(self):
        """日本セラーキーワードの検出"""
        items = [
            {"seller": "tokyo_store"},
            {"seller": "us_seller_123"},
            {"seller": "japan-crafts"},
            {"seller": "somestore"},
        ]
        count = _count_japan_sellers(items)
        assert count == 2

    def test_no_japan_sellers(self):
        """日本セラーなし"""
        items = [
            {"seller": "us_store"},
            {"seller": "uk_crafts"},
        ]
        count = _count_japan_sellers(items)
        assert count == 0


class TestScoring:
    """スコアリングテスト"""

    def test_demand_score(self):
        """需要スコア"""
        assert _calc_demand_score(0) == 0.0
        assert _calc_demand_score(100) > 0
        assert _calc_demand_score(10000) > _calc_demand_score(100)

    def test_margin_score(self):
        """利益率スコア"""
        assert _calc_margin_score(0.0) == 0.0
        assert _calc_margin_score(0.25) == 5.0
        assert _calc_margin_score(0.50) == 10.0

    def test_competition_score(self):
        """競合スコア"""
        assert _calc_competition_score(0) == 0.1
        assert _calc_competition_score(1000) > _calc_competition_score(10)


# --- Webルート・APIテスト ---

class TestResearchPages:
    """リサーチページルート"""

    def test_research_page(self, client):
        """リサーチ一覧ページ"""
        resp = client.get("/research")
        assert resp.status_code == 200
        assert "需要分析" in resp.data.decode("utf-8")

    def test_research_detail_404(self, client):
        """存在しないリサーチ詳細"""
        resp = client.get("/research/99999")
        assert resp.status_code == 404

    def test_research_detail_page(self, client, db):
        """リサーチ詳細ページ"""
        session_id = db.create_research_session({
            "keyword": "test keyword",
            "total_results": 100,
            "avg_price_usd": 15.0,
            "median_price_usd": 12.0,
            "top_items_json": [],
            "price_dist_json": [],
        })
        resp = client.get("/research/{}".format(session_id))
        assert resp.status_code == 200
        assert "test keyword" in resp.data.decode("utf-8")


class TestResearchAPI:
    """リサーチAPIエンドポイント"""

    def test_history_empty(self, client):
        """空の履歴"""
        resp = client.get("/api/research/history")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["sessions"] == []

    def test_history_with_data(self, client, db):
        """データありの履歴"""
        db.create_research_session({"keyword": "tenugui"})
        db.create_research_session({"keyword": "furoshiki"})

        resp = client.get("/api/research/history")
        data = resp.get_json()
        assert len(data["sessions"]) == 2

    def test_history_keyword_filter(self, client, db):
        """キーワード絞り込み"""
        db.create_research_session({"keyword": "tenugui"})
        db.create_research_session({"keyword": "furoshiki"})

        resp = client.get("/api/research/history?keyword=tenugui")
        data = resp.get_json()
        assert len(data["sessions"]) == 1

    def test_detail_api(self, client, db):
        """リサーチ詳細API"""
        session_id = db.create_research_session({
            "keyword": "test",
            "total_results": 50,
            "top_items_json": json.dumps([{"title": "item1"}]),
            "price_dist_json": json.dumps([{"range": "$5-$10", "count": 3}]),
        })

        resp = client.get("/api/research/{}".format(session_id))
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["session"]["keyword"] == "test"
        assert len(data["top_items"]) == 1
        assert len(data["price_dist"]) == 1

    def test_detail_api_404(self, client):
        """存在しないリサーチ詳細API"""
        resp = client.get("/api/research/99999")
        assert resp.status_code == 404

    def test_analyze_empty_keyword(self, client):
        """空キーワードでのリサーチ"""
        resp = client.post(
            "/api/research/analyze",
            data=json.dumps({"keyword": ""}),
            content_type="application/json",
        )
        assert resp.status_code == 400

    def test_compare_empty_ids(self, client):
        """空IDリストでの比較"""
        resp = client.post(
            "/api/research/compare",
            data=json.dumps({"session_ids": []}),
            content_type="application/json",
        )
        assert resp.status_code == 400

    def test_compare_with_sessions(self, client, db):
        """セッション比較"""
        id1 = db.create_research_session({
            "keyword": "tenugui", "total_results": 100,
        })
        id2 = db.create_research_session({
            "keyword": "furoshiki", "total_results": 200,
        })

        resp = client.post(
            "/api/research/compare",
            data=json.dumps({"session_ids": [id1, id2]}),
            content_type="application/json",
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["total"] == 2

    def test_match_netsea_missing_session(self, client):
        """存在しないセッションへのNETSEAマッチング"""
        resp = client.post(
            "/api/research/99999/match-netsea",
            data=json.dumps({"supplier_ids": "12345"}),
            content_type="application/json",
        )
        assert resp.status_code == 404

    def test_match_netsea_empty_supplier(self, client, db):
        """空サプライヤーIDでのNETSEAマッチング"""
        session_id = db.create_research_session({"keyword": "test"})
        resp = client.post(
            "/api/research/{}/match-netsea".format(session_id),
            data=json.dumps({"supplier_ids": ""}),
            content_type="application/json",
        )
        assert resp.status_code == 400
