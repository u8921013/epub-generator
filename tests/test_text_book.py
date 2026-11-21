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


def test_markdown_only_in_a_subfolder_still_makes_a_text_book(tmp_path):
    folder = tmp_path / "pages"
    make_image(folder / "1.jpg")
    write_md(folder / "deep" / "er" / "x.md", "# 甲\n")
    # 依 ADR 0001 是文字書；子資料夾的章（部）在 ticket 04 實作，目前沒有可用的章。
    assert main([str(folder)]) == 1
    assert not (tmp_path / "pages.epub").exists()


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
