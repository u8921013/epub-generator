"""EPUB 組裝：產生 package document、navigation document、每頁 XHTML 並打包。"""

import uuid
import zipfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from xml.sax.saxutils import escape, quoteattr

from .images import PageImage

XML_DECL = '<?xml version="1.0" encoding="UTF-8"?>\n'

CONTAINER_XML = XML_DECL + """<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
  <rootfiles>
    <rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/>
  </rootfiles>
</container>
"""


@dataclass(frozen=True)
class BookSpec:
    title: str
    language: str
    pages: list[PageImage]


def _page_xhtml(index: int, page: PageImage, title: str) -> str:
    w, h = page.width, page.height
    return (
        XML_DECL
        + '<!DOCTYPE html>\n'
        + '<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops">\n'
        + "<head>\n"
        + '  <meta charset="utf-8"/>\n'
        + f"  <title>{escape(title)} - {index}</title>\n"
        + f'  <meta name="viewport" content="width={w}, height={h}"/>\n'
        + f"  <style>html, body {{ margin: 0; padding: 0; width: {w}px; height: {h}px; }}"
        + f" img {{ display: block; width: {w}px; height: {h}px; }}</style>\n"
        + "</head>\n"
        + "<body>\n"
        + f'  <img src="../images/img-{index:04d}{page.extension}" alt=""/>\n'
        + "</body>\n"
        + "</html>\n"
    )


def _nav_xhtml(title: str, language: str) -> str:
    return (
        XML_DECL
        + '<!DOCTYPE html>\n'
        + f'<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops"'
        + f' lang={quoteattr(language)} xml:lang={quoteattr(language)}>\n'
        + f"<head>\n  <meta charset=\"utf-8\"/>\n  <title>{escape(title)}</title>\n</head>\n"
        + "<body>\n"
        + '  <nav epub:type="toc" id="toc">\n'
        + f'    <ol>\n      <li><a href="pages/page-0001.xhtml">{escape(title)}</a></li>\n    </ol>\n'
        + "  </nav>\n"
        + "</body>\n"
        + "</html>\n"
    )


def _package_opf(book: BookSpec, identifier: str, modified: str) -> str:
    manifest = ['    <item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/>']
    spine = []
    for i, page in enumerate(book.pages, start=1):
        props = ' properties="cover-image"' if i == 1 else ""
        manifest.append(
            f'    <item id="img-{i:04d}" href="images/img-{i:04d}{page.extension}"'
            f' media-type="{page.media_type}"{props}/>'
        )
        manifest.append(
            f'    <item id="page-{i:04d}" href="pages/page-{i:04d}.xhtml"'
            f' media-type="application/xhtml+xml"/>'
        )
        spine.append(f'    <itemref idref="page-{i:04d}"/>')
    return (
        XML_DECL
        + '<package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="book-id">\n'
        + '  <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">\n'
        + f'    <dc:identifier id="book-id">{identifier}</dc:identifier>\n'
        + f"    <dc:title>{escape(book.title)}</dc:title>\n"
        + f"    <dc:language>{escape(book.language)}</dc:language>\n"
        + f'    <meta property="dcterms:modified">{modified}</meta>\n'
        + '    <meta property="rendition:layout">pre-paginated</meta>\n'
        + "  </metadata>\n"
        + "  <manifest>\n" + "\n".join(manifest) + "\n  </manifest>\n"
        + "  <spine>\n" + "\n".join(spine) + "\n  </spine>\n"
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
        z.writestr("OEBPS/nav.xhtml", _nav_xhtml(book.title, book.language),
                   compress_type=zipfile.ZIP_DEFLATED)
        for i, page in enumerate(book.pages, start=1):
            z.writestr(f"OEBPS/pages/page-{i:04d}.xhtml", _page_xhtml(i, page, book.title),
                       compress_type=zipfile.ZIP_DEFLATED)
            z.writestr(f"OEBPS/images/img-{i:04d}{page.extension}", page.data,
                       compress_type=zipfile.ZIP_STORED)
