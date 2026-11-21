"""epubgen：把資料夾轉成 EPUB。圖片資料夾產生 fixed layout 的漫畫書，
Markdown 資料夾產生 reflowable 的文字書（見 ADR 0001）。"""

import enum
import os
import tempfile
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from .epub import (DIRECTIONS, BookSpec, TextBookSpec, TextChapter, TocEntry, write_epub,
                   write_text_epub)
from .errors import BrokenImageError, EpubgenError
from .layout import page_viewports
from .images import ImageSettings, PageImage, cover_as_jpeg, load_image
from .metadata import is_valid_language, safe_file_name
from .markdown import render_markdown
from .scan import IMAGE_EXTENSIONS, Book, is_text_book, scan_book, scan_text_book

DEFAULT_LANGUAGE = "zh-TW"
COMIC_DEFAULT_DIRECTION = "rtl"

__all__ = ["build_epub", "BookKind", "BuildOptions", "BuildResult", "EpubgenError"]


class BookKind(enum.Enum):
    COMIC = "漫畫書"
    TEXT = "文字書"


@dataclass(frozen=True)
class BuildOptions:
    output: Path | None = None  # 預設：輸入資料夾旁邊的 <書名>.epub
    force: bool = False  # 輸出檔已存在時是否覆蓋
    skip_broken: bool = False  # 跳過損毀的圖片，而不是報錯
    direction: str | None = None  # 翻頁方向，"rtl" 或 "ltr"；None 表示未指定，依書的種類套用預設（漫畫書 rtl）
    spread: bool = False  # 雙頁模式
    title: str | None = None  # 預設：輸入資料夾名稱
    author: str | None = None
    language: str = DEFAULT_LANGUAGE
    cover: Path | None = None  # 預設：第一頁
    keep_webp: bool = False  # 預設把 WebP 轉成 JPEG；True 則保留原檔
    quality: int | None = None  # 重新壓縮的 JPEG 品質（1–100）；預設不重新壓縮
    max_size: int | None = None  # 長邊的像素上限；預設不縮放


@dataclass(frozen=True)
class BuildResult:
    output: Path
    page_count: int  # 漫畫書的頁數；文字書為 0
    skipped: tuple[str, ...] = ()  # 被 skip_broken 跳過的圖片檔名
    kind: BookKind = BookKind.COMIC
    chapter_count: int = 0  # 文字書的章數


def build_epub(input_dir: Path, options: BuildOptions = BuildOptions()) -> BuildResult:
    """給定輸入資料夾與選項，產生一個 EPUB 檔。

    輸出檔已存在時預設拒絕，options.force 才覆蓋。輸出先寫到暫存檔，
    成功後才移到目標路徑，失敗時不留下半成品。
    圖片損毀時預設報錯，options.skip_broken 則跳過並記錄在結果的 skipped。
    """
    if options.direction is not None and options.direction not in DIRECTIONS:
        raise EpubgenError(f"不合法的翻頁方向：{options.direction}（可用：{', '.join(DIRECTIONS)}）")
    direction = COMIC_DEFAULT_DIRECTION if options.direction is None else options.direction
    if options.quality is not None and not 1 <= options.quality <= 100:
        raise EpubgenError(f"不合法的品質：{options.quality}（要在 1 到 100 之間）")
    if options.max_size is not None and options.max_size < 1:
        raise EpubgenError(f"不合法的尺寸上限：{options.max_size}（要是正整數）")
    if not is_valid_language(options.language):
        raise EpubgenError(f"不合法的語言代碼：{options.language}（例如 ja、zh-TW）")
    folder = Path(input_dir).resolve()
    if not folder.exists():
        raise EpubgenError(f"輸入路徑不存在：{input_dir}")
    if not folder.is_dir():
        raise EpubgenError(f"輸入路徑不是資料夾：{input_dir}")

    text_book = is_text_book(folder)
    if text_book:
        _reject_comic_only_options(options)

    title = folder.name if options.title is None else options.title.strip()
    if not title:
        raise EpubgenError("書名不可為空")
    destination = options.output or folder.parent / f"{safe_file_name(title)}.epub"
    destination = Path(destination)
    _check_destination(destination, options.force)

    if text_book:
        return _build_text_book(input_dir, folder, title, destination, options)
    return _build_comic(input_dir, folder, title, destination, options, direction)


def _reject_comic_only_options(options: BuildOptions) -> None:
    """--direction 與 --spread 只對漫畫書有效；用在文字書時報錯，而不是默默忽略（ADR 0001）。"""
    used = []
    if options.direction is not None:
        used.append("--direction")
    if options.spread:
        used.append("--spread")
    if used:
        raise EpubgenError(f"{'、'.join(used)} 只對漫畫書有效，不能用在文字書（Markdown 資料夾）")


def _build_text_book(input_dir: Path, folder: Path, title: str, destination: Path, options: BuildOptions) -> BuildResult:
    chapters = []
    for part_title, source in scan_text_book(folder).chapters_in_reading_order():
        try:
            text = source.read_text(encoding="utf-8-sig")
        except (OSError, UnicodeDecodeError) as exc:
            raise EpubgenError(f"無法讀取 Markdown 檔（需要 UTF-8）：{source.relative_to(folder)}") from exc
        rendered = render_markdown(text)
        chapters.append(TextChapter(title=rendered.title or source.stem, body=rendered.body, part=part_title))
    if not chapters:
        raise EpubgenError(f"資料夾裡沒有任何有內容的章：{input_dir}")
    book = TextBookSpec(title=title, language=options.language, chapters=tuple(chapters),
                        author=options.author)
    _write_atomically(lambda tmp: write_text_epub(book, tmp), destination, options.force)
    return BuildResult(output=destination, page_count=0, kind=BookKind.TEXT,
                       chapter_count=len(chapters))


def _build_comic(input_dir: Path, folder: Path, title: str, destination: Path, options: BuildOptions,
                 direction: str) -> BuildResult:
    scanned = scan_book(folder)
    if not scanned.pages:
        raise EpubgenError(f"資料夾裡沒有可用的圖片：{input_dir}")
    settings = ImageSettings(options.keep_webp, options.quality, options.max_size)
    loaded = _load_pages(folder, scanned, options.skip_broken, settings)
    if not loaded.pages:
        names = "".join(f"\n  - {n}" for n in loaded.skipped)
        raise EpubgenError(f"所有圖片都無法讀取，沒有可用的圖片：{names}")
    cover_page, external_cover = _resolve_cover(options.cover, loaded, settings)

    book = BookSpec(
        title=title, language=options.language, pages=loaded.pages,
        direction=direction, spread=options.spread, chapters=tuple(loaded.toc),
        author=options.author, cover_page=cover_page, external_cover=external_cover,
        viewports=tuple(page_viewports(loaded.pages)),
    )
    _write_atomically(lambda tmp: write_epub(book, tmp), destination, options.force)
    return BuildResult(output=destination, page_count=len(loaded.pages),
                       skipped=tuple(loaded.skipped))


def _resolve_cover(cover: Path | None, loaded: "_LoadedPages", settings: ImageSettings):
    """回傳 (封面是第幾頁, 不屬於任何頁面的外部封面圖)。

    封面指向書裡的某一頁時直接標記那一頁，不重複加入；否則另外載入。
    封面是 GIF 時，Kobo 不支援，所以另外產生一張 JPEG 當封面，頁面本身維持原樣。
    """
    page, external = _pick_cover(cover, loaded, settings)
    chosen = external or loaded.pages[page - 1]
    if chosen.extension == ".gif":
        external = cover_as_jpeg(chosen, settings.quality)
    return page, external


def _pick_cover(cover: Path | None, loaded: "_LoadedPages", settings: ImageSettings):
    if cover is None:
        return 1, None
    path = Path(cover)
    if not path.exists():
        raise EpubgenError(f"封面圖片不存在：{cover}")
    if not path.is_file() or path.suffix.lower() not in IMAGE_EXTENSIONS:
        raise EpubgenError(f"封面不是支援的圖片檔（JPEG、PNG、WebP、GIF）：{cover}")
    page = loaded.page_of.get(path.resolve())
    if page is not None:
        return page, None
    try:
        return 1, load_image(path, settings=settings)
    except BrokenImageError as exc:
        raise EpubgenError(f"無法讀取封面圖片：{cover}") from exc


@dataclass
class _LoadedPages:
    pages: list[PageImage] = field(default_factory=list)
    toc: list[TocEntry] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)
    page_of: dict[Path, int] = field(default_factory=dict)  # 圖片來源 → 第幾頁（從 1 起算）


def _load_pages(folder: Path, scanned: Book, skip_broken: bool, settings: ImageSettings) -> _LoadedPages:
    """讀取所有圖片。

    章節的目錄項目指向該章第一張讀得出來的圖片；整章都讀不出來就不產生項目。
    """
    loaded = _LoadedPages()

    def load(source: Path) -> bool:
        name = source.relative_to(folder).as_posix()
        try:
            loaded.pages.append(load_image(source, name, settings))
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


def _write_atomically(write: Callable[[Path], None], destination: Path, force: bool) -> None:
    try:
        fd, tmp_name = tempfile.mkstemp(suffix=".epub.tmp", dir=destination.parent)
    except OSError as exc:
        raise EpubgenError(f"無法寫入輸出檔：{destination}（{exc.strerror or exc}）") from exc
    os.close(fd)
    tmp = Path(tmp_name)
    # mkstemp 建立的檔案只有擁有者能讀寫；輸出檔應該跟一般新建的檔案一樣遵守 umask。
    umask = os.umask(0)
    os.umask(umask)
    os.chmod(tmp, 0o666 & ~umask)
    try:
        write(tmp)
        _check_destination(destination, force)  # 寫入期間目標可能被別人建立
        os.replace(tmp, destination)
    except OSError as exc:
        tmp.unlink(missing_ok=True)
        raise EpubgenError(f"無法寫入輸出檔：{destination}（{exc.strerror or exc}）") from exc
    except BaseException:
        tmp.unlink(missing_ok=True)
        raise
