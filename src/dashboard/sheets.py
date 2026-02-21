"""Google Sheets ダッシュボード

gspread + サービスアカウントでスプレッドシートに
日次レポート・在庫状況・注文履歴を自動更新。
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.db.database import Database

# サービスアカウントJSONのパス
_PROJECT_ROOT = Path(__file__).parent.parent.parent
DEFAULT_SA_PATH = _PROJECT_ROOT / "service-account-ec-automation.json"


class SheetsDashboard:
    """Google Sheetsダッシュボード"""

    # シート名定数
    SHEET_DAILY = "日次レポート"
    SHEET_LISTINGS = "出品一覧"
    SHEET_ORDERS = "注文履歴"
    SHEET_INVENTORY = "在庫状況"

    def __init__(
        self,
        spreadsheet_id: Optional[str] = None,
        sa_path: Optional[str] = None,
    ):
        """
        Args:
            spreadsheet_id: Google SheetsのスプレッドシートID
            sa_path: サービスアカウントJSONのパス
        """
        self.spreadsheet_id = spreadsheet_id or os.environ.get(
            "GOOGLE_SHEETS_ID", ""
        )
        self.sa_path = sa_path or str(DEFAULT_SA_PATH)
        self._client = None
        self._spreadsheet = None

    def _get_client(self):
        """gspreadクライアントを遅延初期化"""
        if self._client is None:
            try:
                import gspread
            except ImportError:
                raise ImportError(
                    "gspread がインストールされていません。"
                    "`pip install gspread` を実行してください。"
                )

            if not os.path.exists(self.sa_path):
                raise FileNotFoundError(
                    f"サービスアカウントJSONが見つかりません: {self.sa_path}\n"
                    "Google Cloud Consoleからダウンロードして配置してください。"
                )

            self._client = gspread.service_account(filename=self.sa_path)

        return self._client

    def _get_spreadsheet(self):
        """スプレッドシートを取得"""
        if self._spreadsheet is None:
            if not self.spreadsheet_id:
                raise ValueError(
                    "GOOGLE_SHEETS_ID が設定されていません。"
                    "config/.env に追加してください。"
                )
            client = self._get_client()
            self._spreadsheet = client.open_by_key(self.spreadsheet_id)

        return self._spreadsheet

    def _get_or_create_worksheet(self, title: str, headers: List[str]):
        """ワークシートを取得（なければ作成）"""
        spreadsheet = self._get_spreadsheet()

        try:
            worksheet = spreadsheet.worksheet(title)
        except Exception:
            worksheet = spreadsheet.add_worksheet(
                title=title, rows=1000, cols=len(headers)
            )
            worksheet.append_row(headers)

        return worksheet

    def update_daily_report(self, database: Database,
                            date: Optional[str] = None) -> Dict[str, Any]:
        """日次レポートを更新"""
        summary = database.get_daily_summary(date)

        headers = [
            "日付", "注文数", "売上($)", "利益($)",
            "出品数", "在庫変動", "更新日時",
        ]
        worksheet = self._get_or_create_worksheet(self.SHEET_DAILY, headers)

        row = [
            summary["date"],
            summary["orders_count"],
            round(summary["revenue_usd"], 2),
            round(summary["profit_usd"], 2),
            summary["active_listings"],
            summary["stock_changes"],
            datetime.now().strftime("%Y-%m-%d %H:%M"),
        ]

        # 同日のデータがあれば更新、なければ追加
        try:
            cell = worksheet.find(summary["date"], in_column=1)
            if cell:
                worksheet.update(f"A{cell.row}:G{cell.row}", [row])
            else:
                worksheet.append_row(row)
        except Exception:
            worksheet.append_row(row)

        return {"success": True, "date": summary["date"], "data": summary}

    def update_listings(self, database: Database,
                        platform: Optional[str] = None) -> Dict[str, Any]:
        """出品一覧を更新"""
        listings = database.get_listings(platform=platform, limit=500)

        headers = [
            "ID", "商品ID", "プラットフォーム", "タイトル",
            "価格($)", "送料($)", "ステータス", "売上数",
            "作成日", "更新日",
        ]
        worksheet = self._get_or_create_worksheet(self.SHEET_LISTINGS, headers)

        rows = []
        for l in listings:
            rows.append([
                l["id"],
                l.get("product_id", ""),
                l["platform"],
                (l.get("title_en") or "")[:50],
                l.get("price_usd", 0),
                l.get("shipping_cost_usd", 0),
                l.get("status", ""),
                l.get("sales", 0),
                l.get("created_at", ""),
                l.get("updated_at", ""),
            ])

        # ヘッダー行を残してクリアし、全データを書き換え
        if rows:
            worksheet.clear()
            worksheet.append_row(headers)
            worksheet.append_rows(rows)

        return {"success": True, "count": len(rows)}

    def update_orders(self, database: Database,
                      limit: int = 100) -> Dict[str, Any]:
        """注文履歴を更新"""
        orders = database.get_orders(limit=limit)

        headers = [
            "ID", "プラットフォーム", "注文ID", "配送先",
            "売上($)", "手数料($)", "送料($)", "仕入($)",
            "利益($)", "ステータス", "注文日",
        ]
        worksheet = self._get_or_create_worksheet(self.SHEET_ORDERS, headers)

        rows = []
        for o in orders:
            rows.append([
                o["id"],
                o["platform"],
                o.get("platform_order_id", ""),
                o.get("buyer_country", ""),
                o.get("sale_price_usd", 0),
                o.get("platform_fees_usd", 0),
                o.get("shipping_cost_usd", 0),
                o.get("wholesale_cost_jpy", 0),
                o.get("profit_usd", 0),
                o.get("status", ""),
                o.get("ordered_at", ""),
            ])

        if rows:
            worksheet.clear()
            worksheet.append_row(headers)
            worksheet.append_rows(rows)

        return {"success": True, "count": len(rows)}

    def update_inventory(self, database: Database) -> Dict[str, Any]:
        """在庫状況を更新"""
        products = database.get_products(limit=500)

        headers = [
            "ID", "商品名", "カテゴリ", "卸値(円)", "上代(円)",
            "重量(g)", "在庫状況", "ショップ", "商品URL",
        ]
        worksheet = self._get_or_create_worksheet(self.SHEET_INVENTORY, headers)

        rows = []
        for p in products:
            rows.append([
                p["id"],
                (p.get("name_ja") or "")[:40],
                p.get("category", ""),
                p.get("wholesale_price_jpy", 0),
                p.get("reference_price_jpy") or "",
                p.get("weight_g") or "",
                p.get("stock_status", ""),
                p.get("shop_name") or "",
                p.get("product_url") or "",
            ])

        if rows:
            worksheet.clear()
            worksheet.append_row(headers)
            worksheet.append_rows(rows)

        return {"success": True, "count": len(rows)}

    def update_all(self, database: Database) -> Dict[str, Any]:
        """全シートを一括更新"""
        results = {}
        results["daily"] = self.update_daily_report(database)
        results["listings"] = self.update_listings(database)
        results["orders"] = self.update_orders(database)
        results["inventory"] = self.update_inventory(database)
        return results
