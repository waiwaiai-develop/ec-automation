# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## プロジェクト概要

日本の文化商品（手ぬぐい、風呂敷、包丁、お香、和紙）を海外バイヤーにドロップシッピングで販売するEC自動化システム。詳細は `JAPAN_DROPSHIP_KB.md` を参照。

- メインチャネル: eBay（卸売DS合法、集客力あり）
- サブチャネル: BASE（Phase 2以降、ブランド構築用）
- 現在のフェーズ: Phase 0（アカウントセットアップ）

## コアアーキテクチャ

```
TopSeller/NETSEA → Scraper(Python+Playwright) → SQLite
  → BAN Risk Filter → AI Pipeline(Claude API + DeepL)
  → eBay Inventory API → Inventory Sync(cron 15min)
  → Order Detection → 自動仕入れ + LINE Notify
```

## テックスタック

- 言語: Python
- DB: SQLite（`data/dropship.db`）
- スクレイパー: Playwright
- AI: Claude API (Sonnet) — 商品説明生成、BAN判定、SEOタグ
- 翻訳: DeepL API Free
- プラットフォーム連携: eBay Inventory API (REST), BASE API
- 通知: LINE Notify
- ダッシュボード: Google Sheets + GAS
- インフラ: VPS (Sakura/ConoHa)

## ディレクトリ構成（計画）

```
src/scraper/       — NETSEA/TopSellerスクレイパー
src/ai/            — 商品説明生成、BANフィルタ、SEOタグ
src/platforms/     — eBay/BASE API連携
src/sync/          — 在庫同期、注文処理
src/dashboard/     — Google Sheets連携
data/              — SQLite DB、ブランドブラックリスト
config/            — .env（API keys）、config.yaml
scripts/           — DB初期化、cron設定
tests/             — テスト
```

## 重要なビジネスルール

- **BAN-safe design first**: プラットフォームポリシー遵守が全ての前提
- **VeRO対策**: リスティングにブランド名を絶対に含めない（eBay即ペナルティ）
- **包丁 → UK/IE配送禁止**: 刃物輸入規制のため出品時に必ず除外設定
- **Defect Rate < 0.5%**, **Late Shipment Rate < 3%**（eBay基準）
- **利益率 > 25%** の商品のみ出品対象

## Rules

- 日本語で応答すること
- コードのコメントも日本語で書くこと
- commit messageは日本語OK
