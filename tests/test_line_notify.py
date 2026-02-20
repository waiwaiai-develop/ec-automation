"""LINE Notify テスト

- メッセージフォーマット検証
- トークン未設定エラー
"""

from unittest.mock import patch, MagicMock

import pytest

from src.notifications.line import LineNotifier, LINE_NOTIFY_URL


class TestLineNotifierInit:
    """初期化テスト"""

    def test_missing_token_raises(self, monkeypatch):
        """トークン未設定 → ValueError"""
        monkeypatch.delenv("LINE_NOTIFY_TOKEN", raising=False)
        with pytest.raises(ValueError, match="LINE_NOTIFY_TOKEN"):
            LineNotifier()

    def test_explicit_token(self):
        """明示的トークン指定"""
        notifier = LineNotifier(token="test_token")
        assert notifier.token == "test_token"

    def test_env_token(self, monkeypatch):
        """環境変数からトークン取得"""
        monkeypatch.setenv("LINE_NOTIFY_TOKEN", "env_token")
        notifier = LineNotifier()
        assert notifier.token == "env_token"


class TestMessageFormatting:
    """メッセージフォーマットテスト"""

    @patch("src.notifications.line.httpx.post")
    def test_order_notification(self, mock_post):
        """注文通知のフォーマット"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "ok"
        mock_post.return_value = mock_response

        notifier = LineNotifier(token="test")
        result = notifier.notify_order({
            "platform": "ebay",
            "platform_order_id": "ORD-001",
            "sale_price_usd": 25.00,
            "profit_usd": 8.50,
            "buyer_country": "US",
            "product_name": "手ぬぐい",
        })

        assert result["success"] is True
        # 送信メッセージの検証
        call_data = mock_post.call_args
        message = call_data.kwargs.get("data", call_data[1].get("data", {}))["message"]
        assert "EBAY" in message
        assert "ORD-001" in message
        assert "$25.00" in message

    @patch("src.notifications.line.httpx.post")
    def test_stock_alert(self, mock_post):
        """在庫アラート"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "ok"
        mock_post.return_value = mock_response

        notifier = LineNotifier(token="test")
        alerts = [
            {"product_name": "手ぬぐい A", "action": "deactivated", "platform": "ebay"},
            {"product_name": "風呂敷 B", "action": "reactivated", "platform": "etsy"},
        ]
        result = notifier.notify_stock_alert(alerts)
        assert result["success"] is True

    @patch("src.notifications.line.httpx.post")
    def test_empty_alert(self, mock_post):
        """空のアラート → 通知スキップ"""
        notifier = LineNotifier(token="test")
        result = notifier.notify_stock_alert([])
        assert result["success"] is True
        mock_post.assert_not_called()

    @patch("src.notifications.line.httpx.post")
    def test_daily_summary(self, mock_post):
        """日次サマリー"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "ok"
        mock_post.return_value = mock_response

        notifier = LineNotifier(token="test")
        result = notifier.notify_daily_summary({
            "date": "2026-02-20",
            "orders_count": 3,
            "revenue_usd": 75.00,
            "profit_usd": 22.50,
            "active_listings": 15,
            "stock_changes": 2,
        })
        assert result["success"] is True

    @patch("src.notifications.line.httpx.post")
    def test_error_notification(self, mock_post):
        """エラー通知"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "ok"
        mock_post.return_value = mock_response

        notifier = LineNotifier(token="test")
        result = notifier.notify_error("API_ERROR", "eBay API returned 500")
        assert result["success"] is True

    @patch("src.notifications.line.httpx.post")
    def test_message_truncation(self, mock_post):
        """1000文字超えメッセージの切り詰め"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "ok"
        mock_post.return_value = mock_response

        notifier = LineNotifier(token="test")
        long_message = "a" * 1500
        notifier._send(long_message)

        call_data = mock_post.call_args
        sent_msg = call_data.kwargs.get("data", call_data[1].get("data", {}))["message"]
        assert len(sent_msg) <= 1000
        assert sent_msg.endswith("...")
