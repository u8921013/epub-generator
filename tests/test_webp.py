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


def image_types(epub):
    """依 spine 順序回傳每頁圖片 manifest 的 media-type 與檔名。"""
    out = []
    for page in epub.page_paths():
        path = epub.page_image_path(page)
        item = next(i for i in epub.manifest().values()
                    if epub.resolve(i.get("href")) == path)
        out.append((item.get("media-type"), path.rpartition(".")[2]))
    return out


def decode(data: bytes) -> Image.Image:
    img = Image.open(io.BytesIO(data))
    img.load()
    return img


def save_webp(path, img, **kwargs):
    path.parent.mkdir(parents=True, exist_ok=True)
    img.save(path, "WEBP", **kwargs)
    return path.read_bytes()


# --- 預設：轉成 JPEG -----------------------------------------------------------

def test_webp_is_converted_to_jpeg_by_default(comic):
    make_image(comic / "1.jpg")
    original = make_image(comic / "2.webp", size=(90, 140))

    assert run(comic) == 0

    epub = book(comic)
    assert image_types(epub) == [("image/jpeg", "jpg"), ("image/jpeg", "jpg")]
    converted = epub.page_images()[1]
    assert converted[:2] == b"\xff\xd8"  # JPEG 檔頭
    assert converted != original
    assert decode(converted).format == "JPEG"
    assert not any(n.endswith(".webp") for n in epub.zip.namelist())


def test_viewport_follows_the_converted_image(comic):
    make_image(comic / "1.webp", size=(123, 457))

    run(comic)

    epub = book(comic)
    converted = decode(epub.page_images()[0])
    assert converted.size == (123, 457)
    assert epub.viewport(epub.page_paths()[0]) == converted.size


def test_other_formats_are_still_packaged_byte_for_byte(comic):
    originals = [make_image(comic / name) for name in ("1.jpg", "2.JPEG", "3.png", "4.gif")]
    make_image(comic / "5.webp")

    run(comic)

    assert book(comic).page_images()[:4] == originals


def test_uppercase_webp_extension_is_converted_too(comic):
    make_image(comic / "1.WEBP")

    run(comic)

    assert image_types(book(comic)) == [("image/jpeg", "jpg")]


def test_conversion_keeps_quality_high(comic):
    solid = (200, 40, 40)
    make_image(comic / "1.webp", size=(64, 64), color=solid)

    run(comic)

    converted = decode(book(comic).page_images()[0]).convert("RGB")
    r, g, b = converted.getpixel((32, 32))
    assert max(abs(r - solid[0]), abs(g - solid[1]), abs(b - solid[2])) <= 6


def test_transparent_pixels_become_white(comic):
    img = Image.new("RGBA", (40, 40), (0, 0, 0, 0))  # 全透明
    for x in range(20):
        for y in range(40):
            img.putpixel((x, y), (255, 0, 0, 255))  # 左半不透明紅色
    save_webp(comic / "1.webp", img, lossless=True)

    run(comic)

    converted = decode(book(comic).page_images()[0]).convert("RGB")
    assert min(converted.getpixel((35, 20))) >= 250  # 透明處是白色，不是黑色
    r, g, b = converted.getpixel((5, 20))
    assert r > 240 and g < 20 and b < 20  # 不透明處維持紅色


def test_semi_transparent_pixels_blend_with_white(comic):
    save_webp(comic / "1.webp", Image.new("RGBA", (16, 16), (0, 0, 0, 128)), lossless=True)

    run(comic)

    gray = decode(book(comic).page_images()[0]).convert("RGB").getpixel((8, 8))[0]
    assert 100 <= gray <= 160  # 黑色以 50% 疊在白底上，約為中灰


def test_palette_and_grayscale_webp_are_converted_too(comic):
    save_webp(comic / "1.webp", Image.new("L", (30, 40), 90))
    save_webp(comic / "2.webp", Image.new("P", (30, 40), 3))

    assert run(comic) == 0

    assert image_types(book(comic)) == [("image/jpeg", "jpg")] * 2


# --- 封面 ---------------------------------------------------------------------

def test_cover_that_is_a_webp_page_points_at_the_converted_jpeg(comic):
    make_image(comic / "1.webp")
    make_image(comic / "2.jpg")

    run(comic)

    epub = book(comic)
    covers = epub.cover_items()
    assert len(covers) == 1
    assert covers[0].get("media-type") == "image/jpeg"
    assert epub.zip.read(epub.resolve(covers[0].get("href"))) == epub.page_images()[0]


def test_external_webp_cover_is_converted_by_default(comic, tmp_path):
    make_image(comic / "1.jpg")
    make_image(tmp_path / "front.webp", size=(50, 80))

    run(comic, "--cover", tmp_path / "front.webp")

    epub = book(comic)
    cover = epub.cover_items()[0]
    assert cover.get("media-type") == "image/jpeg"
    assert decode(epub.zip.read(epub.resolve(cover.get("href")))).format == "JPEG"


# --- 保留 WebP ----------------------------------------------------------------

def test_keep_webp_packages_the_original_bytes(comic):
    original = make_image(comic / "1.webp")
    make_image(comic / "2.jpg")

    assert run(comic, "--keep-webp") == 0

    epub = book(comic)
    assert epub.page_images()[0] == original
    assert image_types(epub)[0] == ("image/webp", "webp")


def test_keep_webp_also_keeps_a_webp_cover(comic, tmp_path):
    make_image(comic / "1.jpg")
    original = make_image(tmp_path / "front.webp")

    run(comic, "--keep-webp", "--cover", tmp_path / "front.webp")

    epub = book(comic)
    cover = epub.cover_items()[0]
    assert cover.get("media-type") == "image/webp"
    assert epub.zip.read(epub.resolve(cover.get("href"))) == original


# --- 其他 ---------------------------------------------------------------------

def test_input_files_are_not_modified(comic):
    original = make_image(comic / "1.webp")

    run(comic)

    assert (comic / "1.webp").read_bytes() == original
    assert sorted(p.name for p in comic.iterdir()) == ["1.webp"]


def test_broken_webp_is_reported_and_can_be_skipped(comic, capsys):
    make_image(comic / "1.jpg")
    (comic / "2.webp").write_bytes(b"RIFFxxxxWEBPgarbage")

    assert run(comic) != 0
    assert "2.webp" in capsys.readouterr().err

    assert run(comic, "--skip-broken") == 0
    assert "2.webp" in capsys.readouterr().err
    assert len(book(comic).page_paths()) == 1


def test_help_describes_keep_webp(capsys):
    with pytest.raises(SystemExit):
        main(["--help"])
    out = capsys.readouterr().out
    assert "--keep-webp" in out
    assert "JPEG" in out
