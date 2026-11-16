# 01: 單層資料夾轉成合法的 fixed layout EPUB

**What to build:** 使用者用 `pipx install .` 安裝後，在任何目錄執行 `epubgen ./my-comic`，就會在輸入資料夾旁邊得到 `my-comic.epub`。這是一本 EPUB 3 fixed layout（pre-paginated）的漫畫：資料夾裡每張圖片是獨立的一頁，頁面依檔名自然排序，每頁的版面尺寸等於該圖片自己的像素尺寸，圖片位元組原樣打包。第一張圖是封面，書名取自資料夾名稱，語言預設 `zh-TW`，目錄有一個指向第一頁的項目。完成時在標準輸出印出輸出檔路徑與總頁數。

這張票同時建立專案骨架：Python 套件 `epubgen`、console script 進入點、Pillow 相依、pytest，以及 spec 規定的唯一測試接縫（在同一個行程內以參數列表呼叫 CLI 進入函式，用 Pillow 在暫存資料夾即時產生測試圖片）。對外只有一個深模組介面「給定輸入資料夾和選項，產生一個 EPUB 檔」，CLI 是它的薄包裝；內部分成書籍掃描、圖片處理、EPUB 組裝三個職責。EPUB 用標準函式庫的 zip 功能打包，不使用第三方 EPUB 函式庫。

本票只處理單層資料夾（沒有子資料夾）、預設選項的情況。閱讀方向、章節、metadata 參數、輸出路徑參數、錯誤處理、WebP 轉檔都在後續票卷。

涵蓋 spec 的 user story 1–7、14、19、20、22、31、33、46–48。

**Blocked by:** None (can start immediately)

**Status:** resolved

- [x] `pipx install .` 後可在任何目錄執行 `epubgen`
- [x] `epubgen <資料夾>` 在輸入資料夾的同層目錄產生 `<資料夾名稱>.epub`，結束代碼為 0
- [x] 標準輸出包含輸出檔路徑與總頁數
- [x] 輸出是合法的 zip，`mimetype` 是第一個項目且未壓縮
- [x] package metadata 宣告為 pre-paginated 的 fixed layout，並含唯一識別碼、最後修改時間、書名（資料夾名稱）、語言（`zh-TW`）
- [x] 頁數等於圖片數，每頁是一份只含一張圖片的 XHTML
- [x] 頁面依檔名自然排序（`1, 2, 10` 而不是 `1, 10, 2`）
- [x] 尺寸不同的圖片各自得到與其像素尺寸相同的 viewport
- [x] 接受 `.jpg`、`.jpeg`、`.png`、`.webp`、`.gif`，副檔名不分大小寫
- [x] EPUB 內的圖片位元組與原檔完全相同（本票 WebP 也原樣打包，轉檔在票 08）
- [x] 非圖片檔案（例如 `.DS_Store`、`.txt`）被忽略，不出現在 EPUB 裡
- [x] 第一張圖在 manifest 中標記為 cover image
- [x] navigation document 合法，含一個指向第一頁的項目
- [x] `epubgen --help` 列出參數與預設值，`epubgen --version` 顯示版本
- [x] 以上行為都有透過 CLI 進入點的 pytest 測試，測試不依賴內部模組的函式簽名
