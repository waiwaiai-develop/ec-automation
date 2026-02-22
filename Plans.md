# Plans.md — EC自動化プロジェクト実装計画

> **ソース**: `Japan_DropShip_BattlePlan_v2.docx`
> **最終更新**: 2026-02-21
> **現在フェーズ**: Phase 2完了 → Phase 3 スケール準備

---

## 次のアクション（今すぐやること）

### 1. NETSEA商品を再インポートしてDSフラグを取得 `cc:NEXT`
既存商品のDSフラグ（direct_send_flag等）がNULLのため、再取得が必要。
```bash
python -m src.cli.main netsea import --supplier-id 79841
```
- 再インポート後、Webダッシュボード（`/products?ds_only=1`）でDS対応商品を確認
- DS非対応（直送不可・画像転載不可）の商品は出品候補から除外

### 2. DS対応商品の選定・出品候補リスト作成 `cc:NEXT`
- [ ] DS対応フィルターで絞り込んだ商品を確認
- [ ] 利益率25%以上の商品をピックアップ
- [ ] BANリスクフィルターを通してVeRO問題がないか検証
- [ ] 最初の出品候補10〜20商品を決定

### 3. eBayアカウント準備 `cc:NEXT`
- [ ] eBay Developer Program に登録し API キー取得（Sandbox → Production）
- [ ] eBay セラーアカウント設定（ビジネスポリシー・返品ポリシー・配送設定）
- [ ] OAuth 2.0 トークン取得フロー動作確認

### 4. 追加サプライヤーの商品取得 `cc:TODO`
- [ ] サプライヤー4387の商品を取得・DSフラグ確認
- [ ] お香カテゴリ（31801）の商品を取得・候補選定
- [ ] 新規サプライヤーの発掘（NETSEA `/suppliers` で検索）

---

## 実装済み（Phase 0-1）

- [x] SQLiteデータベース設計・実装（7テーブル: products, listings, orders, brand_blacklist, country_restrictions, ebay_market_data, sync_log）
- [x] NETSEA API クライアント（商品検索・取得・カテゴリ一覧・DB保存）
- [x] NETSEAドロップシッピングフラグ対応（direct_send_flag, image_copy_flag, deal_net_shop_flag, deal_net_auction_flag）
- [x] Webダッシュボード（Flask + Bootstrap 5: 商品一覧・詳細・DS対応フィルター）
- [x] eBay Browse API キーワードリサーチ（価格帯・競合分析・上位商品表示）
- [x] eBay Playwright スクレイパー（sold count 補足取得）
- [x] BANリスクフィルター（VeROブランド検出・禁止キーワード・国別配送制限・利益率フィルタ）
- [x] 利益計算エンジン（送料テーブル・eBay手数料・利益率算出・推奨価格提示）
- [x] AI商品説明生成（Claude API: 英語タイトル + 説明文 + Item Specifics + SEOタグ13個）
- [x] CLIツール（db / netsea / research / product の各コマンド群）
- [x] テスト一式（255+テスト通過: ban_filter, database, description_generator, netsea, profit, platform_clients, web_api, research, topseller, translator 他）
- [x] React SPA フロントエンド（Vite + TypeScript + shadcn/ui: ダッシュボード・商品・出品・注文）
- [x] 商品リサーチWeb UI（需要分析・競合分析・NETSEAマッチング・Chart.jsグラフ）
- [x] SNS投稿管理（AI生成・予約投稿・カレンダービュー）

---

## Phase 2: 自動化構築（優先度順） — **全項目完了**

### 2-1. Etsy API 連携 `cc:DONE`
- [x] Etsy OAuth 2.0 認証フロー実装（`src/platforms/etsy.py`）
- [x] リスティング作成API（craft supplies カテゴリ固定）
- [x] 画像アップロード対応
- [x] リスティング更新・非公開API
- [x] Etsy手数料を利益計算に追加（リスティング$0.20 + トランザクション6.5% + 決済3%+$0.25）

### 2-2. eBay Inventory API 連携 `cc:DONE`
- [x] eBay OAuth 2.0 認証フロー実装（`src/platforms/ebay.py`）
- [x] Inventory API でリスティング作成（Sell API: createOrReplaceInventoryItem）
- [x] UK/IE配送除外設定の自動適用（包丁カテゴリ）
- [x] リスティング更新・非公開API
- [x] eBay Production API キー取得・切替対応

### 2-3. 在庫同期システム `cc:DONE`
- [x] 在庫同期エンジン実装（`src/sync/inventory_sync.py`）
- [x] NETSEA在庫状態の定期チェック（15分間隔）
- [x] 品切れ商品の自動非公開（Etsy/eBay両方）
- [x] 在庫復活時の自動再公開
- [x] cron設定スクリプト（VPS用）

### 2-4. 注文処理・自動仕入れ `cc:DONE`
- [x] 注文検出（eBay/Etsy API ポーリング）
- [x] NETSEA自動発注フロー（注文検出→卸先発注）
- [x] 追跡番号の自動取得・プラットフォーム連携
- [x] 注文ステータスDB管理（orders テーブル活用）

### 2-5. 通知システム（LINE Notify） `cc:DONE`
- [x] LINE Notify API 連携（`src/notifications/line.py`）
- [x] 注文受信通知
- [x] 在庫切れアラート
- [x] 日次売上サマリー通知
- [x] エラー・異常検知通知

### 2-6. ダッシュボード（Google Sheets） `cc:DONE`
- [x] Google Sheets API 連携（`src/dashboard/sheets.py`）
- [x] 売上・利益レポート自動更新
- [x] 在庫状況一覧
- [x] アカウントメトリクス（Defect Rate, Late Shipment Rate）
- [x] GAS（Google Apps Script）トリガー設定

### 2-7. TopSeller スクレイパー追加 `cc:DONE`
- [x] TopSeller商品収集（Playwright、`src/scraper/topseller.py`）
- [x] 既存DB・CLIとの統合（map_to_db形式）
- [x] TopSeller固有の重量・カテゴリ抽出ロジック

### 2-8. DeepL API 翻訳連携 `cc:DONE`
- [x] DeepL API Free クライアント（`src/ai/translator.py`）
- [x] 商品名の日→英翻訳（Claude APIの補助として）
- [x] バッチ翻訳対応（50件ずつ一括処理）

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
