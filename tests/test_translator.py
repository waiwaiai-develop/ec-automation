"""DeepL翻訳モジュールテスト

- クライアント初期化（APIキーバリデーション）
- Free/Pro版URL自動判定
- 単一翻訳・バッチ翻訳のモック
- 商品名一括翻訳
- エッジケース（空文字、None等）
"""

from unittest.mock import MagicMock, patch

import pytest


class TestDeepLInit:
    """初期化テスト"""

    def test_missing_api_key(self):
        """APIキー未設定でValueError"""
        with patch.dict("os.environ", {}, clear=True):
            from src.ai.translator import DeepLTranslator
            with pytest.raises(ValueError, match="DEEPL_API_KEY"):
                DeepLTranslator(api_key="")

    def test_free_url(self):
        """Free版キー（:fx終わり）→Free URL"""
        from src.ai.translator import DeepLTranslator, DEEPL_FREE_URL
        client = DeepLTranslator(api_key="test-key:fx")
        assert client.api_url == DEEPL_FREE_URL

    def test_pro_url(self):
        """Pro版キー→Pro URL"""
        from src.ai.translator import DeepLTranslator, DEEPL_PRO_URL
        client = DeepLTranslator(api_key="test-key-pro")
        assert client.api_url == DEEPL_PRO_URL


class TestTranslate:
    """単一翻訳テスト"""

    def test_empty_text(self):
        """空テキストは空文字を返す"""
        from src.ai.translator import DeepLTranslator
        client = DeepLTranslator(api_key="test:fx")
        assert client.translate("") == ""

    @patch("src.ai.translator.httpx.post")
    def test_basic_translation(self, mock_post):
        """基本的な翻訳"""
        from src.ai.translator import DeepLTranslator

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "translations": [{"text": "Japanese Tenugui Hand Towel"}]
        }
        mock_resp.raise_for_status = MagicMock()
        mock_post.return_value = mock_resp

        client = DeepLTranslator(api_key="test:fx")
        result = client.translate("和柄手ぬぐい")

        assert result == "Japanese Tenugui Hand Towel"
        mock_post.assert_called_once()

    @patch("src.ai.translator.httpx.post")
    def test_auth_error(self, mock_post):
        """認証エラー"""
        from src.ai.translator import DeepLTranslator

        mock_resp = MagicMock()
        mock_resp.status_code = 403
        mock_post.return_value = mock_resp

        client = DeepLTranslator(api_key="invalid:fx")
        with pytest.raises(ValueError, match="認証エラー"):
            client.translate("テスト")

    @patch("src.ai.translator.httpx.post")
    def test_quota_error(self, mock_post):
        """文字数制限超過"""
        from src.ai.translator import DeepLTranslator

        mock_resp = MagicMock()
        mock_resp.status_code = 456
        mock_post.return_value = mock_resp

        client = DeepLTranslator(api_key="test:fx")
        with pytest.raises(ValueError, match="文字数制限"):
            client.translate("テスト")


class TestBatchTranslate:
    """バッチ翻訳テスト"""

    def test_empty_list(self):
        """空リストは空リストを返す"""
        from src.ai.translator import DeepLTranslator
        client = DeepLTranslator(api_key="test:fx")
        assert client.translate_batch([]) == []

    @patch("src.ai.translator.httpx.post")
    def test_batch(self, mock_post):
        """複数テキストの一括翻訳"""
        from src.ai.translator import DeepLTranslator

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "translations": [
                {"text": "Tenugui"},
                {"text": "Furoshiki"},
            ]
        }
        mock_resp.raise_for_status = MagicMock()
        mock_post.return_value = mock_resp

        client = DeepLTranslator(api_key="test:fx")
        result = client.translate_batch(["手ぬぐい", "風呂敷"])

        assert result == ["Tenugui", "Furoshiki"]

    @patch("src.ai.translator.httpx.post")
    def test_batch_with_empty(self, mock_post):
        """空文字を含むバッチ翻訳"""
        from src.ai.translator import DeepLTranslator

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "translations": [{"text": "Tenugui"}]
        }
        mock_resp.raise_for_status = MagicMock()
        mock_post.return_value = mock_resp

        client = DeepLTranslator(api_key="test:fx")
        result = client.translate_batch(["手ぬぐい", "", ""])

        assert len(result) == 3
        assert result[0] == "Tenugui"
        assert result[1] == ""
        assert result[2] == ""


class TestProductNames:
    """商品名一括翻訳テスト"""

    @patch("src.ai.translator.httpx.post")
    def test_translate_product_names(self, mock_post):
        """name_en未設定の商品のみ翻訳"""
        from src.ai.translator import DeepLTranslator

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "translations": [{"text": "Tenugui"}]
        }
        mock_resp.raise_for_status = MagicMock()
        mock_post.return_value = mock_resp

        products = [
            {"name_ja": "手ぬぐい", "name_en": None},
            {"name_ja": "風呂敷", "name_en": "Furoshiki"},  # 既にある
        ]

        client = DeepLTranslator(api_key="test:fx")
        result = client.translate_product_names(products)

        assert result[0]["name_en"] == "Tenugui"
        assert result[1]["name_en"] == "Furoshiki"  # 変更なし

    def test_all_translated(self):
        """全て翻訳済みの場合はAPI呼び出しなし"""
        from src.ai.translator import DeepLTranslator

        products = [
            {"name_ja": "手ぬぐい", "name_en": "Tenugui"},
        ]

        client = DeepLTranslator(api_key="test:fx")
        result = client.translate_product_names(products)
        assert result[0]["name_en"] == "Tenugui"


class TestUsage:
    """使用量取得テスト"""

    @patch("src.ai.translator.httpx.post")
    def test_get_usage(self, mock_post):
        """使用量取得"""
        from src.ai.translator import DeepLTranslator

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "character_count": 12345,
            "character_limit": 500000,
        }
        mock_resp.raise_for_status = MagicMock()
        mock_post.return_value = mock_resp

        client = DeepLTranslator(api_key="test:fx")
        usage = client.get_usage()

        assert usage["character_count"] == 12345
        assert usage["character_limit"] == 500000
