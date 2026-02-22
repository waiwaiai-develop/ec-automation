"""SNS投稿モジュール

各プラットフォーム（X/Twitter, Instagram, Threads）へ投稿するクライアント。
APIキーは環境変数で管理。

- X (Twitter): API v2 (OAuth 1.0a)
- Instagram: Graph API (Facebookページ経由)
- Threads: Threads Publishing API

環境変数:
  TWITTER_API_KEY, TWITTER_API_SECRET, TWITTER_ACCESS_TOKEN, TWITTER_ACCESS_SECRET
  INSTAGRAM_ACCESS_TOKEN, INSTAGRAM_BUSINESS_ACCOUNT_ID
  THREADS_ACCESS_TOKEN, THREADS_USER_ID
"""

import json
import os
from typing import Dict, List, Optional

import httpx


class SnsPostError(Exception):
    """SNS投稿エラー"""
    pass


class TwitterPoster:
    """X (Twitter) API v2 投稿クライアント

    OAuth 1.0a 署名でツイートを投稿。
    """

    API_URL = "https://api.twitter.com/2/tweets"

    def __init__(
        self,
        api_key=None,
        api_secret=None,
        access_token=None,
        access_secret=None,
    ):
        self.api_key = api_key or os.getenv("TWITTER_API_KEY", "")
        self.api_secret = api_secret or os.getenv("TWITTER_API_SECRET", "")
        self.access_token = access_token or os.getenv("TWITTER_ACCESS_TOKEN", "")
        self.access_secret = access_secret or os.getenv("TWITTER_ACCESS_SECRET", "")

        if not all([self.api_key, self.api_secret, self.access_token, self.access_secret]):
            raise ValueError(
                "Twitter APIキーが未設定です。"
                "TWITTER_API_KEY, TWITTER_API_SECRET, TWITTER_ACCESS_TOKEN, "
                "TWITTER_ACCESS_SECRET を設定してください。"
            )

    def _oauth_header(self, method, url, body_params=None):
        """OAuth 1.0a 署名ヘッダーを生成"""
        import hashlib
        import hmac
        import time
        import urllib.parse
        import uuid

        oauth_params = {
            "oauth_consumer_key": self.api_key,
            "oauth_nonce": uuid.uuid4().hex,
            "oauth_signature_method": "HMAC-SHA1",
            "oauth_timestamp": str(int(time.time())),
            "oauth_token": self.access_token,
            "oauth_version": "1.0",
        }

        # パラメータを結合してソート
        all_params = dict(oauth_params)
        if body_params:
            all_params.update(body_params)

        param_string = "&".join(
            "{}={}".format(
                urllib.parse.quote(str(k), safe=""),
                urllib.parse.quote(str(v), safe=""),
            )
            for k, v in sorted(all_params.items())
        )

        base_string = "{}&{}&{}".format(
            method.upper(),
            urllib.parse.quote(url, safe=""),
            urllib.parse.quote(param_string, safe=""),
        )

        signing_key = "{}&{}".format(
            urllib.parse.quote(self.api_secret, safe=""),
            urllib.parse.quote(self.access_secret, safe=""),
        )

        signature = hmac.new(
            signing_key.encode("utf-8"),
            base_string.encode("utf-8"),
            hashlib.sha1,
        ).digest()

        import base64
        oauth_params["oauth_signature"] = base64.b64encode(signature).decode("utf-8")

        auth_header = "OAuth " + ", ".join(
            '{}="{}"'.format(
                urllib.parse.quote(k, safe=""),
                urllib.parse.quote(v, safe=""),
            )
            for k, v in sorted(oauth_params.items())
        )

        return auth_header

    def post(self, text, image_urls=None):
        # type: (str, Optional[List[str]]) -> Dict
        """ツイートを投稿

        Args:
            text: ツイート本文（280文字以内）
            image_urls: 画像URL（現在未対応、将来的にメディアアップロード対応）

        Returns:
            {"platform_post_id": str, "url": str}
        """
        payload = {"text": text}

        auth_header = self._oauth_header("POST", self.API_URL)

        resp = httpx.post(
            self.API_URL,
            json=payload,
            headers={
                "Authorization": auth_header,
                "Content-Type": "application/json",
            },
            timeout=30.0,
        )

        if resp.status_code == 401:
            raise SnsPostError("Twitter認証エラー: APIキーを確認してください")
        if resp.status_code == 403:
            raise SnsPostError("Twitter権限エラー: アプリの権限を確認してください")
        if resp.status_code == 429:
            raise SnsPostError("Twitterレート制限: しばらく待ってから再試行してください")

        if resp.status_code not in (200, 201):
            try:
                err = resp.json()
                detail = err.get("detail", err.get("title", resp.text))
            except Exception:
                detail = resp.text
            raise SnsPostError("Twitter投稿エラー ({}): {}".format(resp.status_code, detail))

        data = resp.json()
        tweet_data = data.get("data", {})
        tweet_id = tweet_data.get("id", "")

        return {
            "platform_post_id": tweet_id,
            "url": "https://x.com/i/web/status/{}".format(tweet_id) if tweet_id else "",
        }


class InstagramPoster:
    """Instagram Graph API 投稿クライアント

    Facebookページに紐づくInstagramビジネスアカウント経由で投稿。
    画像付き投稿が必須。
    """

    GRAPH_API = "https://graph.facebook.com/v18.0"

    def __init__(self, access_token=None, account_id=None):
        self.access_token = access_token or os.getenv("INSTAGRAM_ACCESS_TOKEN", "")
        self.account_id = account_id or os.getenv("INSTAGRAM_BUSINESS_ACCOUNT_ID", "")

        if not self.access_token or not self.account_id:
            raise ValueError(
                "Instagram APIキーが未設定です。"
                "INSTAGRAM_ACCESS_TOKEN, INSTAGRAM_BUSINESS_ACCOUNT_ID を設定してください。"
            )

    def post(self, text, image_urls=None):
        # type: (str, Optional[List[str]]) -> Dict
        """Instagram投稿

        Instagramは画像付き投稿が必須。image_urlsが空の場合はエラー。

        Args:
            text: キャプション（ハッシュタグ含む）
            image_urls: 画像URL（最低1枚必須、公開URLが必要）

        Returns:
            {"platform_post_id": str, "url": str}
        """
        if not image_urls:
            raise SnsPostError("Instagramは画像付き投稿が必須です")

        # Step 1: メディアコンテナを作成
        container_url = "{}/{}/media".format(self.GRAPH_API, self.account_id)
        container_resp = httpx.post(
            container_url,
            data={
                "image_url": image_urls[0],  # 最初の画像
                "caption": text,
                "access_token": self.access_token,
            },
            timeout=30.0,
        )

        if container_resp.status_code != 200:
            try:
                err = container_resp.json().get("error", {})
                msg = err.get("message", container_resp.text)
            except Exception:
                msg = container_resp.text
            raise SnsPostError("Instagramメディア作成エラー: {}".format(msg))

        creation_id = container_resp.json().get("id")
        if not creation_id:
            raise SnsPostError("Instagramメディア作成ID取得に失敗しました")

        # Step 2: メディアを公開
        publish_url = "{}/{}/media_publish".format(self.GRAPH_API, self.account_id)
        publish_resp = httpx.post(
            publish_url,
            data={
                "creation_id": creation_id,
                "access_token": self.access_token,
            },
            timeout=60.0,
        )

        if publish_resp.status_code != 200:
            try:
                err = publish_resp.json().get("error", {})
                msg = err.get("message", publish_resp.text)
            except Exception:
                msg = publish_resp.text
            raise SnsPostError("Instagram公開エラー: {}".format(msg))

        media_id = publish_resp.json().get("id", "")

        return {
            "platform_post_id": media_id,
            "url": "https://www.instagram.com/p/{}".format(media_id) if media_id else "",
        }


class ThreadsPoster:
    """Threads Publishing API クライアント

    Meta Threads APIで投稿を作成。
    """

    GRAPH_API = "https://graph.threads.net/v1.0"

    def __init__(self, access_token=None, user_id=None):
        self.access_token = access_token or os.getenv("THREADS_ACCESS_TOKEN", "")
        self.user_id = user_id or os.getenv("THREADS_USER_ID", "")

        if not self.access_token or not self.user_id:
            raise ValueError(
                "Threads APIキーが未設定です。"
                "THREADS_ACCESS_TOKEN, THREADS_USER_ID を設定してください。"
            )

    def post(self, text, image_urls=None):
        # type: (str, Optional[List[str]]) -> Dict
        """Threadsに投稿

        Args:
            text: 投稿本文（500文字以内）
            image_urls: 画像URL（任意）

        Returns:
            {"platform_post_id": str, "url": str}
        """
        # Step 1: メディアコンテナを作成
        container_url = "{}/{}/threads".format(self.GRAPH_API, self.user_id)
        container_data = {
            "text": text,
            "media_type": "TEXT",
            "access_token": self.access_token,
        }

        # 画像付き投稿
        if image_urls:
            container_data["media_type"] = "IMAGE"
            container_data["image_url"] = image_urls[0]

        container_resp = httpx.post(
            container_url,
            data=container_data,
            timeout=30.0,
        )

        if container_resp.status_code != 200:
            try:
                err = container_resp.json().get("error", {})
                msg = err.get("message", container_resp.text)
            except Exception:
                msg = container_resp.text
            raise SnsPostError("Threadsメディア作成エラー: {}".format(msg))

        creation_id = container_resp.json().get("id")
        if not creation_id:
            raise SnsPostError("Threadsメディア作成ID取得に失敗しました")

        # Step 2: 公開
        publish_url = "{}/{}/threads_publish".format(self.GRAPH_API, self.user_id)
        publish_resp = httpx.post(
            publish_url,
            data={
                "creation_id": creation_id,
                "access_token": self.access_token,
            },
            timeout=30.0,
        )

        if publish_resp.status_code != 200:
            try:
                err = publish_resp.json().get("error", {})
                msg = err.get("message", publish_resp.text)
            except Exception:
                msg = publish_resp.text
            raise SnsPostError("Threads公開エラー: {}".format(msg))

        post_id = publish_resp.json().get("id", "")

        return {
            "platform_post_id": post_id,
            "url": "https://www.threads.net/@/post/{}".format(post_id) if post_id else "",
        }


def get_poster(platform):
    # type: (str) -> object
    """プラットフォーム名からポスターインスタンスを取得

    Args:
        platform: "twitter", "instagram", "threads"

    Returns:
        対応するポスタークラスのインスタンス

    Raises:
        ValueError: APIキー未設定時
        SnsPostError: 未対応プラットフォーム
    """
    if platform == "twitter":
        return TwitterPoster()
    elif platform == "instagram":
        return InstagramPoster()
    elif platform == "threads":
        return ThreadsPoster()
    else:
        raise SnsPostError("未対応のプラットフォーム: {}".format(platform))


def publish_post(platform, text, image_urls=None):
    # type: (str, str, Optional[List[str]]) -> Dict
    """SNSに投稿

    Args:
        platform: "twitter", "instagram", "threads"
        text: 投稿本文
        image_urls: 画像URL（任意）

    Returns:
        {"platform_post_id": str, "url": str}
    """
    poster = get_poster(platform)
    return poster.post(text, image_urls=image_urls)
