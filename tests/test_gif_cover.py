"""Kobo 不支援 GIF 封面（票 07），所以封面是 GIF 時另外產生 JPEG 封面。頁面內容不變。"""

import io

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


def decode(data):
    img = Image.open(io.BytesIO(data))
    img.load()
    return img


def cover_of(epub):
    covers = epub.cover_items()
    assert len(covers) == 1
    item = covers[0]
    return item, epub.zip.read(epub.resolve(item.get("href")))


def assert_jpeg_cover_outside_the_spine(epub):
    item, data = cover_of(epub)
    assert item.get("media-type") == "image/jpeg"
    assert item.get("href").endswith(".jpg")
    assert decode(data).format == "JPEG"
    assert item.get("id") not in [i.get("id") for i in epub.spine_items()]
    return data


def test_first_image_being_a_gif_gets_a_jpeg_cover_and_pages_stay_untouched(comic):
    gif = make_image(comic / "1.gif", size=(60, 90), color=(10, 200, 10))
    other = make_image(comic / "2.jpg")

    assert run(comic) == 0

    epub = book(comic)
    cover = assert_jpeg_cover_outside_the_spine(epub)
    assert decode(cover).size == (60, 90)
    assert epub.page_images() == [gif, other]  # 頁面維持原始 GIF 位元組
    assert len(epub.page_paths()) == 2
    # 沒有任何頁面圖片被標成封面
    page_image_paths = {epub.page_image_path(p) for p in epub.page_paths()}
    assert epub.resolve(epub.cover_items()[0].get("href")) not in page_image_paths


def test_cover_option_pointing_at_a_gif_page_gets_a_jpeg_cover(comic):
    make_image(comic / "1.jpg")
    gif = make_image(comic / "2.gif")

    run(comic, "--cover", comic / "2.gif")

    epub = book(comic)
    assert_jpeg_cover_outside_the_spine(epub)
    assert epub.page_images()[1] == gif


def test_external_gif_cover_is_converted_to_jpeg(comic, tmp_path):
    originals = [make_image(comic / "1.jpg"), make_image(comic / "2.jpg")]
    make_image(tmp_path / "front.gif", size=(50, 70))

    run(comic, "--cover", tmp_path / "front.gif")

    epub = book(comic)
    cover = assert_jpeg_cover_outside_the_spine(epub)
    assert decode(cover).size == (50, 70)
    assert epub.page_images() == originals


def test_transparent_gif_cover_gets_a_white_background(comic):
    img = Image.new("P", (30, 30), 0)
    img.putpalette([0, 0, 0, 255, 0, 0] + [0] * 762)
    img.info["transparency"] = 0
    for x in range(15):
        for y in range(30):
            img.putpixel((x, y), 1)  # 左半紅色，右半透明
    img.save(comic / "1.gif", transparency=0)

    run(comic)

    cover = decode(cover_of(book(comic))[1]).convert("RGB")
    assert min(cover.getpixel((25, 15))) >= 250
    r, g, b = cover.getpixel((5, 15))
    assert r > 200 and g < 60 and b < 60


def test_animated_gif_uses_its_first_frame_for_the_cover_only(comic):
    frames = [Image.new("RGB", (40, 40), c) for c in ((250, 0, 0), (0, 250, 0))]
    frames[0].save(comic / "1.gif", save_all=True, append_images=frames[1:], duration=100, loop=0)
    original = (comic / "1.gif").read_bytes()

    run(comic)

    epub = book(comic)
    r, g, b = decode(cover_of(epub)[1]).convert("RGB").getpixel((20, 20))
    assert r > 200 and g < 60
    assert epub.page_images() == [original]


def test_gif_that_is_not_the_cover_changes_nothing(comic):
    make_image(comic / "1.jpg")
    gif = make_image(comic / "2.gif")

    run(comic)

    epub = book(comic)
    item, data = cover_of(epub)
    assert item.get("media-type") == "image/jpeg"
    assert data == epub.page_images()[0]  # 封面仍是第一頁本身，沒有多餘的圖
    assert epub.page_images()[1] == gif
    assert len([n for n in epub.zip.namelist() if "/images/" in n]) == 2


def test_broken_gif_first_page_is_skipped_and_the_next_page_is_the_cover(comic):
    (comic / "1.gif").write_bytes(b"GIF89agarbage")
    good = make_image(comic / "2.jpg")

    run(comic, "--skip-broken")

    epub = book(comic)
    assert cover_of(epub)[1] == good


def test_input_files_are_not_modified(comic):
    gif = make_image(comic / "1.gif")

    run(comic)

    assert (comic / "1.gif").read_bytes() == gif
    assert sorted(p.name for p in comic.iterdir()) == ["1.gif"]
