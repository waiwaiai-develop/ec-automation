"""LINE Notify 通知モジュール

注文通知・在庫アラート・日次サマリー・エラー通知の4種を提供。
LINE Notify API を直接呼び出す（ライブラリ不要）。
"""

import os
from datetime import datetime
from typing import Any, Dict, List, Optional

import httpx

LINE_NOTIFY_URL = "https://notify-api.line.me/api/notify"


class LineNotifier:
    """LINE Notify 通知送信"""

    def __init__(self, token: Optional[str] = None):
        self.token = token or os.environ.get("LINE_NOTIFY_TOKEN", "")
        if not self.token:
            raise ValueError(
                "LINE_NOTIFY_TOKEN が設定されていません。"
                "config/.env に LINE_NOTIFY_TOKEN を追加してください。"
            )

    def _send(self, message: str) -> Dict[str, Any]:
        """LINE Notify APIにメッセージ送信

        Args:
            message: 送信メッセージ（最大1000文字）

        Returns:
            {"success": bool, "status": int, "message": str}
        """
        # 1000文字制限
        if len(message) > 1000:
            message = message[:997] + "..."

        response = httpx.post(
            LINE_NOTIFY_URL,
            headers={"Authorization": f"Bearer {self.token}"},
            data={"message": message},
            timeout=10,
        )

        return {
            "success": response.status_code == 200,
            "status": response.status_code,
            "message": response.text,
        }

    def notify_order(self, order: Dict[str, Any]) -> Dict[str, Any]:
        """注文通知

        Args:
            order: 注文データ（platform, platform_order_id, sale_price_usd,
                   buyer_country, product_name等）
        """
        platform = order.get("platform", "不明")
        order_id = order.get("platform_order_id", "N/A")
        price = order.get("sale_price_usd", 0)
        country = order.get("buyer_country", "不明")
        product = order.get("product_name", "商品名不明")
        profit = order.get("profit_usd", 0)

        message = (
            f"\n{'='*20}"
            f"\n[新規注文] {platform.upper()}"
            f"\n注文ID: {order_id}"
            f"\n商品: {product[:30]}"
            f"\n売上: ${price:.2f}"
            f"\n利益: ${profit:.2f}"
            f"\n配送先: {country}"
            f"\n{'='*20}"
        )

        return self._send(message)

    def notify_stock_alert(self, alerts: List[Dict[str, Any]]) -> Dict[str, Any]:
        """在庫アラート（品切れ/復活）

        Args:
            alerts: [{"product_name": str, "action": "deactivated"/"reactivated",
                      "platform": str}]
        """
        if not alerts:
            return {"success": True, "status": 200, "message": "通知なし"}

        lines = [f"\n[在庫同期] {len(alerts)}件の変更"]

        for alert in alerts[:10]:  # 最大10件表示
            action = alert.get("action", "unknown")
            name = alert.get("product_name", "不明")[:25]
            platform = alert.get("platform", "不明")
            icon = "x" if action == "deactivated" else "o"
            lines.append(f"[{icon}] {name} ({platform})")

        if len(alerts) > 10:
            lines.append(f"...他{len(alerts) - 10}件")

        return self._send("\n".join(lines))

    def notify_daily_summary(self, summary: Dict[str, Any]) -> Dict[str, Any]:
        """日次サマリー通知

        Args:
            summary: {
                "date": str,
                "orders_count": int,
                "revenue_usd": float,
                "profit_usd": float,
                "active_listings": int,
                "stock_changes": int,
            }
        """
        date = summary.get("date", datetime.now().strftime("%Y-%m-%d"))
        orders = summary.get("orders_count", 0)
        revenue = summary.get("revenue_usd", 0)
        profit = summary.get("profit_usd", 0)
        listings = summary.get("active_listings", 0)
        changes = summary.get("stock_changes", 0)

        message = (
            f"\n{'='*20}"
            f"\n[日次レポート] {date}"
            f"\n注文数: {orders}件"
            f"\n売上: ${revenue:.2f}"
            f"\n利益: ${profit:.2f}"
            f"\n出品数: {listings}件"
            f"\n在庫変動: {changes}件"
            f"\n{'='*20}"
        )

        return self._send(message)

    def notify_error(self, error_type: str, detail: str) -> Dict[str, Any]:
        """エラー通知

        Args:
            error_type: エラー種別（例: "API_ERROR", "SYNC_FAILURE"）
            detail: エラー詳細
        """
        message = (
            f"\n[ERROR] {error_type}"
            f"\n{detail[:500]}"
            f"\n時刻: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )

        return self._send(message)
