"""Gửi thông báo Telegram — tin tổng hợp theo đối tượng."""

from __future__ import annotations

import html
import json
import re
import threading
import urllib.error
import urllib.request
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set, Tuple

_tg_sent_lock = threading.Lock()

from src.common import article_link_url, as_bool, parse_ts
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
    if not as_bool(tg.get("enabled"), False):
        return False
    return bool(str(tg.get("bot_token") or "").strip() and str(tg.get("chat_id") or "").strip())


def notify_key(record: Dict[str, Any]) -> str:
    """Khóa chống gửi trùng — dùng link bài (ưu tiên URL đã decode)."""
    name = str(record.get("target_name") or "").strip()
    url = article_link_url(record) or str(record.get("url") or "").strip()
    return f"{name}|{url}"


def load_telegram_sent_keys() -> Set[str]:
    with _tg_sent_lock:
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
    with _tg_sent_lock:
        write_json(TELEGRAM_SENT_PATH, sorted(keys))


def is_notify_empty_enabled(cfg: Dict[str, Any]) -> bool:
    """Tắt mặc định — tránh gửi tin «không hoạt động» rồi lại gửi tin có bài."""
    tg = _telegram_cfg(cfg)
    return as_bool(tg.get("notify_on_empty"), False)


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
        ts = parse_ts(row.get("timestamp"))
        if ts is None or ts >= cutoff:
            out.append(row)
    return out


def _escape_html(text: str) -> str:
    return html.escape(re.sub(r"\s+", " ", str(text or "").strip()), quote=False)


def _escape_html_attr(text: str) -> str:
    """Giá trị thuộc tính href — escape cả dấu nháy để không vỡ thẻ <a>."""
    return html.escape(re.sub(r"\s+", " ", str(text or "").strip()), quote=True)


_TELEGRAM_MAX_LEN = 4096
_TELEGRAM_SAFE_LEN = 4080


def _split_digest_block(block: str, max_len: int) -> List[str]:
    """Chia một block đối tượng nếu quá dài — không cắt giữa từng bài."""
    block = block.strip()
    if not block or len(block) <= max_len:
        return [block] if block else []

    parts = re.split(r"(?=\n\t\+ Bài \d+:\n)", block)
    if len(parts) <= 1:
        lines = block.split("\n")
        chunks: List[str] = []
        buf = ""
        for line in lines:
            trial = f"{buf}\n{line}" if buf else line
            if len(trial) <= max_len:
                buf = trial
            else:
                if buf:
                    chunks.append(buf)
                buf = line
        if buf:
            chunks.append(buf)
        return chunks

    prefix = parts[0].strip()
    mini_lines: List[str] = []
    for line in prefix.split("\n"):
        mini_lines.append(line)
        if "- Hoạt động trong" in line:
            break
    mini = ("\n".join(mini_lines).strip() + "\n") if mini_lines else ""

    out: List[str] = []
    carry = prefix
    for art in parts[1:]:
        seg = carry + art
        if len(seg) <= max_len:
            carry = seg
            continue
        if carry.strip():
            out.append(carry.strip())
        carry = f"{mini}{art.lstrip()}"
    if carry.strip():
        out.append(carry.strip())
    return out


def _pack_telegram_messages(
    header: str,
    blocks: List[str],
    *,
    max_len: int = _TELEGRAM_SAFE_LEN,
) -> List[str]:
    """Gộp các block HTML thành nhiều tin Telegram, tránh cắt giữa thẻ."""
    pieces: List[str] = []
    for block in blocks:
        pieces.extend(_split_digest_block(block, max_len))

    if not pieces:
        return []

    messages: List[str] = []
    buf = ""
    cont = "📋 (tiếp theo)\n\n"

    for piece in pieces:
        if not piece:
            continue
        if not buf:
            trial = header + piece
            if len(trial) <= max_len:
                buf = trial
                continue
            trial = cont + piece
            if len(trial) <= max_len:
                buf = trial
                continue
            for sub in _split_digest_block(piece, max_len):
                messages.append(cont + sub)
            buf = ""
            continue

        trial = buf + "\n\n" + piece
        if len(trial) <= max_len:
            buf = trial
            continue
        messages.append(buf)
        buf = ""
        trial = cont + piece
        if len(trial) <= max_len:
            buf = trial
        else:
            for sub in _split_digest_block(piece, max_len):
                messages.append(cont + sub)
    if buf:
        messages.append(buf)
    return messages


def _published_label(row: Dict[str, Any]) -> str:
    raw = (
        row.get("published")
        or row.get("published date")
        or row.get("published_at")
        or row.get("publishedAt")
        or row.get("date")
    )
    ts = parse_ts(raw)
    if ts is not None:
        return ts.strftime("%d/%m/%Y %H:%M")
    s = str(raw or "").strip()
    return s if s else "—"


def _is_role_article(row: Dict[str, Any], role_urls: Set[str]) -> bool:
    """In đậm chỉ khi đã vào kênh biến động hoặc AI xác nhận đổi chức vụ có chứng cứ."""
    url = article_link_url(row)
    if url and url in role_urls:
        return True
    ai = row.get("ai_result") if isinstance(row.get("ai_result"), dict) else {}
    if not ai.get("Is_Change") or not ai.get("Matched_Target"):
        return False
    return bool(
        str(ai.get("From_Position") or "").strip()
        or str(ai.get("To_Position") or "").strip()
        or str(ai.get("Decision_Text") or "").strip()
    )


def _format_article_lines(
    index: int,
    row: Dict[str, Any],
    *,
    html_mode: bool,
    bold_block: bool = False,
) -> List[str]:
    """Tiêu đề, link, thời gian đăng; bài chức vụ in đậm cả khối."""
    title = str(row.get("title") or "").strip() or "—"
    link = article_link_url(row) or ""
    when = _published_label(row)
    inner: List[str] = [f"+ Bài {index}:"]
    if html_mode:
        inner.append(f"Tiêu đề: {_escape_html(title)}")
        if link:
            safe_url = _escape_html_attr(link)
            label = _escape_html(link)
            inner.append(f'Link: <a href="{safe_url}">{label}</a>')
        else:
            inner.append("Link: (không có link)")
        inner.append(f"Thời gian đăng: {_escape_html(when)}")
    else:
        inner.append(f"Tiêu đề: {title}")
        inner.append(f"Link: {link if link else '(không có link)'}")
        inner.append(f"Thời gian đăng: {when}")

    block = "\n".join(f"\t{line}" for line in inner)
    if bold_block and html_mode:
        inner[0] = f"<b>{inner[0]}</b>"
        if len(inner) > 1:
            inner[1] = f"<b>{inner[1]}</b>"
        block = "\n".join(f"\t{line}" for line in inner)
    return [block]


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


def _merge_article_rows(
    activity_rows: List[Dict[str, Any]],
    role_rows: Optional[List[Dict[str, Any]]],
) -> List[Dict[str, Any]]:
    """Gộp tin hoạt động + chức vụ, không trùng URL (ưu tiên bản chức vụ)."""
    merged: List[Dict[str, Any]] = []
    seen: Set[str] = set()
    for row in list(role_rows or []) + list(activity_rows):
        if not isinstance(row, dict):
            continue
        url = article_link_url(row)
        if not url or url in seen:
            continue
        seen.add(url)
        merged.append(row)
    return merged


def format_target_digest(
    index: int,
    target_name: str,
    *,
    hours: float,
    role_change: bool,
    activity_rows: List[Dict[str, Any]],
    role_rows: Optional[List[Dict[str, Any]]] = None,
    html_mode: bool = True,
) -> str:
    """Tin Telegram: tiêu đề, link, thời gian; bài về chức vụ in đậm cả khối."""
    name = _escape_html(target_name) if html_mode else target_name
    lines = [f"{index}. Đồng chí {name}:"]
    lines.append(f"- Thay đổi chức vụ: {'Có' if role_change else 'Không'}")

    role_list = list(role_rows or [])
    role_urls = {article_link_url(r) for r in role_list if article_link_url(r)}
    merged = _merge_article_rows(activity_rows, role_list)

    h = int(hours) if hours == int(hours) else hours
    lines.append(f"- Hoạt động trong {h} giờ:")
    if not merged:
        lines.append("\t(không có)")
    else:
        for i, row in enumerate(merged, start=1):
            lines.extend(
                _format_article_lines(
                    i,
                    row,
                    html_mode=html_mode,
                    bold_block=_is_role_article(row, role_urls),
                )
            )

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
    notify_empty = as_bool(tg.get("notify_on_empty"), False)
    role_only = as_bool(tg.get("notify_role_change_only"), False)

    digest_blocks: List[str] = []
    digest_pending: List[Dict[str, Any]] = []
    digest_targets: List[str] = []
    empty_blocks: List[Tuple[int, str]] = []

    for idx, target_name in enumerate(targets_order, start=1):
        rows_hd = _dedupe_rows_by_url(_rows_in_window(channel_hd, target_name, cutoff))
        rows_bd = _dedupe_rows_by_url(_rows_in_window(channel_bd, target_name, cutoff))
        role_change = len(rows_bd) > 0

        batch = grouped.get(target_name, [])
        pending = [r for r in batch if notify_key(r) not in sent_keys]
        has_content = role_change or len(rows_hd) > 0
        empty_key = empty_status_key(target_name)

        if pending:
            if role_only:
                pending_change = any(
                    isinstance(r.get("ai_result"), dict)
                    and r["ai_result"].get("Is_Change")
                    and r["ai_result"].get("Matched_Target")
                    and (
                        str(r["ai_result"].get("From_Position") or "").strip()
                        or str(r["ai_result"].get("To_Position") or "").strip()
                        or str(r["ai_result"].get("Decision_Text") or "").strip()
                    )
                    for r in pending
                )
                if not role_change and not pending_change:
                    skipped_filter += 1
                    continue

            digest_blocks.append(
                format_target_digest(
                    idx,
                    target_name,
                    hours=hours,
                    role_change=role_change,
                    activity_rows=rows_hd,
                    role_rows=rows_bd,
                    html_mode=True,
                )
            )
            digest_pending.extend(pending)
            digest_targets.append(target_name)
            continue

        if has_content:
            skipped_already += 1
            print(f"  [TELEGRAM] bo qua {target_name}: tin cu da gui truoc do")
            continue

        if not notify_empty:
            skipped_dup += 1
            continue

        if empty_key in sent_keys:
            skipped_dup += 1
            continue

        empty_blocks.append((idx, target_name))

    if digest_blocks:
        tg_messages = _pack_telegram_messages(header, digest_blocks)
        all_ok = True
        err = ""
        for part_idx, text in enumerate(tg_messages, start=1):
            out = send_message(token, chat_id, text, use_html=True)
            if not out.get("ok"):
                all_ok = False
                err = str(out.get("error") or "unknown")
                errors.append(err)
                print(
                    f"  [TELEGRAM] FAIL tong hop"
                    f"{f' (phan {part_idx}/{len(tg_messages)})' if len(tg_messages) > 1 else ''}: {err}"
                )
                break
        if all_ok:
            for r in digest_pending:
                sent_keys.add(notify_key(r))
            for tname in digest_targets:
                sent_keys.discard(empty_status_key(tname))
            sent += len(tg_messages)
            names = ", ".join(digest_targets[:5])
            if len(digest_targets) > 5:
                names += f" (+{len(digest_targets) - 5})"
            parts_note = f", {len(tg_messages)} tin" if len(tg_messages) > 1 else ""
            print(
                f"  [TELEGRAM] tong hop{parts_note}: {len(digest_targets)} doi tuong "
                f"({len(digest_pending)} bai moi / {h_label}h) — {names}"
            )

    if notify_empty and empty_blocks:
        parts = [
            format_target_empty(idx, target_name, hours=hours)
            for idx, target_name in empty_blocks
        ]
        text = header + "\n\n".join(parts)
        if len(text) > 4090:
            text = text[:4087] + "…"
        out = send_message(token, chat_id, text, use_html=False)
        if out.get("ok"):
            for _, target_name in empty_blocks:
                sent_keys.add(empty_status_key(target_name))
            sent += 1
            sent_empty += len(empty_blocks)
            print(
                f"  [TELEGRAM] 1 tin trong: {len(empty_blocks)} doi tuong khong hoat dong"
            )
        else:
            err = str(out.get("error") or "unknown")
            errors.append(err)
            print(f"  [TELEGRAM] FAIL tin trong: {err}")

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
        role_change=True,
        activity_rows=[
            {
                "title": "Ví dụ hoạt động thường",
                "url": "https://example.com/a",
                "resolved_url": "https://example.com/a",
                "published": "2026-05-21T10:30:00",
                "news_kind": "hoatdong",
            }
        ],
        role_rows=[
            {
                "title": "Ví dụ tin chức vụ (in đậm)",
                "url": "https://example.com/b",
                "resolved_url": "https://example.com/b",
                "published": "2026-05-20T08:00:00",
                "news_kind": "biendong",
            }
        ],
        html_mode=True,
    )
    return send_message(
        token,
        chat_id,
        "✅ Kiểm tra Telegram\n\n" + sample,
        use_html=True,
    )
