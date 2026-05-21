"""Kiểm tra khi server đang chạy — tương đương: python scripts/system_check.py --live"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def main() -> int:
    script = ROOT / "scripts" / "system_check.py"
    return subprocess.call(
        [sys.executable, str(script), "--live"],
        cwd=str(ROOT),
    )


if __name__ == "__main__":
    raise SystemExit(main())
