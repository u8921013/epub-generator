"""書籍掃描：判斷書的種類，並讀取輸入資料夾產出書的結構。

漫畫書是「書 → 章 → 頁」；文字書是「書 → 章」，每個 Markdown 檔是一章。
"""

import os
import re
from dataclasses import dataclass, field
from pathlib import Path

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
MARKDOWN_EXTENSIONS = {".md", ".markdown"}


@dataclass(frozen=True)
class Chapter:
    title: str  # 取自第一層子資料夾名稱
    pages: list[Path]


@dataclass(frozen=True)
class Book:
    front_pages: list[Path] = field(default_factory=list)  # 根目錄的圖片，不屬於任何章節
    chapters: list[Chapter] = field(default_factory=list)

    @property
    def pages(self) -> list[Path]:
        """整本書依閱讀順序排列的所有頁面。"""
        return self.front_pages + [p for c in self.chapters for p in c.pages]


def natural_key(name: str):
    """自然排序：`2.jpg` 排在 `10.jpg` 前，不分大小寫。"""
    return [int(t) if t.isdigit() else t.casefold() for t in re.split(r"(\d+)", name)]


def _path_key(path: Path, base: Path):
    return [natural_key(part) for part in path.relative_to(base).parts]


def _is_image(path: Path) -> bool:
    return path.suffix.lower() in IMAGE_EXTENSIONS


def _images_under(folder: Path) -> list[Path]:
    """資料夾內（含更深層）的所有圖片，依相對路徑自然排序。"""
    found = [
        Path(root) / name
        for root, _dirs, names in os.walk(folder)
        for name in names
        if _is_image(Path(name)) and (Path(root) / name).is_file()
    ]
    return sorted(found, key=lambda p: _path_key(p, folder))


def scan_book(folder: Path) -> Book:
    """掃描輸入資料夾。

    根目錄的圖片排在最前面；每個含圖片的第一層子資料夾成為一章，
    更深層的圖片併入所屬的第一層章節。
    """
    entries = list(folder.iterdir())
    front = sorted((p for p in entries if p.is_file() and _is_image(p)),
                   key=lambda p: natural_key(p.name))
    chapters = []
    for sub in sorted((p for p in entries if p.is_dir()), key=lambda p: natural_key(p.name)):
        pages = _images_under(sub)
        if pages:
            chapters.append(Chapter(title=sub.name, pages=pages))
    return Book(front_pages=front, chapters=chapters)


def _is_markdown(path: Path) -> bool:
    """非隱藏的 Markdown 檔；隱藏檔（例如 macOS 的 ._x.md）不算。"""
    return path.suffix.lower() in MARKDOWN_EXTENSIONS and not path.name.startswith(".")


def is_text_book(folder: Path) -> bool:
    """資料夾任何位置有 Markdown 檔就是文字書，否則是漫畫書（ADR 0001）。

    隱藏資料夾（例如 .git）裡的檔案不算。
    """
    for _root, dirs, names in os.walk(folder):
        dirs[:] = [d for d in dirs if not d.startswith(".")]
        if any(_is_markdown(Path(name)) for name in names):
            return True
    return False


def scan_text_book(folder: Path) -> list[Path]:
    """文字書的章（Markdown 檔），依檔名自然排序。"""
    return sorted((p for p in folder.iterdir() if p.is_file() and _is_markdown(p)),
                  key=lambda p: natural_key(p.name))
