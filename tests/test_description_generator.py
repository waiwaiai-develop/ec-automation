"""AI商品説明生成テスト

_parse_json_response直接テスト + API呼び出しモック。
ANTHROPIC_API_KEY不要（全てモック）。
"""

from unittest.mock import MagicMock, patch

import pytest

from src.ai.description_generator import (
    _parse_json_response,
    generate_description,
    generate_seo_tags,
    generate_full_listing,
)


# --- _parse_json_response ---

class TestParseJsonResponse:
    """JSONパーサーテスト"""

    def test_plain_json(self):
        """プレーンJSON → パース成功"""
        text = '{"title": "Japanese Tenugui", "description": "Beautiful cotton towel"}'
        result = _parse_json_response(text)
        assert result["title"] == "Japanese Tenugui"

    def test_json_in_code_block(self):
        """```json ... ``` ブロック → パース成功"""
        text = """Here is the listing:

```json
{"title": "Tenugui Towel", "description": "Made in Japan"}
```

I hope this helps!"""
        result = _parse_json_response(text)
        assert result["title"] == "Tenugui Towel"

    def test_json_in_code_block_no_lang(self):
        """``` ... ``` ブロック（言語指定なし） → パース成功"""
        text = """```
{"title": "Furoshiki Wrap", "tags": ["japanese", "gift"]}
```"""
        result = _parse_json_response(text)
        assert result["title"] == "Furoshiki Wrap"

    def test_json_with_surrounding_text(self):
        """前後にテキスト付き → {} ブロック抽出"""
        text = 'The result is: {"title": "Knife", "price": 100} as shown above.'
        result = _parse_json_response(text)
        assert result["title"] == "Knife"

    def test_nested_json(self):
        """ネストJSON → パース成功"""
        text = '{"title": "Tenugui", "item_specifics": {"material": "cotton", "origin": "Japan"}}'
        result = _parse_json_response(text)
        assert result["item_specifics"]["material"] == "cotton"

    def test_invalid_json_raises(self):
        """不正テキスト → ValueError"""
        with pytest.raises(ValueError, match="JSONパースに失敗"):
            _parse_json_response("This is not JSON at all")

    def test_empty_string_raises(self):
        """空文字 → ValueError"""
        with pytest.raises(ValueError):
            _parse_json_response("")

    def test_json_array(self):
        """配列は非対応（dictのみ）→ fallbackで{}検出"""
        text = '{"tags": ["tag1", "tag2", "tag3"]}'
        result = _parse_json_response(text)
        assert len(result["tags"]) == 3


# --- generate_description（モック） ---

class TestGenerateDescription:
    """商品説明生成テスト（APIモック）"""

    @patch("src.ai.description_generator._get_client")
    def test_generate_description(self, mock_get_client):
        """正常ケース: JSON応答をパースして返す"""
        # モックレスポンス
        mock_response = MagicMock()
        mock_response.content = [MagicMock()]
        mock_response.content[0].text = '{"title": "Japanese Cotton Tenugui Towel Mt Fuji Design", "description": "Beautiful traditional towel.", "item_specifics": {"material": "cotton"}}'

        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_response
        mock_get_client.return_value = mock_client

        product = {
            "name_ja": "手ぬぐい 富士山柄",
            "category": "tenugui",
            "weight_g": 50,
            "wholesale_price_jpy": 400,
        }

        result = generate_description(product)
        assert "title" in result
        assert "description" in result
        assert "item_specifics" in result

        # API呼び出し確認
        mock_client.messages.create.assert_called_once()
        call_kwargs = mock_client.messages.create.call_args[1]
        assert call_kwargs["model"] == "claude-sonnet-4-6"
        assert "NEVER include brand names" in call_kwargs["messages"][0]["content"]

    @patch("src.ai.description_generator._get_client")
    def test_generate_description_with_code_block(self, mock_get_client):
        """応答が```json```で囲まれている場合"""
        mock_response = MagicMock()
        mock_response.content = [MagicMock()]
        mock_response.content[0].text = """Here's the listing:

```json
{"title": "Tenugui", "description": "A towel", "item_specifics": {}}
```"""

        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_response
        mock_get_client.return_value = mock_client

        result = generate_description({"name_ja": "手ぬぐい"})
        assert result["title"] == "Tenugui"

    @patch("src.ai.description_generator._get_client")
    def test_custom_model(self, mock_get_client):
        """モデル指定"""
        mock_response = MagicMock()
        mock_response.content = [MagicMock()]
        mock_response.content[0].text = '{"title": "T", "description": "D", "item_specifics": {}}'

        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_response
        mock_get_client.return_value = mock_client

        generate_description({"name_ja": "テスト"}, model="claude-haiku-4-5")

        call_kwargs = mock_client.messages.create.call_args[1]
        assert call_kwargs["model"] == "claude-haiku-4-5"


# --- generate_seo_tags（モック） ---

class TestGenerateSeotags:
    """SEOタグ生成テスト"""

    @patch("src.ai.description_generator._get_client")
    def test_generate_seo_tags(self, mock_get_client):
        """13タグ生成"""
        tags = ["japanese towel", "tenugui", "cotton cloth", "made in japan",
                "japanese gift", "wall decor", "hand towel", "furoshiki",
                "japanese art", "kitchen towel", "eco friendly", "reusable",
                "japanese fabric"]

        mock_response = MagicMock()
        mock_response.content = [MagicMock()]
        mock_response.content[0].text = json.dumps({"tags": tags})

        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_response
        mock_get_client.return_value = mock_client

        result = generate_seo_tags({
            "name_ja": "手ぬぐい",
            "category": "tenugui",
        })
        assert "tags" in result
        assert len(result["tags"]) == 13


# --- generate_full_listing（モック） ---

class TestGenerateFullListing:
    """一括生成テスト"""

    @patch("src.ai.description_generator._get_client")
    def test_full_listing(self, mock_get_client):
        """説明 + タグを一括生成"""
        # 1回目: generate_description
        desc_response = MagicMock()
        desc_response.content = [MagicMock()]
        desc_response.content[0].text = '{"title": "Tenugui", "description": "A towel", "item_specifics": {}}'

        # 2回目: generate_seo_tags
        tags_response = MagicMock()
        tags_response.content = [MagicMock()]
        tags_response.content[0].text = '{"tags": ["tag1", "tag2"]}'

        mock_client = MagicMock()
        mock_client.messages.create.side_effect = [desc_response, tags_response]
        mock_get_client.return_value = mock_client

        result = generate_full_listing({"name_ja": "手ぬぐい", "category": "tenugui"})
        assert result["title"] == "Tenugui"
        assert result["tags"] == ["tag1", "tag2"]
        assert mock_client.messages.create.call_count == 2


# --- API キー未設定テスト ---

class TestApiKeyMissing:
    """APIキー未設定時のエラーテスト"""

    @patch.dict("os.environ", {}, clear=True)
    def test_missing_api_key(self):
        """ANTHROPIC_API_KEY未設定 → ValueError"""
        with pytest.raises(ValueError, match="ANTHROPIC_API_KEY"):
            generate_description({"name_ja": "テスト"})


# jsonモジュールのimport（TestGenerateSeotags内で使用）
import json
