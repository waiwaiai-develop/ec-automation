"""CLIエントリポイント

使い方:
    python -m src.cli.main db init
    python -m src.cli.main db stats
    python -m src.cli.main netsea import -k 手ぬぐい -l 10
    python -m src.cli.main netsea categories
    python -m src.cli.main research keywords -k "japanese tenugui" --sandbox
    python -m src.cli.main product list
    python -m src.cli.main product check --id 1
    python -m src.cli.main product profit --id 1 --price 15.00
    python -m src.cli.main product describe --id 1
"""

import asyncio
import os
import sys
from pathlib import Path

import click
from dotenv import load_dotenv
from rich.console import Console
from rich.table import Table

# .envファイル読み込み
_project_root = Path(__file__).parent.parent.parent
_env_path = _project_root / "config" / ".env"
if _env_path.exists():
    load_dotenv(_env_path)

# プロジェクトルートをパスに追加（python -m 実行用）
sys.path.insert(0, str(_project_root))

from src.db.database import Database

console = Console()


# --- メイングループ ---

@click.group()
def cli():
    """EC自動化ツール — ドロップシッピング商品管理"""
    pass


# --- db コマンド ---

@cli.group()
def db():
    """データベース管理"""
    pass


@db.command("init")
def db_init():
    """テーブル作成 + シードデータ投入"""
    database = Database()
    console.print(f"[bold]DB:[/bold] {database.db_path}")

    tables = database.init_tables()
    console.print(f"[green]✓[/green] テーブル作成: {', '.join(tables)}")

    counts = database.seed_data()
    for table_name, count in counts.items():
        if count > 0:
            console.print(f"  [cyan]{table_name}[/cyan]: {count}件追加")
        else:
            console.print(f"  [dim]{table_name}: 変更なし（既存データ維持）[/dim]")

    console.print("[green]✓[/green] DB初期化完了")


@db.command("stats")
def db_stats():
    """DB統計を表示"""
    database = Database()

    if not os.path.exists(database.db_path):
        console.print("[red]DBが存在しません。先に `db init` を実行してください。[/red]")
        return

    stats = database.get_stats()

    table = Table(title="DB統計")
    table.add_column("テーブル", style="cyan")
    table.add_column("レコード数", justify="right")

    for key, value in stats.items():
        if not isinstance(value, dict):
            table.add_row(key, str(value))

    console.print(table)

    # 仕入先別・カテゴリ別の内訳
    if "products_by_supplier" in stats:
        console.print("\n[bold]商品 (仕入先別):[/bold]")
        for supplier, count in stats["products_by_supplier"].items():
            console.print(f"  {supplier}: {count}")

    if "products_by_category" in stats:
        console.print("\n[bold]商品 (カテゴリ別):[/bold]")
        for category, count in stats["products_by_category"].items():
            console.print(f"  {category}: {count}")


# --- netsea コマンド ---

@cli.group()
def netsea():
    """NETSEA商品管理"""
    pass


@netsea.command("import")
@click.option("-k", "--keyword", required=True, help="検索キーワード（例: 手ぬぐい）")
@click.option("-l", "--limit", default=20, help="取得件数（デフォルト: 20）")
@click.option("--dry-run", is_flag=True, help="DBに保存せずプレビューのみ")
def netsea_import(keyword: str, limit: int, dry_run: bool):
    """NETSEA商品をインポート"""
    from src.scraper.netsea import NetseaClient

    try:
        client = NetseaClient()
    except ValueError as e:
        console.print(f"[red]エラー: {e}[/red]")
        return

    console.print(f"[bold]検索:[/bold] {keyword} (上限: {limit}件)")

    try:
        products = asyncio.run(client.search_and_map(keyword, limit=limit))
    except Exception as e:
        console.print(f"[red]API エラー: {e}[/red]")
        return

    if not products:
        console.print("[yellow]商品が見つかりませんでした。[/yellow]")
        return

    # テーブル表示
    table = Table(title=f"NETSEA検索結果: {keyword}")
    table.add_column("#", justify="right", style="dim")
    table.add_column("商品名", max_width=40)
    table.add_column("カテゴリ", style="cyan")
    table.add_column("卸値(円)", justify="right", style="green")
    table.add_column("重量(g)", justify="right")
    table.add_column("在庫", style="yellow")

    for i, product in enumerate(products, 1):
        table.add_row(
            str(i),
            (product["name_ja"][:37] + "...") if len(product["name_ja"]) > 40 else product["name_ja"],
            product.get("category") or "-",
            str(product["wholesale_price_jpy"]) if product.get("wholesale_price_jpy") else "-",
            str(product["weight_g"]) if product.get("weight_g") else "-",
            product.get("stock_status", "-"),
        )

    console.print(table)

    if dry_run:
        console.print(f"[dim]（dry-run: DB保存スキップ）[/dim]")
        return

    # DB保存
    database = Database()
    database.init_tables()
    saved = 0
    for product in products:
        try:
            database.upsert_product(product)
            saved += 1
        except Exception as e:
            console.print(f"[red]保存エラー ({product['name_ja'][:20]}): {e}[/red]")

    console.print(f"[green]✓[/green] {saved}/{len(products)}件をDBに保存しました。")


@netsea.command("categories")
def netsea_categories():
    """NETSEAカテゴリ一覧を取得"""
    from src.scraper.netsea import NetseaClient

    try:
        client = NetseaClient()
    except ValueError as e:
        console.print(f"[red]エラー: {e}[/red]")
        return

    try:
        categories = asyncio.run(client.get_categories())
    except Exception as e:
        console.print(f"[red]API エラー: {e}[/red]")
        return

    if not categories:
        console.print("[yellow]カテゴリが取得できませんでした。[/yellow]")
        return

    table = Table(title="NETSEAカテゴリ")
    table.add_column("ID", justify="right")
    table.add_column("名前")

    for cat in categories:
        cat_id = str(cat.get("id", cat.get("category_id", "-")))
        cat_name = cat.get("name", cat.get("category_name", "-"))
        table.add_row(cat_id, cat_name)

    console.print(table)


# --- research コマンド ---

@cli.group()
def research():
    """マーケットリサーチ"""
    pass


@research.command("keywords")
@click.option("-k", "--keyword", required=True, help="検索キーワード（英語推奨）")
@click.option("-l", "--limit", default=50, help="分析サンプル数（デフォルト: 50）")
@click.option("--sandbox/--production", default=True, help="sandbox/本番切替")
@click.option("--save/--no-save", default=True, help="結果をDBに保存するか")
def research_keywords(keyword: str, limit: int, sandbox: bool, save: bool):
    """eBayキーワードリサーチ（価格・競合分析）"""
    from src.research.ebay_browse import EbayBrowseClient

    env_label = "sandbox" if sandbox else "production"
    console.print(f"[bold]キーワードリサーチ:[/bold] {keyword} ({env_label})")

    try:
        client = EbayBrowseClient(sandbox=sandbox)
    except ValueError as e:
        console.print(f"[red]エラー: {e}[/red]")
        return

    try:
        result = asyncio.run(client.keyword_research(keyword, limit=limit))
    except Exception as e:
        console.print(f"[red]API エラー: {e}[/red]")
        return

    # 統計表示
    stats_table = Table(title=f"マーケット概要: {keyword}")
    stats_table.add_column("指標", style="cyan")
    stats_table.add_column("値", justify="right")

    stats_table.add_row("検索結果数", f"{result.get('total_results', 0):,}")
    stats_table.add_row("サンプル数", str(result.get("sample_size", 0)))
    stats_table.add_row(
        "平均価格",
        f"${result['avg_price_usd']:.2f}" if result.get("avg_price_usd") else "-",
    )
    stats_table.add_row(
        "最低価格",
        f"${result['min_price_usd']:.2f}" if result.get("min_price_usd") else "-",
    )
    stats_table.add_row(
        "最高価格",
        f"${result['max_price_usd']:.2f}" if result.get("max_price_usd") else "-",
    )
    stats_table.add_row(
        "中央値",
        f"${result['median_price_usd']:.2f}" if result.get("median_price_usd") else "-",
    )
    stats_table.add_row(
        "平均送料",
        f"${result['avg_shipping_usd']:.2f}" if result.get("avg_shipping_usd") else "-",
    )

    console.print(stats_table)

    # 上位商品
    top_items = result.get("top_items", [])
    if top_items:
        items_table = Table(title="上位商品（Top 10）")
        items_table.add_column("#", justify="right", style="dim")
        items_table.add_column("タイトル", max_width=50)
        items_table.add_column("価格", justify="right", style="green")
        items_table.add_column("送料", justify="right")
        items_table.add_column("セラー", style="cyan")

        for i, item in enumerate(top_items, 1):
            price = f"${float(item['price']):.2f}" if item.get("price") else "-"
            shipping = f"${float(item['shipping']):.2f}" if item.get("shipping") else "-"
            title = item.get("title", "")
            title_display = (title[:47] + "...") if len(title) > 50 else title
            items_table.add_row(
                str(i), title_display, price, shipping, item.get("seller", "-")
            )

        console.print(items_table)

    # DB保存
    if save and result.get("sample_size", 0) > 0:
        database = Database()
        database.init_tables()
        database.insert_market_data({
            "keyword": keyword,
            "total_results": result.get("total_results"),
            "avg_price_usd": result.get("avg_price_usd"),
            "min_price_usd": result.get("min_price_usd"),
            "max_price_usd": result.get("max_price_usd"),
            "median_price_usd": result.get("median_price_usd"),
            "avg_shipping_usd": result.get("avg_shipping_usd"),
            "sample_size": result.get("sample_size"),
        })
        console.print("[green]✓[/green] リサーチ結果をDBに保存しました。")


# --- product コマンド ---

@cli.group()
def product():
    """商品管理（BANチェック・利益計算・AI説明生成）"""
    pass


@product.command("list")
@click.option("-c", "--category", default=None, help="カテゴリで絞り込み")
@click.option("-l", "--limit", default=20, help="表示件数（デフォルト: 20）")
def product_list(category, limit):
    """商品一覧を表示"""
    database = Database()

    if not os.path.exists(database.db_path):
        console.print("[red]DBが存在しません。先に `db init` を実行してください。[/red]")
        return

    products = database.get_products(category=category, limit=limit)
    if not products:
        console.print("[yellow]商品がありません。`netsea import` で取得してください。[/yellow]")
        return

    table = Table(title="商品一覧")
    table.add_column("ID", justify="right", style="dim")
    table.add_column("商品名", max_width=40)
    table.add_column("カテゴリ", style="cyan")
    table.add_column("卸値(円)", justify="right", style="green")
    table.add_column("重量(g)", justify="right")
    table.add_column("在庫", style="yellow")

    for p in products:
        name = p["name_ja"]
        name_display = (name[:37] + "...") if len(name) > 40 else name
        table.add_row(
            str(p["id"]),
            name_display,
            p.get("category") or "-",
            str(p["wholesale_price_jpy"]) if p.get("wholesale_price_jpy") else "-",
            str(p["weight_g"]) if p.get("weight_g") else "-",
            p.get("stock_status", "-"),
        )

    console.print(table)
    console.print("[dim]{} 件表示[/dim]".format(len(products)))


@product.command("check")
@click.option("--id", "product_id", type=int, default=None, help="商品ID")
@click.option("--all", "check_all", is_flag=True, help="全商品チェック")
def product_check(product_id, check_all):
    """BANリスクチェック"""
    from src.ai.ban_filter import check_ban_risk

    database = Database()

    if not product_id and not check_all:
        console.print("[red]--id または --all を指定してください。[/red]")
        return

    if product_id:
        products_to_check = [database.get_product(product_id)]
        if products_to_check[0] is None:
            console.print("[red]商品ID {} が見つかりません。[/red]".format(product_id))
            return
    else:
        products_to_check = database.get_products(limit=1000)
        if not products_to_check:
            console.print("[yellow]商品がありません。[/yellow]")
            return

    safe_count = 0
    for p in products_to_check:
        result = check_ban_risk(p, database)

        if result["safe"]:
            safe_count += 1
            if not check_all:
                console.print("[green]SAFE[/green] — {}".format(p["name_ja"][:50]))
                if result["excluded_countries"]:
                    console.print("  配送除外国: {}".format(
                        ", ".join(result["excluded_countries"])
                    ))
        else:
            console.print("[red]RISK ({})[/red] — {}".format(
                result["risk_level"].upper(), p["name_ja"][:50]
            ))
            for issue in result["issues"]:
                console.print("  [yellow]- {}[/yellow]".format(issue["detail"]))
            if result["excluded_countries"]:
                console.print("  配送除外国: {}".format(
                    ", ".join(result["excluded_countries"])
                ))

    if check_all:
        total = len(products_to_check)
        console.print("\n[bold]結果:[/bold] {}/{} 件 SAFE".format(safe_count, total))


@product.command("profit")
@click.option("--id", "product_id", type=int, required=True, help="商品ID")
@click.option("--price", "sale_price", type=float, required=True, help="販売価格（USD）")
def product_profit(product_id, sale_price):
    """利益計算"""
    from src.ai.profit_calculator import calculate_profit, suggest_price

    database = Database()
    p = database.get_product(product_id)
    if not p:
        console.print("[red]商品ID {} が見つかりません。[/red]".format(product_id))
        return

    if not p.get("wholesale_price_jpy"):
        console.print("[red]卸値が設定されていません。[/red]")
        return

    console.print("[bold]商品:[/bold] {}".format(p["name_ja"][:50]))

    result = calculate_profit(
        wholesale_jpy=p["wholesale_price_jpy"],
        sale_usd=sale_price,
        weight_g=p.get("weight_g"),
    )

    # 結果表示
    table = Table(title="利益計算 (${:.2f} 販売時)".format(sale_price))
    table.add_column("項目", style="cyan")
    table.add_column("金額", justify="right")

    table.add_row("販売価格", "${:.2f}".format(result["sale_usd"]))
    table.add_row(
        "仕入原価",
        "${:.2f} ({:,}円)".format(result["wholesale_usd"], result["wholesale_jpy"]),
    )
    table.add_row(
        "国際送料 ({})".format(result["shipping"]["method"]),
        "${:.2f}".format(result["shipping_usd"]),
    )
    table.add_row("eBay FVF (13.25%)", "${:.2f}".format(result["ebay_fvf_usd"]))
    table.add_row("決済手数料", "${:.2f}".format(result["ebay_payment_usd"]))
    table.add_row("[bold]合計コスト[/bold]", "[bold]${:.2f}[/bold]".format(result["total_cost_usd"]))
    table.add_row("[bold]利益[/bold]", "[bold]${:.2f}[/bold]".format(result["profit_usd"]))

    margin_pct = result["profit_margin"] * 100
    margin_style = "green" if result["profitable"] else "red"
    table.add_row(
        "[bold]利益率[/bold]",
        "[{style}]{pct:.1f}%[/{style}]".format(style=margin_style, pct=margin_pct),
    )

    console.print(table)

    if not result["profitable"]:
        console.print("[red]利益率が25%未満です。出品非推奨。[/red]")
        # 推奨価格を提示
        suggestion = suggest_price(
            wholesale_jpy=p["wholesale_price_jpy"],
            weight_g=p.get("weight_g"),
        )
        if suggestion.get("suggested_price_usd"):
            console.print(
                "[yellow]推奨価格（30%利益率）: ${:.2f}[/yellow]".format(
                    suggestion["suggested_price_usd"]
                )
            )


@product.command("describe")
@click.option("--id", "product_id", type=int, required=True, help="商品ID")
@click.option("--model", "model_name", default=None, help="AIモデル（デフォルト: claude-sonnet-4-6）")
@click.option("--save/--no-save", default=False, help="結果をDBに保存")
def product_describe(product_id, model_name, save):
    """AI商品説明生成（ANTHROPIC_API_KEY必要）"""
    from src.ai.description_generator import generate_full_listing

    database = Database()
    p = database.get_product(product_id)
    if not p:
        console.print("[red]商品ID {} が見つかりません。[/red]".format(product_id))
        return

    console.print("[bold]商品:[/bold] {}".format(p["name_ja"][:50]))
    console.print("[dim]AI生成中...[/dim]")

    try:
        result = generate_full_listing(p, model=model_name)
    except ValueError as e:
        console.print("[red]エラー: {}[/red]".format(e))
        return
    except Exception as e:
        console.print("[red]API エラー: {}[/red]".format(e))
        return

    # タイトル
    console.print("\n[bold cyan]Title:[/bold cyan]")
    console.print(result.get("title", "（生成失敗）"))

    # 説明文
    console.print("\n[bold cyan]Description:[/bold cyan]")
    console.print(result.get("description", "（生成失敗）"))

    # Item Specifics
    specifics = result.get("item_specifics", {})
    if specifics:
        console.print("\n[bold cyan]Item Specifics:[/bold cyan]")
        for key, val in specifics.items():
            console.print("  {}: {}".format(key, val))

    # SEOタグ
    tags = result.get("tags", [])
    if tags:
        console.print("\n[bold cyan]SEO Tags ({}):[/bold cyan]".format(len(tags)))
        console.print(", ".join(tags))

    # DB保存
    if save:
        with database.connect() as conn:
            conn.execute(
                """UPDATE products
                   SET name_en = ?, description_en = ?, updated_at = datetime('now')
                   WHERE id = ?""",
                (result.get("title"), result.get("description"), product_id),
            )
        console.print("\n[green]DB に保存しました。[/green]")

    console.print("\n[green]完了[/green]")


# --- エントリポイント ---

def main():
    cli()


if __name__ == "__main__":
    main()
