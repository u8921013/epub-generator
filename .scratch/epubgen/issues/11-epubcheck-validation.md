# 11: EPUBCheck 自動驗證

**What to build:** 測試會對工具產出的 EPUB 執行 EPUBCheck，並要求沒有任何錯誤，讓產出的書在其他符合標準的閱讀器上也有機會正常運作。這組測試掛在同一個測試接縫上（透過 CLI 進入點產生 EPUB，再交給 EPUBCheck）。環境裡沒有 Java 或 EPUBCheck 時，這組測試自動跳過，不算失敗。

提供一個容易重用的做法，讓其他票卷加入新的選項或結構時，可以用很少的程式碼把新情境也送進 EPUBCheck。EPUBCheck 回報的錯誤要在這張票修掉。

涵蓋 spec 的 user story 45。

**Blocked by:** 01

**Status:** ready-for-agent

- [x] 環境有 EPUBCheck 時，測試會對產出的 EPUB 執行它，有任何錯誤就失敗，並在失敗訊息中顯示 EPUBCheck 的輸出
- [x] 環境沒有 Java 或 EPUBCheck 時，這組測試被標示為跳過，其他測試照常執行
- [x] 至少涵蓋票 01 的基本情境；這張票開工時已完成的其他功能（閱讀方向、雙頁、章節、metadata、WebP 轉檔）也各有一個情境
- [x] 新增一個 EPUBCheck 情境不需要重複撰寫呼叫 EPUBCheck 的程式碼
- [x] 說明文件記載如何在本機安裝 EPUBCheck 以執行這組測試
- [x] 目前所有情境的產出都通過 EPUBCheck，沒有錯誤

## Comments

完成。安裝 EPUBCheck 5.4.0（官方 GitHub release，大小與 SHA-256 皆與 release 資訊相符）到 `.tools/`，11 個情境全部通過，沒有錯誤也沒有警告：基本、LTR、兩種雙頁、章節、章節加雙頁、書名作者語言、特殊字元、含 WebP、外部封面、跳過損毀圖片。EPUBCheck 以 EPUB 3.4 規則檢查。

- 以故意弄壞的 EPUB（把 `rendition:layout` 改成不合法的值）確認 EPUBCheck 確實會回報錯誤並以非零代碼結束，測試不是永遠通過。
- 沒有出現原本擔心的問題：含 WebP 的書沒有缺 fallback 的錯誤，無前綴的 `page-spread-left/right` 也沒有警告。
- 這證明結構合法，不代表 Apple Books 與 Kobo 實際顯示正確，後者留給票 12。
- 全部 11 個 EPUBCheck 情境約需 85 秒（每次啟動 Java 約 8 秒）。
