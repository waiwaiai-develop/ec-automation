"""プラットフォームクライアント テスト

- BasePlatformClient ABCの検証
- eBay/Etsy/BASEクライアントのインターフェース適合
"""

import pytest

from src.platforms.base_client import BasePlatformClient
from src.platforms.ebay import EbayClient
from src.platforms.etsy import EtsyClient
from src.platforms.base_shop import BaseShopClient


class TestBasePlatformClientABC:
    """ABCの検証"""

    def test_cannot_instantiate_abc(self):
        """ABCを直接インスタンス化できない"""
        with pytest.raises(TypeError):
            BasePlatformClient()

    def test_ebay_implements_abc(self):
        """EbayClientはABCを実装している"""
        assert issubclass(EbayClient, BasePlatformClient)

    def test_etsy_implements_abc(self):
        """EtsyClientはABCを実装している"""
        assert issubclass(EtsyClient, BasePlatformClient)

    def test_base_implements_abc(self):
        """BaseShopClientはABCを実装している"""
        assert issubclass(BaseShopClient, BasePlatformClient)


class TestEbayClientProperties:
    """eBayクライアントのプロパティテスト"""

    def test_platform_name(self):
        """platform_nameが'ebay'を返す"""
        client = EbayClient(sandbox=True)
        assert client.platform_name == "ebay"

    def test_sandbox_mode(self):
        """sandboxモードが設定される"""
        client = EbayClient(sandbox=True)
        assert client.sandbox is True
        assert "sandbox" in client.endpoints["inventory"]

    def test_production_mode(self):
        """productionモードが設定される"""
        client = EbayClient(sandbox=False)
        assert client.sandbox is False
        assert "sandbox" not in client.endpoints["inventory"]

    def test_sku_generation(self):
        """SKU生成"""
        client = EbayClient(sandbox=True)
        product = {
            "supplier": "netsea",
            "supplier_product_id": "12345",
        }
        sku = client._make_sku(product)
        assert sku == "DS-NETSEA-12345"


class TestEtsyClientProperties:
    """Etsyクライアントのプロパティテスト"""

    def test_platform_name(self):
        """platform_nameが'etsy'を返す"""
        client = EtsyClient()
        assert client.platform_name == "etsy"


class TestBaseShopClientProperties:
    """BASEクライアントのプロパティテスト"""

    def test_platform_name(self):
        """platform_nameが'base'を返す"""
        client = BaseShopClient()
        assert client.platform_name == "base"


class TestRequiredMethods:
    """ABCの必須メソッドが実装されていることを確認"""

    @pytest.mark.parametrize("client_class", [EbayClient, EtsyClient, BaseShopClient])
    def test_has_create_listing(self, client_class):
        assert hasattr(client_class, "create_listing")

    @pytest.mark.parametrize("client_class", [EbayClient, EtsyClient, BaseShopClient])
    def test_has_update_listing(self, client_class):
        assert hasattr(client_class, "update_listing")

    @pytest.mark.parametrize("client_class", [EbayClient, EtsyClient, BaseShopClient])
    def test_has_deactivate_listing(self, client_class):
        assert hasattr(client_class, "deactivate_listing")

    @pytest.mark.parametrize("client_class", [EbayClient, EtsyClient, BaseShopClient])
    def test_has_activate_listing(self, client_class):
        assert hasattr(client_class, "activate_listing")

    @pytest.mark.parametrize("client_class", [EbayClient, EtsyClient, BaseShopClient])
    def test_has_get_orders(self, client_class):
        assert hasattr(client_class, "get_orders")

    @pytest.mark.parametrize("client_class", [EbayClient, EtsyClient, BaseShopClient])
    def test_has_upload_tracking(self, client_class):
        assert hasattr(client_class, "upload_tracking")
