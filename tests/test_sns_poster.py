"""SNS投稿モジュールテスト

- 各ポスタークラスの初期化（APIキーバリデーション）
- 投稿処理のモック
- エラーハンドリング
- get_poster / publish_post
"""

from unittest.mock import MagicMock, patch

import pytest


class TestTwitterPosterInit:
    """Twitter初期化テスト"""

    def test_missing_api_key(self):
        """APIキー未設定でValueError"""
        with patch.dict("os.environ", {}, clear=True):
            from src.sns.poster import TwitterPoster
            with pytest.raises(ValueError, match="Twitter"):
                TwitterPoster(api_key="", api_secret="", access_token="", access_secret="")

    def test_valid_init(self):
        """正常初期化"""
        from src.sns.poster import TwitterPoster
        client = TwitterPoster(
            api_key="key", api_secret="secret",
            access_token="token", access_secret="tsecret"
        )
        assert client.api_key == "key"


class TestTwitterPost:
    """Twitterツイート投稿テスト"""

    @patch("src.sns.poster.httpx.post")
    def test_success(self, mock_post):
        """正常投稿"""
        from src.sns.poster import TwitterPoster

        mock_resp = MagicMock()
        mock_resp.status_code = 201
        mock_resp.json.return_value = {
            "data": {"id": "12345", "text": "test"}
        }
        mock_post.return_value = mock_resp

        client = TwitterPoster(
            api_key="k", api_secret="s", access_token="t", access_secret="ts"
        )
        result = client.post("test tweet")

        assert result["platform_post_id"] == "12345"
        assert "12345" in result["url"]

    @patch("src.sns.poster.httpx.post")
    def test_auth_error(self, mock_post):
        """認証エラー"""
        from src.sns.poster import TwitterPoster, SnsPostError

        mock_resp = MagicMock()
        mock_resp.status_code = 401
        mock_post.return_value = mock_resp

        client = TwitterPoster(
            api_key="k", api_secret="s", access_token="t", access_secret="ts"
        )
        with pytest.raises(SnsPostError, match="認証"):
            client.post("test")

    @patch("src.sns.poster.httpx.post")
    def test_rate_limit(self, mock_post):
        """レート制限"""
        from src.sns.poster import TwitterPoster, SnsPostError

        mock_resp = MagicMock()
        mock_resp.status_code = 429
        mock_post.return_value = mock_resp

        client = TwitterPoster(
            api_key="k", api_secret="s", access_token="t", access_secret="ts"
        )
        with pytest.raises(SnsPostError, match="レート制限"):
            client.post("test")


class TestInstagramPosterInit:
    """Instagram初期化テスト"""

    def test_missing_token(self):
        """トークン未設定でValueError"""
        with patch.dict("os.environ", {}, clear=True):
            from src.sns.poster import InstagramPoster
            with pytest.raises(ValueError, match="Instagram"):
                InstagramPoster(access_token="", account_id="")

    def test_valid_init(self):
        """正常初期化"""
        from src.sns.poster import InstagramPoster
        client = InstagramPoster(access_token="token", account_id="123")
        assert client.account_id == "123"


class TestInstagramPost:
    """Instagram投稿テスト"""

    def test_no_image_error(self):
        """画像なしでエラー"""
        from src.sns.poster import InstagramPoster, SnsPostError

        client = InstagramPoster(access_token="token", account_id="123")
        with pytest.raises(SnsPostError, match="画像"):
            client.post("test", image_urls=[])

    @patch("src.sns.poster.httpx.post")
    def test_success(self, mock_post):
        """正常投稿"""
        from src.sns.poster import InstagramPoster

        # コンテナ作成レスポンス
        mock_container = MagicMock()
        mock_container.status_code = 200
        mock_container.json.return_value = {"id": "container_123"}

        # 公開レスポンス
        mock_publish = MagicMock()
        mock_publish.status_code = 200
        mock_publish.json.return_value = {"id": "media_456"}

        mock_post.side_effect = [mock_container, mock_publish]

        client = InstagramPoster(access_token="token", account_id="123")
        result = client.post("test caption", image_urls=["https://example.com/img.jpg"])

        assert result["platform_post_id"] == "media_456"
        assert mock_post.call_count == 2


class TestThreadsPosterInit:
    """Threads初期化テスト"""

    def test_missing_token(self):
        """トークン未設定でValueError"""
        with patch.dict("os.environ", {}, clear=True):
            from src.sns.poster import ThreadsPoster
            with pytest.raises(ValueError, match="Threads"):
                ThreadsPoster(access_token="", user_id="")

    def test_valid_init(self):
        """正常初期化"""
        from src.sns.poster import ThreadsPoster
        client = ThreadsPoster(access_token="token", user_id="user1")
        assert client.user_id == "user1"


class TestThreadsPost:
    """Threads投稿テスト"""

    @patch("src.sns.poster.httpx.post")
    def test_text_post(self, mock_post):
        """テキストのみ投稿"""
        from src.sns.poster import ThreadsPoster

        mock_container = MagicMock()
        mock_container.status_code = 200
        mock_container.json.return_value = {"id": "container_789"}

        mock_publish = MagicMock()
        mock_publish.status_code = 200
        mock_publish.json.return_value = {"id": "thread_101"}

        mock_post.side_effect = [mock_container, mock_publish]

        client = ThreadsPoster(access_token="token", user_id="user1")
        result = client.post("test thread")

        assert result["platform_post_id"] == "thread_101"
        # テキスト投稿の確認
        call_data = mock_post.call_args_list[0][1]["data"]
        assert call_data["media_type"] == "TEXT"

    @patch("src.sns.poster.httpx.post")
    def test_image_post(self, mock_post):
        """画像付き投稿"""
        from src.sns.poster import ThreadsPoster

        mock_container = MagicMock()
        mock_container.status_code = 200
        mock_container.json.return_value = {"id": "container_789"}

        mock_publish = MagicMock()
        mock_publish.status_code = 200
        mock_publish.json.return_value = {"id": "thread_102"}

        mock_post.side_effect = [mock_container, mock_publish]

        client = ThreadsPoster(access_token="token", user_id="user1")
        result = client.post("test", image_urls=["https://example.com/img.jpg"])

        assert result["platform_post_id"] == "thread_102"
        call_data = mock_post.call_args_list[0][1]["data"]
        assert call_data["media_type"] == "IMAGE"


class TestGetPoster:
    """get_poster関数テスト"""

    def test_twitter(self):
        """Twitterポスター取得"""
        from src.sns.poster import get_poster, TwitterPoster
        with patch.dict("os.environ", {
            "TWITTER_API_KEY": "k", "TWITTER_API_SECRET": "s",
            "TWITTER_ACCESS_TOKEN": "t", "TWITTER_ACCESS_SECRET": "ts",
        }):
            poster = get_poster("twitter")
            assert isinstance(poster, TwitterPoster)

    def test_instagram(self):
        """Instagramポスター取得"""
        from src.sns.poster import get_poster, InstagramPoster
        with patch.dict("os.environ", {
            "INSTAGRAM_ACCESS_TOKEN": "token",
            "INSTAGRAM_BUSINESS_ACCOUNT_ID": "123",
        }):
            poster = get_poster("instagram")
            assert isinstance(poster, InstagramPoster)

    def test_threads(self):
        """Threadsポスター取得"""
        from src.sns.poster import get_poster, ThreadsPoster
        with patch.dict("os.environ", {
            "THREADS_ACCESS_TOKEN": "token",
            "THREADS_USER_ID": "user1",
        }):
            poster = get_poster("threads")
            assert isinstance(poster, ThreadsPoster)

    def test_unknown_platform(self):
        """未知のプラットフォーム"""
        from src.sns.poster import get_poster, SnsPostError
        with pytest.raises(SnsPostError, match="未対応"):
            get_poster("facebook")


class TestPublishPost:
    """publish_post統合テスト"""

    @patch("src.sns.poster.httpx.post")
    def test_publish_twitter(self, mock_post):
        """Twitterに投稿"""
        from src.sns.poster import publish_post

        mock_resp = MagicMock()
        mock_resp.status_code = 201
        mock_resp.json.return_value = {"data": {"id": "99999"}}
        mock_post.return_value = mock_resp

        with patch.dict("os.environ", {
            "TWITTER_API_KEY": "k", "TWITTER_API_SECRET": "s",
            "TWITTER_ACCESS_TOKEN": "t", "TWITTER_ACCESS_SECRET": "ts",
        }):
            result = publish_post("twitter", "Hello from test!")

        assert result["platform_post_id"] == "99999"
