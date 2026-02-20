"""プラットフォーム共通インターフェース

全プラットフォーム（eBay, Etsy, Shopify等）が実装すべき
6メソッドのABCを定義。
"""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, List, Optional


class BasePlatformClient(ABC):
    """プラットフォームクライアントの抽象基底クラス

    新規プラットフォーム追加時はこのクラスを継承し、
    6つのメソッドを全て実装すること。
    """

    @property
    @abstractmethod
    def platform_name(self) -> str:
        """プラットフォーム識別子を返す（例: 'ebay', 'etsy'）"""
        ...

    @abstractmethod
    def create_listing(self, product: Dict[str, Any],
                       listing_data: Dict[str, Any]) -> Dict[str, Any]:
        """商品を出品する

        Args:
            product: DBのproductsテーブルの行データ
            listing_data: 出品情報（title_en, description_en, price_usd, tags等）

        Returns:
            {
                "platform_listing_id": str,
                "status": str,  # "active" or "draft"
                "url": str,     # 出品ページURL
            }
        """
        ...

    @abstractmethod
    def update_listing(self, platform_listing_id: str,
                       updates: Dict[str, Any]) -> Dict[str, Any]:
        """リスティングを更新する

        Args:
            platform_listing_id: プラットフォーム側のリスティングID
            updates: 更新するフィールド（price_usd, title_en等）

        Returns:
            {"success": bool, "updated_fields": list}
        """
        ...

    @abstractmethod
    def deactivate_listing(self, platform_listing_id: str) -> Dict[str, Any]:
        """リスティングを非公開にする（在庫切れ等）

        Args:
            platform_listing_id: プラットフォーム側のリスティングID

        Returns:
            {"success": bool, "status": "paused"}
        """
        ...

    @abstractmethod
    def activate_listing(self, platform_listing_id: str) -> Dict[str, Any]:
        """リスティングを再公開する（在庫復活等）

        Args:
            platform_listing_id: プラットフォーム側のリスティングID

        Returns:
            {"success": bool, "status": "active"}
        """
        ...

    @abstractmethod
    def get_orders(self, since: Optional[datetime] = None) -> List[Dict[str, Any]]:
        """注文を取得する

        Args:
            since: この日時以降の注文を取得（Noneなら直近24時間）

        Returns:
            [
                {
                    "platform_order_id": str,
                    "buyer_country": str,
                    "items": [{"platform_listing_id": str, "quantity": int}],
                    "sale_price_usd": float,
                    "platform_fees_usd": float,
                    "shipping_cost_usd": float,
                    "ordered_at": str,  # ISO format
                    "status": str,
                },
                ...
            ]
        """
        ...

    @abstractmethod
    def upload_tracking(self, platform_order_id: str,
                        tracking_number: str,
                        carrier: str) -> Dict[str, Any]:
        """追跡番号をアップロードする

        Args:
            platform_order_id: プラットフォーム側の注文ID
            tracking_number: 追跡番号
            carrier: 配送業者名（例: "Japan Post"）

        Returns:
            {"success": bool}
        """
        ...
