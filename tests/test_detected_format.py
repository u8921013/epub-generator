"""副檔名跟實際內容不符時，依實際格式打包（主接縫：CLI 進入點）。

例如存成 a.jpg 的 PNG：EPUB 裡要是 .png、image/png，而不是照副檔名宣告成 JPEG。
"""

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


def run(folder, *args):
    assert main([str(folder), *map(str, args)]) == 0
    return Epub(folder.parent / f"{folder.name}.epub")


def item_for(epub, zip_path):
    return next(i for i in epub.manifest().values() if epub.resolve(i.get("href")) == zip_path)


def page_types(epub):
    """依 spine 順序回傳每頁圖片的（media-type, 副檔名）。"""
    out = []
    for page in epub.page_paths():
        path = epub.page_image_path(page)
        out.append((item_for(epub, path).get("media-type"), path.rpartition(".")[2]))
    return out


def detected(data: bytes) -> str:
    with Image.open(io.BytesIO(data)) as img:
        return img.format


# --- 漫畫頁面 --------------------------------------------------------------------

def test_png_saved_as_jpg_is_packaged_as_png_byte_for_byte(comic):
    make_image(comic / "1.jpg")
    original = make_image(comic / "2.jpg", fmt="PNG")

    epub = run(comic)

    assert page_types(epub) == [("image/jpeg", "jpg"), ("image/png", "png")]
    assert epub.page_images()[1] == original


@pytest.mark.parametrize("name, fmt, expected", [
    ("1.png", "JPEG", ("image/jpeg", "jpg")),
    ("1.gif", "PNG", ("image/png", "png")),
    ("1.jpeg", "GIF", ("image/gif", "gif")),
])
def test_every_kept_image_takes_its_type_from_its_content(comic, name, fmt, expected):
    original = make_image(comic / name, fmt=fmt)

    epub = run(comic)

    assert page_types(epub) == [expected]
    assert epub.page_images()[0] == original


def test_webp_saved_as_jpg_is_still_converted_to_jpeg_by_default(comic):
    make_image(comic / "1.jpg", fmt="WEBP")

    epub = run(comic)

    assert page_types(epub) == [("image/jpeg", "jpg")]
    assert detected(epub.page_images()[0]) == "JPEG"


def test_webp_saved_as_png_is_kept_as_webp_with_keep_webp(comic):
    original = make_image(comic / "1.png", fmt="WEBP")

    epub = run(comic, "--keep-webp")

    assert page_types(epub) == [("image/webp", "webp")]
    assert epub.page_images()[0] == original


def test_quality_follows_the_real_format_rules(comic):
    # GIF 不受 --quality 影響；就算檔名是 .jpg 也一樣原樣打包
    original = make_image(comic / "1.jpg", fmt="GIF")

    epub = run(comic, "--quality", "60")

    assert page_types(epub) == [("image/gif", "gif")]
    assert epub.page_images()[0] == original


def test_unsupported_format_behind_an_image_name_becomes_jpeg(comic):
    make_image(comic / "1.jpg", fmt="BMP")

    epub = run(comic)

    assert page_types(epub) == [("image/jpeg", "jpg")]
    assert detected(epub.page_images()[0]) == "JPEG"


def test_gif_saved_as_jpg_on_the_first_page_still_gets_a_jpeg_cover(comic):
    make_image(comic / "1.jpg", fmt="GIF")

    epub = run(comic)

    (cover,) = epub.cover_items()
    assert cover.get("media-type") == "image/jpeg"
    assert detected(epub.zip.read(epub.resolve(cover.get("href")))) == "JPEG"
    assert page_types(epub) == [("image/gif", "gif")]


def test_external_cover_saved_with_the_wrong_name_gets_its_real_type(comic, tmp_path):
    make_image(comic / "1.jpg")
    cover_path = tmp_path / "front.jpg"
    original = make_image(cover_path, fmt="PNG")

    epub = run(comic, "--cover", cover_path)

    (cover,) = epub.cover_items()
    assert cover.get("media-type") == "image/png"
    assert cover.get("href").endswith(".png")
    assert epub.zip.read(epub.resolve(cover.get("href"))) == original


# --- 文字書插圖 ------------------------------------------------------------------

def test_illustration_saved_with_the_wrong_name_gets_its_real_type(tmp_path):
    folder = tmp_path / "pages"
    folder.mkdir()
    (folder / "a.md").write_text("# 甲\n\n![地圖](map.jpg)\n", encoding="utf-8")
    original = make_image(folder / "map.jpg", fmt="PNG")

    epub = run(folder)

    (path,) = epub.illustrations()
    assert path.endswith(".png")
    assert item_for(epub, path).get("media-type") == "image/png"
    assert epub.zip.read(path) == original
    assert [src for src, _ in epub.chapter_images("OEBPS/text/chapter-0001.xhtml")] == [path]
