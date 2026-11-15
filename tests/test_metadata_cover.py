import re

import pytest

from epubgen.cli import main
from tests.helpers import Epub, make_image

ILLEGAL = set('/\\:*?"<>|')


@pytest.fixture
def comic(tmp_path):
    folder = tmp_path / "comics" / "my-comic"
    folder.mkdir(parents=True)
    make_image(folder / "1.jpg", color=(10, 0, 0))
    make_image(folder / "2.jpg", color=(20, 0, 0))
    make_image(folder / "3.jpg", color=(30, 0, 0))
    return folder


def run(*args):
    return main([str(a) for a in args])


def epubs(comic):
    return sorted(comic.parent.glob("*.epub"))


def only_epub(comic):
    found = epubs(comic)
    assert len(found) == 1, found
    return Epub(found[0])


def cover_bytes(book):
    covers = book.cover_items()
    assert len(covers) == 1
    return book.zip.read(book.resolve(covers[0].get("href")))


# --- 書名 ---------------------------------------------------------------------

def test_title_option_overrides_metadata_and_default_file_name(comic, capsys):
    assert run(comic, "--title", "我的漫畫") == 0

    out_path = comic.parent / "我的漫畫.epub"
    assert out_path.is_file()
    assert str(out_path) in capsys.readouterr().out
    assert Epub(out_path).dc("title") == "我的漫畫"
    assert not (comic.parent / "my-comic.epub").exists()


def test_title_defaults_to_the_folder_name(comic):
    run(comic)
    assert only_epub(comic).dc("title") == "my-comic"


def test_title_is_also_used_for_the_navigation_entry_of_a_chapterless_book(comic):
    run(comic, "--title", "Custom")
    book = only_epub(comic)
    assert [text for text, _ in book.nav_links()] == ["Custom"]


def test_illegal_file_name_characters_are_replaced_only_in_the_file_name(comic, capsys):
    title = 'Vol: 1 / "Part" <A>? *|\\'

    assert run(comic, "--title", title) == 0

    book = only_epub(comic)
    assert not (ILLEGAL & set(book.path.name))
    assert book.path.name.endswith(".epub")
    assert book.dc("title") == title
    assert str(book.path) in capsys.readouterr().out


def test_title_made_only_of_illegal_characters_still_gets_a_file_name(comic):
    assert run(comic, "--title", "///") == 0
    book = only_epub(comic)
    assert book.path.stem != ""
    assert book.dc("title") == "///"


def test_output_option_wins_over_the_title_for_the_file_name(comic, tmp_path):
    target = tmp_path / "explicit.epub"

    run(comic, "--title", "Some Title", "-o", target)

    assert target.is_file()
    assert Epub(target).dc("title") == "Some Title"
    assert epubs(comic) == []


def test_empty_title_is_an_error(comic, capsys):
    code = run(comic, "--title", "   ")

    assert code != 0
    assert capsys.readouterr().err.strip() != ""
    assert epubs(comic) == []


def test_metadata_is_xml_escaped(comic):
    run(comic, "--title", "A & B <x>", "--author", "Foo & <Bar>")
    book = only_epub(comic)
    assert book.dc("title") == "A & B <x>"
    assert book.dc("creator") == "Foo & <Bar>"


# --- 作者與語言 ---------------------------------------------------------------

def test_author_is_written_to_metadata(comic):
    run(comic, "--author", "手塚治虫")
    assert only_epub(comic).dc("creator") == "手塚治虫"


def test_no_author_means_no_creator_element(comic):
    run(comic)
    assert only_epub(comic).dc("creator") is None


def test_language_is_written_to_metadata(comic):
    run(comic, "--language", "ja")
    assert only_epub(comic).dc("language") == "ja"


def test_language_defaults_to_zh_tw(comic):
    run(comic)
    assert only_epub(comic).dc("language") == "zh-TW"


def test_language_is_used_by_the_navigation_document(comic):
    run(comic, "--language", "en-US")
    book = only_epub(comic)
    nav = next(i for i in book.manifest().values()
               if "nav" in (i.get("properties") or "").split())
    text = book.zip.read(book.resolve(nav.get("href"))).decode()
    assert re.search(r'lang="en-US"', text)


@pytest.mark.parametrize("bad", ["", "中文", "e n", "x"])
def test_invalid_language_shows_usage_and_fails(comic, capsys, bad):
    with pytest.raises(SystemExit) as exc:
        run(comic, "--language", bad)

    assert exc.value.code != 0
    assert "usage" in capsys.readouterr().err.lower()
    assert epubs(comic) == []


# --- 封面 ---------------------------------------------------------------------

def test_cover_pointing_at_a_page_marks_that_page_without_duplicating_it(comic):
    original = [(comic / n).read_bytes() for n in ("1.jpg", "2.jpg", "3.jpg")]

    run(comic, "--cover", comic / "2.jpg")

    book = only_epub(comic)
    assert cover_bytes(book) == original[1]
    assert book.page_images() == original
    assert len(book.page_paths()) == 3
    images = [n for n in book.zip.namelist() if "/images/" in n]
    assert len(images) == 3


def test_cover_outside_the_folder_is_added_once_and_pages_are_unchanged(comic, tmp_path):
    original = [(comic / n).read_bytes() for n in ("1.jpg", "2.jpg", "3.jpg")]
    outside = tmp_path / "elsewhere" / "front.png"
    front = make_image(outside, size=(300, 400), color=(0, 99, 0))

    run(comic, "--cover", outside)

    book = only_epub(comic)
    assert cover_bytes(book) == front
    assert book.page_images() == original
    assert len(book.page_paths()) == 3
    # 封面圖不屬於 spine
    cover_item = book.cover_items()[0]
    spine_ids = [i.get("id") for i in book.spine_items()]
    assert cover_item.get("id") not in spine_ids
    assert cover_item.get("media-type") == "image/png"


def test_cover_given_as_a_relative_path_is_resolved_from_the_working_directory(
        comic, tmp_path, monkeypatch):
    front = make_image(tmp_path / "front.jpg", color=(1, 2, 3))
    monkeypatch.chdir(tmp_path)

    run(comic, "--cover", "front.jpg")

    assert cover_bytes(only_epub(comic)) == front


def test_cover_can_be_an_image_inside_a_chapter(tmp_path):
    folder = tmp_path / "my-comic"
    make_image(folder / "ch1" / "1.jpg", color=(1, 0, 0))
    wanted = make_image(folder / "ch2" / "1.jpg", color=(2, 0, 0))

    run(folder, "--cover", folder / "ch2" / "1.jpg")

    book = Epub(tmp_path / "my-comic.epub")
    assert cover_bytes(book) == wanted
    assert len(book.page_paths()) == 2


def test_cover_pointing_at_a_page_works_with_skip_broken(comic):
    (comic / "1.jpg").write_bytes(b"garbage")
    wanted = (comic / "3.jpg").read_bytes()

    run(comic, "--skip-broken", "--cover", comic / "3.jpg")

    assert cover_bytes(only_epub(comic)) == wanted


def test_default_cover_is_still_the_first_page(comic):
    run(comic)
    assert cover_bytes(only_epub(comic)) == (comic / "1.jpg").read_bytes()


def test_missing_cover_is_an_error_and_makes_no_book(comic, tmp_path, capsys):
    missing = tmp_path / "nope.jpg"

    code = run(comic, "--cover", missing)

    err = capsys.readouterr().err
    assert code != 0
    assert str(missing) in err
    assert epubs(comic) == []


def test_cover_that_is_not_an_image_file_is_an_error(comic, tmp_path, capsys):
    notes = tmp_path / "notes.txt"
    notes.write_text("hello")

    code = run(comic, "--cover", notes)

    assert code != 0
    assert capsys.readouterr().err.strip() != ""
    assert epubs(comic) == []


def test_unreadable_cover_is_an_error_even_with_skip_broken(comic, tmp_path, capsys):
    bad = tmp_path / "bad.jpg"
    bad.write_bytes(b"garbage")

    code = run(comic, "--skip-broken", "--cover", bad)

    assert code != 0
    assert str(bad.name) in capsys.readouterr().err
    assert epubs(comic) == []


def test_cover_that_is_a_folder_is_an_error(comic, tmp_path, capsys):
    code = run(comic, "--cover", tmp_path)

    assert code != 0
    assert capsys.readouterr().err.strip() != ""


def test_input_folder_is_unchanged(comic, tmp_path):
    outside = tmp_path / "front.jpg"
    make_image(outside)
    before = sorted((p.name, p.read_bytes()) for p in comic.iterdir())

    run(comic, "--title", "T", "--author", "A", "--language", "ja", "--cover", outside)

    assert sorted((p.name, p.read_bytes()) for p in comic.iterdir()) == before


def test_help_lists_the_new_options(capsys):
    with pytest.raises(SystemExit):
        main(["--help"])
    out = capsys.readouterr().out
    for option in ("--title", "--author", "--language", "--cover"):
        assert option in out
    assert "zh-TW" in out
