"""Đọc/ghi file JSON dùng chung — khóa theo đường dẫn, thử lại khi Windows giữ file."""

from __future__ import annotations

import json
import os
import threading
import time
from typing import Any

_path_locks: dict[str, threading.Lock] = {}
_path_locks_guard = threading.Lock()


def _lock_for(path: str) -> threading.Lock:
    key = os.path.normcase(os.path.abspath(str(path)))
    with _path_locks_guard:
        if key not in _path_locks:
            _path_locks[key] = threading.Lock()
        return _path_locks[key]


def read_json(path, default: Any) -> Any:
    p = str(path)
    lock = _lock_for(p)
    with lock:
        try:
            if not os.path.exists(p):
                return default
            with open(p, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return default


def _atomic_replace(src: str, dst: str) -> None:
    """os.replace có thể WinError 32 khi IDE/antivirus đang mở file đích."""
    last_err: BaseException | None = None
    for attempt in range(12):
        try:
            os.replace(src, dst)
            return
        except (PermissionError, OSError) as exc:
            last_err = exc
            winerr = getattr(exc, "winerror", None)
            if winerr not in (5, 32) and not isinstance(exc, PermissionError):
                raise
            if attempt < 11:
                time.sleep(min(0.4, 0.02 * (2**attempt)))
    if last_err is not None:
        try:
            with open(src, encoding="utf-8") as f:
                text = f.read()
            with open(dst, "w", encoding="utf-8", newline="\n") as f:
                f.write(text)
            try:
                os.remove(src)
            except OSError:
                pass
            return
        except Exception:
            pass
        raise last_err


def write_json(path, data: Any) -> None:
    p = str(path)
    tmp = p + ".tmp"
    lock = _lock_for(p)
    with lock:
        with open(tmp, "w", encoding="utf-8", newline="\n") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            f.flush()
            os.fsync(f.fileno())
        _atomic_replace(tmp, p)
