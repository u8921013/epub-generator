"""Markdown 轉譯：把一個檔案的 Markdown 文字轉成章的 XHTML 片段與章名。

純函式，不碰檔案系統。md 裡的相對路徑（連結、插圖）交給呼叫端提供的目標解析器
換成書內的 href。
"""

from dataclasses import dataclass
from typing import Protocol

from markdown_it import MarkdownIt
from markdown_it.token import Token


class TargetResolver(Protocol):
    """把 md 裡的相對路徑換成書內 href；找不到時回傳 None。"""

    def link(self, target: str) -> str | None:
        """連結目標（Markdown 檔，可帶 #錨點）。"""

    def image(self, target: str) -> str | None:
        """插圖路徑。"""


@dataclass(frozen=True)
class RenderedChapter:
    title: str  # 第一個一級標題的純文字；沒有時為空字串，由呼叫端退回檔名
    body: str  # 章的 XHTML 內文片段（可能有多個最上層元素）


def _parser() -> MarkdownIt:
    # html=False：原始 HTML 一律轉義成文字；xhtmlOut：空元素以 <br /> 形式輸出。
    return MarkdownIt("commonmark", {"html": False, "xhtmlOut": True})


def render_markdown(text: str, resolver: TargetResolver | None = None) -> RenderedChapter:
    md = _parser()
    tokens = md.parse(text)
    return RenderedChapter(title=_first_h1_text(tokens), body=md.renderer.render(tokens, md.options, {}))


def _first_h1_text(tokens: list[Token]) -> str:
    for i, token in enumerate(tokens):
        # 只看最上層：引用或清單裡的 # 不算章名。
        if token.type == "heading_open" and token.tag == "h1" and token.level == 0:
            return _plain_text(tokens[i + 1]).strip()
    return ""


def _plain_text(inline: Token) -> str:
    """行內 token 的純文字：保留文字與程式碼，去掉強調、連結等格式。"""
    parts = []
    for child in inline.children or ():
        if child.type in ("text", "code_inline", "image"):
            parts.append(child.content)
        elif child.type in ("softbreak", "hardbreak"):
            parts.append(" ")
    return "".join(parts)
