"""每一頁的版面尺寸（票 13）。

實機驗證：Apple Books 以第一頁的形狀決定整本書的頁面比例。形狀跟第一頁不同的頁面，換頁時會先用
第一頁的比例顯示、再縮回自己的比例，畫面跳一下（差 1% 到 2% 也看得出來）。所以第一頁與形狀接近的
頁面共用同一個尺寸，形狀差很多的頁面（橫向跨頁、特別長的頁面）維持自己的尺寸。
"""

import re

import pytest

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


def make_pages(comic, sizes):
    return [make_image(comic / f"{n:02d}.jpg", size=size, color=(n * 9 % 256, 0, 0))
            for n, size in enumerate(sizes, start=1)]


def viewports(epub):
    return [epub.viewport(p) for p in epub.page_paths()]


def img_box(epub, page):
    """回傳這頁 <img> 的 (left, top, width, height)；沒有位移時 left/top 是 0。"""
    css = re.search(r"img \{([^}]*)\}", epub.page_text(page)).group(1)

    def px(name):
        m = re.search(rf"(?<![-\w]){name}:\s*(-?\d+)px", css)
        return int(m.group(1)) if m else 0

    return px("left"), px("top"), px("width"), px("height")


# 與使用者的書相同的形狀：接近正方形的封面，其餘是寬 1200、高度略有不同的直式頁面
BOOK_LIKE = [(1523, 1469), (1200, 1738), (1200, 1701), (1200, 1743), (1200, 1707), (1200, 1720)]


def test_the_cover_and_all_similar_pages_share_one_viewport(comic):
    make_pages(comic, BOOK_LIKE)

    run(comic)

    # 第一頁以外頁面寬度的中位數 1200、寬高比的中位數 1200/1720
    assert viewports(book(comic)) == [(1200, 1720)] * 6


def test_every_image_is_scaled_to_fit_and_centered_without_distortion(comic):
    make_pages(comic, BOOK_LIKE)

    run(comic)

    epub = book(comic)
    for (iw, ih), page in zip(BOOK_LIKE, epub.page_paths()):
        vw, vh = epub.viewport(page)
        left, top, w, h = img_box(epub, page)
        assert w <= vw and h <= vh
        assert w == vw or h == vh  # 至少一邊填滿
        assert abs(w / h - iw / ih) < 0.002  # 不變形
        assert abs(left - (vw - w) // 2) <= 1 and abs(top - (vh - h) // 2) <= 1
        css = re.search(r"html, body \{[^}]*width: (\d+)px; height: (\d+)px", epub.page_text(page))
        assert (int(css.group(1)), int(css.group(2))) == (vw, vh)


def test_the_square_cover_is_letterboxed_top_and_bottom(comic):
    make_pages(comic, BOOK_LIKE)

    run(comic)

    epub = book(comic)
    left, top, w, h = img_box(epub, epub.page_paths()[0])
    assert (left, w) == (0, 1200) and h < 1720 and top > 0


def test_image_bytes_and_cover_thumbnail_are_untouched(comic):
    originals = make_pages(comic, BOOK_LIKE)

    run(comic)

    epub = book(comic)
    assert epub.page_images() == originals
    cover = epub.cover_items()[0]
    assert epub.zip.read(epub.resolve(cover.get("href"))) == originals[0]


def test_pages_with_a_very_different_shape_keep_their_own_size(comic):
    make_pages(comic, [(1200, 1738), (1200, 864), (1200, 1701), (1200, 2342), (1200, 1707)])

    run(comic)

    reference = (1200, 1704)  # 第一頁以外寬高比的中位數 ≈ 0.7042
    assert viewports(book(comic)) == [reference, (1200, 864), reference, (1200, 2342), reference]


def test_a_page_just_inside_the_tolerance_joins_and_one_outside_does_not(comic):
    # 第一頁以外寬高比的中位數 2/3；差 4% 的頁面共用，差 11% 的頁面維持自己的尺寸
    make_pages(comic, [(1000, 1500)] * 4 + [(1040, 1500), (1000, 1350)])

    run(comic)

    assert viewports(book(comic)) == [(1000, 1500)] * 5 + [(1000, 1350)]


def test_identical_pages_have_no_offset(comic):
    make_pages(comic, [(1000, 1500)] * 3)

    run(comic)

    epub = book(comic)
    assert viewports(epub) == [(1000, 1500)] * 3
    assert [img_box(epub, p) for p in epub.page_paths()] == [(0, 0, 1000, 1500)] * 3


def test_a_landscape_first_page_in_a_portrait_book_is_adjusted(comic):
    make_pages(comic, [(1200, 864), (1200, 1700), (1200, 1700)])

    run(comic)

    assert viewports(book(comic)) == [(1200, 1700)] * 3


def test_a_portrait_cover_in_a_landscape_book_is_adjusted(comic):
    make_pages(comic, [(1000, 1500), (2000, 1000), (2000, 1000)])

    run(comic)

    epub = book(comic)
    assert viewports(epub) == [(2000, 1000)] * 3
    left, top, w, h = img_box(epub, epub.page_paths()[0])
    assert h == 1000 and w < 2000 and top == 0


def test_a_two_page_book_matches_the_first_page_to_the_second(comic):
    make_pages(comic, [(1523, 1469), (1200, 1738)])

    run(comic)

    assert viewports(book(comic)) == [(1200, 1738), (1200, 1738)]


def test_a_single_page_book_keeps_its_own_size(comic):
    make_pages(comic, [(1523, 1469)])

    run(comic)

    assert viewports(book(comic)) == [(1523, 1469)]


def test_the_shape_is_taken_from_the_processed_images(comic):
    make_pages(comic, [(3000, 3000), (2000, 3000), (2000, 3000)])

    run(comic, "--max-size", "900")

    assert viewports(book(comic)) == [(600, 900)] * 3


def test_works_with_an_external_cover_spread_and_chapters(comic, tmp_path):
    make_image(comic / "cover.jpg", size=(1523, 1469))
    for chapter in ("ch1", "ch2"):
        for n, height in ((1, 1701), (2, 1738)):
            make_image(comic / chapter / f"{n}.jpg", size=(1200, height), color=(n * 30, 5, 5))
    make_image(tmp_path / "front.png", size=(800, 800))

    assert run(comic, "--spread", "--direction", "ltr", "--cover", tmp_path / "front.png") == 0

    epub = book(comic)
    assert len(set(viewports(epub))) == 1
    assert [t for t, _ in epub.nav_links()] == ["ch1", "ch2"]
