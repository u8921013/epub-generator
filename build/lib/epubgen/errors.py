class EpubgenError(Exception):
    """可預期的失敗，訊息會直接顯示給使用者。"""


class BrokenImageError(EpubgenError):
    """圖片無法讀取或已損毀。"""

    def __init__(self, name: str):
        super().__init__(f"無法讀取圖片：{name}")
        self.name = name
