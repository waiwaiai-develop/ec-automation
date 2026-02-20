"""注文処理テスト

- 新規注文の検出・DB記録
- 重複注文のスキップ
- 利益計算
"""

import os
import tempfile
from unittest.mock import MagicMock

import pytest

from src.db.database import Database
from src.sync.order_processor import OrderProcessor


@pytest.fixture
def db():
    """テスト用の一時DB"""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    database = Database(db_path=db_path)
    database.init_tables()
    database.seed_data()

    yield database

    os.unlink(db_path)
    for ext in ["-journal", "-wal", "-shm"]:
        path = db_path + ext
        if os.path.exists(path):
            os.unlink(path)


@pytest.fixture
def setup_data(db):
    """テスト用の商品+リスティング"""
    pid = db.upsert_product({
        "supplier": "netsea",
        "supplier_product_id": "ORD-PROD-001",
        "name_ja": "テスト手ぬぐい",
        "category": "tenugui",
        "wholesale_price_jpy": 300,
        "weight_g": 50,
    })

    lid = db.create_listing({
        "product_id": pid,
        "platform": "ebay",
        "platform_listing_id": "EBAY-ITEM-001",
        "title_en": "Japanese Tenugui Hand Towel",
        "price_usd": 15.00,
        "status": "active",
    })

    return {"pid": pid, "lid": lid}


@pytest.fixture
def mock_client(setup_data):
    """注文を返すモッククライアント"""
    client = MagicMock()
    client.platform_name = "ebay"
    client.get_orders.return_value = [
        {
            "platform_order_id": "EBAY-ORD-001",
            "buyer_country": "US",
            "items": [
                {
                    "platform_listing_id": "EBAY-ITEM-001",
                    "quantity": 1,
                    "title": "Japanese Tenugui Hand Towel",
                },
            ],
            "sale_price_usd": 15.00,
            "platform_fees_usd": 2.29,
            "shipping_cost_usd": 3.87,
            "ordered_at": "2026-02-20T10:00:00Z",
            "status": "FULFILLED",
        },
    ]
    return client


class TestOrderProcessor:
    """注文処理テスト"""

    def test_process_new_order(self, db, mock_client, setup_data):
        """新規注文の処理"""
        processor = OrderProcessor(db, {"ebay": mock_client})
        results = processor.process()

        assert results["new_orders"] == 1
        assert results["total_revenue_usd"] == 15.00
        assert results["total_profit_usd"] > 0

    def test_skip_duplicate_order(self, db, mock_client, setup_data):
        """重複注文のスキップ"""
        processor = OrderProcessor(db, {"ebay": mock_client})

        # 1回目
        results1 = processor.process()
        assert results1["new_orders"] == 1

        # 2回目（同じ注文）→ スキップ
        results2 = processor.process()
        assert results2["new_orders"] == 0

    def test_order_saved_to_db(self, db, mock_client, setup_data):
        """注文がDBに保存される"""
        processor = OrderProcessor(db, {"ebay": mock_client})
        processor.process()

        order = db.get_order_by_platform_id("ebay", "EBAY-ORD-001")
        assert order is not None
        assert order["sale_price_usd"] == 15.00
        assert order["buyer_country"] == "US"
        assert order["listing_id"] == setup_data["lid"]

    def test_profit_calculated(self, db, mock_client, setup_data):
        """利益が正しく計算される"""
        processor = OrderProcessor(db, {"ebay": mock_client})
        processor.process()

        order = db.get_order_by_platform_id("ebay", "EBAY-ORD-001")
        assert order["profit_usd"] > 0
        assert order["wholesale_cost_jpy"] == 300

    def test_listing_sales_updated(self, db, mock_client, setup_data):
        """リスティングの売上カウントが更新される"""
        processor = OrderProcessor(db, {"ebay": mock_client})
        processor.process()

        listing = db.get_listing(setup_data["lid"])
        assert listing["sales"] == 1

    def test_notification_sent(self, db, mock_client, setup_data):
        """注文時にLINE通知"""
        mock_notifier = MagicMock()
        processor = OrderProcessor(db, {"ebay": mock_client}, mock_notifier)
        processor.process()

        mock_notifier.notify_order.assert_called_once()
        call_args = mock_notifier.notify_order.call_args[0][0]
        assert call_args["platform"] == "ebay"
        assert call_args["sale_price_usd"] == 15.00

    def test_sync_log_recorded(self, db, mock_client, setup_data):
        """同期ログが記録される"""
        processor = OrderProcessor(db, {"ebay": mock_client})
        processor.process()

        with db.connect() as conn:
            row = conn.execute(
                "SELECT * FROM sync_log WHERE sync_type = 'orders' ORDER BY id DESC LIMIT 1"
            ).fetchone()
            assert row is not None
            assert row["status"] == "completed"
