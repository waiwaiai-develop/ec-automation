"""OAuth初回認証ヘルパー

ブラウザで認証URLを開き、コールバックから認証コードを受け取って
トークンを取得・保存する。

使い方:
    python scripts/oauth_setup.py --platform ebay [--sandbox]
    python scripts/oauth_setup.py --platform etsy
    python scripts/oauth_setup.py --platform base
"""

import sys
import webbrowser
from pathlib import Path

import click
from dotenv import load_dotenv

# .envファイル読み込み
_project_root = Path(__file__).parent.parent
_env_path = _project_root / "config" / ".env"
if _env_path.exists():
    load_dotenv(_env_path)

sys.path.insert(0, str(_project_root))

from src.auth.oauth_manager import OAuthTokenManager

# ローカルコールバックURL
DEFAULT_REDIRECT_URI = "https://localhost:8443/callback"


@click.command()
@click.option("--platform", required=True,
              type=click.Choice(["ebay", "etsy", "base"]),
              help="認証するプラットフォーム")
@click.option("--sandbox", is_flag=True, help="sandbox環境を使用（eBayのみ）")
@click.option("--redirect-uri", default=DEFAULT_REDIRECT_URI,
              help="リダイレクトURI")
def setup_oauth(platform: str, sandbox: bool, redirect_uri: str):
    """OAuth認証セットアップ"""
    click.echo(f"\n{'='*50}")
    click.echo(f"OAuth認証セットアップ: {platform.upper()}")
    if sandbox:
        click.echo("環境: sandbox")
    click.echo(f"{'='*50}\n")

    manager = OAuthTokenManager(platform, sandbox=sandbox)

    # 既存トークンチェック
    existing = manager.load_token()
    if existing and not manager.is_token_expired(existing):
        click.echo("有効なトークンが既に存在します。")
        if not click.confirm("再認証しますか？"):
            click.echo("中止しました。")
            return

    # 認証URL構築
    auth_info = manager.build_auth_url(redirect_uri)
    auth_url = auth_info["url"]

    click.echo("以下のURLをブラウザで開いて認証してください:")
    click.echo(f"\n{auth_url}\n")

    # ブラウザを自動で開く
    try:
        webbrowser.open(auth_url)
        click.echo("(ブラウザが自動で開きました)")
    except Exception:
        click.echo("(ブラウザを手動で開いてください)")

    click.echo("\n認証後、リダイレクトされたURLから認証コードを取得してください。")
    code = click.prompt("認証コード (code パラメータの値)")

    # コード→トークン交換
    try:
        code_verifier = auth_info.get("code_verifier")  # Etsyのみ
        token_data = manager.exchange_code(
            code=code,
            redirect_uri=redirect_uri,
            code_verifier=code_verifier,
        )

        click.echo(f"\nトークンを保存しました: {manager.token_path}")
        click.echo(f"アクセストークン: {token_data['access_token'][:20]}...")

        expires_in = token_data.get("expires_in", "不明")
        click.echo(f"有効期限: {expires_in}秒")

        if token_data.get("refresh_token"):
            click.echo("リフレッシュトークン: あり（自動更新可能）")
        else:
            click.echo("リフレッシュトークン: なし（期限切れ時に再認証が必要）")

        click.echo(f"\n認証完了")

    except Exception as e:
        click.echo(f"\nエラー: {e}")
        click.echo("認証コードが正しいか確認してください。")
        sys.exit(1)


if __name__ == "__main__":
    setup_oauth()
