"""文字書：把 Markdown 資料夾轉成 reflowable EPUB（主接縫：CLI 進入點）。"""

import pytest

from epubgen.cli import main
from tests.helpers import Epub, make_image, spine_direction


def write_md(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


@pytest.fixture
def novel(tmp_path):
    folder = tmp_path / "pages"
    folder.mkdir()
    write_md(folder / "8096_1.md", "# 第1章 開端\n\n第一段。\n")
    write_md(folder / "8096_2.md", "# 第2章 梁溪\n\n第二段。\n")
    return folder


def build(folder, *args):
    code = main([str(folder), *args])
    assert code == 0
    return Epub(folder.parent / f"{folder.name}.epub")


def test_markdown_folder_becomes_a_reflowable_text_book(novel):
    book = build(novel)
    assert book.meta_property("rendition:layout") in (None, "reflowable")
    assert spine_direction(book) == "ltr"
    assert len(book.page_paths()) == 2
    assert all(book.viewport_or_none(p) is None for p in book.page_paths())


# --- 書的種類 -----------------------------------------------------------------

def test_markdown_and_images_in_the_root_still_make_a_text_book_without_the_images(novel):
    make_image(novel / "cover.jpg")
    book = build(novel)
    assert spine_direction(book) == "ltr"
    assert not any(n.lower().endswith(".jpg") for n in book.zip.namelist())


def test_markdown_extensions_are_case_insensitive_and_other_files_are_ignored(tmp_path):
    folder = tmp_path / "pages"
    write_md(folder / "a.MD", "# 甲\n")
    write_md(folder / "b.markdown", "# 乙\n")
    write_md(folder / "c.txt", "# 丙\n")
    (folder / ".DS_Store").write_bytes(b"\x00\x01")
    book = build(folder)
    assert [text for text, _ in book.nav_links()] == ["甲", "乙"]


# --- 章與章名 -----------------------------------------------------------------

def test_each_markdown_file_is_one_chapter_with_a_generated_file_name(tmp_path):
    folder = tmp_path / "pages"
    write_md(folder / "A&B <x>.md", "# 甲\n")
    write_md(folder / "z.md", "# 乙\n")
    book = build(folder)
    assert book.page_paths() == ["OEBPS/text/chapter-0001.xhtml", "OEBPS/text/chapter-0002.xhtml"]


def test_chapters_follow_natural_file_name_order(tmp_path):
    folder = tmp_path / "pages"
    for n in (10, 2, 1):
        write_md(folder / f"8096_{n}.md", f"# 第{n}章\n")
    book = build(folder)
    assert [text for text, _ in book.nav_links()] == ["第1章", "第2章", "第10章"]


def test_chapter_title_is_the_plain_text_of_the_first_h1_which_stays_in_the_body(tmp_path):
    folder = tmp_path / "pages"
    write_md(folder / "01.md", "前言。\n\n# 第8章 *梁溪* `code`\n\n正文。\n\n# 第二個標題\n\n後文。\n")
    book = build(folder)
    chapter = book.page_paths()[0]
    assert book.nav_links()[0][0] == "第8章 梁溪 code"
    assert book.chapter_headings(chapter, "h1") == ["第8章 梁溪 code", "第二個標題"]
    assert "後文。" in book.chapter_body_text(chapter)


def test_without_an_h1_the_chapter_title_is_the_file_name_with_its_number_prefix(tmp_path):
    folder = tmp_path / "pages"
    write_md(folder / "01-序章.md", "## 小標\n\n內容。\n")
    book = build(folder)
    assert book.nav_links()[0][0] == "01-序章"


def test_toc_has_one_entry_per_chapter_pointing_at_its_start(novel):
    book = build(novel)
    assert book.nav_links() == [("第1章 開端", "OEBPS/text/chapter-0001.xhtml"),
                                ("第2章 梁溪", "OEBPS/text/chapter-0002.xhtml")]
    assert "第一段。" in book.chapter_body_text("OEBPS/text/chapter-0001.xhtml")


# --- 書籍資訊與輸出 -------------------------------------------------------------

def test_title_defaults_to_the_folder_name(novel):
    book = build(novel)
    assert book.dc("title") == "pages"
    assert book.dc("language") == "zh-TW"
    assert book.dc("creator") is None


def test_title_author_and_language_are_written_to_metadata(novel):
    assert main([str(novel), "--title", "A & B", "--author", "某某", "--language", "ja"]) == 0
    book = Epub(novel.parent / "A & B.epub")
    assert (book.dc("title"), book.dc("creator"), book.dc("language")) == ("A & B", "某某", "ja")


def test_output_option_and_overwrite_protection_match_comics(novel, tmp_path):
    target = tmp_path / "out.epub"
    assert main([str(novel), "-o", str(target)]) == 0
    assert main([str(novel), "-o", str(target)]) == 1
    assert main([str(novel), "-o", str(target), "--force"]) == 0


def test_success_message_shows_the_output_path_and_chapter_count(novel, capsys):
    build(novel)
    out = capsys.readouterr().out
    assert str(novel.parent / "pages.epub") in out
    assert "共 2 章" in out


def test_failure_leaves_no_output_and_does_not_touch_the_input(tmp_path, capsys):
    folder = tmp_path / "pages"
    write_md(folder / "good.md", "# 甲\n")
    (folder / "bad.md").write_bytes(b"\xff\xfe\x00bad")
    before = sorted((p.name, p.read_bytes()) for p in folder.iterdir())
    assert main([str(folder)]) == 1
    assert "bad.md" in capsys.readouterr().err
    assert sorted((p.name, p.read_bytes()) for p in folder.iterdir()) == before
    assert list(tmp_path.iterdir()) == [folder]


def test_hidden_markdown_files_and_folders_are_ignored(tmp_path):
    folder = tmp_path / "pages"
    write_md(folder / "a.md", "# 甲\n")
    (folder / "._a.md").write_bytes(b"\x00\x05\x16\x07\xff")  # macOS 的 AppleDouble 檔，不是 UTF-8
    book = build(folder)
    assert [text for text, _ in book.nav_links()] == ["甲"]


def test_markdown_inside_a_hidden_folder_does_not_turn_a_comic_into_a_text_book(tmp_path):
    folder = tmp_path / "comic"
    make_image(folder / "1.jpg")
    write_md(folder / ".git" / "README.md", "# 不是書\n")
    assert main([str(folder)]) == 0
    assert spine_direction(Epub(tmp_path / "comic.epub")) == "rtl"


# --- 漫畫專用旗標 ---------------------------------------------------------------

@pytest.mark.parametrize("flags", [["--direction", "rtl"], ["--direction", "ltr"], ["--spread"]])
def test_comic_only_flags_are_rejected_for_a_text_book(novel, capsys, flags):
    assert main([str(novel), *flags]) == 1
    err = capsys.readouterr().err
    assert flags[0] in err
    assert "只對漫畫書有效" in err
    assert not (novel.parent / "pages.epub").exists()


def test_help_mentions_markdown_folders_and_comic_only_flags(capsys):
    with pytest.raises(SystemExit):
        main(["--help"])
    out = " ".join(capsys.readouterr().out.split())
    assert "圖片或 Markdown 檔的資料夾" in out
    assert out.count("只對漫畫書有效") >= 2


def test_comic_only_flag_error_comes_before_the_existing_output_error(novel, capsys):
    (novel.parent / "pages.epub").write_bytes(b"old")
    assert main([str(novel), "--spread"]) == 1
    assert "只對漫畫書有效" in capsys.readouterr().err
    assert (novel.parent / "pages.epub").read_bytes() == b"old"


# --- 部與兩層目錄 ---------------------------------------------------------------

def chapter_path(n):
    return f"OEBPS/text/chapter-{n:04d}.xhtml"


@pytest.fixture
def parted(tmp_path):
    folder = tmp_path / "pages"
    write_md(folder / "序.md", "# 序\n")
    write_md(folder / "第10部" / "a.md", "# 十之一\n")
    write_md(folder / "第2部" / "x_10.md", "# 二之十\n")
    write_md(folder / "第2部" / "x_2.md", "# 二之二\n")
    write_md(folder / "第2部" / "深" / "更深" / "y.md", "# 二之深\n")
    make_image(folder / "插圖" / "1.jpg")
    return folder


def test_first_level_subfolders_become_parts_in_a_two_level_toc(parted):
    book = build(parted)
    assert book.toc() == [
        ("序", 1, chapter_path(1)),
        ("第2部", 1, chapter_path(2)),
        ("二之二", 2, chapter_path(2)),
        ("二之十", 2, chapter_path(3)),
        ("二之深", 2, chapter_path(4)),
        ("第10部", 1, chapter_path(5)),
        ("十之一", 2, chapter_path(5)),
    ]


def test_spine_follows_the_reading_order_of_the_whole_book(parted):
    book = build(parted)
    assert book.page_paths() == [chapter_path(n) for n in range(1, 6)]
    assert [book.chapter_headings(p, "h1")[0] for p in book.page_paths()] == [
        "序", "二之二", "二之十", "二之深", "十之一"]


def test_markdown_only_in_subfolders_makes_a_book_of_parts(tmp_path):
    folder = tmp_path / "pages"
    write_md(folder / "上" / "1.md", "# 甲\n")
    book = build(folder)
    assert book.toc() == [("上", 1, chapter_path(1)), ("甲", 2, chapter_path(1))]


def test_hidden_subfolders_do_not_become_parts(tmp_path):
    folder = tmp_path / "pages"
    write_md(folder / "a.md", "# 甲\n")
    write_md(folder / ".notes" / "x.md", "# 筆記\n")
    book = build(folder)
    assert book.toc() == [("甲", 1, chapter_path(1))]


# --- 警告、front matter、空章、原始 HTML ----------------------------------------

def test_a_book_without_warnings_prints_nothing_to_stderr(novel, capsys):
    build(novel)
    assert capsys.readouterr().err == ""


def test_front_matter_is_left_out_of_the_book(tmp_path):
    folder = tmp_path / "pages"
    write_md(folder / "a.md", "---\ntitle: 網站標題\nlayout: post\n---\n# 第1章\n\n正文。\n")
    book = build(folder)
    assert book.toc() == [("第1章", 1, chapter_path(1))]
    text = book.chapter_body_text(chapter_path(1))
    assert "網站標題" not in text and "layout" not in text
    assert "正文。" in text


def test_empty_chapters_are_skipped_with_warnings_listed_at_the_end(tmp_path, capsys):
    folder = tmp_path / "pages"
    write_md(folder / "1.md", "# 甲\n")
    write_md(folder / "2.md", "")
    write_md(folder / "上" / "3.md", "---\ntitle: x\n---\n")
    write_md(folder / "上" / "4.md", "# 乙\n")
    book = build(folder)
    assert book.toc() == [("甲", 1, chapter_path(1)), ("上", 1, chapter_path(2)), ("乙", 2, chapter_path(2))]
    captured = capsys.readouterr()
    assert "共 2 章" in captured.out
    header, *warnings = captured.err.splitlines()
    assert "2 則警告" in header
    assert len(warnings) == 2
    assert "2.md" in warnings[0] and "沒有內容" in warnings[0]
    assert "上/3.md" in warnings[1] and "沒有內容" in warnings[1]


def test_a_folder_of_only_empty_chapters_is_an_error(tmp_path, capsys):
    folder = tmp_path / "pages"
    write_md(folder / "1.md", "\n\n")
    write_md(folder / "2.md", "---\na: 1\n---\n")
    assert main([str(folder)]) == 1
    assert "沒有任何有內容的章" in capsys.readouterr().err
    assert list(tmp_path.iterdir()) == [folder]


def test_raw_html_is_shown_as_text_and_warned_about_with_the_file_name(tmp_path, capsys):
    folder = tmp_path / "pages"
    write_md(folder / "a.md", "# 甲\n\n<div>區塊</div>\n\n文 <span>行內</span>。\n")
    book = build(folder)
    text = book.chapter_body_text(chapter_path(1))
    assert "<div>區塊</div>" in text and "<span>行內</span>" in text
    err = capsys.readouterr().err
    assert "a.md" in err and "原始 HTML" in err and "第 3、5 行" in err


# --- 內建樣式 --------------------------------------------------------------------

def test_every_chapter_links_the_built_in_stylesheet_listed_in_the_manifest(novel):
    book = build(novel)
    css = book.stylesheet_paths()
    assert len(css) == 1
    for chapter in book.page_paths():
        assert book.stylesheets(chapter) == css
    style = book.zip.read(css[0]).decode("utf-8")
    assert "table" in style and "pre" in style and "max-width: 100%" in style


def test_no_fonts_are_embedded(novel):
    book = build(novel)
    assert not [n for n in book.zip.namelist() if n.lower().endswith((".ttf", ".otf", ".woff", ".woff2"))]
    assert not [i for i in book.manifest().values() if "font" in i.get("media-type")]
    assert all("@font-face" not in book.zip.read(css).decode("utf-8") for css in book.stylesheet_paths())


# --- 書內連結 --------------------------------------------------------------------

@pytest.fixture
def linked(tmp_path):
    folder = tmp_path / "pages"
    write_md(folder / "序.md", "# 序\n\n[第一章](第一部/01.md) [標題](第一部/01.md#開端-a) "
                               "[本章](#前言) [外部](https://example.com/x)\n\n## 前言\n")
    write_md(folder / "第一部" / "01.md", "# 第一章\n\n## 開端 A\n\n[回序](../序.md#序) "
                                         "[跨部](../第二部/深/02.md#同名-1) [自己](01.md)\n")
    write_md(folder / "第二部" / "深" / "02.md", "# 第二章\n\n## 同名\n\n## 同名\n")
    return folder


def test_links_between_markdown_files_point_at_chapters_and_headings(linked):
    book = build(linked)
    assert book.links(chapter_path(1)) == [
        ("第一章", chapter_path(2)), ("標題", f"{chapter_path(2)}#開端-a"),
        ("本章", f"{chapter_path(1)}#前言"), ("外部", "https://example.com/x")]
    assert book.links(chapter_path(2)) == [
        ("回序", f"{chapter_path(1)}#序"), ("跨部", f"{chapter_path(3)}#同名-1"), ("自己", chapter_path(2))]


def test_link_anchors_exist_as_heading_ids(linked):
    book = build(linked)
    for chapter in book.page_paths():
        for _text, target in book.links(chapter):
            path, _, fragment = target.partition("#")
            if fragment:
                assert fragment in book.ids(path)
    assert book.ids(chapter_path(3)) == ["第二章", "同名", "同名-1"]


def test_broken_links_become_text_with_a_warning_naming_the_file(tmp_path, capsys):
    folder = tmp_path / "pages"
    write_md(folder / "a.md", "# 甲\n\n[無檔](nope.md) [無錨](b.md#nope) [本章無錨](#nope)\n"
                              "[非 md](doc.pdf) [空章](empty.md) [好](b.md#乙)\n")
    write_md(folder / "b.md", "# 乙\n")
    write_md(folder / "empty.md", "")
    (folder / "doc.pdf").write_bytes(b"%PDF")
    book = build(folder)
    assert book.links(chapter_path(1)) == [("好", f"{chapter_path(2)}#乙")]
    assert "無檔 無錨 本章無錨" in book.chapter_body_text(chapter_path(1))
    warnings = [line for line in capsys.readouterr().err.splitlines() if "失效的連結" in line]
    assert [w.split("：")[-1] for w in warnings] == [
        "nope.md（第 3 行）", "b.md#nope（第 3 行）", "#nope（第 3 行）",
        "doc.pdf（第 4 行）", "empty.md（第 4 行）"]
    assert all("a.md" in w for w in warnings)


def test_anchor_links_match_headings_case_insensitively_like_github(tmp_path):
    folder = tmp_path / "pages"
    write_md(folder / "a.md", "# Intro\n\n[上](#INTRO) [下](b.md#Part-Two)\n")
    write_md(folder / "b.md", "# Part Two\n")
    assert build(folder).links(chapter_path(1)) == [
        ("上", f"{chapter_path(1)}#intro"), ("下", f"{chapter_path(2)}#part-two")]


# --- 插圖 ------------------------------------------------------------------------

@pytest.fixture
def illustrated(tmp_path):
    folder = tmp_path / "pages"
    write_md(folder / "a.md", "# 甲\n\n![地圖](images/map.png)\n\n![](../shared/logo.JPG)\n")
    write_md(folder / "第一部" / "b.md", "# 乙\n\n![同一張](../images/map.png) ![近照](pic.gif)\n")
    make_image(folder / "images" / "map.png", fmt="PNG")
    make_image(folder / "images" / "unused.jpg")
    make_image(folder / "第一部" / "pic.gif", fmt="GIF")
    make_image(tmp_path / "shared" / "logo.JPG", fmt="JPEG")
    return folder


def test_referenced_illustrations_are_packaged_once_and_shown_in_place(illustrated):
    book = build(illustrated)
    packaged = book.illustrations()
    assert len(packaged) == 3
    a_images = book.chapter_images(chapter_path(1))
    b_images = book.chapter_images(chapter_path(2))
    assert [alt for _, alt in a_images + b_images] == ["地圖", "", "同一張", "近照"]
    map_path, logo_path = (path for path, _ in a_images)
    assert b_images[0][0] == map_path
    assert {map_path, logo_path, b_images[1][0]} == set(packaged)
    assert map_path.endswith(".png") and logo_path.endswith(".jpg") and b_images[1][0].endswith(".gif")
    assert book.zip.read(logo_path) == (illustrated.parent / "shared" / "logo.JPG").read_bytes()


def test_unreferenced_images_are_not_packaged(illustrated):
    book = build(illustrated)
    names = book.zip.namelist()
    assert not any("unused" in n for n in names)
    assert len([n for n in names if n.lower().endswith((".png", ".jpg", ".gif", ".webp"))]) == 3


def illustration_sizes(book):
    from PIL import Image
    import io
    return {path.rsplit(".", 1)[-1]: Image.open(io.BytesIO(book.zip.read(path))).size
            for path in book.illustrations()}


@pytest.mark.parametrize("args, expected", [
    ([], {"jpg": (80, 120)}),
    (["--keep-webp"], {"webp": (80, 120)}),
    (["--max-size", "60"], {"jpg": (40, 60)}),
])
def test_image_options_apply_to_illustrations_like_comics(tmp_path, args, expected):
    folder = tmp_path / "pages"
    write_md(folder / "a.md", "![圖](a.webp)\n")
    make_image(folder / "a.webp", fmt="WEBP")
    assert illustration_sizes(build(folder, *args)) == expected


def test_quality_recompresses_illustrations(tmp_path):
    folder = tmp_path / "pages"
    write_md(folder / "a.md", "![圖](a.jpg)\n")
    make_image(folder / "a.jpg", size=(400, 400))
    original = (folder / "a.jpg").read_bytes()
    book = build(folder, "--quality", "10")
    assert book.zip.read(book.illustrations()[0]) != original


@pytest.mark.parametrize("prepare", ["missing", "broken"])
def test_a_missing_or_broken_illustration_is_an_error_by_default(tmp_path, capsys, prepare):
    folder = tmp_path / "pages"
    write_md(folder / "a.md", "# 甲\n\n![壞圖](images/bad.png)\n")
    if prepare == "broken":
        (folder / "images").mkdir()
        (folder / "images" / "bad.png").write_bytes(b"not a png")
    assert main([str(folder)]) == 1
    err = capsys.readouterr().err
    assert "images/bad.png" in err and "--skip-broken" in err
    assert not (tmp_path / "pages.epub").exists()


def test_skip_broken_shows_alt_text_and_lists_skipped_illustrations(tmp_path, capsys):
    folder = tmp_path / "pages"
    write_md(folder / "a.md", "# 甲\n\n前![壞圖](bad.png)後 ![](gone.jpg)\n")
    write_md(folder / "b.md", "# 乙\n\n![又一次](bad.png)\n")
    (folder / "bad.png").write_bytes(b"not a png")
    book = build(folder, "--skip-broken")
    assert book.illustrations() == []
    assert "前壞圖後 gone.jpg" in book.chapter_body_text(chapter_path(1))
    err = capsys.readouterr().err
    assert "已跳過 2 張" in err
    assert "a.md：bad.png" in err and "a.md：gone.jpg" in err


def test_web_and_svg_illustrations_show_alt_text_with_warnings(tmp_path, capsys):
    folder = tmp_path / "pages"
    write_md(folder / "a.md", "# 甲\n\n![網圖](https://example.com/a.png) ![向量](a.svg)\n")
    (folder / "a.svg").write_text("<svg/>", encoding="utf-8")
    book = build(folder)
    assert book.illustrations() == []
    assert not any(n.endswith(".svg") for n in book.zip.namelist())
    assert "網圖 向量" in book.chapter_body_text(chapter_path(1))
    err = capsys.readouterr().err
    assert "a.md：網路圖片不會下載" in err and "a.md：不支援的插圖格式" in err


# --- 封面與封面頁 ----------------------------------------------------------------

def cover_of(book):
    covers = book.cover_items()
    assert len(covers) == 1
    return covers[0], book.resolve(covers[0].get("href"))


def test_a_cover_becomes_the_cover_image_and_a_cover_page_first_in_the_spine(novel, tmp_path):
    cover_bytes = make_image(tmp_path / "art" / "cover.jpg", size=(300, 450))
    book = build(novel, "--cover", str(tmp_path / "art" / "cover.jpg"))
    item, cover_path = cover_of(book)
    assert item.get("media-type") == "image/jpeg"
    assert book.zip.read(cover_path) == cover_bytes
    first, *chapters = book.page_paths()
    assert chapters == [chapter_path(1), chapter_path(2)]
    assert [path for path, _ in book.chapter_images(first)] == [cover_path]
    assert book.chapter_body_text(first).strip() == ""


def test_the_cover_page_is_not_in_the_toc(novel, tmp_path):
    make_image(tmp_path / "cover.png")
    book = build(novel, "--cover", str(tmp_path / "cover.png"))
    cover_page = book.page_paths()[0]
    assert [target for _, _, target in book.toc()] == [chapter_path(1), chapter_path(2)]
    assert cover_page not in [target for _, _, target in book.toc()]


def test_without_a_cover_there_is_no_cover_image_or_cover_page(novel):
    book = build(novel)
    assert book.cover_items() == []
    assert book.page_paths()[0] == chapter_path(1)
    assert not [n for n in book.zip.namelist() if "cover" in n.lower()]


def test_a_relative_cover_path_is_resolved_from_the_working_directory(novel, tmp_path, monkeypatch):
    make_image(tmp_path / "art" / "c.jpg")
    monkeypatch.chdir(tmp_path / "art")
    book = build(novel, "--cover", "c.jpg")
    assert len(book.cover_items()) == 1


def test_a_gif_cover_becomes_a_jpeg_like_comics(novel, tmp_path):
    make_image(tmp_path / "cover.gif")
    book = build(novel, "--cover", str(tmp_path / "cover.gif"))
    item, cover_path = cover_of(book)
    assert item.get("media-type") == "image/jpeg"
    assert book.zip.read(cover_path)[:3] == b"\xff\xd8\xff"
    assert [path for path, _ in book.chapter_images(book.page_paths()[0])] == [cover_path]


def test_image_options_apply_to_the_cover(novel, tmp_path):
    make_image(tmp_path / "cover.webp", size=(300, 450))
    book = build(novel, "--cover", str(tmp_path / "cover.webp"), "--max-size", "90")
    item, cover_path = cover_of(book)
    assert item.get("media-type") == "image/jpeg"
    from PIL import Image
    import io
    assert Image.open(io.BytesIO(book.zip.read(cover_path))).size == (60, 90)


@pytest.mark.parametrize("make, message", [
    (lambda path: None, "封面圖片不存在"),
    (lambda path: path.with_suffix(".svg").write_text("<svg/>"), "不是支援的圖片"),
    (lambda path: path.with_suffix(".png").write_bytes(b"not a png"), "無法讀取封面圖片"),
    (lambda path: path.with_suffix(".jpg").mkdir(), "不是支援的圖片"),
])
def test_a_bad_cover_is_an_error_and_makes_no_book(novel, tmp_path, capsys, make, message):
    stem = tmp_path / "cover"
    make(stem)
    candidates = [p for p in tmp_path.iterdir() if p.name.startswith("cover")]
    cover = candidates[0] if candidates else stem.with_suffix(".jpg")
    assert main([str(novel), "--cover", str(cover), "--skip-broken"]) == 1
    assert message in capsys.readouterr().err
    assert not (tmp_path / "pages.epub").exists()


def test_a_bad_cover_is_reported_before_problems_in_the_chapters(tmp_path, capsys):
    folder = tmp_path / "pages"
    (folder).mkdir()
    (folder / "bad.md").write_bytes(b"\xff\xfe\x00bad")
    assert main([str(folder), "--cover", str(tmp_path / "missing.jpg")]) == 1
    assert "封面圖片不存在" in capsys.readouterr().err


def test_a_cover_that_is_also_an_illustration_is_packaged_for_both(tmp_path):
    folder = tmp_path / "pages"
    write_md(folder / "a.md", "# 甲\n\n![圖](art.jpg)\n")
    make_image(folder / "art.jpg")
    book = build(folder, "--cover", str(folder / "art.jpg"))
    assert len(book.cover_items()) == 1
    assert len(book.illustrations()) == 2  # 封面圖與插圖各一份
