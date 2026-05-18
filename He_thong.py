"""Điểm chạy ứng dụng."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.web import app  # noqa: E402

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=False)
