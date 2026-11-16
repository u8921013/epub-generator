"""票 07 查證出的 Kobo fixed layout 設定。

每一項都要在所有選項組合下都成立，而且同一個輸出檔同時給 Apple Books 與 Kobo 使用。
"""

import io
import re

import pytest
from PIL import Image

from epubgen.cli import main
from tests.helpers import NS, Epub, make_image, spine_direction, spine_spread_properties

OPTION_SETS = {
    "default": [],
    "ltr": ["--direction", "ltr"],
    "spread-rtl": ["--spread"],
    "spread-ltr": ["--spread", "--direction", "ltr"],
    "title-author-language": ["--title", "T", "--author", "A", "--language", "ja"],
}


@pytest.fixture(params=list(OPTION_SETS), ids=list(OPTION_SETS))
def built(request, tmp_path):
    folder = tmp_path / "in" / "my-comic"
    sizes = [(300, 500), (320, 480), (200, 200), (640, 480), (100, 150)]
    for chapter, count in (("ch1", 3), ("ch2", 2)):
        for n in range(count):
            make_image(folder / chapter / f"{n + 1}.jpg", size=sizes.pop(0),
                       color=(len(sizes) * 20, 5, 5))
    out = tmp_path / "out"
    out.mkdir()
    target = out / "book.epub"
    assert main([str(folder), "-o", str(target), *OPTION_SETS[request.param]]) == 0
    return Epub(target), out, request.param


def test_book_is_declared_pre_paginated(built):
    book, _, _ = built
    assert book.meta_property("rendition:layout") == "pre-paginated"


def test_spread_setting_is_a_value_kobo_accepts_at_book_level(built):
    book, _, name = built
    expected = "landscape" if "spread" in name else "none"
    assert book.meta_property("rendition:spread") == expected
    # Kobo 只讀取 metadata 層級；spine 項目上不應該有 rendition:spread-* 覆寫
    for props in spine_spread_properties(book):
        assert not [p for p in props if p.startswith("rendition:spread")]


def test_page_progression_direction_is_declared_on_the_spine(built):
    book, _, name = built
    assert spine_direction(book) == ("ltr" if "ltr" in name else "rtl")


def test_viewport_is_identical_in_meta_and_css_and_matches_the_image(built):
    """Kobo：viewport 在 meta 與 CSS 一致，圖片寬高比與 viewport 相符。

    第一頁與形狀接近的頁面共用同一個 viewport（票 13），圖片等比例縮放置中、不變形，
    所以寬高比相差最多約 5%，Kobo 規格要求的是寬高比相符、尺寸不必相同。
    """
    book, _, _ = built
    for page in book.page_paths():
        text = book.page_text(page)
        meta_w, meta_h = book.viewport(page)
        css = re.search(r"html, body \{[^}]*width: (\d+)px; height: (\d+)px", text)
        assert (int(css.group(1)), int(css.group(2))) == (meta_w, meta_h)
        img_css = re.search(r"img \{[^}]*width: (\d+)px; height: (\d+)px", text)
        shown = (int(img_css.group(1)), int(img_css.group(2)))
        with Image.open(io.BytesIO(book.zip.read(book.page_image_path(page)))) as img:
            assert shown[0] <= meta_w and shown[1] <= meta_h
            assert shown[0] == meta_w or shown[1] == meta_h
            assert abs(shown[0] / shown[1] - img.size[0] / img.size[1]) < 0.01


def test_every_page_is_its_own_document_with_one_img_and_no_background_image(built):
    book, _, _ = built
    pages = book.page_paths()
    assert len(set(pages)) == len(pages)
    for page in pages:
        text = book.page_text(page)
        assert len(re.findall(r"<img\b", text)) == 1
        assert "background" not in text
        assert "<svg" not in text


def test_cover_image_is_shown_by_its_own_xhtml_page(built):
    book, _, _ = built
    cover = book.cover_items()[0]
    cover_path = book.resolve(cover.get("href"))
    first_page = book.page_paths()[0]
    assert book.page_image_path(first_page) == cover_path


def test_adjacent_pages_never_reference_the_same_image_file(built):
    book, _, _ = built
    images = [book.page_image_path(p) for p in book.page_paths()]
    assert all(a != b for a, b in zip(images, images[1:]))


def test_no_smil_and_no_kobo_display_options_file_is_needed(built):
    book, _, _ = built
    assert not any(i.get("media-type") == "application/smil+xml" for i in book.manifest().values())
    assert not any(i.get("media-overlay") for i in book.manifest().values())
    assert "META-INF/com.kobobooks.display-options.xml" not in book.zip.namelist()


def test_first_spine_item_has_no_page_spread_property(built):
    book, _, _ = built
    assert spine_spread_properties(book)[0] == []


def test_spread_properties_use_the_unprefixed_form_kobo_documents(built):
    book, _, name = built
    allowed = {"page-spread-left", "page-spread-right"}
    for props in spine_spread_properties(book):
        assert set(props) <= allowed
        assert len(props) <= 1  # 每個項目最多一個跨頁屬性（EPUB 3.3 8.2.2.4）
    if "spread" not in name:
        assert all(props == [] for props in spine_spread_properties(book))


def test_only_a_single_output_file_is_produced(built):
    _, out_dir, _ = built
    assert [p.name for p in out_dir.iterdir()] == ["book.epub"]


def test_help_mentions_kobo_fixed_layout_file_name_hint(capsys):
    with pytest.raises(SystemExit):
        main(["--help"])
    out = capsys.readouterr().out
    assert "Kobo" in out
    assert ".fxl.kepub.epub" in out
