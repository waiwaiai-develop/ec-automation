"""DB初期化スクリプト

テーブル作成 + シードデータ投入。冪等に実行可能。
CLIからも直接実行可能: python scripts/setup_db.py
"""

import sys
from pathlib import Path

# プロジェクトルートをパスに追加
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.db.database import Database


def main():
    db = Database()
    print(f"DB: {db.db_path}")

    # テーブル作成
    tables = db.init_tables()
    print(f"テーブル作成完了: {', '.join(tables)}")

    # シードデータ
    counts = db.seed_data()
    for table, count in counts.items():
        print(f"  {table}: {count}件追加")

    # 統計
    stats = db.get_stats()
    print("\n--- DB統計 ---")
    for key, value in stats.items():
        if isinstance(value, dict):
            print(f"  {key}:")
            for k, v in value.items():
                print(f"    {k}: {v}")
        else:
            print(f"  {key}: {value}")


if __name__ == "__main__":
    main()
