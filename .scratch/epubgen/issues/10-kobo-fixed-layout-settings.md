# 10: 加入 Kobo 的 fixed layout 設定

**What to build:** 同一個 EPUB 檔在 Kobo 上也能以固定版面開啟，使用者不用為不同裝置各轉一次。依照票 07 查證出的結論，把 Kobo 需要的 fixed layout 設定加進輸出，不另外產生 Kobo 專用檔，也不能破壞 Apple Books 的顯示。

只實作票 07 中有來源支持的設定。票 07 標示為「未證實」的項目，依它建議的保守做法處理，並留給票 12 實機確認。

涵蓋 spec 的 user story 44（自動化可驗證的部分）。

**Blocked by:** 01、07

**Status:** ready-for-agent

- [ ] 輸出的 EPUB 含有票 07 列出的每一項 Kobo 設定
- [ ] 這些設定在所有選項組合下都存在（至少涵蓋預設、`--direction ltr`、`--spread` 中已實作的部分）
- [ ] 仍然只產生一個輸出檔
- [ ] 既有測試全部通過，票 01 定義的 EPUB 結構沒有被破壞
- [ ] 若環境有 EPUBCheck，產出的 EPUB 沒有錯誤
- [ ] 以上行為都有透過 CLI 進入點的測試
