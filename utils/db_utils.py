"""
Database utility functions for generating unique numbers and other common database operations.
"""
import random
import logging

# ロガー設定
logger = logging.getLogger(__name__)

def generate_unique_number(cursor, table, column, length):
    """
    指定されたテーブルのカラムに対して、一意の数値を生成します。

    Args:
        cursor: データベースカーソル（DictCursor）
        table (str): テーブル名
        column (str): カラム名
        length (int): 生成する数値の長さ

    Returns:
        str: 生成された一意の数値

    Raises:
        ValueError: 5回試行しても一意の数値が生成できない場合
    """
    for _ in range(5):  # 5回まで試行
        number = ''.join([str(random.randint(0, 9)) for _ in range(length)])
        cursor.execute(f"SELECT COUNT(*) as count FROM {table} WHERE {column} = %s", (number,))
        if cursor.fetchone()['count'] == 0:
            return number
    
    error_msg = f"Failed to generate a unique {column} after 5 attempts"
    logger.error(error_msg)
    raise ValueError(error_msg) 