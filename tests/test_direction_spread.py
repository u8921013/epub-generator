import pytest

from epubgen import build_epub
from epubgen.cli import main
from tests.helpers import Epub, make_image, spine_direction, spine_spread_properties


@pytest.fixture
def comic(tmp_path):
    folder = tmp_path / "my-comic"
    folder.mkdir()
    for n in range(1, 6):
        make_image(folder / f"{n}.jpg")
    return folder


def build(comic, *args):
    code = main([str(comic), *args])
    assert code == 0
    return Epub(comic.parent / "my-comic.epub")


def spread_roles(book):
    """把每頁的 spread 標記簡化成 left / right / none（沒有標記）。"""
    out = []
    for props in spine_spread_properties(book):
        roles = [p.removeprefix("page-spread-") for p in props if p.startswith("page-spread-")]
        out.append(roles[0] if roles else "none")
    return out


# --- 閱讀方向 -----------------------------------------------------------------

def test_comic_without_direction_defaults_to_right_to_left(comic):
    """CLI 不給 --direction 時是「未指定」，由建書流程替漫畫書套用 RTL。"""
    assert spine_direction(build(comic)) == "rtl"


def test_build_epub_with_default_options_makes_a_right_to_left_comic(comic):
    result = build_epub(comic)
    assert spine_direction(Epub(result.output)) == "rtl"


def test_direction_ltr_changes_page_progression(comic):
    assert spine_direction(build(comic, "--direction", "ltr")) == "ltr"


def test_direction_rtl_can_be_given_explicitly(comic):
    assert spine_direction(build(comic, "--direction", "rtl")) == "rtl"


def test_invalid_direction_shows_usage_and_fails(comic, capsys):
    with pytest.raises(SystemExit) as exc:
        main([str(comic), "--direction", "up"])

    captured = capsys.readouterr()
    assert exc.value.code != 0
    assert "usage" in captured.err.lower()
    assert "up" in captured.err
    assert not (comic.parent / "my-comic.epub").exists()


def test_direction_does_not_change_page_order(comic):
    rtl = build(comic)
    images_rtl = rtl.page_images()
    (comic.parent / "my-comic.epub").unlink()
    ltr = build(comic, "--direction", "ltr")
    assert ltr.page_images() == images_rtl


# --- 跨頁 ---------------------------------------------------------------------

def test_default_pages_are_not_merged_into_spreads(comic):
    book = build(comic)
    assert book.meta_property("rendition:spread") == "none"
    assert spread_roles(book) == ["none"] * 5


def test_spread_rtl_cover_unmarked_then_right_left_alternating(comic):
    book = build(comic, "--spread")
    assert book.meta_property("rendition:spread") != "none"
    assert spread_roles(book) == ["none", "right", "left", "right", "left"]


def test_spread_ltr_cover_unmarked_then_left_right_alternating(comic):
    book = build(comic, "--spread", "--direction", "ltr")
    assert spread_roles(book) == ["none", "left", "right", "left", "right"]


def test_spread_keeps_the_declared_direction(comic):
    assert spine_direction(build(comic, "--spread")) == "rtl"


def test_spread_with_a_single_page_book_has_no_left_or_right_mark(tmp_path):
    folder = tmp_path / "solo"
    folder.mkdir()
    make_image(folder / "1.jpg")
    assert main([str(folder), "--spread"]) == 0
    assert spread_roles(Epub(tmp_path / "solo.epub")) == ["none"]


def test_spread_does_not_change_page_order_or_viewports(comic):
    plain = build(comic)
    images = plain.page_images()
    viewports = [plain.viewport(p) for p in plain.page_paths()]
    (comic.parent / "my-comic.epub").unlink()
    spread = build(comic, "--spread")
    assert spread.page_images() == images
    assert [spread.viewport(p) for p in spread.page_paths()] == viewports


def test_help_lists_direction_and_spread_with_defaults(capsys):
    with pytest.raises(SystemExit):
        main(["--help"])
    out = capsys.readouterr().out
    assert "--direction" in out
    assert "rtl" in out and "ltr" in out
    assert "--spread" in out


def test_help_still_says_comics_default_to_right_to_left(capsys):
    with pytest.raises(SystemExit):
        main(["--help"])
    out = " ".join(capsys.readouterr().out.split())
    assert "漫畫書預設：rtl" in out
