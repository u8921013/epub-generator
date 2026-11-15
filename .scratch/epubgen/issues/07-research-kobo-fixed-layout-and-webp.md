# 07: 查證 Kobo 的 fixed layout 設定與 WebP 支援

**What to build:** 這是研究票，不產出程式碼。spec 的 Further Notes 指出有兩點在需求討論時沒有可靠的查證結果，實作前必須查官方文件或其他高可信度的一手來源，不能憑印象寫：

1. Kobo 顯示 fixed layout EPUB 需要哪些額外設定，以及不同機型與韌體的支援程度。
2. Kobo 是否支援 WebP。目前「WebP 預設轉 JPEG」是以不支援為前提的保守做法。

把結論寫在這張票的 `## Answer` 段落，讓票 08 和票 10 的實作者可以直接照著做。每個結論都要附來源連結；查不到可靠來源的部分要明確標示為「未證實」，並說明建議的保守做法，留給票 12 的實機驗證確認。

**Blocked by:** None (can start immediately)

**Status:** ready-for-agent

- [ ] 列出 Kobo 顯示 fixed layout EPUB 所需的具體設定（要加在哪份文件、寫什麼），每項附來源
- [ ] 說明這些設定與 Apple Books 是否衝突，同一份 EPUB 能否兩邊通用
- [ ] 說明已知的機型或韌體差異，包含 `.epub` 與 `.kepub.epub` 的行為差別（如果有）
- [ ] 回答 Kobo 是否支援 WebP，並說明「預設轉 JPEG」這個決定是否需要調整
- [ ] 沒有可靠來源的結論標示為「未證實」，並列入票 12 的實機確認項目
- [ ] 若結論與 spec 的既有決定衝突，在票中明確指出，不自行修改 spec
