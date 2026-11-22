# 07: 書內連結與錨點

**What to build:** 作者在 md 之間寫的連結在書裡也能點：

- `[見第二章](02.md)` 跳到該章開頭；`[](02.md#某標題)` 跳到該章的那個標題；同檔內的 `[](#某標題)` 在章內跳轉。相對路徑以 md 檔所在資料夾為基準，跨部（不同子資料夾）的連結也要正確。
- 標題的錨點名稱與 GitHub 預覽產生的一致：小寫、去標點、空白換成 `-`、保留中文；同一章內重複的名稱依序加 `-1`、`-2`。
- 連到不存在的檔案或錨點、或連到非 Markdown 的本地檔案時，輸出連結文字（不是連結）並產生警告。
- 有 scheme 的外部連結（`https://` 等）原樣保留。

**實作前要先查證** GitHub 標題錨點的確切規則（哪些標點被移除、全形標點與 emoji 的處理），對照 GitHub 的實際行為或其公開實作，把查證結果與出處記在這張票的 Comments，不能憑印象寫。

跨章錨點的驗證需要先知道所有章的錨點，組裝流程要先取得每章的錨點再完成連結解析。

涵蓋 spec 的 user story 31–36。

**Blocked by:** 04（部與兩層目錄）、05（警告機制）

**Status:** resolved

- [x] 查證結果與出處記錄在本票 Comments
- [x] 連到其他 md 檔的連結指向該章 XHTML
- [x] 連到其他 md 的錨點指向該章 XHTML 中對應的標題 id
- [x] 同章內 `#錨點` 連結可跳轉
- [x] 跨部（`../第一部/01.md`）的連結正確
- [x] 錨點名稱：英文、中文、標點、重複標題的情境都有第二接縫測試
- [x] 失效的檔案、失效的錨點、指向非 Markdown 檔的連結都變成純文字並產生警告
- [x] 外部連結原樣保留
- [x] EPUB 解析輔助工具能讀出某個書內連結的目標
- [x] EPUBCheck 情境表的「有部有章」情境加入書內連結，沒有錯誤

## Comments

### 標題錨點規則的查證（2026-11-22）

出處：

- GitHub 自家的舊實作 html-pipeline 的 `TableOfContentsFilter`（https://raw.githubusercontent.com/gjtorikian/html-pipeline/v2.14.3/lib/html/pipeline/toc_filter.rb）：
  - 先 `ascii_downcase`，再用 `/[^\p{Word}\- ]/u` 移除字元，然後把空白換成 `-`。
  - 重複的名稱依各自的計數加 `-1`、`-2`。
- github-slugger（https://github.com/Flet/github-slugger）。README 說它的目標是盡量模仿 GitHub 產生標題錨點的方式，GitHub 與 VS Code 預覽的連結通常也以它為準：
  - `index.js`：`toLowerCase()` → 移除 regex 比對到的字元 → 空白換成 `-`。重複時以 occurrences 計數加 `-1`、`-2`，並避開已用過的名稱（`foo`、`foo`、`foo-1`、`foo` → `foo`、`foo-1`、`foo-1-1`、`foo-2`）。
  - `script/generate-regex.js`：移除 Unicode 類別 Other_Number、各類標點（Ps、Pe、Pi、Pf、Po）、Dash_Punctuation（`-` 除外）、Symbol、Control、Private_Use、Format、Unassigned、Separator（空白除外）。但 Alphabetic 字元一律保留。
  - 因此保留：字母、組合記號、十進位數字、`_`（Pc）、`-`、空白。
  - README 範例：`Привет non-latin 你好` 轉成 `привет-non-latin-你好`；`😄 emoji` 轉成 `-emoji`。

採用 github-slugger 的規則：

- 全形標點（，！「」）與 emoji 都會被移除，中文、日文保留。
- 轉小寫用 Python `str.lower()`，跟 JavaScript `toLowerCase()` 一樣是完整的 Unicode 轉換。html-pipeline 只轉 ASCII 字母，兩者只在大寫的非拉丁字母上有差別。
- 標題的文字取 HTML 裡看得到的文字：一般文字、行內程式碼、連結文字。圖片的替代文字不算。

已知與 github-slugger 不同的地方：

- 「是否為字母」用 Python `str.isalpha()` 判斷，不是 Unicode 的 Alphabetic 屬性。差別只在少數屬於符號類、但 Unicode 仍算字母的字元，例如 Ⓐ、🄰：github-slugger 保留，這裡移除。
- 標題經過處理後一個字都不剩時（例如 `## 😀`），不給 id。github-slugger 會給空字串，第二個同名的給 `-1`。

### 連結

- 解析分兩階段：
  - 第一次轉譯不解析連結，只取得每章是否為空與它的錨點。
  - 第二次轉譯時，每章拿到自己的解析器。相對路徑以該 md 所在的資料夾為基準。
- 判斷順序：
  - 有 scheme 的連結（`https:`、`mailto:` 等）原樣保留，不交給解析器。
  - `//host`、`www.x.com` 這類沒有 scheme 的寫法當作本地路徑處理，所以會失效並產生警告。
  - 連到資料夾、帶 query、非 Markdown 檔、空章、不存在的檔案或錨點，一律變成純文字並警告。警告統一寫「失效的連結已改成純文字：目標（第 N 行）」。
- 錨點比對先找完全相同的。找不到時，跟 GitHub 一樣改用小寫再找一次，例如 `#Intro` 可以找到 `intro`。
- 中文錨點直接寫進 href，不做百分比編碼；EPUBCheck 沒有錯誤。
- 審查記下但未處理：
  - 章的編號在建書與寫出 EPUB 兩處各算一次，目前由連結測試確保一致。
  - 每章會解析兩次，234 章的小說仍在 0.5 秒內完成。
  - 指向同一個檔案的符號連結會被視為同一章。
