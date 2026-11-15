import os

import pytest
from PIL import Image

from epubgen.cli import main
from tests.helpers import Epub, make_image


@pytest.fixture
def comic(tmp_path):
    folder = tmp_path / "my-comic"
    folder.mkdir()
    return folder


def run(*args):
    return main([str(a) for a in args])


def default_output(comic):
    return comic.parent / "my-comic.epub"


def make_truncated_jpeg(path):
    """產生一張檔頭正常、但資料被截斷的 JPEG。"""
    img = Image.frombytes("RGB", (200, 200), os.urandom(200 * 200 * 3))
    img.save(path, "JPEG")
    data = path.read_bytes()
    path.write_bytes(data[: len(data) // 2])


def assert_failed_cleanly(code, capsys, tmp_path, *, mentions=()):
    captured = capsys.readouterr()
    assert code != 0
    assert captured.out == ""
    assert captured.err.strip() != ""
    for text in mentions:
        assert text in captured.err
    assert not list(tmp_path.glob("*.epub*"))


# --- 輸入路徑 -----------------------------------------------------------------

def test_missing_input_path_names_the_path(tmp_path, capsys):
    missing = tmp_path / "nope"

    code = run(missing)

    assert_failed_cleanly(code, capsys, tmp_path, mentions=[str(missing)])


def test_input_path_that_is_a_file_is_explained(tmp_path, capsys):
    not_a_folder = tmp_path / "1.jpg"
    make_image(not_a_folder)

    code = run(not_a_folder)

    assert_failed_cleanly(code, capsys, tmp_path, mentions=["資料夾"])


def test_missing_and_file_inputs_get_different_messages(tmp_path, capsys):
    run(tmp_path / "nope")
    missing_msg = capsys.readouterr().err
    f = tmp_path / "file.txt"
    f.write_text("x")
    run(f)
    file_msg = capsys.readouterr().err
    assert missing_msg != file_msg


# --- 沒有可用圖片 -------------------------------------------------------------

def test_empty_folder_is_an_error_and_makes_no_book(comic, capsys, tmp_path):
    code = run(comic)
    assert_failed_cleanly(code, capsys, tmp_path, mentions=["圖片"])


def test_folder_with_only_non_images_is_an_error(comic, capsys, tmp_path):
    (comic / "notes.txt").write_text("hello")
    (comic / ".DS_Store").write_bytes(b"junk")

    code = run(comic)

    assert_failed_cleanly(code, capsys, tmp_path, mentions=["圖片"])


# --- 損毀圖片 -----------------------------------------------------------------

def test_broken_image_is_an_error_naming_the_file(comic, capsys, tmp_path):
    make_image(comic / "1.jpg")
    (comic / "2.jpg").write_bytes(b"this is not an image")
    make_image(comic / "3.jpg")

    code = run(comic)

    assert_failed_cleanly(code, capsys, tmp_path, mentions=["2.jpg"])


def test_error_for_broken_image_hints_at_skip_broken(comic, capsys):
    (comic / "1.jpg").write_bytes(b"garbage")

    run(comic)

    assert "--skip-broken" in capsys.readouterr().err


def test_truncated_image_counts_as_broken(comic, capsys, tmp_path):
    make_image(comic / "1.jpg")
    make_truncated_jpeg(comic / "2.jpg")

    code = run(comic)

    assert_failed_cleanly(code, capsys, tmp_path, mentions=["2.jpg"])


def test_broken_image_does_not_overwrite_an_existing_output_even_with_force(comic, capsys):
    (comic / "1.jpg").write_bytes(b"garbage")
    out = default_output(comic)
    out.write_bytes(b"precious")

    code = run(comic, "--force")

    assert code != 0
    assert out.read_bytes() == b"precious"


def test_skip_broken_leaves_out_broken_images_and_lists_them(comic, capsys):
    originals = [make_image(comic / "1.jpg", color=(1, 1, 1)),
                 None,
                 make_image(comic / "3.jpg", color=(3, 3, 3))]
    (comic / "2.jpg").write_bytes(b"garbage")
    make_truncated_jpeg(comic / "4.jpg")

    code = run(comic, "--skip-broken")

    captured = capsys.readouterr()
    assert code == 0
    book = Epub(default_output(comic))
    assert book.page_images() == [originals[0], originals[2]]
    assert "2" in captured.out  # 頁數
    assert str(default_output(comic)) in captured.out
    assert "2.jpg" in captured.err
    assert "4.jpg" in captured.err
    assert "1.jpg" not in captured.err
    assert "3.jpg" not in captured.err


def test_skip_broken_without_broken_images_reports_nothing_skipped(comic, capsys):
    make_image(comic / "1.jpg")

    code = run(comic, "--skip-broken")

    captured = capsys.readouterr()
    assert code == 0
    assert captured.err == ""


def test_skip_broken_takes_the_first_good_image_as_cover(comic):
    (comic / "1.jpg").write_bytes(b"garbage")
    good = make_image(comic / "2.jpg")

    run(comic, "--skip-broken")

    book = Epub(default_output(comic))
    covers = book.cover_items()
    assert len(covers) == 1
    assert book.zip.read(book.resolve(covers[0].get("href"))) == good


def test_all_images_broken_with_skip_broken_is_an_error(comic, capsys, tmp_path):
    (comic / "1.jpg").write_bytes(b"garbage")
    (comic / "2.png").write_bytes(b"garbage")

    code = run(comic, "--skip-broken")

    assert_failed_cleanly(code, capsys, tmp_path, mentions=["1.jpg", "2.png"])


def test_failures_do_not_modify_the_input_folder(comic):
    make_image(comic / "1.jpg")
    (comic / "2.jpg").write_bytes(b"garbage")
    before = sorted((p.name, p.read_bytes()) for p in comic.iterdir())

    run(comic)
    run(comic, "--skip-broken")

    assert sorted((p.name, p.read_bytes()) for p in comic.iterdir()) == before


def test_help_lists_skip_broken(capsys):
    with pytest.raises(SystemExit):
        main(["--help"])
    assert "--skip-broken" in capsys.readouterr().out


# --- 不合法的參數 -------------------------------------------------------------

def test_unknown_option_shows_usage_and_fails(comic, capsys):
    make_image(comic / "1.jpg")

    with pytest.raises(SystemExit) as exc:
        run(comic, "--bogus")

    captured = capsys.readouterr()
    assert exc.value.code != 0
    assert "usage" in captured.err.lower()
    assert captured.out == ""
    assert not default_output(comic).exists()


def test_missing_input_argument_shows_usage_and_fails(capsys):
    with pytest.raises(SystemExit) as exc:
        main([])

    assert exc.value.code != 0
    assert "usage" in capsys.readouterr().err.lower()


def test_option_missing_its_value_shows_usage_and_fails(comic, capsys):
    make_image(comic / "1.jpg")

    with pytest.raises(SystemExit) as exc:
        run(comic, "-o")

    assert exc.value.code != 0
    assert "usage" in capsys.readouterr().err.lower()
