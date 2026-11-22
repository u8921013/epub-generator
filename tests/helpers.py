"""測試用的小工具：即時產生圖片，並把輸出的 EPUB 當 zip 解開觀察。"""

import io
import re
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

from PIL import Image

NS = {
    "c": "urn:oasis:names:tc:opendocument:xmlns:container",
    "opf": "http://www.idpf.org/2007/opf",
    "dc": "http://purl.org/dc/elements/1.1/",
    "x": "http://www.w3.org/1999/xhtml",
}


def make_image(path: Path, size=(80, 120), fmt=None, color=(200, 30, 30)) -> bytes:
    """在 path 產生一張圖片並回傳它的位元組。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    fmt = fmt or {".jpg": "JPEG", ".jpeg": "JPEG", ".png": "PNG",
                  ".webp": "WEBP", ".gif": "GIF"}[path.suffix.lower()]
    img = Image.new("RGB", size, color)
    buf = io.BytesIO()
    img.save(buf, fmt)
    path.write_bytes(buf.getvalue())
    return buf.getvalue()


class Epub:
    """把 EPUB 解開後，提供測試斷言用的觀察方法。"""

    def __init__(self, path: Path):
        self.path = path
        self.zip = zipfile.ZipFile(path)
        container = ET.fromstring(self.zip.read("META-INF/container.xml"))
        rootfile = container.find(".//c:rootfile", NS)
        self.opf_path = rootfile.get("full-path")
        self.opf_dir = self.opf_path.rpartition("/")[0]
        self.opf = ET.fromstring(self.zip.read(self.opf_path))

    def resolve(self, href: str, base_dir: str = None) -> str:
        base = self.opf_dir if base_dir is None else base_dir
        parts = [p for p in (base + "/" + href).split("/") if p]
        out = []
        for p in parts:
            if p == "..":
                out.pop()
            elif p != ".":
                out.append(p)
        return "/".join(out)

    def manifest(self) -> dict:
        return {i.get("id"): i for i in self.opf.findall(".//opf:manifest/opf:item", NS)}

    def spine_items(self) -> list:
        manifest = self.manifest()
        return [manifest[r.get("idref")] for r in self.opf.findall(".//opf:spine/opf:itemref", NS)]

    def page_paths(self) -> list:
        return [self.resolve(i.get("href")) for i in self.spine_items()]

    def page_text(self, page_path: str) -> str:
        return self.zip.read(page_path).decode("utf-8")

    def page_image_path(self, page_path: str) -> str:
        src = re.search(r'<img[^>]*\ssrc="([^"]+)"', self.page_text(page_path)).group(1)
        return self.resolve(src, page_path.rpartition("/")[0])

    def page_images(self) -> list:
        """依 spine 順序回傳每頁圖片的位元組。"""
        return [self.zip.read(self.page_image_path(p)) for p in self.page_paths()]

    def viewport(self, page_path: str):
        m = re.search(r'name="viewport"\s+content="width=(\d+),\s*height=(\d+)"',
                      self.page_text(page_path))
        return int(m.group(1)), int(m.group(2))

    def viewport_or_none(self, page_path: str):
        """有 viewport 時回傳 (寬, 高)，沒有時回傳 None（文字書）。"""
        return self.viewport(page_path) if 'name="viewport"' in self.page_text(page_path) else None

    def chapter_root(self, chapter_path: str) -> ET.Element:
        """把章的 XHTML 解析成 XML（解析失敗即代表不是格式正確的 XHTML）。"""
        return ET.fromstring(self.zip.read(chapter_path))

    def stylesheet_paths(self) -> list:
        """manifest 裡所有 CSS 的 zip 內路徑。"""
        return [self.resolve(i.get("href")) for i in self.manifest().values() if i.get("media-type") == "text/css"]

    def stylesheets(self, chapter_path: str) -> list:
        """章 <head> 引用的樣式表，換成 zip 內的路徑。"""
        head = self.chapter_root(chapter_path).find("x:head", NS)
        base = chapter_path.rpartition("/")[0]
        return [self.resolve(link.get("href"), base) for link in head.findall("x:link", NS)
                if link.get("rel") == "stylesheet"]

    def chapter_body_text(self, chapter_path: str) -> str:
        """章 <body> 的純文字。"""
        body = self.chapter_root(chapter_path).find("x:body", NS)
        return "".join(body.itertext())

    def links(self, chapter_path: str) -> list:
        """章內所有連結的（文字, 目標）。書內連結的目標換成 zip 內路徑（可帶 #錨點），外部連結原樣。"""
        base = chapter_path.rpartition("/")[0]
        out = []
        for a in self.chapter_root(chapter_path).iter("{%s}a" % NS["x"]):
            href = a.get("href")
            if ":" not in href.split("#")[0]:
                path, _, fragment = href.partition("#")
                href = (self.resolve(path, base) if path else chapter_path) + (f"#{fragment}" if fragment else "")
            out.append(("".join(a.itertext()), href))
        return out

    def ids(self, chapter_path: str) -> list:
        """章內所有元素的 id，依出現順序。"""
        return [e.get("id") for e in self.chapter_root(chapter_path).iter() if e.get("id")]

    def chapter_headings(self, chapter_path: str, tag: str) -> list:
        """章內某一級標題（例如 "h1"）的純文字，依出現順序。"""
        return ["".join(h.itertext()) for h in self.chapter_root(chapter_path).iter("{%s}%s" % (NS["x"], tag))]

    def meta_property(self, prop: str):
        for m in self.opf.findall(".//opf:metadata/opf:meta", NS):
            if m.get("property") == prop:
                return m.text
        return None

    def dc(self, name: str):
        el = self.opf.find(f".//opf:metadata/dc:{name}", NS)
        return None if el is None else el.text

    def cover_items(self) -> list:
        return [i for i in self.manifest().values()
                if "cover-image" in (i.get("properties") or "").split()]

    def _nav(self):
        nav_item = next(i for i in self.manifest().values()
                        if "nav" in (i.get("properties") or "").split())
        nav_path = self.resolve(nav_item.get("href"))
        return ET.fromstring(self.zip.read(nav_path)), nav_path.rpartition("/")[0]

    def toc(self) -> list:
        """回傳目錄項目 [(文字, 層級, 解析後路徑)]，層級從 1 起算，依出現順序。"""
        root, base = self._nav()
        toc_ol = root.find(".//x:nav/x:ol", NS)
        entries = []

        def walk(ol, level):
            for li in ol.findall("x:li", NS):
                a = li.find("x:a", NS)
                entries.append(("".join(a.itertext()), level,
                                self.resolve(a.get("href").split("#")[0], base)))
                child = li.find("x:ol", NS)
                if child is not None:
                    walk(child, level + 1)

        walk(toc_ol, 1)
        return entries

    def nav_links(self) -> list:
        """回傳 navigation document 的 toc 連結 [(文字, 解析後路徑)]。"""
        root, base = self._nav()
        links = []
        for a in root.iter("{%s}a" % NS["x"]):
            href = a.get("href").split("#")[0]
            links.append(("".join(a.itertext()), self.resolve(href, base)))
        return links


def spine_direction(book: "Epub"):
    return book.opf.find(".//opf:spine", NS).get("page-progression-direction")


def spine_spread_properties(book: "Epub") -> list:
    """回傳每個 spine itemref 的 properties（以空白切開的 list）。"""
    return [(r.get("properties") or "").split()
            for r in book.opf.findall(".//opf:spine/opf:itemref", NS)]
