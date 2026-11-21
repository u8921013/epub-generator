"""Markdown 轉譯（第二接縫）：給 Markdown 文字，斷言章名與 XHTML 片段。"""

import xml.etree.ElementTree as ET

from epubgen.markdown import render_markdown


class NoTargets:
    """假的目標解析器：什麼都找不到。"""

    def link(self, target):
        return None

    def image(self, target):
        return None


def parse(body: str) -> ET.Element:
    """片段可能有多個最上層元素，包進一個 div 後必須能被 XML 解析器解析。"""
    return ET.fromstring(f'<div xmlns="http://www.w3.org/1999/xhtml">{body}</div>')


def test_title_is_the_plain_text_of_the_first_h1():
    result = render_markdown("# 第8章 **梁溪** _a_ `b`\n\n段落。\n", NoTargets())
    assert result.title == "第8章 梁溪 a b"


def test_title_is_empty_without_an_h1():
    assert render_markdown("## 小標\n\n段落。\n", NoTargets()).title == ""


def test_setext_h1_counts_as_the_title():
    assert render_markdown("章名\n===\n\n段落。\n", NoTargets()).title == "章名"


def test_paragraphs_headings_and_inline_formatting_become_xhtml():
    result = render_markdown(
        "# 一\n\n第一段 **粗** *斜* `碼`，A & B < C。\n\n## 二\n\n第二段  \n硬換行。\n\n---\n", NoTargets())
    root = parse(result.body)
    ns = "{http://www.w3.org/1999/xhtml}"
    assert [h.text for h in root.iter(f"{ns}h1")] == ["一"]
    assert [h.text for h in root.iter(f"{ns}h2")] == ["二"]
    first = root.find(f"{ns}p")
    assert first.find(f"{ns}strong").text == "粗"
    assert first.find(f"{ns}em").text == "斜"
    assert first.find(f"{ns}code").text == "碼"
    assert "A & B < C。" in "".join(first.itertext())
    assert root.find(f".//{ns}br") is not None
    assert root.find(f"{ns}hr") is not None


def test_second_h1_stays_as_an_ordinary_heading():
    root = parse(render_markdown("# 甲\n\n文。\n\n# 乙\n", NoTargets()).body)
    assert [h.text for h in root.iter("{http://www.w3.org/1999/xhtml}h1")] == ["甲", "乙"]


def test_an_h1_nested_in_a_quote_or_list_is_not_the_title():
    assert render_markdown("> # 引用\n\n- # 清單\n\n# 章名\n", NoTargets()).title == "章名"


# --- front matter --------------------------------------------------------------

def test_front_matter_is_skipped_and_the_body_starts_after_it():
    result = render_markdown("---\ntitle: 不要\ntags: [a]\n---\n# 章名\n\n正文。\n", NoTargets())
    assert result.title == "章名"
    assert "不要" not in result.body and "tags" not in result.body
    assert not result.is_empty


def test_an_opening_dash_line_without_a_closing_one_is_not_front_matter():
    result = render_markdown("---\n# 章名\n\n正文。\n", NoTargets())
    assert result.title == "章名"
    assert parse(result.body).find("{http://www.w3.org/1999/xhtml}hr") is not None


def test_a_file_with_only_front_matter_or_nothing_is_empty():
    assert render_markdown("---\ntitle: x\n---\n", NoTargets()).is_empty
    assert render_markdown("---\n---\n\n  \n", NoTargets()).is_empty
    assert render_markdown("", NoTargets()).is_empty
    assert not render_markdown("文。\n", NoTargets()).is_empty


# --- 原始 HTML -------------------------------------------------------------------

def test_raw_html_blocks_and_inline_tags_are_escaped_into_visible_text():
    result = render_markdown('<div class="x">\n區塊\n</div>\n\n文字 <span>行內</span> <br>。\n', NoTargets())
    root = parse(result.body)
    ns = "{http://www.w3.org/1999/xhtml}"
    assert root.find(f".//{ns}div") is None and root.find(f".//{ns}span") is None
    inline_paragraph = root.findall(f"{ns}p")[-1]
    assert inline_paragraph.find(f"{ns}br") is None
    text = "".join(root.itertext())
    assert '<div class="x">' in text and "</div>" in text
    assert "<span>行內</span> <br>" in text


def test_raw_html_gives_one_warning_per_file_with_line_numbers():
    text = "---\nt: x\n---\n# 章\n\n<div>\n</div>\n\n文 <b>粗</b>\n第二行 <i>斜</i>\n"
    assert render_markdown(text, NoTargets()).warnings == ("原始 HTML 已轉義成純文字（第 6、9、10 行）",)


def test_plain_markdown_has_no_warnings():
    assert render_markdown("# 章\n\n文 A < B & C。\n", NoTargets()).warnings == ()


def test_an_escaped_html_block_keeps_its_line_breaks():
    root = parse(render_markdown("<div>\n<p>甲</p>\n</div>\n", NoTargets()).body)
    paragraph = root.find("{http://www.w3.org/1999/xhtml}p")
    assert len(paragraph.findall("{http://www.w3.org/1999/xhtml}br")) == 2
