"""商品リサーチサービス

eBay Browse APIでのキーワードリサーチ、価格分布分析、
日本セラー検出、NETSEAマッチング＆スコアリングを提供。
"""

import asyncio
import math
from typing import Any, Dict, List, Optional


def run_keyword_research(keyword: str, limit: int = 50) -> Dict[str, Any]:
    """eBayキーワードリサーチを実行

    EbayBrowseClient.keyword_research() をラップし、
    価格分布ヒストグラムと日本セラー数を追加で計算する。

    Returns:
        keyword_research結果 + price_dist + japan_seller_count
    """
    from src.research.ebay_browse import EbayBrowseClient

    client = EbayBrowseClient()
    result = asyncio.run(client.keyword_research(keyword, limit=limit))

    # 価格分布ヒストグラム（8バケツ）を計算
    top_items = result.get("top_items", [])
    prices = []
    for item in top_items:
        try:
            p = float(item.get("price", 0))
            if p > 0:
                prices.append(p)
        except (ValueError, TypeError):
            pass

    result["price_dist"] = _build_price_histogram(prices)

    # 日本セラー検出
    japan_sellers = _count_japan_sellers(top_items)
    result["japan_seller_count"] = japan_sellers

    return result


def _build_price_histogram(prices: List[float], buckets: int = 8) -> List[Dict]:
    """価格リストから等間隔ヒストグラムを生成

    Returns:
        [{"range": "$5-$10", "min": 5, "max": 10, "count": 3}, ...]
    """
    if not prices:
        return []

    min_p = min(prices)
    max_p = max(prices)

    if min_p == max_p:
        return [{"range": "${:.0f}".format(min_p), "min": min_p,
                 "max": max_p, "count": len(prices)}]

    step = math.ceil((max_p - min_p) / buckets)
    if step == 0:
        step = 1

    histogram = []
    for i in range(buckets):
        low = min_p + i * step
        high = low + step
        count = sum(1 for p in prices if low <= p < high)
        # 最後のバケツは上端を含む
        if i == buckets - 1:
            count = sum(1 for p in prices if low <= p <= high)
        if count > 0 or i < buckets:
            histogram.append({
                "range": "${:.0f}-${:.0f}".format(low, high),
                "min": round(low, 2),
                "max": round(high, 2),
                "count": count,
            })

    return histogram


# 日本セラーを示すキーワードパターン
_JAPAN_SELLER_KEYWORDS = [
    "japan", "jp", "tokyo", "osaka", "kyoto",
    "-jp", "_jp", "nihon", "nippon",
]


def _count_japan_sellers(top_items: List[Dict]) -> int:
    """トップ商品のセラー名から日本セラー数を推定"""
    count = 0
    for item in top_items:
        seller = (item.get("seller") or "").lower()
        if any(kw in seller for kw in _JAPAN_SELLER_KEYWORDS):
            count += 1
    return count


def match_netsea_products(
    keyword: str,
    total_results: int,
    median_price_usd: Optional[float],
    supplier_ids: str,
) -> List[Dict[str, Any]]:
    """NETSEAから商品を検索し、利益計算＋スコアリングを実行

    Args:
        keyword: 検索キーワード
        total_results: eBayの総出品数（需要スコア用）
        median_price_usd: eBay中央価格（利益計算用）
        supplier_ids: NETSEAサプライヤーID（カンマ区切り）

    Returns:
        スコア降順の上位20件のマッチング結果リスト
    """
    from src.ai.profit_calculator import calculate_profit
    from src.scraper.netsea import NetseaClient

    client = NetseaClient()
    netsea_items = client.get_items_and_map(
        supplier_ids=supplier_ids,
        keyword=keyword,
    )

    if not median_price_usd or median_price_usd <= 0:
        median_price_usd = 20.0  # フォールバック

    matches = []
    for item in netsea_items:
        wholesale_jpy = item.get("wholesale_price_jpy")
        if not wholesale_jpy:
            continue

        # DS適合フラグチェック
        ds_ok = (
            item.get("direct_send_flag") == "Y"
            and item.get("image_copy_flag") == "Y"
            and item.get("deal_net_shop_flag") == "Y"
        )

        # 利益計算（eBay中央価格で販売する想定）
        profit = calculate_profit(
            wholesale_jpy=wholesale_jpy,
            sale_usd=median_price_usd,
            weight_g=item.get("weight_g"),
            platform="ebay",
        )

        # スコアリング
        demand_score = _calc_demand_score(total_results)
        margin_score = _calc_margin_score(profit["profit_margin"])
        competition_score = _calc_competition_score(total_results)

        # DS適合フラグ全Yでなければスコア0
        if ds_ok:
            total_score = round(
                (demand_score * margin_score) / max(competition_score, 0.1),
                2,
            )
        else:
            total_score = 0.0

        matches.append({
            "netsea_product_id": item.get("supplier_product_id"),
            "netsea_name_ja": item.get("name_ja"),
            "wholesale_price_jpy": wholesale_jpy,
            "suggested_price_usd": median_price_usd,
            "profit_usd": profit["profit_usd"],
            "profit_margin": profit["profit_margin"],
            "profitable": profit["profitable"],
            "demand_score": demand_score,
            "margin_score": margin_score,
            "competition_score": competition_score,
            "total_score": total_score,
            "direct_send_flag": item.get("direct_send_flag"),
            "image_copy_flag": item.get("image_copy_flag"),
            "deal_net_shop_flag": item.get("deal_net_shop_flag"),
        })

    # スコア降順ソート、上位20件
    matches.sort(key=lambda m: m["total_score"], reverse=True)
    return matches[:20]


def _calc_demand_score(total_results: int) -> float:
    """需要スコア（0〜10）: 出品数が多いほど需要あり"""
    if total_results <= 0:
        return 0.0
    # log10スケール: 10件→1, 100件→2, 1000件→3, ... 最大10
    score = math.log10(max(total_results, 1))
    return round(min(score, 10.0), 2)


def _calc_margin_score(margin: float) -> float:
    """利益率スコア（0〜10）: 利益率が高いほど高スコア"""
    # 0% → 0, 25% → 5, 50% → 10
    score = margin * 20.0
    return round(max(0.0, min(score, 10.0)), 2)


def _calc_competition_score(total_results: int) -> float:
    """競合スコア（0.1〜10）: 出品数が多いほど競争激しい"""
    if total_results <= 0:
        return 0.1
    score = math.log10(max(total_results, 1)) * 0.8
    return round(max(0.1, min(score, 10.0)), 2)


def compare_keywords(session_ids: List[int], db) -> List[Dict[str, Any]]:
    """複数キーワードのリサーチ結果を比較用データにまとめる

    Args:
        session_ids: リサーチセッションIDリスト（最大5件）
        db: Databaseインスタンス

    Returns:
        セッションデータのリスト
    """
    results = []
    for sid in session_ids[:5]:
        session = db.get_research_session(sid)
        if session:
            results.append(session)
    return results
