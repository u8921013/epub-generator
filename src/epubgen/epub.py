"""EPUB 組裝：產生 package document、navigation document、每頁 XHTML 並打包。"""

import uuid
import zipfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from xml.sax.saxutils import escape, quoteattr

from .images import PageImage
from .layout import fit_inside, own_viewports

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
        page_background = ""
    else:
        # viewport 與圖片尺寸不同（--uniform-size）：圖片等比例縮放並置中，不變形。
        left, top, iw, ih = fit_inside(page, viewport)
        img_css = (f"img {{ position: absolute; left: {left}px; top: {top}px; "
                   f"width: {iw}px; height: {ih}px; }}")
        page_background = " background: #fff;"  # 留白處的底色
    return (
        XML_DECL
        + '<!DOCTYPE html>\n'
        + '<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops">\n'
        + "<head>\n"
        + '  <meta charset="utf-8"/>\n'
        + f"  <title>{escape(title)} - {index}</title>\n"
        + f'  <meta name="viewport" content="width={w}, height={h}"/>\n'
        + f"  <style>html, body {{ margin: 0; padding: 0; width: {w}px; height: {h}px;"
        + f"{page_background} }} {img_css}</style>\n"
        + "</head>\n"
        + "<body>\n"
        + f'  <img src="../images/img-{index:04d}{page.extension}" alt=""/>\n'
        + "</body>\n"
        + "</html>\n"
    )


def _nav_xhtml(book: BookSpec) -> str:
    title, language = book.title, book.language
    entries = book.chapters or (TocEntry(title, 1),)
    items = "".join(
        f'      <li><a href="pages/page-{e.page:04d}.xhtml">{escape(e.title)}</a></li>\n'
        for e in entries
    )
    return (
        XML_DECL
        + '<!DOCTYPE html>\n'
        + f'<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops"'
        + f' lang={quoteattr(language)} xml:lang={quoteattr(language)}>\n'
        + f"<head>\n  <meta charset=\"utf-8\"/>\n  <title>{escape(title)}</title>\n</head>\n"
        + "<body>\n"
        + '  <nav epub:type="toc" id="toc">\n'
        + f"    <ol>\n{items}    </ol>\n"
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
    creator = f"    <dc:creator>{escape(book.author)}</dc:creator>\n" if book.author else ""
    return (
        XML_DECL
        + '<package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="book-id">\n'
        + '  <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">\n'
        + f'    <dc:identifier id="book-id">{identifier}</dc:identifier>\n'
        + f"    <dc:title>{escape(book.title)}</dc:title>\n"
        + creator
        + f"    <dc:language>{escape(book.language)}</dc:language>\n"
        + f'    <meta property="dcterms:modified">{modified}</meta>\n'
        + '    <meta property="rendition:layout">pre-paginated</meta>\n'
        + f'    <meta property="rendition:spread">{"landscape" if book.spread else "none"}</meta>\n'
        + "  </metadata>\n"
        + "  <manifest>\n" + "\n".join(manifest) + "\n  </manifest>\n"
        + f'  <spine page-progression-direction="{book.direction}">\n' + "\n".join(spine) + "\n  </spine>\n"
        + "</package>\n"
    )


def write_epub(book: BookSpec, destination: Path) -> None:
    identifier = f"urn:uuid:{uuid.uuid4()}"
    modified = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    with zipfile.ZipFile(destination, "w") as z:
        z.writestr("mimetype", "application/epub+zip", compress_type=zipfile.ZIP_STORED)
        z.writestr("META-INF/container.xml", CONTAINER_XML, compress_type=zipfile.ZIP_DEFLATED)
        z.writestr("OEBPS/content.opf", _package_opf(book, identifier, modified),
                   compress_type=zipfile.ZIP_DEFLATED)
        z.writestr("OEBPS/nav.xhtml", _nav_xhtml(book),
                   compress_type=zipfile.ZIP_DEFLATED)
        viewports = book.viewports or own_viewports(book.pages)
        for i, page in enumerate(book.pages, start=1):
            z.writestr(f"OEBPS/pages/page-{i:04d}.xhtml", _page_xhtml(i, page, book.title, viewports[i - 1]),
                       compress_type=zipfile.ZIP_DEFLATED)
            z.writestr(f"OEBPS/images/img-{i:04d}{page.extension}", page.data,
                       compress_type=zipfile.ZIP_STORED)
        if book.external_cover is not None:
            z.writestr(f"OEBPS/images/cover{book.external_cover.extension}",
                       book.external_cover.data, compress_type=zipfile.ZIP_STORED)
