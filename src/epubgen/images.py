"""圖片處理：驗證圖片可讀、取得像素尺寸。預設不動原圖位元組。"""

from dataclasses import dataclass
from pathlib import Path

from PIL import Image

from .errors import EpubgenError

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


def load_image(path: Path) -> PageImage:
    data = path.read_bytes()
    try:
        with Image.open(path) as img:
            img.verify()
        with Image.open(path) as img:
            width, height = img.size
    except Exception as exc:
        raise EpubgenError(f"無法讀取圖片：{path.name}") from exc
    suffix = path.suffix.lower()
    extension = ".jpg" if suffix == ".jpeg" else suffix
    return PageImage(data, extension, MEDIA_TYPES[suffix], width, height)
