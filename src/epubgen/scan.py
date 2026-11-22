"""書籍掃描：判斷書的種類，並讀取輸入資料夾產出書的結構。

漫畫書是「書 → 章 → 頁」；文字書是「書 → 部 → 章」，每個 Markdown 檔是一章。
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
    return path.suffix.lower() in MARKDOWN_EXTENSIONS and not _is_hidden(path.name)


def _is_hidden(name: str) -> bool:
    return name.startswith(".")


def _visible_dirs(dirs: list[str]) -> list[str]:
    return [d for d in dirs if not _is_hidden(d)]


def is_text_book(folder: Path) -> bool:
    """資料夾任何位置有 Markdown 檔就是文字書，否則是漫畫書（ADR 0001）。

    隱藏資料夾（例如 .git）裡的檔案與壞掉的符號連結不算；跟 scan_text_book 一樣，
    不走進指向資料夾的符號連結。
    """
    for root, dirs, names in os.walk(folder):
        dirs[:] = _visible_dirs(dirs)
        if any(_is_markdown(p) and p.is_file() for p in (Path(root) / n for n in names)):
            return True
    return False


@dataclass(frozen=True)
class Part:
    title: str  # 取自第一層子資料夾名稱
    chapters: list[Path]


@dataclass(frozen=True)
class TextBook:
    front_chapters: list[Path] = field(default_factory=list)  # 根目錄的章，不屬於任何部
    parts: list[Part] = field(default_factory=list)

    def chapters_in_reading_order(self) -> list[tuple[str | None, Path]]:
        """整本書依閱讀順序排列的章：(所屬部名，根目錄的章為 None；Markdown 檔)。"""
        return ([(None, p) for p in self.front_chapters]
                + [(part.title, p) for part in self.parts for p in part.chapters])


def _markdown_under(folder: Path) -> list[Path]:
    """資料夾內（含更深層、不含隱藏資料夾）的所有 Markdown 檔，依相對路徑自然排序。"""
    found = []
    for root, dirs, names in os.walk(folder):
        dirs[:] = _visible_dirs(dirs)
        found += [p for p in (Path(root) / n for n in names) if _is_markdown(p) and p.is_file()]
    return sorted(found, key=lambda p: _path_key(p, folder))


def scan_text_book(folder: Path) -> TextBook:
    """掃描文字書資料夾。

    根目錄的 md 是不屬於任何部的章，排在最前面；每個含 md 的第一層子資料夾
    成為一部，更深層的 md 併入所屬的第一層部。部與章都依名稱自然排序。
    指向資料夾的符號連結不算部，跟更深層的 os.walk 與 is_text_book 一致。
    """
    entries = list(folder.iterdir())
    front = sorted((p for p in entries if p.is_file() and _is_markdown(p)),
                   key=lambda p: natural_key(p.name))
    parts = []
    subfolders = (p for p in entries if p.is_dir() and not p.is_symlink() and not _is_hidden(p.name))
    for sub in sorted(subfolders, key=lambda p: natural_key(p.name)):
        chapters = _markdown_under(sub)
        if chapters:
            parts.append(Part(title=sub.name, chapters=chapters))
    return TextBook(front_chapters=front, parts=parts)
