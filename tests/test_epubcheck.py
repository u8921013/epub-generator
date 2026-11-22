"""用 EPUBCheck 驗證各情境產出的 EPUB。環境沒有 Java 或 EPUBCheck 時整組跳過。

新增情境只要在 SCENARIOS 加一列：名稱 → (準備資料夾的函式, CLI 參數)。
"""

import pytest

from epubgen.cli import main
from tests import epubcheck
from tests.helpers import make_image

COMMAND = epubcheck.find_command()

pytestmark = pytest.mark.skipif(
    COMMAND is None,
    reason="找不到 Java 或 EPUBCheck（設定 EPUBCHECK_JAR，或解壓到 .tools/，見 README）",
)


def flat(folder):
    make_image(folder / "1.jpg", size=(300, 500))
    make_image(folder / "2.jpg", size=(320, 480))
    make_image(folder / "10.png", size=(640, 480))
    make_image(folder / "11.gif", size=(100, 150))


def chapters(folder):
    make_image(folder / "cover.jpg", size=(300, 500))
    for chapter, count in (("第 10 話", 2), ("第 2 話", 3)):
        for n in range(count):
            make_image(folder / chapter / f"{n + 1}.jpg", size=(300 + n, 500))
    make_image(folder / "第 2 話" / "extra" / "1.jpg", size=(300, 500))


def with_webp(folder):
    make_image(folder / "1.jpg", size=(300, 500))
    make_image(folder / "2.webp", size=(300, 500))


def square_cover(folder):
    make_image(folder / "1.jpg", size=(1523, 1469))
    for n in range(2, 6):
        make_image(folder / f"{n}.jpg", size=(1200, 1700 + n * 10))


def gif_first(folder):
    make_image(folder / "1.gif", size=(300, 500))
    make_image(folder / "2.jpg", size=(300, 500))


def special_characters(folder):
    make_image(folder / "A&B <1>" / "1.jpg", size=(300, 500))
    make_image(folder / "A&B <1>" / "2.jpg", size=(300, 500))


def text_simple(folder):
    (folder / "8096_1.md").write_text("# 第1章 開端\n\n第一段 **粗體**，A & B < C。\n", encoding="utf-8")
    (folder / "8096_2.md").write_text("沒有標題的一章。\n\n---\n\n第二段  \n硬換行。\n", encoding="utf-8")
    (folder / "8096_10.md").write_text("# 第10章\n\n## 小標\n\n內容。\n", encoding="utf-8")


def text_parts(folder):
    def md(rel, text):
        path = folder / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    md("序.md", "# 序\n\n前言，見[第二章](第2部%20A&B/深/2.md#重複-1)與[本章](#小節-a)。\n\n## 小節 A\n")
    md("第2部 A&B/1.md", "# 第1章\n\n[回序](../序.md)、[失效](nope.md)、[外部](https://example.com)。\n")
    md("第2部 A&B/深/2.md", "# 第2章 <x>\n\n## 重複\n\n## 重複\n\n[第一章](../1.md#第1章)\n")
    md("第10部/1.md", "沒有標題。\n")
    make_image(folder / "插圖" / "1.jpg")


def text_rich(folder):
    (folder / "1.md").write_text(
        "# 表格與程式碼\n\n今天天氣很好，\n我們去散步。English\nwords ~~刪除~~。\n\n"
        "| 名稱 | 數量 |\n|:--|--:|\n| A&B | <3> |\n\n"
        "```python\ndef f(x):\n    return x < 1 and x & 2\n```\n\n"
        "    縮排程式碼\n\n> 引用\n>\n> - 清單\n\n1. 一\n2. 二\n\n***\n", encoding="utf-8")


def text_illustrated(folder):
    (folder / "1.md").write_text(
        "# 插圖\n\n![地圖](images/map.png)\n\n![](images/photo.webp) ![動](anim.gif)\n\n"
        "![向量](a.svg) ![網圖](https://example.com/a.png)\n", encoding="utf-8")
    (folder / "第一部").mkdir()
    (folder / "第一部" / "2.md").write_text("# 共用\n\n![同一張](../images/map.png) ![外部](../../logo.jpg)\n",
                                         encoding="utf-8")
    make_image(folder / "images" / "map.png")
    make_image(folder / "images" / "photo.webp")
    make_image(folder / "anim.gif")
    make_image(folder.parent / "logo.jpg")


def text_warnings(folder):
    (folder / "1.md").write_text(
        "---\ntitle: x\n---\n# 第1章\n\n<div class=\"a\">\n<p>區塊 &nbsp; HTML</p>\n</div>\n\n"
        "文 <span>行內</span> <br> <!-- 註解 --> &copy;。\n", encoding="utf-8")
    (folder / "2.md").write_text("", encoding="utf-8")
    (folder / "3.md").write_text("---\na: 1\n---\n", encoding="utf-8")


SCENARIOS = {
    "basic": (flat, []),
    "ltr": (flat, ["--direction", "ltr"]),
    "spread-rtl": (flat, ["--spread"]),
    "spread-ltr": (flat, ["--spread", "--direction", "ltr"]),
    "chapters": (chapters, []),
    "chapters-spread": (chapters, ["--spread", "--direction", "ltr"]),
    "metadata": (flat, ["--title", "A & B <x>", "--author", "某某", "--language", "ja"]),
    "special-characters": (special_characters, []),
    "gif-cover": (gif_first, []),
    "square-cover": (square_cover, []),
    "quality-and-resize": (flat, ["--quality", "60", "--max-size", "400"]),
    "resize-only": (flat, ["--max-size", "250"]),
    "webp-converted": (with_webp, []),
    "webp-kept": (with_webp, ["--keep-webp"]),
    "text-simple": (text_simple, ["--author", "某某"]),
    "text-parts": (text_parts, []),
    "text-warnings": (text_warnings, []),
    "text-rich": (text_rich, []),
    "text-illustrated": (text_illustrated, ["--max-size", "60"]),
}


def build(tmp_path, prepare, args, extra=()):
    folder = tmp_path / "in" / "my-comic"
    folder.mkdir(parents=True)
    prepare(folder)
    target = tmp_path / "book.epub"
    assert main([str(folder), "-o", str(target), *args, *extra]) == 0
    return target


@pytest.mark.parametrize("name", list(SCENARIOS))
def test_epubcheck_reports_no_errors(tmp_path, name):
    prepare, args = SCENARIOS[name]
    target = build(tmp_path, prepare, args)

    ok, output = epubcheck.run(COMMAND, target)

    assert ok, f"EPUBCheck 回報錯誤（情境 {name}）：\n{output}"


def test_epubcheck_reports_no_errors_with_an_external_cover(tmp_path):
    cover = tmp_path / "front.png"
    make_image(cover, size=(200, 300))
    prepare, args = SCENARIOS["basic"]
    target = build(tmp_path, prepare, args, extra=["--cover", str(cover)])

    ok, output = epubcheck.run(COMMAND, target)

    assert ok, f"EPUBCheck 回報錯誤（外部封面）：\n{output}"


def test_epubcheck_reports_no_errors_after_skipping_broken_images(tmp_path):
    def prepare(folder):
        flat(folder)
        (folder / "5.jpg").write_bytes(b"garbage")

    target = build(tmp_path, prepare, [], extra=["--skip-broken"])

    ok, output = epubcheck.run(COMMAND, target)

    assert ok, f"EPUBCheck 回報錯誤（跳過損毀圖片）：\n{output}"
