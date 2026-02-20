"""CLIエントリポイント

使い方:
    python -m src.cli.main db init
    python -m src.cli.main db stats
    python -m src.cli.main netsea import -k 手ぬぐい -l 10
    python -m src.cli.main netsea categories
    python -m src.cli.main research keywords -k "japanese tenugui" --sandbox
    python -m src.cli.main product list
    python -m src.cli.main product check --id 1
    python -m src.cli.main product profit --id 1 --price 15.00 [--platform etsy]
    python -m src.cli.main product describe --id 1
    python -m src.cli.main platform list-ebay --id 1 --price 18.00
    python -m src.cli.main platform list-etsy --id 1 --price 18.00
    python -m src.cli.main platform listings [--platform ebay]
    python -m src.cli.main sync inventory
    python -m src.cli.main sync orders
    python -m src.cli.main notify test
    python -m src.cli.main notify daily
    python -m src.cli.main auth setup --platform ebay [--sandbox]
    python -m src.cli.main auth status --platform ebay
    python -m src.cli.main dashboard update
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
@click.option("--platform", "platform_name", default="ebay",
              type=click.Choice(["ebay", "etsy"]), help="プラットフォーム（デフォルト: ebay）")
def product_profit(product_id, sale_price, platform_name):
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
        platform=platform_name,
    )

    # 結果表示
    table = Table(title="利益計算 (${:.2f} 販売時 / {})".format(sale_price, platform_name))
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
    table.add_row("プラットフォーム手数料", "${:.2f}".format(result["platform_fees_usd"]))
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
        suggestion = suggest_price(
            wholesale_jpy=p["wholesale_price_jpy"],
            weight_g=p.get("weight_g"),
            platform=platform_name,
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


# --- platform コマンド ---

@cli.group()
def platform():
    """プラットフォーム出品管理（eBay/Etsy/BASE）"""
    pass


@platform.command("list-ebay")
@click.option("--id", "product_id", type=int, required=True, help="商品ID")
@click.option("--price", "price_usd", type=float, required=True, help="販売価格（USD）")
@click.option("--category-id", default=None, help="eBayカテゴリID")
@click.option("--sandbox/--production", default=True, help="sandbox/本番切替")
def platform_list_ebay(product_id, price_usd, category_id, sandbox):
    """eBayに出品"""
    from src.ai.ban_filter import check_ban_risk
    from src.ai.description_generator import generate_full_listing
    from src.platforms.ebay import EbayClient

    database = Database()
    p = database.get_product(product_id)
    if not p:
        console.print("[red]商品ID {} が見つかりません。[/red]".format(product_id))
        return

    # BANチェック
    ban_result = check_ban_risk(p, database)
    if not ban_result["safe"]:
        console.print("[red]BANリスクあり。出品中止。[/red]")
        for issue in ban_result["issues"]:
            console.print("  [yellow]- {}[/yellow]".format(issue["detail"]))
        return

    console.print("[bold]商品:[/bold] {}".format(p["name_ja"][:50]))

    # AI説明生成
    console.print("[dim]AI説明生成中...[/dim]")
    try:
        listing_content = generate_full_listing(p)
    except Exception as e:
        console.print("[red]AI生成エラー: {}[/red]".format(e))
        return

    listing_data = {
        "title_en": listing_content.get("title", ""),
        "description_en": listing_content.get("description", ""),
        "price_usd": price_usd,
        "tags": listing_content.get("tags", []),
        "category_id": category_id,
        "excluded_countries": ban_result.get("excluded_countries", []),
    }

    # 出品
    console.print("[dim]eBay出品中...[/dim]")
    try:
        client = EbayClient(sandbox=sandbox)
        result = client.create_listing(p, listing_data)
    except Exception as e:
        console.print("[red]出品エラー: {}[/red]".format(e))
        return

    # DB記録
    from src.ai.profit_calculator import estimate_shipping
    shipping = estimate_shipping(p.get("weight_g"))
    database.create_listing({
        "product_id": product_id,
        "platform": "ebay",
        "platform_listing_id": result["platform_listing_id"],
        "title_en": listing_data["title_en"],
        "description_en": listing_data["description_en"],
        "tags": listing_data["tags"],
        "price_usd": price_usd,
        "shipping_cost_usd": shipping["cost_usd"],
        "status": result["status"],
        "ban_check_passed": True,
        "excluded_countries": listing_data["excluded_countries"],
    })

    console.print("[green]出品完了[/green]")
    console.print("  Listing ID: {}".format(result["platform_listing_id"]))
    console.print("  URL: {}".format(result.get("url", "")))


@platform.command("list-etsy")
@click.option("--id", "product_id", type=int, required=True, help="商品ID")
@click.option("--price", "price_usd", type=float, required=True, help="販売価格（USD）")
@click.option("--taxonomy-id", type=int, default=None, help="EtsyタクソノミーID")
def platform_list_etsy(product_id, price_usd, taxonomy_id):
    """Etsyに出品"""
    from src.ai.ban_filter import check_ban_risk
    from src.ai.description_generator import generate_full_listing
    from src.platforms.etsy import EtsyClient

    database = Database()
    p = database.get_product(product_id)
    if not p:
        console.print("[red]商品ID {} が見つかりません。[/red]".format(product_id))
        return

    # BANチェック
    ban_result = check_ban_risk(p, database)
    if not ban_result["safe"]:
        console.print("[red]BANリスクあり。出品中止。[/red]")
        for issue in ban_result["issues"]:
            console.print("  [yellow]- {}[/yellow]".format(issue["detail"]))
        return

    console.print("[bold]商品:[/bold] {}".format(p["name_ja"][:50]))

    # AI説明生成
    console.print("[dim]AI説明生成中...[/dim]")
    try:
        listing_content = generate_full_listing(p)
    except Exception as e:
        console.print("[red]AI生成エラー: {}[/red]".format(e))
        return

    listing_data = {
        "title_en": listing_content.get("title", ""),
        "description_en": listing_content.get("description", ""),
        "price_usd": price_usd,
        "tags": listing_content.get("tags", []),
        "taxonomy_id": taxonomy_id,
    }

    # 出品
    console.print("[dim]Etsy出品中...[/dim]")
    try:
        client = EtsyClient()
        result = client.create_listing(p, listing_data)
    except Exception as e:
        console.print("[red]出品エラー: {}[/red]".format(e))
        return

    # DB記録
    from src.ai.profit_calculator import estimate_shipping
    shipping = estimate_shipping(p.get("weight_g"))
    database.create_listing({
        "product_id": product_id,
        "platform": "etsy",
        "platform_listing_id": result["platform_listing_id"],
        "title_en": listing_data["title_en"],
        "description_en": listing_data["description_en"],
        "tags": listing_data["tags"],
        "price_usd": price_usd,
        "shipping_cost_usd": shipping["cost_usd"],
        "status": result["status"],
        "ban_check_passed": True,
    })

    console.print("[green]出品完了[/green]")
    console.print("  Listing ID: {}".format(result["platform_listing_id"]))
    console.print("  URL: {}".format(result.get("url", "")))


@platform.command("listings")
@click.option("-p", "--platform", "platform_name", default=None,
              type=click.Choice(["ebay", "etsy", "base"]), help="プラットフォーム絞り込み")
@click.option("-s", "--status", default=None, help="ステータス絞り込み")
@click.option("-l", "--limit", default=20, help="表示件数")
def platform_listings(platform_name, status, limit):
    """リスティング一覧を表示"""
    database = Database()

    listings = database.get_listings(
        platform=platform_name, status=status, limit=limit
    )
    if not listings:
        console.print("[yellow]リスティングがありません。[/yellow]")
        return

    table = Table(title="リスティング一覧")
    table.add_column("ID", justify="right", style="dim")
    table.add_column("商品ID", justify="right")
    table.add_column("PF", style="cyan")
    table.add_column("タイトル", max_width=35)
    table.add_column("価格($)", justify="right", style="green")
    table.add_column("状態", style="yellow")
    table.add_column("売上", justify="right")

    for l in listings:
        title = (l.get("title_en") or "")
        title_display = (title[:32] + "...") if len(title) > 35 else title
        table.add_row(
            str(l["id"]),
            str(l.get("product_id", "")),
            l["platform"],
            title_display,
            "${:.2f}".format(l["price_usd"]) if l.get("price_usd") else "-",
            l.get("status", "-"),
            str(l.get("sales", 0)),
        )

    console.print(table)
    console.print("[dim]{} 件表示[/dim]".format(len(listings)))


# --- sync コマンド ---

@cli.group()
def sync():
    """在庫同期・注文処理"""
    pass


@sync.command("inventory")
@click.option("-p", "--platform", "platform_name", default=None,
              type=click.Choice(["ebay", "etsy", "base"]), help="プラットフォーム指定")
def sync_inventory(platform_name):
    """在庫同期を実行"""
    from src.sync.inventory_sync import InventorySyncEngine

    database = Database()

    # プラットフォームクライアント初期化
    clients = _init_platform_clients()
    if not clients:
        console.print("[red]利用可能なプラットフォームがありません。[/red]")
        return

    # 通知
    notifier = _init_notifier()

    engine = InventorySyncEngine(database, clients, notifier)

    console.print("[bold]在庫同期実行中...[/bold]")
    try:
        results = engine.sync(platform=platform_name)
    except Exception as e:
        console.print("[red]同期エラー: {}[/red]".format(e))
        return

    console.print("[green]同期完了[/green]")
    console.print("  チェック: {}件".format(results["items_checked"]))
    console.print("  変更: {}件".format(results["items_changed"]))

    if results["deactivated"]:
        console.print("  非公開化: {}件".format(len(results["deactivated"])))
    if results["reactivated"]:
        console.print("  再公開: {}件".format(len(results["reactivated"])))
    if results["errors"]:
        console.print("  [red]エラー: {}件[/red]".format(len(results["errors"])))


@sync.command("orders")
@click.option("-p", "--platform", "platform_name", default=None,
              type=click.Choice(["ebay", "etsy", "base"]), help="プラットフォーム指定")
def sync_orders(platform_name):
    """注文を取得・処理"""
    from src.sync.order_processor import OrderProcessor

    database = Database()

    clients = _init_platform_clients()
    if not clients:
        console.print("[red]利用可能なプラットフォームがありません。[/red]")
        return

    notifier = _init_notifier()

    processor = OrderProcessor(database, clients, notifier)

    console.print("[bold]注文処理実行中...[/bold]")
    try:
        results = processor.process(platform=platform_name)
    except Exception as e:
        console.print("[red]注文処理エラー: {}[/red]".format(e))
        return

    console.print("[green]注文処理完了[/green]")
    console.print("  新規注文: {}件".format(results["new_orders"]))
    console.print("  売上: ${:.2f}".format(results["total_revenue_usd"]))
    console.print("  利益: ${:.2f}".format(results["total_profit_usd"]))
    if results["errors"]:
        console.print("  [red]エラー: {}件[/red]".format(len(results["errors"])))


# --- notify コマンド ---

@cli.group()
def notify():
    """通知管理（LINE Notify）"""
    pass


@notify.command("test")
def notify_test():
    """LINE Notifyテスト通知"""
    from src.notifications.line import LineNotifier

    try:
        notifier = LineNotifier()
    except ValueError as e:
        console.print("[red]エラー: {}[/red]".format(e))
        return

    result = notifier._send("\n[テスト] EC自動化システムからの通知テストです。")
    if result["success"]:
        console.print("[green]テスト通知を送信しました。[/green]")
    else:
        console.print("[red]通知失敗 (status={})[/red]".format(result["status"]))


@notify.command("daily")
def notify_daily():
    """日次サマリー通知"""
    from src.notifications.line import LineNotifier

    database = Database()

    try:
        notifier = LineNotifier()
    except ValueError as e:
        console.print("[red]エラー: {}[/red]".format(e))
        return

    summary = database.get_daily_summary()
    result = notifier.notify_daily_summary(summary)

    if result["success"]:
        console.print("[green]日次サマリーを送信しました。[/green]")
        console.print("  注文: {}件 / 売上: ${:.2f} / 利益: ${:.2f}".format(
            summary["orders_count"], summary["revenue_usd"], summary["profit_usd"]
        ))
    else:
        console.print("[red]通知失敗 (status={})[/red]".format(result["status"]))


# --- auth コマンド ---

@cli.group()
def auth():
    """OAuth認証管理"""
    pass


@auth.command("setup")
@click.option("--platform", "platform_name", required=True,
              type=click.Choice(["ebay", "etsy", "base"]), help="プラットフォーム")
@click.option("--sandbox", is_flag=True, help="sandbox環境（eBayのみ）")
def auth_setup(platform_name, sandbox):
    """OAuth認証セットアップ（ブラウザ認証）"""
    console.print("OAuth認証は専用スクリプトで実行してください:")
    cmd = "python scripts/oauth_setup.py --platform {}".format(platform_name)
    if sandbox:
        cmd += " --sandbox"
    console.print("[cyan]{}[/cyan]".format(cmd))


@auth.command("status")
@click.option("--platform", "platform_name", required=True,
              type=click.Choice(["ebay", "etsy", "base"]), help="プラットフォーム")
def auth_status(platform_name):
    """トークン状態を確認"""
    from src.auth.oauth_manager import OAuthTokenManager

    manager = OAuthTokenManager(platform_name)
    token_data = manager.load_token()

    if not token_data:
        console.print("[red]{}のトークンが未設定です。[/red]".format(platform_name))
        return

    expired = manager.is_token_expired(token_data)

    table = Table(title="{}トークン状態".format(platform_name.upper()))
    table.add_column("項目", style="cyan")
    table.add_column("値")

    table.add_row("ファイル", str(manager.token_path))
    table.add_row("状態", "[red]期限切れ[/red]" if expired else "[green]有効[/green]")
    table.add_row("リフレッシュ", "あり" if token_data.get("refresh_token") else "なし")

    import time
    expires_at = token_data.get("expires_at", 0)
    if expires_at:
        from datetime import datetime
        expires_dt = datetime.fromtimestamp(expires_at)
        table.add_row("有効期限", expires_dt.strftime("%Y-%m-%d %H:%M:%S"))

    saved_at = token_data.get("saved_at", 0)
    if saved_at:
        from datetime import datetime
        saved_dt = datetime.fromtimestamp(saved_at)
        table.add_row("保存日時", saved_dt.strftime("%Y-%m-%d %H:%M:%S"))

    console.print(table)


# --- dashboard コマンド ---

@cli.group()
def dashboard():
    """ダッシュボード管理（Google Sheets）"""
    pass


@dashboard.command("update")
@click.option("--sheet", default="all",
              type=click.Choice(["all", "daily", "listings", "orders", "inventory"]),
              help="更新するシート")
def dashboard_update(sheet):
    """Google Sheetsダッシュボードを更新"""
    from src.dashboard.sheets import SheetsDashboard

    database = Database()

    try:
        dash = SheetsDashboard()
    except Exception as e:
        console.print("[red]エラー: {}[/red]".format(e))
        return

    console.print("[bold]ダッシュボード更新中...[/bold]")

    try:
        if sheet == "all":
            results = dash.update_all(database)
            for name, result in results.items():
                if result.get("success"):
                    console.print("[green]  {} 更新完了[/green]".format(name))
        elif sheet == "daily":
            dash.update_daily_report(database)
        elif sheet == "listings":
            dash.update_listings(database)
        elif sheet == "orders":
            dash.update_orders(database)
        elif sheet == "inventory":
            dash.update_inventory(database)

        console.print("[green]ダッシュボード更新完了[/green]")

    except Exception as e:
        console.print("[red]更新エラー: {}[/red]".format(e))


# --- ヘルパー関数 ---

def _init_platform_clients():
    """利用可能なプラットフォームクライアントを初期化"""
    clients = {}

    try:
        from src.platforms.ebay import EbayClient
        clients["ebay"] = EbayClient(sandbox=False)
    except Exception:
        pass

    try:
        from src.platforms.etsy import EtsyClient
        clients["etsy"] = EtsyClient()
    except Exception:
        pass

    try:
        from src.platforms.base_shop import BaseShopClient
        clients["base"] = BaseShopClient()
    except Exception:
        pass

    return clients


def _init_notifier():
    """LINE Notifier を初期化（失敗時はNone）"""
    try:
        from src.notifications.line import LineNotifier
        return LineNotifier()
    except (ValueError, Exception):
        return None


# --- エントリポイント ---

def main():
    cli()


if __name__ == "__main__":
    main()
