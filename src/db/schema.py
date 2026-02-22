"""SQLiteスキーマ定義

KB既存5テーブル + ebay_market_data テーブル。
冪等に実行可能（IF NOT EXISTS）。
"""

# 仕入先から取得した商品
PRODUCTS_TABLE = """
CREATE TABLE IF NOT EXISTS products (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    supplier            TEXT NOT NULL,            -- 'netsea' or 'topseller'
    supplier_product_id TEXT UNIQUE,
    name_ja             TEXT NOT NULL,
    name_en             TEXT,
    description_ja      TEXT,
    description_en      TEXT,
    category            TEXT,                     -- 'tenugui','furoshiki','knife','incense','washi'
    wholesale_price_jpy INTEGER,
    weight_g            INTEGER,                  -- NULLは不明（0ではない）
    image_urls          TEXT,                     -- JSON array
    stock_status        TEXT DEFAULT 'in_stock',  -- 'in_stock','out_of_stock','discontinued'
    product_url         TEXT,                     -- 仕入先の商品ページURL
    supplier_id         TEXT,                     -- 仕入先サプライヤーID
    shop_name           TEXT,                     -- サプライヤー/ショップ名
    spec_text           TEXT,                     -- スペックテキスト（サイズ・素材等の生テキスト）
    reference_price_jpy INTEGER,                  -- 参考上代（定価）
    netsea_category_id  INTEGER,                  -- NETSEAカテゴリID
    direct_send_flag      TEXT,                   -- 消費者直送可（Y/N）
    image_copy_flag       TEXT,                   -- 画像転載可（Y/N）
    deal_net_shop_flag    TEXT,                   -- ネット販売可（Y/N）
    deal_net_auction_flag TEXT,                   -- ネットオークション可（Y/N）
    list_on_ebay        INTEGER DEFAULT 0,       -- eBay出品フラグ（0=OFF, 1=ON）
    list_on_base        INTEGER DEFAULT 0,       -- BASE出品フラグ（0=OFF, 1=ON）
    list_on_shopify     INTEGER DEFAULT 0,       -- Shopify出品フラグ（0=OFF, 1=ON）
    last_stock_check    DATETIME,
    created_at          DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at          DATETIME DEFAULT CURRENT_TIMESTAMP
);
"""

# プラットフォームに公開したリスティング
LISTINGS_TABLE = """
CREATE TABLE IF NOT EXISTS listings (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id          INTEGER REFERENCES products(id),
    platform            TEXT NOT NULL,            -- 'ebay','base','etsy'
    platform_listing_id TEXT,
    title_en            TEXT,
    description_en      TEXT,
    tags                TEXT,                     -- JSON array
    price_usd           REAL,
    shipping_cost_usd   REAL,
    status              TEXT DEFAULT 'draft',     -- 'draft','active','paused','sold','removed'
    ban_check_passed    BOOLEAN DEFAULT FALSE,
    ban_check_issues    TEXT,                     -- JSON array
    excluded_countries  TEXT,                     -- JSON array e.g. ["GB","IE"]
    views               INTEGER DEFAULT 0,
    favorites           INTEGER DEFAULT 0,
    sales               INTEGER DEFAULT 0,
    created_at          DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at          DATETIME DEFAULT CURRENT_TIMESTAMP
);
"""

# 注文
ORDERS_TABLE = """
CREATE TABLE IF NOT EXISTS orders (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    listing_id          INTEGER REFERENCES listings(id),
    platform            TEXT NOT NULL,
    platform_order_id   TEXT,
    buyer_country       TEXT,
    sale_price_usd      REAL,
    platform_fees_usd   REAL,
    shipping_cost_usd   REAL,
    wholesale_cost_jpy  INTEGER,
    profit_usd          REAL,
    status              TEXT DEFAULT 'pending',   -- 'pending','purchased','shipped','delivered','issue'
    supplier_order_id   TEXT,
    tracking_number     TEXT,
    ordered_at          DATETIME DEFAULT CURRENT_TIMESTAMP,
    shipped_at          DATETIME,
    delivered_at        DATETIME
);
"""

# VeRO対策用ブランドブラックリスト
BRAND_BLACKLIST_TABLE = """
CREATE TABLE IF NOT EXISTS brand_blacklist (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    brand_name          TEXT UNIQUE NOT NULL,
    platform            TEXT,                     -- 'ebay','etsy','all'
    risk_level          TEXT DEFAULT 'high',      -- 'high','medium'
    notes               TEXT,
    added_at            DATETIME DEFAULT CURRENT_TIMESTAMP
);
"""

# 国別配送制限
COUNTRY_RESTRICTIONS_TABLE = """
CREATE TABLE IF NOT EXISTS country_restrictions (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    category            TEXT NOT NULL,            -- 'knife' etc.
    country_code        TEXT NOT NULL,            -- ISO 3166-1 alpha-2
    reason              TEXT,
    UNIQUE(category, country_code)
);
"""

# eBayマーケットデータ（キーワードリサーチ結果）
EBAY_MARKET_DATA_TABLE = """
CREATE TABLE IF NOT EXISTS ebay_market_data (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    keyword             TEXT NOT NULL,
    marketplace_id      TEXT DEFAULT 'EBAY_US',
    total_results       INTEGER,
    avg_price_usd       REAL,
    min_price_usd       REAL,
    max_price_usd       REAL,
    median_price_usd    REAL,
    avg_shipping_usd    REAL,
    sold_count_sample   INTEGER,                  -- Playwright取得のsold数サンプル
    sample_size         INTEGER,                  -- 集計に使った商品数
    searched_at         DATETIME DEFAULT CURRENT_TIMESTAMP
);
"""

# キーワードリサーチセッション
RESEARCH_SESSIONS_TABLE = """
CREATE TABLE IF NOT EXISTS research_sessions (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    keyword             TEXT NOT NULL,
    marketplace_id      TEXT DEFAULT 'EBAY_US',
    total_results       INTEGER,
    avg_price_usd       REAL,
    min_price_usd       REAL,
    max_price_usd       REAL,
    median_price_usd    REAL,
    avg_shipping_usd    REAL,
    sample_size         INTEGER,
    japan_seller_count  INTEGER DEFAULT 0,
    top_items_json      TEXT,                     -- JSON配列
    price_dist_json     TEXT,                     -- JSON配列（ヒストグラムバケツ）
    status              TEXT DEFAULT 'completed', -- 'running','completed','failed'
    error_msg           TEXT,
    searched_at         DATETIME DEFAULT CURRENT_TIMESTAMP
);
"""

# NETSEAマッチング結果
RESEARCH_MATCHES_TABLE = """
CREATE TABLE IF NOT EXISTS research_matches (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id          INTEGER NOT NULL REFERENCES research_sessions(id),
    netsea_product_id   TEXT,
    netsea_name_ja      TEXT,
    wholesale_price_jpy INTEGER,
    suggested_price_usd REAL,
    profit_usd          REAL,
    profit_margin       REAL,
    profitable          BOOLEAN DEFAULT FALSE,
    demand_score        REAL,
    margin_score        REAL,
    competition_score   REAL,
    total_score         REAL,
    direct_send_flag    TEXT,
    image_copy_flag     TEXT,
    deal_net_shop_flag  TEXT,
    created_at          DATETIME DEFAULT CURRENT_TIMESTAMP
);
"""

# 同期ログ（在庫同期・注文処理の実行記録）
SYNC_LOG_TABLE = """
CREATE TABLE IF NOT EXISTS sync_log (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    sync_type           TEXT NOT NULL,            -- 'inventory' or 'orders'
    platform            TEXT,                     -- 'ebay','etsy','all'
    status              TEXT DEFAULT 'running',   -- 'running','completed','failed'
    items_checked       INTEGER DEFAULT 0,
    items_changed       INTEGER DEFAULT 0,
    errors              TEXT,                     -- JSON array
    started_at          DATETIME DEFAULT CURRENT_TIMESTAMP,
    completed_at        DATETIME
);
"""

# SNS投稿管理
SNS_POSTS_TABLE = """
CREATE TABLE IF NOT EXISTS sns_posts (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id          INTEGER REFERENCES products(id),
    platform            TEXT NOT NULL,            -- 'twitter','instagram','threads'
    body                TEXT NOT NULL DEFAULT '',
    image_urls          TEXT,                     -- JSON array
    hashtags            TEXT,
    status              TEXT DEFAULT 'draft',     -- 'draft','scheduled','posted','failed'
    scheduled_at        DATETIME,
    posted_at           DATETIME,
    platform_post_id    TEXT,
    error_message       TEXT,
    created_at          DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at          DATETIME DEFAULT CURRENT_TIMESTAMP
);
"""

# 全テーブル定義（作成順）
ALL_TABLES = [
    ("products", PRODUCTS_TABLE),
    ("listings", LISTINGS_TABLE),
    ("orders", ORDERS_TABLE),
    ("brand_blacklist", BRAND_BLACKLIST_TABLE),
    ("country_restrictions", COUNTRY_RESTRICTIONS_TABLE),
    ("ebay_market_data", EBAY_MARKET_DATA_TABLE),
    ("research_sessions", RESEARCH_SESSIONS_TABLE),
    ("research_matches", RESEARCH_MATCHES_TABLE),
    ("sync_log", SYNC_LOG_TABLE),
    ("sns_posts", SNS_POSTS_TABLE),
]

# シードデータ: 包丁の配送制限（UK/IE）
SEED_COUNTRY_RESTRICTIONS = [
    ("knife", "GB", "UK刃物輸入規制 - Offensive Weapons Act 2019"),
    ("knife", "IE", "アイルランド刃物輸入規制"),
]

# シードデータ: VeROブランドブラックリスト（主要な日本ブランド）
SEED_BRAND_BLACKLIST = [
    ("Shun", "ebay", "high", "旬 — 貝印の包丁ブランド。VeRO登録済み"),
    ("Global", "ebay", "high", "グローバル — 吉田金属工業。VeRO登録済み"),
    ("Miyabi", "ebay", "high", "雅 — ツヴィリング傘下。VeRO登録済み"),
    ("Kai", "ebay", "high", "貝印 — VeRO登録済み"),
    ("Zwilling", "all", "high", "ツヴィリング — VeRO常連"),
    ("Wüsthof", "all", "high", "ヴュストホフ — VeRO常連"),
    ("Victorinox", "all", "high", "ビクトリノックス — VeRO常連"),
    ("Sanrio", "all", "high", "サンリオ — キャラクター権利保持"),
    ("Studio Ghibli", "all", "high", "スタジオジブリ — キャラクター権利保持"),
    ("Nintendo", "all", "high", "任天堂 — ゲーム関連商品"),
]
