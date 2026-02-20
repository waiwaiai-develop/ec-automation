"""BANリスクフィルター

ルールベースでeBay/Etsy出品のBANリスクを総合判定。
AI不使用 — ブランド名+禁止語+国制限は決定的ルールで十分。
"""

from typing import Dict, List, Optional

from src.ai.profit_calculator import calculate_profit

# --- 禁止キーワード（リスティングに含めてはいけない語句） ---
PROHIBITED_KEYWORDS = [
    # ドロップシッピング関連（eBayが嫌う表現）
    "dropship",
    "dropshipping",
    "drop ship",
    "wholesale",
    "bulk order",
    # レプリカ・偽物関連
    "replica",
    "counterfeit",
    "fake",
    "knockoff",
    "imitation",
    "bootleg",
    # 誇大表現（eBayポリシー違反リスク）
    "guaranteed authentic",
    "100% genuine",
]


def check_prohibited_keywords(text: str) -> List[Dict]:
    """テキスト内の禁止キーワードを検出

    Args:
        text: チェック対象テキスト（タイトル+説明文）

    Returns:
        検出された禁止語リスト [{"keyword": str, "severity": str}]
    """
    if not text:
        return []

    text_lower = text.lower()
    found = []
    for keyword in PROHIBITED_KEYWORDS:
        if keyword.lower() in text_lower:
            severity = "high" if keyword in (
                "replica", "counterfeit", "fake", "dropship", "dropshipping"
            ) else "medium"
            found.append({"keyword": keyword, "severity": severity})
    return found


def check_ban_risk(
    product: Dict,
    db,
    sale_price_usd: Optional[float] = None,
) -> Dict:
    """BANリスク総合判定

    以下のチェックを実行:
    1. ブランドブラックリスト（VeRO対策）
    2. 国別配送制限
    3. 禁止キーワード
    4. 利益率（sale_price指定時のみ）

    Args:
        product: 商品データ dict（name_ja, category, description_ja 等）
        db: Database インスタンス
        sale_price_usd: 販売予定価格（利益率チェック用、省略可）

    Returns:
        {
            "safe": bool,
            "issues": [{"type": str, "detail": str, "severity": str}],
            "risk_level": "none" | "low" | "medium" | "high",
            "excluded_countries": [str],
        }
    """
    issues = []  # type: List[Dict]
    excluded_countries = []  # type: List[str]

    # --- 1. ブランドブラックリスト ---
    # 商品名（日本語・英語）と説明文をチェック
    texts_to_check = []
    if product.get("name_ja"):
        texts_to_check.append(product["name_ja"])
    if product.get("name_en"):
        texts_to_check.append(product["name_en"])
    if product.get("description_ja"):
        texts_to_check.append(product["description_ja"])
    if product.get("description_en"):
        texts_to_check.append(product["description_en"])

    combined_text = " ".join(texts_to_check)
    brand_matches = db.is_brand_blacklisted(combined_text)
    for match in brand_matches:
        issues.append({
            "type": "brand_blacklist",
            "detail": "VeROブランド検出: {} (リスク: {})".format(
                match["brand_name"], match["risk_level"]
            ),
            "severity": match["risk_level"],
        })

    # --- 2. 国別配送制限 ---
    category = product.get("category")
    if category:
        restrictions = db.get_country_restrictions(category)
        for r in restrictions:
            excluded_countries.append(r["country_code"])
            issues.append({
                "type": "country_restriction",
                "detail": "{}への配送禁止: {}".format(
                    r["country_code"], r["reason"]
                ),
                "severity": "high",
            })

    # --- 3. 禁止キーワード ---
    keyword_hits = check_prohibited_keywords(combined_text)
    for hit in keyword_hits:
        issues.append({
            "type": "prohibited_keyword",
            "detail": "禁止語検出: '{}'".format(hit["keyword"]),
            "severity": hit["severity"],
        })

    # --- 4. 利益率チェック（sale_price指定時のみ） ---
    if sale_price_usd is not None and product.get("wholesale_price_jpy"):
        profit_result = calculate_profit(
            wholesale_jpy=product["wholesale_price_jpy"],
            sale_usd=sale_price_usd,
            weight_g=product.get("weight_g"),
        )
        if not profit_result["profitable"]:
            margin_pct = round(profit_result["profit_margin"] * 100, 1)
            issues.append({
                "type": "low_margin",
                "detail": "利益率 {}% (基準: 25%以上)".format(margin_pct),
                "severity": "medium",
            })

    # --- リスクレベル判定 ---
    if not issues:
        risk_level = "none"
    elif any(i["severity"] == "high" for i in issues):
        risk_level = "high"
    elif any(i["severity"] == "medium" for i in issues):
        risk_level = "medium"
    else:
        risk_level = "low"

    safe = risk_level in ("none", "low")

    return {
        "safe": safe,
        "issues": issues,
        "risk_level": risk_level,
        "excluded_countries": sorted(set(excluded_countries)),
    }
