"""DeepL API 翻訳モジュール

DeepL API Free を使用して日本語→英語翻訳を提供。
Claude APIの補助として、商品名の高速翻訳・バッチ翻訳に使用。

API仕様: https://www.deepl.com/docs-api/translate-text
Free版制限: 500,000文字/月
"""

import os
from typing import Dict, List, Optional

import httpx

# DeepL API エンドポイント
DEEPL_FREE_URL = "https://api-free.deepl.com/v2/translate"
DEEPL_PRO_URL = "https://api.deepl.com/v2/translate"


class DeepLTranslator:
    """DeepL API クライアント

    環境変数 DEEPL_API_KEY からAPIキーを取得。
    Free版（api-free.deepl.com）とPro版（api.deepl.com）を自動判定。
    """

    def __init__(self, api_key=None):
        # type: (Optional[str]) -> None
        self.api_key = api_key or os.getenv("DEEPL_API_KEY", "")
        if not self.api_key:
            raise ValueError(
                "DEEPL_API_KEYが未設定です。"
                "config/.envにDeepL APIキーを設定してください。"
            )

        # Free版キーは ":fx" で終わる
        if self.api_key.endswith(":fx"):
            self.api_url = DEEPL_FREE_URL
        else:
            self.api_url = DEEPL_PRO_URL

    def translate(
        self,
        text,               # type: str
        source_lang="JA",   # type: str
        target_lang="EN",   # type: str
    ):
        # type: (...) -> str
        """単一テキストを翻訳

        Args:
            text: 翻訳元テキスト
            source_lang: ソース言語（デフォルト: JA）
            target_lang: ターゲット言語（デフォルト: EN）

        Returns:
            翻訳結果テキスト

        Raises:
            ValueError: APIエラー時
        """
        if not text or not text.strip():
            return ""

        resp = httpx.post(
            self.api_url,
            data={
                "auth_key": self.api_key,
                "text": text,
                "source_lang": source_lang,
                "target_lang": target_lang,
            },
            timeout=30.0,
        )

        if resp.status_code == 403:
            raise ValueError("DeepL API認証エラー: APIキーが無効です")
        if resp.status_code == 456:
            raise ValueError("DeepL API文字数制限超過: 月間上限に達しました")

        resp.raise_for_status()
        result = resp.json()

        translations = result.get("translations", [])
        if not translations:
            return ""

        return translations[0].get("text", "")

    def translate_batch(
        self,
        texts,              # type: List[str]
        source_lang="JA",   # type: str
        target_lang="EN",   # type: str
    ):
        # type: (...) -> List[str]
        """複数テキストを一括翻訳

        DeepL APIはtextパラメータを複数指定可能。
        1回のリクエストで最大50件まで翻訳可能。

        Args:
            texts: 翻訳元テキストのリスト
            source_lang: ソース言語
            target_lang: ターゲット言語

        Returns:
            翻訳結果テキストのリスト（入力と同じ順序）
        """
        if not texts:
            return []

        # 空テキストを除外しつつインデックスを保持
        results = [""] * len(texts)
        non_empty = [(i, t) for i, t in enumerate(texts) if t and t.strip()]

        if not non_empty:
            return results

        # 50件ずつバッチ処理
        batch_size = 50
        for batch_start in range(0, len(non_empty), batch_size):
            batch = non_empty[batch_start:batch_start + batch_size]
            batch_texts = [t for _, t in batch]

            # DeepLはtextパラメータを複数回指定で配列送信
            params = [
                ("auth_key", self.api_key),
                ("source_lang", source_lang),
                ("target_lang", target_lang),
            ]
            for t in batch_texts:
                params.append(("text", t))

            resp = httpx.post(
                self.api_url,
                data=params,
                timeout=60.0,
            )

            if resp.status_code == 403:
                raise ValueError("DeepL API認証エラー: APIキーが無効です")
            if resp.status_code == 456:
                raise ValueError("DeepL API文字数制限超過: 月間上限に達しました")

            resp.raise_for_status()
            data = resp.json()

            translations = data.get("translations", [])
            for j, trans in enumerate(translations):
                original_idx = batch[j][0]
                results[original_idx] = trans.get("text", "")

        return results

    def translate_product_names(self, products):
        # type: (List[Dict]) -> List[Dict]
        """商品リストの名前を一括翻訳してname_enを設定

        name_enが未設定の商品のみ翻訳する。
        翻訳結果は各商品dictのname_enキーに設定される。

        Args:
            products: 商品dictのリスト（name_jaキーが必要）

        Returns:
            name_enが設定された商品リスト（入力と同じオブジェクト）
        """
        # 翻訳が必要な商品を抽出
        to_translate = []
        for p in products:
            if not p.get("name_en") and p.get("name_ja"):
                to_translate.append(p)

        if not to_translate:
            return products

        names_ja = [p["name_ja"] for p in to_translate]
        names_en = self.translate_batch(names_ja)

        for p, name_en in zip(to_translate, names_en):
            p["name_en"] = name_en

        return products

    def get_usage(self):
        # type: () -> Dict
        """API使用量を取得

        Returns:
            {"character_count": int, "character_limit": int}
        """
        usage_url = self.api_url.replace("/translate", "/usage")

        resp = httpx.post(
            usage_url,
            data={"auth_key": self.api_key},
            timeout=15.0,
        )
        resp.raise_for_status()
        return resp.json()
