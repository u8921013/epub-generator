"""圖片處理：驗證圖片可讀、取得像素尺寸。預設不動原圖位元組。"""

from dataclasses import dataclass
from pathlib import Path

from PIL import Image

from .errors import BrokenImageError

MEDIA_TYPES = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
    ".gif": "image/gif",
}


@dataclass(frozen=True)
class PageImage:
    data: bytes
    extension: str  # 含點，小寫，例如 ".jpg"
    media_type: str
    width: int
    height: int


def load_image(path: Path, name: str | None = None) -> PageImage:
    """讀取並完整解碼圖片以確認沒有損毀。name 是錯誤訊息中顯示的檔名。"""
    name = name or path.name
    try:
        data = path.read_bytes()
        with Image.open(path) as img:
            img.load()  # 完整解碼，才抓得到被截斷的檔案
            width, height = img.size
    except Exception as exc:
        raise BrokenImageError(name) from exc
    suffix = path.suffix.lower()
    extension = ".jpg" if suffix == ".jpeg" else suffix
    return PageImage(data, extension, MEDIA_TYPES[suffix], width, height)
