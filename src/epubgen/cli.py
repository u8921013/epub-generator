"""命令列介面：解析參數、呼叫 build_epub、把結果或錯誤轉成訊息與結束代碼。"""

import argparse
import sys
from importlib.metadata import PackageNotFoundError, version

from . import EpubgenError, build_epub


def _version() -> str:
    try:
        return version("epubgen")
    except PackageNotFoundError:
        return "unknown"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="epubgen",
        description="把圖片資料夾轉成 fixed layout 的漫畫 EPUB。",
    )
    parser.add_argument("input", help="放滿圖片的資料夾")
    parser.add_argument("--version", action="version", version=f"epubgen {_version()}")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        result = build_epub(args.input)
    except EpubgenError as exc:
        print(f"epubgen: 錯誤：{exc}", file=sys.stderr)
        return 1
    print(f"已輸出：{result.output}（共 {result.page_count} 頁）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
