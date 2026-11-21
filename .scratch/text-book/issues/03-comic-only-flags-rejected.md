# 03: 漫畫專用旗標對文字書報錯，並更新 `--help`

**What to build:** 使用者對文字書使用 `--direction`（任何值）或 `--spread` 時，得到明確的錯誤訊息，說明這些旗標只對漫畫書有效，結束代碼 1、不產生輸出檔。`epubgen --help` 說明輸入可以是放滿圖片或 Markdown 檔的資料夾，並註明 `--direction`、`--spread` 只對漫畫書有效。

涵蓋 spec 的 user story 55、57。

**Blocked by:** 01（`--direction` 未指定）、02（最簡單的文字書）

**Status:** ready-for-agent

- [ ] 文字書加 `--direction rtl` 或 `--direction ltr` → 錯誤，訊息指出只對漫畫書有效
- [ ] 文字書加 `--spread` → 錯誤，訊息指出只對漫畫書有效
- [ ] 錯誤時結束代碼為 1，不留下輸出檔
- [ ] 漫畫書使用這兩個旗標的行為不變
- [ ] `--help` 的位置參數說明涵蓋 Markdown 資料夾，兩個旗標的說明註明只對漫畫書有效
