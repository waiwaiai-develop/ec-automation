# EC自動化 — 日本文化商品ドロップシッピングツール

日本の文化商品（手ぬぐい、風呂敷、包丁、お香、和紙）を海外バイヤーにドロップシッピングで販売するためのEC自動化システム。

## コンセプト

```
NETSEA/TopSeller（卸売サイト）
  → 商品収集（API/スクレイパー）
    → BANリスクフィルター（VeRO/ブランド/規制チェック）
      → 利益計算（送料・手数料込み、25%以上のみ）
        → AI商品説明生成（Claude API: 英語タイトル+説明文+SEOタグ）
          → eBay / Etsy に出品（自動化予定）
            → 在庫同期 + 注文処理（自動化予定）
```

## 販売チャネル

| チャネル | 戦略 | 対象商品 |
|---------|------|---------|
| **eBay** | メイン。卸売DSが合法 | 包丁、お香、手ぬぐい |
| **Etsy** | craft suppliesカテゴリ限定 | 手ぬぐい、風呂敷、和紙 |
| **Shopify** | Phase 4以降。保険用自前ショップ | 全商品 |

## 現在できること

### データベース管理
```bash
python -m src.cli.main db init     # テーブル作成+シードデータ
python -m src.cli.main db stats    # DB統計表示
```

### NETSEA商品取り込み
```bash
python -m src.cli.main netsea import -k 手ぬぐい -l 10       # 商品検索→DB保存
python -m src.cli.main netsea import -k 風呂敷 --dry-run     # プレビューのみ
python -m src.cli.main netsea categories                      # カテゴリ一覧
```

### eBayマーケットリサーチ
```bash
python -m src.cli.main research keywords -k "japanese tenugui" --sandbox
```
価格帯（平均/中央値/最低/最高）、送料、上位商品を分析。

### 商品管理
```bash
python -m src.cli.main product list                    # 商品一覧
python -m src.cli.main product check --id 1            # BANリスクチェック
python -m src.cli.main product check --all             # 全商品一括チェック
python -m src.cli.main product profit --id 1 --price 15.00  # 利益計算
python -m src.cli.main product describe --id 1         # AI商品説明生成
python -m src.cli.main product describe --id 1 --save  # 生成結果をDBに保存
```

## セットアップ

### 1. 依存パッケージ
```bash
pip install -r requirements.txt
playwright install chromium
```

### 2. 環境変数
```bash
cp config/.env.template config/.env
```

`config/.env` に以下のAPIキーを設定:

| キー | 用途 | 必須 |
|------|------|------|
| `NETSEA_API_TOKEN` | NETSEA商品取り込み | NETSEA利用時 |
| `EBAY_CLIENT_ID` / `EBAY_CLIENT_SECRET` | eBayリサーチ | リサーチ利用時 |
| `ANTHROPIC_API_KEY` | AI商品説明生成 | describe利用時 |

### 3. DB初期化
```bash
python -m src.cli.main db init
```

## テスト
```bash
pytest tests/
```

## テックスタック

- **言語**: Python
- **DB**: SQLite
- **スクレイパー**: Playwright
- **AI**: Claude API（商品説明生成、SEOタグ）
- **CLI**: Click + Rich
- **テスト**: pytest

## プロジェクト構成

```
src/
├── scraper/       NETSEA APIクライアント
├── research/      eBay Browse API / Playwrightスクレイパー
├── ai/            BANフィルター / 利益計算 / AI商品説明生成
├── db/            SQLiteデータベース（6テーブル）
└── cli/           CLIエントリポイント
config/            .env / config.yaml
tests/             テスト一式
data/              SQLite DBファイル（自動生成）
```

## 今後の実装予定

詳細は [Plans.md](Plans.md) を参照。

- **Phase 2**: Etsy/eBay出品API連携、在庫同期、注文処理自動化、LINE通知、ダッシュボード
- **Phase 3**: 300商品スケール、自動ローテーション、価格最適化
- **Phase 4**: Shopify自前ショップ、データ駆動の新カテゴリ探索
