"""OAuth 2.0 トークン管理

トークンをJSON形式でファイル保存し、期限切れ時に自動リフレッシュする。
eBay（Basic Auth方式）とEtsy（PKCE方式）とBASE（標準OAuth2方式）の
リフレッシュ差異を内部吸収。

BASEトークンの自動管理:
- アクセストークン有効期限: 1時間
- リフレッシュトークン有効期限: 約30日
- .envに初期トークンを設定 → 初回利用時に自動でトークンファイルを作成
- 以降はトークンファイルで管理し、期限切れ時に自動リフレッシュ
"""

import base64
import hashlib
import json
import os
import secrets
import time
from pathlib import Path
from typing import Dict, Optional
from urllib.parse import urlencode

import httpx
import yaml


# トークン保存先ディレクトリ
_PROJECT_ROOT = Path(__file__).parent.parent.parent
TOKENS_DIR = _PROJECT_ROOT / "config" / "tokens"
_CONFIG_PATH = _PROJECT_ROOT / "config" / "config.yaml"


class OAuthTokenManager:
    """OAuthトークンの保存・読込・リフレッシュを管理"""

    # プラットフォーム別設定
    PLATFORM_CONFIG = {
        "ebay": {
            "auth_url": "https://auth.ebay.com/oauth2/authorize",
            "token_url": "https://api.ebay.com/identity/v1/oauth2/token",
            "sandbox_auth_url": "https://auth.sandbox.ebay.com/oauth2/authorize",
            "sandbox_token_url": "https://api.sandbox.ebay.com/identity/v1/oauth2/token",
            "scopes": [
                "https://api.ebay.com/oauth/api_scope",
                "https://api.ebay.com/oauth/api_scope/sell.inventory",
                "https://api.ebay.com/oauth/api_scope/sell.fulfillment",
                "https://api.ebay.com/oauth/api_scope/sell.account",
            ],
        },
        "etsy": {
            "auth_url": "https://www.etsy.com/oauth/connect",
            "token_url": "https://api.etsy.com/v3/public/oauth/token",
            "scopes": [
                "listings_w",
                "listings_r",
                "transactions_r",
                "shops_r",
            ],
        },
        "base": {
            "auth_url": "https://api.thebase.in/1/oauth/authorize",
            "token_url": "https://api.thebase.in/1/oauth/token",
            "scopes": [
                "read_items",
                "write_items",
                "read_orders",
                "write_orders",
            ],
        },
    }

    def __init__(self, platform: str, sandbox: bool = False):
        """
        Args:
            platform: 'ebay' or 'etsy'
            sandbox: True=sandbox環境（eBayのみ）
        """
        if platform not in self.PLATFORM_CONFIG:
            raise ValueError(f"未対応プラットフォーム: {platform}")

        self.platform = platform
        self.sandbox = sandbox
        self.config = self.PLATFORM_CONFIG[platform]
        self.token_path = TOKENS_DIR / f"{platform}.json"

        # トークンディレクトリ作成
        TOKENS_DIR.mkdir(parents=True, exist_ok=True)

    def _get_token_url(self) -> str:
        """環境に応じたトークンURLを返す"""
        if self.sandbox and self.platform == "ebay":
            return self.config["sandbox_token_url"]
        return self.config["token_url"]

    def _get_auth_url(self) -> str:
        """環境に応じた認証URLを返す"""
        if self.sandbox and self.platform == "ebay":
            return self.config["sandbox_auth_url"]
        return self.config["auth_url"]

    def save_token(self, token_data: Dict) -> None:
        """トークンをファイルに保存"""
        # 有効期限の絶対時刻を計算して保存
        if "expires_in" in token_data and "expires_at" not in token_data:
            token_data["expires_at"] = time.time() + token_data["expires_in"]

        token_data["platform"] = self.platform
        token_data["saved_at"] = time.time()

        with open(self.token_path, "w") as f:
            json.dump(token_data, f, indent=2)

    def load_token(self) -> Optional[Dict]:
        """保存済みトークンを読み込む"""
        if not self.token_path.exists():
            return None

        with open(self.token_path) as f:
            return json.load(f)

    def is_token_expired(self, token_data: Optional[Dict] = None) -> bool:
        """トークンが期限切れかチェック（60秒のバッファ付き）"""
        if token_data is None:
            token_data = self.load_token()

        if not token_data:
            return True

        expires_at = token_data.get("expires_at", 0)
        # 60秒のバッファ: 期限切れ直前にリフレッシュ
        return time.time() >= (expires_at - 60)

    def get_valid_token(self) -> str:
        """有効なアクセストークンを返す（期限切れなら自動リフレッシュ）

        BASEの場合、トークンファイルが未作成なら.envから自動ブートストラップする。
        """
        token_data = self.load_token()

        # トークンファイルが無い場合、.envからブートストラップを試みる
        if not token_data:
            if self.platform == "base":
                token_data = self._bootstrap_base_from_env()
            if not token_data:
                raise ValueError(
                    f"{self.platform}のトークンが未設定です。"
                    f"`python -m src.cli.main auth init --platform {self.platform}` で初期化してください。"
                )

        if self.is_token_expired(token_data):
            token_data = self.refresh_token(token_data)

        return token_data["access_token"]

    def _bootstrap_base_from_env(self) -> Optional[Dict]:
        """BASE: .envのトークンからトークンファイルを初期作成

        .envにBASE_ACCESS_TOKENとBASE_REFRESH_TOKENがあれば
        トークンファイルを作成する。有効期限は不明なので即リフレッシュ対象とする。
        """
        access_token = os.environ.get("BASE_ACCESS_TOKEN", "")
        refresh_token = os.environ.get("BASE_REFRESH_TOKEN", "")

        if not access_token or not refresh_token:
            return None

        token_data = {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            # 有効期限不明 → 期限切れとして扱い、次回アクセス時にリフレッシュ
            "expires_at": 0,
        }
        self.save_token(token_data)
        return token_data

    def refresh_token(self, token_data: Dict) -> Dict:
        """リフレッシュトークンで新しいアクセストークンを取得"""
        refresh_token = token_data.get("refresh_token")
        if not refresh_token:
            raise ValueError(
                f"{self.platform}のリフレッシュトークンがありません。再認証が必要です。"
            )

        if self.platform == "ebay":
            new_token = self._refresh_ebay(refresh_token)
        elif self.platform == "etsy":
            new_token = self._refresh_etsy(refresh_token)
        elif self.platform == "base":
            new_token = self._refresh_base(refresh_token)
        else:
            raise ValueError(f"未対応プラットフォーム: {self.platform}")

        # リフレッシュトークンが新しく発行されなければ既存を引き継ぎ
        if "refresh_token" not in new_token:
            new_token["refresh_token"] = refresh_token

        self.save_token(new_token)
        return new_token

    def _refresh_ebay(self, refresh_token: str) -> Dict:
        """eBay: Basic Auth方式でリフレッシュ"""
        client_id = os.environ.get("EBAY_CLIENT_ID", "")
        client_secret = os.environ.get("EBAY_CLIENT_SECRET", "")

        if not client_id or not client_secret:
            raise ValueError("EBAY_CLIENT_ID / EBAY_CLIENT_SECRET が設定されていません。")

        # Basic認証ヘッダー
        credentials = base64.b64encode(
            f"{client_id}:{client_secret}".encode()
        ).decode()

        response = httpx.post(
            self._get_token_url(),
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "Authorization": f"Basic {credentials}",
            },
            data={
                "grant_type": "refresh_token",
                "refresh_token": refresh_token,
            },
            timeout=30,
        )
        response.raise_for_status()
        return response.json()

    def _refresh_etsy(self, refresh_token: str) -> Dict:
        """Etsy: PKCE方式でリフレッシュ"""
        api_key = os.environ.get("ETSY_API_KEY", "")
        if not api_key:
            raise ValueError("ETSY_API_KEY が設定されていません。")

        response = httpx.post(
            self._get_token_url(),
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            data={
                "grant_type": "refresh_token",
                "client_id": api_key,
                "refresh_token": refresh_token,
            },
            timeout=30,
        )
        response.raise_for_status()
        return response.json()

    def _refresh_base(self, refresh_token: str) -> Dict:
        """BASE: リフレッシュトークンで更新

        BASE APIはredirect_uriが必須パラメータ。
        config.yamlのbase.redirect_uriから読み込む。
        レスポンスには新しいaccess_tokenとrefresh_tokenが含まれる。
        """
        client_id = os.environ.get("BASE_CLIENT_ID", "")
        client_secret = os.environ.get("BASE_CLIENT_SECRET", "")

        if not client_id or not client_secret:
            raise ValueError("BASE_CLIENT_ID / BASE_CLIENT_SECRET が設定されていません。")

        redirect_uri = self._get_base_redirect_uri()

        data = {
            "grant_type": "refresh_token",
            "client_id": client_id,
            "client_secret": client_secret,
            "refresh_token": refresh_token,
        }
        if redirect_uri:
            data["redirect_uri"] = redirect_uri

        response = httpx.post(
            self._get_token_url(),
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            data=data,
            timeout=30,
        )
        response.raise_for_status()
        return response.json()

    @staticmethod
    def _get_base_redirect_uri() -> Optional[str]:
        """config.yamlからBASEのredirect_uriを取得"""
        if not _CONFIG_PATH.exists():
            return None
        with open(_CONFIG_PATH) as f:
            config = yaml.safe_load(f)
        return config.get("base", {}).get("redirect_uri")

    def build_auth_url(self, redirect_uri: str, state: Optional[str] = None) -> Dict:
        """認証URL（ブラウザ用）を構築

        Returns:
            {"url": str, "state": str, "code_verifier": str (Etsyのみ)}
        """
        state = state or secrets.token_urlsafe(32)

        if self.platform == "ebay":
            return self._build_ebay_auth_url(redirect_uri, state)
        elif self.platform == "etsy":
            return self._build_etsy_auth_url(redirect_uri, state)
        elif self.platform == "base":
            return self._build_base_auth_url(redirect_uri, state)
        else:
            raise ValueError(f"未対応プラットフォーム: {self.platform}")

    def _build_ebay_auth_url(self, redirect_uri: str, state: str) -> Dict:
        """eBay認証URL構築"""
        client_id = os.environ.get("EBAY_CLIENT_ID", "")
        params = {
            "client_id": client_id,
            "response_type": "code",
            "redirect_uri": redirect_uri,
            "scope": " ".join(self.config["scopes"]),
            "state": state,
        }
        url = f"{self._get_auth_url()}?{urlencode(params)}"
        return {"url": url, "state": state}

    def _build_etsy_auth_url(self, redirect_uri: str, state: str) -> Dict:
        """Etsy認証URL構築（PKCE）"""
        api_key = os.environ.get("ETSY_API_KEY", "")

        # PKCE: code_verifier と code_challenge を生成
        code_verifier = secrets.token_urlsafe(64)
        code_challenge = base64.urlsafe_b64encode(
            hashlib.sha256(code_verifier.encode()).digest()
        ).decode().rstrip("=")

        params = {
            "response_type": "code",
            "client_id": api_key,
            "redirect_uri": redirect_uri,
            "scope": " ".join(self.config["scopes"]),
            "state": state,
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
        }
        url = f"{self._get_auth_url()}?{urlencode(params)}"
        return {"url": url, "state": state, "code_verifier": code_verifier}

    def _build_base_auth_url(self, redirect_uri: str, state: str) -> Dict:
        """BASE認証URL構築"""
        client_id = os.environ.get("BASE_CLIENT_ID", "")
        params = {
            "response_type": "code",
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "scope": " ".join(self.config["scopes"]),
            "state": state,
        }
        url = f"{self._get_auth_url()}?{urlencode(params)}"
        return {"url": url, "state": state}

    def exchange_code(self, code: str, redirect_uri: str,
                      code_verifier: Optional[str] = None) -> Dict:
        """認証コードをトークンに交換"""
        if self.platform == "ebay":
            token_data = self._exchange_ebay(code, redirect_uri)
        elif self.platform == "etsy":
            if not code_verifier:
                raise ValueError("Etsyにはcode_verifierが必要です。")
            token_data = self._exchange_etsy(code, redirect_uri, code_verifier)
        elif self.platform == "base":
            token_data = self._exchange_base(code, redirect_uri)
        else:
            raise ValueError(f"未対応プラットフォーム: {self.platform}")

        self.save_token(token_data)
        return token_data

    def _exchange_ebay(self, code: str, redirect_uri: str) -> Dict:
        """eBay: 認証コード→トークン交換"""
        client_id = os.environ.get("EBAY_CLIENT_ID", "")
        client_secret = os.environ.get("EBAY_CLIENT_SECRET", "")

        credentials = base64.b64encode(
            f"{client_id}:{client_secret}".encode()
        ).decode()

        response = httpx.post(
            self._get_token_url(),
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "Authorization": f"Basic {credentials}",
            },
            data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": redirect_uri,
            },
            timeout=30,
        )
        response.raise_for_status()
        return response.json()

    def _exchange_etsy(self, code: str, redirect_uri: str,
                       code_verifier: str) -> Dict:
        """Etsy: 認証コード→トークン交換（PKCE）"""
        api_key = os.environ.get("ETSY_API_KEY", "")

        response = httpx.post(
            self._get_token_url(),
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            data={
                "grant_type": "authorization_code",
                "client_id": api_key,
                "redirect_uri": redirect_uri,
                "code": code,
                "code_verifier": code_verifier,
            },
            timeout=30,
        )
        response.raise_for_status()
        return response.json()

    def _exchange_base(self, code: str, redirect_uri: str) -> Dict:
        """BASE: 認証コード→トークン交換"""
        client_id = os.environ.get("BASE_CLIENT_ID", "")
        client_secret = os.environ.get("BASE_CLIENT_SECRET", "")

        response = httpx.post(
            self._get_token_url(),
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            data={
                "grant_type": "authorization_code",
                "client_id": client_id,
                "client_secret": client_secret,
                "code": code,
                "redirect_uri": redirect_uri,
            },
            timeout=30,
        )
        response.raise_for_status()
        return response.json()

    def delete_token(self) -> bool:
        """保存済みトークンを削除"""
        if self.token_path.exists():
            self.token_path.unlink()
            return True
        return False
