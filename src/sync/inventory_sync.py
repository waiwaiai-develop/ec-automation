"""在庫同期エンジン

NETSEA在庫チェック → リスティング同期（品切れ→非公開、復活→再公開）。
ステートレス設計: 15分間隔のcronで実行。
プラットフォーム横断で動作。
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from src.db.database import Database
from src.notifications.line import LineNotifier
from src.platforms.base_client import BasePlatformClient

logger = logging.getLogger(__name__)


class InventorySyncEngine:
    """在庫同期エンジン"""

    def __init__(
        self,
        database: Database,
        clients: Dict[str, BasePlatformClient],
        notifier: Optional[LineNotifier] = None,
    ):
        """
        Args:
            database: DBインスタンス
            clients: {"ebay": EbayClient, "etsy": EtsyClient} のマップ
            notifier: LINE通知（Noneなら通知スキップ）
        """
        self.db = database
        self.clients = clients
        self.notifier = notifier

    def sync(self, platform: Optional[str] = None) -> Dict[str, Any]:
        """在庫同期を実行

        Args:
            platform: 特定プラットフォームのみ同期（Noneなら全て）

        Returns:
            {
                "items_checked": int,
                "items_changed": int,
                "deactivated": list,
                "reactivated": list,
                "errors": list,
            }
        """
        # 同期ログ開始
        sync_id = self.db.create_sync_log(
            "inventory", platform or "all"
        )

        results = {
            "items_checked": 0,
            "items_changed": 0,
            "deactivated": [],
            "reactivated": [],
            "errors": [],
        }

        try:
            # アクティブなリスティングを商品情報付きで取得
            listings = self.db.get_active_listings_with_products(platform)
            results["items_checked"] = len(listings)

            # 品切れ商品の非公開化
            for listing in listings:
                try:
                    self._check_and_sync(listing, results)
                except Exception as e:
                    error_msg = f"同期エラー (listing={listing['id']}): {e}"
                    logger.error(error_msg)
                    results["errors"].append(error_msg)

            # 非公開リスティングの再公開チェック
            paused = self.db.get_listings(status="paused", platform=platform)
            for listing in paused:
                try:
                    self._check_reactivation(listing, results)
                except Exception as e:
                    error_msg = f"再公開チェックエラー (listing={listing['id']}): {e}"
                    logger.error(error_msg)
                    results["errors"].append(error_msg)

            # 同期ログ完了
            self.db.complete_sync_log(
                sync_id,
                items_checked=results["items_checked"],
                items_changed=results["items_changed"],
                errors=results["errors"] if results["errors"] else None,
                success=True,
            )

            # LINE通知
            self._notify_results(results)

        except Exception as e:
            logger.error(f"在庫同期失敗: {e}")
            self.db.complete_sync_log(
                sync_id,
                items_checked=results["items_checked"],
                items_changed=results["items_changed"],
                errors=[str(e)],
                success=False,
            )
            raise

        return results

    def _check_and_sync(self, listing: Dict[str, Any],
                        results: Dict[str, Any]) -> None:
        """個別リスティングの在庫チェックと同期"""
        stock_status = listing.get("stock_status", "in_stock")
        platform = listing["platform"]
        platform_listing_id = listing.get("platform_listing_id")

        if not platform_listing_id:
            return

        client = self.clients.get(platform)
        if not client:
            return

        # 品切れの場合 → 非公開化
        if stock_status in ("out_of_stock", "discontinued"):
            client.deactivate_listing(platform_listing_id)
            self.db.update_listing(listing["id"], {"status": "paused"})
            results["items_changed"] += 1
            results["deactivated"].append({
                "product_name": listing.get("name_ja", "不明"),
                "platform": platform,
                "action": "deactivated",
                "listing_id": listing["id"],
            })
            logger.info(
                f"非公開化: {listing.get('name_ja', '')} ({platform})"
            )

    def _check_reactivation(self, listing: Dict[str, Any],
                            results: Dict[str, Any]) -> None:
        """非公開リスティングの再公開チェック"""
        product_id = listing.get("product_id")
        if not product_id:
            return

        product = self.db.get_product(product_id)
        if not product:
            return

        platform = listing["platform"]
        platform_listing_id = listing.get("platform_listing_id")

        if not platform_listing_id:
            return

        client = self.clients.get(platform)
        if not client:
            return

        # 在庫復活 → 再公開
        if product.get("stock_status") == "in_stock":
            client.activate_listing(platform_listing_id)
            self.db.update_listing(listing["id"], {"status": "active"})
            results["items_changed"] += 1
            results["reactivated"].append({
                "product_name": product.get("name_ja", "不明"),
                "platform": platform,
                "action": "reactivated",
                "listing_id": listing["id"],
            })
            logger.info(
                f"再公開: {product.get('name_ja', '')} ({platform})"
            )

    def _notify_results(self, results: Dict[str, Any]) -> None:
        """同期結果をLINE通知"""
        if not self.notifier:
            return

        # 変更があった場合のみ通知
        alerts = results["deactivated"] + results["reactivated"]
        if alerts:
            try:
                self.notifier.notify_stock_alert(alerts)
            except Exception as e:
                logger.error(f"LINE通知失敗: {e}")

        # エラーがあった場合もエラー通知
        if results["errors"]:
            try:
                self.notifier.notify_error(
                    "INVENTORY_SYNC",
                    f"エラー{len(results['errors'])}件: {results['errors'][0]}"
                )
            except Exception as e:
                logger.error(f"エラー通知失敗: {e}")
