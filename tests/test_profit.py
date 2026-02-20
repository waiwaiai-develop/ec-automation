"""利益計算テスト

KB記載の計算例と照合:
- 手ぬぐい: 卸300-600円、$15販売、ePacket $3.87 → 利益$4.84-6.84 (32-46%)
- 包丁: 卸5000円、$100販売、EMS $24.00 → 利益$29.12 (29%)
"""

import pytest

from src.ai.profit_calculator import (
    EBAY_FVF_RATE,
    EBAY_PAYMENT_FEE_USD,
    USD_JPY_RATE,
    calculate_profit,
    estimate_shipping,
    suggest_price,
)


# --- estimate_shipping ---

class TestEstimateShipping:
    """送料推定テスト"""

    def test_epacket_50g(self):
        """50g以下 → ePacket Lite"""
        result = estimate_shipping(50)
        assert result["method"] == "ePacket Lite"
        assert result["cost_usd"] == 3.87
        assert result["cost_jpy"] == 580

    def test_ems_300g(self):
        """51-300g → EMS"""
        result = estimate_shipping(300)
        assert result["method"] == "EMS"
        assert result["cost_usd"] == 24.00

    def test_weight_none(self):
        """重量不明 → ePacket想定"""
        result = estimate_shipping(None)
        assert "ePacket" in result["method"]
        assert result["cost_usd"] == 3.87

    def test_heavy_item(self):
        """2000g超 → 超過重量"""
        result = estimate_shipping(3000)
        assert "超過" in result["method"]


# --- calculate_profit ---

class TestCalculateProfit:
    """利益計算テスト — KB記載の計算例と照合"""

    def test_tenugui_300jpy(self):
        """手ぬぐい（卸300円、$15販売）→ 利益$6.84, 46%"""
        result = calculate_profit(
            wholesale_jpy=300,
            sale_usd=15.00,
            weight_g=50,
        )
        # 卸値: 300 / 150 = $2.00
        assert result["wholesale_usd"] == 2.00
        # 送料: ePacket $3.87
        assert result["shipping_usd"] == 3.87
        # FVF: 15 * 0.1325 = $1.99 (切り捨て)
        assert result["ebay_fvf_usd"] == pytest.approx(1.99, abs=0.01)
        # 決済手数料: $0.30
        assert result["ebay_payment_usd"] == 0.30
        # 合計コスト: 2.00 + 3.87 + 1.99 + 0.30 = $8.16
        assert result["total_cost_usd"] == pytest.approx(8.16, abs=0.01)
        # 利益: 15.00 - 8.16 = $6.84
        assert result["profit_usd"] == pytest.approx(6.84, abs=0.01)
        # 利益率: 6.84 / 15 = 45.6%
        assert result["profit_margin"] >= 0.45
        assert result["profitable"] is True

    def test_tenugui_600jpy(self):
        """手ぬぐい（卸600円、$15販売）→ 利益$4.84, 32%"""
        result = calculate_profit(
            wholesale_jpy=600,
            sale_usd=15.00,
            weight_g=50,
        )
        # 卸値: 600 / 150 = $4.00
        assert result["wholesale_usd"] == 4.00
        # 合計コスト: 4.00 + 3.87 + 1.99 + 0.30 = $10.16
        assert result["total_cost_usd"] == pytest.approx(10.16, abs=0.01)
        # 利益: 15.00 - 10.16 = $4.84
        assert result["profit_usd"] == pytest.approx(4.84, abs=0.01)
        # 利益率: 4.84 / 15 ≈ 32.3%
        assert result["profit_margin"] >= 0.32
        assert result["profitable"] is True

    def test_knife_5000jpy(self):
        """包丁（卸5000円、$100販売）→ 利益$29.12, 29%"""
        result = calculate_profit(
            wholesale_jpy=5000,
            sale_usd=100.00,
            weight_g=300,
        )
        # 卸値: 5000 / 150 = $33.33
        assert result["wholesale_usd"] == pytest.approx(33.33, abs=0.01)
        # 送料: EMS $24.00
        assert result["shipping_usd"] == 24.00
        # FVF: 100 * 0.1325 = $13.25
        assert result["ebay_fvf_usd"] == 13.25
        # 合計コスト: 33.33 + 24.00 + 13.25 + 0.30 = $70.88
        assert result["total_cost_usd"] == pytest.approx(70.88, abs=0.01)
        # 利益: 100.00 - 70.88 = $29.12
        assert result["profit_usd"] == pytest.approx(29.12, abs=0.01)
        # 利益率: 29.12 / 100 = 29.12%
        assert result["profit_margin"] >= 0.29
        assert result["profitable"] is True

    def test_unprofitable_product(self):
        """利益率 < 25% の場合 → profitable=False"""
        result = calculate_profit(
            wholesale_jpy=1500,
            sale_usd=15.00,
            weight_g=50,
        )
        # 卸値: $10.00 + 送料$3.87 + FVF$1.99 + $0.30 = $16.16 > $15.00
        assert result["profitable"] is False

    def test_shipping_override(self):
        """送料手動指定"""
        result = calculate_profit(
            wholesale_jpy=300,
            sale_usd=15.00,
            weight_g=50,
            shipping_override_usd=5.00,
        )
        assert result["shipping_usd"] == 5.00


# --- suggest_price ---

class TestSuggestPrice:
    """推奨価格逆算テスト"""

    def test_tenugui_30pct(self):
        """手ぬぐい卸300円、目標30% → 推奨価格算出"""
        result = suggest_price(wholesale_jpy=300, weight_g=50, target_margin=0.30)
        price = result["suggested_price_usd"]
        assert price is not None
        # 逆算結果で利益率が30%に近いか検証
        breakdown = result["breakdown"]
        assert breakdown["profit_margin"] >= 0.29

    def test_knife_30pct(self):
        """包丁卸5000円、目標30% → 推奨価格算出"""
        result = suggest_price(wholesale_jpy=5000, weight_g=300, target_margin=0.30)
        price = result["suggested_price_usd"]
        assert price is not None
        assert price > 80  # EMS + 高卸値なので$80以上

    def test_impossible_margin(self):
        """不可能な利益率 → エラー"""
        result = suggest_price(wholesale_jpy=300, weight_g=50, target_margin=0.90)
        assert result["suggested_price_usd"] is None
        assert "error" in result
