"""找到並執行 EPUBCheck。找不到 Java 或 EPUBCheck 時，呼叫端用 skip 跳過，不算失敗。

尋找順序：
1. 環境變數 EPUBCHECK_JAR（指向 epubcheck.jar）
2. 專案內的 .tools/epubcheck-*/epubcheck.jar
3. PATH 上的 epubcheck 指令
"""

import os
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _java_works() -> bool:
    java = shutil.which("java")
    if not java:
        return False
    try:
        return subprocess.run([java, "-version"], capture_output=True, timeout=30).returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        return False


def find_command() -> list[str] | None:
    """回傳執行 EPUBCheck 的指令前綴，找不到時回傳 None。"""
    jar = os.environ.get("EPUBCHECK_JAR")
    candidates = [Path(jar)] if jar else sorted((ROOT / ".tools").glob("epubcheck-*/epubcheck.jar"))
    for candidate in candidates:
        if candidate.is_file() and _java_works():
            return [shutil.which("java"), "-jar", str(candidate)]
    on_path = shutil.which("epubcheck")
    if on_path and _java_works():
        return [on_path]
    return None


def run(command: list[str], epub: Path) -> tuple[bool, str]:
    """對 epub 執行 EPUBCheck，回傳 (沒有錯誤, 完整輸出)。

    EPUBCheck 只在有錯誤（含 fatal）時以非零代碼結束；警告不影響結果，但會留在輸出裡。
    """
    result = subprocess.run([*command, str(epub)], capture_output=True, text=True, timeout=300)
    return result.returncode == 0, result.stdout + result.stderr
