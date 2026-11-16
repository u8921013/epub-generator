"""命令列介面：解析參數、呼叫 build_epub、把結果或錯誤轉成訊息與結束代碼。"""

import argparse
import sys
from importlib.metadata import PackageNotFoundError, version

from . import BuildOptions, EpubgenError, build_epub
from .metadata import is_valid_language
from .epub import DIRECTIONS


def _version() -> str:
    try:
        return version("epubgen")
    except PackageNotFoundError:
        return "unknown"


def _language(value: str) -> str:
    if not is_valid_language(value):
        raise argparse.ArgumentTypeError(f"不合法的語言代碼：{value!r}（例如 ja、zh-TW）")
    return value


def _quality(value: str) -> int:
    try:
        number = int(value)
    except ValueError:
        number = 0
    if not 1 <= number <= 100:
        raise argparse.ArgumentTypeError(f"品質要是 1 到 100 的整數，收到 {value!r}")
    return number


def _max_size(value: str) -> int:
    try:
        number = int(value)
    except ValueError:
        number = 0
    if number < 1:
        raise argparse.ArgumentTypeError(f"尺寸上限要是正整數（像素），收到 {value!r}")
    return number


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="epubgen",
        description="把圖片資料夾轉成 fixed layout 的漫畫 EPUB。",
        epilog=(
            "Kobo 說明：輸出的檔案以同時給 Apple Books 與 Kobo 使用為目標。把檔案側載到 Kobo "
            "eInk 時，Kobo 官方規格說固定版面的書要用 .fxl.kepub.epub 副檔名才會以 Kobo "
            "自己的引擎顯示（代價是停用書籤與筆記）；維持 .epub 是否也能以固定版面開啟，"
            "官方沒有說明。若顯示不正常，可以先把檔名改成 .fxl.kepub.epub 再試。"
        ),
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
    parser.add_argument(
        "--title", metavar="TITLE",
        help="書名（預設：輸入資料夾名稱）；預設輸出檔名也跟著書名",
    )
    parser.add_argument("--author", metavar="NAME", help="作者（預設：不寫入）")
    parser.add_argument(
        "--language", metavar="CODE", type=_language, default="zh-TW",
        help="語言代碼，例如 ja、en、zh-TW（預設：zh-TW）",
    )
    parser.add_argument(
        "--cover", metavar="IMAGE",
        help="指定封面圖片，可以在輸入資料夾內或外；相對路徑從目前目錄算起（預設：第一頁）",
    )
    parser.add_argument(
        "--keep-webp", action="store_true",
        help="保留 WebP 原檔（預設：把 WebP 轉成高品質 JPEG，因為不是所有閱讀器都能顯示 WebP）",
    )
    parser.add_argument(
        "--quality", metavar="1-100", type=_quality,
        help=("重新壓縮的 JPEG 品質（預設：不重新壓縮，圖片原樣打包）。JPEG 與 WebP 重新壓縮；"
              "PNG 會轉成 JPEG；GIF 不受影響。壓縮後反而變大的 JPEG 會維持原檔"),
    )
    parser.add_argument(
        "--max-size", metavar="PIXELS", type=_max_size,
        help=("圖片長邊的像素上限（預設：不縮放）。超過的圖片等比例縮小，不會放大。"
              "縮小後 JPEG 維持 JPEG、PNG 維持 PNG（無損）、GIF 與預設的 WebP 轉成 JPEG"),
    )
    parser.add_argument("--version", action="version", version=f"epubgen {_version()}")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        result = build_epub(args.input, BuildOptions(
            output=args.output, force=args.force, skip_broken=args.skip_broken,
            direction=args.direction, spread=args.spread, title=args.title,
            author=args.author, language=args.language, cover=args.cover,
            keep_webp=args.keep_webp, quality=args.quality, max_size=args.max_size,
        ))
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
