"""eBay sold count スクレイパー

Browse APIにsold countフィールドがないため、
Playwright + stealth で商品ページから "X sold" テキストを取得する。

使用は補完目的のみ。メインデータはBrowse APIから取得。
"""

import re
from typing import Any, Dict, List


async def get_sold_counts(
    item_urls: List[str],
    headless: bool = True,
) -> List[Dict[str, Any]]:
    """商品URLリストからsold countを取得

    Args:
        item_urls: eBay商品ページURL（最大10件推奨）
        headless: ブラウザをヘッドレスで実行

    Returns:
        [{url, sold_count, sold_text}]
    """
    # playwright は重い依存なので遅延インポート
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        raise ImportError(
            "playwrightがインストールされていません。"
            "pip install playwright && playwright install chromium"
        )

    results = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=headless)
        context = await browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1280, "height": 720},
        )

        for url in item_urls:
            try:
                page = await context.new_page()
                await page.goto(url, wait_until="domcontentloaded", timeout=15000)

                # "X sold" テキストを探す
                sold_count = None
                sold_text = None

                # 複数のセレクタを試行（eBayのHTML構造は変わることがある）
                selectors = [
                    'span.d-quantity__sold',
                    '[data-testid="x-quantity__sold"]',
                    'span:has-text("sold")',
                ]

                for selector in selectors:
                    try:
                        element = await page.query_selector(selector)
                        if element:
                            text = await element.inner_text()
                            sold_text = text.strip()
                            # "123 sold" → 123
                            match = re.search(r"([\d,]+)\s*sold", text, re.IGNORECASE)
                            if match:
                                sold_count = int(match.group(1).replace(",", ""))
                            break
                    except Exception:
                        continue

                results.append({
                    "url": url,
                    "sold_count": sold_count,
                    "sold_text": sold_text,
                })
                await page.close()

            except Exception as e:
                results.append({
                    "url": url,
                    "sold_count": None,
                    "sold_text": None,
                    "error": str(e),
                })

        await browser.close()

    return results
