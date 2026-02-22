"""SQLiteデータベース接続管理

同期sqlite3を使用（DB操作はサブミリ秒、async不要）。
upsertメソッドと統計集計を提供。
"""

import json
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.db.schema import (
    ALL_TABLES,
    SEED_BRAND_BLACKLIST,
    SEED_COUNTRY_RESTRICTIONS,
)


class Database:
    """SQLiteデータベースマネージャー"""

    def __init__(self, db_path: Optional[str] = None):
        if db_path is None:
            # プロジェクトルートからの相対パス
            project_root = Path(__file__).parent.parent.parent
            db_path = str(project_root / "data" / "dropship.db")

        self.db_path = db_path
        # dataディレクトリが存在しない場合は作成
        os.makedirs(os.path.dirname(db_path), exist_ok=True)

    @contextmanager
    def connect(self):
        """コネクション管理（コンテキストマネージャー）"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def init_tables(self) -> List[str]:
        """全テーブルを作成（冪等）。作成したテーブル名リストを返す"""
        created = []
        with self.connect() as conn:
            for name, sql in ALL_TABLES:
                conn.execute(sql)
                created.append(name)

            # 既存DBへのマイグレーション: productsテーブルに追加カラム
            migrate_columns = [
                ("product_url", "TEXT"),
                ("supplier_id", "TEXT"),
                ("shop_name", "TEXT"),
                ("spec_text", "TEXT"),
                ("reference_price_jpy", "INTEGER"),
                ("netsea_category_id", "INTEGER"),
                ("direct_send_flag", "TEXT"),
                ("image_copy_flag", "TEXT"),
                ("deal_net_shop_flag", "TEXT"),
                ("deal_net_auction_flag", "TEXT"),
                ("list_on_ebay", "INTEGER DEFAULT 0"),
                ("list_on_base", "INTEGER DEFAULT 0"),
                ("list_on_shopify", "INTEGER DEFAULT 0"),
            ]
            for col_name, col_type in migrate_columns:
                try:
                    conn.execute(
                        "ALTER TABLE products ADD COLUMN {} {}".format(
                            col_name, col_type
                        )
                    )
                except sqlite3.OperationalError:
                    pass  # カラム既存ならスキップ

        return created

    def seed_data(self) -> Dict[str, int]:
        """シードデータ投入（冪等: INSERT OR IGNORE）"""
        counts = {"country_restrictions": 0, "brand_blacklist": 0}

        with self.connect() as conn:
            # 国別配送制限
            for category, country_code, reason in SEED_COUNTRY_RESTRICTIONS:
                cursor = conn.execute(
                    """INSERT OR IGNORE INTO country_restrictions
                       (category, country_code, reason)
                       VALUES (?, ?, ?)""",
                    (category, country_code, reason),
                )
                counts["country_restrictions"] += cursor.rowcount

            # ブランドブラックリスト
            for brand, platform, risk, notes in SEED_BRAND_BLACKLIST:
                cursor = conn.execute(
                    """INSERT OR IGNORE INTO brand_blacklist
                       (brand_name, platform, risk_level, notes)
                       VALUES (?, ?, ?, ?)""",
                    (brand, platform, risk, notes),
                )
                counts["brand_blacklist"] += cursor.rowcount

        return counts

    def upsert_product(self, product: Dict[str, Any]) -> int:
        """商品をupsert（supplier_product_idで一意判定）。product IDを返す"""
        with self.connect() as conn:
            # image_urlsがリストの場合はJSON文字列化
            image_urls = product.get("image_urls")
            if isinstance(image_urls, list):
                image_urls = json.dumps(image_urls)

            cursor = conn.execute(
                """INSERT INTO products
                   (supplier, supplier_product_id, name_ja, name_en,
                    description_ja, description_en, category,
                    wholesale_price_jpy, weight_g, image_urls,
                    stock_status, product_url, supplier_id, shop_name,
                    spec_text, reference_price_jpy, netsea_category_id,
                    direct_send_flag, image_copy_flag,
                    deal_net_shop_flag, deal_net_auction_flag,
                    last_stock_check, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                   ON CONFLICT(supplier_product_id) DO UPDATE SET
                    name_ja = excluded.name_ja,
                    description_ja = excluded.description_ja,
                    wholesale_price_jpy = excluded.wholesale_price_jpy,
                    weight_g = excluded.weight_g,
                    image_urls = excluded.image_urls,
                    stock_status = excluded.stock_status,
                    product_url = excluded.product_url,
                    supplier_id = excluded.supplier_id,
                    shop_name = excluded.shop_name,
                    spec_text = excluded.spec_text,
                    reference_price_jpy = excluded.reference_price_jpy,
                    netsea_category_id = excluded.netsea_category_id,
                    direct_send_flag = excluded.direct_send_flag,
                    image_copy_flag = excluded.image_copy_flag,
                    deal_net_shop_flag = excluded.deal_net_shop_flag,
                    deal_net_auction_flag = excluded.deal_net_auction_flag,
                    last_stock_check = excluded.last_stock_check,
                    updated_at = excluded.updated_at""",
                (
                    product.get("supplier", "netsea"),
                    product["supplier_product_id"],
                    product["name_ja"],
                    product.get("name_en"),
                    product.get("description_ja"),
                    product.get("description_en"),
                    product.get("category"),
                    product.get("wholesale_price_jpy"),
                    product.get("weight_g"),  # NULLのまま保持（0にしない）
                    image_urls,
                    product.get("stock_status", "in_stock"),
                    product.get("product_url"),
                    product.get("supplier_id"),
                    product.get("shop_name"),
                    product.get("spec_text"),
                    product.get("reference_price_jpy"),
                    product.get("netsea_category_id"),
                    product.get("direct_send_flag"),
                    product.get("image_copy_flag"),
                    product.get("deal_net_shop_flag"),
                    product.get("deal_net_auction_flag"),
                    product.get("last_stock_check", datetime.now().isoformat()),
                    datetime.now().isoformat(),
                ),
            )
            # upsert後のIDを取得
            row = conn.execute(
                "SELECT id FROM products WHERE supplier_product_id = ?",
                (product["supplier_product_id"],),
            ).fetchone()
            return row["id"]

    def insert_market_data(self, data: Dict[str, Any]) -> int:
        """eBayマーケットデータを挿入"""
        with self.connect() as conn:
            cursor = conn.execute(
                """INSERT INTO ebay_market_data
                   (keyword, marketplace_id, total_results,
                    avg_price_usd, min_price_usd, max_price_usd,
                    median_price_usd, avg_shipping_usd,
                    sold_count_sample, sample_size)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    data["keyword"],
                    data.get("marketplace_id", "EBAY_US"),
                    data.get("total_results"),
                    data.get("avg_price_usd"),
                    data.get("min_price_usd"),
                    data.get("max_price_usd"),
                    data.get("median_price_usd"),
                    data.get("avg_shipping_usd"),
                    data.get("sold_count_sample"),
                    data.get("sample_size"),
                ),
            )
            return cursor.lastrowid

    def get_stats(self) -> Dict[str, Any]:
        """全テーブルのレコード数と概要統計を返す"""
        stats = {}
        with self.connect() as conn:
            for name, _ in ALL_TABLES:
                try:
                    row = conn.execute(
                        f"SELECT COUNT(*) as cnt FROM {name}"
                    ).fetchone()
                    stats[name] = row["cnt"]
                except sqlite3.OperationalError:
                    stats[name] = "テーブル未作成"

            # 商品の仕入先別内訳
            try:
                rows = conn.execute(
                    """SELECT supplier, COUNT(*) as cnt
                       FROM products GROUP BY supplier"""
                ).fetchall()
                stats["products_by_supplier"] = {
                    row["supplier"]: row["cnt"] for row in rows
                }
            except sqlite3.OperationalError:
                pass

            # 商品のカテゴリ別内訳
            try:
                rows = conn.execute(
                    """SELECT category, COUNT(*) as cnt
                       FROM products GROUP BY category"""
                ).fetchall()
                stats["products_by_category"] = {
                    (row["category"] or "未分類"): row["cnt"] for row in rows
                }
            except sqlite3.OperationalError:
                pass

        return stats

    def get_product(self, product_id: int) -> Optional[dict]:
        """商品をIDで取得"""
        with self.connect() as conn:
            row = conn.execute(
                "SELECT * FROM products WHERE id = ?",
                (product_id,),
            ).fetchone()
            return dict(row) if row else None

    def get_products(
        self,
        supplier: Optional[str] = None,
        category: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
        search: Optional[str] = None,
    ) -> List[dict]:
        """商品一覧を取得"""
        query = "SELECT * FROM products WHERE 1=1"
        params: List[Any] = []

        if supplier:
            query += " AND supplier = ?"
            params.append(supplier)
        if category:
            query += " AND category = ?"
            params.append(category)
        if search:
            query += " AND (name_ja LIKE ? OR name_en LIKE ?)"
            like = "%{}%".format(search)
            params.extend([like, like])

        query += " ORDER BY updated_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        with self.connect() as conn:
            rows = conn.execute(query, params).fetchall()
            return [dict(row) for row in rows]

    def count_products(
        self,
        supplier: Optional[str] = None,
        category: Optional[str] = None,
        search: Optional[str] = None,
        stock_status: Optional[str] = None,
        ds_only: bool = False,
    ) -> int:
        """フィルタ条件に合致する商品の総件数を返す"""
        query = "SELECT COUNT(*) as cnt FROM products WHERE 1=1"
        params = []  # type: List[Any]

        if supplier:
            query += " AND supplier = ?"
            params.append(supplier)
        if category:
            query += " AND category = ?"
            params.append(category)
        if stock_status:
            query += " AND stock_status = ?"
            params.append(stock_status)
        if ds_only:
            query += (" AND direct_send_flag = 'Y'"
                      " AND image_copy_flag = 'Y'"
                      " AND deal_net_shop_flag = 'Y'")
        if search:
            query += " AND (name_ja LIKE ? OR name_en LIKE ?)"
            like = "%{}%".format(search)
            params.extend([like, like])

        with self.connect() as conn:
            row = conn.execute(query, params).fetchone()
            return row["cnt"]

    def is_brand_blacklisted(self, text: str) -> List[dict]:
        """テキスト内にブラックリストブランドが含まれるか検査"""
        matches = []
        with self.connect() as conn:
            brands = conn.execute(
                "SELECT brand_name, platform, risk_level, notes FROM brand_blacklist"
            ).fetchall()
            text_lower = text.lower()
            for brand in brands:
                if brand["brand_name"].lower() in text_lower:
                    matches.append(dict(brand))
        return matches

    def get_country_restrictions(self, category: str) -> List[dict]:
        """カテゴリの配送制限国を取得"""
        with self.connect() as conn:
            rows = conn.execute(
                """SELECT country_code, reason FROM country_restrictions
                   WHERE category = ?""",
                (category,),
            ).fetchall()
            return [dict(row) for row in rows]

    # --- リスティング CRUD ---

    def create_listing(self, listing: Dict[str, Any]) -> int:
        """リスティングを作成。listing IDを返す"""
        with self.connect() as conn:
            # tagsがリストの場合はJSON文字列化
            tags = listing.get("tags")
            if isinstance(tags, list):
                tags = json.dumps(tags)

            excluded = listing.get("excluded_countries")
            if isinstance(excluded, list):
                excluded = json.dumps(excluded)

            ban_issues = listing.get("ban_check_issues")
            if isinstance(ban_issues, list):
                ban_issues = json.dumps(ban_issues)

            cursor = conn.execute(
                """INSERT INTO listings
                   (product_id, platform, platform_listing_id,
                    title_en, description_en, tags,
                    price_usd, shipping_cost_usd, status,
                    ban_check_passed, ban_check_issues, excluded_countries)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    listing["product_id"],
                    listing["platform"],
                    listing.get("platform_listing_id"),
                    listing.get("title_en"),
                    listing.get("description_en"),
                    tags,
                    listing.get("price_usd"),
                    listing.get("shipping_cost_usd"),
                    listing.get("status", "draft"),
                    listing.get("ban_check_passed", False),
                    ban_issues,
                    excluded,
                ),
            )
            return cursor.lastrowid

    def get_listing(self, listing_id: int) -> Optional[dict]:
        """リスティングをIDで取得"""
        with self.connect() as conn:
            row = conn.execute(
                "SELECT * FROM listings WHERE id = ?",
                (listing_id,),
            ).fetchone()
            return dict(row) if row else None

    def get_listings(
        self,
        platform: Optional[str] = None,
        status: Optional[str] = None,
        product_id: Optional[int] = None,
        limit: int = 50,
        offset: int = 0,
        search: Optional[str] = None,
    ) -> List[dict]:
        """リスティング一覧を取得"""
        query = "SELECT * FROM listings WHERE 1=1"
        params: List[Any] = []

        if platform:
            query += " AND platform = ?"
            params.append(platform)
        if status:
            query += " AND status = ?"
            params.append(status)
        if product_id:
            query += " AND product_id = ?"
            params.append(product_id)
        if search:
            query += " AND title_en LIKE ?"
            params.append("%{}%".format(search))

        query += " ORDER BY updated_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        with self.connect() as conn:
            rows = conn.execute(query, params).fetchall()
            return [dict(row) for row in rows]

    def count_listings(
        self,
        platform: Optional[str] = None,
        status: Optional[str] = None,
        search: Optional[str] = None,
    ) -> int:
        """フィルタ条件に合致するリスティングの総件数"""
        query = "SELECT COUNT(*) as cnt FROM listings WHERE 1=1"
        params = []  # type: List[Any]

        if platform:
            query += " AND platform = ?"
            params.append(platform)
        if status:
            query += " AND status = ?"
            params.append(status)
        if search:
            query += " AND title_en LIKE ?"
            params.append("%{}%".format(search))

        with self.connect() as conn:
            row = conn.execute(query, params).fetchone()
            return row["cnt"]

    def update_listing(self, listing_id: int, updates: Dict[str, Any]) -> bool:
        """リスティングを更新"""
        if not updates:
            return False

        # 更新可能なカラム
        allowed = {
            "platform_listing_id", "title_en", "description_en",
            "tags", "price_usd", "shipping_cost_usd", "status",
            "ban_check_passed", "ban_check_issues", "excluded_countries",
            "views", "favorites", "sales",
        }

        set_clauses = []
        params: List[Any] = []
        for key, value in updates.items():
            if key not in allowed:
                continue
            # リスト値はJSON文字列化
            if isinstance(value, list):
                value = json.dumps(value)
            set_clauses.append(f"{key} = ?")
            params.append(value)

        if not set_clauses:
            return False

        set_clauses.append("updated_at = ?")
        params.append(datetime.now().isoformat())
        params.append(listing_id)

        with self.connect() as conn:
            conn.execute(
                f"UPDATE listings SET {', '.join(set_clauses)} WHERE id = ?",
                params,
            )
            return True

    def get_listing_by_platform_id(self, platform: str,
                                    platform_listing_id: str) -> Optional[dict]:
        """プラットフォームIDからリスティングを取得"""
        with self.connect() as conn:
            row = conn.execute(
                """SELECT * FROM listings
                   WHERE platform = ? AND platform_listing_id = ?""",
                (platform, platform_listing_id),
            ).fetchone()
            return dict(row) if row else None

    def get_active_listings_with_products(
        self, platform: Optional[str] = None,
    ) -> List[dict]:
        """アクティブなリスティングを商品情報付きで取得"""
        query = """
            SELECT l.*, p.supplier_product_id, p.name_ja, p.stock_status,
                   p.wholesale_price_jpy, p.weight_g, p.category
            FROM listings l
            JOIN products p ON l.product_id = p.id
            WHERE l.status = 'active'
        """
        params: List[Any] = []
        if platform:
            query += " AND l.platform = ?"
            params.append(platform)

        with self.connect() as conn:
            rows = conn.execute(query, params).fetchall()
            return [dict(row) for row in rows]

    # --- 注文 CRUD ---

    def create_order(self, order: Dict[str, Any]) -> int:
        """注文を作成。order IDを返す"""
        with self.connect() as conn:
            cursor = conn.execute(
                """INSERT INTO orders
                   (listing_id, platform, platform_order_id,
                    buyer_country, sale_price_usd, platform_fees_usd,
                    shipping_cost_usd, wholesale_cost_jpy, profit_usd,
                    status, ordered_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    order.get("listing_id"),
                    order["platform"],
                    order["platform_order_id"],
                    order.get("buyer_country"),
                    order.get("sale_price_usd"),
                    order.get("platform_fees_usd"),
                    order.get("shipping_cost_usd"),
                    order.get("wholesale_cost_jpy"),
                    order.get("profit_usd"),
                    order.get("status", "pending"),
                    order.get("ordered_at", datetime.now().isoformat()),
                ),
            )
            return cursor.lastrowid

    def get_order(self, order_id: int) -> Optional[dict]:
        """注文をIDで取得"""
        with self.connect() as conn:
            row = conn.execute(
                "SELECT * FROM orders WHERE id = ?",
                (order_id,),
            ).fetchone()
            return dict(row) if row else None

    def get_order_by_platform_id(self, platform: str,
                                  platform_order_id: str) -> Optional[dict]:
        """プラットフォーム注文IDから注文を取得"""
        with self.connect() as conn:
            row = conn.execute(
                """SELECT * FROM orders
                   WHERE platform = ? AND platform_order_id = ?""",
                (platform, platform_order_id),
            ).fetchone()
            return dict(row) if row else None

    def get_orders(
        self,
        platform: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
        search: Optional[str] = None,
    ) -> List[dict]:
        """注文一覧を取得"""
        query = "SELECT * FROM orders WHERE 1=1"
        params: List[Any] = []

        if platform:
            query += " AND platform = ?"
            params.append(platform)
        if status:
            query += " AND status = ?"
            params.append(status)
        if search:
            query += " AND (buyer_name LIKE ? OR platform_order_id LIKE ?)"
            like = "%{}%".format(search)
            params.extend([like, like])

        query += " ORDER BY ordered_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        with self.connect() as conn:
            rows = conn.execute(query, params).fetchall()
            return [dict(row) for row in rows]

    def count_orders(
        self,
        platform: Optional[str] = None,
        status: Optional[str] = None,
        search: Optional[str] = None,
    ) -> int:
        """フィルタ条件に合致する注文の総件数"""
        query = "SELECT COUNT(*) as cnt FROM orders WHERE 1=1"
        params = []  # type: List[Any]

        if platform:
            query += " AND platform = ?"
            params.append(platform)
        if status:
            query += " AND status = ?"
            params.append(status)
        if search:
            query += " AND (buyer_name LIKE ? OR platform_order_id LIKE ?)"
            like = "%{}%".format(search)
            params.extend([like, like])

        with self.connect() as conn:
            row = conn.execute(query, params).fetchone()
            return row["cnt"]

    def update_order(self, order_id: int, updates: Dict[str, Any]) -> bool:
        """注文を更新"""
        if not updates:
            return False

        allowed = {
            "status", "supplier_order_id", "tracking_number",
            "shipped_at", "delivered_at", "profit_usd",
            "platform_fees_usd", "shipping_cost_usd",
        }

        set_clauses = []
        params: List[Any] = []
        for key, value in updates.items():
            if key not in allowed:
                continue
            set_clauses.append(f"{key} = ?")
            params.append(value)

        if not set_clauses:
            return False

        params.append(order_id)

        with self.connect() as conn:
            conn.execute(
                f"UPDATE orders SET {', '.join(set_clauses)} WHERE id = ?",
                params,
            )
            return True

    # --- 同期ログ ---

    def create_sync_log(self, sync_type: str, platform: str = "all") -> int:
        """同期ログを開始。sync_log IDを返す"""
        with self.connect() as conn:
            cursor = conn.execute(
                """INSERT INTO sync_log (sync_type, platform, status)
                   VALUES (?, ?, 'running')""",
                (sync_type, platform),
            )
            return cursor.lastrowid

    def complete_sync_log(self, sync_id: int, items_checked: int,
                          items_changed: int,
                          errors: Optional[List[str]] = None,
                          success: bool = True) -> None:
        """同期ログを完了"""
        errors_json = json.dumps(errors) if errors else None
        status = "completed" if success else "failed"

        with self.connect() as conn:
            conn.execute(
                """UPDATE sync_log
                   SET status = ?, items_checked = ?, items_changed = ?,
                       errors = ?, completed_at = ?
                   WHERE id = ?""",
                (status, items_checked, items_changed,
                 errors_json, datetime.now().isoformat(), sync_id),
            )

    def update_product(self, product_id: int, updates: Dict[str, Any]) -> bool:
        """商品の部分更新（ホワイトリストで更新可能カラムを制限）"""
        if not updates:
            return False

        allowed = {
            "name_ja", "name_en", "description_ja", "description_en",
            "category", "weight_g", "stock_status",
            "list_on_ebay", "list_on_base", "list_on_shopify",
        }

        set_clauses = []
        params = []  # type: List[Any]
        for key, value in updates.items():
            if key not in allowed:
                continue
            set_clauses.append("{} = ?".format(key))
            params.append(value)

        if not set_clauses:
            return False

        set_clauses.append("updated_at = ?")
        params.append(datetime.now().isoformat())
        params.append(product_id)

        with self.connect() as conn:
            cursor = conn.execute(
                "UPDATE products SET {} WHERE id = ?".format(
                    ", ".join(set_clauses)
                ),
                params,
            )
            return cursor.rowcount > 0

    def delete_products(self, product_ids: List[int]) -> int:
        """商品を一括削除（関連listings先に削除）。削除件数を返す"""
        if not product_ids:
            return 0

        placeholders = ",".join("?" for _ in product_ids)

        with self.connect() as conn:
            # 関連リスティングを先に削除
            conn.execute(
                "DELETE FROM listings WHERE product_id IN ({})".format(
                    placeholders
                ),
                product_ids,
            )
            # 商品削除
            cursor = conn.execute(
                "DELETE FROM products WHERE id IN ({})".format(
                    placeholders
                ),
                product_ids,
            )
            return cursor.rowcount

    def update_product_flags(
        self, product_ids: List[int], flags: Dict[str, int]
    ) -> int:
        """複数商品の出品フラグを一括更新。更新件数を返す"""
        if not product_ids or not flags:
            return 0

        allowed_flags = {"list_on_ebay", "list_on_base", "list_on_shopify"}
        set_clauses = []
        params = []  # type: List[Any]
        for key, value in flags.items():
            if key not in allowed_flags:
                continue
            set_clauses.append("{} = ?".format(key))
            params.append(value)

        if not set_clauses:
            return 0

        set_clauses.append("updated_at = ?")
        params.append(datetime.now().isoformat())

        placeholders = ",".join("?" for _ in product_ids)
        params.extend(product_ids)

        with self.connect() as conn:
            cursor = conn.execute(
                "UPDATE products SET {} WHERE id IN ({})".format(
                    ", ".join(set_clauses), placeholders
                ),
                params,
            )
            return cursor.rowcount

    # --- SNS投稿 CRUD ---

    def create_sns_post(self, post: Dict[str, Any]) -> int:
        """SNS投稿を作成。post IDを返す"""
        with self.connect() as conn:
            image_urls = post.get("image_urls")
            if isinstance(image_urls, list):
                image_urls = json.dumps(image_urls)

            cursor = conn.execute(
                """INSERT INTO sns_posts
                   (product_id, platform, body, image_urls, hashtags,
                    status, scheduled_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    post.get("product_id"),
                    post["platform"],
                    post.get("body", ""),
                    image_urls,
                    post.get("hashtags"),
                    post.get("status", "draft"),
                    post.get("scheduled_at"),
                ),
            )
            return cursor.lastrowid

    def get_sns_post(self, post_id: int) -> Optional[dict]:
        """SNS投稿をIDで取得"""
        with self.connect() as conn:
            row = conn.execute(
                "SELECT * FROM sns_posts WHERE id = ?",
                (post_id,),
            ).fetchone()
            return dict(row) if row else None

    def get_sns_posts(
        self,
        platform: Optional[str] = None,
        status: Optional[str] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[dict]:
        """SNS投稿一覧を取得（date_from/date_toで予約日時フィルター可）"""
        query = "SELECT * FROM sns_posts WHERE 1=1"
        params = []  # type: List[Any]

        if platform:
            query += " AND platform = ?"
            params.append(platform)
        if status:
            query += " AND status = ?"
            params.append(status)
        if date_from:
            query += " AND scheduled_at >= ?"
            params.append(date_from)
        if date_to:
            query += " AND scheduled_at < ?"
            params.append(date_to)

        query += " ORDER BY updated_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        with self.connect() as conn:
            rows = conn.execute(query, params).fetchall()
            return [dict(row) for row in rows]

    def count_sns_posts(
        self,
        platform: Optional[str] = None,
        status: Optional[str] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
    ) -> int:
        """フィルタ条件に合致するSNS投稿の総件数"""
        query = "SELECT COUNT(*) as cnt FROM sns_posts WHERE 1=1"
        params = []  # type: List[Any]

        if platform:
            query += " AND platform = ?"
            params.append(platform)
        if status:
            query += " AND status = ?"
            params.append(status)
        if date_from:
            query += " AND scheduled_at >= ?"
            params.append(date_from)
        if date_to:
            query += " AND scheduled_at < ?"
            params.append(date_to)

        with self.connect() as conn:
            row = conn.execute(query, params).fetchone()
            return row["cnt"]

    def update_sns_post(self, post_id: int, updates: Dict[str, Any]) -> bool:
        """SNS投稿を更新"""
        if not updates:
            return False

        allowed = {
            "platform", "body", "image_urls", "hashtags",
            "status", "scheduled_at", "posted_at",
            "platform_post_id", "error_message",
        }

        set_clauses = []
        params = []  # type: List[Any]
        for key, value in updates.items():
            if key not in allowed:
                continue
            if isinstance(value, list):
                value = json.dumps(value)
            set_clauses.append("{} = ?".format(key))
            params.append(value)

        if not set_clauses:
            return False

        set_clauses.append("updated_at = ?")
        params.append(datetime.now().isoformat())
        params.append(post_id)

        with self.connect() as conn:
            cursor = conn.execute(
                "UPDATE sns_posts SET {} WHERE id = ?".format(
                    ", ".join(set_clauses)
                ),
                params,
            )
            return cursor.rowcount > 0

    def delete_sns_post(self, post_id: int) -> bool:
        """SNS投稿を削除"""
        with self.connect() as conn:
            cursor = conn.execute(
                "DELETE FROM sns_posts WHERE id = ?",
                (post_id,),
            )
            return cursor.rowcount > 0

    # --- リサーチ CRUD ---

    def create_research_session(self, session: Dict[str, Any]) -> int:
        """リサーチセッションを作成。session IDを返す"""
        with self.connect() as conn:
            top_items = session.get("top_items_json")
            if isinstance(top_items, list):
                top_items = json.dumps(top_items, ensure_ascii=False)
            price_dist = session.get("price_dist_json")
            if isinstance(price_dist, list):
                price_dist = json.dumps(price_dist, ensure_ascii=False)

            cursor = conn.execute(
                """INSERT INTO research_sessions
                   (keyword, marketplace_id, total_results,
                    avg_price_usd, min_price_usd, max_price_usd,
                    median_price_usd, avg_shipping_usd, sample_size,
                    japan_seller_count, top_items_json, price_dist_json,
                    status, error_msg)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    session["keyword"],
                    session.get("marketplace_id", "EBAY_US"),
                    session.get("total_results"),
                    session.get("avg_price_usd"),
                    session.get("min_price_usd"),
                    session.get("max_price_usd"),
                    session.get("median_price_usd"),
                    session.get("avg_shipping_usd"),
                    session.get("sample_size"),
                    session.get("japan_seller_count", 0),
                    top_items,
                    price_dist,
                    session.get("status", "completed"),
                    session.get("error_msg"),
                ),
            )
            return cursor.lastrowid

    def get_research_session(self, session_id: int) -> Optional[dict]:
        """リサーチセッションをIDで取得"""
        with self.connect() as conn:
            row = conn.execute(
                "SELECT * FROM research_sessions WHERE id = ?",
                (session_id,),
            ).fetchone()
            return dict(row) if row else None

    def get_research_sessions(
        self,
        keyword: Optional[str] = None,
        limit: int = 50,
    ) -> List[dict]:
        """リサーチセッション一覧を取得"""
        query = "SELECT * FROM research_sessions WHERE 1=1"
        params: List[Any] = []

        if keyword:
            query += " AND keyword LIKE ?"
            params.append("%{}%".format(keyword))

        query += " ORDER BY searched_at DESC LIMIT ?"
        params.append(limit)

        with self.connect() as conn:
            rows = conn.execute(query, params).fetchall()
            return [dict(row) for row in rows]

    def create_research_match(self, match: Dict[str, Any]) -> int:
        """リサーチマッチングを作成。match IDを返す"""
        with self.connect() as conn:
            cursor = conn.execute(
                """INSERT INTO research_matches
                   (session_id, netsea_product_id, netsea_name_ja,
                    wholesale_price_jpy, suggested_price_usd,
                    profit_usd, profit_margin, profitable,
                    demand_score, margin_score, competition_score,
                    total_score, direct_send_flag, image_copy_flag,
                    deal_net_shop_flag)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    match["session_id"],
                    match.get("netsea_product_id"),
                    match.get("netsea_name_ja"),
                    match.get("wholesale_price_jpy"),
                    match.get("suggested_price_usd"),
                    match.get("profit_usd"),
                    match.get("profit_margin"),
                    match.get("profitable", False),
                    match.get("demand_score"),
                    match.get("margin_score"),
                    match.get("competition_score"),
                    match.get("total_score"),
                    match.get("direct_send_flag"),
                    match.get("image_copy_flag"),
                    match.get("deal_net_shop_flag"),
                ),
            )
            return cursor.lastrowid

    def get_research_matches(self, session_id: int) -> List[dict]:
        """セッションに紐づくマッチング結果を取得（スコア降順）"""
        with self.connect() as conn:
            rows = conn.execute(
                """SELECT * FROM research_matches
                   WHERE session_id = ?
                   ORDER BY total_score DESC""",
                (session_id,),
            ).fetchall()
            return [dict(row) for row in rows]

    def delete_research_session(self, session_id: int) -> bool:
        """リサーチセッションを削除（関連マッチングも削除）"""
        with self.connect() as conn:
            conn.execute(
                "DELETE FROM research_matches WHERE session_id = ?",
                (session_id,),
            )
            cursor = conn.execute(
                "DELETE FROM research_sessions WHERE id = ?",
                (session_id,),
            )
            return cursor.rowcount > 0

    def get_daily_summary(self, date: Optional[str] = None) -> Dict[str, Any]:
        """日次サマリーを取得"""
        if date is None:
            date = datetime.now().strftime("%Y-%m-%d")

        with self.connect() as conn:
            # 当日の注文
            order_row = conn.execute(
                """SELECT COUNT(*) as cnt,
                          COALESCE(SUM(sale_price_usd), 0) as revenue,
                          COALESCE(SUM(profit_usd), 0) as profit
                   FROM orders
                   WHERE date(ordered_at) = ?""",
                (date,),
            ).fetchone()

            # アクティブリスティング数
            listing_row = conn.execute(
                "SELECT COUNT(*) as cnt FROM listings WHERE status = 'active'"
            ).fetchone()

            # 当日の在庫変動
            sync_row = conn.execute(
                """SELECT COALESCE(SUM(items_changed), 0) as changes
                   FROM sync_log
                   WHERE sync_type = 'inventory'
                     AND date(started_at) = ?""",
                (date,),
            ).fetchone()

            return {
                "date": date,
                "orders_count": order_row["cnt"],
                "revenue_usd": order_row["revenue"],
                "profit_usd": order_row["profit"],
                "active_listings": listing_row["cnt"],
                "stock_changes": sync_row["changes"],
            }
