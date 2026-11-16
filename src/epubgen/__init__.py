"""epubgen：把圖片資料夾轉成 fixed layout 的漫畫 EPUB。"""

import os
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

from .epub import DIRECTIONS, BookSpec, TocEntry, write_epub
from .errors import BrokenImageError, EpubgenError
from .images import PageImage, load_image
from .metadata import is_valid_language, safe_file_name
from .scan import IMAGE_EXTENSIONS, Book, scan_book

DEFAULT_LANGUAGE = "zh-TW"

__all__ = ["build_epub", "BuildOptions", "BuildResult", "EpubgenError"]


@dataclass(frozen=True)
class BuildOptions:
    output: Path | None = None  # 預設：輸入資料夾旁邊的 <書名>.epub
    force: bool = False  # 輸出檔已存在時是否覆蓋
    skip_broken: bool = False  # 跳過損毀的圖片，而不是報錯
    direction: str = "rtl"  # 翻頁方向，"rtl" 或 "ltr"
    spread: bool = False  # 雙頁模式
    title: str | None = None  # 預設：輸入資料夾名稱
    author: str | None = None
    language: str = DEFAULT_LANGUAGE
    cover: Path | None = None  # 預設：第一頁
    keep_webp: bool = False  # 預設把 WebP 轉成 JPEG；True 則保留原檔


@dataclass(frozen=True)
class BuildResult:
    output: Path
    page_count: int
    skipped: tuple[str, ...] = ()  # 被 skip_broken 跳過的圖片檔名


def build_epub(input_dir: Path, options: BuildOptions = BuildOptions()) -> BuildResult:
    """給定輸入資料夾與選項，產生一個 EPUB 檔。

    輸出檔已存在時預設拒絕，options.force 才覆蓋。輸出先寫到暫存檔，
    成功後才移到目標路徑，失敗時不留下半成品。
    圖片損毀時預設報錯，options.skip_broken 則跳過並記錄在結果的 skipped。
    """
    if options.direction not in DIRECTIONS:
        raise EpubgenError(f"不合法的翻頁方向：{options.direction}（可用：{', '.join(DIRECTIONS)}）")
    if not is_valid_language(options.language):
        raise EpubgenError(f"不合法的語言代碼：{options.language}（例如 ja、zh-TW）")
    folder = Path(input_dir).resolve()
    if not folder.exists():
        raise EpubgenError(f"輸入路徑不存在：{input_dir}")
    if not folder.is_dir():
        raise EpubgenError(f"輸入路徑不是資料夾：{input_dir}")

    title = folder.name if options.title is None else options.title.strip()
    if not title:
        raise EpubgenError("書名不可為空")
    destination = options.output or folder.parent / f"{safe_file_name(title)}.epub"
    destination = Path(destination)
    _check_destination(destination, options.force)

    scanned = scan_book(folder)
    if not scanned.pages:
        raise EpubgenError(f"資料夾裡沒有可用的圖片：{input_dir}")
    loaded = _load_pages(folder, scanned, options.skip_broken, options.keep_webp)
    if not loaded.pages:
        names = "".join(f"\n  - {n}" for n in loaded.skipped)
        raise EpubgenError(f"所有圖片都無法讀取，沒有可用的圖片：{names}")
    cover_page, external_cover = _resolve_cover(options.cover, loaded.page_of, options.keep_webp)

    book = BookSpec(
        title=title, language=options.language, pages=loaded.pages,
        direction=options.direction, spread=options.spread, chapters=tuple(loaded.toc),
        author=options.author, cover_page=cover_page, external_cover=external_cover,
    )
    _write_atomically(book, destination, options.force)
    return BuildResult(output=destination, page_count=len(loaded.pages),
                       skipped=tuple(loaded.skipped))


def _resolve_cover(cover: Path | None, page_of: dict[Path, int], keep_webp: bool):
    """回傳 (封面是第幾頁, 不屬於任何頁面的外部封面圖)。

    封面指向書裡的某一頁時直接標記那一頁，不重複加入；否則另外載入。
    """
    if cover is None:
        return 1, None
    path = Path(cover)
    if not path.exists():
        raise EpubgenError(f"封面圖片不存在：{cover}")
    if not path.is_file() or path.suffix.lower() not in IMAGE_EXTENSIONS:
        raise EpubgenError(f"封面不是支援的圖片檔（JPEG、PNG、WebP、GIF）：{cover}")
    page = page_of.get(path.resolve())
    if page is not None:
        return page, None
    try:
        return 1, load_image(path, keep_webp=keep_webp)
    except BrokenImageError as exc:
        raise EpubgenError(f"無法讀取封面圖片：{cover}") from exc


@dataclass
class _LoadedPages:
    pages: list[PageImage] = field(default_factory=list)
    toc: list[TocEntry] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)
    page_of: dict[Path, int] = field(default_factory=dict)  # 圖片來源 → 第幾頁（從 1 起算）


def _load_pages(folder: Path, scanned: Book, skip_broken: bool, keep_webp: bool) -> _LoadedPages:
    """讀取所有圖片。

    章節的目錄項目指向該章第一張讀得出來的圖片；整章都讀不出來就不產生項目。
    """
    loaded = _LoadedPages()

    def load(source: Path) -> bool:
        name = source.relative_to(folder).as_posix()
        try:
            loaded.pages.append(load_image(source, name, keep_webp))
        except BrokenImageError as exc:
            if not skip_broken:
                raise EpubgenError(f"{exc}（要跳過損毀的圖片請加上 --skip-broken）") from exc
            loaded.skipped.append(name)
            return False
        loaded.page_of[source.resolve()] = len(loaded.pages)
        return True

    for source in scanned.front_pages:
        load(source)
    for chapter in scanned.chapters:
        first_page = len(loaded.pages) + 1
        if sum(load(source) for source in chapter.pages):
            loaded.toc.append(TocEntry(chapter.title, first_page))
    return loaded


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
