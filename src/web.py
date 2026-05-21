from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from typing import Any, Dict
from urllib.parse import quote

if sys.platform == "win32":
    for _stream in (sys.stdout, sys.stderr):
        try:
            _stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

import threading

from flask import Flask, Response, jsonify, render_template, request

from src import monitor
from src.auto_scanner import get_auto_scanner
from src.data_store import TIME_RANGE_OPTIONS, clear_data, get_data_stats
from src.common import as_bool
from src.json_io import read_json, write_json
from src.telegram_notify import send_test_message
from src.paths import (
    CHINH_THONG_PATH,
    CONFIG_PATH,
    STATIC_DIR,
    TEMPLATES_DIR,
    path_str,
)

_AUTO_SCANNER = get_auto_scanner()

app = Flask(
    __name__,
    template_folder=path_str(TEMPLATES_DIR),
    static_folder=path_str(STATIC_DIR),
)
app.config["TEMPLATES_AUTO_RELOAD"] = True


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
        "enabled": as_bool(tg.get("enabled"), False),
        "bot_token": str(tg.get("bot_token") or ""),
        "chat_id": str(tg.get("chat_id") or ""),
        "notify_role_change_only": as_bool(tg.get("notify_role_change_only"), False),
        "notify_on_empty": as_bool(tg.get("notify_on_empty"), False),
    }


def _targets_list(cfg: Dict[str, Any]) -> list:
    targets = cfg.get("targets", [])
    return targets if isinstance(targets, list) else []


def _sanitize_config(cfg: Dict[str, Any]) -> Dict[str, Any]:
    """Config công khai — không trả API key / token Telegram."""
    out = dict(cfg)
    if out.get("gemini_api_key"):
        out["gemini_api_key"] = "(đã cấu hình)"
    tg = out.get("telegram")
    if isinstance(tg, dict):
        tg = dict(tg)
        if tg.get("bot_token"):
            tg["bot_token"] = "(đã cấu hình)"
        out["telegram"] = tg
    gn = out.get("google_news")
    if isinstance(gn, dict):
        gn = dict(gn)
        gn.pop("merge_duplicate_articles", None)
        gn.pop("use_event_intelligence", None)
        out["google_news"] = gn
    return out


@app.get("/")
def index():
    return render_template("dashboard.html")


@app.get("/target")
def target_detail_page():
    return render_template("target_detail.html")


@app.get("/api/targets")
def api_get_targets():
    cfg = read_json(CONFIG_PATH, default={})
    if not isinstance(cfg, dict):
        cfg = {}
    return jsonify({"success": True, "targets": _targets_list(cfg)})


@app.get("/config")
def get_config():
    """Tương thích — không trả secret; ưu tiên GET /api/targets cho danh sách đối tượng."""
    cfg = read_json(CONFIG_PATH, default={})
    if not isinstance(cfg, dict):
        cfg = {}
    cfg.setdefault("targets", [])
    return jsonify({"success": True, "config": _sanitize_config(cfg)})


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


def _notifications_for_display() -> Dict[str, Any]:
    cfg = read_json(CONFIG_PATH, default={})
    notifs = monitor.load_notifications()
    return monitor.filter_notifications_for_display(notifs, cfg)


@app.get("/notifications")
def get_notifications():
    notifs = _notifications_for_display()
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
    notifs = monitor.filter_notifications_for_display(
        monitor.load_notifications(), cfg
    )
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
    notifs = monitor.filter_notifications_for_display(
        monitor.load_notifications(), cfg
    )
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
    notifs = monitor.filter_notifications_for_display(
        monitor.load_notifications(), cfg
    )
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
    gn = _ensure_gn(cfg)
    monitor.ensure_ai_scan_sync(gn, cfg)
    ai_opts = monitor.resolve_ai_scan_options(cfg)
    return jsonify(
        {
            "success": True,
            "settings": {
                "filter_chinh_thong_only": monitor.is_chinh_thong_filter_enabled(cfg),
                "use_ai": ai_opts["use_gemini"],
                "ai_verify_target": ai_opts["ai_verify_target"],
                "scan_role_change": ai_opts["scan_role_change"],
                "ai_scan_mode": ai_opts["mode"],
                "ai_scan_mode_label": ai_opts["label"],
                "ai_scan_mode_hint": ai_opts["hint"],
                "ai_scan_profiles": [
                    {"id": k, "label": v["label"], "hint": v["hint"]}
                    for k, v in monitor.AI_SCAN_PROFILES.items()
                    if k in monitor.AI_SCAN_UI_MODES
                ],
                "max_results_per_target": int(gn.get("max_results_per_target") or 15),
                "use_rss_feeds": as_bool(gn.get("use_rss_feeds"), True),
                "auto_scan_enabled": as_bool(cfg.get("auto_scan_enabled"), True),
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
        gn["filter_chinh_thong_only"] = as_bool(data.get("filter_chinh_thong_only"), True)
    ai_mode_saved = False
    ai_only_request = False
    if "ai_scan_mode" in data:
        mode = str(data.get("ai_scan_mode") or "activity").strip().lower()
        ai_only_request = set(data.keys()) <= {"ai_scan_mode"}
        if ai_only_request:
            ai_opts = monitor.set_and_persist_ai_scan_mode(mode)
            _AUTO_SCANNER.wake_reconfig(scan_soon=False)
            rescan = _AUTO_SCANNER.request_rescan_for_mode_change()
            return jsonify(
                {
                    "success": True,
                    "message": (
                        "Đã lưu — đang quét lại theo chế độ mới"
                        if rescan
                        else "Đã lưu — đang có lượt quét, hãy quét lại sau"
                    ),
                    "ai_scan_mode": ai_opts["mode"],
                    "ai_scan_mode_label": ai_opts["label"],
                    "rescan_started": rescan,
                }
            )
        monitor.apply_ai_scan_mode(gn, mode)
        ai_mode_saved = True
    else:
        legacy_touch = any(
            k in data
            for k in (
                "use_ai",
                "use_gemini_analysis",
                "ai_verify_target",
                "scan_role_change",
            )
        )
        if legacy_touch:
            if "use_ai" in data or "use_gemini_analysis" in data:
                use_g = as_bool(
                    data.get("use_gemini_analysis", data.get("use_ai")), True
                )
                gn["use_gemini_analysis"] = use_g
                gn["use_ai"] = use_g
            if "ai_verify_target" in data:
                gn["ai_verify_target"] = as_bool(data.get("ai_verify_target"), True)
            if "scan_role_change" in data:
                gn["scan_role_change"] = as_bool(data.get("scan_role_change"), True)
    if "ai_scan_mode" not in data:
        monitor.ensure_ai_scan_sync(gn, cfg)
    if "max_results_per_target" in data:
        try:
            n = int(data.get("max_results_per_target"))
            gn["max_results_per_target"] = max(1, min(50, n))
        except (TypeError, ValueError):
            pass
    if "use_rss_feeds" in data:
        gn["use_rss_feeds"] = as_bool(data.get("use_rss_feeds"), True)
    if "auto_scan_enabled" in data:
        cfg["auto_scan_enabled"] = as_bool(data.get("auto_scan_enabled"), True)
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
        tg["enabled"] = as_bool(data.get("enabled"), False)
    if "bot_token" in data:
        tg["bot_token"] = str(data.get("bot_token") or "").strip()
    if "chat_id" in data:
        tg["chat_id"] = str(data.get("chat_id") or "").strip()
    if "notify_role_change_only" in data:
        tg["notify_role_change_only"] = as_bool(data.get("notify_role_change_only"), False)
    if "notify_on_empty" in data:
        tg["notify_on_empty"] = as_bool(data.get("notify_on_empty"), False)

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
            if cleaned or not existing:
                write_json(CHINH_THONG_PATH, cleaned)
            elif monitor.is_chinh_thong_filter_enabled(cfg):
                return jsonify(
                    {
                        "success": False,
                        "error": "Danh sách báo chính thống trống. Thêm ít nhất một báo hoặc tắt «Chỉ báo chính thống».",
                    }
                ), 400

    cfg["google_news"] = gn
    write_json(CONFIG_PATH, cfg)
    ai_opts = monitor.resolve_ai_scan_options(cfg)
    rescan_started = False
    if ai_mode_saved:
        _AUTO_SCANNER.wake_reconfig(scan_soon=False)
        rescan_started = _AUTO_SCANNER.request_rescan_for_mode_change()
    else:
        _AUTO_SCANNER.wake_reconfig(scan_soon=False)

    trigger_scan = as_bool(data.get("trigger_scan"), False)
    scan_started = False
    if trigger_scan:
        st = _AUTO_SCANNER.get_status()
        if st.get("is_scanning"):
            print(
                "[SETTINGS] Yêu cầu quét sau lưu — xếp hàng sau lượt quét hiện tại",
                flush=True,
            )
        else:
            print(
                f"[SETTINGS] Quét ngay sau lưu — chế độ {ai_opts['label']}",
                flush=True,
            )

        def _scan_after_save() -> None:
            try:
                _AUTO_SCANNER.run_scan(
                    scan_hours=None,
                    source="settings",
                    blocking=True,
                    ignore_history=True,
                )
            except Exception as exc:
                print(f"[SETTINGS] Quét sau lưu lỗi: {exc}", flush=True)

        threading.Thread(
            target=_scan_after_save, name="settings-scan", daemon=True
        ).start()
        scan_started = True

    msg = "Đã lưu cài đặt"
    if rescan_started:
        msg = "Đã lưu — đang quét lại theo chế độ mới"
    elif scan_started:
        msg = "Đã lưu — đang quét…"
    return jsonify(
        {
            "success": True,
            "message": msg,
            "ai_scan_mode": ai_opts["mode"],
            "ai_scan_mode_label": ai_opts["label"],
            "scan_started": scan_started,
            "rescan_started": rescan_started,
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


@app.get("/api/data/stats")
def api_data_stats():
    time_range = str(request.args.get("time_range") or "all").strip().lower()
    target_name = str(request.args.get("target_name") or "").strip() or None
    try:
        return jsonify(
            {
                "success": True,
                "stats": get_data_stats(
                    time_range=time_range, target_name=target_name
                ),
                "time_range_options": [
                    {"id": k, "label": v.get("label", k)}
                    for k, v in TIME_RANGE_OPTIONS.items()
                ],
            }
        )
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.post("/api/data/clear")
def api_data_clear():
    st = _AUTO_SCANNER.get_status()
    if st.get("is_scanning"):
        return jsonify(
            {"success": False, "error": "Đang quét — hãy đợi xong rồi mới xóa dữ liệu"}
        ), 409

    body = request.get_json(silent=True) or {}
    items = body.get("items")
    if not isinstance(items, list) or not items:
        return jsonify({"success": False, "error": "Thiếu danh sách items cần xóa"}), 400

    target_name = str(body.get("target_name") or "").strip() or None
    confirm = str(body.get("confirm") or "").strip().upper()
    if confirm != "XOA":
        return jsonify(
            {
                "success": False,
                "error": 'Gửi confirm: "XOA" để xác nhận xóa',
            }
        ), 400

    time_range = str(body.get("time_range") or "all").strip().lower()

    try:
        out = clear_data(
            items, target_name=target_name, time_range=time_range
        )
        return jsonify({"success": True, **out})
    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), 400
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.get("/api/monitor/status")
def api_monitor_status():
    _AUTO_SCANNER.ensure_running()
    st = _AUTO_SCANNER.get_status()
    return jsonify({"success": True, "status": st})


@app.post("/monitor/run")
def monitor_run():
    """Bắt đầu quét trên thread riêng — không chặn Flask (tránh UI/API «đơ»)."""
    try:
        _AUTO_SCANNER.ensure_running()
        body = request.get_json(silent=True) or {}
        hours = None
        if body.get("scan_hours") is not None:
            try:
                hours = float(body.get("scan_hours"))
            except (TypeError, ValueError):
                hours = None
        target_name = str(body.get("target_name") or "").strip() or None
        ignore_history = True
        if body.get("ignore_history") is not None:
            ignore_history = as_bool(body.get("ignore_history"), True)
        st = _AUTO_SCANNER.get_status()
        if st.get("is_scanning"):
            who = target_name or "tất cả đối tượng"
            print(
                f"[MANUAL] Từ chối quét ({who}) — đang có lượt quét khác",
                flush=True,
            )
            return jsonify(
                {
                    "success": False,
                    "error": "Đang quét — vui lòng đợi lượt hiện tại xong",
                    "is_scanning": True,
                }
            ), 409

        who = target_name or "tất cả đối tượng"
        print(f"[MANUAL] Yêu cầu quét ({who}) — bắt đầu…", flush=True)

        def _manual_scan() -> None:
            try:
                out = _AUTO_SCANNER.run_scan(
                    scan_hours=hours,
                    source="manual",
                    target_name=target_name,
                    ignore_history=ignore_history,
                )
                if out is None and _AUTO_SCANNER.get_status().get("is_scanning"):
                    print(
                        "[MANUAL] Không chạy được — vẫn đang có lượt quét khác",
                        flush=True,
                    )
            except Exception as exc:
                print(f"[MANUAL] Quét lỗi: {exc}", flush=True)

        threading.Thread(
            target=_manual_scan, name="manual-scan", daemon=True
        ).start()
        return jsonify(
            {
                "success": True,
                "started": True,
                "queued": False,
                "message": "Đã bắt đầu quét — theo dõi trên giao diện hoặc log terminal",
            }
        )
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


def _start_background_scanner() -> None:
    _AUTO_SCANNER.start()


_start_background_scanner()
