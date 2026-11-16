"""版面尺寸：決定每一頁在 EPUB 裡宣告的 viewport。"""

import statistics

from .images import PageImage

Viewport = tuple[int, int]

# 寬高比與參考值相差在這個比例以內的頁面共用同一個 viewport。
RATIO_TOLERANCE = 0.05


def own_viewports(pages: list[PageImage]) -> list[Viewport]:
    """預設：每一頁的 viewport 就是那張圖片自己的像素尺寸。"""
    return [(p.width, p.height) for p in pages]


def uniform_viewports(pages: list[PageImage]) -> list[Viewport]:
    """讓寬高比接近的頁面共用同一個 viewport。

    漫畫掃圖的尺寸常常每頁差幾個像素，Apple Books 換頁時會因為 viewport 不同而重新調整，
    畫面會跳一下。參考尺寸取所有頁面寬度與寬高比的中位數；寬高比與參考值相差在
    RATIO_TOLERANCE 以內的頁面共用它，差太多的頁面（橫向跨頁、特殊尺寸）保留自己的尺寸，
    不然會被縮得很小。
    """
    width = round(statistics.median(p.width for p in pages))
    ratio = statistics.median(p.width / p.height for p in pages)
    reference = (width, max(1, round(width / ratio)))
    return [
        reference if abs((p.width / p.height) / ratio - 1) <= RATIO_TOLERANCE else (p.width, p.height)
        for p in pages
    ]


def fit_inside(page: PageImage, viewport: Viewport) -> tuple[int, int, int, int]:
    """把圖片等比例縮放到塞進 viewport 並置中，回傳 (left, top, width, height)。"""
    vw, vh = viewport
    scale = min(vw / page.width, vh / page.height)
    width, height = max(1, round(page.width * scale)), max(1, round(page.height * scale))
    return (vw - width) // 2, (vh - height) // 2, width, height
