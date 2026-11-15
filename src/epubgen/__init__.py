"""epubgen：把圖片資料夾轉成 fixed layout 的漫畫 EPUB。"""

import os
import tempfile
from dataclasses import dataclass
from pathlib import Path

from .epub import DIRECTIONS, BookSpec, TocEntry, write_epub
from .errors import BrokenImageError, EpubgenError
from .images import load_image
from .scan import Book, scan_book

DEFAULT_LANGUAGE = "zh-TW"

__all__ = ["build_epub", "BuildResult", "EpubgenError"]


@dataclass(frozen=True)
class BuildResult:
    output: Path
    page_count: int
    skipped: tuple[str, ...] = ()  # 被 skip_broken 跳過的圖片檔名


def build_epub(
    input_dir: Path,
    output: Path | None = None,
    force: bool = False,
    skip_broken: bool = False,
    direction: str = "rtl",
    spread: bool = False,
) -> BuildResult:
    """給定輸入資料夾，產生一個 EPUB 檔。

    輸出檔已存在時預設拒絕，force=True 才覆蓋。輸出先寫到暫存檔，
    成功後才移到目標路徑，失敗時不留下半成品。
    圖片損毀時預設報錯，skip_broken=True 則跳過並記錄在結果的 skipped。
    direction 是翻頁方向（"rtl" 或 "ltr"），spread=True 啟用雙頁模式。
    """
    if direction not in DIRECTIONS:
        raise EpubgenError(f"不合法的翻頁方向：{direction}（可用：{', '.join(DIRECTIONS)}）")
    folder = Path(input_dir).resolve()
    if not folder.exists():
        raise EpubgenError(f"輸入路徑不存在：{input_dir}")
    if not folder.is_dir():
        raise EpubgenError(f"輸入路徑不是資料夾：{input_dir}")
    title = folder.name
    destination = Path(output) if output else folder.parent / f"{title}.epub"
    _check_destination(destination, force)

    scanned = scan_book(folder)
    if not scanned.pages:
        raise EpubgenError(f"資料夾裡沒有可用的圖片：{input_dir}")
    pages, toc, skipped = _load_pages(folder, scanned, skip_broken)
    if not pages:
        names = "".join(f"\n  - {n}" for n in skipped)
        raise EpubgenError(f"所有圖片都無法讀取，沒有可用的圖片：{names}")

    book = BookSpec(title=title, language=DEFAULT_LANGUAGE, pages=pages,
                    direction=direction, spread=spread, chapters=tuple(toc))
    _write_atomically(book, destination, force)
    return BuildResult(output=destination, page_count=len(pages), skipped=tuple(skipped))


def _load_pages(folder: Path, scanned: Book, skip_broken: bool):
    """讀取所有圖片，回傳 (頁面, 目錄項目, 被跳過的檔名)。

    章節的目錄項目指向該章第一張讀得出來的圖片；整章都讀不出來就不產生項目。
    """
    pages, toc, skipped = [], [], []

    def load(source: Path) -> bool:
        name = source.relative_to(folder).as_posix()
        try:
            pages.append(load_image(source, name))
        except BrokenImageError as exc:
            if not skip_broken:
                raise EpubgenError(f"{exc}（要跳過損毀的圖片請加上 --skip-broken）") from exc
            skipped.append(name)
            return False
        return True

    for source in scanned.front_pages:
        load(source)
    for chapter in scanned.chapters:
        first_page = len(pages) + 1
        if sum(load(source) for source in chapter.pages):
            toc.append(TocEntry(chapter.title, first_page))
    return pages, toc, skipped


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
