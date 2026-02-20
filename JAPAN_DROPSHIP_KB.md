# Japan DropShip Project — Knowledge Base

> **Single Source of Truth** for the Japan DropShip project.
> AI アシスタントとの作業時はこのファイルをコンテキストとして使用する。
> Last updated: 2026-02-19

---

## 1. プロジェクト概要

日本の文化商品（手ぬぐい・風呂敷・包丁・お香・和紙）を海外バイヤーにドロップシッピングで販売するEC事業。

**オーナー**: プログラミング・AI活用スキルあり。日本在住。
**ターゲット**: 米国・欧州の日本文化に関心のあるバイヤー

### チャネル戦略

| チャネル | 役割 | 優先度 |
|---------|------|--------|
| **eBay** | メイン。卸売DSが合法。集客力あり | 最優先 |
| **BASE** | ブランド構築 + BAN保険。eBay売れ筋を厳選展開 | Phase 2〜 |
| **Etsy** | craft supplies限定で将来検討 | 未定 |

### 最重要原則

> **BAN-safe design first.** プラットフォームポリシー遵守が全ての前提。

---

## 2. プラットフォームポリシー（必読）

### eBay

| ルール | 内容 |
|--------|------|
| ドロップシッピング | **合法**（卸売仕入先からの直送OK） |
| VeRO違反ペナルティ | 1回目: 警告/削除 → 2回目: 2-3週間停止 → 3回目: **永久BAN** |
| Defect Rate | **< 0.5%** 必須（超過で自動レビュー発動） |
| Late Shipment Rate | **< 3%** |
| 包丁の配送制限 | **UK/アイルランドへの配送禁止**（刃物輸入規制）→ 出品時に必ず除外設定 |

### BASE

| ルール | 内容 |
|--------|------|
| ドロップシッピング | **制限なし** |
| 手数料（スタンダード） | 決済3.6%+40円 + サービス3% = 合計 **6.6%+40円** |
| かんたん海外販売 | 追加5%（want.jpが発送代行） |
| 集客力 | ほぼゼロ → 自力でSNS/SEO集客が必要 |

### Etsy（将来参考）

| ルール | 内容 |
|--------|------|
| ドロップシッピング | **禁止**（craft supplies除く） |
| 日本セラー手数料 | 6% + $0.30/件（USの3%より高い） |
| セットアップ費 | $15-29（1回きり） |

---

## 3. 商品戦略

### 選定基準（7項目すべて合格が必須）

1. 破損リスク（DSは梱包コントロール不可）
2. Etsy policy compliant（将来用）
3. eBay policy compliant
4. VeRO risk（ブランド名問題）
5. 配送コスト（重量ベース）
6. リピート購入可能性
7. 1個あたり利益

### 商品ラインナップ

| 商品 | スコア | 重量 | 利益/個 | 備考 |
|------|--------|------|---------|------|
| **手ぬぐい / 風呂敷** | 7/7 | ~50g | $3-8 | 最優先。ゼロリスク。ノーブランド。 |
| **包丁** | 5/7 | ~300g | $15-60 | 単価最高。eBay専用。UK/IE除外必須。 |
| **お香** | 6/7 | ~100g | $4-10 | リピート率高（消耗品）。 |
| **和紙 / 文具** | 7/7 | ~80g | $3-7 | 破損ゼロ。VeROゼロ。 |

---

## 4. 利益計算

**前提**: 1 USD = 150 JPY

### 手ぬぐい（eBay、$15販売時）

| 項目 | 金額 |
|------|------|
| 仕入原価（NETSEA平均） | $2-4 (300-600 JPY) |
| 国際送料（ePacket ~50g） | $3.87 (580 JPY) |
| eBay Final Value Fee (13.25%) | $1.99 |
| eBay Payment Processing | $0.30 |
| **合計コスト** | **$8.16-10.16** |
| **利益** | **$4.84-6.84 (32-46%)** |

### 包丁（eBay、$100販売 / 仕入5,000円時）

| 項目 | 金額 |
|------|------|
| 仕入原価 | $33.33 (5,000 JPY) |
| 国際送料（EMS ~300g） | $24.00 (3,600 JPY) |
| eBay Final Value Fee (13.25%) | $13.25 |
| eBay Payment Processing | $0.30 |
| **合計コスト** | **$70.88** |
| **利益** | **$29.12 (29%)** |

### 月次売上シミュレーション（保守的）

| 月 | 出品数 | 販売数/月 | 平均利益 | 月次売上 | 日次作業 |
|----|--------|----------|---------|---------|---------|
| 1 | 10 | 2-5 | $6 | $12-30 | 2-3h |
| 2 | 30 | 5-12 | $8 | $40-96 | 2h |
| 3 | 80 | 12-25 | $10 | $120-250 | 1.5h |
| 4-6 | 200 | 30-60 | $12 | $360-720 | 1h |
| 7-12 | 500+ | 60-150 | $15 | $900-2,250 | 1h |

---

## 5. インフラ & コスト

### 月額固定費

| 項目 | 費用 | 備考 |
|------|------|------|
| VPS (Sakura/ConoHa) | 700-1,000 JPY | Scraper, cron, DB |
| SQLite | 0 JPY | ファイルベースDB |
| Claude API (Sonnet) | 100-800 JPY | 50商品=100円, 500商品=800円 |
| DeepL API Free | 0 JPY | 50万文字/月 無料 |
| TopSeller | 0 JPY | 無料プラン（5商品） |
| NETSEA | 0 JPY | 無料登録 |
| eRank | 0-900 JPY | 無料 or $5.99/月 |
| eBay | 0 JPY | ストア契約不要。250出品/月 無料 |
| BASE (Standard) | 0 JPY | 売上発生時のみ手数料 |
| **合計（50商品）** | **~2,300-3,400 JPY/月** | |
| **合計（200商品）** | **~2,800-3,900 JPY/月** | |

**初期投資**: ~1,000 JPY（VPS初月のみ）

---

## 6. システムアーキテクチャ

### データフロー

```
TopSeller / NETSEA
  │
  ▼
Scraper (Python + Playwright)
  │
  ▼
SQLite DB
  │
  ├─▶ BAN Risk Filter
  │     • ブランド名ブラックリスト照合
  │     • 国別配送制限チェック（包丁 → UK/IE除外）
  │     • 利益率チェック（>25%のみ通過）
  │
  ├─▶ AI Pipeline
  │     • Claude API → 英語商品説明生成
  │     • DeepL API → 翻訳/推敲
  │     • SEOタグ生成
  │
  ├─▶ Channel Router
  │     • eBay Inventory API
  │     • (将来: BASE API, Etsy API)
  │
  ├─▶ Inventory Sync (cron: 15分間隔)
  │
  ├─▶ Order Detection (webhook / polling)
  │     • 仕入先への自動発注
  │     • LINE Notify アラート
  │
  └─▶ Dashboard (Google Sheets + GAS)
```

### テックスタック

| コンポーネント | 技術 | 費用 |
|---------------|------|------|
| スクレイパー | Python + Playwright | 無料 |
| データベース | SQLite | 無料 |
| AI商品説明 | Claude API (Sonnet) | ~0.5 JPY/商品 |
| 翻訳 | DeepL API Free | 無料（50万文字/月） |
| eBay連携 | eBay Inventory API (REST) | 無料 |
| BASE連携 | BASE API | 無料 |
| スケジューラー | cron (Linux) | VPS込み |
| 通知 | LINE Notify | 無料 |
| ダッシュボード | Google Sheets + GAS | 無料 |
| サーバー | Sakura or ConoHa VPS | 700-1,000 JPY/月 |

### データベーススキーマ (SQLite)

```sql
-- 仕入先から取得した商品
CREATE TABLE products (
  id                  INTEGER PRIMARY KEY AUTOINCREMENT,
  supplier            TEXT NOT NULL,            -- 'netsea' or 'topseller'
  supplier_product_id TEXT UNIQUE,
  name_ja             TEXT NOT NULL,
  name_en             TEXT,
  description_ja      TEXT,
  description_en      TEXT,
  category            TEXT,                     -- 'tenugui','furoshiki','knife','incense','washi'
  wholesale_price_jpy INTEGER,
  weight_g            INTEGER,
  image_urls          TEXT,                     -- JSON array
  stock_status        TEXT DEFAULT 'in_stock',  -- 'in_stock','out_of_stock','discontinued'
  last_stock_check    DATETIME,
  created_at          DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at          DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- プラットフォームに公開したリスティング
CREATE TABLE listings (
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

-- 注文
CREATE TABLE orders (
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

-- VeRO対策用ブランドブラックリスト
CREATE TABLE brand_blacklist (
  id                  INTEGER PRIMARY KEY AUTOINCREMENT,
  brand_name          TEXT UNIQUE NOT NULL,
  platform            TEXT,                     -- 'ebay','etsy','all'
  risk_level          TEXT DEFAULT 'high',      -- 'high','medium'
  notes               TEXT,
  added_at            DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 国別配送制限
CREATE TABLE country_restrictions (
  id                  INTEGER PRIMARY KEY AUTOINCREMENT,
  category            TEXT NOT NULL,            -- 'knife' etc.
  country_code        TEXT NOT NULL,            -- ISO 3166-1 alpha-2
  reason              TEXT,
  UNIQUE(category, country_code)
);
```

---

## 7. AIプロンプトテンプレート

### 商品説明生成（eBay向け）

```
System: You are an expert eBay copywriter specializing in Japanese cultural products
for international buyers. Write compelling, SEO-optimized listings.

User:
Product: {name_ja}
Category: {category}
Material: {material}
Size: {dimensions}
Weight: {weight_g}g
Wholesale Price: {wholesale_price_jpy} JPY

Rules:
- Title: max 80 chars, SEO keywords first
- Description: 3 paragraphs
  (1) What it is + Japanese cultural context
  (2) Quality/material details + dimensions
  (3) Shipping info + care instructions
- NEVER include brand names
- NEVER mention dropshipping or wholesale
- Include "Made in Japan" naturally

Output JSON:
{"title": "", "description": "", "item_specifics": {}}
```

### BANリスクチェッカー

```
System: You are a compliance checker for eBay/Etsy listings.

Check the following listing for:
1. Brand names in title or description (check against known VeRO brands)
2. Prohibited keywords that trigger automated review
3. Category correctness
4. Country restrictions (knives cannot ship to UK/IE)

Input: {listing_json}

Output JSON:
{"safe": true/false, "issues": [], "suggestions": [], "risk_level": "none|low|medium|high"}
```

### SEOタグ生成

```
System: Generate 13 Etsy-compatible tags (max 20 chars each) for this product.
Mix broad terms ("japanese fabric") and long-tail ("furoshiki gift wrap").
NEVER include brand names.

Product: {product_info}

Output JSON: {"tags": ["tag1", "tag2", ...]}
```

---

## 8. 実行タイムライン

### Phase 0: アカウントセットアップ（Day 1-3）

- [ ] eBay seller account + business policies（handling time: 3日）
- [ ] NETSEA 無料登録 + 候補20商品ブラウズ
- [ ] TopSeller 無料プラン登録 + CSV ダウンロード
- [ ] DeepL API Free key + Claude API key 取得
- [ ] (Optional) VPS契約

### Phase 1: 手動で初販売（Day 4-14）

- [ ] eRank キーワードリサーチ（検索ボリューム、競合）
- [ ] 最終5商品を選定（手ぬぐい3 + 風呂敷1 + お香1）
- [ ] Claude で英語商品説明を5商品分生成
- [ ] eBay に5リスティング公開（手動）
  - 包丁: **UK/IE必ず除外**
  - 全商品: handling time 3 business days
- [ ] 10日間 アナリティクスを毎日モニター（impressions, CTR, clicks）

### Phase 2: 自動化構築（Day 15-45）

- [ ] 商品スクレイパー（Python + Playwright → SQLite）
- [ ] AIリスティングパイプライン（Claude + DeepL + SEOタグ）
- [ ] BANリスクフィルター（ブランドブラックリスト + 国別制限）
- [ ] eBay API連携（DBから自動公開）
- [ ] 在庫同期 cron（15分間隔）
- [ ] 注文検知 + LINE Notify + 自動仕入れ

### Phase 3: スケール（Day 46-90）

- [ ] バッチ出品: 10 → 80 → 200商品
- [ ] Google Sheets ダッシュボード + GAS
- [ ] AI商品ローテーション（Claude が売上データ分析）
- [ ] BASE ストア開設（eBayトップセラー厳選）

### Phase 4: 最適化（Day 91+）

- [ ] A/Bテスト自動化（タイトルバリアント）
- [ ] Pinterest/Instagram マーケティング（BASE向け）
- [ ] 職人との直接取引
- [ ] (Optional) Etsy craft supplies チャネル

---

## 9. 自動化の効果

| タスク | 手動 | 自動化後 | 高速化 |
|--------|------|---------|--------|
| 商品リサーチ | 10分/商品 | 3秒/商品 | 200x |
| リスティング作成（EN） | 20-30分/商品 | 5秒/商品 | 300x |
| プラットフォーム公開 | 5-10分/商品 | 2秒/商品 | 200x |
| 在庫チェック | 1回/日（手動） | 15分間隔（自動） | 24/7 |
| 注文処理 | 15分/注文 | 0分（自動） | - |
| BANリスクチェック | 5-10分/商品 | 即時 | - |
| 売上分析 | 30分/日 | 自動ダッシュボード | - |
| **200商品合計** | **~67時間** | **~2時間** | **33x** |

---

## 10. AI活用ポイント

| 活用箇所 | Claude がやること | コスト/回 |
|---------|------------------|----------|
| 商品説明 | JA→EN ユニークリスティング + SEO | ~0.5 JPY |
| BANリスクチェック | ブランド名・ポリシー違反スキャン | ~0.3 JPY |
| SEOタグ | 最適化された13タグ生成 | 上記に含む |
| 競合分析 | トップ10結果分析、ギャップ発見 | ~1 JPY |
| 売上分析 | 週次データ分析、ローテーション提案 | ~2 JPY |
| A/Bタイトル | 2-3タイトルバリアント作成 | ~0.3 JPY |
| カスタマーサービス | バイヤーへの英語返信ドラフト | ~0.5 JPY |

**AI合計コスト: 500商品で ~800 JPY/月**

---

## 11. 成功確率

| シナリオ | 確率 | 12ヶ月後の月収 |
|---------|------|---------------|
| FAIL（1-2ヶ月で断念） | 25% | 0 |
| SURVIVE（副収入） | 40% | 3-8万円/月 |
| WIN（本業級） | 25% | 10-30万円/月 |
| BIG WIN（事業化） | 10% | 30-100万円/月 |

**成功率（何らかの収入あり）: 75%**

最大リスク: 月1-2で売上ゼロ期間に諦めること。eBayアルゴリズムがリスティングをランク付けするには時間が必要。

---

## 12. 競合優位性

| 強み | 詳細 |
|------|------|
| 日本在住 | NETSEA, TopSeller, JP Post料金に直接アクセス |
| プログラミングスキル | 自動化 = 手動競合者の33倍速 |
| MADE IN JAPAN | 価格プレミアム、価格非感応バイヤー |
| 円安 | JPY商品がUSD/EURバイヤーに割安に見える |
| BAN-safe設計 | コンプライアンスフィルターでアカウント停止を防止 |

---

## 13. 仕入先情報

### NETSEA (netsea.jp)

- 無料登録、200万商品以上
- フィルター: 「消費者直送可」（direct-to-consumer shipping OK）
- 検索キーワード: 手ぬぐい, 風呂敷, お香, 和紙
- 卸売価格帯: 300-8,000 JPY

### TopSeller (top-seller.jp)

- 無料プラン: 5商品まで
- DS特化（ドロップシッピング向け設計）
- CSV一括ダウンロード対応
- 包丁に強い

### 配送

| 方法 | 重量目安 | 費用 | 適した商品 |
|------|---------|------|-----------|
| ePacket Lite | ~50g (US宛) | ~580 JPY ($3.87) | 手ぬぐい、お香、和紙 |
| EMS | ~300g (US宛) | ~3,600 JPY ($24.00) | 包丁 |

---

## 14. 関連ファイル

| ファイル | 内容 |
|---------|------|
| `Japan_DropShip_BattlePlan_v2.docx` | 完全版ビジネスプラン（表付き） |
| `ActionPlan_JP.docx` | 日本語アクションプラン + 勝率分析 |
| `JAPAN_DROPSHIP_KB.md` | このファイル（AI用ナレッジベース） |

---

## 15. 推奨ディレクトリ構成

```
ec-automation/
├── CLAUDE.md                # Claude Code プロジェクトコンテキスト
├── JAPAN_DROPSHIP_KB.md     # このファイル
├── src/
│   ├── scraper/             # NETSEA/TopSeller スクレイパー
│   │   ├── netsea.py
│   │   └── topseller.py
│   ├── ai/                  # AI パイプライン
│   │   ├── description_generator.py
│   │   ├── ban_filter.py
│   │   └── seo_tags.py
│   ├── platforms/           # プラットフォーム連携
│   │   ├── ebay_api.py
│   │   └── base_api.py
│   ├── sync/                # 在庫・注文同期
│   │   ├── inventory_sync.py
│   │   └── order_handler.py
│   └── dashboard/           # アナリティクス
│       └── sheets_sync.py
├── data/
│   ├── dropship.db          # SQLite データベース
│   └── brand_blacklist.json
├── config/
│   ├── .env                 # APIキー（gitignore済み）
│   └── config.yaml          # プラットフォーム設定
├── scripts/
│   ├── setup_db.py          # DB初期化
│   └── cron_jobs.sh         # cron設定
├── tests/
│   └── test_ban_filter.py
└── requirements.txt
```

---

## Changelog

- 2026-02-19: v2 完成。eBay-first戦略。BAN-safe アーキテクチャ。Full KB作成。
- 2026-02-18: v1 作成 → 致命的問題発覚（Etsy DS禁止）→ v2 再設計開始。
