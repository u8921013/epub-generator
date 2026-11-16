"""用 EPUBCheck 驗證各情境產出的 EPUB。環境沒有 Java 或 EPUBCheck 時整組跳過。

新增情境只要在 SCENARIOS 加一列：名稱 → (準備資料夾的函式, CLI 參數)。
"""

import pytest

from epubgen.cli import main
from tests import epubcheck
from tests.helpers import make_image

COMMAND = epubcheck.find_command()

pytestmark = pytest.mark.skipif(
    COMMAND is None,
    reason="找不到 Java 或 EPUBCheck（設定 EPUBCHECK_JAR，或解壓到 .tools/，見 README）",
)


def flat(folder):
    make_image(folder / "1.jpg", size=(300, 500))
    make_image(folder / "2.jpg", size=(320, 480))
    make_image(folder / "10.png", size=(640, 480))
    make_image(folder / "11.gif", size=(100, 150))


def chapters(folder):
    make_image(folder / "cover.jpg", size=(300, 500))
    for chapter, count in (("第 10 話", 2), ("第 2 話", 3)):
        for n in range(count):
            make_image(folder / chapter / f"{n + 1}.jpg", size=(300 + n, 500))
    make_image(folder / "第 2 話" / "extra" / "1.jpg", size=(300, 500))


def with_webp(folder):
    make_image(folder / "1.jpg", size=(300, 500))
    make_image(folder / "2.webp", size=(300, 500))


def gif_first(folder):
    make_image(folder / "1.gif", size=(300, 500))
    make_image(folder / "2.jpg", size=(300, 500))


def special_characters(folder):
    make_image(folder / "A&B <1>" / "1.jpg", size=(300, 500))
    make_image(folder / "A&B <1>" / "2.jpg", size=(300, 500))


SCENARIOS = {
    "basic": (flat, []),
    "ltr": (flat, ["--direction", "ltr"]),
    "spread-rtl": (flat, ["--spread"]),
    "spread-ltr": (flat, ["--spread", "--direction", "ltr"]),
    "chapters": (chapters, []),
    "chapters-spread": (chapters, ["--spread", "--direction", "ltr"]),
    "metadata": (flat, ["--title", "A & B <x>", "--author", "某某", "--language", "ja"]),
    "special-characters": (special_characters, []),
    "gif-cover": (gif_first, []),
    "uniform-size": (flat, ["--uniform-size"]),
    "uniform-size-chapters": (chapters, ["--uniform-size", "--spread"]),
    "quality-and-resize": (flat, ["--quality", "60", "--max-size", "400"]),
    "resize-only": (flat, ["--max-size", "250"]),
    "webp-converted": (with_webp, []),
    "webp-kept": (with_webp, ["--keep-webp"]),
}


def build(tmp_path, prepare, args, extra=()):
    folder = tmp_path / "in" / "my-comic"
    folder.mkdir(parents=True)
    prepare(folder)
    target = tmp_path / "book.epub"
    assert main([str(folder), "-o", str(target), *args, *extra]) == 0
    return target


@pytest.mark.parametrize("name", list(SCENARIOS))
def test_epubcheck_reports_no_errors(tmp_path, name):
    prepare, args = SCENARIOS[name]
    target = build(tmp_path, prepare, args)

    ok, output = epubcheck.run(COMMAND, target)

    assert ok, f"EPUBCheck 回報錯誤（情境 {name}）：\n{output}"


def test_epubcheck_reports_no_errors_with_an_external_cover(tmp_path):
    cover = tmp_path / "front.png"
    make_image(cover, size=(200, 300))
    prepare, args = SCENARIOS["basic"]
    target = build(tmp_path, prepare, args, extra=["--cover", str(cover)])

    ok, output = epubcheck.run(COMMAND, target)

    assert ok, f"EPUBCheck 回報錯誤（外部封面）：\n{output}"


def test_epubcheck_reports_no_errors_after_skipping_broken_images(tmp_path):
    def prepare(folder):
        flat(folder)
        (folder / "5.jpg").write_bytes(b"garbage")

    target = build(tmp_path, prepare, [], extra=["--skip-broken"])

    ok, output = epubcheck.run(COMMAND, target)

    assert ok, f"EPUBCheck 回報錯誤（跳過損毀圖片）：\n{output}"
