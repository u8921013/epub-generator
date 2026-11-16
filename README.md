# epubgen

把圖片資料夾轉成 EPUB 3 fixed layout（預先分頁）的漫畫電子書，給 Apple Books 與 Kobo 閱讀。需求與設計見 [.scratch/epubgen/spec.md](.scratch/epubgen/spec.md)。

## 安裝

```bash
pipx install .
```

## 使用

```bash
epubgen ./my-comic
```

輸出 `my-comic.epub`，放在輸入資料夾旁邊。所有參數與預設值見 `epubgen --help`，完整教學見 [docs/tutorial.md](docs/tutorial.md)。

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
