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
