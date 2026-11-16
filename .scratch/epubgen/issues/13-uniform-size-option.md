# 13: 避免 Apple Books 換頁時畫面跳動（`--uniform-size`）

**What to build:** 使用者轉換自己的書（258 頁、1200 像素寬的 JPEG 與 PNG，`--direction ltr`）後，在 Apple Books 換頁時，每一頁會先顯示、稍等不到一秒才重新調整高度，畫面會跳一下。

分析這本書的圖片：258 頁有 48 種不同的尺寸，寬度幾乎都是 1200，但高度從 1697 到 1741 不等，寬高比在 0.689 到 0.707 之間，另有少數橫向或特殊尺寸的頁面。spec 決定「每一頁的版面尺寸等於該圖片自己的像素尺寸」（user story 4），所以這本書的每一頁各自宣告了略有不同的 viewport。

推測原因（**未經 Apple Books 實機證實**）：Apple Books 以 viewport 決定頁面的長寬比，viewport 逐頁不同，換頁時就需要重新計算。Apple 的 Asset Guide 提到 Books 以這些尺寸決定書的長寬比（只讀到搜尋摘要，未核對全文）。

新增選項 `--uniform-size`（預設關閉，所以預設行為與 spec 不變）：寬高比與參考值相差在 5% 以內的頁面共用同一個 viewport。參考值取所有頁面寬度與寬高比的中位數。圖片不重新取樣，只在 viewport 內等比例縮放並置中，留白處是白色。寬高比差太多的頁面（橫向跨頁、特殊尺寸）維持自己的尺寸，否則會被縮得很小。

**Blocked by:** None

**Status:** ready-for-human

- [x] 預設行為不變：沒給 `--uniform-size` 時，每頁的 viewport 仍等於圖片自己的尺寸
- [x] `--uniform-size`：寬高比接近的頁面共用同一個 viewport，meta viewport、body 尺寸與圖片位置一致
- [x] 圖片位元組不被重新取樣，縮放置中時不變形
- [x] 寬高比差太多的頁面維持自己的尺寸
- [x] 與 `--max-size`、`--quality`、章節、`--spread`、`--direction` 可以一起使用
- [x] `--help` 說明這個選項
- [x] EPUBCheck 沒有錯誤
- [ ] 實機：用使用者的書比較有無 `--uniform-size`，確認 Apple Books 換頁不再跳動

## Comments

使用者的書以 `--uniform-size` 轉換後，258 頁中有 254 頁共用 viewport 1200x1718，另外 4 頁維持自己的尺寸：1523x1469（封面）、1200x864、960x673、1200x2342。比較用的兩個檔案在 `device-test/user-book/`：A-per-page-size.epub（預設）與 B-uniform-size.epub。

Kobo 注意：留白處以絕對定位置中，不依賴 `object-fit`，因為 Kobo eInk 的舊版 WebKit 可能不支援。Kobo 規格要求圖片寬高比與 viewport 相符，這裡最多差 5%，留白最多 5%，沒有變形。Kobo 上是否沒有問題未實測。
