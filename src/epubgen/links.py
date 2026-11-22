"""書內連結：把 md 之間的相對連結換成章 XHTML 的 href。

建書時先知道每一章的來源、檔名與錨點，再為每一章提供一個目標解析器（見 markdown.TargetResolver）。
"""

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class LinkedChapter:
    file_name: str  # 章 XHTML 的檔名；所有章在同一個資料夾，彼此以檔名互連
    anchors: frozenset[str]


class BookLinks:
    def __init__(self, chapters: dict[Path, LinkedChapter]):
        # 鍵是來源 md 的絕對路徑；空章不在裡面，連到空章算失效連結。
        self._chapters = chapters

    def for_chapter(self, source: Path) -> "ChapterLinks":
        return ChapterLinks(self._chapters, source.resolve())


class ChapterLinks:
    """一章的目標解析器：相對路徑以這個 md 所在的資料夾為基準。"""

    def __init__(self, chapters: dict[Path, LinkedChapter], source: Path):
        self._chapters = chapters
        self._source = source

    def link(self, target: str) -> str | None:
        path, _, fragment = target.partition("#")
        if not path:  # 只有 #錨點：同章內跳轉
            anchor = _find_anchor(self._chapters[self._source], fragment)
            return None if anchor is None else f"#{anchor}"
        chapter = self._chapters.get((self._source.parent / path).resolve())
        if chapter is None:  # 不存在、不是 Markdown、或是空章
            return None
        if not fragment:
            return chapter.file_name
        anchor = _find_anchor(chapter, fragment)
        return None if anchor is None else f"{chapter.file_name}#{anchor}"

    def image(self, target: str) -> str | None:
        return None  # 插圖在票 08 處理


def _find_anchor(chapter: LinkedChapter, fragment: str) -> str | None:
    """錨點都是小寫；跟 GitHub 一樣，大小寫不符時改用小寫再找一次。"""
    for candidate in (fragment, fragment.lower()):
        if candidate in chapter.anchors:
            return candidate
    return None
