"""目標解析：把 md 裡的相對路徑（書內連結、插圖）換成書內的 href。

建書時先知道每一章的來源、檔名與錨點，再為每一章提供一個目標解析器（見 markdown.TargetResolver）。
"""

from dataclasses import dataclass
from pathlib import Path

from .illustrations import Illustrations


@dataclass(frozen=True)
class LinkedChapter:
    file_name: str  # 章 XHTML 的檔名；所有章在同一個資料夾，彼此以檔名互連
    anchors: frozenset[str]


class BookTargets:
    def __init__(self, chapters: dict[Path, LinkedChapter], illustrations: Illustrations):
        # 鍵是來源 md 的絕對路徑；空章不在裡面，連到空章算失效連結。
        self._chapters = chapters
        self._illustrations = illustrations

    def for_chapter(self, source: Path, name: str) -> "ChapterTargets":
        """name 是這個 md 相對於輸入資料夾的路徑，用在跳過清單與錯誤訊息。"""
        return ChapterTargets(self._chapters, self._illustrations, source.resolve(), name)


class ChapterTargets:
    """一章的目標解析器：相對路徑以這個 md 所在的資料夾為基準。"""

    def __init__(self, chapters: dict[Path, LinkedChapter], illustrations: Illustrations, source: Path, name: str):
        self._chapters = chapters
        self._illustrations = illustrations
        self._source = source
        self._name = name

    def link(self, path: str, fragment: str) -> str | None:
        if not path:  # 只有 #錨點：同章內跳轉
            anchor = _find_anchor(self._chapters[self._source], fragment)
            return None if anchor is None else f"#{anchor}"
        chapter = self._chapters.get(_resolved(self._source.parent / path))
        if chapter is None:  # 不存在、不是 Markdown、是空章、或根本不是合法路徑
            return None
        if not fragment:
            return chapter.file_name
        anchor = _find_anchor(chapter, fragment)
        return None if anchor is None else f"{chapter.file_name}#{anchor}"

    def image(self, target: str) -> str | None:
        return self._illustrations.href(self._source.parent / target, f"{self._name}：{target}")


def _resolved(path: Path) -> Path | None:
    """絕對路徑；路徑不合法（例如 %00 解碼出的 NUL 字元）時回傳 None。"""
    try:
        return path.resolve()
    except (OSError, ValueError):
        return None


def _find_anchor(chapter: LinkedChapter, fragment: str) -> str | None:
    """錨點都是小寫；跟 GitHub 一樣，大小寫不符時改用小寫再找一次。"""
    for candidate in (fragment, fragment.lower()):
        if candidate in chapter.anchors:
            return candidate
    return None
