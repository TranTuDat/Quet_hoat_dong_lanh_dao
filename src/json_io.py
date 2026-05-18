"""Đọc/ghi file JSON dùng chung."""

from __future__ import annotations

import json
import os
from typing import Any


def read_json(path, default: Any) -> Any:
    p = str(path)
    try:
        if not os.path.exists(p):
            return default
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def write_json(path, data: Any) -> None:
    p = str(path)
    tmp = p + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp, p)
