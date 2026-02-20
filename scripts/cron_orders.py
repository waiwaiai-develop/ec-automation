"""cron用 注文処理エントリポイント

5分間隔で実行。

crontab設定例:
    */5 * * * * cd /path/to/ec-automation && python scripts/cron_orders.py >> logs/orders.log 2>&1
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
logger = logging.getLogger("cron_orders")


def main():
    """注文処理を実行"""
    from src.db.database import Database
    from src.notifications.line import LineNotifier
    from src.platforms.ebay import EbayClient
    from src.platforms.etsy import EtsyClient
    from src.sync.order_processor import OrderProcessor

    logger.info("注文処理開始")
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

    # 注文処理実行
    processor = OrderProcessor(database, clients, notifier)

    try:
        results = processor.process()
        elapsed = (datetime.now() - start).total_seconds()
        logger.info(
            f"注文処理完了: "
            f"新規注文={results['new_orders']}件, "
            f"売上=${results['total_revenue_usd']:.2f}, "
            f"利益=${results['total_profit_usd']:.2f}, "
            f"エラー={len(results['errors'])}件, "
            f"所要時間={elapsed:.1f}秒"
        )
    except Exception as e:
        logger.error(f"注文処理失敗: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
