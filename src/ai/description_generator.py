"""AI商品説明生成モジュール

Claude API（Sonnet）を使って英語商品説明・SEOタグを生成。
JAPAN_DROPSHIP_KB.md のプロンプトテンプレート準拠。
"""

import json
import os
import re
from typing import Dict, Optional

import anthropic

# デフォルトモデル（コスト重視でSonnet使用、CLIで変更可能）
DEFAULT_MODEL = "claude-sonnet-4-6"


def _get_client() -> anthropic.Anthropic:
    """Anthropicクライアントを取得（ANTHROPIC_API_KEY必須）"""
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError(
            "ANTHROPIC_API_KEY が未設定です。"
            "config/.env に設定するか環境変数を設定してください。"
        )
    return anthropic.Anthropic(api_key=api_key)


def _parse_json_response(text: str) -> Dict:
    """Claude応答からJSONをパース

    ```json ... ``` で囲まれている場合や、余分なテキストが
    含まれている場合にも対応するfallback付きパーサー。

    Args:
        text: Claude応答テキスト

    Returns:
        パースされたdict

    Raises:
        ValueError: JSONパースに失敗した場合
    """
    # 1. そのままパースを試みる
    try:
        return json.loads(text)
    except (json.JSONDecodeError, TypeError):
        pass

    # 2. ```json ... ``` ブロックを抽出
    pattern = r"```(?:json)?\s*\n?(.*?)\n?\s*```"
    match = re.search(pattern, text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass

    # 3. 最初の { ... } ブロックを抽出
    brace_match = re.search(r"\{.*\}", text, re.DOTALL)
    if brace_match:
        try:
            return json.loads(brace_match.group(0))
        except json.JSONDecodeError:
            pass

    raise ValueError("JSONパースに失敗しました: {}".format(text[:200]))


def generate_description(
    product: Dict,
    model: Optional[str] = None,
) -> Dict:
    """商品説明を生成（英語タイトル + 説明文）

    Args:
        product: 商品データ dict
        model: 使用モデル（デフォルト: claude-sonnet-4-6）

    Returns:
        {"title": str, "description": str, "item_specifics": dict}
    """
    client = _get_client()
    model = model or DEFAULT_MODEL

    # プロンプト組み立て（KB準拠）
    product_info = "Product: {name}\n".format(
        name=product.get("name_ja", "不明")
    )
    if product.get("category"):
        product_info += "Category: {}\n".format(product["category"])
    if product.get("weight_g"):
        product_info += "Weight: {}g\n".format(product["weight_g"])
    if product.get("wholesale_price_jpy"):
        product_info += "Wholesale Price: {} JPY\n".format(
            product["wholesale_price_jpy"]
        )
    if product.get("description_ja"):
        product_info += "Description (JA): {}\n".format(
            product["description_ja"][:500]
        )

    system_prompt = (
        "You are an expert eBay copywriter specializing in Japanese cultural "
        "products for international buyers. Write compelling, SEO-optimized listings."
    )

    user_prompt = """{product_info}
Rules:
- Title: max 80 chars, SEO keywords first
- Description: 3 paragraphs
  (1) What it is + Japanese cultural context
  (2) Quality/material details + dimensions
  (3) Shipping info + care instructions
- NEVER include brand names
- NEVER mention dropshipping or wholesale
- Include "Made in Japan" naturally

Output JSON:
{{"title": "", "description": "", "item_specifics": {{}}}}""".format(
        product_info=product_info
    )

    response = client.messages.create(
        model=model,
        max_tokens=1024,
        system=system_prompt,
        messages=[{"role": "user", "content": user_prompt}],
    )

    return _parse_json_response(response.content[0].text)


def generate_seo_tags(
    product: Dict,
    model: Optional[str] = None,
) -> Dict:
    """SEOタグを生成（13タグ）

    Args:
        product: 商品データ dict
        model: 使用モデル

    Returns:
        {"tags": [str, ...]}
    """
    client = _get_client()
    model = model or DEFAULT_MODEL

    product_info = "{name} ({category})".format(
        name=product.get("name_ja", "不明"),
        category=product.get("category", "不明"),
    )

    system_prompt = (
        "Generate 13 eBay-compatible tags (max 20 chars each) for this product. "
        "Mix broad terms (\"japanese fabric\") and long-tail (\"furoshiki gift wrap\"). "
        "NEVER include brand names."
    )

    user_prompt = "Product: {}\n\nOutput JSON: {{\"tags\": [\"tag1\", \"tag2\", ...]}}".format(
        product_info
    )

    response = client.messages.create(
        model=model,
        max_tokens=512,
        system=system_prompt,
        messages=[{"role": "user", "content": user_prompt}],
    )

    return _parse_json_response(response.content[0].text)


def generate_description_ja(
    product: Dict,
    model: Optional[str] = None,
) -> Dict:
    """日本語商品説明を生成（BASEショップ向け）

    Args:
        product: 商品データ dict
        model: 使用モデル（デフォルト: claude-sonnet-4-6）

    Returns:
        {"title_ja": str, "description_ja": str}
    """
    client = _get_client()
    model = model or DEFAULT_MODEL

    # 商品情報組み立て
    product_info = "商品名: {name}\n".format(
        name=product.get("name_ja", "不明")
    )
    if product.get("category"):
        product_info += "カテゴリ: {}\n".format(product["category"])
    if product.get("weight_g"):
        product_info += "重量: {}g\n".format(product["weight_g"])
    if product.get("wholesale_price_jpy"):
        product_info += "卸値: {}円\n".format(product["wholesale_price_jpy"])
    if product.get("description_ja"):
        product_info += "説明: {}\n".format(product["description_ja"][:500])

    system_prompt = (
        "あなたは日本のECサイト（BASE）で販売する商品の魅力的な説明文を書く専門家です。"
        "日本国内の購入者向けに、商品の魅力が伝わる説明文を作成してください。"
    )

    user_prompt = """{product_info}
ルール:
- タイトル: 50文字以内、検索されやすいキーワードを含める
- 説明文: 商品の特徴・素材・使い方を丁寧に説明（200〜400文字）
- ブランド名は絶対に含めない
- ドロップシッピングや卸売に関する記述は含めない
- 「日本製」「職人」などの魅力的なキーワードを自然に含める

出力JSON:
{{"title_ja": "", "description_ja": ""}}""".format(
        product_info=product_info
    )

    response = client.messages.create(
        model=model,
        max_tokens=1024,
        system=system_prompt,
        messages=[{"role": "user", "content": user_prompt}],
    )

    return _parse_json_response(response.content[0].text)


def generate_full_listing(
    product: Dict,
    model: Optional[str] = None,
) -> Dict:
    """商品説明 + SEOタグを一括生成

    Args:
        product: 商品データ dict
        model: 使用モデル

    Returns:
        {"title": str, "description": str, "item_specifics": dict, "tags": [str]}
    """
    # 説明文生成
    desc_result = generate_description(product, model=model)

    # SEOタグ生成
    tags_result = generate_seo_tags(product, model=model)

    # マージ
    desc_result["tags"] = tags_result.get("tags", [])
    return desc_result
