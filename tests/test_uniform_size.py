"""--uniform-size：讓寬高比接近的頁面共用同一個版面尺寸，避免 Apple Books 換頁時重新調整高度。"""

import re

import pytest
from PIL import Image

from epubgen.cli import main
from tests.helpers import Epub, make_image


@pytest.fixture
def comic(tmp_path):
    folder = tmp_path / "comics" / "my-comic"
    folder.mkdir(parents=True)
    return folder


def run(*args):
    return main([str(a) for a in args])


def book(comic):
    return Epub(comic.parent / "my-comic.epub")


def viewports(epub):
    return [epub.viewport(p) for p in epub.page_paths()]


def img_box(epub, page):
    """回傳這頁 <img> 的 (left, top, width, height)；沒有位移時 left/top 是 0。"""
    css = re.search(r"img \{([^}]*)\}", epub.page_text(page)).group(1)

    def px(name, default=0):
        m = re.search(rf"{name}:\s*(-?\d+)px", css)
        return int(m.group(1)) if m else default

    return px("left"), px("top"), px("width"), px("height")


def make_pages(comic, sizes):
    for n, size in enumerate(sizes, start=1):
        make_image(comic / f"{n:02d}.jpg", size=size, color=(n * 10, 0, 0))


# --- 預設不變 -----------------------------------------------------------------

def test_without_the_option_every_page_keeps_its_own_viewport(comic):
    sizes = [(1200, 1701), (1200, 1738), (1190, 1720)]
    make_pages(comic, sizes)

    run(comic)

    assert viewports(book(comic)) == sizes


# --- 共用版面尺寸 -------------------------------------------------------------

def test_pages_with_similar_ratios_share_one_viewport(comic):
    make_pages(comic, [(1200, 1701), (1200, 1738), (1190, 1720), (1200, 1690), (1200, 1710)])

    assert run(comic, "--uniform-size") == 0

    epub = book(comic)
    assert len(set(viewports(epub))) == 1


def test_reference_is_the_median_width_and_median_aspect_ratio(comic):
    make_pages(comic, [(1000, 1500), (1000, 1500), (1100, 1650)])

    run(comic, "--uniform-size")

    assert viewports(book(comic)) == [(1000, 1500)] * 3


def test_every_page_declares_the_same_size_in_meta_and_css(comic):
    make_pages(comic, [(1200, 1701), (1200, 1738), (1190, 1720)])

    run(comic, "--uniform-size")

    epub = book(comic)
    for page in epub.page_paths():
        w, h = epub.viewport(page)
        css = re.search(r"html, body \{[^}]*width: (\d+)px; height: (\d+)px", epub.page_text(page))
        assert (int(css.group(1)), int(css.group(2))) == (w, h)


def test_images_are_scaled_to_fit_and_centered_without_distortion(comic):
    make_pages(comic, [(1000, 1500), (1000, 1500), (1000, 1560), (1040, 1500)])

    run(comic, "--uniform-size")

    epub = book(comic)
    ref_w, ref_h = viewports(epub)[0]
    for (iw, ih), page in zip([(1000, 1500), (1000, 1500), (1000, 1560), (1040, 1500)],
                              epub.page_paths()):
        left, top, w, h = img_box(epub, page)
        assert w <= ref_w and h <= ref_h
        assert (w == ref_w) or (h == ref_h)  # 至少一邊填滿
        assert abs(w / h - iw / ih) < 0.002  # 不變形
        assert abs(left - (ref_w - w) // 2) <= 1 and abs(top - (ref_h - h) // 2) <= 1


def test_image_bytes_are_never_resampled_by_this_option(comic):
    originals = [make_image(comic / f"{n}.jpg", size=(1000 + n * 5, 1500)) for n in (1, 2, 3)]

    run(comic, "--uniform-size")

    assert book(comic).page_images() == originals


def test_pages_with_very_different_ratios_keep_their_own_viewport(comic):
    make_pages(comic, [(1200, 1701), (1200, 1710), (1523, 1469), (1200, 1705), (2000, 1000)])

    run(comic, "--uniform-size")

    sizes = viewports(book(comic))
    assert sizes[2] == (1523, 1469)
    assert sizes[4] == (2000, 1000)
    assert len({sizes[0], sizes[1], sizes[3]}) == 1


def test_a_page_just_inside_the_tolerance_joins_and_one_just_outside_does_not(comic):
    # 參考寬高比 = 中位數 2/3；差 4% 的頁面共用，差 11% 的頁面各自保留
    make_pages(comic, [(1000, 1500), (1000, 1500), (1000, 1500), (1040, 1500), (1000, 1350)])

    run(comic, "--uniform-size")

    sizes = viewports(book(comic))
    assert sizes[:4] == [(1000, 1500)] * 4
    assert sizes[4] == (1000, 1350)


def test_a_single_page_book_uses_its_own_size(comic):
    make_pages(comic, [(640, 960)])

    run(comic, "--uniform-size")

    assert viewports(book(comic)) == [(640, 960)]


def test_pages_that_already_match_the_reference_have_no_offset(comic):
    make_pages(comic, [(1000, 1500), (1000, 1500), (1000, 1500)])

    run(comic, "--uniform-size")

    epub = book(comic)
    assert [img_box(epub, p) for p in epub.page_paths()] == [(0, 0, 1000, 1500)] * 3


# --- 與其他功能的互動 -----------------------------------------------------------

def test_reference_is_computed_from_the_processed_images(comic):
    make_pages(comic, [(2000, 3000), (2000, 3000), (2100, 3150)])

    run(comic, "--uniform-size", "--max-size", "1000")

    sizes = viewports(book(comic))
    assert sizes == [(667, 1000)] * 3


def test_chapters_spread_direction_and_cover_still_work(comic):
    for chapter in ("ch1", "ch2"):
        for n, size in enumerate([(1200, 1701), (1200, 1738)], start=1):
            make_image(comic / chapter / f"{n}.jpg", size=size, color=(n * 20, 9, 9))

    assert run(comic, "--uniform-size", "--spread", "--direction", "ltr") == 0

    epub = book(comic)
    assert len(set(viewports(epub))) == 1
    assert [t for t, _ in epub.nav_links()] == ["ch1", "ch2"]
    assert len(epub.cover_items()) == 1


def test_help_explains_the_option(capsys):
    with pytest.raises(SystemExit):
        main(["--help"])
    out = capsys.readouterr().out
    assert "--uniform-size" in out
    assert "Apple Books" in out
