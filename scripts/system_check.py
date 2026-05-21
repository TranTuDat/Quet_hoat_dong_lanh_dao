"""Kiểm tra hệ thống — offline: python scripts/system_check.py | live: python scripts/system_check.py --live"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _run_offline() -> tuple[list[str], list[str]]:
    errors: list[str] = []
    ok: list[str] = []

    from src.paths import migrate_legacy_files

    migrate_legacy_files()

    from src.monitor import load_config, resolve_ai_scan_options
    from src.web import app

    cfg = load_config()
    opts = resolve_ai_scan_options(cfg)
    ok.append(f"config: mode={opts['mode']}, targets={len(cfg.get('targets') or [])}")

    rules = {r.rule for r in app.url_map.iter_rules()}
    need = [
        "/",
        "/api/targets",
        "/api/settings",
        "/api/monitor/status",
        "/monitor/run",
        "/api/data/stats",
        "/api/data/clear",
        "/notifications",
    ]
    missing = [p for p in need if p not in rules]
    if missing:
        errors.append(f"Thiếu route: {missing}")
    else:
        ok.append(f"routes: {len(rules)} endpoints")

    c = app.test_client()
    for path, name in [
        ("/api/monitor/status", "status"),
        ("/api/settings", "settings"),
        ("/api/targets", "targets"),
        ("/api/data/stats?time_range=24h", "data/stats"),
        ("/notifications", "notifications"),
    ]:
        r = c.get(path)
        if r.status_code != 200:
            errors.append(f"GET {path} -> {r.status_code}")
        else:
            ok.append(f"GET {name} 200")

    j = c.get("/api/settings").get_json()
    if not j.get("success") or "ai_scan_mode" not in (j.get("settings") or {}):
        errors.append("settings thiếu ai_scan_mode")
    elif not j.get("settings", {}).get("ai_scan_profiles"):
        errors.append("settings thiếu ai_scan_profiles")

    r = c.post(
        "/monitor/run",
        json={"scan_hours": 24},
        content_type="application/json",
    )
    j = r.get_json()
    if r.status_code != 200 or not j.get("started"):
        errors.append(f"POST /monitor/run -> {r.status_code} {j}")
    else:
        ok.append("POST monitor/run started (async)")

    from src.telegram_notify import notify_key

    k = notify_key(
        {"target_name": "T", "url": "http://g", "resolved_url": "http://b.com/x"}
    )
    if k != "T|http://b.com/x":
        errors.append(f"notify_key sai: {k}")

    for rel in (
        "data/notifications.json",
        "data/history.json",
        "config/config.json",
    ):
        if not (ROOT / rel).is_file():
            errors.append(f"Thiếu file: {rel}")

    from src.data_store import get_data_stats

    get_data_stats(time_range="24h")
    ok.append("data_store OK")
    return errors, ok


def _fetch(base: str, path: str) -> tuple[int | None, object]:
    try:
        r = urllib.request.urlopen(base + path, timeout=12)
        body = r.read().decode("utf-8", "replace")
        if body.strip().startswith("{"):
            return r.status, json.loads(body)
        return r.status, body
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")[:300]
    except Exception as e:
        return None, str(e)


def _run_live(base: str = "http://127.0.0.1:8000") -> tuple[list[str], list[str]]:
    errors: list[str] = []
    ok: list[str] = []
    warnings: list[str] = []

    for path in [
        "/api/targets",
        "/api/settings",
        "/api/monitor/status",
        "/api/targets/summary?hours=24",
        "/notifications",
    ]:
        code, data = _fetch(base, path)
        if code == 200:
            ok.append(f"GET {path} 200")
        else:
            errors.append(f"GET {path} HTTP {code}: {data}")
        if path == "/api/monitor/status" and isinstance(data, dict):
            st = data.get("status") or {}
            if st.get("enabled") and st.get("thread_alive") is False:
                errors.append("Auto-scanner thread is dead")
            if st.get("last_scan_ok") is False and st.get("last_error"):
                warnings.append(f"Last scan error: {st.get('last_error')}")

    code, html = _fetch(base, "/")
    if code == 200:
        ok.append("GET / 200")
    else:
        errors.append("Dashboard not responding")

    for path in ("/static/js/dashboard.js", "/static/js/theme.js"):
        code, _ = _fetch(base, path)
        if code == 200:
            ok.append(f"GET {path} 200")
        else:
            errors.append(f"Missing static: {path}")

    for w in warnings:
        ok.append(f"WARN: {w}")
    return errors, ok


def main() -> int:
    parser = argparse.ArgumentParser(description="Kiểm tra hệ thống giám sát")
    parser.add_argument(
        "--live",
        action="store_true",
        help="Gọi API server đang chạy (mặc định: kiểm tra offline qua test_client)",
    )
    parser.add_argument("--base", default="http://127.0.0.1:8000", help="URL khi --live")
    args = parser.parse_args()

    try:
        if args.live:
            print(f"=== LIVE ({args.base}) ===\n")
            errors, ok = _run_live(args.base.rstrip("/"))
        else:
            print("=== OFFLINE ===\n")
            errors, ok = _run_offline()
    except Exception as exc:
        print(f"  [LOI] {exc}")
        return 1

    for line in ok:
        print(f"  [OK] {line}")
    if errors:
        print()
        for line in errors:
            print(f"  [LOI] {line}")
        print(f"\nTong: {len(ok)} OK, {len(errors)} LOI")
        return 1
    print(f"\nTat ca {len(ok)} muc deu OK.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
