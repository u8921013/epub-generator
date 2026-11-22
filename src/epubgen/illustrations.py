"""文字書的插圖：載入被 md 引用的本地圖片，同一個來源檔案只載入、打包一次。

圖片處理（WebP 轉 JPEG、--quality、--max-size、損毀判斷）沿用漫畫書的 load_image。
"""

from pathlib import Path

from .epub import illustration_href
from .errors import BrokenImageError, EpubgenError
from .images import ImageSettings, PageImage, load_image


class Illustrations:
    def __init__(self, settings: ImageSettings, skip_broken: bool):
        self._settings = settings
        self._skip_broken = skip_broken
        self._href_of: dict[Path, str | None] = {}  # 來源的絕對路徑 → href；被跳過的是 None
        self.images: list[PageImage] = []  # 依編號排列，交給 EPUB 組裝
        self.skipped: list[str] = []

    def href(self, path: Path, name: str) -> str | None:
        """插圖從章 XHTML 看過去的 href。找不到或損毀時預設報錯；skip_broken 時記到跳過清單並回傳 None。

        name 是訊息裡顯示的名稱。
        """
        key = path.resolve()
        if key not in self._href_of:
            self._href_of[key] = self._load(path, name)
        return self._href_of[key]

    def _load(self, path: Path, name: str) -> str | None:
        image = problem = None
        if not path.is_file():
            problem = f"找不到插圖：{name}"
        else:
            try:
                image = load_image(path, name, self._settings)
            except BrokenImageError as exc:
                problem = str(exc)
        if image is None:
            if not self._skip_broken:
                raise EpubgenError(f"{problem}（要跳過找不到或損毀的插圖請加上 --skip-broken）")
            self.skipped.append(name)
            return None
        self.images.append(image)
        return illustration_href(len(self.images), image)
