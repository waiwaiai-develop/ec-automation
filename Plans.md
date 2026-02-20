# Plans.md — EC自動化プロジェクト実装計画

> **ソース**: `Japan_DropShip_BattlePlan_v2.docx`
> **最終更新**: 2026-02-20
> **現在フェーズ**: Phase 1完了 → Phase 2 自動化構築

---

## 実装済み（Phase 0-1）

- [x] SQLiteデータベース設計・実装（6テーブル: products, listings, orders, brand_blacklist, country_restrictions, ebay_market_data）
- [x] NETSEA API クライアント（商品検索・取得・カテゴリ一覧・DB保存）
- [x] eBay Browse API キーワードリサーチ（価格帯・競合分析・上位商品表示）
- [x] eBay Playwright スクレイパー（sold count 補足取得）
- [x] BANリスクフィルター（VeROブランド検出・禁止キーワード・国別配送制限・利益率フィルタ）
- [x] 利益計算エンジン（送料テーブル・eBay手数料・利益率算出・推奨価格提示）
- [x] AI商品説明生成（Claude API: 英語タイトル + 説明文 + Item Specifics + SEOタグ13個）
- [x] CLIツール（db / netsea / research / product の各コマンド群）
- [x] テスト一式（ban_filter, database, description_generator, netsea, profit）

---

## Phase 2: 自動化構築（優先度順）

### 2-1. Etsy API 連携 `cc:TODO`
- [ ] Etsy OAuth 2.0 認証フロー実装（`src/platforms/etsy.py`）
- [ ] リスティング作成API（craft supplies カテゴリ固定）
- [ ] 画像アップロード対応
- [ ] リスティング更新・非公開API
- [ ] Etsy手数料を利益計算に追加（リスティング$0.20 + トランザクション6.5% + 決済3%+$0.25）

### 2-2. eBay Inventory API 連携 `cc:TODO`
- [ ] eBay OAuth 2.0 認証フロー実装（`src/platforms/ebay.py`）
- [ ] Inventory API でリスティング作成（Sell API: createOrReplaceInventoryItem）
- [ ] UK/IE配送除外設定の自動適用（包丁カテゴリ）
- [ ] リスティング更新・非公開API
- [ ] eBay Production API キー取得・切替対応

### 2-3. 在庫同期システム `cc:TODO`
- [ ] 在庫同期エンジン実装（`src/sync/inventory_sync.py`）
- [ ] NETSEA在庫状態の定期チェック（15分間隔）
- [ ] 品切れ商品の自動非公開（Etsy/eBay両方）
- [ ] 在庫復活時の自動再公開
- [ ] cron設定スクリプト（VPS用）

### 2-4. 注文処理・自動仕入れ `cc:TODO`
- [ ] 注文検出（eBay/Etsy API ポーリング）
- [ ] NETSEA自動発注フロー（注文検出→卸先発注）
- [ ] 追跡番号の自動取得・プラットフォーム連携
- [ ] 注文ステータスDB管理（orders テーブル活用）

### 2-5. 通知システム（LINE Notify） `cc:TODO`
- [ ] LINE Notify API 連携（`src/notifications/line.py`）
- [ ] 注文受信通知
- [ ] 在庫切れアラート
- [ ] 日次売上サマリー通知
- [ ] エラー・異常検知通知

### 2-6. ダッシュボード（Google Sheets） `cc:TODO`
- [ ] Google Sheets API 連携（`src/dashboard/sheets.py`）
- [ ] 売上・利益レポート自動更新
- [ ] 在庫状況一覧
- [ ] アカウントメトリクス（Defect Rate, Late Shipment Rate）
- [ ] GAS（Google Apps Script）トリガー設定

### 2-7. TopSeller スクレイパー追加 `cc:TODO`
- [ ] TopSeller商品収集（Playwright、`src/scraper/topseller.py`）
- [ ] 既存DB・CLIとの統合
- [ ] TopSeller固有の重量・カテゴリ抽出ロジック

### 2-8. DeepL API 翻訳連携 `cc:TODO`
- [ ] DeepL API Free クライアント（`src/ai/translator.py`）
- [ ] 商品名の日→英翻訳（Claude APIの補助として）
- [ ] バッチ翻訳対応

---

## Phase 3: スケール（50→300商品）

### 3-1. 自動商品ローテーション `cc:TODO`
- [ ] 30日間売れない商品の自動非公開
- [ ] 売れ筋商品の類似品自動探索
- [ ] カテゴリ別パフォーマンス分析

### 3-2. マルチチャネル一括管理 `cc:TODO`
- [ ] Etsy + eBay の統合管理画面（CLI拡張）
- [ ] チャネル別利益率レポート
- [ ] 商品のクロスリスティング（1商品→複数チャネル出品）

### 3-3. 価格最適化 `cc:TODO`
- [ ] 競合価格の定期モニタリング
- [ ] 動的価格調整（競合比較ベース）
- [ ] A/Bテスト（タイトル・価格・タグ）

---

## Phase 4: 最適化 + 保険

### 4-1. Shopify自前ショップ構築 `cc:TODO`
- [ ] Shopifyストア構築
- [ ] Pinterest/Instagram連携（集客用）
- [ ] 既存商品データのShopify移行

### 4-2. データ駆動の新カテゴリ探索 `cc:TODO`
- [ ] お香リピート購入率分析
- [ ] 売上データからの新カテゴリ候補自動抽出
- [ ] 利益率×需要の二軸マトリクスによる商品評価

---

## 配送方法ガイド（BattlePlan v2準拠）

| 商品 | 配送方法 | 料金目安 |
|------|---------|---------|
| 手ぬぐい・風呂敷（〜100g） | 小形包装物航空便 | 580円 |
| お香（〜200g） | 国際eパケットライト | 740円 |
| 包丁（〜500g） | EMS | 3,900円（買い手負担 or 売価含む） |

## ビジネスルール（厳守）

- **BAN-safe first**: プラットフォームポリシー遵守が全ての前提
- **VeRO対策**: リスティングにブランド名を絶対に含めない
- **包丁 → UK/IE配送禁止**: 刃物輸入規制
- **Defect Rate < 0.5%**, **Late Shipment Rate < 3%**
- **利益率 > 25%** の商品のみ出品
- **Etsy → craft supplies カテゴリ限定**（handmadeカテゴリは絶対NG）
