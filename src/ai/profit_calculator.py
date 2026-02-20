"""利益計算モジュール

送料推定・利益計算・推奨価格逆算を提供。
KBの計算例（手ぬぐい$15/包丁$100）と一致するよう設計。
"""

from typing import Dict, Optional


# --- 為替レート ---
USD_JPY_RATE = 150.0

# --- 送料テーブル（日本→US、重量別） ---
# (上限重量g, 方法名, 費用JPY, 費用USD)
SHIPPING_TABLE = [
    (50, "ePacket Lite", 580, 3.87),
    (300, "EMS", 3600, 24.00),
    (2000, "EMS", 5000, 33.33),
]

# --- eBay手数料 ---
EBAY_FVF_RATE = 0.1325       # Final Value Fee 13.25%
EBAY_PAYMENT_FEE_USD = 0.30  # 決済手数料（固定）


def estimate_shipping(weight_g: Optional[int]) -> Dict:
    """重量から送料を推定

    Args:
        weight_g: 商品重量（g）。NULLの場合はePacket想定

    Returns:
        {"method": str, "cost_jpy": int, "cost_usd": float}
    """
    if weight_g is None:
        # 不明時はePacket想定（軽量商品が主力）
        return {
            "method": "ePacket Lite (推定)",
            "cost_jpy": 580,
            "cost_usd": 3.87,
        }

    for max_weight, method, cost_jpy, cost_usd in SHIPPING_TABLE:
        if weight_g <= max_weight:
            return {
                "method": method,
                "cost_jpy": cost_jpy,
                "cost_usd": cost_usd,
            }

    # テーブル上限超過
    return {
        "method": "EMS (超過重量)",
        "cost_jpy": 8000,
        "cost_usd": round(8000 / USD_JPY_RATE, 2),
    }


def calculate_profit(
    wholesale_jpy: int,
    sale_usd: float,
    weight_g: Optional[int] = None,
    shipping_override_usd: Optional[float] = None,
) -> Dict:
    """利益を計算

    Args:
        wholesale_jpy: 卸値（円）
        sale_usd: 販売価格（USD）
        weight_g: 重量（g）。送料推定に使用
        shipping_override_usd: 送料を手動指定する場合

    Returns:
        {
            "sale_usd": float,
            "wholesale_usd": float,
            "wholesale_jpy": int,
            "shipping": dict,
            "ebay_fvf_usd": float,
            "ebay_payment_usd": float,
            "total_cost_usd": float,
            "profit_usd": float,
            "profit_margin": float,  # 0-1
            "profitable": bool,      # 利益率 > 25%
        }
    """
    # 卸値のUSD換算
    wholesale_usd = round(wholesale_jpy / USD_JPY_RATE, 2)

    # 送料
    shipping = estimate_shipping(weight_g)
    shipping_usd = shipping_override_usd if shipping_override_usd is not None else shipping["cost_usd"]

    # eBay手数料
    ebay_fvf = round(sale_usd * EBAY_FVF_RATE, 2)
    ebay_payment = EBAY_PAYMENT_FEE_USD

    # 合計コスト
    total_cost = round(wholesale_usd + shipping_usd + ebay_fvf + ebay_payment, 2)

    # 利益
    profit = round(sale_usd - total_cost, 2)
    margin = round(profit / sale_usd, 4) if sale_usd > 0 else 0.0

    return {
        "sale_usd": sale_usd,
        "wholesale_usd": wholesale_usd,
        "wholesale_jpy": wholesale_jpy,
        "shipping": shipping,
        "shipping_usd": shipping_usd,
        "ebay_fvf_usd": ebay_fvf,
        "ebay_payment_usd": ebay_payment,
        "total_cost_usd": total_cost,
        "profit_usd": profit,
        "profit_margin": margin,
        "profitable": margin >= 0.25,
    }


def suggest_price(
    wholesale_jpy: int,
    weight_g: Optional[int] = None,
    target_margin: float = 0.30,
) -> Dict:
    """目標利益率から推奨販売価格を逆算

    price = (wholesale_usd + shipping_usd + payment_fee) / (1 - fvf_rate - target_margin)

    Args:
        wholesale_jpy: 卸値（円）
        weight_g: 重量（g）
        target_margin: 目標利益率（デフォルト30%）

    Returns:
        {"suggested_price_usd": float, "breakdown": dict}
    """
    wholesale_usd = wholesale_jpy / USD_JPY_RATE
    shipping = estimate_shipping(weight_g)
    shipping_usd = shipping["cost_usd"]

    # price * (1 - fvf_rate - target_margin) = wholesale + shipping + payment
    # price = (wholesale + shipping + payment) / (1 - fvf_rate - target_margin)
    denominator = 1.0 - EBAY_FVF_RATE - target_margin
    if denominator <= 0:
        # 目標利益率が高すぎる場合
        return {
            "suggested_price_usd": None,
            "error": "目標利益率が高すぎます（FVF + margin >= 100%）",
        }

    suggested = round(
        (wholesale_usd + shipping_usd + EBAY_PAYMENT_FEE_USD) / denominator, 2
    )

    # 検算
    breakdown = calculate_profit(wholesale_jpy, suggested, weight_g)

    return {
        "suggested_price_usd": suggested,
        "target_margin": target_margin,
        "breakdown": breakdown,
    }
