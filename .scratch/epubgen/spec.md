# epubgen：把圖片資料夾轉成漫畫 EPUB

Status: ready-for-agent

## Problem Statement

我手上有一批漫畫，每本是一個放滿圖片的資料夾。我想在 Apple Books 和 Kobo 上閱讀，但這兩個閱讀器都不能直接開圖片資料夾。手動把圖片包成 EPUB 很繁瑣，而且漫畫需要固定版面、正確的翻頁方向和章節目錄，一般的轉檔工具常常會把圖片縮放、切割，或把翻頁方向弄反。

## Solution

提供一個名為 `epubgen` 的命令列工具。使用者給它一個圖片資料夾，它產生一個 EPUB 3 fixed layout（預先分頁）的漫畫電子書：每張圖片是獨立的一頁，頁面順序依檔名自然排序，子資料夾變成章節目錄，翻頁方向可選。同一個輸出檔在 Apple Books 和 Kobo 都能正常閱讀。

最簡單的用法只需要一個參數：

```
epubgen ./my-comic
```

輸出 `my-comic.epub`，放在輸入資料夾旁邊。

## User Stories

### 基本轉換

1. As a 漫畫讀者, I want 用一個指令把圖片資料夾轉成 EPUB, so that 我不用手動打包。
2. As a 漫畫讀者, I want 每張圖片成為獨立的一頁且版面固定, so that 圖片不會被重排、切割或變形。
3. As a 漫畫讀者, I want 頁面依檔名自然排序（`2.jpg` 排在 `10.jpg` 前）, so that 頁碼沒有補零時順序也正確。
4. As a 漫畫讀者, I want 每一頁的版面尺寸等於該圖片自己的像素尺寸, so that 封面和內頁尺寸不同時各自都能正確顯示。
5. As a 漫畫讀者, I want 圖片預設原樣打包、不重新壓縮, so that 畫質不會因為轉檔而下降。
6. As a 漫畫讀者, I want 工具接受 JPEG、PNG、WebP、GIF, so that 常見來源的漫畫都能直接使用。
7. As a 漫畫讀者, I want 非圖片檔案（例如 `.DS_Store`、`.txt`）被自動忽略, so that 資料夾裡的雜檔不會造成錯誤或混進書裡。

### 閱讀方向與跨頁

8. As a 日漫讀者, I want 預設翻頁方向是從右到左, so that 不加任何參數就能照日漫的習慣閱讀。
9. As a 美漫或台漫讀者, I want 用 `--direction ltr` 改成從左到右, so that 翻頁方向符合該作品的排版。
10. As a 手機讀者, I want 預設每頁單獨顯示, so that 小螢幕上不會被硬塞成雙頁。
11. As a 平板讀者, I want 用 `--spread` 啟用雙頁模式, so that 橫放時可以像實體書一樣左右並排。
12. As a 平板讀者, I want 雙頁模式下封面單獨一頁、之後兩兩並排, so that 原本的跨頁畫面能正確對齊。
13. As a 日漫讀者, I want 雙頁模式下左右頁的配置跟隨閱讀方向, so that RTL 的書右頁在先、LTR 的書左頁在先。

### 章節與目錄

14. As a 漫畫讀者, I want 沒有子資料夾時整個資料夾就是一本書, so that 單話或單行本可以直接轉。
15. As a 漫畫讀者, I want 每個子資料夾成為一章, so that 我可以把多話整理在一個資料夾裡一次轉成一本。
16. As a 漫畫讀者, I want 章節依子資料夾名稱自然排序, so that 「第 2 話」排在「第 10 話」前面。
17. As a 漫畫讀者, I want 章節名稱取自子資料夾名稱, so that 目錄不需要另外設定。
18. As a 漫畫讀者, I want 閱讀器的目錄能直接跳到各章第一頁, so that 我可以快速找到想看的那一話。
19. As a 漫畫讀者, I want 沒有章節的書也有合法的目錄, so that 閱讀器不會因為缺目錄而拒絕開啟。

### 封面與書籍資訊

20. As a 漫畫讀者, I want 預設用第一張圖當封面, so that 書櫃裡有正確的縮圖而不用額外設定。
21. As a 漫畫讀者, I want 用參數指定其他圖片當封面, so that 第一張圖不是封面時也能有正確的縮圖。
22. As a 漫畫讀者, I want 書名預設取自資料夾名稱, so that 我不用每次都輸入書名。
23. As a 漫畫讀者, I want 用參數覆寫書名, so that 資料夾名稱不適合當書名時可以修正。
24. As a 漫畫讀者, I want 用參數指定作者, so that 書櫃可以依作者整理。
25. As a 漫畫讀者, I want 用參數指定語言, so that 閱讀器能正確標示這本書的語言。

### 圖片處理

26. As a Kobo 使用者, I want WebP 圖片預設自動轉成 JPEG, so that 不支援 WebP 的閱讀器也能顯示。
27. As a 漫畫讀者, I want 用參數關掉 WebP 轉檔, so that 我確定閱讀器支援時可以保留原檔。
28. As a 儲存空間有限的讀者, I want 選用的壓縮參數, so that 我可以縮小檔案大小。
29. As a 儲存空間有限的讀者, I want 選用的縮放參數把圖片縮到指定尺寸上限, so that 超高解析度的掃圖不會佔用太多空間。
30. As a 漫畫讀者, I want 圖片經過轉檔或縮放後，該頁的版面尺寸跟著處理後的圖片, so that 頁面不會出現留白或變形。

### 輸出

31. As a 漫畫讀者, I want 輸出檔預設放在輸入資料夾旁邊、檔名是 `<書名>.epub`, so that 我不用想輸出路徑。
32. As a 漫畫讀者, I want 用 `-o` 指定輸出路徑, so that 我可以直接輸出到同步資料夾或閱讀器的掛載點。
33. As a 漫畫讀者, I want 完成時看到輸出檔的路徑和總頁數, so that 我知道轉換成功以及檔案在哪裡。
34. As a 漫畫讀者, I want 輸入資料夾完全不被修改, so that 原始圖片保持原樣。

### 錯誤處理

35. As a 漫畫讀者, I want 輸入路徑不存在或不是資料夾時看到清楚的錯誤訊息, so that 我知道是路徑打錯。
36. As a 漫畫讀者, I want 資料夾裡沒有任何圖片時直接報錯, so that 不會產生一本空書。
37. As a 漫畫讀者, I want 圖片損毀時預設報錯並指出是哪個檔案, so that 我可以修好或換掉那張圖。
38. As a 漫畫讀者, I want 用 `--skip-broken` 跳過損毀的圖片並列出被跳過的檔名, so that 少數壞圖不會擋住整本書。
39. As a 漫畫讀者, I want 輸出檔已存在時預設拒絕覆蓋, so that 我不會不小心蓋掉之前的檔案。
40. As a 漫畫讀者, I want 用 `--force` 明確允許覆蓋, so that 重新轉檔時不用先手動刪除舊檔。
41. As a 漫畫讀者, I want 任何失敗都以非零結束代碼結束且不留下半成品檔案, so that 我可以在腳本裡批次處理並可靠地判斷成敗。
42. As a 漫畫讀者, I want 參數值不合法（例如 `--direction up`）時看到用法說明, so that 我知道正確的寫法。

### 相容性與安裝

43. As a Apple Books 使用者, I want 產出的 EPUB 能在 Apple Books 以固定版面開啟, so that 我可以在 iPhone、iPad 和 Mac 上閱讀。
44. As a Kobo 使用者, I want 同一個 EPUB 檔在 Kobo 上也能以固定版面開啟, so that 我不用為不同裝置各轉一次。
45. As a 漫畫讀者, I want 產出的 EPUB 通過 EPUBCheck, so that 它在其他符合標準的閱讀器上也有機會正常運作。
46. As a 使用者, I want 用 `pipx install .` 安裝後在任何目錄直接輸入 `epubgen`, so that 我不用每次切換到專案資料夾。
47. As a 使用者, I want `epubgen --help` 列出所有參數與預設值, so that 我不用查文件。
48. As a 使用者, I want `epubgen --version` 顯示版本, so that 我知道目前裝的是哪一版。

## Implementation Decisions

### 技術選型

- 用 Python 實作，套件與指令名稱都是 `epubgen`，專案資料夾維持 `epub-generator`。
- 做成可安裝的套件，提供 `epubgen` 這個 console script 進入點，支援 `pipx install .`。
- 圖片的讀取、尺寸判斷、轉檔與縮放使用 Pillow。
- EPUB 的打包使用標準函式庫的 zip 功能，不依賴第三方 EPUB 函式庫，以便完全掌控 fixed layout 與 Kobo 相關的 metadata。

### 模組劃分

對外只有一個深模組的介面：「給定輸入資料夾和選項，產生一個 EPUB 檔」。CLI 是這個介面上的薄包裝，只負責解析參數、呼叫、把結果或錯誤轉成訊息與結束代碼。內部分成三個職責：

- **書籍掃描**：讀取輸入資料夾，套用副檔名過濾與自然排序，判斷有無子資料夾，產出「書 → 章 → 頁」的結構。
- **圖片處理**：驗證圖片可讀、取得像素尺寸，並依選項做 WebP 轉 JPEG、壓縮、縮放。預設不動原圖位元組。
- **EPUB 組裝**：依書籍結構與處理後的圖片產生 package document、navigation document、每頁的 XHTML，並打包成 EPUB。

### CLI 介面

已定案的參數：

- 位置參數：輸入資料夾。
- `--direction rtl|ltr`：閱讀方向，預設 `rtl`。
- `--spread`：啟用雙頁模式，預設關閉。
- `-o`：輸出路徑。預設為輸入資料夾的同層目錄下的 `<書名>.epub`。
- `--skip-broken`：跳過無法讀取的圖片。
- `--force`：允許覆蓋已存在的輸出檔。

功能已定案、名稱由實作者決定的參數（下列為建議名稱）：

- `--title`：覆寫書名，預設為輸入資料夾名稱。
- `--author`：作者。
- `--language`：語言代碼。
- `--cover`：指定封面圖片。
- `--keep-webp`：關閉 WebP 轉 JPEG。
- `--quality`：重新壓縮的 JPEG 品質。
- `--max-size`：縮放的尺寸上限。
- `--help`、`--version`。

### EPUB 結構

- 輸出 EPUB 3，package metadata 宣告為 pre-paginated 的 fixed layout。
- 每一頁是一份 XHTML 文件，內含一張圖片，並宣告與該圖片像素尺寸相同的 viewport。
- package document 的 spine 依頁面順序排列，並設定對應 `--direction` 的 page progression direction。
- 預設所有頁面不合併成跨頁。啟用 `--spread` 時，封面單獨顯示，其後頁面依閱讀方向交替標記為左頁與右頁。
- navigation document 在有章節時每章一個項目，指向該章第一頁。沒有章節時提供一個指向第一頁的項目，確保目錄合法。
- 封面圖片在 manifest 中標記為 cover image。
- 每本書產生唯一識別碼與最後修改時間，滿足 EPUB 3 的必要 metadata。
- `mimetype` 必須是壓縮檔中的第一個項目且不壓縮。
- 同一份輸出加入 Kobo 需要的 fixed layout 設定，不另外產生 Kobo 專用檔。具體需要哪些設定見 Further Notes 的待查證事項。

### 輸入規則

- 接受的副檔名：JPEG（`.jpg`、`.jpeg`）、PNG、WebP、GIF，不分大小寫。其他檔案一律忽略。
- 頁面與章節都使用自然排序。
- 章節只看輸入資料夾的第一層子資料夾。

### 圖片處理規則

- 預設把原始檔案位元組原樣放進 EPUB。
- 例外：WebP 預設轉成 JPEG，可用參數關閉。
- 壓縮與縮放只有在使用者給了對應參數時才執行。
- 頁面的 viewport 一律取自最終放進 EPUB 的那張圖片。

### 錯誤處理

- 輸入路徑不存在或不是資料夾：報錯，非零結束。
- 沒有任何可用圖片（包含全部被 `--skip-broken` 跳過的情況）：報錯，非零結束。
- 圖片無法讀取：預設報錯並指出檔名。`--skip-broken` 時跳過並在結束時列出被跳過的檔案。
- 輸出檔已存在：預設報錯。`--force` 時覆蓋。
- 輸出先寫到暫存檔，成功後才移到目標路徑，失敗時不留下半成品。
- 錯誤訊息寫到標準錯誤輸出，成功訊息（輸出路徑與頁數）寫到標準輸出。

## Testing Decisions

### 什麼是好的測試

只測使用者觀察得到的行為：結束代碼、輸出訊息、輸出檔是否存在，以及把 EPUB 當 zip 解開後的內容。不測內部模組的函式簽名或彼此的呼叫方式，讓書籍掃描、圖片處理、EPUB 組裝三塊可以自由重構而不用改測試。

### 測試接縫

只有一個接縫：CLI 進入點。測試在同一個 Python 行程內以參數列表呼叫進入函式，等同使用者在終端機輸入指令。

- **輸入**：測試用 Pillow 在暫存資料夾即時產生小圖片，組成各種情境。不把二進位圖片檔放進版本控制。
- **觀察**：結束代碼、標準輸出與標準錯誤的內容、輸出檔路徑，以及解開 EPUB 後的 `mimetype`、package document、navigation document、各頁 XHTML 與圖片。

### 要涵蓋的情境

- 單層資料夾產生合法的 fixed layout EPUB，頁數與圖片數相同。
- 自然排序：`1, 2, 10` 的順序正確。
- 尺寸不同的圖片各自得到對應的 viewport。
- 預設閱讀方向為 RTL，`--direction ltr` 會改變 page progression direction。
- 預設無跨頁，`--spread` 時封面單獨、其後依閱讀方向交替左右頁。
- 子資料夾產生對應章節目錄，章節名稱與順序正確。
- 沒有子資料夾時目錄仍然合法。
- 預設封面是第一張圖，指定封面時改用指定的圖。
- 書名預設為資料夾名稱，作者、語言、書名參數會寫入 metadata。
- 非 WebP 圖片的位元組與原檔完全相同。
- WebP 預設轉成 JPEG，關閉轉檔時保留 WebP。
- 壓縮與縮放參數生效，且 viewport 跟著處理後的尺寸。
- 非圖片檔案被忽略。
- 輸出路徑的預設值與 `-o` 的行為。
- 各種錯誤：輸入路徑不存在、空資料夾、損毀圖片（有無 `--skip-broken`）、輸出檔已存在（有無 `--force`）、不合法的參數值。
- 失敗時不留下輸出檔，輸入資料夾不被修改。

### EPUBCheck

掛在同一個接縫上：對測試產出的 EPUB 執行 EPUBCheck，要求沒有錯誤。環境裡沒有 Java 或 EPUBCheck 時自動跳過這組測試，不讓它失敗。

### 手動驗證

Apple Books 和 Kobo 的實機確認是手動步驟，不寫成自動測試。每次改動 EPUB 結構後，用一本 RTL 有章節的書和一本 LTR 無章節的書各開一次，確認固定版面、翻頁方向、目錄與封面縮圖。

### 既有範例

專案是全新的，沒有可參考的既有測試。測試框架使用 `pytest`。

## Out of Scope

- 直排文字與 reflowable（可重排）版型。
- 設定檔（例如 `book.yaml`）。
- 自動把橫向的雙頁大圖切成左右兩頁。
- 網頁介面與桌面介面。
- 從網路抓取漫畫。
- 上架 Kindle 或其他平台所需的專用格式與轉檔。
- EPUB 2 輸出。
- 圖片資料夾以外的輸入，例如 CBZ、PDF、既有 EPUB。

## Further Notes

### 實作前需要查證

以下兩點在需求討論時沒有可靠的查證結果，實作對應功能前要先查官方文件或實機測試，不能憑印象寫：

- Kobo 顯示 fixed layout EPUB 需要哪些額外設定，以及不同機型與韌體的支援程度。
- Kobo 是否支援 WebP。目前「WebP 預設轉 JPEG」是以不支援為前提的保守做法。

### 需求討論沒有涵蓋、建議的預設做法

以下細節沒有被明確決定，實作者可採用建議做法，若有疑慮再回頭確認：

- **語言預設值**：沒有給語言參數時，建議預設 `zh-TW`，因為 EPUB 3 要求必須有語言。
- **根目錄與子資料夾同時有圖片**：建議根目錄的圖片排在最前面，不屬於任何章節。
- **多層子資料夾**：建議只把第一層當章節，更深層的圖片併入所屬的第一層章節並依路徑自然排序。
- **GIF 動畫**：建議原樣打包，不特別處理。
- **WebP 轉 JPEG 的品質**：建議使用高品質設定，並把帶透明度的圖片合成到白底。
- **書名含有檔名不允許的字元**：建議在產生預設輸出檔名時替換掉，但 metadata 裡的書名保留原樣。
- **`--cover` 指定的圖片**：建議接受資料夾內外的任何圖片。若該圖片本來就在頁面中，不重複加入。
