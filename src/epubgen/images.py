"""圖片處理：驗證圖片可讀、取得像素尺寸。預設不動原圖位元組。"""

import io
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageFile, ImageOps

from .errors import BrokenImageError

MEDIA_TYPES = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
    ".gif": "image/gif",
}

# Pillow 偵測到的實際格式 → 打包時用的副檔名。MPO 是相機產生、內含多張圖的 JPEG，
# 原樣打包就是一般 JPEG。不在這裡的格式（例如改名成 .jpg 的 BMP）一律轉成 JPEG。
FORMAT_EXTENSIONS = {
    "JPEG": ".jpg",
    "MPO": ".jpg",
    "PNG": ".png",
    "GIF": ".gif",
    "WEBP": ".webp",
}


@dataclass(frozen=True)
class PageImage:
    data: bytes
    extension: str  # 含點，小寫，例如 ".jpg"
    media_type: str
    width: int
    height: int


JPEG_QUALITY = 95  # 沒有指定 --quality 時，轉檔或縮放後重新編碼用的高品質設定
_WHITE = (255, 255, 255)


@dataclass(frozen=True)
class ImageSettings:
    """圖片處理選項。全部都是預設值時，只有 WebP 會被動到（轉成 JPEG）。"""

    keep_webp: bool = False  # True：WebP 不轉成 JPEG
    quality: int | None = None  # 重新壓縮的品質（1–100）；None 表示不主動重新壓縮
    max_size: int | None = None  # 長邊的像素上限；None 表示不縮放


def _flatten(img: Image.Image) -> Image.Image:
    """帶透明度的圖合成到白底，其他模式轉成 RGB。"""
    has_alpha = img.mode in ("RGBA", "LA", "PA") or (
        img.mode == "P" and "transparency" in img.info
    )
    if not has_alpha:
        return img.convert("RGB")
    rgba = img.convert("RGBA")
    flat = Image.new("RGB", rgba.size, _WHITE)
    flat.paste(rgba, mask=rgba.getchannel("A"))
    return flat


def _encode_jpeg(img: Image.Image, quality: int) -> tuple[bytes, int, int]:
    flat = _flatten(img)
    # optimize=True 時 libjpeg 要一次把整個輸出放進緩衝區；細節很多的大頁面會超過
    # Pillow 預設的 64KB 而失敗（OSError: broken data stream），所以放寬到不可能超過的大小。
    ImageFile.MAXBLOCK = max(ImageFile.MAXBLOCK, flat.width * flat.height * 3 + 65536)
    buffer = io.BytesIO()
    flat.save(buffer, "JPEG", quality=quality, subsampling=0, optimize=True,
              icc_profile=img.info.get("icc_profile"))
    return buffer.getvalue(), flat.width, flat.height


def _to_jpeg(img: Image.Image) -> tuple[bytes, int, int]:
    """把圖片轉成高品質 JPEG；帶透明度的圖合成到白底。回傳 (位元組, 寬, 高)。"""
    return _encode_jpeg(img, JPEG_QUALITY)


def _plan(kind: str | None, size: tuple[int, int], settings: ImageSettings) -> str | None:
    """決定這張圖要不要處理、處理後是什麼格式（"JPEG"、"PNG"、"WEBP"），None 表示原樣打包。

    kind 是依實際內容判斷的副檔名（見 FORMAT_EXTENSIONS），不看檔名，所以存成 a.jpg 的
    PNG 依 PNG 的規則處理。kind 為 None（EPUB 不支援的格式）時一律轉成 JPEG。

    - JPEG：給了 quality 或超過上限時重新編碼成 JPEG。
    - PNG：給了 quality 時轉成 JPEG；只有超過上限時縮小並維持 PNG（無損）。
    - WebP：預設轉成 JPEG；keep_webp 時，需要處理才重新編碼成 WebP。
    - GIF：只有超過上限時縮小並轉成 JPEG（動畫只留第一個畫格）；quality 不影響 GIF。
    """
    oversize = settings.max_size is not None and max(size) > settings.max_size
    recompress = settings.quality is not None
    if kind is None:
        return "JPEG"
    if kind == ".webp":
        if not settings.keep_webp:
            return "JPEG"
        return "WEBP" if oversize or recompress else None
    if kind == ".gif":
        return "JPEG" if oversize else None
    if kind == ".jpg":
        return "JPEG" if oversize or recompress else None
    if kind == ".png":
        if recompress:
            return "JPEG"
        return "PNG" if oversize else None
    return None


def _scaled(size: tuple[int, int], limit: int) -> tuple[int, int]:
    ratio = limit / max(size)
    return max(1, round(size[0] * ratio)), max(1, round(size[1] * ratio))


def _render(img: Image.Image, fmt: str, settings: ImageSettings) -> tuple[PageImage, bool]:
    """依 fmt 重新編碼。回傳 (圖片, 是否縮小過)。"""
    img = ImageOps.exif_transpose(img)  # 重新編碼會丟掉 EXIF，所以先把方向轉正
    resized = settings.max_size is not None and max(img.size) > settings.max_size
    if resized:
        if img.mode in ("P", "PA"):
            img = img.convert("RGBA" if "transparency" in img.info or img.mode == "PA" else "RGB")
        img = img.resize(_scaled(img.size, settings.max_size), Image.LANCZOS)
    quality = settings.quality or JPEG_QUALITY
    if fmt == "JPEG":
        data, width, height = _encode_jpeg(img, quality)
        return PageImage(data, ".jpg", MEDIA_TYPES[".jpg"], width, height), resized
    buffer = io.BytesIO()
    keep_alpha = img.mode in ("RGBA", "LA", "PA") or (img.mode == "P" and "transparency" in img.info)
    out = img.convert("RGBA" if keep_alpha else "RGB")
    if fmt == "PNG":
        out.save(buffer, "PNG", optimize=True, icc_profile=img.info.get("icc_profile"))
        return PageImage(buffer.getvalue(), ".png", MEDIA_TYPES[".png"], *out.size), resized
    out.save(buffer, "WEBP", quality=quality, icc_profile=img.info.get("icc_profile"))
    return PageImage(buffer.getvalue(), ".webp", MEDIA_TYPES[".webp"], *out.size), resized


def _keeps_original(kind: str | None, fmt: str, resized: bool, new_size: int, old_size: int) -> bool:
    """只重新壓縮（沒縮小、格式沒變）卻變得更大時，維持原檔：使用者要的是縮小檔案。

    WebP 預設轉成 JPEG 是格式轉換，不適用這條。
    """
    same_format = (kind == ".jpg" and fmt == "JPEG") or (kind == ".webp" and fmt == "WEBP")
    return same_format and not resized and new_size >= old_size


def load_image(path: Path, name: str | None = None,
               settings: ImageSettings = ImageSettings()) -> PageImage:
    """讀取並完整解碼圖片以確認沒有損毀。name 是錯誤訊息中顯示的檔名。

    預設原樣保留檔案位元組；只有 WebP 預設會轉成 JPEG，其餘只有使用者給了
    --quality 或 --max-size 才會重新編碼（規則見 _plan）。
    格式一律依 Pillow 偵測到的實際內容判斷，不看副檔名：存成 a.jpg 的 PNG 會以
    .png、image/png 打包，避免 EPUB 宣告錯誤的媒體類型。
    回傳的尺寸一律是最終放進 EPUB 的那張圖片。
    """
    name = name or path.name
    try:
        data = path.read_bytes()
        with Image.open(path) as img:
            img.load()  # 完整解碼，才抓得到被截斷的檔案
            width, height = img.size
            kind = FORMAT_EXTENSIONS.get(img.format)
            fmt = _plan(kind, (width, height), settings)
            if fmt is not None:
                processed, resized = _render(img, fmt, settings)
                if not _keeps_original(kind, fmt, resized, len(processed.data), len(data)):
                    return processed
    except Exception as exc:
        raise BrokenImageError(name) from exc
    return PageImage(data, kind, MEDIA_TYPES[kind], width, height)


def cover_as_jpeg(page: PageImage, quality: int | None = None) -> PageImage:
    """把 GIF 封面轉成 JPEG（Kobo 不支援 GIF 封面）。動畫只取第一個畫格，透明處合成到白底。"""
    with Image.open(io.BytesIO(page.data)) as img:
        img.seek(0)
        img.load()
        data, width, height = _encode_jpeg(img, quality or JPEG_QUALITY)
    return PageImage(data, ".jpg", MEDIA_TYPES[".jpg"], width, height)
