"""Đọc thống kê và xóa dữ liệu chạy trong data/."""

from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Set, Tuple

from src.common import parse_ts
from src.json_io import read_json, write_json
from src.paths import (
    HISTORY_PATH,
    NOTIFICATIONS_PATH,
    TELEGRAM_SENT_PATH,
    URL_DECODE_CACHE_PATH,
    ensure_project_dirs,
)

_EMPTY_NOTIFICATIONS: Dict[str, List[Any]] = {
    "channel_hoatdong": [],
    "channel_biendong": [],
}

_CLEAR_KEYS = ("notifications", "history", "telegram_sent", "decode_cache")

TIME_RANGE_OPTIONS: Dict[str, Dict[str, Any]] = {
    "1h": {"label": "1 giờ qua", "hours": 1},
    "24h": {"label": "24 giờ qua", "hours": 24},
    "7d": {"label": "7 ngày qua", "days": 7},
    "4w": {"label": "4 tuần qua", "days": 28},
    "all": {"label": "Toàn bộ", "hours": None},
}


def resolve_time_cutoff(time_range: str) -> Tuple[Optional[datetime], str]:
    key = str(time_range or "all").strip().lower()
    opt = TIME_RANGE_OPTIONS.get(key) or TIME_RANGE_OPTIONS["all"]
    label = str(opt.get("label") or "Toàn bộ")
    if key == "all":
        return None, label
    now = datetime.now()
    if opt.get("hours") is not None:
        return now - timedelta(hours=float(opt["hours"])), label
    if opt.get("days") is not None:
        return now - timedelta(days=float(opt["days"])), label
    return None, label


def _in_delete_window(ts: Optional[datetime], cutoff: Optional[datetime]) -> bool:
    if cutoff is None:
        return True
    if ts is None:
        return False
    return ts >= cutoff


def _notify_key(name: str, url: str) -> str:
    return f"{str(name or '').strip()}|{str(url or '').strip()}"


def _file_size(path) -> int:
    try:
        return os.path.getsize(path) if path.is_file() else 0
    except OSError:
        return 0


def _count_notifications(data: Any) -> Dict[str, int]:
    if not isinstance(data, dict):
        return {"hoatdong": 0, "biendong": 0, "total": 0}
    hd = data.get("channel_hoatdong") or []
    bd = data.get("channel_biendong") or []
    n_hd = len(hd) if isinstance(hd, list) else 0
    n_bd = len(bd) if isinstance(bd, list) else 0
    return {"hoatdong": n_hd, "biendong": n_bd, "total": n_hd + n_bd}


def _iter_notif_rows(notifs: Dict[str, Any]):
    for ch in ("channel_hoatdong", "channel_biendong"):
        for row in notifs.get(ch) or []:
            if isinstance(row, dict):
                yield row


def _collect_drop_sets(
    notifs: Dict[str, Any],
    cutoff: Optional[datetime],
    *,
    target_name: str = "",
) -> Tuple[Set[str], Set[str]]:
    """Khóa history/TG và URL (decode cache) sẽ bị xóa theo cửa sổ thời gian."""
    name = str(target_name or "").strip()
    keys: Set[str] = set()
    urls: Set[str] = set()
    for row in _iter_notif_rows(notifs):
        tname = str(row.get("target_name") or "").strip()
        if name and tname != name:
            continue
        if not _in_delete_window(parse_ts(row.get("timestamp")), cutoff):
            continue
        url = str(row.get("url") or "").strip()
        if tname and url:
            keys.add(_notify_key(tname, url))
        if url:
            urls.add(url)
    return keys, urls


def _count_notifs_in_window(
    notifs: Dict[str, Any],
    cutoff: Optional[datetime],
    *,
    target_name: str = "",
) -> int:
    name = str(target_name or "").strip()
    n = 0
    for row in _iter_notif_rows(notifs):
        tname = str(row.get("target_name") or "").strip()
        if name and tname != name:
            continue
        if _in_delete_window(parse_ts(row.get("timestamp")), cutoff):
            n += 1
    return n


def get_data_stats(
    *,
    time_range: str = "all",
    target_name: Optional[str] = None,
) -> Dict[str, Any]:
    ensure_project_dirs()
    cutoff, range_label = resolve_time_cutoff(time_range)
    name = str(target_name or "").strip()

    notifs = read_json(NOTIFICATIONS_PATH, default=_EMPTY_NOTIFICATIONS)
    if not isinstance(notifs, dict):
        notifs = dict(_EMPTY_NOTIFICATIONS)
    history = read_json(HISTORY_PATH, default=[])
    tg_sent = read_json(TELEGRAM_SENT_PATH, default=[])
    cache = read_json(URL_DECODE_CACHE_PATH, default={})

    counts = _count_notifications(notifs)
    in_window = _count_notifs_in_window(notifs, cutoff, target_name=name)
    drop_keys, drop_urls = _collect_drop_sets(notifs, cutoff, target_name=name)

    hist_total = len(history) if isinstance(history, list) else 0
    tg_total = len(tg_sent) if isinstance(tg_sent, list) else 0
    cache_total = len(cache) if isinstance(cache, dict) else 0

    hist_in = (
        hist_total
        if cutoff is None
        else _count_history_in_keys(history, drop_keys)
    )
    tg_in = (
        tg_total if cutoff is None else _count_tg_in_keys(tg_sent, drop_keys)
    )
    cache_in = (
        cache_total
        if cutoff is None
        else _count_cache_urls(cache, drop_urls)
    )

    return {
        "time_range": time_range,
        "time_range_label": range_label,
        "in_window_notifications": in_window,
        "notifications": {**counts, "bytes": _file_size(NOTIFICATIONS_PATH)},
        "history": {
            "entries": hist_in,
            "entries_total": hist_total,
            "bytes": _file_size(HISTORY_PATH),
        },
        "telegram_sent": {
            "entries": tg_in,
            "entries_total": tg_total,
            "bytes": _file_size(TELEGRAM_SENT_PATH),
        },
        "decode_cache": {
            "entries": cache_in,
            "entries_total": cache_total,
            "bytes": _file_size(URL_DECODE_CACHE_PATH),
        },
    }


def _count_history_in_keys(history: Any, keys: Set[str]) -> int:
    if not isinstance(history, list) or not keys:
        return 0
    return sum(1 for k in history if isinstance(k, str) and k in keys)


def _count_tg_in_keys(sent: Any, keys: Set[str]) -> int:
    if not isinstance(sent, list) or not keys:
        return 0
    return sum(1 for k in sent if isinstance(k, str) and k in keys)


def _count_cache_urls(cache: Any, urls: Set[str]) -> int:
    if not isinstance(cache, dict) or not urls:
        return 0
    return sum(1 for k in cache if str(k) in urls)


def _prune_notifications(
    notifs: Dict[str, Any],
    cutoff: Optional[datetime],
    *,
    target_name: str = "",
) -> Tuple[Dict[str, List[Dict[str, Any]]], int]:
    name = str(target_name or "").strip()
    removed = 0
    out: Dict[str, List[Dict[str, Any]]] = {}
    for ch in ("channel_hoatdong", "channel_biendong"):
        rows = notifs.get(ch) or []
        if not isinstance(rows, list):
            out[ch] = []
            continue
        kept: List[Dict[str, Any]] = []
        for row in rows:
            if not isinstance(row, dict):
                kept.append(row)
                continue
            tname = str(row.get("target_name") or "").strip()
            if name and tname != name:
                kept.append(row)
                continue
            if _in_delete_window(parse_ts(row.get("timestamp")), cutoff):
                removed += 1
                continue
            kept.append(row)
        out[ch] = kept
    return out, removed


def _filter_notifs_by_target(
    notifs: Dict[str, List[Dict[str, Any]]], target_name: str
) -> Dict[str, List[Dict[str, Any]]]:
    name = str(target_name or "").strip()
    if not name:
        return notifs
    out = dict(notifs)
    for ch in ("channel_hoatdong", "channel_biendong"):
        rows = notifs.get(ch) or []
        if not isinstance(rows, list):
            out[ch] = []
            continue
        out[ch] = [
            r
            for r in rows
            if isinstance(r, dict) and str(r.get("target_name") or "").strip() != name
        ]
    return out


def _prune_history(history: List[Any], drop_keys: Set[str]) -> List[Any]:
    if not drop_keys:
        return history if isinstance(history, list) else []
    return [
        k
        for k in (history if isinstance(history, list) else [])
        if isinstance(k, str) and k not in drop_keys
    ]


def _prune_telegram_sent(sent: List[Any], drop_keys: Set[str]) -> List[Any]:
    if not drop_keys:
        return sent if isinstance(sent, list) else []
    return [k for k in sent if isinstance(k, str) and k not in drop_keys]


def _prune_decode_cache(cache: Dict[str, Any], drop_urls: Set[str]) -> Dict[str, Any]:
    if not isinstance(cache, dict):
        return {}
    if not drop_urls:
        return dict(cache)
    return {k: v for k, v in cache.items() if str(k) not in drop_urls}


def clear_data(
    items: List[str],
    *,
    target_name: Optional[str] = None,
    time_range: str = "all",
) -> Dict[str, Any]:
    ensure_project_dirs()
    want = {str(x).strip().lower() for x in items if str(x).strip()}
    if "all" in want:
        want = set(_CLEAR_KEYS)

    invalid = want - set(_CLEAR_KEYS)
    if invalid:
        raise ValueError(f"Loại dữ liệu không hợp lệ: {', '.join(sorted(invalid))}")

    if not want:
        raise ValueError("Chưa chọn loại dữ liệu cần xóa")

    tr = str(time_range or "all").strip().lower()
    if tr not in TIME_RANGE_OPTIONS:
        raise ValueError("Khoảng thời gian không hợp lệ")

    name = str(target_name or "").strip()
    cutoff, range_label = resolve_time_cutoff(tr)
    cleared: List[str] = []
    removed_notifications = 0

    notifs = read_json(NOTIFICATIONS_PATH, default=_EMPTY_NOTIFICATIONS)
    if not isinstance(notifs, dict):
        notifs = dict(_EMPTY_NOTIFICATIONS)

    drop_keys, drop_urls = _collect_drop_sets(notifs, cutoff, target_name=name)

    if "notifications" in want:
        if name and cutoff is None:
            before = _count_notifications(notifs)["total"]
            notifs = _filter_notifs_by_target(notifs, name)
            removed_notifications = before - _count_notifications(notifs)["total"]
        else:
            notifs, removed_notifications = _prune_notifications(
                notifs, cutoff, target_name=name
            )
        write_json(NOTIFICATIONS_PATH, notifs)
        cleared.append("notifications")

    if "history" in want:
        hist = read_json(HISTORY_PATH, default=[])
        if cutoff is None and not name:
            write_json(HISTORY_PATH, [])
        else:
            write_json(HISTORY_PATH, _prune_history(hist, drop_keys))
        cleared.append("history")

    if "telegram_sent" in want:
        sent = read_json(TELEGRAM_SENT_PATH, default=[])
        if cutoff is None and not name:
            write_json(TELEGRAM_SENT_PATH, [])
        else:
            write_json(TELEGRAM_SENT_PATH, _prune_telegram_sent(sent, drop_keys))
        cleared.append("telegram_sent")

    if "decode_cache" in want and not name:
        cache = read_json(URL_DECODE_CACHE_PATH, default={})
        if cutoff is None:
            write_json(URL_DECODE_CACHE_PATH, {})
        else:
            write_json(URL_DECODE_CACHE_PATH, _prune_decode_cache(cache, drop_urls))
        cleared.append("decode_cache")

    return {
        "cleared": cleared,
        "target_name": name or None,
        "time_range": tr,
        "time_range_label": range_label,
        "removed_notifications": removed_notifications,
        "stats": get_data_stats(time_range="all", target_name=name or None),
    }
