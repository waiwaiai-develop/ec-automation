# Japan DropShip Project — 完全ナレッジベース

> **目的**: このドキュメント1枚で、本プロジェクトの全てがわかる。
> 誰がいつ読んでも、背景・戦略・技術仕様・運用方法の全てが把握できるように設計されている。
> Claude Code や AI アシスタントにコンテキストとして渡すことを前提に構造化。
> 最終更新: 2026-02-20

---

## 設計思想: 完全自動化ファースト

**本プロジェクトは「人間が毎日作業する店」ではなく「AIとプログラムが回す自動販売システム」として設計する。**

自動化の対象:
- 商品リサーチ（スクレイピング + データ分析）
- 商品説明文の生成（Claude API、日英両対応）
- 出品（eBay API / BASE API）
- 在庫同期（15分間隔cron）
- 受注処理（自動検知 → 自動仕入れ発注）
- SNS投稿（画像生成 + 投稿文生成 + API投稿）
- カスタマーサポート（Claude APIで返信ドラフト → レビュー → 送信）
- 売上分析・商品ローテーション（週次自動レポート）
- A/Bテスト（タイトル・価格・SNSキャプションの自動比較）

**人間（Kei）がやること**:
- 戦略的な意思決定（新カテゴリ参入、価格戦略変更）
- 自動生成された内容のスポットレビュー
- TikTok動画の撮影（動画だけは自動化困難）
- 月次の帳簿確認

**目標**: 自動化完成後は1日15-30分の監視で運用可能な状態。

---

## 目次
1. プロジェクト概要
2. 意思決定ログ
3. ブランディング・ショップ名
4. 市場データ（なぜこの市場か）
5. プラットフォームポリシー
6. 商品戦略
7. 商品リサーチ手法（自動化）
8. 利益計算
9. インフラ・コスト
10. システムアーキテクチャ（DB含む）
11. AI プロンプトテンプレート
12. eBay Cassini SEO戦略
13. BASE戦略（国内+海外）
14. SNS戦略+自動投稿
15. マーケティングコスト
16. 実行タイムライン
17. 自動化一覧
18. AI連携ポイント
19. 成功確率
20. 競争優位性
21. 仕入先情報
22. リスク管理
23. 法務・税務
24. カスタマーサポート（自動化）
25. KPI・ダッシュボード
26. API仕様
27. 日次・週次・月次オペレーション
28. スケーリング戦略（月商50万円+）
29. Claude Code 使い方
30. ディレクトリ構造
31. ドキュメント一覧
32. 用語集
33. 更新履歴

---

## 1. プロジェクト概要

### 何をやるか
日本の文化商品（手ぬぐい、風呂敷、包丁、お香、和紙）を海外バイヤーにドロップシッピングで販売するEC事業。
加えてBASE国内向けにはジャンル制限なしで販売。
**商品選定からSNS発信まで全工程をAI+プログラミングで完全自動化**する。

### 誰がやるか
- オーナー: Kei。プログラミング・AI活用スキルあり。東京在住。
- 開発ツール: Claude Code（AI アシスト開発）
- 役割: システム構築者 → 完成後は監視者。手を動かすのはAIとcron。

### 顧客
- 海外: 米国・欧州の日本文化に関心のあるバイヤー
- 国内: 日本の一般消費者（BASE経由）

### チャネル戦略
- **eBay** → メインの収益チャネル。卸売DSが合法。集客力あり。月250件無料出品。
- **BASE（海外向け）** → eBay売れ筋を厳選。かんたん海外販売でwant.jpが発送代行。SNSから集客。
- **BASE（国内向け）** → ジャンル制限なし。SNS+Pay IDアプリで集客。
- **Etsy** → 現時点では不使用。将来craft supplies限定で検討。

### 3つの基本原則
1. **BAN回避ファースト**: ポリシー遵守が全ての前提。出品前に全件AIチェック。
2. **完全自動化**: 人間の作業を限りなくゼロに近づける。手動は戦略判断とTikTok撮影のみ。
3. **Day 60まで評価しない**: 初期の売上ゼロは正常。eBayアルゴリズムが評価するまで耐える。

---

## 2. 意思決定ログ

### v1 → v2 ピボット (2026-02-18 → 02-19)

| 項目 | v1（失敗） | v2（現行） |
|------|-----------|-----------|
| メインチャネル | Etsy | eBay |
| 問題 | Etsyはドロップシッピング禁止（craft supplies以外）。完成品の出品はポリシー違反で即BAN。 | eBayは卸売DSが合法。 |
| 教訓 | **プラットフォームポリシーの完全理解が出店前の最優先タスク。** | — |

### eBay集中の決定 (2026-02-20)
- eBayをメイン収益源、BASEをブランド構築+保険に位置づけ
- SNSはBASEへの集客エンジン
- Etsyは将来のcraft supplies限定チャネルとして保留

### BASE国内+海外の両建て決定 (2026-02-20)
- 2026年1月に「かんたん海外販売」正式リリース。want.jpが海外対応代行。
- 国内向けは追加コストゼロ。Pay IDアプリ（1,600万ユーザー）から無料露出。
- 国内向けはジャンル制限なし。トレンド商品・日用品も可。

### 完全自動化方針の決定 (2026-02-20)
- 商品選定、商品説明生成、出品、在庫同期、受注処理、SNS投稿、CS返信、売上分析まで全てAI+コードで自動化
- 人間がやるのは戦略判断と動画撮影のみ
- 目標: 自動化完成後は1日15-30分の監視運用

---

## 3. ブランディング・ショップ名

### ブランド名: **Yorimichi（寄り道）**

**由来**: 目的地への途中で思いがけず立ち寄ること。日本文化の商品を「発見する楽しさ」を表現。
8文字で短く覚えやすい。英語圏で発音可能。検索ユニーク性が高い。商品ジャンルを限定しない。

### 全チャネル名

| チャネル | ショップ名 | ID / URL |
|---------|-----------|----------|
| eBay | Yorimichi Japan | `yorimichi_japan` |
| BASE（海外） | Yorimichi — Japanese Goods | yorimichi.base.shop |
| BASE（国内） | 寄り道商店 | yorimichi-shouten.base.shop |
| Pinterest | Yorimichi Japan | pinterest.com/yorimichijapan |
| Instagram（EN） | @yorimichi.japan | 英語投稿 |
| Instagram（JP） | @yorimichi.shouten | 日本語投稿 |
| TikTok | @yorimichi.japan | EN/JP両方 |
| YouTube | Yorimichi Japan | Phase 3以降 |
| LinkTree | linktr.ee/yorimichijapan | 全リンク集約 |
| メール | hello@yorimichi.shop | ドメイン取得後 |

### タグライン

| チャネル | タグライン |
|---------|-----------|
| eBay | "Authentic Japanese goods, shipped from Tokyo." |
| BASE（海外） | "Discover Japan, one item at a time." |
| BASE（国内） | "日本のいいもの、寄り道して見つけよう。" |
| Instagram（EN） | "Your detour to Japanese craft & culture" |
| Instagram（JP） | "暮らしに寄り添う、日本のいいもの。" |

### ショップ説明文

**eBay:**
```
Welcome to Yorimichi Japan — your gateway to authentic Japanese craftsmanship.
We ship traditional Japanese goods directly from Tokyo: hand-dyed tenugui towels,
elegant furoshiki wrapping cloths, handcrafted kitchen knives, artisan incense,
and beautiful washi paper.

"Yorimichi" means "a pleasant detour" in Japanese — the joy of discovering
something unexpected.

Free shipping available on select items. 30-day returns accepted.
Questions? We respond within 24 hours.
```

**BASE（国内）:**
```
寄り道商店へようこそ。
日本各地のいいものを集めたオンラインセレクトショップです。
手ぬぐい、風呂敷、お香、和紙、暮らしの雑貨など、丁寧に選んだ商品をお届けします。
「寄り道」のように、ふと立ち寄って素敵なものに出会える。そんなお店を目指しています。
```

### ビジュアル
- ロゴ: Canva Freeで作成。サンセリフフォント + 鳥居 or 波のアイコン
- カラー: 藍色 `#264653` / 朱色 `#E76F51` / 生成色 `#FEFAE0` / 墨色 `#2A2A2A`
- フォント: Noto Sans JP + Inter（Google Fonts無料）

---

## 4. 市場データ

### 越境EC市場
- 世界のDS市場: 2025年に約4,350億ドル（約64兆円）。年+23.6%成長。
- 日本→米国のEC販売額: 1兆5,978億円（+8.0%）
- 日本→中国のEC販売額: 2兆6,372億円（+8.5%）
- 合計: **4兆2,350億円**（経済産業省 2025年8月）
- 対比: 日本人が海外から買う額は4,208億円 → 売る額の9分の1以下 → **日本は「売る側」として圧倒的に有利**

### 3つの構造的追い風
1. **円安**: 海外消費者から見て日本商品が割安
2. **インバウンド→越境EC**: 訪日中に購入した商品を帰国後にECで再購入する人が44.0%（BEENOS調査）
3. **"MADE IN JAPAN"の信頼**: クラフト系商品は信頼がそのまま価格プレミアムになる

### 注意
「出せば売れる」時代は終わり。商品選定とSEOの精度が勝負を分ける → **ここにAI自動化の強みが活きる**

---

## 5. プラットフォームポリシー

### eBay
- DS: **合法**（卸売仕入先からの直送OK。AliExpress等の小売DSは違反）
- VeRO: ブランド名をリスティングに含めると即ペナルティ（1回目=警告、2回目=停止、3回目=永久BAN）
- Defect Rate: 0.5%未満必須。超過でランキング激減
- Late Shipment Rate: 3%未満
- 包丁: **UK/アイルランドへの配送禁止**（Offensive Weapons Act 2019）→ 出品時に自動除外
- 新規セラー制限: 月250件 or $25,000まで
- → **BANフィルター（AI）が全出品を自動チェック。ブランド名検出・国制限・利益率を出品前に検証。**

### Etsy（将来参考）
- DS: **禁止**（craft supplies除く）
- 日本セラー手数料: 6%+$0.30/件
- セットアップ費: $15-29

### BASE
- DS: **制限なし**
- スタンダード: 決済3.6%+40円 + サービス3% = 合計6.6%+40円
- かんたん海外販売: 追加5%（want.jp代行）
- Pay ID経由: 9.5%+40円（高い）
- 集客力: ほぼゼロ → SNS自動投稿で集客

### 絶対禁止事項（BANフィルターに組み込む）
1. ブランド名をリスティングに含める
2. 仕入先の説明文をコピペ
3. 在庫切れ商品の放置
4. 包丁のUK/IE配送
5. 購入者メッセージの24時間以上放置

---

## 6. 商品戦略

### 自動スコアリング基準（7項目）
BANフィルターと利益計算エンジンが全商品を自動スコアリング:
1. 破損リスク（DSは梱包制御不可）
2. eBayポリシー適合
3. VeROリスク（ブランド名問題）
4. 配送コスト（重量ベース）
5. リピート購入可能性
6. 1個あたり利益（25%以上のみ通過）
7. 競合密度（Terapeakデータ）

### 海外向け主力商品

| 商品 | スコア | 利益/個 | 特徴 |
|------|--------|---------|------|
| 手ぬぐい/風呂敷 | 7/7 | $3-8 | **最優先**。破損ゼロ、超軽量、VeROゼロ |
| 包丁 | 5/7 | $15-60 | 単価最高。UK/IE除外必須 |
| お香 | 6/7 | $4-10 | リピート率最高（消耗品） |
| 和紙/文具 | 7/7 | $3-7 | 破損ゼロ、軽量 |

### 国内向け（BASEジャンル自由）
- eBay海外商品の国内版
- NETSEAトレンド商品
- SNSでバズった商品の即出品 → **トレンド検知もスクリプトで自動化**

---

## 7. 商品リサーチ（自動化）

### 自動リサーチパイプライン
```
[Terapeak/eRank データ取得（スクレイピング）]
  → "japanese"関連キーワードの需要・競合・価格データ
  ↓
[NETSEA/TopSeller 商品データ取得（スクレイパー）]
  → 仕入れ可能商品とマッチング
  → 「消費者直送可」フィルター
  ↓
[利益計算エンジン]
  → 仕入価格 + 手数料 + 送料 → 利益率25%以上のみ通過
  ↓
[BANリスクフィルター（Claude API）]
  → ブランド名チェック + 国制限チェック
  ↓
[スコアリング]
  → 7項目で自動採点 → 上位商品を出品キューに投入
  ↓
[出品（eBay API / BASE API）]
  → Claude APIで商品説明自動生成 → 自動出品
```

**手動: 1商品10分 × 200商品 = 33時間**
**自動: 200商品 = 数分**

### Terapeak活用（自動化対象）
- Seller Hub内で無料。キーワードごとの90日間売上・平均価格・sell-through rate
- 自動スクレイピングでデータ取得 → SQLiteに保存 → 週次で更新

### eRank/EtsyHunt（参考データ）
- 検索ボリューム・競合数・クリック率
- 「検索多い × 競合少ない」キーワード = 狙い目

---

## 8. 利益計算

### 為替前提: 1 USD = 150 JPY

### 手ぬぐい eBay（$15販売）
| 項目 | 金額 |
|------|------|
| 仕入（NETSEA平均） | $2-4 (300-600円) |
| 国際送料（ePacket ~50g） | $3.87 (580円) |
| eBay手数料（13.25%） | $1.99 |
| 決済手数料 | $0.30 |
| **合計コスト** | **$8.16-10.16** |
| **利益** | **$4.84-6.84 (32-46%)** |

### 包丁 eBay（$100販売、仕入5,000円）
| 項目 | 金額 |
|------|------|
| 仕入 | $33.33 |
| 国際送料（EMS ~300g） | $24.00 |
| eBay手数料（13.25%） | $13.25 |
| 決済手数料 | $0.30 |
| **合計コスト** | **$70.88** |
| **利益** | **$29.12 (29%)** |

### 手ぬぐい BASE海外（2,500円販売）
| 項目 | 金額 |
|------|------|
| 仕入 | 300-600円 |
| 決済（3.6%+40円） | 130円 |
| サービス（3%） | 75円 |
| 海外販売（5%） | 125円 |
| **合計コスト** | **630-930円** |
| **利益** | **1,570-1,870円 (63-75%)** |

### 月次売上シミュレーション
| 月 | 出品数 | 販売/月 | 平均利益 | 月間収益 | 日次作業 |
|---|--------|---------|----------|----------|----------|
| 1 | 10 | 2-5件 | $6 | $12-30 | 2-3h（構築中） |
| 2 | 30 | 5-12件 | $8 | $40-96 | 1h（自動化途中） |
| 3 | 80 | 12-25件 | $10 | $120-250 | 30min（自動化完了） |
| 4-6 | 200 | 30-60件 | $12 | $360-720 | 15min（監視のみ） |
| 7-12 | 500+ | 60-150件 | $15 | $900-2,250 | 15min |

### 損益分岐点
月額固定費 ~3,000円 ÷ 平均利益 ~$6/件 = **月3-4件で黒字**

---

## 9. インフラ・コスト

### 月額固定費
| 項目 | 費用 | 備考 |
|------|------|------|
| VPS（さくら/ConoHa） | 700-1,000円 | スクレイパー、cron、DB、SNSボット全てここ |
| SQLite | 0円 | ファイルベースDB |
| Claude API（Sonnet） | 100-800円 | 商品説明+SNS投稿+CS返信+分析 |
| DeepL API Free | 0円 | 50万文字/月無料 |
| TopSeller | 0円 | 無料プラン（5商品） |
| NETSEA | 0円 | 登録無料 |
| eBay | 0円 | ストア契約不要。250件/月無料 |
| BASE | 0円 | 販売時のみ手数料 |
| SNSツール（Buffer/Tailwind無料枠） | 0円 | |
| **合計（50商品）** | **~2,300-3,400円/月** |
| **合計（200商品）** | **~2,800-3,900円/月** |

### 初期投資: ~1,000円（VPS初月のみ）

---

## 10. システムアーキテクチャ

### 全体データフロー（完全自動化版）
```
━━━ 商品パイプライン ━━━
[NETSEA/TopSeller]
  → スクレイパー（Python + Playwright）→ SQLite products テーブル
  → BANフィルター（Claude API）: ブランド名・国制限・利益率チェック
  → 商品説明生成（Claude API）: EN + JP 同時生成
  → SEOタグ生成（Claude API）
  → チャネルルーター → eBay API / BASE API で自動出品

━━━ 在庫同期 ━━━
[cron 15分間隔]
  → 仕入先の在庫状況スクレイプ
  → DB更新 → 在庫切れ商品は自動非公開 → LINE Notify

━━━ 受注処理 ━━━
[eBay/BASE 注文検知（webhook/polling）]
  → 自動で仕入先に発注
  → 追跡番号取得 → 購入者に自動通知
  → LINE Notify でオーナーにアラート

━━━ SNS自動投稿 ━━━
[SQLite 商品データ]
  → 投稿文生成（Claude API）: EN + JP
  → 画像加工（Pillow）: ピン用2:3、IG用1:1、ストーリー用9:16
  → Pinterest API / Instagram API / Buffer → cron で定時投稿
  → 投稿パフォーマンスを自動取得 → analytics テーブルに保存

━━━ カスタマーサポート ━━━
[eBay/BASE メッセージ検知]
  → Claude API で返信ドラフト生成
  → LINE Notify でオーナーに確認依頼
  → 承認後 → API経由で送信（または手動送信）

━━━ 分析・最適化 ━━━
[週次cron]
  → 売上データ集計 → Claude API で分析レポート生成
  → 下位10%商品の自動取下げ提案
  → A/Bテスト結果の自動判定
  → Google Sheets ダッシュボード更新
```

### 技術スタック
| コンポーネント | 技術 | 費用 |
|--------------|------|------|
| 言語 | Python 3.11+ | 無料 |
| スクレイパー | Playwright | 無料 |
| データベース | SQLite 3 | 無料 |
| AI（説明文/SNS/CS/分析） | Claude API (claude-sonnet-4-20250514) | ~0.5円/商品 |
| 翻訳 | DeepL API Free | 無料 |
| 画像加工 | Pillow (PIL) | 無料 |
| eBay連携 | eBay REST APIs | 無料 |
| BASE連携 | BASE API | 無料 |
| Pinterest連携 | Pinterest API v5 | 無料 |
| Instagram連携 | Meta Graph API | 無料 |
| スケジューラー | cron (Linux) | VPS内 |
| アラート | LINE Notify API | 無料 |
| ダッシュボード | Google Sheets + Apps Script | 無料 |
| VPS | さくら or ConoHa (Ubuntu) | 700-1,000円/月 |
| バージョン管理 | Git + GitHub | 無料 |

### データベーススキーマ（SQLite）
```sql
-- 仕入先から取得した商品マスター
CREATE TABLE products (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  supplier TEXT NOT NULL,             -- 'netsea' / 'topseller'
  supplier_product_id TEXT UNIQUE,
  name_ja TEXT NOT NULL,
  name_en TEXT,
  description_ja TEXT,
  description_en TEXT,
  category TEXT,                      -- 'tenugui','furoshiki','knife','incense','washi','other'
  wholesale_price_jpy INTEGER,
  weight_g INTEGER,
  dimensions TEXT,
  material TEXT,
  image_urls TEXT,                    -- JSON配列
  stock_status TEXT DEFAULT 'in_stock',
  ban_score REAL,                     -- BANフィルターのリスクスコア (0.0-1.0)
  profit_score REAL,                  -- 利益率スコア
  demand_score REAL,                  -- Terapeak需要スコア
  total_score REAL,                   -- 総合スコア（上記の加重平均）
  last_stock_check DATETIME,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 各プラットフォームのリスティング
CREATE TABLE listings (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  product_id INTEGER REFERENCES products(id),
  platform TEXT NOT NULL,             -- 'ebay','base_overseas','base_domestic'
  platform_listing_id TEXT,
  title_en TEXT,
  title_ja TEXT,
  description_en TEXT,
  description_ja TEXT,
  tags TEXT,                          -- JSON配列
  price_usd REAL,
  price_jpy INTEGER,
  shipping_cost_usd REAL,
  status TEXT DEFAULT 'draft',        -- 'draft','active','paused','sold','removed'
  ban_check_passed BOOLEAN DEFAULT FALSE,
  ban_check_issues TEXT,              -- JSON配列
  excluded_countries TEXT,            -- JSON配列 例: ["GB","IE"]
  views INTEGER DEFAULT 0,
  favorites INTEGER DEFAULT 0,
  sales INTEGER DEFAULT 0,
  ab_test_variant TEXT,               -- 'A' / 'B'
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 受注データ
CREATE TABLE orders (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  listing_id INTEGER REFERENCES listings(id),
  platform TEXT NOT NULL,
  platform_order_id TEXT,
  buyer_country TEXT,
  buyer_name TEXT,
  sale_price_usd REAL,
  sale_price_jpy INTEGER,
  platform_fees_usd REAL,
  platform_fees_jpy INTEGER,
  shipping_cost_usd REAL,
  shipping_cost_jpy INTEGER,
  wholesale_cost_jpy INTEGER,
  profit_usd REAL,
  profit_jpy INTEGER,
  status TEXT DEFAULT 'pending',      -- 'pending','auto_purchased','shipped','delivered','returned','issue'
  supplier_order_id TEXT,
  tracking_number TEXT,
  auto_purchased_at DATETIME,         -- 自動仕入れ発注日時
  shipped_at DATETIME,
  delivered_at DATETIME,
  notes TEXT,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- VeROブランドブラックリスト
CREATE TABLE brand_blacklist (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  brand_name TEXT UNIQUE NOT NULL,
  platform TEXT DEFAULT 'all',
  risk_level TEXT DEFAULT 'high',
  notes TEXT,
  added_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 国別配送制限
CREATE TABLE country_restrictions (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  category TEXT NOT NULL,
  country_code TEXT NOT NULL,
  reason TEXT,
  UNIQUE(category, country_code)
);

-- SNS投稿ログ
CREATE TABLE sns_posts (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  product_id INTEGER REFERENCES products(id),
  platform TEXT NOT NULL,             -- 'pinterest','instagram_en','instagram_jp','tiktok'
  post_id TEXT,
  content_text TEXT,
  image_path TEXT,
  hashtags TEXT,                      -- JSON配列
  link_url TEXT,
  status TEXT DEFAULT 'scheduled',    -- 'scheduled','posted','failed'
  impressions INTEGER DEFAULT 0,
  clicks INTEGER DEFAULT 0,
  saves INTEGER DEFAULT 0,
  scheduled_at DATETIME,
  posted_at DATETIME,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- A/Bテスト
CREATE TABLE ab_tests (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  listing_id INTEGER REFERENCES listings(id),
  test_type TEXT,                     -- 'title','price','description','sns_caption'
  variant_a TEXT,
  variant_b TEXT,
  variant_a_views INTEGER DEFAULT 0,
  variant_a_clicks INTEGER DEFAULT 0,
  variant_a_sales INTEGER DEFAULT 0,
  variant_b_views INTEGER DEFAULT 0,
  variant_b_clicks INTEGER DEFAULT 0,
  variant_b_sales INTEGER DEFAULT 0,
  winner TEXT,
  started_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  ended_at DATETIME,
  status TEXT DEFAULT 'running'
);

-- カスタマーサポートログ
CREATE TABLE cs_messages (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  order_id INTEGER REFERENCES orders(id),
  platform TEXT NOT NULL,
  direction TEXT NOT NULL,            -- 'inbound' / 'outbound'
  original_message TEXT,
  ai_draft TEXT,                      -- Claude APIが生成した返信ドラフト
  final_message TEXT,                 -- 実際に送信したメッセージ
  auto_approved BOOLEAN DEFAULT FALSE,-- 自動承認されたか
  responded_at DATETIME,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

---

## 11. AIプロンプトテンプレート

全てのプロンプトは `src/ai/` 配下のPythonモジュールに組み込み、cron/APIから自動呼び出しされる。

### 商品説明生成（eBay英語）
```
System: eBayの日本文化商品に特化したSEOコピーライター。
ルール:
- タイトル: 最大80文字。キーワードを先頭に配置。"Japanese"と"Made in Japan"を含める
- 説明: 3段落（①文化的背景 ②素材・サイズ詳細 ③配送・手入れ）
- ブランド名は絶対に含めない
- DS・卸売・転売には絶対に触れない
- Item Specifics も生成: Material, Color, Size, Country/Region of Manufacture
出力: JSON {"title":"","description":"","item_specifics":{}}
```

### 商品説明生成（BASE国内 日本語）
```
System: BASEネットショップの商品説明ライター。国内消費者向け。
ルール:
- 商品名: 50文字以内。検索キーワードを含む
- 説明: 3段落（①魅力・特徴 ②素材・使い方 ③ギフト用途）
- 丁寧な日本語
出力: JSON {"title_ja":"","description_ja":""}
```

### BANリスクチェック（全出品に自動適用）
```
System: eBayコンプライアンスチェッカー。
チェック項目:
1. タイトル/説明にブランド名がないか（VeROデータベース照合）
2. 自動レビューをトリガーする禁止キーワード
3. カテゴリ整合性
4. 国制限（包丁→UK/IE不可）
5. 虚偽表示（"handmade"等）
出力: JSON {"safe":true/false,"issues":[],"risk_level":"none|low|medium|high"}
```

### SNS投稿文生成（Pinterest英語）
```
System: Pinterest SEO特化コンテンツクリエイター。日本文化商品。
ルール:
- タイトル: 100文字以内、キーワード多め
- 説明: 2-3文、キーワード自然に含む
- "Made in Japan", "authentic" を含む
- ハッシュタグ5個
- CTA: "Shop now" or "Discover more"
出力: JSON {"title":"","description":"","hashtags":[],"link":""}
```

### SNS投稿文生成（Instagram日本語）
```
System: 日本の生活雑貨ブランドのInstagram担当者。
ルール:
- キャプション: 150-300文字
- 絵文字1-2個まで
- ハッシュタグ20個（大#暮らし / 中#手ぬぐい / 小#手ぬぐいのある暮らし）
- CTA: BASEリンクへ誘導
出力: JSON {"caption":"","hashtags":[],"alt_text":""}
```

### カスタマーサポート返信ドラフト（自動生成）
```
System: eBayの日本雑貨ストアのカスタマーサポート担当。
ルール:
- プロフェッショナルかつフレンドリー
- 追跡情報がある場合は含める
- 問題がある場合は解決策を提案（部分返金/交換/全額返金）
- 150語以内
- 購入者のメッセージと注文情報を元に返信
出力: JSON {"reply":"","suggested_action":"none|partial_refund|full_refund|replacement"}
```

### 週次分析レポート（自動生成）
```
System: ECビジネスのデータアナリスト。
入力: 過去7日間の売上データ、CTR、CVR、SNSパフォーマンス
ルール:
- 好調な商品トップ5と不調な商品ワースト5を特定
- 不調商品の改善提案（タイトル変更/価格変更/取下げ）
- SNSで最もトラフィックを生んだ投稿
- 来週のアクション提案
出力: 日本語のMarkdownレポート
```

---

## 12. eBay Cassini SEO戦略

### Cassiniランキング要因

| 要因 | 重要度 | 自動化アクション |
|------|--------|----------------|
| タイトルキーワード | 最重要 | Claude APIが検索語を分析してSEOタイトル自動生成 |
| Item Specifics | 最重要 | 全項目を自動入力（Material, Brand:Unbranded, Country:Japan等） |
| 写真 | 高 | 仕入先画像を自動取得 + Pillowで白背景加工 |
| セラー実績 | 高 | Defect Rate 0%維持。CSを24h以内にAI返信 |
| 販売速度 | 高 | 初期価格を市場の87-92%に設定。利益計算エンジンが自動算出 |
| CTR+CVR | 中 | A/Bテスト自動化。低CTR商品は自動でタイトル変更 |
| 送料 | 中 | Free Shipping設定。送料は商品価格に含める |
| 新規ブースト | 中 | 毎日10-20件を定時出品（火曜ET10-11AMに集中） |
| Best Offer | 低 | 全商品でON |
| 30日返品 | 低 | 全商品で30日返品OK |

### eBayタイトル公式
```
[商品タイプ] [素材] [スタイル/柄] [用途] [産地] [サイズ]
例: Japanese Tenugui Cotton Hand Towel Traditional Wave Pattern Made in Japan 35x90cm
```

### 出品チェックリスト（BANフィルターが自動検証）
- タイトル80文字フル活用
- Item Specifics全入力
- 写真5枚以上
- 価格: Terapeak中央値の87-92%
- Free Shipping
- ハンドリングタイム: 3営業日
- 30日返品OK
- Best Offer ON
- 包丁の場合UK/IE除外

---

## 13. BASE戦略（国内+海外）

### 海外向け
- かんたん海外販売ON（want.jp代行）
- 英語・外貨対応App
- 商品: eBay売れ筋の上位を厳選
- 手数料合計: 約11.6%+40円
- 集客: Pinterest(EN) + Instagram(EN) → BASE

### 国内向け
- ジャンル制限なし
- Pay IDアプリ掲載（無料露出、ただし手数料9.5%+40円）
- 集客: Instagram(JP) + TikTok(JP) → BASE
- 商品: eBay海外商品の国内版 + NETSEAトレンド + SNSバズ商品

### 展開フロー（自動化）
```
Month 1-2: eBayで売上データ自動収集
Month 2-3: 売上上位を自動でBASE海外に出品。国内向け商品もスクレイパーで自動選定。
Month 3+:  SNS自動投稿トラフィック → BASE売上成長
```

---

## 14. SNS戦略+自動投稿

### チャネル構成

| プラットフォーム | 言語 | 対象 | 投稿/週 | 自動化レベル |
|----------------|------|------|---------|------------|
| Pinterest | EN | 海外 | 15ピン | **完全自動**（API） |
| Instagram(EN) | EN | 海外 | 5投稿 | **半自動**（AI生成→Buffer→cron） |
| Instagram(JP) | JP | 国内 | 3投稿 | **半自動** |
| TikTok | EN/JP | 両方 | 3動画 | 手動撮影→自動スケジュール |
| YouTube | EN | 海外 | 月2-4本 | 手動（Phase 3+） |

### 自動投稿パイプライン
```
[SQLite: 売れ筋商品データ]
  → Claude API: 投稿文生成（EN + JP同時）
  → Pillow: 画像加工
    - Pinterest: 1000x1500px（2:3）テキストオーバーレイ
    - Instagram: 1080x1080px + 1080x1920px
  → 投稿スケジューラ
    - Pinterest: Pinterest API v5 → 自動ピン
    - Instagram: Meta Graph API or Buffer Free → 半自動
    - cron: 毎日指定時刻に実行
  → パフォーマンス自動取得 → sns_posts テーブル更新
```

### ハッシュタグDB（`data/hashtag_db.json`）
```json
{
  "en_large": ["#japaneseculture","#madeinjapan","#japanlife","#homedecor"],
  "en_medium": ["#tenugui","#furoshiki","#japaneseknife","#japaneseincense"],
  "en_niche": ["#japanesehandtowel","#furoshikiwrap","#japancrafts"],
  "jp_large": ["#暮らし","#日本製","#丁寧な暮らし","#和雑貨"],
  "jp_medium": ["#手ぬぐい","#風呂敷","#包丁","#お香"],
  "jp_niche": ["#手ぬぐいのある暮らし","#風呂敷包み","#和の暮らし"]
}
```

### Pinterestボード構成
| ボード名 | コンテンツ比率 |
|---------|-------------|
| Japanese Tenugui - Traditional Hand Towels | 商品80% + 使い方20% |
| Furoshiki Gift Wrapping Ideas | 商品40% + How-to 60% |
| Japanese Kitchen Knives | 商品70% + 料理30% |
| Japanese Incense & Wellness | 商品50% + ライフスタイル50% |
| Gift Ideas from Japan | 商品50% + キュレーション50% |
| Made in Japan - Craftsmanship | 職人写真 + 文化解説 |

---

## 15. マーケティングコスト

### 無料施策（全部やる）
Pinterest/Instagram/TikTokオーガニック、eBay Terapeak、BASE Pay ID、メルマガ、Canva Free、Buffer/Tailwind無料枠

### 少額投資（ROI > 3倍で継続）
| 施策 | コスト | Phase |
|------|--------|-------|
| eBay Promoted Listings | 売上の2-5%（成果報酬） | Phase 1+ |
| Canva Pro | 1,500円/月 | Phase 3+ |
| Pinterest/Instagram広告 | $5-10/月 | Phase 3+ |

---

## 16. 実行タイムライン

### Phase 0: アカウント開設 (Day 1-3)
- [ ] eBayセラーアカウント + ビジネスポリシー設定
- [ ] NETSEA/TopSeller登録
- [ ] DeepL/Claude APIキー取得
- [ ] VPS契約
- [ ] 全SNSアカウント開設（Section 3参照）
- [ ] BASE開設 + かんたん海外販売 + 英語対応App
- [ ] LinkTree設定
- [ ] Gitリポジトリ初期化

### Phase 1: 手動初売上 + SNS開始 (Day 4-14)
- [ ] Terapeak調査
- [ ] 5商品手動出品（3手ぬぐい + 1風呂敷 + 1お香）
- [ ] Promoted Listings 2%でON
- [ ] Pinterest 7ボード作成 + 毎日2ピン（手動）
- [ ] Instagram 初期9投稿（手動）

### Phase 2: 自動化構築 (Day 15-45)
- [ ] 商品スクレイパー（NETSEA/TopSeller → SQLite）
- [ ] BANフィルター（Claude API）
- [ ] 商品説明自動生成パイプライン（Claude API + DeepL）
- [ ] eBay API自動出品
- [ ] BASE API自動出品（海外+国内）
- [ ] 在庫同期cron（15分間隔）
- [ ] 受注自動検知 + LINE Notify + 自動仕入れ発注
- [ ] SNS自動投稿システム構築
- [ ] CS自動返信ドラフトシステム
- [ ] メルマガ設定（BASEアプリ）

### Phase 3: スケール (Day 46-90)
- [ ] eBay 200+出品（自動）
- [ ] BASE 50+商品（海外）+ 国内商品追加（自動）
- [ ] SNS完全自動ルーティン稼働
- [ ] TikTok動画制作開始（手動撮影→自動スケジュール）
- [ ] マイクロ広告テスト
- [ ] Google Sheetsダッシュボード構築
- [ ] 週次自動分析レポート稼働

### Phase 4: 最適化 (Day 91+)
- [ ] A/Bテスト自動化
- [ ] YouTube開始
- [ ] 広告拡大（ROI 3倍以上のみ）
- [ ] 職人直接取引
- [ ] （任意）Etsy craft supplies

---

## 17. 自動化一覧

| タスク | 手動時間 | 自動化後 | 倍速 | 実装Phase |
|--------|---------|---------|------|----------|
| 商品リサーチ | 10分/商品 | 3秒 | 200x | 2 |
| 商品説明（EN） | 25分/商品 | 5秒 | 300x | 2 |
| 商品説明（JP） | 15分/商品 | 5秒 | 180x | 2 |
| 出品 | 8分/商品 | 2秒 | 240x | 2 |
| 在庫確認 | 1日1回 | 15分間隔 | 24/7 | 2 |
| 受注処理 | 15分/件 | 0分 | ∞ | 2 |
| BANチェック | 8分/商品 | 即時 | ∞ | 2 |
| SNS投稿作成 | 15分/投稿 | 10秒 | 90x | 2 |
| SNS投稿実行 | 5分/投稿 | 0分（cron） | ∞ | 2 |
| CS返信ドラフト | 10分/件 | 5秒 | 120x | 2 |
| 画像加工（SNS） | 10分/枚 | 3秒 | 200x | 2 |
| 売上分析 | 30分/日 | 自動レポート | ∞ | 3 |
| A/Bテスト管理 | 20分/日 | 自動判定 | ∞ | 4 |
| **200商品の全工程** | **~80時間** | **~2時間** | **40倍** | — |

---

## 18. AI連携ポイント

| 連携先 | AIがやること | コスト/回 |
|--------|------------|----------|
| eBay商品説明 | JA→EN SEOリスティング生成 | ~0.5円 |
| BASE商品説明 | 国内向け日本語説明生成 | ~0.3円 |
| BANチェック | ブランド名・ポリシー違反検出 | ~0.3円 |
| SEOタグ | 13個のタグ自動生成 | 含む |
| SNS投稿（EN） | Pinterestピン + IGキャプション | ~0.5円 |
| SNS投稿（JP） | IG日本語キャプション | ~0.3円 |
| CS返信 | 英語返信ドラフト | ~0.5円 |
| 週次分析 | 売上分析+改善提案レポート | ~2円 |
| A/Bテスト | タイトルバリエーション生成 | ~0.3円 |
| 画像テキスト | Pinterestピンのテキストオーバーレイ文 | ~0.2円 |

**月間AI費用: ~1,000円（500商品 + 毎日SNS + CS対応含む）**

---

## 19. 成功確率

| シナリオ | 確率 | 月12の収益 |
|---------|------|-----------|
| 失敗（Month 1-2で挫折） | 25% | 0 |
| 生存（副収入） | 40% | 3-8万円/月 |
| 成功（本収入） | 25% | 10-30万円/月 |
| 大成功（スケール事業） | 10% | 30-100万円/月 |

**成功率（収入あり）: 75%**
**最大リスク: Month 1-2の売上ゼロ期間で挫折すること。自動化はDay 45までに完成するので、そこまで走り切る。**

---

## 20. 競争優位性

| 優位性 | 詳細 |
|--------|------|
| 日本在住 | NETSEA/TopSeller/JP Post直接アクセス。職人直接取引可能 |
| プログラミング | **完全自動化 = 40倍速**。手動の競合は絶対に追いつけない |
| AI活用 | 商品説明・SNS・CS・分析まで全てAI。コスト月~1,000円 |
| MADE IN JAPAN | 価格に敏感でないバイヤー。文化的価値 > コモディティ価格 |
| 円安 | 構造的追い風。海外バイヤーから見て日本商品が割安 |
| BAN-safe設計 | 全出品をAIがチェック。ほとんどのDSセラーは6ヶ月でBANされる |
| デュアルチャネル | eBay + BASE。片方が停止しても他方で継続 |
| SNS自動化 | 一貫した投稿を人的コストゼロで実現。複利で効く |

---

## 21. 仕入先情報

### NETSEA (netsea.jp)
- 登録無料（法人/個人事業主）。商品200万件超
- フィルター: 「消費者直送可」= DS対応
- 検索語: 手ぬぐい、風呂敷、お香、和紙、包丁
- 卸売価格帯: 300-8,000円
- **スクレイパーで自動データ取得 → SQLiteに保存**

### TopSeller (top-seller.jp)
- 無料プラン: 5商品。DS特化。CSV一括ダウンロード
- 包丁・キッチンツールに強い

### 配送オプション
| サービス | 重量 | 米国まで | 配達日数 |
|---------|------|---------|---------|
| ePacket Lite | ~50g | ~580円 | 7-14日 |
| ePacket | ~100g | ~800円 | 7-14日 |
| EMS | ~300g | ~3,600円 | 3-7日 |
| SAL | ~200g | ~1,200円 | 2-6週 |
| BASE海外(want.jp) | 変動 | アジア490円~/米国1,710円~ | 変動 |

---

## 22. リスク管理

| リスク | 確率 | 影響 | 自動化された対策 |
|--------|------|------|----------------|
| eBayアカウント停止 | 低 | 致命的 | BANフィルターが全出品を自動チェック。VeROリスト自動更新 |
| 在庫切れ+注文受付 | 中 | 高 | 15分cron在庫同期。OOS即自動非公開 |
| 仕入先の配送遅延 | 中 | 中 | ハンドリング3日で余裕。遅延時は自動通知 |
| 為替変動（円高） | 中 | 中 | 利益率25%以上のみ出品。10%円高でも黒字維持 |
| VeROクレーム | 低 | 高 | AIフィルターでブランド名検出。全件チェック |
| SNSアカウント凍結 | 低 | 中 | メールリスト構築でSNS依存回避 |
| **Month 1-2の挫折** | **高** | **致命的** | **「Day 60まで評価しない」をルール化** |

---

## 23. 法務・税務

### 開業届
- 個人事業主として税務署に提出（開業後1ヶ月以内）
- 青色申告承認申請書も同時提出

### 確定申告
- 年間所得20万円超（給与所得者）or 48万円超（専業）で必要
- 青色申告: 65万円特別控除
- 経費計上可能: VPS代、API費用、仕入代、送料、通信費、PC減価償却費

### 古物商許可
- 新品の卸売→販売は不要。ヴィンテージ品を扱う場合は要取得

### 特定商取引法
- BASEでは必須（販売業者名、所在地、電話番号、メール、返品ポリシー）
- バーチャルオフィス利用可

### 輸出規制
- 包丁: 刃渡り15cm以下なら日本輸出OK。UK/IEは輸入側が規制
- お香: スティック/コーン型はOK。液体/スプレー型は不可
- ワシントン条約: 象牙・べっ甲は絶対に扱わない

### 消費税
- 年間売上1,000万円以下は免税事業者
- 輸出取引は消費税免除。仕入消費税は還付申請可能

---

## 24. カスタマーサポート（自動化）

### 自動CSフロー
```
[eBay/BASEメッセージ受信]
  → 自動検知（webhook/polling）
  → Claude API でメッセージ分類 + 返信ドラフト生成
  → cs_messages テーブルに保存
  → LINE Notify でオーナーに通知（ドラフト内容表示）
  → オーナーが承認 or 修正 → 送信
  → (将来) 定型対応は自動承認・自動送信
```

### 対応テンプレート（AIが自動判断）

| 問い合わせ | 自動アクション |
|-----------|-------------|
| 配送状況 | 追跡番号を自動検索して返信ドラフト生成 |
| 商品未着（14日+） | 追跡調査。21日未着なら全額返金提案 |
| 商品破損 | 写真確認依頼ドラフト。低単価なら即返金提案 |
| 返品リクエスト | eBay返品フロー案内ドラフト |
| 値引き交渉 | 複数購入割引を提案 |

### エスカレーション（自動→手動）
- 購入者が怒っている → 即全額返金提案（Defect Rate防止優先）
- eBay Case open → 緊急LINE通知 → 24時間以内に手動対応
- $50以上の返品 → 手動判断

---

## 25. KPI・ダッシュボード

### 自動ダッシュボード（Google Sheets + GAS）
週次cronで自動更新。

### 毎日監視KPI

| KPI | 目標 | 自動アクション |
|-----|------|-------------|
| eBayインプレッション | 増加トレンド | 減少時にタイトル改善を自動提案 |
| eBay CTR | 2%以上 | 低CTR商品を自動フラグ |
| eBay CVR | 3%以上 | 低CVR商品の価格調整を提案 |
| Defect Rate | 0% | 異常時に即LINE通知 |

### 月次Go/No-Go

| チェックポイント | 日 | Go条件 |
|----------------|---|--------|
| Phase 1完了 | Day 14 | 5リスティングがライブ |
| Phase 2完了 | Day 45 | 自動化パイプライン稼働 |
| 初評価 | Day 60 | 月5件以上の販売 |
| Phase 3完了 | Day 90 | 月15件以上 + BASE稼働 |
| 半年評価 | Day 180 | 月10万円以上の純利益 |

---

## 26. API仕様

### eBay
| API | 用途 | 認証 |
|-----|------|------|
| Inventory API | 出品作成/更新 | OAuth 2.0 |
| Fulfillment API | 受注管理 | OAuth 2.0 |
| Browse API | 競合分析 | OAuth 2.0 |
| Analytics API | トラフィック/売上 | OAuth 2.0 |

サンドボックス: sandbox.ebay.com / レート制限: 5,000回/日

### BASE API
商品作成: `api.thebase.in/1/products` / 受注管理: `api.thebase.in/1/orders` / OAuth 2.0

### Claude API
モデル: `claude-sonnet-4-20250514` / エンドポイント: `api.anthropic.com/v1/messages`
温度: 0.7（説明文）/ 0.3（コンプライアンスチェック）

### DeepL API Free
エンドポイント: `api-free.deepl.com/v2/translate` / 50万文字/月

### Pinterest API v5
`POST /pins`（ピン作成）/ `POST /boards`（ボード作成）/ OAuth 2.0 / 1,000回/日

### Instagram (Meta Graph API)
`POST /{id}/media` → `POST /{id}/media_publish` / 25回/時間

### LINE Notify
`notify-api.line.me/api/notify` / Bearerトークン

---

## 27. 日次・週次・月次オペレーション

**自動化完成後の作業量: 1日15-30分**

### 毎日（自動化により大半は通知確認のみ）
- [ ] LINE通知確認（受注・在庫切れ・CS・エラー）
- [ ] CS返信ドラフト確認 → 承認/修正 → 送信
- [ ] SNS自動投稿の稼働確認

### 週次（1時間程度）
- [ ] 自動生成された週次レポートの確認
- [ ] 商品ローテーション提案の承認/却下
- [ ] A/Bテスト結果の確認
- [ ] 新商品候補の確認（スクレイパーが自動抽出）

### 月次（2-3時間）
- [ ] 月次P/L確認
- [ ] Promoted Listings ROI確認
- [ ] ブランドブラックリスト更新
- [ ] メールニュースレター確認→送信
- [ ] 帳簿整理（freee/マネーフォワード）

---

## 28. スケーリング戦略（月商50万円+）

### Phase 5: 成長（月商50万円超）
- BASE: グロースプラン切替（月額16,580円、手数料2.9%）
- eBay Store subscription検討
- Shopify検討（自社ドメイン）
- SEOブログ（WordPress）→ BASEへの流入

### Phase 6: 拡大（月商100万円超）
- 職人直接取引（独占商品）
- 法人化検討（年間所得800万円超で有利）
- CS外注（VA委託）
- Amazon Global Selling検討

### Phase 7: ブランド化（月商300万円超）
- 自社ブランド商品企画
- オリジナルパッケージ
- インフルエンサーマーケティング
- 実店舗/ポップアップ

---

## 29. Claude Code 使い方

### CLAUDE.md の内容
```markdown
# Japan DropShip Project
JAPAN_DROPSHIP_KB.md を読んでプロジェクト全体のコンテキストを把握すること。
現在のPhase: Phase 0
日本語で応答すること。コードのコメントも日本語。
```

### よく使うタスク
1. `NETSEAスクレイパー構築。Section 10のスキーマでSQLiteに保存`
2. `AI商品説明パイプライン。Section 11のプロンプト使用`
3. `BANフィルター。Section 5のポリシー参照`
4. `eBay API連携。Section 26のAPI仕様参照`
5. `SNS自動投稿。Section 14のアーキテクチャ参照`
6. `CS自動返信。Section 24のフロー参照`
7. `Google Sheetsダッシュボード。Section 25のKPI参照`

---

## 30. ディレクトリ構造

```
japan-dropship/
├── CLAUDE.md
├── JAPAN_DROPSHIP_KB.md          # このファイル
├── README.md
├── src/
│   ├── scraper/
│   │   ├── netsea.py
│   │   └── topseller.py
│   ├── ai/
│   │   ├── description_generator.py    # eBay英語
│   │   ├── description_generator_jp.py # BASE日本語
│   │   ├── ban_filter.py
│   │   ├── seo_tags.py
│   │   ├── sns_content_generator.py
│   │   ├── cs_responder.py             # CS自動返信
│   │   └── weekly_analyst.py           # 週次分析
│   ├── platforms/
│   │   ├── ebay_api.py
│   │   └── base_api.py
│   ├── sns/
│   │   ├── pinterest_poster.py
│   │   ├── instagram_poster.py
│   │   ├── tiktok_poster.py
│   │   └── image_processor.py          # Pillow画像加工
│   ├── sync/
│   │   ├── inventory_sync.py
│   │   └── order_handler.py            # 自動仕入れ発注含む
│   ├── cs/
│   │   └── message_handler.py          # CS受信→AI→通知
│   └── dashboard/
│       ├── sheets_sync.py
│       └── sns_analytics.py
├── data/
│   ├── dropship.db
│   ├── brand_blacklist.json
│   └── hashtag_db.json
├── config/
│   ├── .env                            # APIキー（gitignore）
│   ├── config.yaml
│   └── sns_schedule.yaml
├── scripts/
│   ├── setup_db.py
│   └── cron_jobs.sh                    # 全cron定義
├── tests/
│   ├── test_ban_filter.py
│   ├── test_sns_poster.py
│   └── test_inventory_sync.py
├── .gitignore
└── requirements.txt
```

---

## 31. ドキュメント一覧

| ファイル | 説明 |
|---------|------|
| `JAPAN_DROPSHIP_KB.md` | このファイル。唯一の真実の源泉。 |
| `Japan_DropShip_BattlePlan_v2.docx` | ビジネスプラン（英語、テーブル付き） |
| `ActionPlan_JP.docx` | 日本語アクションプラン |
| `CLAUDE.md` | Claude Codeプロジェクトコンテキスト |

---

## 32. 用語集

| 用語 | 意味 |
|------|------|
| DS | DropShipping。在庫を持たずに販売する手法 |
| VeRO | eBayのブランド保護プログラム。違反=即ペナルティ |
| Cassini | eBayの検索アルゴリズム |
| BAN | アカウント停止 |
| Defect Rate | eBayのセラー品質指標。0.5%超でペナルティ |
| CTR | Click-Through Rate。クリック率 |
| CVR | Conversion Rate。購入率 |
| NETSEA | 日本最大級BtoB卸売マーケットプレイス |
| TopSeller | DS特化仕入れサービス |
| ePacket | 日本郵便の小型国際配送サービス |
| EMS | 国際スピード郵便 |
| Item Specifics | eBayの商品属性フィールド |
| Terapeak | eBay内の無料リサーチツール |
| BASE | 日本のネットショップ作成サービス |
| want.jp | BASE「かんたん海外販売」の越境EC代行会社 |
| Pay ID | BASEのショッピングアプリ（1,600万ユーザー） |
| Pillow | Python画像処理ライブラリ |
| Playwright | Pythonブラウザ自動化ライブラリ |
| cron | Linux定期実行スケジューラー |
| GAS | Google Apps Script |
| P/L | 損益計算書 |
| ROI | 投資対効果 |
| OOS | Out of Stock。在庫切れ |
| VA | Virtual Assistant。外注アシスタント |

---

## 33. 更新履歴

| 日付 | 変更内容 |
|------|---------|
| 2026-02-20 | **KB完全版 v4**: 全文日本語化。完全自動化前提で再設計。CSテーブル追加。自動フロー図全面改訂。 |
| 2026-02-20 | ブランディング「Yorimichi（寄り道）」追加。全チャネル名・タグライン・説明文。 |
| 2026-02-20 | eBay Cassini戦略、BASE国内+海外、SNS自動投稿、マーケティングプラン追加。 |
| 2026-02-20 | Market Validation、商品リサーチ手法、リスク管理、法務税務、KPI等追加。 |
| 2026-02-19 | v2完成。eBay集中戦略。BAN-safe設計。 |
| 2026-02-18 | v1作成 → Etsy DS禁止の致命的欠陥発見 → v2再設計開始。 |