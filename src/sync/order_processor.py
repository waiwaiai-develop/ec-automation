"""注文処理エンジン

注文検出 → DB記録 → 利益計算 → LINE通知。
5分間隔のcronで実行。
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from src.ai.profit_calculator import calculate_profit
from src.db.database import Database
from src.notifications.line import LineNotifier
from src.platforms.base_client import BasePlatformClient

logger = logging.getLogger(__name__)


class OrderProcessor:
    """注文処理エンジン"""

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

    def process(self, platform: Optional[str] = None,
                since: Optional[datetime] = None) -> Dict[str, Any]:
        """注文を処理

        Args:
            platform: 特定プラットフォームのみ（Noneなら全て）
            since: この日時以降の注文を取得

        Returns:
            {
                "new_orders": int,
                "total_revenue_usd": float,
                "total_profit_usd": float,
                "errors": list,
            }
        """
        # 同期ログ開始
        sync_id = self.db.create_sync_log(
            "orders", platform or "all"
        )

        results = {
            "new_orders": 0,
            "total_revenue_usd": 0.0,
            "total_profit_usd": 0.0,
            "errors": [],
        }

        platforms_to_check = (
            {platform: self.clients[platform]}
            if platform and platform in self.clients
            else self.clients
        )

        try:
            for plat_name, client in platforms_to_check.items():
                try:
                    orders = client.get_orders(since=since)
                    for order_data in orders:
                        self._process_single_order(
                            plat_name, order_data, results
                        )
                except Exception as e:
                    error_msg = f"注文取得エラー ({plat_name}): {e}"
                    logger.error(error_msg)
                    results["errors"].append(error_msg)

            # 同期ログ完了
            self.db.complete_sync_log(
                sync_id,
                items_checked=results["new_orders"],
                items_changed=results["new_orders"],
                errors=results["errors"] if results["errors"] else None,
                success=True,
            )

        except Exception as e:
            logger.error(f"注文処理失敗: {e}")
            self.db.complete_sync_log(
                sync_id,
                items_checked=0,
                items_changed=0,
                errors=[str(e)],
                success=False,
            )
            raise

        return results

    def _process_single_order(self, platform: str,
                               order_data: Dict[str, Any],
                               results: Dict[str, Any]) -> None:
        """個別注文を処理"""
        platform_order_id = order_data["platform_order_id"]

        # 重複チェック
        existing = self.db.get_order_by_platform_id(
            platform, platform_order_id
        )
        if existing:
            return  # 既に処理済み

        # リスティングとの紐付け
        listing = None
        product = None
        for item in order_data.get("items", []):
            listing = self.db.get_listing_by_platform_id(
                platform, item["platform_listing_id"]
            )
            if listing:
                product = self.db.get_product(listing["product_id"])
                break

        # 利益計算
        profit_usd = 0.0
        wholesale_cost_jpy = 0
        if product:
            wholesale_cost_jpy = product.get("wholesale_price_jpy", 0)
            profit_result = calculate_profit(
                wholesale_jpy=wholesale_cost_jpy,
                sale_usd=order_data["sale_price_usd"],
                weight_g=product.get("weight_g"),
                platform=platform,
            )
            profit_usd = profit_result["profit_usd"]

        # DB記録
        order_record = {
            "listing_id": listing["id"] if listing else None,
            "platform": platform,
            "platform_order_id": platform_order_id,
            "buyer_country": order_data.get("buyer_country"),
            "sale_price_usd": order_data["sale_price_usd"],
            "platform_fees_usd": order_data.get("platform_fees_usd", 0),
            "shipping_cost_usd": order_data.get("shipping_cost_usd", 0),
            "wholesale_cost_jpy": wholesale_cost_jpy,
            "profit_usd": profit_usd,
            "status": "pending",
            "ordered_at": order_data.get("ordered_at"),
        }
        self.db.create_order(order_record)

        # リスティングの売上カウント更新
        if listing:
            current_sales = listing.get("sales", 0)
            self.db.update_listing(listing["id"], {
                "sales": current_sales + 1,
            })

        results["new_orders"] += 1
        results["total_revenue_usd"] += order_data["sale_price_usd"]
        results["total_profit_usd"] += profit_usd

        # LINE通知
        if self.notifier:
            try:
                product_name = ""
                if product:
                    product_name = product.get("name_ja", "")
                elif order_data.get("items"):
                    product_name = order_data["items"][0].get("title", "")

                self.notifier.notify_order({
                    "platform": platform,
                    "platform_order_id": platform_order_id,
                    "sale_price_usd": order_data["sale_price_usd"],
                    "profit_usd": profit_usd,
                    "buyer_country": order_data.get("buyer_country", "不明"),
                    "product_name": product_name,
                })
            except Exception as e:
                logger.error(f"注文通知失敗: {e}")

        logger.info(
            f"新規注文: {platform_order_id} ({platform}) "
            f"${order_data['sale_price_usd']:.2f}"
        )
