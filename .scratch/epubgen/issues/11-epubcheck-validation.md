# 11: EPUBCheck 自動驗證

**What to build:** 測試會對工具產出的 EPUB 執行 EPUBCheck，並要求沒有任何錯誤，讓產出的書在其他符合標準的閱讀器上也有機會正常運作。這組測試掛在同一個測試接縫上（透過 CLI 進入點產生 EPUB，再交給 EPUBCheck）。環境裡沒有 Java 或 EPUBCheck 時，這組測試自動跳過，不算失敗。

提供一個容易重用的做法，讓其他票卷加入新的選項或結構時，可以用很少的程式碼把新情境也送進 EPUBCheck。EPUBCheck 回報的錯誤要在這張票修掉。

涵蓋 spec 的 user story 45。

**Blocked by:** 01

**Status:** ready-for-agent

- [ ] 環境有 EPUBCheck 時，測試會對產出的 EPUB 執行它，有任何錯誤就失敗，並在失敗訊息中顯示 EPUBCheck 的輸出
- [ ] 環境沒有 Java 或 EPUBCheck 時，這組測試被標示為跳過，其他測試照常執行
- [ ] 至少涵蓋票 01 的基本情境；這張票開工時已完成的其他功能（閱讀方向、雙頁、章節、metadata、WebP 轉檔）也各有一個情境
- [ ] 新增一個 EPUBCheck 情境不需要重複撰寫呼叫 EPUBCheck 的程式碼
- [ ] 說明文件記載如何在本機安裝 EPUBCheck 以執行這組測試
- [ ] 目前所有情境的產出都通過 EPUBCheck，沒有錯誤
