# 10: 加入 Kobo 的 fixed layout 設定

**What to build:** 同一個 EPUB 檔在 Kobo 上也能以固定版面開啟，使用者不用為不同裝置各轉一次。依照票 07 查證出的結論，把 Kobo 需要的 fixed layout 設定加進輸出，不另外產生 Kobo 專用檔，也不能破壞 Apple Books 的顯示。

只實作票 07 中有來源支持的設定。票 07 標示為「未證實」的項目，依它建議的保守做法處理，並留給票 12 實機確認。

涵蓋 spec 的 user story 44（自動化可驗證的部分）。

**Blocked by:** 01、07

**Status:** ready-for-agent

- [x] 輸出的 EPUB 含有票 07 列出的每一項 Kobo 設定
- [x] 這些設定在所有選項組合下都存在（至少涵蓋預設、`--direction ltr`、`--spread` 中已實作的部分）
- [x] 仍然只產生一個輸出檔
- [x] 既有測試全部通過，票 01 定義的 EPUB 結構沒有被破壞
- [x] 若環境有 EPUBCheck，產出的 EPUB 沒有錯誤
- [x] 以上行為都有透過 CLI 進入點的測試

## Comments

完成。依票 07 的結論逐項核對 Kobo 設定，實際需要改動的只有跨頁屬性與 `--help` 說明，其餘已在票 01–04 符合：

- 已符合且新增測試鎖住（所有選項組合）：`rendition:layout` 為 pre-paginated、`rendition:spread` 只在 metadata 層級且值為 `none` 或 `landscape`、viewport 在 meta 與 CSS 一致且等於圖片尺寸、每頁獨立 XHTML 且只有一個 `<img>`、封面圖由自己的 XHTML 顯示、相鄰頁面不引用同一個圖片檔、沒有 SMIL、spine 有 `page-progression-direction`、不需要 `com.kobobooks.display-options.xml`、只產生一個輸出檔。
- 調整：`--spread` 時封面不再標記 `rendition:page-spread-center`（Kobo 規格建議第一個項目不加任何跨頁屬性，且從未提到 center）；其餘頁面改用不帶 `rendition:` 前綴的 `page-spread-left` / `page-spread-right`。依據是 EPUB 3.3 把 `rendition:page-spread-left/right` 定義為這兩個屬性的別名，並註明較舊的閱讀系統可能只認得無前綴版本，而 Kobo 規格的範例也是無前綴寫法。封面仍然單獨一頁，因為第二頁開始新的跨頁。
- 新增：`--help` 末尾加上 Kobo 說明，提到 `.fxl.kepub.epub`。語氣依票 07 的結論，沒有宣稱純 `.epub` 一定可用。
- 未做：EPUBCheck 沒有執行，這台機器有 Java 21 但沒有 EPUBCheck，下載需要先取得同意，留給票 11。Apple Books 是否正確處理「封面無標記」與無前綴寫法，Kobo 是否正確處理，都留給票 12 實機確認。
- 未處理：GIF 封面在 Kobo 不支援，票 07 建議在票 08 範圍討論。

