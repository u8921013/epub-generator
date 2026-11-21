"""Markdown 轉譯：把一個檔案的 Markdown 文字轉成章的 XHTML 片段與章名。

純函式，不碰檔案系統。md 裡的相對路徑（連結、插圖）交給呼叫端提供的目標解析器
換成書內的 href。
"""

import re
from collections.abc import Iterable
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


# 軟換行兩側都是這些字元時直接相連，不輸出空白。依照 CSS Text Level 3 的分段換行規則：
# 東亞寬字（中日文字、全形與半形中日標點）相連，但韓文不算，因為韓文以空白分詞。
_CJK_RANGES = (
    (0x2E80, 0x2FDF),    # 中日韓部首補充、康熙部首
    (0x2FF0, 0x2FFF),    # 表意文字描述字元
    (0x3000, 0x303F),    # 中日韓符號與標點（、。「」『』【】）
    (0x3040, 0x30FF),    # 平假名、片假名
    (0x3100, 0x312F),    # 注音符號
    (0x3190, 0x31FF),    # 漢文訓讀、注音擴充、筆畫、片假名音標擴充
    (0x3200, 0x33FF),    # 中日韓帶圈字母與月份、中日韓相容字元
    (0x3400, 0x4DBF),    # 中日韓統一表意文字擴充 A
    (0x4E00, 0x9FFF),    # 中日韓統一表意文字
    (0xF900, 0xFAFF),    # 中日韓相容表意文字
    (0xFE10, 0xFE1F),    # 直排形式
    (0xFE30, 0xFE4F),    # 中日韓相容形式
    (0xFE50, 0xFE6F),    # 小寫變體（﹐﹑﹒）
    (0xFF01, 0xFF60),    # 全形 ASCII 與全形括號（，！？）
    (0xFF61, 0xFF9F),    # 半形中日標點與半形片假名
    (0xFFE0, 0xFFE6),    # 全形符號（￥￡）
    (0x1B000, 0x1B16F),  # 假名補充、假名擴充 A、小假名擴充
    (0x1F200, 0x1F2FF),  # 帶圈表意文字補充
    (0x20000, 0x3FFFD),  # 第二、第三平面：表意文字擴充 B 以後與相容補充
)

# 中文常用、但西文也用的標點（引號、刪節號、破折號、間隔號）。它們本身不決定相連與否，
# 而是看同一段文字裡越過它們之後的第一個字元：「他說“好。”\n“走吧”」相連，`“hi”\n“there”` 不相連。
_SHARED_PUNCTUATION = frozenset("\u00b7\u2014\u2015\u2018\u2019\u201c\u201d\u2025\u2026\u2027")


def _is_cjk(char: str) -> bool:
    code = ord(char)
    return any(low <= code <= high for low, high in _CJK_RANGES)


def _is_cjk_side(run: str) -> bool:
    """軟換行一側的文字（從換行往外讀）是否算中日韓：越過共用標點，看第一個其他字元。"""
    for char in run:
        if char not in _SHARED_PUNCTUATION:
            return _is_cjk(char)
    return False


def _parser() -> MarkdownIt:
    # html=True 只是為了認出原始 HTML 好發出警告；輸出時由下面的規則轉義成文字。
    # xhtmlOut：空元素以 <br /> 形式輸出。
    md = MarkdownIt("commonmark", {"html": True, "xhtmlOut": True}).enable(["table", "strikethrough"])
    md.add_render_rule("html_block", _escaped_html_block)
    md.add_render_rule("html_inline", _escaped_html_inline)
    md.add_render_rule("softbreak", _softbreak)
    return md


def _softbreak(self, tokens: list[Token], idx: int, options, env) -> str:
    return "" if _is_joined(tokens[idx]) else "\n"


def _is_joined(softbreak: Token) -> bool:
    return softbreak.meta.get("join", False)


def _mark_cjk_soft_breaks(tokens: list[Token]) -> None:
    """兩側都是中日韓字元的軟換行標記為相連；左右的字元會跳過粗體、連結等格式標記去找。"""
    for token in tokens:
        children = token.children or []
        for i, child in enumerate(children):
            if child.type != "softbreak":
                continue
            before = _neighbor_text(reversed(children[:i]), outward_is_backward=True)
            after = _neighbor_text(children[i + 1:], outward_is_backward=False)
            if _is_cjk_side(before) and _is_cjk_side(after):
                child.meta["join"] = True


def _neighbor_text(siblings: Iterable[Token], outward_is_backward: bool) -> str:
    """軟換行一側緊鄰的那段文字，依離換行由近到遠的順序排列。

    跳過粗體、連結等格式標記；碰到圖片、行內 HTML 等非文字內容就停下（回傳空字串）。
    """
    for sibling in siblings:
        if sibling.nesting != 0:  # 粗體、斜體、連結等的開頭與結尾
            continue
        if sibling.type not in ("text", "code_inline"):
            return ""
        if sibling.content:
            return sibling.content[::-1] if outward_is_backward else sibling.content
    return ""


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
    _mark_cjk_soft_breaks(tokens)
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
        elif child.type == "softbreak" and _is_joined(child):
            continue
        elif child.type in ("softbreak", "hardbreak"):
            parts.append(" ")
    return "".join(parts)
