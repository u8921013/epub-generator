"""Markdown 轉譯：把一個檔案的 Markdown 文字轉成章的 XHTML 片段與章名。

純函式，不碰檔案系統。md 裡的相對路徑（連結、插圖）交給呼叫端提供的目標解析器
換成書內的 href。
"""

import re
from dataclasses import dataclass
from typing import Protocol

from markdown_it import MarkdownIt
from markdown_it.common.utils import escapeHtml
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
    is_empty: bool = False  # 略過 front matter 後沒有任何內容
    warnings: tuple[str, ...] = ()  # 給作者看的原因，不含檔名（由呼叫端加上）


# 開頭 `---` 單獨一行、到下一個單獨一行的 `---` 為止；沒有結束行就不算 front matter。
_FRONT_MATTER = re.compile(r"\A---[ \t]*\r?\n(?:.*?\r?\n)?---[ \t]*(?:\r?\n|\Z)", re.DOTALL)


def _parser() -> MarkdownIt:
    # html=True 只是為了認出原始 HTML 好發出警告；輸出時由下面的規則轉義成文字。
    # xhtmlOut：空元素以 <br /> 形式輸出。
    md = MarkdownIt("commonmark", {"html": True, "xhtmlOut": True})
    md.add_render_rule("html_block", _escaped_html_block)
    md.add_render_rule("html_inline", _escaped_html_inline)
    return md


def _escaped_html_block(self, tokens: list[Token], idx: int, options, env) -> str:
    # 保留原本的換行，閱讀器才不會把整段 HTML 併成一行。
    lines = tokens[idx].content.strip().split("\n")
    return "<p>" + "<br />\n".join(escapeHtml(line) for line in lines) + "</p>\n"


def _escaped_html_inline(self, tokens: list[Token], idx: int, options, env) -> str:
    return escapeHtml(tokens[idx].content)


def render_markdown(text: str, resolver: TargetResolver | None = None) -> RenderedChapter:
    md = _parser()
    front_matter = _FRONT_MATTER.match(text)
    skipped_lines = front_matter.group().count("\n") if front_matter else 0
    tokens = md.parse(text[front_matter.end():] if front_matter else text)
    warnings = []
    html_lines = [line + skipped_lines for line in _raw_html_lines(tokens)]
    if html_lines:
        lines = "、".join(str(n) for n in sorted(set(html_lines)))
        warnings.append(f"原始 HTML 已轉義成純文字（第 {lines} 行）")
    return RenderedChapter(title=_first_h1_text(tokens), body=md.renderer.render(tokens, md.options, {}),
                           is_empty=not tokens, warnings=tuple(warnings))


def _raw_html_lines(tokens: list[Token]) -> list[int]:
    """原始 HTML 出現的行號（從 1 起算，相對於傳給解析器的文字）。"""
    lines = []
    for token in tokens:
        if token.type == "html_block" and token.map:
            lines.append(token.map[0] + 1)
        elif token.type == "inline" and token.map:
            line = token.map[0] + 1
            for child in token.children or ():
                if child.type in ("softbreak", "hardbreak"):
                    line += 1
                elif child.type == "html_inline":
                    lines.append(line)
    return lines


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
