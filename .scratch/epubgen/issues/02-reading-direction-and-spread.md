# 02: 閱讀方向與雙頁模式

**What to build:** 不加任何參數時，產出的書從右到左翻頁（日漫習慣）；加上 `--direction ltr` 則從左到右。預設每頁單獨顯示，不合併成跨頁。加上 `--spread` 後啟用雙頁模式：封面單獨一頁，其後的頁面依閱讀方向交替標記為左頁與右頁，RTL 的書右頁在先、LTR 的書左頁在先，讓原本的跨頁畫面能正確對齊。

涵蓋 spec 的 user story 8–13。

**Blocked by:** 01

**Status:** resolved

- [x] 預設的 page progression direction 是 RTL
- [x] `--direction ltr` 把 page progression direction 改成 LTR
- [x] 預設所有頁面都不合併成跨頁
- [x] `--spread` 時封面單獨顯示
- [x] `--spread` 且 RTL 時，封面之後的頁面依序標記為右、左、右、左…
- [x] `--spread` 且 LTR 時，封面之後的頁面依序標記為左、右、左、右…
- [x] `--help` 顯示這兩個參數與預設值
- [x] 以上行為都有透過 CLI 進入點的測試

## Comments

票 10 調整了雙頁模式的標記寫法（行為上封面仍單獨一頁、其後右左／左右交替）：封面不再有 `rendition:page-spread-center`，其餘頁面改用不帶前綴的 `page-spread-left` / `page-spread-right`。原因與依據見票 10 與票 07。

