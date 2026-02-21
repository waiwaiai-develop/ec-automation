"""Webダッシュボード（Flask + Bootstrap 5）

ブラウザでDB内容を閲覧するための軽量Web UI。
起動: python -m src.cli.main web --port 5000
"""

import json
import os
from pathlib import Path
from typing import Optional

from flask import Flask, render_template, request

from src.db.database import Database


def create_app(db_path=None):
    # type: (Optional[str]) -> Flask
    """Flaskアプリファクトリ"""
    template_dir = os.path.join(os.path.dirname(__file__), "templates")
    app = Flask(__name__, template_folder=template_dir)

    # データベース初期化
    db = Database(db_path=db_path)

    def parse_image_urls(raw):
        # type: (Optional[str]) -> list
        """image_urls文字列をリストにパース"""
        if not raw:
            return []
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, list):
                return parsed
        except (json.JSONDecodeError, TypeError):
            pass
        return []

    # テンプレートフィルター登録
    @app.template_filter("format_price")
    def format_price(value, currency="JPY"):
        """価格フォーマット"""
        if value is None:
            return "-"
        if currency == "USD":
            return "${:,.2f}".format(float(value))
        return "{:,}".format(int(value))

    @app.template_filter("parse_images")
    def parse_images_filter(raw):
        """テンプレート内でimage_urlsをパース"""
        return parse_image_urls(raw)

    # --- ルート定義 ---

    @app.route("/")
    def index():
        """ダッシュボード: DB統計サマリー"""
        stats = db.get_stats()
        daily = db.get_daily_summary()
        return render_template("index.html", stats=stats, daily=daily)

    @app.route("/products")
    def products():
        """商品一覧（フィルター付き）"""
        category = request.args.get("category", "").strip() or None
        stock_status = request.args.get("stock_status", "").strip() or None
        limit = request.args.get("limit", "100", type=str)
        try:
            limit_int = int(limit)
        except ValueError:
            limit_int = 100

        # カテゴリ一覧を取得（フィルターセレクトボックス用）
        categories = []
        try:
            with db.connect() as conn:
                rows = conn.execute(
                    "SELECT DISTINCT category FROM products WHERE category IS NOT NULL ORDER BY category"
                ).fetchall()
                categories = [row["category"] for row in rows]
        except Exception:
            pass

        # DS対応のみフィルター
        ds_only = request.args.get("ds_only", "").strip()

        # stock_statusフィルターはget_productsに無いので直接クエリ
        query = "SELECT * FROM products WHERE 1=1"
        params = []
        if category:
            query += " AND category = ?"
            params.append(category)
        if stock_status:
            query += " AND stock_status = ?"
            params.append(stock_status)
        if ds_only == "1":
            query += (" AND direct_send_flag = 'Y'"
                      " AND image_copy_flag = 'Y'"
                      " AND deal_net_shop_flag = 'Y'")
        query += " ORDER BY updated_at DESC LIMIT ?"
        params.append(limit_int)

        with db.connect() as conn:
            rows = conn.execute(query, params).fetchall()
            product_list = [dict(row) for row in rows]

        return render_template(
            "products.html",
            products=product_list,
            categories=categories,
            current_category=category or "",
            current_stock=stock_status or "",
            current_ds_only=ds_only,
            current_limit=limit_int,
        )

    @app.route("/products/<int:product_id>")
    def product_detail(product_id):
        """商品詳細"""
        product = db.get_product(product_id)
        if not product:
            return render_template("404.html", message="商品ID {} が見つかりません".format(product_id)), 404

        # 画像URLをパース
        images = parse_image_urls(product.get("image_urls"))

        # 利益計算（簡易版）
        profit_info = None
        wholesale = product.get("wholesale_price_jpy")
        if wholesale:
            try:
                from src.ai.profit_calculator import calculate_profit
                # $15, $20, $25 の3パターン
                profit_info = []
                for price in [15.0, 20.0, 25.0, 30.0]:
                    calc = calculate_profit(
                        wholesale_jpy=wholesale,
                        sale_usd=price,
                        weight_g=product.get("weight_g"),
                        platform="ebay",
                    )
                    profit_info.append(calc)
            except Exception:
                pass

        # 関連リスティング
        listings = db.get_listings(product_id=product_id)

        return render_template(
            "product_detail.html",
            product=product,
            images=images,
            profit_info=profit_info,
            listings=listings,
        )

    @app.route("/listings")
    def listings():
        """出品一覧"""
        platform = request.args.get("platform", "").strip() or None
        status = request.args.get("status", "").strip() or None
        limit = request.args.get("limit", "100", type=str)
        try:
            limit_int = int(limit)
        except ValueError:
            limit_int = 100

        listing_list = db.get_listings(
            platform=platform, status=status, limit=limit_int
        )

        return render_template(
            "listings.html",
            listings=listing_list,
            current_platform=platform or "",
            current_status=status or "",
        )

    @app.route("/orders")
    def orders():
        """注文一覧"""
        platform = request.args.get("platform", "").strip() or None
        status = request.args.get("status", "").strip() or None
        limit = request.args.get("limit", "100", type=str)
        try:
            limit_int = int(limit)
        except ValueError:
            limit_int = 100

        order_list = db.get_orders(
            platform=platform, status=status, limit=limit_int
        )

        return render_template(
            "orders.html",
            orders=order_list,
            current_platform=platform or "",
            current_status=status or "",
        )

    return app
