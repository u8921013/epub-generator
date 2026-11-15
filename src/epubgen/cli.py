"""命令列介面：解析參數、呼叫 build_epub、把結果或錯誤轉成訊息與結束代碼。"""

import argparse
import sys
from importlib.metadata import PackageNotFoundError, version

from . import EpubgenError, build_epub
from .epub import DIRECTIONS


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
    parser.add_argument(
        "--direction", choices=DIRECTIONS, default="rtl",
        help="翻頁方向：rtl 從右到左、ltr 從左到右（預設：rtl）",
    )
    parser.add_argument(
        "--spread", action="store_true",
        help="啟用雙頁模式：封面單獨一頁，其後兩兩並排（預設：每頁單獨顯示）",
    )
    parser.add_argument(
        "-o", "--output", metavar="PATH",
        help="輸出檔路徑（預設：輸入資料夾旁邊的 <資料夾名稱>.epub）",
    )
    parser.add_argument(
        "--force", action="store_true",
        help="輸出檔已存在時覆蓋它（預設：拒絕覆蓋）",
    )
    parser.add_argument(
        "--skip-broken", action="store_true",
        help="跳過無法讀取的圖片並在結束時列出（預設：遇到損毀圖片就報錯）",
    )
    parser.add_argument("--version", action="version", version=f"epubgen {_version()}")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        result = build_epub(args.input, output=args.output, force=args.force,
                            skip_broken=args.skip_broken, direction=args.direction,
                            spread=args.spread)
    except EpubgenError as exc:
        print(f"epubgen: 錯誤：{exc}", file=sys.stderr)
        return 1
    if result.skipped:
        print(f"epubgen: 已跳過 {len(result.skipped)} 張無法讀取的圖片：", file=sys.stderr)
        for name in result.skipped:
            print(f"  - {name}", file=sys.stderr)
    print(f"已輸出：{result.output}（共 {result.page_count} 頁）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
