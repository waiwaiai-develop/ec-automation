"""Webダッシュボード（Flask + React SPA / Bootstrap 5）

ブラウザでDB内容を閲覧・操作するためのWeb UI。
起動: python -m src.cli.main web --port 8080
- React SPA: /app 以下で frontend/dist/ を配信
- レガシーUI: / 以下で Jinja2 テンプレートを配信
- JSON API: /api/* でフロントエンドにデータを提供
"""

import json
import os
import re
import traceback
from pathlib import Path
from typing import Optional

from flask import Flask, jsonify, render_template, request, send_from_directory

from src.db.database import Database


def create_app(db_path=None):
    # type: (Optional[str]) -> Flask
    """Flaskアプリファクトリ"""
    template_dir = os.path.join(os.path.dirname(__file__), "templates")
    # frontend/dist/ のパスを解決
    project_root = Path(__file__).parent.parent.parent
    frontend_dist = str(project_root / "frontend" / "dist")
    app = Flask(__name__, template_folder=template_dir,
                static_folder=None)  # 静的ファイルはSPA用に別途設定

    # データベース初期化
    db = Database(db_path=db_path)

    # --- 開発用CORS ---
    @app.after_request
    def add_cors_headers(response):
        """開発時のみ Vite dev server からのリクエストを許可"""
        if app.debug:
            origin = request.headers.get("Origin", "")
            if origin in ("http://localhost:5173", "http://127.0.0.1:5173"):
                response.headers["Access-Control-Allow-Origin"] = origin
                response.headers["Access-Control-Allow-Headers"] = "Content-Type"
                response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
        return response

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

    # --- ページルート定義 ---

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

    # --- リサーチページルート ---

    @app.route("/research")
    def research():
        """リサーチダッシュボード"""
        return render_template("research.html")

    @app.route("/research/<int:session_id>")
    def research_detail(session_id):
        """リサーチ詳細"""
        session = db.get_research_session(session_id)
        if not session:
            return render_template(
                "404.html",
                message="リサーチID {} が見つかりません".format(session_id),
            ), 404

        # JSONカラムをパース
        top_items = []
        if session.get("top_items_json"):
            try:
                top_items = json.loads(session["top_items_json"])
            except (json.JSONDecodeError, TypeError):
                pass

        price_dist = []
        if session.get("price_dist_json"):
            try:
                price_dist = json.loads(session["price_dist_json"])
            except (json.JSONDecodeError, TypeError):
                pass

        matches = db.get_research_matches(session_id)

        return render_template(
            "research_detail.html",
            session=session,
            top_items=top_items,
            price_dist=price_dist,
            matches=matches,
        )

    # --- BASE OAuth認証 ---

    @app.route("/auth/base")
    def auth_base_start():
        """BASE OAuth認証開始 — 認証URLにリダイレクト"""
        from src.auth.oauth_manager import OAuthTokenManager
        manager = OAuthTokenManager("base")
        # コールバックURLはこのダッシュボードの/auth/base/callback
        callback_url = request.host_url.rstrip("/") + "/auth/base/callback"
        result = manager.build_auth_url(redirect_uri=callback_url)
        return render_template("auth_base.html",
                               auth_url=result["url"],
                               callback_url=callback_url)

    @app.route("/auth/base/callback")
    def auth_base_callback():
        """BASE OAuthコールバック — 認証コードをトークンに交換"""
        code = request.args.get("code", "")
        error = request.args.get("error", "")
        if error:
            return render_template("auth_base.html",
                                   error="認証エラー: {}".format(error),
                                   auth_url=None, callback_url=None)
        if not code:
            return render_template("auth_base.html",
                                   error="認証コードが取得できませんでした",
                                   auth_url=None, callback_url=None)

        try:
            from src.auth.oauth_manager import OAuthTokenManager
            manager = OAuthTokenManager("base")
            callback_url = request.host_url.rstrip("/") + "/auth/base/callback"
            token_data = manager.exchange_code(code, redirect_uri=callback_url)
            scope = token_data.get("scope", "不明")
            return render_template("auth_base.html",
                                   success=True, scope=scope,
                                   auth_url=None, callback_url=None)
        except Exception as e:
            return render_template("auth_base.html",
                                   error="トークン交換エラー: {}".format(str(e)),
                                   auth_url=None, callback_url=None)

    # --- SPA配信ルート ---

    @app.route("/app")
    @app.route("/app/<path:path>")
    def serve_spa(path=""):
        """React SPAを配信（/app 以下のすべてのパスで index.html を返す）"""
        if path and os.path.isfile(os.path.join(frontend_dist, path)):
            return send_from_directory(frontend_dist, path)
        index_path = os.path.join(frontend_dist, "index.html")
        if os.path.isfile(index_path):
            return send_from_directory(frontend_dist, "index.html")
        return "フロントエンドがビルドされていません。cd frontend && npm run build を実行してください。", 404

    # --- GET JSON API ---

    @app.route("/api/dashboard")
    def api_dashboard():
        """ダッシュボード統計データ"""
        stats = db.get_stats()
        daily = db.get_daily_summary()
        return jsonify({"stats": stats, "daily_summary": daily})

    @app.route("/api/products")
    def api_products_list():
        """商品リスト（フィルター付き）"""
        category = request.args.get("category", "").strip() or None
        stock_status = request.args.get("stock_status", "").strip() or None
        ds_only = request.args.get("ds_only", "").strip()
        limit = request.args.get("limit", "100", type=str)
        try:
            limit_int = int(limit)
        except ValueError:
            limit_int = 100

        # カテゴリ一覧
        categories = []
        try:
            with db.connect() as conn:
                rows = conn.execute(
                    "SELECT DISTINCT category FROM products WHERE category IS NOT NULL ORDER BY category"
                ).fetchall()
                categories = [row["category"] for row in rows]
        except Exception:
            pass

        # 商品クエリ
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

        return jsonify({
            "products": product_list,
            "categories": categories,
            "total": len(product_list),
        })

    @app.route("/api/products/<int:product_id>")
    def api_product_detail(product_id):
        """商品詳細（画像・利益計算・リスティング含む）"""
        product = db.get_product(product_id)
        if not product:
            return jsonify({"error": "商品ID {} が見つかりません".format(product_id)}), 404

        images = parse_image_urls(product.get("image_urls"))

        # 利益計算
        profit_info = None
        wholesale = product.get("wholesale_price_jpy")
        if wholesale:
            try:
                from src.ai.profit_calculator import calculate_profit
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

        listings = db.get_listings(product_id=product_id)

        return jsonify({
            "product": product,
            "images": images,
            "profit_info": profit_info,
            "listings": listings,
        })

    @app.route("/api/listings")
    def api_listings_list():
        """リスティング一覧"""
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
        return jsonify({"listings": listing_list, "total": len(listing_list)})

    @app.route("/api/orders")
    def api_orders_list():
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
        return jsonify({"orders": order_list, "total": len(order_list)})

    # --- POST APIエンドポイント ---

    @app.route("/api/products/import-netsea-url", methods=["POST"])
    def api_import_netsea_url():
        """NETSEA商品URLからDB登録"""
        data = request.get_json(force=True)
        url = (data.get("url") or "").strip()
        if not url:
            return jsonify({"error": "URLが空です"}), 400

        # URLからsupplier_id, product_idを抽出
        # パターン: https://www.netsea.jp/shop/{supplier_id}/{product_id}
        match = re.search(
            r"netsea\.jp/shop/(\d+)/(\d+)", url
        )
        if not match:
            return jsonify({"error": "無効なNETSEA URLです。形式: https://www.netsea.jp/shop/SUPPLIER_ID/PRODUCT_ID"}), 400

        supplier_id = match.group(1)
        target_product_id = match.group(2)

        try:
            from src.scraper.netsea import NetseaClient
            client = NetseaClient()
            items = client.get_items(supplier_ids=supplier_id)

            # 対象product_idでフィルタ
            target_item = None
            for item in items:
                pid = str(item.get("product_id", item.get("item_id", item.get("id", ""))))
                if pid == target_product_id:
                    target_item = item
                    break

            if not target_item:
                return jsonify({"error": "商品ID {} が見つかりません（サプライヤー {} の商品一覧に該当なし）".format(
                    target_product_id, supplier_id
                )}), 404

            mapped = client.map_to_db(target_item)
            product_id = db.upsert_product(mapped)

            return jsonify({
                "success": True,
                "product_id": product_id,
                "name_ja": mapped.get("name_ja", ""),
                "message": "商品を登録しました: {}".format(mapped.get("name_ja", "")),
            })
        except ValueError as e:
            return jsonify({"error": str(e)}), 400
        except Exception as e:
            return jsonify({"error": "NETSEA API エラー: {}".format(str(e))}), 500

    @app.route("/api/products/bulk-delete", methods=["POST"])
    def api_bulk_delete():
        """商品一括削除"""
        data = request.get_json(force=True)
        product_ids = data.get("product_ids", [])
        if not product_ids:
            return jsonify({"error": "product_idsが空です"}), 400

        try:
            product_ids = [int(pid) for pid in product_ids]
        except (ValueError, TypeError):
            return jsonify({"error": "product_idsは整数のリストである必要があります"}), 400

        deleted = db.delete_products(product_ids)
        return jsonify({
            "success": True,
            "deleted": deleted,
            "message": "{}件の商品を削除しました".format(deleted),
        })

    @app.route("/api/products/bulk-set-flags", methods=["POST"])
    def api_bulk_set_flags():
        """出品フラグ一括設定"""
        data = request.get_json(force=True)
        product_ids = data.get("product_ids", [])
        flags = data.get("flags", {})
        if not product_ids:
            return jsonify({"error": "product_idsが空です"}), 400
        if not flags:
            return jsonify({"error": "flagsが空です"}), 400

        try:
            product_ids = [int(pid) for pid in product_ids]
        except (ValueError, TypeError):
            return jsonify({"error": "product_idsは整数のリストである必要があります"}), 400

        updated = db.update_product_flags(product_ids, flags)
        return jsonify({
            "success": True,
            "updated": updated,
            "message": "{}件の商品のフラグを更新しました".format(updated),
        })

    @app.route("/api/products/<int:product_id>/update", methods=["POST"])
    def api_update_product(product_id):
        """商品情報更新"""
        data = request.get_json(force=True)
        if not data:
            return jsonify({"error": "更新データが空です"}), 400

        product = db.get_product(product_id)
        if not product:
            return jsonify({"error": "商品ID {} が見つかりません".format(product_id)}), 404

        success = db.update_product(product_id, data)
        if success:
            return jsonify({
                "success": True,
                "message": "商品情報を更新しました",
            })
        else:
            return jsonify({"error": "更新可能なフィールドがありません"}), 400

    @app.route("/api/products/<int:product_id>/generate", methods=["POST"])
    def api_generate_listing(product_id):
        """AI商品説明生成"""
        product = db.get_product(product_id)
        if not product:
            return jsonify({"error": "商品ID {} が見つかりません".format(product_id)}), 404

        try:
            from src.ai.description_generator import generate_full_listing
            result = generate_full_listing(product)
            return jsonify({
                "success": True,
                "title": result.get("title", ""),
                "description": result.get("description", ""),
                "tags": result.get("tags", []),
                "item_specifics": result.get("item_specifics", {}),
            })
        except Exception as e:
            return jsonify({"error": "AI生成エラー: {}".format(str(e))}), 500

    @app.route("/api/products/<int:product_id>/generate-ja", methods=["POST"])
    def api_generate_listing_ja(product_id):
        """AI日本語商品説明生成（BASE向け）"""
        product = db.get_product(product_id)
        if not product:
            return jsonify({"error": "商品ID {} が見つかりません".format(product_id)}), 404

        try:
            from src.ai.description_generator import generate_description_ja
            result = generate_description_ja(product)
            return jsonify({
                "success": True,
                "title_ja": result.get("title_ja", ""),
                "description_ja": result.get("description_ja", ""),
            })
        except Exception as e:
            return jsonify({"error": "AI生成エラー: {}".format(str(e))}), 500

    @app.route("/api/products/<int:product_id>/ban-check", methods=["POST"])
    def api_ban_check(product_id):
        """BANチェック"""
        product = db.get_product(product_id)
        if not product:
            return jsonify({"error": "商品ID {} が見つかりません".format(product_id)}), 404

        issues = []

        # ブランドブラックリストチェック
        text = "{} {} {}".format(
            product.get("name_ja", ""),
            product.get("name_en", "") or "",
            product.get("description_en", "") or "",
        )
        brand_matches = db.is_brand_blacklisted(text)
        if brand_matches:
            for m in brand_matches:
                issues.append("VeRO警告: {} ({})".format(m["brand_name"], m["risk_level"]))

        # 配送制限チェック
        category = product.get("category")
        excluded_countries = []
        if category:
            restrictions = db.get_country_restrictions(category)
            for r in restrictions:
                excluded_countries.append(r["country_code"])
                issues.append("配送制限: {} ({})".format(r["country_code"], r["reason"]))

        passed = len(issues) == 0 or all("配送制限" in i for i in issues)

        return jsonify({
            "success": True,
            "passed": passed,
            "issues": issues,
            "excluded_countries": excluded_countries,
        })

    @app.route("/api/products/<int:product_id>/list-ebay", methods=["POST"])
    def api_list_ebay(product_id):
        """eBay出品"""
        product = db.get_product(product_id)
        if not product:
            return jsonify({"error": "商品ID {} が見つかりません".format(product_id)}), 404

        data = request.get_json(force=True)
        title_en = data.get("title_en", "")
        description_en = data.get("description_en", "")
        price_usd = data.get("price_usd")
        tags = data.get("tags", [])

        if not title_en or not description_en or not price_usd:
            return jsonify({"error": "title_en, description_en, price_usd は必須です"}), 400

        try:
            price_usd = float(price_usd)
        except (ValueError, TypeError):
            return jsonify({"error": "price_usdは数値である必要があります"}), 400

        # BANチェック
        text = "{} {}".format(title_en, description_en)
        brand_matches = db.is_brand_blacklisted(text)
        if brand_matches:
            brand_names = [m["brand_name"] for m in brand_matches]
            return jsonify({"error": "VeRO警告: ブランド名が含まれています: {}".format(", ".join(brand_names))}), 400

        # 配送除外国
        excluded_countries = []
        category = product.get("category")
        if category:
            restrictions = db.get_country_restrictions(category)
            excluded_countries = [r["country_code"] for r in restrictions]

        try:
            from src.platforms.ebay import EbayClient
            ebay = EbayClient()
            listing_data = {
                "title_en": title_en,
                "description_en": description_en,
                "price_usd": price_usd,
                "tags": tags,
                "excluded_countries": excluded_countries,
            }
            result = ebay.create_listing(product, listing_data)

            # DBにリスティング登録
            listing_id = db.create_listing({
                "product_id": product_id,
                "platform": "ebay",
                "platform_listing_id": result.get("platform_listing_id"),
                "title_en": title_en,
                "description_en": description_en,
                "tags": tags,
                "price_usd": price_usd,
                "status": result.get("status", "active"),
                "ban_check_passed": True,
                "excluded_countries": excluded_countries,
            })

            return jsonify({
                "success": True,
                "listing_id": listing_id,
                "platform_listing_id": result.get("platform_listing_id"),
                "url": result.get("url", ""),
                "message": "eBayに出品しました",
            })
        except Exception as e:
            return jsonify({"error": "eBay出品エラー: {}".format(str(e))}), 500

    @app.route("/api/products/<int:product_id>/list-base", methods=["POST"])
    def api_list_base(product_id):
        """BASE出品"""
        product = db.get_product(product_id)
        if not product:
            return jsonify({"error": "商品ID {} が見つかりません".format(product_id)}), 404

        data = request.get_json(force=True)
        price_jpy = data.get("price_jpy")
        stock = data.get("stock", 5)
        # リクエストから日本語タイトル・説明を受け取り、なければDB値を使用
        title_ja = data.get("title_ja") or product.get("name_ja", "")
        description_ja = data.get("description_ja") or product.get("description_ja", "")

        if not price_jpy:
            return jsonify({"error": "price_jpy は必須です"}), 400

        try:
            price_jpy = int(price_jpy)
        except (ValueError, TypeError):
            return jsonify({"error": "price_jpyは整数である必要があります"}), 400

        try:
            from src.platforms.base_shop import BaseShopClient
            base_client = BaseShopClient()
            listing_data = {
                "title_ja": title_ja,
                "description_ja": description_ja,
                "price_jpy": price_jpy,
                "stock": stock,
            }
            result = base_client.create_listing(product, listing_data)

            # DBにリスティング登録
            listing_id = db.create_listing({
                "product_id": product_id,
                "platform": "base",
                "platform_listing_id": result.get("platform_listing_id"),
                "title_en": product.get("name_ja", ""),
                "price_usd": price_jpy / 150.0,
                "status": result.get("status", "active"),
                "ban_check_passed": True,
            })

            return jsonify({
                "success": True,
                "listing_id": listing_id,
                "platform_listing_id": result.get("platform_listing_id"),
                "url": result.get("url", ""),
                "message": "BASEに出品しました",
            })
        except Exception as e:
            return jsonify({"error": "BASE出品エラー: {}".format(str(e))}), 500

    @app.route("/api/products/bulk-list", methods=["POST"])
    def api_bulk_list():
        """一括出品"""
        data = request.get_json(force=True)
        product_ids = data.get("product_ids", [])
        platform = data.get("platform", "ebay")
        auto_generate = data.get("auto_generate", False)
        price_usd = data.get("price_usd")

        if not product_ids:
            return jsonify({"error": "product_idsが空です"}), 400

        results = []
        for pid in product_ids:
            try:
                pid = int(pid)
                product = db.get_product(pid)
                if not product:
                    results.append({"product_id": pid, "success": False, "error": "商品が見つかりません"})
                    continue

                title_en = product.get("name_en", "")
                description_en = product.get("description_en", "")
                tags = []

                # AI自動生成
                if auto_generate:
                    try:
                        from src.ai.description_generator import generate_full_listing
                        generated = generate_full_listing(product)
                        title_en = generated.get("title", title_en)
                        description_en = generated.get("description", description_en)
                        tags = generated.get("tags", [])
                    except Exception as e:
                        results.append({"product_id": pid, "success": False, "error": "AI生成エラー: {}".format(str(e))})
                        continue

                if not title_en or not description_en:
                    results.append({"product_id": pid, "success": False, "error": "英語タイトル・説明が未設定です"})
                    continue

                # BANチェック
                text = "{} {}".format(title_en, description_en)
                brand_matches = db.is_brand_blacklisted(text)
                if brand_matches:
                    brand_names = [m["brand_name"] for m in brand_matches]
                    results.append({"product_id": pid, "success": False, "error": "VeRO警告: {}".format(", ".join(brand_names))})
                    continue

                if platform == "ebay":
                    sale_price = price_usd
                    if not sale_price:
                        results.append({"product_id": pid, "success": False, "error": "price_usdが未設定です"})
                        continue

                    excluded_countries = []
                    category = product.get("category")
                    if category:
                        restrictions = db.get_country_restrictions(category)
                        excluded_countries = [r["country_code"] for r in restrictions]

                    from src.platforms.ebay import EbayClient
                    ebay = EbayClient()
                    listing_data = {
                        "title_en": title_en,
                        "description_en": description_en,
                        "price_usd": float(sale_price),
                        "tags": tags,
                        "excluded_countries": excluded_countries,
                    }
                    result = ebay.create_listing(product, listing_data)

                    db.create_listing({
                        "product_id": pid,
                        "platform": "ebay",
                        "platform_listing_id": result.get("platform_listing_id"),
                        "title_en": title_en,
                        "description_en": description_en,
                        "tags": tags,
                        "price_usd": float(sale_price),
                        "status": result.get("status", "active"),
                        "ban_check_passed": True,
                        "excluded_countries": excluded_countries,
                    })
                    results.append({"product_id": pid, "success": True, "platform_listing_id": result.get("platform_listing_id")})

                elif platform == "base":
                    from src.platforms.base_shop import BaseShopClient
                    base_client = BaseShopClient()
                    listing_data = {
                        "title_ja": product.get("name_ja", ""),
                        "description_ja": product.get("description_ja", ""),
                        "price_jpy": int(price_usd * 150) if price_usd else 2000,
                        "stock": 5,
                    }
                    result = base_client.create_listing(product, listing_data)

                    db.create_listing({
                        "product_id": pid,
                        "platform": "base",
                        "platform_listing_id": result.get("platform_listing_id"),
                        "title_en": product.get("name_ja", ""),
                        "price_usd": price_usd or (2000 / 150.0),
                        "status": result.get("status", "active"),
                        "ban_check_passed": True,
                    })
                    results.append({"product_id": pid, "success": True, "platform_listing_id": result.get("platform_listing_id")})
                else:
                    results.append({"product_id": pid, "success": False, "error": "未対応プラットフォーム: {}".format(platform)})

            except Exception as e:
                results.append({"product_id": pid, "success": False, "error": str(e)})

        success_count = sum(1 for r in results if r.get("success"))
        return jsonify({
            "success": True,
            "results": results,
            "message": "{}/{}件の出品に成功しました".format(success_count, len(product_ids)),
        })

    # --- リサーチ APIエンドポイント ---

    @app.route("/api/research/analyze", methods=["POST"])
    def api_research_analyze():
        """eBayキーワードリサーチ実行→DB保存→結果返却"""
        data = request.get_json(force=True)
        keyword = (data.get("keyword") or "").strip()
        limit = data.get("limit", 50)

        if not keyword:
            return jsonify({"error": "キーワードが空です"}), 400

        try:
            limit = int(limit)
            limit = max(1, min(limit, 200))
        except (ValueError, TypeError):
            limit = 50

        try:
            from src.research.research_service import run_keyword_research

            result = run_keyword_research(keyword, limit=limit)

            # DB保存
            session_data = {
                "keyword": keyword,
                "marketplace_id": "EBAY_US",
                "total_results": result.get("total_results"),
                "avg_price_usd": result.get("avg_price_usd"),
                "min_price_usd": result.get("min_price_usd"),
                "max_price_usd": result.get("max_price_usd"),
                "median_price_usd": result.get("median_price_usd"),
                "avg_shipping_usd": result.get("avg_shipping_usd"),
                "sample_size": result.get("sample_size"),
                "japan_seller_count": result.get("japan_seller_count", 0),
                "top_items_json": result.get("top_items", []),
                "price_dist_json": result.get("price_dist", []),
                "status": "completed",
            }
            session_id = db.create_research_session(session_data)
            session = db.get_research_session(session_id)

            return jsonify({
                "success": True,
                "session": session,
                "message": "リサーチ完了: {}".format(keyword),
            })
        except Exception as e:
            # エラー時もDBに記録
            try:
                err_session = {
                    "keyword": keyword,
                    "status": "failed",
                    "error_msg": str(e),
                }
                db.create_research_session(err_session)
            except Exception:
                pass
            return jsonify({"error": "リサーチエラー: {}".format(str(e))}), 500

    @app.route("/api/research/history")
    def api_research_history():
        """リサーチ履歴一覧"""
        keyword = request.args.get("keyword", "").strip() or None
        limit = request.args.get("limit", "50", type=str)
        try:
            limit_int = int(limit)
        except ValueError:
            limit_int = 50

        sessions = db.get_research_sessions(keyword=keyword, limit=limit_int)
        return jsonify({"sessions": sessions, "total": len(sessions)})

    @app.route("/api/research/<int:session_id>")
    def api_research_detail(session_id):
        """リサーチ詳細（matches含む）"""
        session = db.get_research_session(session_id)
        if not session:
            return jsonify({"error": "リサーチID {} が見つかりません".format(session_id)}), 404

        # JSONカラムをパース
        top_items = []
        if session.get("top_items_json"):
            try:
                top_items = json.loads(session["top_items_json"])
            except (json.JSONDecodeError, TypeError):
                pass

        price_dist = []
        if session.get("price_dist_json"):
            try:
                price_dist = json.loads(session["price_dist_json"])
            except (json.JSONDecodeError, TypeError):
                pass

        matches = db.get_research_matches(session_id)

        return jsonify({
            "session": session,
            "top_items": top_items,
            "price_dist": price_dist,
            "matches": matches,
        })

    @app.route("/api/research/compare", methods=["POST"])
    def api_research_compare():
        """複数キーワード比較（最大5件）"""
        data = request.get_json(force=True)
        session_ids = data.get("session_ids", [])

        if not session_ids:
            return jsonify({"error": "session_idsが空です"}), 400

        try:
            session_ids = [int(sid) for sid in session_ids[:5]]
        except (ValueError, TypeError):
            return jsonify({"error": "session_idsは整数のリストである必要があります"}), 400

        from src.research.research_service import compare_keywords
        results = compare_keywords(session_ids, db)

        return jsonify({
            "success": True,
            "sessions": results,
            "total": len(results),
        })

    @app.route("/api/research/<int:session_id>/match-netsea", methods=["POST"])
    def api_research_match_netsea(session_id):
        """NETSEAマッチング実行"""
        session = db.get_research_session(session_id)
        if not session:
            return jsonify({"error": "リサーチID {} が見つかりません".format(session_id)}), 404

        data = request.get_json(force=True)
        supplier_ids = (data.get("supplier_ids") or "").strip()

        if not supplier_ids:
            return jsonify({"error": "supplier_idsが空です"}), 400

        try:
            from src.research.research_service import match_netsea_products

            matches = match_netsea_products(
                keyword=session["keyword"],
                total_results=session.get("total_results") or 0,
                median_price_usd=session.get("median_price_usd"),
                supplier_ids=supplier_ids,
            )

            # DB保存
            for m in matches:
                m["session_id"] = session_id
                db.create_research_match(m)

            return jsonify({
                "success": True,
                "matches": matches,
                "message": "{}件のマッチング結果".format(len(matches)),
            })
        except Exception as e:
            return jsonify({"error": "NETSEAマッチングエラー: {}".format(str(e))}), 500

    # --- SNS APIエンドポイント ---

    @app.route("/api/sns/posts")
    def api_sns_posts_list():
        """SNS投稿一覧（date_from/date_toで予約日時範囲フィルター可）"""
        platform = request.args.get("platform", "").strip() or None
        status = request.args.get("status", "").strip() or None
        date_from = request.args.get("date_from", "").strip() or None
        date_to = request.args.get("date_to", "").strip() or None
        limit = request.args.get("limit", "50", type=str)
        try:
            limit_int = int(limit)
        except ValueError:
            limit_int = 50

        posts = db.get_sns_posts(
            platform=platform, status=status,
            date_from=date_from, date_to=date_to,
            limit=limit_int,
        )
        return jsonify({"posts": posts, "total": len(posts)})

    @app.route("/api/sns/posts", methods=["POST"])
    def api_sns_posts_create():
        """SNS投稿保存（下書き/予約）"""
        data = request.get_json(force=True)
        platform = (data.get("platform") or "").strip()
        body = (data.get("body") or "").strip()

        if platform not in ("twitter", "instagram", "threads"):
            return jsonify({"error": "platformはtwitter/instagram/threadsのいずれかです"}), 400
        if not body:
            return jsonify({"error": "本文が空です"}), 400

        # プラットフォーム別文字数制限
        char_limits = {"twitter": 280, "instagram": 2200, "threads": 500}
        limit = char_limits.get(platform, 280)
        if len(body) > limit:
            return jsonify({"error": "本文が{}文字制限を超えています（{}文字）".format(limit, len(body))}), 400

        post_data = {
            "product_id": data.get("product_id"),
            "platform": platform,
            "body": body,
            "hashtags": data.get("hashtags"),
            "scheduled_at": data.get("scheduled_at"),
            "status": data.get("status", "draft"),
        }

        # 商品に紐づく画像を自動設定
        product_id = data.get("product_id")
        if product_id:
            product = db.get_product(int(product_id))
            if product and product.get("image_urls"):
                post_data["image_urls"] = product["image_urls"]

        post_id = db.create_sns_post(post_data)
        post = db.get_sns_post(post_id)

        return jsonify({
            "success": True,
            "post": post,
            "message": "SNS投稿を保存しました",
        })

    @app.route("/api/sns/posts/<int:post_id>/publish", methods=["POST"])
    def api_sns_post_publish(post_id):
        """SNS投稿を実行（スタブ: ステータスをpostedに変更）"""
        post = db.get_sns_post(post_id)
        if not post:
            return jsonify({"error": "投稿ID {} が見つかりません".format(post_id)}), 404

        from datetime import datetime as dt
        db.update_sns_post(post_id, {
            "status": "posted",
            "posted_at": dt.now().isoformat(),
            "platform_post_id": "stub_{}".format(post_id),
        })

        return jsonify({
            "success": True,
            "message": "投稿しました（スタブ）",
        })

    @app.route("/api/sns/posts/<int:post_id>/delete", methods=["POST"])
    def api_sns_post_delete(post_id):
        """SNS投稿を削除"""
        post = db.get_sns_post(post_id)
        if not post:
            return jsonify({"error": "投稿ID {} が見つかりません".format(post_id)}), 404

        db.delete_sns_post(post_id)
        return jsonify({
            "success": True,
            "message": "投稿を削除しました",
        })

    @app.route("/api/sns/generate", methods=["POST"])
    def api_sns_generate():
        """SNS投稿文をAI生成（スタブ: テンプレ返却）"""
        data = request.get_json(force=True)
        product_id = data.get("product_id")
        platform = data.get("platform", "twitter")

        if not product_id:
            return jsonify({"error": "product_idは必須です"}), 400

        product = db.get_product(int(product_id))
        if not product:
            return jsonify({"error": "商品ID {} が見つかりません".format(product_id)}), 404

        name = product.get("name_ja", "商品")
        category = product.get("category", "")

        # スタブ: テンプレートで投稿文を生成
        hashtag_map = {
            "tenugui": "#手ぬぐい #tenugui #japanesetextile",
            "furoshiki": "#風呂敷 #furoshiki #japaneseculture",
            "knife": "#包丁 #japaneseknife #kitchenknife",
            "incense": "#お香 #incense #japaneseincense",
            "washi": "#和紙 #washi #japanesepaper",
        }
        hashtags = hashtag_map.get(category, "#japan #japanese #madeinjapan")

        body = "{}をご紹介します！日本の伝統的な{}です。海外発送対応。".format(
            name, category or "文化商品"
        )

        return jsonify({
            "success": True,
            "body": body,
            "hashtags": hashtags,
        })

    @app.route("/api/products/<int:product_id>/profit", methods=["POST"])
    def api_profit(product_id):
        """利益計算"""
        product = db.get_product(product_id)
        if not product:
            return jsonify({"error": "商品ID {} が見つかりません".format(product_id)}), 404

        data = request.get_json(force=True)
        sale_usd = data.get("sale_usd")
        platform = data.get("platform", "ebay")

        if not sale_usd:
            return jsonify({"error": "sale_usd は必須です"}), 400

        try:
            sale_usd = float(sale_usd)
        except (ValueError, TypeError):
            return jsonify({"error": "sale_usdは数値である必要があります"}), 400

        wholesale = product.get("wholesale_price_jpy")
        if not wholesale:
            return jsonify({"error": "卸値が未設定です"}), 400

        from src.ai.profit_calculator import calculate_profit
        calc = calculate_profit(
            wholesale_jpy=wholesale,
            sale_usd=sale_usd,
            weight_g=product.get("weight_g"),
            platform=platform,
        )

        return jsonify({
            "success": True,
            "sale_usd": calc["sale_usd"],
            "wholesale_usd": calc["wholesale_usd"],
            "shipping_usd": calc["shipping_usd"],
            "platform_fees_usd": calc["platform_fees_usd"],
            "profit_usd": calc["profit_usd"],
            "profit_margin": calc["profit_margin"],
            "profitable": calc["profitable"],
        })

    return app
