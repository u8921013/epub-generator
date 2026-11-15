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


def build_epub(input_dir: Path, output: Path | None = None, force: bool = False) -> BuildResult:
    """給定輸入資料夾，產生一個 EPUB 檔。

    輸出檔已存在時預設拒絕，force=True 才覆蓋。輸出先寫到暫存檔，
    成功後才移到目標路徑，失敗時不留下半成品。
    """
    folder = Path(input_dir).resolve()
    if not folder.is_dir():
        raise EpubgenError(f"輸入路徑不是資料夾：{input_dir}")
    title = folder.name
    destination = Path(output) if output else folder.parent / f"{title}.epub"
    _check_destination(destination, force)

    sources = scan_pages(folder)
    if not sources:
        raise EpubgenError(f"資料夾裡沒有可用的圖片：{input_dir}")
    pages = [load_image(p) for p in sources]

    book = BookSpec(title=title, language=DEFAULT_LANGUAGE, pages=pages)
    _write_atomically(book, destination, force)
    return BuildResult(output=destination, page_count=len(pages))


def _check_destination(destination: Path, force: bool) -> None:
    if destination.is_dir():
        raise EpubgenError(f"輸出路徑是資料夾，請指定檔名：{destination}")
    if not destination.parent.is_dir():
        raise EpubgenError(f"輸出資料夾不存在：{destination.parent}")
    if destination.exists() and not force:
        raise EpubgenError(f"輸出檔已存在：{destination}（要覆蓋請加上 --force）")


def _write_atomically(book: BookSpec, destination: Path, force: bool) -> None:
    try:
        fd, tmp_name = tempfile.mkstemp(suffix=".epub.tmp", dir=destination.parent)
    except OSError as exc:
        raise EpubgenError(f"無法寫入輸出檔：{destination}（{exc.strerror or exc}）") from exc
    os.close(fd)
    tmp = Path(tmp_name)
    try:
        write_epub(book, tmp)
        _check_destination(destination, force)  # 寫入期間目標可能被別人建立
        os.replace(tmp, destination)
    except OSError as exc:
        tmp.unlink(missing_ok=True)
        raise EpubgenError(f"無法寫入輸出檔：{destination}（{exc.strerror or exc}）") from exc
    except BaseException:
        tmp.unlink(missing_ok=True)
        raise
