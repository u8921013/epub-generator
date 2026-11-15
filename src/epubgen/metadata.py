"""書籍資訊的驗證與輸出檔名的處理。"""

import re

# 簡化的 BCP 47：主語言 2–3 個字母，後面接任意個 2–8 字元的子標籤，例如 ja、zh-TW、zh-Hant-TW。
_LANGUAGE = re.compile(r"^[A-Za-z]{2,3}(-[A-Za-z0-9]{2,8})*$")
_ILLEGAL_IN_FILE_NAME = re.compile(r'[/\\:*?"<>|\x00-\x1f]')
_MAX_FILE_NAME_LENGTH = 200


def is_valid_language(code: str) -> bool:
    return bool(_LANGUAGE.match(code))


def safe_file_name(title: str) -> str:
    """把書名轉成可以當檔名的字串：替換不允許的字元，書名本身不受影響。"""
    name = _ILLEGAL_IN_FILE_NAME.sub("_", title).strip().strip(".").strip()
    return name[:_MAX_FILE_NAME_LENGTH] or "book"
