# 01: `--direction` 改成「未指定」時才套用預設值

**What to build:** 事先重構，讓後續的文字書能分辨使用者有沒有給 `--direction`。目前 CLI 層把 `--direction` 的預設值寫死成 `rtl`，程式分不出「沒給」與「給了 rtl」。改成 CLI 層預設為「未指定」，由建書流程依書的種類套用預設（漫畫書為 RTL）。

使用者觀察得到的漫畫書行為與輸出完全不變；這張票沒有新功能。

見 spec「判斷 `--direction` 是否被使用」。

**Blocked by:** None (can start immediately)

**Status:** ready-for-agent

- [ ] CLI 不給 `--direction` 時，建書流程收到「未指定」，漫畫書套用 RTL
- [ ] 漫畫書不帶 `--direction` 時輸出仍是 RTL（新增一條測試明確鎖住這點）
- [ ] `--direction ltr` 與 `--direction rtl` 的行為不變
- [ ] 直接呼叫建書函式、不指定方向時，漫畫書仍是 RTL
- [ ] `--help` 仍顯示漫畫書的預設方向是 rtl
- [ ] 既有測試全部通過，EPUBCheck 情境沒有錯誤
