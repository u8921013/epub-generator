"""產生 Apple Books 與 Kobo 實機驗證用的測試書（票 12）。

每一頁都畫上大大的章節與頁碼，翻頁方向、左右頁配對與目錄跳轉一眼就能看出對不對。

用法：
    .venv/bin/python scripts/make_device_test_books.py [輸出資料夾]

預設輸出到專案的 device-test/（已被 .gitignore 排除）。每本書產生：
    <輸出資料夾>/books/<名稱>.epub            給 Apple Books，也給 Kobo 試純 .epub
    <輸出資料夾>/books/<名稱>.fxl.kepub.epub  內容相同，只有副檔名不同，給 Kobo eInk 試
"""

import shutil
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from epubgen.cli import main

PORTRAIT = (1200, 1800)
COLORS = [(230, 90, 90), (90, 160, 230), (110, 200, 120), (240, 190, 70),
          (180, 120, 220), (90, 200, 200), (240, 140, 80), (150, 150, 150)]


def draw_page(path: Path, label: str, number: int, size=PORTRAIT, note="", fmt=None):
    """畫一頁：底色隨頁碼變化，中間是大大的標籤與頁碼，四個角落各有一個記號。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    img = Image.new("RGB", size, COLORS[number % len(COLORS)])
    d = ImageDraw.Draw(img)
    w, h = size
    d.rectangle([20, 20, w - 21, h - 21], outline=(0, 0, 0), width=8)
    big = ImageFont.load_default(size=max(w // 4, 40))
    mid = ImageFont.load_default(size=max(w // 14, 24))
    d.text((w / 2, h * 0.38), f"P{number}", fill=(0, 0, 0), font=big, anchor="mm")
    d.text((w / 2, h * 0.58), label, fill=(0, 0, 0), font=mid, anchor="mm")
    if note:
        d.text((w / 2, h * 0.68), note, fill=(0, 0, 0), font=mid, anchor="mm")
    d.text((w * 0.08, h * 0.04), "TL", fill=(0, 0, 0), font=mid, anchor="la")
    d.text((w * 0.92, h * 0.04), "TR", fill=(0, 0, 0), font=mid, anchor="ra")
    d.text((w * 0.08, h * 0.96), "BL", fill=(0, 0, 0), font=mid, anchor="ld")
    d.text((w * 0.92, h * 0.96), "BR", fill=(0, 0, 0), font=mid, anchor="rd")
    img.save(path, fmt)


def chaptered(folder: Path):
    """RTL 有章節：根目錄一張封面，三章，章名測試自然排序（第 2 話在第 10 話前）。第 2 話含一張 WebP。"""
    draw_page(folder / "cover.jpg", "COVER (root, not in TOC)", 1)
    page = 1
    for name, count in (("第 1 話", 4), ("第 2 話", 3), ("第 10 話", 3)):
        for i in range(1, count + 1):
            page += 1
            label = f"{name} / page {i}"
            if name == "第 2 話" and i == 2:
                draw_page(folder / name / f"{i}.webp", label, page, note="(WebP source)")
            else:
                draw_page(folder / name / f"{i}.jpg", label, page)


def plain(folder: Path, count=8):
    for i in range(1, count + 1):
        draw_page(folder / f"{i:02d}.jpg", f"page {i}", i)


def gif_first(folder: Path):
    draw_page(folder / "01.gif", "GIF COVER", 1, fmt="GIF")
    for i in range(2, 6):
        draw_page(folder / f"{i:02d}.jpg", f"page {i}", i)


def with_webp(folder: Path):
    for i in range(1, 5):
        if i % 2 == 0:
            draw_page(folder / f"{i:02d}.webp", f"page {i}", i, note="(WebP)")
        else:
            draw_page(folder / f"{i:02d}.jpg", f"page {i}", i)


def big_pages(folder: Path):
    for i in range(1, 7):
        draw_page(folder / f"{i:02d}.jpg", f"BIG page {i}", i, size=(3000, 4500))


def outside_cover(folder: Path):
    plain(folder, 4)


# 名稱 → (準備輸入資料夾, epubgen 參數, 這本書要驗證什麼)
BOOKS = {
    "A-rtl-chapters": (chaptered, [], "RTL 預設、章節目錄、WebP 轉 JPEG、封面縮圖"),
    "B-ltr-plain": (plain, ["--direction", "ltr"], "LTR、沒有章節的目錄"),
    "C-rtl-spread": (plain, ["--spread"], "RTL 雙頁：橫放時封面單獨，之後 P2 在右、P3 在左…"),
    "D-ltr-spread": (plain, ["--spread", "--direction", "ltr"], "LTR 雙頁：橫放時封面單獨，之後 P2 在左、P3 在右…"),
    "E-gif-cover": (gif_first, [], "第一張圖是 GIF，Kobo 書櫃封面是否正常（封面另外轉成 JPEG）"),
    "F-keep-webp": (with_webp, ["--keep-webp"], "保留 WebP 原檔，Kobo 是否顯示（社群回報 Kobo Forma 韌體 4.38 顯示空白）"),
    "G-big-pages": (big_pages, [], "3000x4500（約 13.5M 像素）的頁面，翻頁是否明顯變慢"),
    "H-big-pages-resized": (big_pages, ["--max-size", "1950"], "和 G 同一批圖，縮到長邊 1950，比較翻頁速度"),
    "I-external-cover": (outside_cover, ["--cover", "{cover}"], "封面是資料夾外的圖（紫色 EXTERNAL COVER），書櫃縮圖是否正確"),
}


def main_script(out: Path):
    inputs, books = out / "input", out / "books"
    shutil.rmtree(out, ignore_errors=True)
    books.mkdir(parents=True)
    cover = inputs / "external-cover.jpg"
    draw_page(cover, "EXTERNAL COVER", 5, note="(not a page)")
    for name, (prepare, args, _) in BOOKS.items():
        folder = inputs / name
        prepare(folder)
        target = books / f"{name}.epub"
        args = [str(cover) if a == "{cover}" else a for a in args]
        code = main([str(folder), "-o", str(target), "--title", name, *args])
        if code != 0:
            sys.exit(f"{name} 產生失敗")
        shutil.copy(target, books / f"{name}.fxl.kepub.epub")
    print(f"\n完成：{books}")
    for name, (_, args, what) in BOOKS.items():
        print(f"  {name}: {what}")


if __name__ == "__main__":
    main_script(Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parent.parent / "device-test")
