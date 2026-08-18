"""複数の箇所（View・管理コマンド）から共通で使うユーティリティ関数"""


def get_next_month(year, month):
    """指定した年月の翌月を返す（12月の場合は翌年1月になる）"""
    if month == 12:
        return year + 1, 1
    return year, month + 1


def shift_month(year, month, offset):
    """year/monthをoffsetヶ月分シフトした年月を返す（offsetは負の値で過去方向にシフト）"""
    index = year * 12 + (month - 1) + offset
    return index // 12, index % 12 + 1
