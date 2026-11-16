import re
import zipfile

import pytest

from epubgen.cli import main
from tests.helpers import Epub, make_image


@pytest.fixture
def comic(tmp_path):
    folder = tmp_path / "my-comic"
    folder.mkdir()
    return folder


def run(*args):
    return main([str(a) for a in args])


def test_generates_epub_next_to_input_and_reports_path_and_pages(comic, capsys):
    for n in (1, 2, 3):
        make_image(comic / f"{n}.jpg")

    code = run(comic)

    out = capsys.readouterr().out
    epub_path = comic.parent / "my-comic.epub"
    assert code == 0
    assert epub_path.is_file()
    assert str(epub_path) in out
    assert "3" in out


def test_mimetype_is_first_entry_and_stored(comic):
    make_image(comic / "1.jpg")
    run(comic)

    with zipfile.ZipFile(comic.parent / "my-comic.epub") as z:
        first = z.infolist()[0]
        assert first.filename == "mimetype"
        assert first.compress_type == zipfile.ZIP_STORED
        assert z.read("mimetype") == b"application/epub+zip"


def test_package_declares_fixed_layout_and_required_metadata(comic):
    make_image(comic / "1.jpg")
    run(comic)

    book = Epub(comic.parent / "my-comic.epub")
    assert book.meta_property("rendition:layout") == "pre-paginated"
    assert book.dc("title") == "my-comic"
    assert book.dc("language") == "zh-TW"
    assert book.dc("identifier")
    assert re.match(r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ$", book.meta_property("dcterms:modified"))


def test_each_book_gets_a_unique_identifier(comic):
    make_image(comic / "1.jpg")
    run(comic)
    first = Epub(comic.parent / "my-comic.epub").dc("identifier")
    (comic.parent / "my-comic.epub").unlink()
    run(comic)
    assert Epub(comic.parent / "my-comic.epub").dc("identifier") != first


def test_one_page_per_image_in_natural_order(comic):
    originals = {n: make_image(comic / f"{n}.jpg", color=(n * 10, 0, 0)) for n in (1, 2, 10)}
    run(comic)

    book = Epub(comic.parent / "my-comic.epub")
    assert book.page_images() == [originals[1], originals[2], originals[10]]


def test_each_page_viewport_matches_its_image_size(comic):
    make_image(comic / "1.jpg", size=(300, 500))
    make_image(comic / "2.png", size=(120, 80))
    run(comic)

    book = Epub(comic.parent / "my-comic.epub")
    pages = book.page_paths()
    assert book.viewport(pages[0]) == (300, 500)
    assert book.viewport(pages[1]) == (120, 80)


def test_image_bytes_are_packaged_unchanged_for_every_supported_format(comic):
    originals = [make_image(comic / name) for name in
                 ("1.jpg", "2.JPEG", "3.png", "4.webp", "5.gif")]
    run(comic, "--keep-webp")  # WebP 預設會轉成 JPEG，保留原檔要明確要求（票 08）

    book = Epub(comic.parent / "my-comic.epub")
    assert book.page_images() == originals


def test_non_image_files_are_ignored(comic, capsys):
    make_image(comic / "1.jpg")
    (comic / ".DS_Store").write_bytes(b"junk")
    (comic / "notes.txt").write_text("hello")
    run(comic)

    book = Epub(comic.parent / "my-comic.epub")
    assert len(book.page_paths()) == 1
    assert not any(n.endswith((".txt",)) or "DS_Store" in n for n in book.zip.namelist())


def test_first_image_is_the_cover(comic):
    make_image(comic / "1.jpg", color=(1, 2, 3))
    make_image(comic / "2.jpg", color=(9, 9, 9))
    run(comic)

    book = Epub(comic.parent / "my-comic.epub")
    covers = book.cover_items()
    assert len(covers) == 1
    assert book.zip.read(book.resolve(covers[0].get("href"))) == book.page_images()[0]


def test_navigation_document_has_an_entry_for_the_first_page(comic):
    make_image(comic / "1.jpg")
    make_image(comic / "2.jpg")
    run(comic)

    book = Epub(comic.parent / "my-comic.epub")
    links = book.nav_links()
    assert [path for _, path in links] == [book.page_paths()[0]]


def test_works_when_input_is_given_as_a_relative_path(comic, monkeypatch):
    make_image(comic / "1.jpg")
    monkeypatch.chdir(comic)
    code = run(".")

    assert code == 0
    assert (comic.parent / "my-comic.epub").is_file()


def test_input_folder_is_not_modified(comic):
    make_image(comic / "1.jpg")
    before = sorted((p.name, p.read_bytes()) for p in comic.iterdir())
    run(comic)
    assert sorted((p.name, p.read_bytes()) for p in comic.iterdir()) == before


def test_help_lists_usage(capsys):
    with pytest.raises(SystemExit) as exc:
        main(["--help"])
    assert exc.value.code == 0
    assert "epubgen" in capsys.readouterr().out


def test_version_prints_version(capsys):
    with pytest.raises(SystemExit) as exc:
        main(["--version"])
    assert exc.value.code == 0
    assert re.search(r"epubgen \d+\.\d+\.\d+", capsys.readouterr().out)
