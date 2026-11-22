# 10: 實機測試範本與 Apple Books / Kobo 驗收

**What to build:** 在實機測試書產生腳本中加入一本文字書範本，並在 Apple Books 與 Kobo 實機上驗收。範本涵蓋：有部有章、中文軟換行、表格、程式碼區塊、插圖、書內連結（跨章、跨部、章內錨點）、封面頁。另外用使用者手上那本 234 章的小說資料夾（`pages/`，只在本機、不進版本控制）做一次真實驗收。

實機驗收需要人操作，所以這張票是 `ready-for-human`；產生範本的腳本可以由 agent 先完成。驗收結果與發現的問題記在本票 Comments，問題另開票。

涵蓋 spec 的 user story 66，以及「手動驗證」一節。

**Blocked by:** 03、04、05、06、07、08、09

**Status:** ready-for-human

- [x] 實機測試書產生腳本能產生文字書範本，範本涵蓋上述所有情境
- [x] Apple Books：文字隨字級重排、目錄兩層可跳轉、書內連結可跳、插圖不超出螢幕、封面縮圖與封面頁正確
- [ ] Kobo：同上各項
- [ ] Kobo 對兩層目錄的顯示方式記錄在 Comments
- [ ] `pages/` 小說：234 章、章名與順序正確，兩台閱讀器都能開啟（Apple Books 已通過，Kobo 待測）
- [ ] 驗收結果記錄在本票 Comments

## Comments

**2026-11-22（agent）** 腳本部分完成：`scripts/make_device_test_books.py` 新增
`T-text-book`（序章在根目錄，「第一部 出發」「第二部 歸來」兩個子資料夾成為兩部；含中文軟換行、
表格、刪除線、程式碼區塊、3000x1200 橫幅與 1200x3600 直幅插圖、跨章／跨部／章內錨點連結、
`--cover` 封面頁），以及在 `pages/` 存在時產生 `U-pages-novel`。兩本都通過 EPUBCheck 5.4.0
（0 錯誤 0 警告），產生時沒有任何警告；小說目錄 234 章，第 1、2、3、232、233、234 章章名與順序抽查正確。
文字書只產生 `.epub`（`.kepub.epub` 不在範圍內）。實機驗收（下面其餘勾選項）待使用者在
Apple Books 與 Kobo 上進行，結果補記於此。

**2026-11-22（使用者）** Apple Books：`T-text-book` 與 `U-pages-novel` 兩本都驗收通過。
Kobo 先跳過，本票維持 `ready-for-human`，等 Kobo 測完再勾選其餘項目並結案。

**2026-11-22（使用者）** Readium Web 閱讀器：以 code review 修正後的程式（commit `16e3b35`）重新產生
`T-text-book` 與 `U-pages-novel`，開啟都沒有問題。這是額外的佐證，不取代 Kobo 驗收。

Kobo 驗收延到後續階段，屆時一併確認 code review（`docs/code-review/2026-11-22.md`）第 12 項：
封面頁 CSS 的 `max-height: 100vh` 在 Kobo 側載純 `.epub`（Adobe RMSDK）時是否生效、細長封面圖會不會跨頁。
若會跨頁，再評估改用 SVG 包裝封面圖或其他相容寫法。

