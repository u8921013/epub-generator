"""EPUB 組裝：產生 package document、navigation document 與內容文件並打包。

漫畫書是 fixed layout（每頁一個 XHTML）；文字書是 reflowable（每章一個 XHTML）。
"""

import itertools
import uuid
import zipfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from xml.sax.saxutils import escape, quoteattr

from .images import PageImage
from .layout import fit_inside

XML_DECL = '<?xml version="1.0" encoding="UTF-8"?>\n'

CONTAINER_XML = XML_DECL + """<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
  <rootfiles>
    <rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/>
  </rootfiles>
</container>
"""


DIRECTIONS = ("rtl", "ltr")


@dataclass(frozen=True)
class TocEntry:
    title: str
    page: int  # 目標頁面，從 1 起算


@dataclass(frozen=True)
class BookSpec:
    title: str
    language: str
    pages: list[PageImage]
    direction: str = "rtl"  # 翻頁方向，"rtl" 或 "ltr"
    spread: bool = False  # 是否啟用雙頁模式
    chapters: tuple[TocEntry, ...] = ()  # 空的話，目錄只有一個指向第一頁的項目
    author: str | None = None
    cover_page: int = 1  # 哪一頁的圖片是封面（從 1 起算）
    external_cover: PageImage | None = None  # 不屬於任何頁面的封面圖；有的話優先於 cover_page
    viewports: tuple[tuple[int, int], ...] = ()  # 每頁的 viewport；空的話用各頁圖片自己的尺寸


def _spread_property(index: int, direction: str) -> str | None:
    """雙頁模式下第 index 頁（從 1 起算）的 spine 屬性；不需要標記時回傳 None。

    封面不加任何標記：Kobo 規格建議第一個項目不要有跨頁屬性（iOS 會自行把
    第一頁置中並單獨成頁），而它之後的頁面從下一個跨頁開始，所以封面自然單獨一頁。
    其後依閱讀方向交替：RTL 右頁在先，LTR 左頁在先。

    使用不帶 rendition: 前綴的 page-spread-left / page-spread-right：EPUB 3.3
    認可它們（rendition: 版本是別名，較舊的閱讀系統可能只認得無前綴版本），
    也是 Kobo 規格範例使用的寫法。
    """
    if index == 1:
        return None
    first, second = ("right", "left") if direction == "rtl" else ("left", "right")
    side = first if index % 2 == 0 else second
    return f"page-spread-{side}"


def _page_xhtml(index: int, page: PageImage, title: str, viewport: tuple[int, int]) -> str:
    w, h = viewport
    if viewport == (page.width, page.height):
        img_css = f"img {{ display: block; width: {w}px; height: {h}px; }}"
    else:
        # viewport 與圖片尺寸不同（第一頁配合其餘頁面的比例）：圖片等比例縮放並置中，不變形。
        left, top, iw, ih = fit_inside(page, viewport)
        img_css = (f"img {{ position: absolute; left: {left}px; top: {top}px; "
                   f"width: {iw}px; height: {ih}px; }}")
    return (
        XML_DECL
        + '<!DOCTYPE html>\n'
        + '<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops">\n'
        + "<head>\n"
        + '  <meta charset="utf-8"/>\n'
        + f"  <title>{escape(title)} - {index}</title>\n"
        + f'  <meta name="viewport" content="width={w}, height={h}"/>\n'
        + f"  <style>html, body {{ margin: 0; padding: 0; width: {w}px; height: {h}px; }}"
        + f" {img_css}</style>\n"
        + "</head>\n"
        + "<body>\n"
        + f'  <img src="../images/img-{index:04d}{page.extension}" alt=""/>\n'
        + "</body>\n"
        + "</html>\n"
    )


def _nav_xhtml(book: BookSpec) -> str:
    entries = book.chapters or (TocEntry(book.title, 1),)
    return _nav_document(book.title, book.language,
                         [NavEntry(e.title, f"pages/page-{e.page:04d}.xhtml") for e in entries])


@dataclass(frozen=True)
class NavEntry:
    text: str
    href: str  # 相對 nav.xhtml
    children: tuple["NavEntry", ...] = ()  # 第二層項目


def _nav_items(entries: "list[NavEntry] | tuple[NavEntry, ...]", indent: str) -> str:
    """目錄的 <li> 項目；有子項目時內嵌一層 <ol>。"""
    out = ""
    for e in entries:
        link = f"<a href={quoteattr(e.href)}>{escape(e.text)}</a>"
        if e.children:
            out += (f"{indent}<li>{link}\n{indent}  <ol>\n"
                    + _nav_items(e.children, indent + "    ")
                    + f"{indent}  </ol>\n{indent}</li>\n")
        else:
            out += f"{indent}<li>{link}</li>\n"
    return out


def _nav_document(title: str, language: str, entries: list[NavEntry]) -> str:
    """navigation document；項目可以有一層子項目（文字書的部 → 章）。"""
    return (
        XML_DECL
        + '<!DOCTYPE html>\n'
        + f'<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops"'
        + f' lang={quoteattr(language)} xml:lang={quoteattr(language)}>\n'
        + f"<head>\n  <meta charset=\"utf-8\"/>\n  <title>{escape(title)}</title>\n</head>\n"
        + "<body>\n"
        + '  <nav epub:type="toc" id="toc">\n'
        + f"    <ol>\n{_nav_items(entries, '      ')}    </ol>\n"
        + "  </nav>\n"
        + "</body>\n"
        + "</html>\n"
    )


def _package_opf(book: BookSpec, identifier: str, modified: str) -> str:
    manifest = ['    <item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/>']
    spine = []
    for i, page in enumerate(book.pages, start=1):
        is_cover = book.external_cover is None and i == book.cover_page
        props = ' properties="cover-image"' if is_cover else ""
        manifest.append(
            f'    <item id="img-{i:04d}" href="images/img-{i:04d}{page.extension}"'
            f' media-type="{page.media_type}"{props}/>'
        )
        manifest.append(
            f'    <item id="page-{i:04d}" href="pages/page-{i:04d}.xhtml"'
            f' media-type="application/xhtml+xml"/>'
        )
        spread_property = _spread_property(i, book.direction) if book.spread else None
        props = f' properties="{spread_property}"' if spread_property else ""
        spine.append(f'    <itemref idref="page-{i:04d}"{props}/>')
    if book.external_cover is not None:
        cover = book.external_cover
        manifest.append(
            f'    <item id="cover-image" href="images/cover{cover.extension}"'
            f' media-type="{cover.media_type}" properties="cover-image"/>'
        )
    rendition = ('    <meta property="rendition:layout">pre-paginated</meta>\n'
                 + f'    <meta property="rendition:spread">{"landscape" if book.spread else "none"}</meta>\n')
    return _package_document(book.title, book.author, book.language, identifier, modified,
                             rendition, manifest, spine, book.direction)


def _package_document(title: str, author: str | None, language: str, identifier: str, modified: str,
                      extra_meta: str, manifest: list[str], spine: list[str], direction: str) -> str:
    """package document 的共通外框：metadata、manifest、spine。"""
    creator = f"    <dc:creator>{escape(author)}</dc:creator>\n" if author else ""
    return (
        XML_DECL
        + '<package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="book-id">\n'
        + '  <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">\n'
        + f'    <dc:identifier id="book-id">{identifier}</dc:identifier>\n'
        + f"    <dc:title>{escape(title)}</dc:title>\n"
        + creator
        + f"    <dc:language>{escape(language)}</dc:language>\n"
        + f'    <meta property="dcterms:modified">{modified}</meta>\n'
        + extra_meta
        + "  </metadata>\n"
        + "  <manifest>\n" + "\n".join(manifest) + "\n  </manifest>\n"
        + f'  <spine page-progression-direction="{direction}">\n' + "\n".join(spine) + "\n  </spine>\n"
        + "</package>\n"
    )


def write_epub(book: BookSpec, destination: Path) -> None:
    identifier, modified = _new_identity()
    viewports = book.viewports or [(p.width, p.height) for p in book.pages]
    files: list[tuple[str, str | bytes, int]] = [
        ("OEBPS/content.opf", _package_opf(book, identifier, modified), zipfile.ZIP_DEFLATED),
        ("OEBPS/nav.xhtml", _nav_xhtml(book), zipfile.ZIP_DEFLATED),
    ]
    for i, page in enumerate(book.pages, start=1):
        files.append((f"OEBPS/pages/page-{i:04d}.xhtml",
                      _page_xhtml(i, page, book.title, viewports[i - 1]), zipfile.ZIP_DEFLATED))
        files.append((f"OEBPS/images/img-{i:04d}{page.extension}", page.data, zipfile.ZIP_STORED))
    if book.external_cover is not None:
        files.append((f"OEBPS/images/cover{book.external_cover.extension}",
                      book.external_cover.data, zipfile.ZIP_STORED))
    _write_zip(destination, files)


# --- 文字書（reflowable） ------------------------------------------------------

@dataclass(frozen=True)
class TextChapter:
    title: str  # 章名，用於目錄與 <title>
    body: str  # 章的 XHTML 內文片段
    file_name: str  # 章 XHTML 的檔名（見 chapter_file_name）；書內連結也指向它，所以由建書時決定一次
    part: str | None = None  # 所屬的部；None 表示根目錄的章


@dataclass(frozen=True)
class TextBookSpec:
    title: str
    language: str
    chapters: tuple[TextChapter, ...]
    author: str | None = None
    illustrations: tuple[PageImage, ...] = ()  # 依編號排列；第 i 張的位置見 illustration_href
    cover: PageImage | None = None  # 有的話：manifest 標記為 cover-image，spine 最前面加一頁封面頁


def illustration_href(index: int, image: PageImage) -> str:
    """第 index 張插圖（從 1 起算）從章 XHTML 看過去的 href。"""
    return f"../{_illustration_path(index, image)}"


def _illustration_path(index: int, image: PageImage) -> str:
    """第 index 張插圖相對 OEBPS 的路徑。"""
    return f"images/illus-{index:04d}{image.extension}"


def chapter_file_name(index: int) -> str:
    """第 index 章（從 1 起算）XHTML 的檔名；依閱讀順序編號，與來源檔名無關。
    所有章放在同一個資料夾，章與章之間以這個檔名互連。"""
    return f"chapter-{index:04d}.xhtml"


def _chapter_href(chapter: "TextChapter") -> str:
    """章相對 OEBPS 的路徑。"""
    return f"text/{chapter.file_name}"


_STYLESHEET_HREF = "styles/book.css"

# 只排版面結構；字型、字級、行距都交給閱讀器設定，也不嵌入任何字型。
_STYLESHEET = """\
p { margin: 0.5em 0; }
h1, h2, h3, h4, h5, h6 { line-height: 1.3; margin: 1.2em 0 0.6em; page-break-after: avoid; }
blockquote { margin: 1em 0 1em 1em; padding-left: 0.8em; border-left: 0.2em solid #999; }
ul, ol { margin: 0.5em 0; padding-left: 1.5em; }
pre { font-family: monospace; white-space: pre-wrap; overflow-wrap: break-word; margin: 1em 0;
      padding: 0.5em; border: 1px solid #ccc; }
code { font-family: monospace; }
table { border-collapse: collapse; margin: 1em 0; }
th, td { border: 1px solid #999; padding: 0.25em 0.5em; }
img { max-width: 100%; height: auto; }
hr { margin: 1.5em 0; }
.cover { margin: 0; padding: 0; text-align: center; }
.cover img { max-width: 100%; max-height: 100vh; }
"""

_COVER_PAGE_HREF = "text/cover.xhtml"


def _cover_image_path(cover: PageImage) -> str:
    return f"images/cover{cover.extension}"


def _text_xhtml(title: str, language: str, body: str, body_attributes: str = "") -> str:
    """文字書的 XHTML 頁（章與封面頁共用）：引用內建 CSS，放在 text/ 之下。"""
    return (
        XML_DECL
        + '<!DOCTYPE html>\n'
        + f'<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops"'
        + f' lang={quoteattr(language)} xml:lang={quoteattr(language)}>\n'
        + f"<head>\n  <meta charset=\"utf-8\"/>\n  <title>{escape(title)}</title>\n"
        + f'  <link rel="stylesheet" type="text/css" href="../{_STYLESHEET_HREF}"/>\n</head>\n'
        + f"<body{body_attributes}>\n"
        + body
        + "</body>\n"
        + "</html>\n"
    )


def _cover_page_xhtml(book: TextBookSpec) -> str:
    """只放封面圖的頁面；不在目錄裡。"""
    image = f'  <img src="../{_cover_image_path(book.cover)}" alt={quoteattr(book.title)}/>\n'
    return _text_xhtml(book.title, book.language, image, ' class="cover" epub:type="cover"')


def _chapter_xhtml(chapter: TextChapter, language: str) -> str:
    return _text_xhtml(chapter.title, language, chapter.body)


def _text_package_opf(book: TextBookSpec, identifier: str, modified: str) -> str:
    manifest = ['    <item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/>',
                f'    <item id="css" href="{_STYLESHEET_HREF}" media-type="text/css"/>']
    spine = []
    if book.cover is not None:
        manifest.append(f'    <item id="cover-image" href="{_cover_image_path(book.cover)}"'
                        f' media-type="{book.cover.media_type}" properties="cover-image"/>')
        manifest.append(f'    <item id="cover" href="{_COVER_PAGE_HREF}" media-type="application/xhtml+xml"/>')
        spine.append('    <itemref idref="cover"/>')
    for i, chapter in enumerate(book.chapters, start=1):
        manifest.append(f'    <item id="chapter-{i:04d}" href="{_chapter_href(chapter)}"'
                        f' media-type="application/xhtml+xml"/>')
        spine.append(f'    <itemref idref="chapter-{i:04d}"/>')
    for i, image in enumerate(book.illustrations, start=1):
        manifest.append(f'    <item id="illus-{i:04d}" href="{_illustration_path(i, image)}"'
                        f' media-type="{image.media_type}"/>')
    # 不宣告 rendition:layout，預設即為 reflowable。
    return _package_document(book.title, book.author, book.language, identifier, modified,
                             "", manifest, spine, "ltr")


def _text_toc(chapters: tuple[TextChapter, ...]) -> list[NavEntry]:
    """根目錄的章是第一層項目；每部是第一層項目並指向該部第一章，其章是第二層項目。

    chapters 依閱讀順序排列，同一部的章彼此相鄰。
    """
    entries = [(c.part, NavEntry(c.title, _chapter_href(c))) for c in chapters]
    toc: list[NavEntry] = []
    for part, group in itertools.groupby(entries, key=lambda e: e[0]):
        members = [entry for _part, entry in group]
        if part is None:
            toc += members
        else:
            toc.append(NavEntry(part, members[0].href, tuple(members)))
    return toc


def write_text_epub(book: TextBookSpec, destination: Path) -> None:
    identifier, modified = _new_identity()
    nav = _nav_document(book.title, book.language, _text_toc(book.chapters))
    files: list[tuple[str, str | bytes, int]] = [
        ("OEBPS/content.opf", _text_package_opf(book, identifier, modified), zipfile.ZIP_DEFLATED),
        ("OEBPS/nav.xhtml", nav, zipfile.ZIP_DEFLATED),
        (f"OEBPS/{_STYLESHEET_HREF}", _STYLESHEET, zipfile.ZIP_DEFLATED),
    ]
    for chapter in book.chapters:
        files.append((f"OEBPS/{_chapter_href(chapter)}", _chapter_xhtml(chapter, book.language),
                      zipfile.ZIP_DEFLATED))
    for i, image in enumerate(book.illustrations, start=1):
        files.append((f"OEBPS/{_illustration_path(i, image)}", image.data, zipfile.ZIP_STORED))
    if book.cover is not None:
        files.append((f"OEBPS/{_COVER_PAGE_HREF}", _cover_page_xhtml(book), zipfile.ZIP_DEFLATED))
        files.append((f"OEBPS/{_cover_image_path(book.cover)}", book.cover.data, zipfile.ZIP_STORED))
    _write_zip(destination, files)


# --- 共通 ----------------------------------------------------------------------

def _new_identity() -> tuple[str, str]:
    """每次產生的書都有新的識別碼與修改時間。"""
    identifier = f"urn:uuid:{uuid.uuid4()}"
    modified = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    return identifier, modified


def _write_zip(destination: Path, files: list[tuple[str, str | bytes, int]]) -> None:
    """打包 EPUB：mimetype 放第一個且不壓縮，其後是 container 與各檔案。"""
    with zipfile.ZipFile(destination, "w") as z:
        z.writestr("mimetype", "application/epub+zip", compress_type=zipfile.ZIP_STORED)
        z.writestr("META-INF/container.xml", CONTAINER_XML, compress_type=zipfile.ZIP_DEFLATED)
        for name, data, compression in files:
            z.writestr(name, data, compress_type=compression)
