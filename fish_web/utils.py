"""複数の箇所（View・管理コマンド）から共通で使うユーティリティ関数"""


def get_next_month(year, month):
    """指定した年月の翌月を返す（12月の場合は翌年1月になる）"""
    if month == 12:
        return year + 1, 1
    return year, month + 1
