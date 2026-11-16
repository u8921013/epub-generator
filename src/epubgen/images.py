"""圖片處理：驗證圖片可讀、取得像素尺寸。預設不動原圖位元組。"""

import io
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


JPEG_QUALITY = 95  # 轉檔用的高品質設定
_WHITE = (255, 255, 255)


def _to_jpeg(img: Image.Image) -> tuple[bytes, int, int]:
    """把圖片轉成高品質 JPEG；帶透明度的圖合成到白底。回傳 (位元組, 寬, 高)。"""
    has_alpha = img.mode in ("RGBA", "LA", "PA") or (
        img.mode == "P" and "transparency" in img.info
    )
    if has_alpha:
        rgba = img.convert("RGBA")
        flat = Image.new("RGB", rgba.size, _WHITE)
        flat.paste(rgba, mask=rgba.getchannel("A"))
    else:
        flat = img.convert("RGB")
    buffer = io.BytesIO()
    flat.save(buffer, "JPEG", quality=JPEG_QUALITY, subsampling=0, optimize=True,
              icc_profile=img.info.get("icc_profile"))
    return buffer.getvalue(), flat.width, flat.height


def load_image(path: Path, name: str | None = None, keep_webp: bool = False) -> PageImage:
    """讀取並完整解碼圖片以確認沒有損毀。name 是錯誤訊息中顯示的檔名。

    預設原樣保留檔案位元組；例外是 WebP 會轉成 JPEG（keep_webp=True 則保留）。
    回傳的尺寸一律是最終放進 EPUB 的那張圖片。
    """
    name = name or path.name
    suffix = path.suffix.lower()
    try:
        data = path.read_bytes()
        with Image.open(path) as img:
            img.load()  # 完整解碼，才抓得到被截斷的檔案
            width, height = img.size
            if suffix == ".webp" and not keep_webp:
                data, width, height = _to_jpeg(img)
                return PageImage(data, ".jpg", MEDIA_TYPES[".jpg"], width, height)
    except Exception as exc:
        raise BrokenImageError(name) from exc
    extension = ".jpg" if suffix == ".jpeg" else suffix
    return PageImage(data, extension, MEDIA_TYPES[suffix], width, height)
