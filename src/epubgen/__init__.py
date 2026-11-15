"""epubgen：把圖片資料夾轉成 fixed layout 的漫畫 EPUB。"""

import os
import tempfile
from dataclasses import dataclass
from pathlib import Path

from .epub import BookSpec, write_epub
from .errors import EpubgenError
from .images import load_image
from .scan import scan_pages

DEFAULT_LANGUAGE = "zh-TW"

__all__ = ["build_epub", "BuildResult", "EpubgenError"]


@dataclass(frozen=True)
class BuildResult:
    output: Path
    page_count: int


def build_epub(input_dir: Path, output: Path | None = None) -> BuildResult:
    """給定輸入資料夾，產生一個 EPUB 檔。"""
    folder = Path(input_dir).resolve()
    if not folder.is_dir():
        raise EpubgenError(f"輸入路徑不是資料夾：{input_dir}")
    title = folder.name
    destination = Path(output) if output else folder.parent / f"{title}.epub"

    sources = scan_pages(folder)
    if not sources:
        raise EpubgenError(f"資料夾裡沒有可用的圖片：{input_dir}")
    pages = [load_image(p) for p in sources]

    # 先寫到暫存檔，成功後才移到目標路徑，失敗時不留下半成品。
    fd, tmp_name = tempfile.mkstemp(suffix=".epub.tmp", dir=destination.parent)
    os.close(fd)
    try:
        write_epub(BookSpec(title=title, language=DEFAULT_LANGUAGE, pages=pages), Path(tmp_name))
        os.replace(tmp_name, destination)
    except BaseException:
        Path(tmp_name).unlink(missing_ok=True)
        raise
    return BuildResult(output=destination, page_count=len(pages))
