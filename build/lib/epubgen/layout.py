"""版面尺寸：決定每一頁在 EPUB 裡宣告的 viewport。"""

import statistics

from .images import PageImage

Viewport = tuple[int, int]

# 寬高比與參考值相差在這個比例以內的頁面，共用同一個 viewport。
SHAPE_TOLERANCE = 0.05


def page_viewports(pages: list[PageImage]) -> list[Viewport]:
    """決定每一頁的 viewport。

    Apple Books 以第一頁的形狀決定整本書的頁面比例（實機驗證，票 13）：形狀跟第一頁不同的頁面，
    換頁時會先用第一頁的比例顯示、再縮回自己的比例，畫面會跳一下。差 1% 到 2% 也看得出來。

    所以：參考尺寸取第一頁以外所有頁面寬度與寬高比的中位數。第一頁一律用參考尺寸；
    其他頁面寬高比與參考值相差在 SHAPE_TOLERANCE 以內的，也用參考尺寸；差太多的
    （橫向跨頁、特別長的頁面）維持自己的尺寸，否則會被縮得很小。
    圖片在 viewport 裡等比例縮放置中，不重新取樣。
    """
    own = [(p.width, p.height) for p in pages]
    rest = pages[1:]
    if not rest:
        return own
    ratio = statistics.median(p.width / p.height for p in rest)
    width = round(statistics.median(p.width for p in rest))
    reference = (width, max(1, round(width / ratio)))
    viewports = [reference]
    for page, size in zip(rest, own[1:]):
        close = abs((page.width / page.height) / ratio - 1) <= SHAPE_TOLERANCE
        viewports.append(reference if close else size)
    return viewports


def fit_inside(page: PageImage, viewport: Viewport) -> tuple[int, int, int, int]:
    """把圖片等比例縮放到塞進 viewport 並置中，回傳 (left, top, width, height)。"""
    vw, vh = viewport
    scale = min(vw / page.width, vh / page.height)
    width, height = max(1, round(page.width * scale)), max(1, round(page.height * scale))
    return (vw - width) // 2, (vh - height) // 2, width, height
