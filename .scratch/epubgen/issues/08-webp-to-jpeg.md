# 08: WebP 預設轉成 JPEG

**What to build:** 輸入資料夾裡的 WebP 圖片預設會自動轉成 JPEG 再放進 EPUB，讓不支援 WebP 的閱讀器也能顯示。使用者確定閱讀器支援時，可以用參數關掉轉檔、保留原檔（spec 的建議名稱是 `--keep-webp`）。其他格式的圖片仍然原樣打包。

採用 spec 建議的做法：轉檔使用高品質設定，帶透明度的圖片合成到白底。頁面的 viewport 一律取自最終放進 EPUB 的那張圖片。

實作前先讀票 07 的結論。如果票 07 發現 Kobo 支援 WebP，預設值是否要改需要回頭跟使用者確認，不要自行決定。

涵蓋 spec 的 user story 26、27、30。

**Blocked by:** 01、07

**Status:** ready-for-agent

- [ ] 預設情況下，WebP 圖片在 EPUB 中是 JPEG，manifest 的 media type 與檔案內容一致
- [ ] 轉檔後該頁的 viewport 等於轉檔後圖片的像素尺寸
- [ ] 帶透明度的 WebP 轉檔後背景是白色
- [ ] 關閉轉檔的參數存在時，WebP 位元組原樣放進 EPUB，media type 是 WebP
- [ ] 非 WebP 圖片的位元組與原檔完全相同，不受這個功能影響
- [ ] WebP 當封面時，cover image 指向轉檔後的圖片
- [ ] 輸入資料夾裡的 WebP 原檔不被修改
- [ ] `--help` 顯示這個參數與預設行為
- [ ] 以上行為都有透過 CLI 進入點的測試
