"""第一頁的版面尺寸要跟其餘頁面的比例一致（票 13）。

實機驗證：Apple Books 以第一頁的尺寸決定整本書的頁面比例。第一頁是接近正方形的封面、
其餘是直式頁面時，每次換頁都會先用錯的比例顯示、再縮回正確大小，畫面跳一下。
只要第一頁的比例跟其餘頁面一致就不會跳；其餘頁面彼此差幾個像素沒有影響。
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


def test_a_square_cover_gets_the_shape_of_the_rest_of_the_book(comic):
    make_pages(comic, BOOK_LIKE)

    run(comic)

    sizes = viewports(book(comic))
    # 其餘頁面寬度的中位數 1200、寬高比的中位數 1200/1720
    assert sizes[0] == (1200, 1720)
    assert sizes[1:] == BOOK_LIKE[1:]  # 其餘頁面維持自己的尺寸


def test_the_cover_image_is_scaled_to_fit_and_centered_without_distortion(comic):
    make_pages(comic, BOOK_LIKE)

    run(comic)

    epub = book(comic)
    first = epub.page_paths()[0]
    left, top, w, h = img_box(epub, first)
    vw, vh = epub.viewport(first)
    assert w == vw and h < vh  # 寬的封面放進直式版面：寬度填滿、上下留白
    assert abs(w / h - 1523 / 1469) < 0.002
    assert left == 0 and abs(top - (vh - h) // 2) <= 1
    css = re.search(r"html, body \{[^}]*width: (\d+)px; height: (\d+)px", epub.page_text(first))
    assert (int(css.group(1)), int(css.group(2))) == (vw, vh)


def test_image_bytes_and_cover_thumbnail_are_untouched(comic):
    originals = make_pages(comic, BOOK_LIKE)

    run(comic)

    epub = book(comic)
    assert epub.page_images() == originals
    cover = epub.cover_items()[0]
    assert epub.zip.read(epub.resolve(cover.get("href"))) == originals[0]


def test_a_first_page_that_already_matches_keeps_its_own_size(comic):
    sizes = [(1200, 1738), (1200, 1701), (1200, 1743), (1200, 1707)]
    make_pages(comic, sizes)

    run(comic)

    assert viewports(book(comic)) == sizes
    epub = book(comic)
    assert img_box(epub, epub.page_paths()[0]) == (0, 0, 1200, 1738)


def test_other_odd_pages_keep_their_own_size(comic):
    sizes = [(1200, 1738), (1200, 864), (1200, 1701), (1200, 2342), (1200, 1707)]
    make_pages(comic, sizes)

    run(comic)

    assert viewports(book(comic)) == sizes


def test_a_landscape_first_page_in_a_portrait_book_is_adjusted_too(comic):
    make_pages(comic, [(1200, 864), (1200, 1700), (1200, 1700)])

    run(comic)

    assert viewports(book(comic))[0] == (1200, 1700)


def test_a_portrait_cover_in_a_landscape_book_is_adjusted_too(comic):
    make_pages(comic, [(1000, 1500), (2000, 1000), (2000, 1000)])

    run(comic)

    epub = book(comic)
    assert viewports(epub)[0] == (2000, 1000)
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

    assert viewports(book(comic)) == [(600, 900), (600, 900), (600, 900)]


def test_works_with_an_external_cover_spread_and_chapters(comic, tmp_path):
    make_image(comic / "cover.jpg", size=(1523, 1469))
    for chapter in ("ch1", "ch2"):
        for n in (1, 2):
            make_image(comic / chapter / f"{n}.jpg", size=(1200, 1720), color=(n * 30, 5, 5))
    make_image(tmp_path / "front.png", size=(800, 800))

    assert run(comic, "--spread", "--direction", "ltr", "--cover", tmp_path / "front.png") == 0

    epub = book(comic)
    assert set(viewports(epub)) == {(1200, 1720)}
    assert [t for t, _ in epub.nav_links()] == ["ch1", "ch2"]
