"""cron用 在庫同期エントリポイント

15分間隔で実行。

crontab設定例:
    */15 * * * * cd /path/to/ec-automation && python scripts/cron_sync.py >> logs/sync.log 2>&1
"""

import logging
import sys
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

# プロジェクト設定
_project_root = Path(__file__).parent.parent
_env_path = _project_root / "config" / ".env"
if _env_path.exists():
    load_dotenv(_env_path)

sys.path.insert(0, str(_project_root))

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("cron_sync")


def main():
    """在庫同期を実行"""
    from src.db.database import Database
    from src.notifications.line import LineNotifier
    from src.platforms.ebay import EbayClient
    from src.platforms.etsy import EtsyClient
    from src.sync.inventory_sync import InventorySyncEngine

    logger.info("在庫同期開始")
    start = datetime.now()

    database = Database()

    # プラットフォームクライアント初期化
    clients = {}
    try:
        clients["ebay"] = EbayClient(sandbox=False)
    except Exception as e:
        logger.warning(f"eBayクライアント初期化スキップ: {e}")

    try:
        clients["etsy"] = EtsyClient()
    except Exception as e:
        logger.warning(f"Etsyクライアント初期化スキップ: {e}")

    if not clients:
        logger.error("利用可能なプラットフォームがありません。")
        sys.exit(1)

    # 通知
    notifier = None
    try:
        notifier = LineNotifier()
    except ValueError:
        logger.warning("LINE Notify未設定。通知なしで実行。")

    # 同期実行
    engine = InventorySyncEngine(database, clients, notifier)

    try:
        results = engine.sync()
        elapsed = (datetime.now() - start).total_seconds()
        logger.info(
            f"在庫同期完了: "
            f"チェック={results['items_checked']}件, "
            f"変更={results['items_changed']}件, "
            f"エラー={len(results['errors'])}件, "
            f"所要時間={elapsed:.1f}秒"
        )
    except Exception as e:
        logger.error(f"在庫同期失敗: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
