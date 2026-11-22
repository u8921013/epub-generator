# epubgen

把資料夾轉成 EPUB 3 電子書，給 Apple Books 與 Kobo 閱讀：

- **漫畫書**：只有圖片的資料夾 → fixed layout（預先分頁）的漫畫。需求與設計見 [.scratch/epubgen/spec.md](.scratch/epubgen/spec.md)。
- **文字書**：含有 Markdown 檔（`.md`、`.markdown`）的資料夾 → 文字可隨字級重排的書，例如小說。需求與設計見 [.scratch/text-book/spec.md](.scratch/text-book/spec.md)。

書的種類由資料夾內容自動判斷，不需要額外參數。

## 安裝

```bash
pipx install .
```

## 使用

```bash
epubgen ./my-comic
```

輸出 `my-comic.epub`，放在輸入資料夾旁邊。所有參數與預設值見 `epubgen --help`，漫畫書的完整教學見 [docs/tutorial.md](docs/tutorial.md)。

## 文字書

```bash
epubgen ./my-novel --author 作者 --cover cover.jpg
```

資料夾裡有任何 Markdown 檔，就會產生文字書（根目錄的圖片只當插圖候選，不會變成漫畫頁）。

### 資料夾怎麼擺

```
my-novel/
├── 01-序章.md            ← 根目錄的 md：不屬於任何部的章
├── 第一部 出發/           ← 第一層子資料夾：一「部」，目錄第一層，名稱就是資料夾名稱
│   ├── 01-第一章.md
│   ├── 02-第二章.md
│   └── images/wide.jpg   ← 插圖；沒有 md 的資料夾不會出現在目錄
└── 第二部 歸來/
    └── 01-第三章.md
```

- **一個 md 檔是一章**，依檔名自然排序（`2.md` 在 `10.md` 前面）。
- **章名**取自檔案內第一個一級標題（`# 第8章 梁溪`），標題同時保留在內文；沒有一級標題時用檔名（保留數字前綴，例如 `01-序章`）。
- 目錄最多兩層：部 → 章。章內的小標題不列入目錄。
- 開頭的 YAML front matter 會被略過（但不會讀成書籍資訊）；空的章會被跳過並警告。

### Markdown 支援範圍

- CommonMark，加上表格與刪除線（`~~文字~~`）。程式碼區塊不做語法上色。
- **中文軟換行**：段落中間的單一換行，在兩個中文字之間會直接接起來，不會多一個空白；英文之間照常補空白。
- **書內連結**：`[第一章](第一部%20出發/01-第一章.md)`、`[表格](01-第一章.md#表格)`、`[本章最後](#本章最後)` 都會轉成書內跳轉。錨點規則和 GitHub 預覽相同（小寫、去標點、空白換成 `-`、保留中文、重複標題加 `-1`、`-2`），在 GitHub 或 VS Code 預覽能用的連結，轉成書後也能用。路徑含空白時可以寫成 `[文字](<第一部 出發/01-第一章.md>)`。連到不存在的檔案或標題時保留文字並警告。
- **插圖**：`![說明](images/a.png)` 引用的本地圖片會打包進書，顯示在原位置且不超出螢幕。支援 JPEG、PNG、GIF、WebP；`--quality`、`--max-size`、`--keep-webp` 的規則和漫畫書相同。找不到或損毀的插圖預設讓轉換失敗，加 `--skip-broken` 則改顯示替代文字並列出。網路圖片與 SVG 不打包，改顯示替代文字並警告。
- **原始 HTML** 會被轉成純文字顯示並警告，避免產生閱讀器打不開的書。

### 封面、書籍資訊與限制

- `--cover IMAGE` 指定封面：成為書櫃縮圖，並在書的最前面加一頁封面頁（不列入目錄）。沒有指定就沒有封面圖；資料夾裡的 `cover.jpg` 不會被自動採用。
- `--title`、`--author`、`--language` 和漫畫書相同，書名預設是資料夾名稱。
- `--direction` 與 `--spread` 只對漫畫書有效，用在文字書會報錯。文字書一律由左到右、橫排。
- 不嵌入字型、不支援自訂 CSS，由閱讀器使用自己的字型與排版設定。
- 轉換中遇到的警告會在結束時集中列出（含檔名與原因）；有警告但成功時結束代碼仍是 0。

## 開發與測試

```bash
python3 -m venv .venv
.venv/bin/pip install -e '.[test]'
.venv/bin/pytest
```

### EPUBCheck（選用）

`tests/test_epubcheck.py` 會對各情境產出的 EPUB 執行 [EPUBCheck](https://github.com/w3c/epubcheck)，要求沒有錯誤。需要 Java（11 以上）。找不到 Java 或 EPUBCheck 時整組測試自動跳過，不算失敗。

安裝方式：從 [EPUBCheck 的 GitHub release](https://github.com/w3c/epubcheck/releases) 下載 `epubcheck-<版本>.zip`，解壓到專案的 `.tools/` 資料夾（已被 `.gitignore` 排除），例如：

```bash
mkdir -p .tools && unzip epubcheck-5.4.0.zip -d .tools
```

測試依下列順序尋找 EPUBCheck：

1. 環境變數 `EPUBCHECK_JAR`，指向 `epubcheck.jar`
2. `.tools/epubcheck-*/epubcheck.jar`
3. `PATH` 上的 `epubcheck` 指令

執行並顯示跳過的原因：

```bash
.venv/bin/pytest tests/test_epubcheck.py -rs
```

要新增 EPUBCheck 情境，在 `tests/test_epubcheck.py` 的 `SCENARIOS` 加一列即可。

### 實機測試書

```bash
.venv/bin/python scripts/make_device_test_books.py
```

在 `device-test/books/` 產生一組給 Apple Books 與 Kobo 實機驗證用的書：A–I 是漫畫書的各種情境，`T-text-book` 是涵蓋部與章、表格、程式碼、插圖、書內連結與封面頁的文字書範本。各本要驗證的項目會在執行結束時列出。
