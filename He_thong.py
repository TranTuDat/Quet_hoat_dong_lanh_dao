"""Điểm chạy ứng dụng."""

from __future__ import annotations

import os

# Log quét hiện ngay trên terminal (không bị buffer khi chạy nền lâu).
os.environ.setdefault("PYTHONUNBUFFERED", "1")

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _configure_console_utf8() -> None:
    """Windows mặc định cp1252 — in tiếng Việt trong thread quét nền dễ crash."""
    if sys.platform != "win32":
        return
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass


_configure_console_utf8()

try:
    sys.stdout.reconfigure(line_buffering=True)
except Exception:
    pass

from src.paths import migrate_legacy_files

migrate_legacy_files()

from src.web import app  # noqa: E402

if __name__ == "__main__":
    print("[SYS] Khởi động Flask — log quét in trực tiếp ra terminal này", flush=True)
    app.run(host="0.0.0.0", port=8000, debug=False)
