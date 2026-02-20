"""在庫同期テスト

- 品切れ→非公開化
- 在庫復活→再公開
- 同期ログ記録
"""

import os
import tempfile
from unittest.mock import MagicMock

import pytest

from src.db.database import Database
from src.sync.inventory_sync import InventorySyncEngine


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
def mock_client():
    """モッククライアント"""
    client = MagicMock()
    client.platform_name = "ebay"
    client.deactivate_listing.return_value = {"success": True, "status": "paused"}
    client.activate_listing.return_value = {"success": True, "status": "active"}
    return client


@pytest.fixture
def setup_data(db):
    """テスト用の商品+リスティングデータ"""
    # 在庫あり商品
    pid1 = db.upsert_product({
        "supplier": "netsea",
        "supplier_product_id": "SYNC-001",
        "name_ja": "在庫あり手ぬぐい",
        "stock_status": "in_stock",
        "category": "tenugui",
        "wholesale_price_jpy": 500,
    })

    # 品切れ商品
    pid2 = db.upsert_product({
        "supplier": "netsea",
        "supplier_product_id": "SYNC-002",
        "name_ja": "品切れ風呂敷",
        "stock_status": "out_of_stock",
        "category": "furoshiki",
        "wholesale_price_jpy": 1000,
    })

    # アクティブリスティング（品切れ商品）
    lid2 = db.create_listing({
        "product_id": pid2,
        "platform": "ebay",
        "platform_listing_id": "EBAY-LID-002",
        "title_en": "Furoshiki Wrapping Cloth",
        "price_usd": 25.00,
        "status": "active",
    })

    return {"pid1": pid1, "pid2": pid2, "lid2": lid2}


class TestInventorySync:
    """在庫同期テスト"""

    def test_deactivate_out_of_stock(self, db, mock_client, setup_data):
        """品切れ商品のリスティングを非公開化"""
        engine = InventorySyncEngine(db, {"ebay": mock_client})
        results = engine.sync()

        assert results["items_changed"] >= 1
        assert len(results["deactivated"]) >= 1

        # クライアントのdeactivateが呼ばれた
        mock_client.deactivate_listing.assert_called_with("EBAY-LID-002")

        # DBのステータスが更新された
        listing = db.get_listing(setup_data["lid2"])
        assert listing["status"] == "paused"

    def test_reactivate_restocked(self, db, mock_client, setup_data):
        """在庫復活した商品のリスティングを再公開"""
        # まずリスティングをpaused状態にする
        db.update_listing(setup_data["lid2"], {"status": "paused"})

        # 商品の在庫を復活させる
        with db.connect() as conn:
            conn.execute(
                "UPDATE products SET stock_status = 'in_stock' WHERE id = ?",
                (setup_data["pid2"],),
            )

        engine = InventorySyncEngine(db, {"ebay": mock_client})
        results = engine.sync()

        assert len(results["reactivated"]) >= 1
        mock_client.activate_listing.assert_called_with("EBAY-LID-002")

    def test_sync_log_created(self, db, mock_client, setup_data):
        """同期ログが記録される"""
        engine = InventorySyncEngine(db, {"ebay": mock_client})
        engine.sync()

        with db.connect() as conn:
            row = conn.execute(
                "SELECT * FROM sync_log ORDER BY id DESC LIMIT 1"
            ).fetchone()
            assert row is not None
            assert row["sync_type"] == "inventory"
            assert row["status"] == "completed"

    def test_no_changes_when_all_in_stock(self, db, mock_client):
        """全商品在庫あり → 変更なし"""
        engine = InventorySyncEngine(db, {"ebay": mock_client})
        results = engine.sync()

        assert results["items_changed"] == 0

    def test_notification_on_changes(self, db, mock_client, setup_data):
        """変更時にLINE通知"""
        mock_notifier = MagicMock()
        engine = InventorySyncEngine(db, {"ebay": mock_client}, mock_notifier)
        engine.sync()

        mock_notifier.notify_stock_alert.assert_called_once()
