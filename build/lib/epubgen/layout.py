"""版面尺寸：決定每一頁在 EPUB 裡宣告的 viewport。"""

import statistics

from .images import PageImage

Viewport = tuple[int, int]

# 第一頁的寬高比與其餘頁面相差超過這個比例，就改用其餘頁面的尺寸。
# 實機驗證過：其餘頁面彼此差約 2% 不會造成跳動。
FIRST_PAGE_TOLERANCE = 0.02


def page_viewports(pages: list[PageImage]) -> list[Viewport]:
    """每一頁的 viewport 是該圖片自己的像素尺寸，第一頁例外。

    Apple Books 以第一頁的尺寸決定整本書的頁面比例（實機驗證，票 13）。第一頁的形狀跟其餘
    頁面不同時（例如接近正方形的封面配直式內頁），每次換頁都會先用第一頁的比例顯示、
    再縮回正確大小，畫面會跳一下。所以第一頁改用其餘頁面寬度與寬高比的中位數，
    圖片在裡面等比例縮放置中（不重新取樣）。
    """
    own = [(p.width, p.height) for p in pages]
    rest = pages[1:]
    if not rest:
        return own
    ratio = statistics.median(p.width / p.height for p in rest)
    first = pages[0]
    if abs((first.width / first.height) / ratio - 1) <= FIRST_PAGE_TOLERANCE:
        return own
    width = round(statistics.median(p.width for p in rest))
    return [(width, max(1, round(width / ratio)))] + own[1:]


def fit_inside(page: PageImage, viewport: Viewport) -> tuple[int, int, int, int]:
    """把圖片等比例縮放到塞進 viewport 並置中，回傳 (left, top, width, height)。"""
    vw, vh = viewport
    scale = min(vw / page.width, vh / page.height)
    width, height = max(1, round(page.width * scale)), max(1, round(page.height * scale))
    return (vw - width) // 2, (vh - height) // 2, width, height
