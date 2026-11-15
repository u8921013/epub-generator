"""書籍掃描：讀取輸入資料夾，產出依自然排序的頁面來源。"""

import re
from pathlib import Path

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}


def natural_key(name: str):
    """自然排序：`2.jpg` 排在 `10.jpg` 前，不分大小寫。"""
    return [int(t) if t.isdigit() else t.casefold() for t in re.split(r"(\d+)", name)]


def scan_pages(folder: Path) -> list[Path]:
    """回傳資料夾（僅第一層）內所有圖片，依檔名自然排序。"""
    images = [
        p for p in folder.iterdir()
        if p.is_file() and p.suffix.lower() in IMAGE_EXTENSIONS
    ]
    return sorted(images, key=lambda p: natural_key(p.name))
