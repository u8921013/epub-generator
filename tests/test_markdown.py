"""Markdown 轉譯（第二接縫）：給 Markdown 文字，斷言章名與 XHTML 片段。"""

import xml.etree.ElementTree as ET

import pytest

from epubgen.markdown import render_markdown


class NoTargets:
    """假的目標解析器：什麼都找不到。"""

    def link(self, path, fragment):
        return None

    def image(self, target):
        return None


def parse(body: str) -> ET.Element:
    """片段可能有多個最上層元素，包進一個 div 後必須能被 XML 解析器解析。"""
    return ET.fromstring(f'<div xmlns="http://www.w3.org/1999/xhtml">{body}</div>')


def test_title_is_the_plain_text_of_the_first_h1():
    result = render_markdown("# 第8章 **梁溪** _a_ `b`\n\n段落。\n", NoTargets())
    assert result.title == "第8章 梁溪 a b"


def test_title_drops_the_formatting_inside_image_alt_text():
    assert render_markdown("# 章 ![**粗**圖](a.png)\n", NoTargets()).title == "章 粗圖"


def test_title_shows_raw_html_as_the_text_the_body_shows():
    result = render_markdown("# 章 <span>內</span>\n", NoTargets())
    assert result.title == "章 <span>內</span>"
    assert "".join(parse(result.body).itertext()).strip() == result.title


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


def test_raw_html_inside_image_alt_text_is_warned_about_too():
    result = render_markdown("# 章\n\n![圖 <b>x</b>](a.png)\n", NoTargets())
    assert result.warnings == ("原始 HTML 已轉義成純文字（第 3 行）",)


def test_plain_markdown_has_no_warnings():
    assert render_markdown("# 章\n\n文 A < B & C。\n", NoTargets()).warnings == ()


def test_an_escaped_html_block_keeps_its_line_breaks():
    root = parse(render_markdown("<div>\n<p>甲</p>\n</div>\n", NoTargets()).body)
    paragraph = root.find("{http://www.w3.org/1999/xhtml}p")
    assert len(paragraph.findall("{http://www.w3.org/1999/xhtml}br")) == 2


# --- 軟換行 ----------------------------------------------------------------------

def paragraph_text(markdown: str) -> str:
    root = parse(render_markdown(markdown, NoTargets()).body)
    return "".join(root.find("{http://www.w3.org/1999/xhtml}p").itertext())


def test_a_soft_break_between_chinese_characters_joins_them():
    assert paragraph_text("今天天氣很好，\n我們去散步。\n") == "今天天氣很好，我們去散步。"


def test_a_soft_break_between_english_words_becomes_whitespace():
    assert paragraph_text("hello\nworld\n").split() == ["hello", "world"]


@pytest.mark.parametrize("before, after", [
    ("中", "A"),   # 中英交界：一邊不是中日韓 → 照標準
    ("A", "中"),
    ("中", "1"),
    ("，", "a"),
    ("中", "한"),  # 韓文以空白分詞，不相連
    ("한", "국"),
    ("中", "😀"),
])
def test_a_soft_break_keeps_whitespace_unless_both_sides_are_cjk(before, after):
    text = paragraph_text(f"{before}\n{after}\n")
    assert text != before + after and text.split() == [before, after]


@pytest.mark.parametrize("before, after", [
    ("一", "鿿"),          # 中日韓統一表意文字
    ("㐀", "䶿"),          # 擴充 A
    ("\U00020000", "\U0003134a"),  # 擴充 B 以後（第二、第三平面）
    ("豈", "﫿"),          # 相容表意文字
    ("、", "〿"),          # 中日韓符號與標點（、。「」）
    ("ぁ", "ヿ"),          # 平假名、片假名
    ("ㄅ", "ㆿ"),          # 注音符號
    ("！", "｠"),          # 全形 ASCII 與全形括號（，！？）
    ("｡", "ﾟ"),          # 半形中日標點與半形片假名
    ("︰", "﹏"),          # 相容形式（直排標點）
])
def test_unicode_ranges_that_count_as_cjk_are_joined_at_their_edges(before, after):
    assert paragraph_text(f"{before}\n{after}\n") == before + after


def test_the_cjk_rule_looks_through_inline_formatting():
    assert paragraph_text("很**好**\n`我們`去\n") == "很好我們去"


def test_a_multi_line_setext_title_joins_cjk_lines():
    assert render_markdown("第一\n章\n===\n", NoTargets()).title == "第一章"


def test_hard_breaks_are_unaffected():
    root = parse(render_markdown("中文  \n中文\n", NoTargets()).body)
    assert root.find(".//{http://www.w3.org/1999/xhtml}br") is not None


# --- 區塊與 GFM -------------------------------------------------------------------

X = "{http://www.w3.org/1999/xhtml}"


def test_tables_become_xhtml_tables():
    root = parse(render_markdown("| 名稱 | 數量 |\n|:--|--:|\n| 蘋果 | 3 |\n| 香蕉 | 10 |\n", NoTargets()).body)
    table = root.find(f"{X}table")
    assert ["".join(th.itertext()) for th in table.iter(f"{X}th")] == ["名稱", "數量"]
    assert [["".join(td.itertext()) for td in tr.iter(f"{X}td")] for tr in table.find(f"{X}tbody")] == [
        ["蘋果", "3"], ["香蕉", "10"]]


def test_strikethrough_is_rendered():
    root = parse(render_markdown("這是 ~~刪掉~~ 的字。\n", NoTargets()).body)
    assert root.find(f".//{X}s").text == "刪掉"


def test_code_blocks_keep_indentation_and_line_breaks_without_joining_cjk():
    code = "def 函式():\n    中文\n    文字 < 1 & 2\n"
    for markdown in (f"```python\n{code}```\n", "".join(f"    {line}\n" for line in code.splitlines())):
        root = parse(render_markdown(markdown, NoTargets()).body)
        pre = root.find(f"{X}pre")
        assert "".join(pre.find(f"{X}code").itertext()) == code


def test_quotes_lists_and_horizontal_rules_follow_commonmark():
    root = parse(render_markdown("> 引用\n\n- 甲\n- 乙\n\n1. 一\n2. 二\n\n***\n", NoTargets()).body)
    assert "".join(root.find(f"{X}blockquote").itertext()).strip() == "引用"
    assert ["".join(li.itertext()) for li in root.find(f"{X}ul")] == ["甲", "乙"]
    assert ["".join(li.itertext()) for li in root.find(f"{X}ol")] == ["一", "二"]
    assert root.find(f"{X}hr") is not None


@pytest.mark.parametrize("markdown, expected", [
    ("中文\n“引號”\n", "中文“引號”"),
    ("他說“好。”\n“走吧。”\n", "他說“好。”“走吧。”"),
    ("等等……\n他說\n", "等等……他說"),
    ("前\n——後\n", "前——後"),
    ("約翰·\n史密斯\n", "約翰·史密斯"),
    ("小\n﹐字\n", "小﹐字"),           # 小寫變體
    ("か\n\U0001b001\n", "か\U0001b001"),     # 假名補充
    ("中&#x6587;\n字\n", "中文字"),              # 字元參照仍是文字
    ("中文\n“**引號**”\n", "中文“引號”"),           # 共用標點與中文字分屬不同 token
    ("他說“**好。**”\n“走吧”\n", "他說“好。”“走吧”"),
])
def test_punctuation_shared_with_western_text_joins_when_it_sits_in_cjk_text(markdown, expected):
    assert paragraph_text(markdown) == expected


@pytest.mark.parametrize("markdown", [
    "He said “hi”\n“there”\n",
    "wait…\n…then\n",
    "“”\n“”\n",
    "He said “**hi**”\n“there”\n",
])
def test_punctuation_shared_with_western_text_keeps_whitespace_in_western_text(markdown):
    assert "\n" in paragraph_text(markdown)


def test_an_image_or_raw_html_next_to_a_soft_break_keeps_the_whitespace():
    assert "\n" in paragraph_text("中文![圖](a.png)\n中文\n")
    assert paragraph_text("中文<b>\n中文\n") == "中文<b>\n中文"


# --- 標題錨點 --------------------------------------------------------------------

def heading_ids(markdown: str) -> list:
    root = parse(render_markdown(markdown, NoTargets()).body)
    return [h.get("id") for h in root.iter() if h.tag[len(X):] in ("h1", "h2", "h3", "h4", "h5", "h6")]


@pytest.mark.parametrize("heading, anchor", [
    ("Hello World", "hello-world"),
    ("第一章 開端", "第一章-開端"),
    ("What's new? (v2.0)", "whats-new-v20"),
    ("A -- B", "a----b"),
    ("全形，標點！「引號」", "全形標點引號"),
    ("\U0001f604 emoji", "-emoji"),
    ("snake_case 與 kebab-case", "snake_case-與-kebab-case"),
    ("**粗體** `Code` [連結](x.md)", "粗體-code-連結"),
    ("Ünïcode ÄÖ", "ünïcode-äö"),
    ("中文　全形空白", "中文全形空白"),
])
def test_heading_anchors_follow_github(heading, anchor):
    result = render_markdown(f"## {heading}\n", NoTargets())
    assert result.anchors == (anchor,)
    assert heading_ids(f"## {heading}\n") == [anchor]


def test_repeated_heading_anchors_get_numbered_like_github():
    markdown = "# A\n\n## A\n\n## A-1\n\n### A\n"
    assert render_markdown(markdown, NoTargets()).anchors == ("a", "a-1", "a-1-1", "a-2")
    assert heading_ids(markdown) == ["a", "a-1", "a-1-1", "a-2"]


def test_a_heading_with_nothing_left_for_an_anchor_gets_no_id():
    assert render_markdown("## !!!\n", NoTargets()).anchors == ()
    assert heading_ids("## !!!\n") == [None]


# --- 連結 ------------------------------------------------------------------------

class Targets:
    """假的目標解析器：只認得給定的（路徑, 錨點），並記下被問過哪些目標。"""

    def __init__(self, links):
        self.links = links
        self.asked = []

    def link(self, path, fragment):
        self.asked.append((path, fragment))
        return self.links.get((path, fragment))

    def image(self, target):
        return None


def links(body: str) -> list:
    return [("".join(a.itertext()), a.get("href")) for a in parse(body).iter(f"{X}a")]


def test_local_links_are_replaced_by_what_the_resolver_returns():
    targets = Targets({("02.md", ""): "chapter-0002.xhtml", ("02.md", "某標題"): "chapter-0002.xhtml#某標題",
                       ("", "本章"): "#本章", ("../第一部/01.md", ""): "chapter-0001.xhtml"})
    result = render_markdown(
        "[見第二章](02.md)、[標題](02.md#某標題)、[本章](#本章)、[跨部](../第一部/01.md)\n", targets)
    assert links(result.body) == [("見第二章", "chapter-0002.xhtml"), ("標題", "chapter-0002.xhtml#某標題"),
                                  ("本章", "#本章"), ("跨部", "chapter-0001.xhtml")]
    assert targets.asked == [("02.md", ""), ("02.md", "某標題"), ("", "本章"), ("../第一部/01.md", "")]
    assert result.warnings == ()


def test_targets_are_given_to_the_resolver_decoded():
    targets = Targets({("第 2 章.md", "a b"): "chapter-0002.xhtml#a"})
    result = render_markdown("[x](<第 2 章.md#a b>) [y](%E7%AC%AC%202%20%E7%AB%A0.md#a%20b)\n", targets)
    assert [href for _, href in links(result.body)] == ["chapter-0002.xhtml#a", "chapter-0002.xhtml#a"]


def test_an_encoded_hash_belongs_to_the_file_name_not_the_anchor():
    targets = Targets({("C#.md", ""): "chapter-0002.xhtml", ("C#.md", "a#b"): "chapter-0002.xhtml#ab"})
    result = render_markdown("[C#](C%23.md) [錨](C%23.md#a%23b) [錯](C#.md)\n", targets)
    assert targets.asked == [("C#.md", ""), ("C#.md", "a#b"), ("C", ".md")]
    assert [href for _, href in links(result.body)] == ["chapter-0002.xhtml", "chapter-0002.xhtml#ab"]
    assert result.warnings == ("失效的連結已改成純文字：C#.md（第 1 行）",)


def test_unresolved_links_become_their_text_with_a_warning_each():
    result = render_markdown("# 章\n\n前 [**失效**](nope.md#x) 後\n[檔案](a.pdf)\n", NoTargets())
    root = parse(result.body)
    assert root.find(f".//{X}a") is None
    assert "".join(root.find(f"{X}p").itertext()) == "前 失效 後檔案"
    assert root.find(f".//{X}strong").text == "失效"
    assert result.warnings == ("失效的連結已改成純文字：nope.md#x（第 3 行）",
                               "失效的連結已改成純文字：a.pdf（第 4 行）")


class Refuses:
    def link(self, path, fragment):
        raise AssertionError(f"外部連結不該交給解析器：{path}#{fragment}")

    def image(self, target):
        return None


def test_links_with_a_scheme_are_kept_as_written():
    result = render_markdown(
        "[網站](https://example.com/a?b=1#c) <https://example.org> <me@example.com> [信](mailto:x@y.z)\n",
        Refuses())
    assert [href for _, href in links(result.body)] == [
        "https://example.com/a?b=1#c", "https://example.org", "mailto:me@example.com", "mailto:x@y.z"]
    assert result.warnings == ()


def test_without_a_resolver_links_are_left_as_written():
    assert links(render_markdown("[a](x.md#y)\n").body) == [("a", "x.md#y")]


# --- 插圖 ------------------------------------------------------------------------

class Images:
    """假的目標解析器：只認得給定的插圖，並記下被問過哪些目標。"""

    def __init__(self, images):
        self.images = images
        self.asked = []

    def link(self, path, fragment):
        return None

    def image(self, target):
        self.asked.append(target)
        return self.images.get(target)


def images(body: str) -> list:
    return [(img.get("src"), img.get("alt")) for img in parse(body).iter(f"{X}img")]


def test_local_illustrations_are_replaced_by_what_the_resolver_returns():
    resolver = Images({"images/a.png": "../images/img-0001.png", "../共用/b 圖.JPG": "../images/img-0002.jpg"})
    result = render_markdown("前 ![甲圖](images/a.png) 後\n\n![乙](<../共用/b 圖.JPG>)\n", resolver)
    assert images(result.body) == [("../images/img-0001.png", "甲圖"), ("../images/img-0002.jpg", "乙")]
    assert resolver.asked == ["images/a.png", "../共用/b 圖.JPG"]
    assert result.warnings == ()


def test_an_illustration_the_resolver_skips_shows_its_alt_text_without_a_warning():
    result = render_markdown("前 ![替代 *文字*](gone.png) 後\n", Images({}))
    root = parse(result.body)
    assert root.find(f".//{X}img") is None
    assert paragraph_text("前 ![替代 *文字*](gone.png) 後\n") == "前 替代 文字 後"
    assert result.warnings == ()


@pytest.mark.parametrize("markdown, warning", [
    ("![網圖](https://example.com/a.png)", "網路圖片不會下載，改顯示替代文字：https://example.com/a.png（第 3 行）"),
    ("![向量](a.svg)", "不支援的插圖格式，改顯示替代文字：a.svg（第 3 行）"),
    ("![點陣](scan.TIFF)", "不支援的插圖格式，改顯示替代文字：scan.TIFF（第 3 行）"),
    ("![無副檔名](picture)", "不支援的插圖格式，改顯示替代文字：picture（第 3 行）"),
])
def test_web_and_unsupported_illustrations_show_alt_text_with_a_warning(markdown, warning):
    class Refuses:
        def link(self, path, fragment):
            return None

        def image(self, target):
            raise AssertionError(f"不該交給解析器：{target}")

    result = render_markdown(f"# 章\n\n{markdown}\n", Refuses())
    assert parse(result.body).find(f".//{X}img") is None
    assert result.warnings == (warning,)


def test_an_empty_alt_text_falls_back_to_the_file_name():
    assert paragraph_text("前![](https://example.com/dir/photo.png?x=1)後\n") == "前photo.png後"
    assert paragraph_text("前![](images/%E5%9C%96.svg)後\n") == "前圖.svg後"


# --- XHTML 合法性 ----------------------------------------------------------------

@pytest.mark.parametrize("char", ["\x00", "\x01", "\x08", "\x0b", "\x0c", "\x0e", "\x1f", "\ufffe", "\uffff"])
def test_characters_xml_forbids_are_replaced_so_the_xhtml_still_parses(char):
    result = render_markdown(f"# 標{char}題\n\nhello {char} world\n\n`碼{char}`\n", NoTargets())
    root = parse(result.body)  # 解析失敗即代表不是格式正確的 XHTML
    assert char not in result.body and char not in result.title
    assert "hello \ufffd world" in "".join(root.itertext())
    assert result.title == "標\ufffd題"


def test_tabs_and_line_breaks_are_kept():
    root = parse(render_markdown("```\na\tb\r\nc\n```\n", NoTargets()).body)
    assert root.find(f"{X}pre/{X}code").text == "a\tb\nc\n"
