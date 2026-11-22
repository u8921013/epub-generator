# 09: 封面與封面頁

**What to build:** 使用者用 `--cover` 指定圖片時，文字書在書架上顯示這張**封面**，而且開書第一個畫面是只放這張圖的封面頁；封面頁不在目錄中。圖片可以在輸入資料夾內或外，相對路徑從目前目錄算起，規則與漫畫書的 `--cover` 相同（GIF 封面另外產生 JPEG 給 Kobo 用）。沒有指定時文字書沒有封面圖、也沒有封面頁。

涵蓋 spec 的 user story 50–53。

**Blocked by:** 02（最簡單的文字書）

**Status:** resolved

- [x] 指定 `--cover` 時，封面圖在 manifest 標記為 cover image
- [x] spine 第一項是封面頁，只含封面圖
- [x] 封面頁不出現在目錄
- [x] 封面圖在輸入資料夾外也可用
- [x] GIF 封面的處理與漫畫書一致
- [x] 不指定 `--cover` 時沒有 cover image、沒有封面頁，spine 第一項是第一章
- [x] 封面檔不存在、不是支援的圖片、無法讀取時報錯（結束代碼 1）
- [x] EPUBCheck 情境表加入「有封面」的文字書，沒有錯誤

## Comments

- 2026-11-22：封面沿用漫畫書的 `--cover` 規則。
  - 把漫畫書的檢查拆成 `_checked_cover_path`（存在、格式）與 `_load_cover`（讀取；`--skip-broken` 也不跳過封面），兩種書共用。
  - `--keep-webp`、`--quality`、`--max-size` 也套用在封面上。GIF 封面轉成 JPEG，封面頁顯示的也是這張 JPEG。
- 封面在讀章之前就載入，封面有問題時會先報錯。
- 封面頁是 `OEBPS/text/cover.xhtml`，放在 spine 第一項，不在目錄裡。
  - `body` 帶 `epub:type="cover"`，`img` 的 `alt` 是書名。
  - 內建 CSS 的 `.cover` 讓封面置中，高度不超過畫面。
- 封面圖與某張插圖是同一個檔案時，會各打包一份（已有測試鎖住）。
- 章與封面頁共用 `_text_xhtml` 的頁面骨架。
- 審查記下但未處理：漫畫書與文字書各寫了一次「GIF 封面轉 JPEG」的判斷。原本要收進 `images.py`，但當時另一個 session 正在改那個檔案（判斷圖片真實格式），所以先不動。
