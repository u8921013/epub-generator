"""產生 Apple Books 與 Kobo 實機驗證用的測試書（漫畫書：票 12；文字書：text-book 票 10）。

漫畫書每一頁都畫上大大的章節與頁碼，翻頁方向、左右頁配對與目錄跳轉一眼就能看出對不對。
文字書範本 T-text-book 涵蓋有部有章、中文軟換行、表格、程式碼區塊、插圖、書內連結與封面頁。
專案根目錄若有 pages/（使用者本機的小說資料夾，不進版本控制），另外產生 U-pages-novel。

用法：
    .venv/bin/python scripts/make_device_test_books.py [輸出資料夾]

預設輸出到專案的 device-test/（已被 .gitignore 排除）。每本書產生：
    <輸出資料夾>/books/<名稱>.epub            給 Apple Books，也給 Kobo 試純 .epub
    <輸出資料夾>/books/<名稱>.fxl.kepub.epub  內容相同，只有副檔名不同，給 Kobo eInk 試（只有漫畫書）
"""

import shutil
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from epubgen.cli import main

ROOT = Path(__file__).resolve().parent.parent

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


TEXT_CHAPTERS = {
    "01-序章.md": """# 序章

這一段刻意在句子中間換行，
在 Apple Books 與 Kobo 上應該接成同一行，
中文之間不會多出空白。English words
still get a space between lines.

這一章測試書內連結：

- 跨章：[第一章](<第一部 出發/01-第一章.md>)
- 跨章並跳到章內標題：[第一章的「表格」](<第一部 出發/01-第一章.md#表格>)
- 跨部：[第三章](<第二部 歸來/01-第三章.md>)
- 章內錨點：[跳到本章最後](#本章最後)

把字級調到最大、最小各試一次，文字應該重新排版，不會被截斷。

""" + "\n\n".join(f"填充段落 {i}：為了讓章內錨點真的需要捲動，這裡放一些重複的文字。" * 3 for i in range(1, 16)) + """

## 本章最後

到這裡就是序章的結尾。[回到開頭](#序章)
""",
    "第一部 出發/01-第一章.md": """# 第一章

## 表格

| 角色 | 年齡 | 備註 |
| --- | ---: | --- |
| 林小明 | 17 | 主角 |
| 王大華 | 42 | ~~反派~~ 其實是好人 |
| Alice | 25 | 很長很長很長很長很長很長很長很長很長很長的欄位，看會不會撐破螢幕 |

## 程式碼區塊

```python
def greet(name: str) -> str:
    # 這一行故意寫得很長，看閱讀器怎麼處理超出螢幕寬度的程式碼：要換行還是可以橫向捲動
    return f"你好，{name}！"
```

行內程式碼：`epubgen pages/ -o book.epub`。

[回序章](../01-序章.md) · [下一章](02-第二章.md)
""",
    "第一部 出發/02-第二章.md": """# 第二章

下面是一張很大的橫幅插圖（3000x1200），不應超出螢幕：

![大橫幅插圖](images/wide.jpg)

下面是一張很高的直幅插圖（1200x3600），整張應該縮在一頁內：

![高直幅插圖](images/tall.png)

[跨部：第三章的「重逢」](<../第二部 歸來/01-第三章.md#重逢>)
""",
    "第二部 歸來/01-第三章.md": """# 第三章

## 重逢

這是第二部的第一章。目錄應該是兩層：「第二部 歸來」底下有「第三章」。

[跨部回第一章的「程式碼區塊」](<../第一部 出發/01-第一章.md#程式碼區塊>)
""",
}


def text_book(folder: Path):
    """文字書範本：根目錄一章（序章），兩個子資料夾各成一部；插圖放在第一部的 images/。"""
    for name, body in TEXT_CHAPTERS.items():
        path = folder / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(body, encoding="utf-8")
    draw_page(folder / "第一部 出發" / "images" / "wide.jpg", "WIDE ILLUSTRATION", 2, size=(3000, 1200))
    draw_page(folder / "第一部 出發" / "images" / "tall.png", "TALL ILLUSTRATION", 3, size=(1200, 3600))


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

# 文字書：只產生 .epub（.kepub.epub 不在文字書的範圍內）
TEXT_BOOKS = {
    "T-text-book": (text_book, ["--cover", "{cover}", "--language", "zh-TW"],
                    "文字重排、兩層目錄、書內連結（跨章／跨部／章內錨點）、插圖不超出螢幕、表格、程式碼、"
                    "中文軟換行、封面縮圖與封面頁"),
}
NOVEL = ROOT / "pages"


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
    descriptions = {name: what for name, (_, _, what) in BOOKS.items()}
    for name, (prepare, args, what) in TEXT_BOOKS.items():
        folder = inputs / name
        prepare(folder)
        args = [str(cover) if a == "{cover}" else a for a in args]
        build(name, [str(folder), "-o", str(books / f"{name}.epub"), "--title", name, *args])
        descriptions[name] = what
    if NOVEL.is_dir():
        build("U-pages-novel", [str(NOVEL), "-o", str(books / "U-pages-novel.epub"),
                                "--title", "U-pages-novel", "--language", "zh-TW"])
        descriptions["U-pages-novel"] = "pages/ 小說：234 章、章名與順序正確，兩台閱讀器都能開啟"
    print(f"\n完成：{books}")
    for name, what in descriptions.items():
        print(f"  {name}: {what}")


def build(name: str, argv: list[str]):
    if main(argv) != 0:
        sys.exit(f"{name} 產生失敗")


if __name__ == "__main__":
    main_script(Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "device-test")
