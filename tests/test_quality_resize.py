import io
import os

import pytest
from PIL import Image

from epubgen.cli import main
from tests.helpers import Epub


@pytest.fixture
def comic(tmp_path):
    folder = tmp_path / "comics" / "my-comic"
    folder.mkdir(parents=True)
    return folder


def run(*args):
    return main([str(a) for a in args])


def book(comic):
    return Epub(comic.parent / "my-comic.epub")


def noise(size, mode="RGB"):
    channels = len(mode)
    return Image.frombytes(mode, size, os.urandom(size[0] * size[1] * channels))


def save(path, img, fmt, **kwargs):
    path.parent.mkdir(parents=True, exist_ok=True)
    img.save(path, fmt, **kwargs)
    return path.read_bytes()


def decode(data):
    img = Image.open(io.BytesIO(data))
    img.load()
    return img


def media_types(epub):
    types = []
    for page in epub.page_paths():
        path = epub.page_image_path(page)
        item = next(i for i in epub.manifest().values() if epub.resolve(i.get("href")) == path)
        types.append(item.get("media-type"))
    return types


def page_size(epub, index=0):
    page = epub.page_paths()[index]
    img = decode(epub.zip.read(epub.page_image_path(page)))
    assert epub.viewport(page) == img.size  # viewport 一律等於最終圖片尺寸
    return img.size


def usage_error(capsys, *args):
    with pytest.raises(SystemExit) as exc:
        run(*args)
    assert exc.value.code != 0
    assert "usage" in capsys.readouterr().err.lower()


# --- 沒給參數：不動原圖 ---------------------------------------------------------

def test_without_the_options_every_non_webp_image_is_untouched(comic):
    originals = [
        save(comic / "1.jpg", noise((120, 180)), "JPEG", quality=90),
        save(comic / "2.png", noise((120, 180)), "PNG"),
        save(comic / "3.gif", noise((60, 90)).convert("P"), "GIF"),
    ]

    run(comic)

    assert book(comic).page_images() == originals


# --- --quality ------------------------------------------------------------------

def test_quality_recompresses_a_jpeg_to_a_smaller_file(comic):
    original = save(comic / "1.jpg", noise((300, 400)), "JPEG", quality=95)

    assert run(comic, "--quality", "30") == 0

    epub = book(comic)
    data = epub.page_images()[0]
    assert len(data) < len(original)
    assert decode(data).format == "JPEG"
    assert page_size(epub) == (300, 400)


def test_lower_quality_gives_a_smaller_file(comic, tmp_path):
    save(comic / "1.jpg", noise((300, 400)), "JPEG", quality=100)
    run(comic, "--quality", "85", "-o", tmp_path / "high.epub")
    run(comic, "--quality", "20", "-o", tmp_path / "low.epub")

    high = len(Epub(tmp_path / "high.epub").page_images()[0])
    low = len(Epub(tmp_path / "low.epub").page_images()[0])
    assert low < high


def test_quality_turns_a_png_into_a_smaller_jpeg(comic):
    original = save(comic / "1.png", noise((250, 350)), "PNG")

    run(comic, "--quality", "50")

    epub = book(comic)
    assert media_types(epub) == ["image/jpeg"]
    assert len(epub.page_images()[0]) < len(original)
    assert page_size(epub) == (250, 350)


def test_quality_flattens_a_transparent_png_onto_white(comic):
    save(comic / "1.png", Image.new("RGBA", (40, 40), (0, 0, 0, 0)), "PNG")

    run(comic, "--quality", "80")

    pixel = decode(book(comic).page_images()[0]).convert("RGB").getpixel((20, 20))
    assert min(pixel) >= 250


def test_quality_leaves_gifs_alone(comic):
    gif = save(comic / "1.gif", noise((60, 90)).convert("P"), "GIF")

    run(comic, "--quality", "20")

    assert book(comic).page_images() == [gif]


def test_quality_also_applies_to_the_default_webp_to_jpeg_conversion(comic, tmp_path):
    save(comic / "1.webp", noise((300, 400)), "WEBP", lossless=True)
    run(comic, "-o", tmp_path / "default.epub")
    run(comic, "--quality", "20", "-o", tmp_path / "low.epub")

    default = Epub(tmp_path / "default.epub")
    low = Epub(tmp_path / "low.epub")
    assert media_types(low) == ["image/jpeg"]
    assert len(low.page_images()[0]) < len(default.page_images()[0])


def test_quality_with_keep_webp_recompresses_the_webp_as_webp(comic):
    original = save(comic / "1.webp", noise((300, 400)), "WEBP", lossless=True)

    run(comic, "--keep-webp", "--quality", "30")

    epub = book(comic)
    assert media_types(epub) == ["image/webp"]
    assert decode(epub.page_images()[0]).format == "WEBP"
    assert len(epub.page_images()[0]) < len(original)


def test_a_recompressed_jpeg_that_would_get_bigger_is_left_as_it_was(comic):
    original = save(comic / "1.jpg", noise((300, 400)), "JPEG", quality=30)

    run(comic, "--quality", "95")

    assert book(comic).page_images() == [original]


@pytest.mark.parametrize("bad", ["0", "101", "-5", "abc", "50.5", ""])
def test_invalid_quality_shows_usage_and_fails(comic, capsys, bad):
    save(comic / "1.jpg", noise((40, 40)), "JPEG")

    usage_error(capsys, comic, "--quality", bad)

    assert not (comic.parent / "my-comic.epub").exists()


# --- --max-size -----------------------------------------------------------------

def test_a_portrait_image_is_scaled_so_its_long_side_matches_the_limit(comic):
    save(comic / "1.jpg", noise((1000, 1500)), "JPEG")

    assert run(comic, "--max-size", "600") == 0

    assert page_size(book(comic)) == (400, 600)


def test_a_landscape_image_is_scaled_the_same_way(comic):
    save(comic / "1.jpg", noise((1500, 1000)), "JPEG")

    run(comic, "--max-size", "600")

    assert page_size(book(comic)) == (600, 400)


def test_images_within_the_limit_are_not_touched_or_enlarged(comic):
    small = save(comic / "1.jpg", noise((300, 400)), "JPEG")
    exact = save(comic / "2.png", noise((300, 400)), "PNG")

    run(comic, "--max-size", "400")

    epub = book(comic)
    assert epub.page_images() == [small, exact]
    assert page_size(epub, 0) == (300, 400)


def test_extreme_aspect_ratios_never_shrink_to_zero_pixels(comic):
    save(comic / "1.png", noise((3000, 3)), "PNG")

    run(comic, "--max-size", "100")

    width, height = page_size(book(comic))
    assert width == 100 and height >= 1


def test_each_page_gets_its_own_viewport(comic):
    save(comic / "1.jpg", noise((1000, 1500)), "JPEG")
    save(comic / "2.jpg", noise((1600, 800)), "JPEG")
    save(comic / "3.jpg", noise((100, 200)), "JPEG")

    run(comic, "--max-size", "500")

    epub = book(comic)
    assert [page_size(epub, i) for i in range(3)] == [(333, 500), (500, 250), (100, 200)]


def test_resizing_keeps_each_format_where_it_makes_sense(comic):
    save(comic / "1.jpg", noise((800, 1000)), "JPEG")
    save(comic / "2.png", noise((800, 1000)), "PNG")
    save(comic / "3.gif", noise((800, 1000)).convert("P"), "GIF")
    save(comic / "4.webp", noise((800, 1000)), "WEBP")

    run(comic, "--max-size", "400")

    epub = book(comic)
    assert media_types(epub) == ["image/jpeg", "image/png", "image/jpeg", "image/jpeg"]
    assert [page_size(epub, i) for i in range(4)] == [(320, 400)] * 4


def test_resizing_a_kept_webp_stays_webp(comic):
    save(comic / "1.webp", noise((800, 1000)), "WEBP")

    run(comic, "--keep-webp", "--max-size", "400")

    epub = book(comic)
    assert media_types(epub) == ["image/webp"]
    assert page_size(epub) == (320, 400)


def test_resizing_shrinks_the_file(comic):
    original = save(comic / "1.jpg", noise((1000, 1500)), "JPEG", quality=90)

    run(comic, "--max-size", "500")

    assert len(book(comic).page_images()[0]) < len(original)


def test_quality_and_max_size_work_together(comic):
    save(comic / "1.png", noise((800, 1000)), "PNG")
    save(comic / "2.webp", noise((800, 1000)), "WEBP")

    run(comic, "--quality", "40", "--max-size", "400")

    epub = book(comic)
    assert media_types(epub) == ["image/jpeg", "image/jpeg"]
    assert [page_size(epub, i) for i in range(2)] == [(320, 400)] * 2


@pytest.mark.parametrize("bad", ["0", "-1", "abc", "1.5", ""])
def test_invalid_max_size_shows_usage_and_fails(comic, capsys, bad):
    save(comic / "1.jpg", noise((40, 40)), "JPEG")

    usage_error(capsys, comic, "--max-size", bad)

    assert not (comic.parent / "my-comic.epub").exists()


# --- 封面與其他互動 -----------------------------------------------------------------

def test_a_resized_cover_page_is_the_cover_image(comic):
    save(comic / "1.jpg", noise((1000, 1500)), "JPEG")
    save(comic / "2.jpg", noise((100, 150)), "JPEG")

    run(comic, "--max-size", "300")

    epub = book(comic)
    covers = epub.cover_items()
    assert len(covers) == 1
    assert epub.zip.read(epub.resolve(covers[0].get("href"))) == epub.page_images()[0]
    assert page_size(epub) == (200, 300)


def test_an_external_cover_is_processed_too(comic, tmp_path):
    save(comic / "1.jpg", noise((100, 150)), "JPEG")
    save(tmp_path / "front.png", noise((900, 1200)), "PNG")

    run(comic, "--cover", tmp_path / "front.png", "--max-size", "300")

    epub = book(comic)
    cover = epub.cover_items()[0]
    assert decode(epub.zip.read(epub.resolve(cover.get("href")))).size == (225, 300)


def test_a_gif_cover_stays_a_jpeg_cover_with_the_page_untouched(comic):
    gif = save(comic / "1.gif", noise((60, 90)).convert("P"), "GIF")

    run(comic, "--quality", "50", "--max-size", "400")

    epub = book(comic)
    assert epub.page_images() == [gif]
    assert epub.cover_items()[0].get("media-type") == "image/jpeg"


def test_exif_orientation_is_applied_when_an_image_is_reprocessed(comic):
    exif = Image.Exif()
    exif[0x0112] = 6  # 需要順時針轉 90 度
    save(comic / "1.jpg", noise((300, 200)), "JPEG", exif=exif)

    run(comic, "--quality", "40")

    assert page_size(book(comic)) == (200, 300)


def test_chapters_skip_broken_and_direction_still_work(comic):
    save(comic / "ch1" / "1.jpg", noise((600, 800)), "JPEG")
    (comic / "ch1" / "2.jpg").write_bytes(b"garbage")
    save(comic / "ch2" / "1.png", noise((600, 800)), "PNG")

    assert run(comic, "--max-size", "400", "--skip-broken", "--direction", "ltr") == 0

    epub = book(comic)
    assert len(epub.page_paths()) == 2
    assert [t for t, _ in epub.nav_links()] == ["ch1", "ch2"]


def test_input_files_are_not_modified(comic):
    original = save(comic / "1.jpg", noise((600, 800)), "JPEG")

    run(comic, "--quality", "30", "--max-size", "200")

    assert (comic / "1.jpg").read_bytes() == original
    assert sorted(p.name for p in comic.iterdir()) == ["1.jpg"]


def test_help_explains_both_options(capsys):
    with pytest.raises(SystemExit):
        main(["--help"])
    out = capsys.readouterr().out
    assert "--quality" in out and "--max-size" in out
    assert "JPEG" in out
    assert "長邊" in out


def test_very_detailed_pages_can_be_reencoded_at_high_quality(comic):
    """回歸測試：細節極多的大頁面以高品質重新編碼時，不能因為編碼器緩衝區太小而失敗。"""
    save(comic / "1.png", noise((1200, 1600)), "PNG")

    assert run(comic, "--quality", "95") == 0

    assert decode(book(comic).page_images()[0]).size == (1200, 1600)
