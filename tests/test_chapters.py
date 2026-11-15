import pytest

from epubgen.cli import main
from tests.helpers import Epub, make_image


@pytest.fixture
def comic(tmp_path):
    folder = tmp_path / "my-comic"
    folder.mkdir()
    return folder


def build(comic, *args):
    code = main([str(comic), *args])
    assert code == 0
    return Epub(comic.parent / "my-comic.epub")


def toc(book):
    """回傳 [(章節名稱, 目標是第幾頁（從 1 起算）)]。"""
    pages = book.page_paths()
    return [(text, pages.index(path) + 1) for text, path in book.nav_links()]


def color(n):
    return (n, 255 - n, 7)


# --- 基本章節 -----------------------------------------------------------------

def test_each_subfolder_becomes_a_chapter_pointing_at_its_first_page(comic):
    make_image(comic / "ch1" / "1.jpg")
    make_image(comic / "ch1" / "2.jpg")
    make_image(comic / "ch2" / "1.jpg")
    make_image(comic / "ch2" / "2.jpg")
    make_image(comic / "ch2" / "3.jpg")

    book = build(comic)

    assert len(book.page_paths()) == 5
    assert toc(book) == [("ch1", 1), ("ch2", 3)]


def test_chapters_are_sorted_naturally_by_folder_name(comic):
    for name in ("第 10 話", "第 2 話", "第 1 話"):
        make_image(comic / name / "1.jpg")

    book = build(comic)

    assert [t for t, _ in toc(book)] == ["第 1 話", "第 2 話", "第 10 話"]


def test_pages_follow_chapter_order_then_natural_order_inside_a_chapter(comic):
    unique = 0
    for chapter, files in (("b-ch2", (2, 10, 1)), ("a-ch1", (1, 2))):
        for n in files:
            unique += 1
            make_image(comic / chapter / f"{n}.jpg", color=color(unique * 10))
    expected = [
        (comic / "a-ch1" / "1.jpg").read_bytes(),
        (comic / "a-ch1" / "2.jpg").read_bytes(),
        (comic / "b-ch2" / "1.jpg").read_bytes(),
        (comic / "b-ch2" / "2.jpg").read_bytes(),
        (comic / "b-ch2" / "10.jpg").read_bytes(),
    ]

    book = build(comic)

    assert book.page_images() == expected
    assert toc(book) == [("a-ch1", 1), ("b-ch2", 3)]


def test_chapter_titles_with_xml_special_characters_survive(comic):
    make_image(comic / "A&B <1> \"x\"" / "1.jpg")

    book = build(comic)

    assert toc(book) == [("A&B <1> \"x\"", 1)]


# --- 根目錄圖片 ---------------------------------------------------------------

def test_root_images_come_first_and_belong_to_no_chapter(comic):
    make_image(comic / "cover.jpg", color=color(1))
    make_image(comic / "ch1" / "1.jpg", color=color(2))
    make_image(comic / "ch1" / "2.jpg", color=color(3))

    book = build(comic)

    assert len(book.page_paths()) == 3
    assert book.page_images()[0] == (comic / "cover.jpg").read_bytes()
    assert toc(book) == [("ch1", 2)]


def test_book_with_only_root_images_is_unchanged(comic):
    make_image(comic / "1.jpg")
    make_image(comic / "2.jpg")

    book = build(comic)

    assert toc(book) == [("my-comic", 1)]


def test_default_cover_is_the_first_page_of_the_whole_book(comic):
    make_image(comic / "ch2" / "1.jpg", color=color(9))
    make_image(comic / "ch1" / "1.jpg", color=color(5))

    book = build(comic)

    covers = book.cover_items()
    assert len(covers) == 1
    assert book.zip.read(book.resolve(covers[0].get("href"))) == (
        comic / "ch1" / "1.jpg").read_bytes()


# --- 深層資料夾與空資料夾 -----------------------------------------------------

def test_deeper_folders_merge_into_their_first_level_chapter(comic):
    make_image(comic / "ch1" / "1.jpg", color=color(1))
    make_image(comic / "ch1" / "part-2" / "1.jpg", color=color(3))
    make_image(comic / "ch1" / "part-2" / "deeper" / "1.jpg", color=color(4))
    make_image(comic / "ch1" / "part-10" / "1.jpg", color=color(5))
    make_image(comic / "ch2" / "1.jpg", color=color(6))

    book = build(comic)

    assert [t for t, _ in toc(book)] == ["ch1", "ch2"]
    assert toc(book) == [("ch1", 1), ("ch2", 5)]
    assert book.page_images() == [
        (comic / "ch1" / "1.jpg").read_bytes(),
        (comic / "ch1" / "part-2" / "1.jpg").read_bytes(),
        (comic / "ch1" / "part-2" / "deeper" / "1.jpg").read_bytes(),
        (comic / "ch1" / "part-10" / "1.jpg").read_bytes(),
        (comic / "ch2" / "1.jpg").read_bytes(),
    ]


def test_subfolders_without_images_make_no_chapter(comic):
    make_image(comic / "ch1" / "1.jpg")
    (comic / "empty").mkdir()
    (comic / "notes").mkdir()
    (comic / "notes" / "readme.txt").write_text("hi")

    book = build(comic)

    assert toc(book) == [("ch1", 1)]


def test_only_empty_subfolders_is_a_no_images_error(comic, capsys):
    (comic / "empty").mkdir()
    (comic / "notes").mkdir()
    (comic / "notes" / "readme.txt").write_text("hi")

    code = main([str(comic)])

    assert code != 0
    assert "圖片" in capsys.readouterr().err
    assert not (comic.parent / "my-comic.epub").exists()


# --- 與其他功能的互動 ---------------------------------------------------------

def test_skip_broken_moves_a_chapter_to_its_first_readable_page(comic, capsys):
    make_image(comic / "ch1" / "1.jpg")
    (comic / "ch2" / "1.jpg").parent.mkdir()
    (comic / "ch2" / "1.jpg").write_bytes(b"garbage")
    make_image(comic / "ch2" / "2.jpg")

    book = build(comic, "--skip-broken")

    assert toc(book) == [("ch1", 1), ("ch2", 2)]
    assert "ch2/1.jpg" in capsys.readouterr().err


def test_skip_broken_drops_a_chapter_with_no_readable_page(comic, capsys):
    make_image(comic / "ch1" / "1.jpg")
    (comic / "ch2").mkdir()
    (comic / "ch2" / "1.jpg").write_bytes(b"garbage")

    book = build(comic, "--skip-broken")

    assert toc(book) == [("ch1", 1)]
    assert len(book.page_paths()) == 1


def test_broken_image_error_names_the_path_inside_the_chapter(comic, capsys):
    (comic / "ch1").mkdir()
    (comic / "ch1" / "7.jpg").write_bytes(b"garbage")

    code = main([str(comic)])

    assert code != 0
    assert "ch1/7.jpg" in capsys.readouterr().err


def test_chapters_work_with_spread_and_direction(comic):
    make_image(comic / "ch1" / "1.jpg")
    make_image(comic / "ch1" / "2.jpg")
    make_image(comic / "ch2" / "1.jpg")

    book = build(comic, "--spread", "--direction", "ltr")

    assert toc(book) == [("ch1", 1), ("ch2", 3)]


def test_input_folder_is_unchanged(comic):
    make_image(comic / "ch1" / "1.jpg")
    make_image(comic / "ch2" / "1.jpg")
    before = sorted((p.relative_to(comic).as_posix(), p.read_bytes())
                    for p in comic.rglob("*") if p.is_file())

    build(comic)

    assert sorted((p.relative_to(comic).as_posix(), p.read_bytes())
                  for p in comic.rglob("*") if p.is_file()) == before
