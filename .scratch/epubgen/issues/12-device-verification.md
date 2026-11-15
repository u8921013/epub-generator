# 12: Apple Books 與 Kobo 實機驗證

**What to build:** 這是手動驗證票，需要真人和實體裝置，不寫成自動測試。用 `epubgen` 產生兩本書，分別在 Apple Books 和 Kobo 上開啟，確認同一個檔案在兩邊都能以固定版面正常閱讀：

- 一本 RTL、有章節的書
- 一本 LTR、沒有章節的書

發現的問題記錄在這張票的 `## Comments`，並另開票卷修正。票 07 標示為「未證實」的 Kobo 項目也在這裡確認。

涵蓋 spec 的 user story 43、44。

**Blocked by:** 02、03、04、08、10

**Status:** ready-for-human

- [ ] Apple Books：兩本書都以固定版面開啟，圖片沒有被重排、切割或變形
- [ ] Apple Books：翻頁方向正確（RTL 的書往右翻到下一頁，LTR 相反）
- [ ] Apple Books：目錄可以跳到各章第一頁；沒有章節的書目錄也能正常顯示
- [ ] Apple Books：書櫃顯示正確的封面縮圖、書名與作者
- [ ] Apple Books：加上 `--spread` 的書在橫放時封面單獨、其後兩兩並排，左右頁配置正確
- [ ] Kobo：以上五項同樣確認
- [ ] Kobo：含 WebP 來源圖片的書（預設轉成 JPEG）可以正常顯示
- [ ] 票 07 標示為「未證實」的每個項目都有實機結論，並回寫到票 07
- [ ] 記錄測試用的裝置型號與系統／韌體版本
- [ ] （票 07 衍生）Kobo eInk：同一個檔案以 `.epub` 側載是否以固定版面顯示；改名為 `.fxl.kepub.epub` 後的差異（版面、翻頁方向、目錄、封面縮圖、書籤與筆記）
- [ ] （票 07 衍生）Kobo：`--spread` 的封面標記（`page-spread-center`）、RTL 第二頁起右左順序，以及帶前綴與不帶前綴的跨頁屬性寫法，哪一種顯示正確
- [ ] （票 07 衍生）Kobo：`--cover` 指向書外圖片時封面縮圖是否正常；GIF 當封面時是否顯示
- [ ] （票 07 衍生）Kobo：以 `--keep-webp` 產生的書，WebP 圖片是否顯示（官方文件說支援，社群回報 Kobo Forma 韌體 4.38 顯示空白）
- [ ] （票 07 衍生）Kobo：超過 3,800,000 像素的頁面翻頁是否明顯變慢
- [ ] （票 07 衍生）Apple Books：本次未能讀取 Apple 文件全文，確認 viewport 與跨頁屬性的實際行為
