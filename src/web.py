from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Dict
from urllib.parse import quote

from flask import Flask, Response, jsonify, render_template, request

from src import monitor
from src.auto_scanner import get_auto_scanner
from src.json_io import read_json, write_json
from src.telegram_notify import send_test_message
from src.paths import (
    CHINH_THONG_PATH,
    CONFIG_PATH,
    STATIC_DIR,
    TEMPLATES_DIR,
    migrate_legacy_files,
    path_str,
)

migrate_legacy_files()

_AUTO_SCANNER = get_auto_scanner()

app = Flask(
    __name__,
    template_folder=path_str(TEMPLATES_DIR),
    static_folder=path_str(STATIC_DIR),
)


def _ensure_gn(cfg: Dict[str, Any]) -> Dict[str, Any]:
    gn = cfg.get("google_news")
    if not isinstance(gn, dict):
        gn = {}
        cfg["google_news"] = gn
    return gn


def _ensure_telegram(cfg: Dict[str, Any]) -> Dict[str, Any]:
    tg = cfg.get("telegram")
    if not isinstance(tg, dict):
        tg = {}
        cfg["telegram"] = tg
    return tg


def _telegram_settings_payload(tg: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "enabled": _as_bool(tg.get("enabled"), False),
        "bot_token": str(tg.get("bot_token") or ""),
        "chat_id": str(tg.get("chat_id") or ""),
        "notify_role_change_only": _as_bool(tg.get("notify_role_change_only"), False),
    }


def _as_bool(val: Any, default: bool = False) -> bool:
    if isinstance(val, bool):
        return val
    if val is None:
        return default
    return str(val).strip().lower() not in ("0", "false", "no", "off", "")


@app.get("/")
def index():
    return render_template("dashboard.html")


@app.get("/target")
def target_detail_page():
    return render_template("target_detail.html")


@app.get("/config")
def get_config():
    cfg = read_json(CONFIG_PATH, default={})
    if not isinstance(cfg, dict):
        cfg = {}
    cfg.setdefault("targets", [])
    return jsonify({"success": True, "config": cfg})


def _save_target_in_config(
    cfg: Dict[str, Any],
    *,
    original_name: str = "",
    name: str = "",
    position: str = "",
) -> tuple[Dict[str, Any], str | None]:
    """Cập nhật hoặc thêm đối tượng trong config. Trả về (cfg, lỗi)."""
    targets = cfg.get("targets", [])
    if not isinstance(targets, list):
        targets = []

    old = str(original_name or "").strip()
    new = str(name or "").strip()
    pos = str(position or "").strip()

    if old:
        idx = None
        for i, t in enumerate(targets):
            if isinstance(t, dict) and str(t.get("name", "")).strip() == old:
                idx = i
                break
        if idx is None:
            return cfg, f"Không tìm thấy đối tượng: {old}"
        if new != old:
            for t in targets:
                if isinstance(t, dict) and str(t.get("name", "")).strip() == new:
                    return cfg, f"Đã tồn tại đối tượng: {new}"
        old_pos = ""
        if isinstance(targets[idx], dict):
            old_pos = str(targets[idx].get("position", "")).strip()
        targets[idx] = {"name": new, "position": pos}
        cfg["targets"] = targets
        if new != old or pos != old_pos:
            monitor.update_target_identity(old, new, pos)
        return cfg, None

    for t in targets:
        if isinstance(t, dict) and str(t.get("name", "")).strip() == new:
            t["position"] = pos
            cfg["targets"] = targets
            return cfg, None

    targets.append({"name": new, "position": pos})
    cfg["targets"] = targets
    return cfg, None


@app.post("/config/targets/add")
def add_target():
    data = request.get_json(force=True) or {}
    original_name = str(data.get("original_name", "")).strip()
    name = str(data.get("name", "")).strip()
    position = str(data.get("position", "")).strip()
    if not name:
        return jsonify({"success": False, "error": "Thiếu tên đối tượng"}), 400

    cfg = read_json(CONFIG_PATH, default={})
    if not isinstance(cfg, dict):
        cfg = {}
    cfg, err = _save_target_in_config(
        cfg, original_name=original_name, name=name, position=position
    )
    if err:
        return jsonify({"success": False, "error": err}), 404 if original_name else 400

    write_json(CONFIG_PATH, cfg)
    return jsonify({"success": True, "config": cfg, "message": "Đã lưu"})


@app.post("/config/targets/update")
def update_target():
    """Giữ tương thích — chuyển sang logic lưu chung."""
    data = request.get_json(force=True) or {}
    original = str(data.get("name", "")).strip()
    name = str(data.get("new_name", "") or original).strip()
    position = str(data.get("position", "")).strip()
    if not original:
        return jsonify({"success": False, "error": "Thiếu tên đối tượng gốc"}), 400
    if not name:
        return jsonify({"success": False, "error": "Thiếu tên mới"}), 400

    cfg = read_json(CONFIG_PATH, default={})
    if not isinstance(cfg, dict):
        cfg = {}
    cfg, err = _save_target_in_config(
        cfg, original_name=original, name=name, position=position
    )
    if err:
        return jsonify({"success": False, "error": err}), 404
    write_json(CONFIG_PATH, cfg)
    return jsonify({"success": True, "config": cfg, "message": "Đã lưu"})


@app.post("/config/targets/delete")
def delete_target():
    data = request.get_json(force=True) or {}
    name = str(data.get("name", "")).strip()
    if not name:
        return jsonify({"success": False, "error": "Thiếu name"}), 400

    cfg = read_json(CONFIG_PATH, default={})
    if not isinstance(cfg, dict):
        cfg = {}
    targets = cfg.get("targets", [])
    if not isinstance(targets, list):
        targets = []
    cfg["targets"] = [
        t for t in targets if not (isinstance(t, dict) and str(t.get("name", "")).strip() == name)
    ]
    write_json(CONFIG_PATH, cfg)
    return jsonify({"success": True, "config": cfg})


@app.get("/notifications")
def get_notifications():
    notifs = monitor.load_notifications()
    return jsonify({"success": True, "notifications": notifs})


@app.get("/api/targets/summary")
def api_targets_summary():
    raw_h = request.args.get("hours", default="24", type=str) or "24"
    try:
        hours = float(str(raw_h).replace(",", "."))
    except Exception:
        hours = 24.0

    cfg = read_json(CONFIG_PATH, default={})
    gn = cfg.get("google_news") if isinstance(cfg.get("google_news"), dict) else {}
    notifs = monitor.load_notifications()
    names = [
        str(t.get("name", "")).strip()
        for t in (cfg.get("targets") or [])
        if isinstance(t, dict) and str(t.get("name", "")).strip()
    ]
    items = monitor.summarize_targets_in_window(notifs, names, hours, gn=gn)
    return jsonify({
        "success": True,
        "hours": hours,
        "hours_requested": hours,
        "summaries": items,
    })


@app.get("/api/target/detail")
def api_target_detail():
    name = str(request.args.get("name", "") or "").strip()
    if not name:
        return jsonify({"success": False, "error": "Thiếu tham số name"}), 400

    raw_h = request.args.get("hours", default="24", type=str) or "24"
    try:
        hours = float(str(raw_h).replace(",", "."))
    except Exception:
        hours = 24.0

    cfg = read_json(CONFIG_PATH, default={})
    gn = cfg.get("google_news") if isinstance(cfg.get("google_news"), dict) else {}
    notifs = monitor.load_notifications()
    detail = monitor.collect_target_detail(notifs, name, hours, gn=gn)
    return jsonify({"success": True, **detail})


@app.get("/api/target/export.json")
def api_target_export_json():
    name = str(request.args.get("name", "") or "").strip()
    if not name:
        return jsonify({"success": False, "error": "Thiếu name"}), 400

    raw_h = request.args.get("hours", default="24", type=str) or "24"
    try:
        hours = float(str(raw_h).replace(",", "."))
    except Exception:
        hours = 24.0

    cfg = read_json(CONFIG_PATH, default={})
    gn = cfg.get("google_news") if isinstance(cfg.get("google_news"), dict) else {}
    notifs = monitor.load_notifications()
    detail = monitor.collect_target_detail(notifs, name, hours, gn=gn)
    payload = {
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "target_name": name,
        "hours": hours,
        **detail,
    }
    body = json.dumps(payload, ensure_ascii=False, indent=2)
    fname = f"target_{quote(name)}_{int(hours)}h.json"
    return Response(
        body,
        mimetype="application/json; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{fname}"'},
    )


@app.get("/api/settings")
def api_get_settings():
    cfg = read_json(CONFIG_PATH, default={})
    if not isinstance(cfg, dict):
        cfg = {}
    gn = _ensure_gn(cfg)
    tg = _ensure_telegram(cfg)
    press = read_json(CHINH_THONG_PATH, default=[])
    if not isinstance(press, list):
        press = []
    return jsonify(
        {
            "success": True,
            "settings": {
                "filter_chinh_thong_only": monitor.is_chinh_thong_filter_enabled(cfg),
                "merge_duplicate_articles": _as_bool(gn.get("merge_duplicate_articles"), False),
                "use_event_intelligence": _as_bool(gn.get("use_event_intelligence"), False),
                "max_results_per_target": int(gn.get("max_results_per_target") or 15),
                "use_rss_feeds": _as_bool(gn.get("use_rss_feeds"), True),
                "auto_scan_enabled": _as_bool(cfg.get("auto_scan_enabled"), True),
                "scan_interval_minutes": max(
                    5, min(1440, int(cfg.get("scan_interval_minutes") or 60))
                ),
                "ui_refresh_seconds": max(
                    10, min(120, int(cfg.get("ui_refresh_seconds") or 30))
                ),
                **_telegram_settings_payload(tg),
            },
            "press_sources": [p for p in press if isinstance(p, dict)],
        }
    )


@app.post("/api/settings")
def api_save_settings():
    data = request.get_json(force=True) or {}
    cfg = read_json(CONFIG_PATH, default={})
    if not isinstance(cfg, dict):
        cfg = {}
    gn = _ensure_gn(cfg)
    tg = _ensure_telegram(cfg)

    if "filter_chinh_thong_only" in data:
        gn["filter_chinh_thong_only"] = _as_bool(data.get("filter_chinh_thong_only"), True)
    if "merge_duplicate_articles" in data:
        gn["merge_duplicate_articles"] = _as_bool(data.get("merge_duplicate_articles"), False)
    if "use_event_intelligence" in data:
        gn["use_event_intelligence"] = _as_bool(data.get("use_event_intelligence"), False)
    if "max_results_per_target" in data:
        try:
            n = int(data.get("max_results_per_target"))
            gn["max_results_per_target"] = max(1, min(50, n))
        except (TypeError, ValueError):
            pass
    if "use_rss_feeds" in data:
        gn["use_rss_feeds"] = _as_bool(data.get("use_rss_feeds"), True)
    if "auto_scan_enabled" in data:
        cfg["auto_scan_enabled"] = _as_bool(data.get("auto_scan_enabled"), True)
    if "scan_interval_minutes" in data:
        try:
            n = int(data.get("scan_interval_minutes"))
            cfg["scan_interval_minutes"] = max(5, min(1440, n))
        except (TypeError, ValueError):
            pass
    if "ui_refresh_seconds" in data:
        try:
            n = int(data.get("ui_refresh_seconds"))
            cfg["ui_refresh_seconds"] = max(10, min(120, n))
        except (TypeError, ValueError):
            pass

    if "enabled" in data:
        tg["enabled"] = _as_bool(data.get("enabled"), False)
    if "bot_token" in data:
        tg["bot_token"] = str(data.get("bot_token") or "").strip()
    if "chat_id" in data:
        tg["chat_id"] = str(data.get("chat_id") or "").strip()
    if "notify_role_change_only" in data:
        tg["notify_role_change_only"] = _as_bool(data.get("notify_role_change_only"), False)

    if "press_sources" in data:
        sources = data.get("press_sources")
        if isinstance(sources, list):
            from src.rss_fetch import guess_rss_url

            existing = read_json(CHINH_THONG_PATH, default=[])
            by_home: Dict[str, Dict[str, Any]] = {}
            if isinstance(existing, list):
                for row in existing:
                    if isinstance(row, dict):
                        home = str(row.get("homepage_url") or row.get("url") or "").strip()
                        if home:
                            by_home[home] = row

            cleaned = []
            for row in sources:
                if not isinstance(row, dict):
                    continue
                name = str(row.get("name", "")).strip()
                url = str(row.get("homepage_url") or row.get("url") or "").strip()
                if name and url:
                    item: Dict[str, str] = {"name": name, "homepage_url": url}
                    rss = str(row.get("rss_url") or row.get("feed_url") or "").strip()
                    if not rss.startswith("http"):
                        old = by_home.get(url) or {}
                        rss = str(old.get("rss_url") or "").strip()
                    if not rss.startswith("http"):
                        rss = guess_rss_url(url)
                    if rss.startswith("http"):
                        item["rss_url"] = rss
                    cleaned.append(item)
            write_json(CHINH_THONG_PATH, cleaned)

    write_json(CONFIG_PATH, cfg)
    _AUTO_SCANNER.wake_reconfig()
    return jsonify(
        {
            "success": True,
            "message": "Đã lưu cài đặt — chu kỳ quét sẽ áp dụng ngay",
            "config": cfg,
        }
    )


@app.post("/api/settings/telegram-test")
def api_telegram_test():
    data = request.get_json(force=True) or {}
    cfg = read_json(CONFIG_PATH, default={})
    if not isinstance(cfg, dict):
        cfg = {}
    tg = _ensure_telegram(cfg)
    if data.get("bot_token"):
        tg["bot_token"] = str(data.get("bot_token")).strip()
    if data.get("chat_id"):
        tg["chat_id"] = str(data.get("chat_id")).strip()
    out = send_test_message(cfg)
    if not out.get("ok"):
        return jsonify({"success": False, "error": out.get("error") or "Gửi thất bại"}), 400
    return jsonify({"success": True, "message": "Đã gửi tin nhắn thử"})


@app.get("/api/monitor/status")
def api_monitor_status():
    st = _AUTO_SCANNER.get_status()
    return jsonify({"success": True, "status": st})


@app.post("/monitor/run")
def monitor_run():
    try:
        body = request.get_json(silent=True) or {}
        hours = None
        if body.get("scan_hours") is not None:
            try:
                hours = float(body.get("scan_hours"))
            except (TypeError, ValueError):
                hours = None
        out = _AUTO_SCANNER.run_scan(scan_hours=hours, source="manual")
        return jsonify({"success": True, **out})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


def _start_background_scanner() -> None:
    _AUTO_SCANNER.start()


_start_background_scanner()
