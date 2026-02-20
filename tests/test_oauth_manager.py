"""OAuthトークン管理テスト

- トークン保存・読込
- 期限切れ判定
- 認証URL構築
"""

import json
import os
import tempfile
import time

import pytest

from src.auth.oauth_manager import OAuthTokenManager, TOKENS_DIR


@pytest.fixture
def token_dir(tmp_path):
    """テスト用トークンディレクトリ"""
    import src.auth.oauth_manager as mod
    original = mod.TOKENS_DIR
    mod.TOKENS_DIR = tmp_path
    yield tmp_path
    mod.TOKENS_DIR = original


@pytest.fixture
def ebay_manager(token_dir):
    """eBay用マネージャー"""
    manager = OAuthTokenManager("ebay", sandbox=True)
    manager.token_path = token_dir / "ebay.json"
    return manager


@pytest.fixture
def etsy_manager(token_dir):
    """Etsy用マネージャー"""
    manager = OAuthTokenManager("etsy")
    manager.token_path = token_dir / "etsy.json"
    return manager


class TestTokenSaveLoad:
    """トークン保存・読込テスト"""

    def test_save_and_load(self, ebay_manager):
        """トークンの保存と読込"""
        token_data = {
            "access_token": "test_access_token",
            "refresh_token": "test_refresh_token",
            "expires_in": 7200,
        }
        ebay_manager.save_token(token_data)

        loaded = ebay_manager.load_token()
        assert loaded is not None
        assert loaded["access_token"] == "test_access_token"
        assert loaded["refresh_token"] == "test_refresh_token"
        assert "expires_at" in loaded
        assert loaded["platform"] == "ebay"

    def test_load_nonexistent(self, ebay_manager):
        """存在しないトークンの読込"""
        result = ebay_manager.load_token()
        assert result is None

    def test_delete_token(self, ebay_manager):
        """トークン削除"""
        ebay_manager.save_token({"access_token": "test", "expires_in": 3600})
        assert ebay_manager.delete_token() is True
        assert ebay_manager.load_token() is None
        assert ebay_manager.delete_token() is False


class TestTokenExpiry:
    """トークン期限切れ判定テスト"""

    def test_valid_token(self, ebay_manager):
        """有効なトークン"""
        token_data = {
            "access_token": "test",
            "expires_at": time.time() + 3600,  # 1時間後
        }
        ebay_manager.save_token(token_data)
        assert ebay_manager.is_token_expired() is False

    def test_expired_token(self, ebay_manager):
        """期限切れトークン"""
        token_data = {
            "access_token": "test",
            "expires_at": time.time() - 100,  # 100秒前
        }
        ebay_manager.save_token(token_data)
        assert ebay_manager.is_token_expired() is True

    def test_no_token(self, ebay_manager):
        """トークンなし → 期限切れ扱い"""
        assert ebay_manager.is_token_expired() is True

    def test_buffer_60sec(self, ebay_manager):
        """60秒バッファ: 残り30秒 → 期限切れ扱い"""
        token_data = {
            "access_token": "test",
            "expires_at": time.time() + 30,  # 30秒後（バッファ60秒未満）
        }
        ebay_manager.save_token(token_data)
        assert ebay_manager.is_token_expired() is True


class TestAuthUrl:
    """認証URL構築テスト"""

    def test_ebay_auth_url(self, ebay_manager, monkeypatch):
        """eBay認証URL構築"""
        monkeypatch.setenv("EBAY_CLIENT_ID", "test_client_id")
        result = ebay_manager.build_auth_url("https://localhost/callback")
        assert "url" in result
        assert "state" in result
        assert "sandbox.ebay.com" in result["url"]
        assert "test_client_id" in result["url"]

    def test_etsy_auth_url_pkce(self, etsy_manager, monkeypatch):
        """Etsy認証URL（PKCE: code_verifierあり）"""
        monkeypatch.setenv("ETSY_API_KEY", "test_api_key")
        result = etsy_manager.build_auth_url("https://localhost/callback")
        assert "url" in result
        assert "state" in result
        assert "code_verifier" in result  # PKCEなのでcode_verifierが必要
        assert "etsy.com" in result["url"]


class TestGetValidToken:
    """有効トークン取得テスト"""

    def test_no_token_raises(self, ebay_manager):
        """トークンなし → ValueError"""
        with pytest.raises(ValueError, match="トークンが未設定"):
            ebay_manager.get_valid_token()

    def test_valid_token_returned(self, ebay_manager):
        """有効なトークンがそのまま返る"""
        token_data = {
            "access_token": "valid_token_123",
            "expires_at": time.time() + 3600,
        }
        ebay_manager.save_token(token_data)
        assert ebay_manager.get_valid_token() == "valid_token_123"


class TestUnsupportedPlatform:
    """未対応プラットフォームテスト"""

    def test_invalid_platform_raises(self, token_dir):
        """未対応プラットフォーム → ValueError"""
        with pytest.raises(ValueError, match="未対応"):
            OAuthTokenManager("shopify")
