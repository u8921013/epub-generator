# 08: WebP 預設轉成 JPEG

**What to build:** 輸入資料夾裡的 WebP 圖片預設會自動轉成 JPEG 再放進 EPUB，讓不支援 WebP 的閱讀器也能顯示。使用者確定閱讀器支援時，可以用參數關掉轉檔、保留原檔（spec 的建議名稱是 `--keep-webp`）。其他格式的圖片仍然原樣打包。

採用 spec 建議的做法：轉檔使用高品質設定，帶透明度的圖片合成到白底。頁面的 viewport 一律取自最終放進 EPUB 的那張圖片。

實作前先讀票 07 的結論。如果票 07 發現 Kobo 支援 WebP，預設值是否要改需要回頭跟使用者確認，不要自行決定。

涵蓋 spec 的 user story 26、27、30。

**Blocked by:** 01、07

**Status:** ready-for-agent

- [x] 預設情況下，WebP 圖片在 EPUB 中是 JPEG，manifest 的 media type 與檔案內容一致
- [x] 轉檔後該頁的 viewport 等於轉檔後圖片的像素尺寸
- [x] 帶透明度的 WebP 轉檔後背景是白色
- [x] 關閉轉檔的參數存在時，WebP 位元組原樣放進 EPUB，media type 是 WebP
- [x] 非 WebP 圖片的位元組與原檔完全相同，不受這個功能影響
- [x] WebP 當封面時，cover image 指向轉檔後的圖片
- [x] 輸入資料夾裡的 WebP 原檔不被修改
- [x] `--help` 顯示這個參數與預設行為
- [x] 以上行為都有透過 CLI 進入點的測試

## Comments

完成。轉檔使用 JPEG 品質 95、色度不抽樣（4:4:4）、保留 ICC 色彩設定檔；帶透明度的圖（RGBA、LA、帶透明的 P 模式）合成到白底，半透明像素與白色混合。灰階與調色盤模式的 WebP 也會正確轉成 JPEG。

- 依票 07 的結論維持「預設轉 JPEG」，沒有調整預設值。`--keep-webp` 的 `--help` 說明寫的是「不是所有閱讀器都能顯示 WebP」。
- 外部 `--cover` 指向 WebP 時，同樣預設轉成 JPEG，加了 `--keep-webp` 則保留。
- 票 04 的 EPUBCheck 情境新增「webp-converted」與「webp-kept」兩個，12 個情境都通過，保留 WebP 的書沒有 fallback 錯誤。
- 因為 WebP 預設不再原樣打包，票 01 的「所有支援格式位元組不變」測試改為加上 `--keep-webp`。
- 動畫 WebP 只會轉出第一個畫格，spec 沒有規定動畫處理。
- 未處理：票 07 提到 GIF 當封面在 Kobo 不支援。這不在本票驗收範圍，需要另外決定是否把 GIF 封面轉成 JPEG。
