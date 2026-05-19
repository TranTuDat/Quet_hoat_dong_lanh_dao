"""Gửi thông báo Telegram — tin tổng hợp theo đối tượng."""

from __future__ import annotations

import json
import re
import urllib.error
import urllib.request
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set

from src.json_io import read_json, write_json
from src.paths import TELEGRAM_SENT_PATH


def _telegram_cfg(cfg: Dict[str, Any]) -> Dict[str, Any]:
    tg = cfg.get("telegram")
    if not isinstance(tg, dict):
        tg = {}
        cfg["telegram"] = tg
    return tg


def is_telegram_enabled(cfg: Dict[str, Any]) -> bool:
    tg = _telegram_cfg(cfg)
    if not _as_bool(tg.get("enabled"), False):
        return False
    return bool(str(tg.get("bot_token") or "").strip() and str(tg.get("chat_id") or "").strip())


def _as_bool(val: Any, default: bool = False) -> bool:
    if isinstance(val, bool):
        return val
    if val is None:
        return default
    return str(val).strip().lower() not in ("0", "false", "no", "off", "")


def notify_key(record: Dict[str, Any]) -> str:
    name = str(record.get("target_name") or "").strip()
    url = str(record.get("url") or "").strip()
    return f"{name}|{url}"


def load_telegram_sent_keys() -> Set[str]:
    data = read_json(TELEGRAM_SENT_PATH, default=[])
    if not isinstance(data, list):
        return set()
    out: Set[str] = set()
    for x in data:
        if not isinstance(x, str):
            continue
        k = str(x).strip()
        if not k:
            continue
        if "|scan|" in k:
            continue
        out.add(k)
    return out


def save_telegram_sent_keys(keys: Set[str]) -> None:
    write_json(TELEGRAM_SENT_PATH, sorted(keys))


def _parse_ts(value: Any) -> Optional[datetime]:
    if not value:
        return None
    s = str(value).strip()
    for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M"):
        try:
            return datetime.strptime(s[:19], fmt)
        except Exception:
            pass
    try:
        from email.utils import parsedate_to_datetime

        return parsedate_to_datetime(s)
    except Exception:
        return None


def _rows_in_window(
    rows: List[Dict[str, Any]], target_name: str, cutoff: datetime
) -> List[Dict[str, Any]]:
    name = str(target_name or "").strip()
    out: List[Dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        if str(row.get("target_name", "")).strip() != name:
            continue
        ts = _parse_ts(row.get("timestamp"))
        if ts is None or ts >= cutoff:
            out.append(row)
    return out


def article_link_url(row: Dict[str, Any]) -> str:
    resolved = str(row.get("resolved_url") or "").strip()
    url = str(row.get("url") or "").strip()
    return resolved if resolved.startswith("http") else url


def _activity_label(row: Dict[str, Any]) -> str:
    ai = row.get("ai_result") if isinstance(row.get("ai_result"), dict) else {}
    summary = str(ai.get("Summary") or "").strip()
    title = str(row.get("title") or "").strip()
    text = summary or title or "Không có tiêu đề"
    return re.sub(r"\s+", " ", text)[:500]


def _dedupe_rows_by_url(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    seen: Set[str] = set()
    out: List[Dict[str, Any]] = []
    for row in rows:
        url = article_link_url(row)
        if not url or url in seen:
            continue
        seen.add(url)
        out.append(row)
    return out


def format_target_digest(
    index: int,
    target_name: str,
    *,
    hours: float,
    role_change: bool,
    activity_rows: List[Dict[str, Any]],
) -> str:
    """Tin plain text theo mẫu người dùng."""
    lines = [f"{index}. Đồng chí {target_name}:"]
    lines.append(f"- Thay đổi chức vụ: {'Có' if role_change else 'Không'}")
    h = int(hours) if hours == int(hours) else hours
    lines.append(f"- Hoạt động trong {h} giờ:")

    if not activity_rows:
        lines.append("\t(không có)")
    else:
        for i, row in enumerate(activity_rows, start=1):
            label = _activity_label(row)
            link = article_link_url(row)
            lines.append(f"\t+ Hoạt động {i}: {label}")
            lines.append(f"\tLink bài: {link if link else '(không có link)'}")

    return "\n".join(lines)


def format_target_empty(index: int, target_name: str, *, hours: float) -> str:
    h = int(hours) if hours == int(hours) else hours
    return (
        f"{index}. Đồng chí {target_name}:\n"
        f"- Thay đổi chức vụ: Không\n"
        f"- Hoạt động trong {h} giờ: Không có hoạt động\n"
    )


def empty_status_key(target_name: str) -> str:
    """Đã gửi tin 'không có hoạt động' — không gửi lại cho đến khi có tin mới."""
    return f"{str(target_name or '').strip()}|empty_status"


def explain_telegram_error(raw: str) -> str:
    msg = str(raw or "").strip()
    low = msg.lower()
    if "can't send messages to the bot" in low or "bots can't send messages to bots" in low:
        return "Chat ID sai (đang là ID bot). Cần ID người/nhóm nhận."
    if "chat not found" in low:
        return "Không tìm thấy chat — kiểm tra Chat ID."
    if "bot was blocked" in low:
        return "Đã chặn bot — mở bot và bấm Start."
    if "not a member" in low or "need administrator" in low:
        return "Bot chưa trong nhóm hoặc thiếu quyền."
    if "unauthorized" in low:
        return "Bot token sai."
    return msg or "Gửi Telegram thất bại"


def send_message(
    bot_token: str, chat_id: str, text: str, *, use_html: bool = False
) -> Dict[str, Any]:
    token = str(bot_token or "").strip()
    cid = str(chat_id or "").strip()
    if not token or not cid:
        return {"ok": False, "error": "Thiếu bot_token hoặc chat_id"}

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload: Dict[str, Any] = {
        "chat_id": cid,
        "text": text[:4096],
    }
    if use_html:
        payload["parse_mode"] = "HTML"

    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=25) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
            data = json.loads(raw) if raw else {}
            if data.get("ok"):
                return {"ok": True}
            desc = str(data.get("description") or data)
            return {"ok": False, "error": explain_telegram_error(desc)}
    except urllib.error.HTTPError as e:
        try:
            err_body = e.read().decode("utf-8", errors="replace")
            err_data = json.loads(err_body)
            desc = err_data.get("description") or err_body
        except Exception:
            desc = str(e)
        return {"ok": False, "error": explain_telegram_error(desc)}
    except Exception as e:
        return {"ok": False, "error": explain_telegram_error(str(e))}


def _group_new_by_target(records: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    grouped: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for row in records:
        if not isinstance(row, dict):
            continue
        name = str(row.get("target_name") or "").strip()
        if name:
            grouped[name].append(row)
    return grouped


def notify_records(
    cfg: Dict[str, Any],
    new_records: List[Dict[str, Any]],
    *,
    notifs: Optional[Dict[str, List[Dict[str, Any]]]] = None,
    hours: float = 24.0,
    all_targets: Optional[List[str]] = None,
    scan_id: str = "",
) -> Dict[str, Any]:
    """
    Gửi Telegram theo đối tượng:
    - Có tin MỚI lần này (chưa gửi URL) → báo cáo đầy đủ
    - Đã có hoạt động cũ, không tin mới → không gửi (tránh spam)
    - Không hoạt động / biến động trong cửa sổ → tin trống (một lần đến khi có tin mới)
    """
    result = {
        "sent": 0,
        "skipped_dup": 0,
        "skipped_filter": 0,
        "skipped_no_new": 0,
        "skipped_already_notified": 0,
        "sent_empty": 0,
        "errors": [],
        "enabled": False,
    }
    if not is_telegram_enabled(cfg):
        return result

    tg = _telegram_cfg(cfg)
    token = str(tg.get("bot_token") or "").strip()
    chat_id = str(tg.get("chat_id") or "").strip()
    sent_keys = load_telegram_sent_keys()
    sent = 0
    sent_empty = 0
    skipped_dup = 0
    skipped_filter = 0
    skipped_already = 0
    errors: List[str] = []

    notif_data = notifs if isinstance(notifs, dict) else {}
    channel_hd = notif_data.get("channel_hoatdong") or []
    channel_bd = notif_data.get("channel_biendong") or []
    if not isinstance(channel_hd, list):
        channel_hd = []
    if not isinstance(channel_bd, list):
        channel_bd = []

    cutoff = datetime.now() - timedelta(hours=max(0.1, float(hours)))
    grouped = _group_new_by_target(new_records)

    targets_order: List[str] = []
    if all_targets:
        for name in all_targets:
            n = str(name or "").strip()
            if n and n not in targets_order:
                targets_order.append(n)
    for name in grouped:
        if name not in targets_order:
            targets_order.append(name)

    if not targets_order:
        print("  [TELEGRAM] không có đối tượng trong config")
        return {**result, "enabled": True}

    h_label = int(hours) if hours == int(hours) else hours
    header = f"📋 Báo cáo giám sát — {datetime.now().strftime('%d/%m/%Y %H:%M')}\n\n"

    for idx, target_name in enumerate(targets_order, start=1):
        rows_hd = _dedupe_rows_by_url(_rows_in_window(channel_hd, target_name, cutoff))
        rows_bd = _dedupe_rows_by_url(_rows_in_window(channel_bd, target_name, cutoff))
        role_change = len(rows_bd) > 0

        batch = grouped.get(target_name, [])
        pending = [r for r in batch if notify_key(r) not in sent_keys]
        has_content = role_change or len(rows_hd) > 0
        empty_key = empty_status_key(target_name)

        if pending:
            if _as_bool(tg.get("notify_role_change_only"), False):
                pending_change = any(
                    isinstance(r.get("ai_result"), dict)
                    and r["ai_result"].get("Is_Change")
                    for r in pending
                )
                if not role_change and not pending_change:
                    skipped_filter += 1
                    continue

            body = format_target_digest(
                idx,
                target_name,
                hours=hours,
                role_change=role_change,
                activity_rows=rows_hd,
            )
            out = send_message(token, chat_id, header + body, use_html=False)
            if out.get("ok"):
                for r in pending:
                    sent_keys.add(notify_key(r))
                sent_keys.discard(empty_key)
                sent += 1
                print(
                    f"  [TELEGRAM] bao cao moi: {target_name} "
                    f"({len(pending)} tin / {h_label}h)"
                )
            else:
                err = str(out.get("error") or "unknown")
                errors.append(f"{target_name}: {err}")
                print(f"  [TELEGRAM] FAIL {target_name}: {err}")
            continue

        if has_content:
            skipped_already += 1
            print(f"  [TELEGRAM] bo qua {target_name}: tin cu da gui truoc do")
            continue

        if empty_key in sent_keys:
            skipped_dup += 1
            continue

        body = format_target_empty(idx, target_name, hours=hours)
        out = send_message(token, chat_id, header + body, use_html=False)
        if out.get("ok"):
            sent_keys.add(empty_key)
            sent += 1
            sent_empty += 1
            print(f"  [TELEGRAM] trong (khong hoat dong): {target_name}")
        else:
            err = str(out.get("error") or "unknown")
            errors.append(f"{target_name}: {err}")
            print(f"  [TELEGRAM] FAIL {target_name}: {err}")

    if sent_keys:
        save_telegram_sent_keys(sent_keys)

    return {
        "sent": sent,
        "skipped_dup": skipped_dup,
        "skipped_filter": skipped_filter,
        "skipped_no_new": 0 if new_records else 1,
        "skipped_already_notified": skipped_already,
        "sent_empty": sent_empty,
        "errors": errors[:5],
        "enabled": True,
    }


def send_test_message(cfg: Dict[str, Any]) -> Dict[str, Any]:
    tg = _telegram_cfg(cfg)
    token = str(tg.get("bot_token") or "").strip()
    chat_id = str(tg.get("chat_id") or "").strip()
    if not token or not chat_id:
        return {"ok": False, "error": "Chưa cấu hình bot_token hoặc chat_id"}
    sample = format_target_digest(
        1,
        "Tô Lâm (mẫu)",
        hours=24,
        role_change=False,
        activity_rows=[
            {
                "title": "Ví dụ hoạt động",
                "url": "https://example.com",
                "ai_result": {"Summary": "Đây là tin thử nghiệm."},
            }
        ],
    )
    return send_message(
        token,
        chat_id,
        "✅ Kiểm tra Telegram\n\n" + sample,
        use_html=False,
    )
