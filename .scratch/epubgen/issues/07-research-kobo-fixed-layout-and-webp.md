# 07: 查證 Kobo 的 fixed layout 設定與 WebP 支援

**What to build:** 這是研究票，不產出程式碼。spec 的 Further Notes 指出有兩點在需求討論時沒有可靠的查證結果，實作前必須查官方文件或其他高可信度的一手來源，不能憑印象寫：

1. Kobo 顯示 fixed layout EPUB 需要哪些額外設定，以及不同機型與韌體的支援程度。
2. Kobo 是否支援 WebP。目前「WebP 預設轉 JPEG」是以不支援為前提的保守做法。

把結論寫在這張票的 `## Answer` 段落，讓票 08 和票 10 的實作者可以直接照著做。每個結論都要附來源連結；查不到可靠來源的部分要明確標示為「未證實」，並說明建議的保守做法，留給票 12 的實機驗證確認。

**Blocked by:** None (can start immediately)

**Status:** ready-for-agent

- [x] 列出 Kobo 顯示 fixed layout EPUB 所需的具體設定（要加在哪份文件、寫什麼），每項附來源
- [x] 說明這些設定與 Apple Books 是否衝突，同一份 EPUB 能否兩邊通用
- [x] 說明已知的機型或韌體差異，包含 `.epub` 與 `.kepub.epub` 的行為差別（如果有）
- [x] 回答 Kobo 是否支援 WebP，並說明「預設轉 JPEG」這個決定是否需要調整
- [x] 沒有可靠來源的結論標示為「未證實」，並列入票 12 的實機確認項目
- [x] 若結論與 spec 的既有決定衝突，在票中明確指出，不自行修改 spec

## Answer

查證日期：2026-11-16。標記為「**未證實**」的項目沒有可靠的一手來源，建議的保守做法已寫明，並已列入票 12 的實機確認。

**來源與可信度說明**

- 一手來源是 Kobo 自己維護的 [kobolabs/epub-spec](https://github.com/kobolabs/epub-spec)（下稱 Kobo 規格）。該文件沒有標示最後更新日期，只寫 Kobo 目前支援 EPUB 3.3，並使用 EPUBCheck 4.2.6 檢查。
- 下文引用的英文原句，是透過網頁摘要工具從 Kobo 規格擷取的，可能與原文有細微出入。實作前請對照[原文](https://github.com/kobolabs/epub-spec)。
- Kobo 規格以平台區分（eInk、Desktop、Android、iOS），**完全沒有列出機型或韌體版本**。所以「不同機型與韌體的支援程度」這一題，官方來源給不出答案。

### 一、Kobo 顯示 fixed layout 所需的設定

| # | 設定 | 結論 | 目前輸出是否已符合 |
|---|------|------|------------------|
| 1 | OPF metadata 的 `rendition:layout` | 設為 `pre-paginated`，Kobo 以此判斷是否為固定版面（Kobo 規格「Fixed Layout (FXL) Support」） | 已符合 |
| 2 | `rendition:spread` | 只在 metadata（整本書）層級讀取，值可為 `auto`、`landscape`、`none`、`both`、`portrait`。`auto` 與 `landscape` 效果相同，雙頁只在橫放出現；`none` 用於不要並排；`both` 會在直放也並排，Kobo 要求謹慎使用（Kobo 規格「Two Pages Display in Portrait Orientation on Android」） | 已符合（預設 `none`，`--spread` 時 `landscape`） |
| 3 | viewport 一致 | 「Ensure that the viewport listed in all the CSS and XHTML files is the same.」圖片的寬高比應與 viewport 相符（Kobo 規格「Viewport Issues」） | 已符合（每頁 meta viewport 與 CSS 尺寸相同，且等於圖片尺寸） |
| 4 | 圖片尺寸 | 建議每個 viewport 不超過 3,800,000 像素，單圖頁約 1950x1950。超過仍可使用，但下載較慢、佔用更多記憶體（Kobo 規格「Image Dimensions」、「Limitations and Maximums」） | **未處理**，見下方建議 |
| 5 | 封面頁 | 「Cover images must be contained in their own XHTML files.」建議用 `<img>`，不要用 CSS background（Kobo 規格「Cover Images」） | 已符合（每頁獨立 XHTML、用 `<img>`）。`--cover` 指向書外圖片時，該圖不在任何 XHTML 裡，Kobo 的行為**未證實** |
| 6 | `com.kobobooks.display-options.xml` | 「This file is not required for EPUB3 FXL content.」 | 不需要 |
| 7 | spine 的 `page-progression-direction` | Kobo 支援（Kobo 規格「Right to Left」） | 已符合 |
| 8 | Image-Based FXL Reader（僅 Android、iOS） | 觸發條件：每個 spine 項目都有圖片、沒有 SMIL、相鄰兩頁不引用同一張圖、圖片不是用 CSS background 設定；否則退回預設閱讀器 | 已符合 |
| 9 | 封面格式 | 規格指出**封面不支援 GIF** | **未處理**。第一張圖或 `--cover` 是 GIF 時，Kobo 可能不顯示封面 |

沒有任何一項是 Kobo 專用、會與 Apple Books 衝突的設定。

### 二、與 Apple Books 是否衝突、同一份 EPUB 能否兩邊通用

- Apple 的[Apple Books Asset Guide](https://help.apple.com/itc/booksassetguide/en.lproj/static.html)同樣以 `rendition:layout` = `pre-paginated` 宣告固定版面，每頁（或每個跨頁）是獨立的 XHTML，viewport 尺寸須與 meta viewport 一致。這些與 Kobo 要求相容。
- Apple 規定固定版面書裡的圖片不得超過 5.6 百萬像素；Kobo 建議的 3.8 百萬像素較嚴格，所以以 Kobo 的建議為準，兩邊都能滿足。
- **本段 Apple 的內容只來自搜尋結果摘要。** 我嘗試直接讀取 Apple 文件頁面但被擋下，所以沒有核對全文。Apple 對 `page-spread-*` 與 viewport 的更細要求**未證實**。
- 結論：在 metadata 層級，兩邊設定沒有衝突，同一個檔案原則上可以通用。**真正的風險是下一節的副檔名問題，以及第四節的跨頁屬性，而不是 metadata。**

### 三、`.epub` 與 `.kepub.epub` 的差別（影響「同一個檔案兩邊通用」）

Kobo 規格「Sideloading for Testing Purposes」（eInk 側載）寫明：

- 副檔名維持 `.epub`：會「trigger the ADE display engine」，可以用書籤與筆記。
- `.kepub.epub`：觸發 Kobo WebKit，停用書籤與筆記，封面縮圖可能不顯示。
- 固定版面書：「To trigger the Kobo WebKit for a Fixed Layout title, change the extension to `.fxl.kepub.epub`.」

重點是：**Kobo 規格沒有說明維持 `.epub` 時，ADE 能不能正確顯示 fixed layout。** 第三方資訊互相矛盾，而且都只有搜尋結果摘要，我沒有讀全文：

- 一則 MobileRead 發文說，OPF 設為 `rendition:layout` = `pre-paginated` 時，Kobo 會當成固定版面處理。這是個人經驗，Kobo 沒有確認。
- Jutoh 的知識庫文章說，側載固定版面 EPUB 到 eInk 時會出現文字與圖片錯位，改用 USB 傳輸可以正常顯示。

結論：**「同一個 `.epub` 在 Kobo eInk 上以固定版面開啟」未證實，是這個專案最大的相容性風險。** 這與 spec 的「不另外產生 Kobo 專用檔」可能衝突，因為使用者可能需要把檔案改名為 `.fxl.kepub.epub`。我不自行修改 spec，建議在票 12 實機確認：

1. 同一個檔案以 `.epub` 側載，是否以固定版面顯示。
2. 同一個檔案改名為 `.fxl.kepub.epub` 後的差異（版面、封面縮圖、翻頁方向）。
3. 若 `.epub` 不行，由你決定處理方式：在 `README` 與 `--help` 說明改名即可、新增輸出副檔名選項，或調整 spec。

另外，Kobo 規格提到 EPUB 2 的固定版面內容在 Desktop 與 eInk 上不可用。本專案輸出 EPUB 3，不受影響。

### 四、跨頁屬性（影響票 02 已完成的 `--spread`，由票 10 處理）

Kobo 規格關於 `page-spread-left` 與 `page-spread-right` 的內容：

- 「The Kobo iOS app will always display the first page centered and as its own spread.」
- 建議第一個 spine 項目「do not indicate a page spread property」，之後再從左頁開始。
- 「applying `properties="page-spread-right"` to the first spine item in rtl books will throw off the page sequence on iOS.」

與目前輸出比對：

- 目前 `--spread` 對封面標記 `rendition:page-spread-center`。Kobo 規格**完全沒有提到 `page-spread-center`**，所以它在 Kobo 上的效果未證實；Kobo 建議的做法是第一個項目不要有任何跨頁屬性。
- Kobo 規格範例使用的是不帶前綴的 `page-spread-left`／`page-spread-right`，我們使用的是帶 `rendition:` 前綴的寫法。Kobo 是否兩種都認、哪一種符合 EPUB 3.3 與 EPUBCheck，**未證實**。
- RTL 書第二頁起標記為右、左、右、左，是依 spec 的描述。Kobo 規格只警告「不要把 `page-spread-right` 放在第一個項目」，沒有直接規定 RTL 第二頁該是左還是右。**未證實**，票 12 實機確認。

建議（供票 10 採用，仍需 EPUBCheck 與實機驗證）：封面不加任何跨頁屬性；封面之後的頁面是否改用不帶前綴的寫法，先用 EPUBCheck 判定，再由票 12 實機決定。

### 五、不同機型與韌體的支援程度

官方來源只有平台層級的差異，沒有機型或韌體：

- Image-Based FXL Reader：只在 Android、iOS。
- iOS：第一頁一律置中、單獨成頁。
- FXL 的 SMIL：只在 Android、iOS（本專案不使用 SMIL）。

eInk 各機型與韌體對固定版面的支援程度：**未證實**，列入票 12。測試時請記錄機型與韌體版本。

### 六、Kobo 是否支援 WebP

- **官方文件說支援**：Kobo 規格「Supported Image Formats」寫 Kobo 平台支援核心圖片類型，包括 JPG、PNG、SVG 與 WebP。
- **實際使用經驗說不支援（至少在某些 eInk 韌體上）**：
  - 一篇 [MobileRead 發文](https://www.mobileread.com/forums/showthread.php?p=4597504)指出，Kobo Forma（N782）韌體 4.38.23697 可以開啟 EPUB 3.3，但裡面的 WebP 圖片無法顯示，並推測原因是該機使用 Qt 5.2.1，而 WebP 支援從 Qt 5.3.0 才開始。
  - [ePubLift 的發布說明](https://newreleases.io/project/github/ePubLift/epublift/release/cli-v1.8.0)也寫 stock Kobo 會把 WebP 顯示為空白。
  - 這兩項來源很可能出自同一位作者（他同時提供了一個非官方的 WebP 外掛），所以是單一來源的個人回報，不是獨立驗證。
- 結論：官方文件與實際回報互相矛盾。**WebP 預設轉成 JPEG 的決定不需要調整**，因為保守做法在兩種情況下都安全。`--keep-webp` 建議在 `--help` 與說明文件標明「Kobo eInk 上可能顯示空白」。
- 另一個與 WebP 有關的線索：一則 MobileRead 討論提到 EPUBCheck 可能對 WebP 圖片回報缺少 fallback 的錯誤。這只來自搜尋結果摘要，**未證實**，票 11 的 EPUBCheck 測試會自然驗證，可作為 `--keep-webp` 情境的測試項目。

### 七、對其他票卷的建議

- **票 08**：維持「WebP 預設轉 JPEG」。GIF 若會成為封面，Kobo 不支援；是否要把 GIF 封面轉成 JPEG，建議在票 08 的範圍內討論。
- **票 09**：`--max-size` 建議在說明文件中提到 Kobo 的 3,800,000 像素建議，必要時可以把它當成範例值。是否設為預設值，由你決定。
- **票 10**：範圍比原本預期小。metadata 與 viewport 已符合，主要工作是第四節的跨頁屬性調整，加上 `--help` 與說明文件對 `.fxl.kepub.epub` 的說明。是否需要輸出副檔名選項，等票 12 的結果。
- **票 11**：加入 `--keep-webp` 與 `--spread` 的 EPUBCheck 情境。
- **票 12**：新增下列實機確認項目（已寫入該票）。

### 與 spec 的衝突

- spec「不另外產生 Kobo 專用檔」可能與第三節衝突（取決於實機結果）。
- spec 的 RTL 跨頁順序（第二頁起右、左）與 Kobo 的建議沒有直接矛盾，但 Kobo 對封面的建議（不加任何屬性）與目前的 `page-spread-center` 不同。

以上都已記錄，spec 沒有被修改。

## 實機結果（來自票 12，2026-11-16）

使用者回報票 12 的實機驗證都通過，WebP 與 GIF 沒有太大影響，大圖（約 13.5M 像素）載入較慢。因為回報沒有附上裝置型號、韌體版本，也沒有說明 Kobo 純 `.epub` 與 `.fxl.kepub.epub` 的差異，所以第三節（`.epub` 是否固定版面）、第四節（跨頁屬性）、第六節（WebP）的「未證實」標記**維持不變**，只在這裡記錄這個初步結果。補齊細節後再回寫。
