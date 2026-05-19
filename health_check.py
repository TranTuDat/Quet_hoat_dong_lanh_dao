"""Kiểm tra nhanh hệ thống — chạy: python health_check.py"""
from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request

if sys.platform == "win32":
    for _stream in (sys.stdout, sys.stderr):
        try:
            _stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

BASE = "http://127.0.0.1:8000"


def fetch(path: str) -> tuple[int | None, object]:
    try:
        r = urllib.request.urlopen(BASE + path, timeout=12)
        body = r.read().decode("utf-8", "replace")
        if body.strip().startswith("{"):
            return r.status, json.loads(body)
        return r.status, body
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")[:300]
    except Exception as e:
        return None, str(e)


def main() -> int:
    errors: list[str] = []
    warnings: list[str] = []

    print("=== API ===")
    for path in [
        "/config",
        "/api/settings",
        "/api/monitor/status",
        "/api/targets/summary?hours=24",
        "/notifications",
    ]:
        code, data = fetch(path)
        ok = code == 200
        print(f"  {path}: {'OK' if ok else 'FAIL'} ({code})")
        if not ok:
            errors.append(f"{path} HTTP {code}: {data}")
            continue
        if path == "/api/monitor/status" and isinstance(data, dict):
            st = data.get("status") or {}
            print(f"    auto_scan={st.get('enabled')} thread_alive={st.get('thread_alive')}")
            print(f"    last_scan_ok={st.get('last_scan_ok')} is_scanning={st.get('is_scanning')}")
            if st.get("last_error"):
                print(f"    last_error={st.get('last_error')}")
            if st.get("enabled") and st.get("thread_alive") is False:
                errors.append("Auto-scanner thread is dead")
            if st.get("last_scan_ok") is False and st.get("last_error"):
                warnings.append(f"Last scan error: {st.get('last_error')}")

    code, html = fetch("/")
    print(f"  /: {'OK' if code == 200 else 'FAIL'} ({code})")
    if code != 200:
        errors.append("Dashboard không phản hồi")
    elif isinstance(html, str):
        for needle in ("theme.js", "data-theme-toggle", "Quét tất cả"):
            if needle not in html:
                warnings.append(f"Dashboard thiếu: {needle}")

    print("\n=== Static ===")
    for path in (
        "/static/js/dashboard.js",
        "/static/js/theme.js",
        "/static/css/isr-theme.css",
    ):
        code, _ = fetch(path)
        print(f"  {path}: {'OK' if code == 200 else 'FAIL'} ({code})")
        if code != 200:
            errors.append(f"Thiếu file static: {path}")

    print("\n=== Kết luận ===")
    if errors:
        print("LỖI:")
        for e in errors:
            print("  -", e)
    if warnings:
        print("CẢNH BÁO:")
        for w in warnings:
            print("  -", w)
    if not errors and not warnings:
        print("Hệ thống ổn — không phát hiện lỗi.")
    elif not errors:
        print("Không có lỗi nghiêm trọng.")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
