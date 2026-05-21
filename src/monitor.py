from __future__ import annotations

import json
import os
import re
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set, Tuple
from urllib.parse import urlparse

from gnews import GNews

if sys.platform == "win32":
    for _stream in (sys.stdout, sys.stderr):
        try:
            _stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

import google.generativeai as genai

from src.json_io import read_json, write_json
from src.paths import (
    CHINH_THONG_PATH,
    CONFIG_PATH,
    HISTORY_PATH,
    NOTIFICATIONS_PATH,
    URL_DECODE_CACHE_PATH,
    path_str,
)
from src.press_whitelist import PressWhitelist, _norm_domain
from src.rss_fetch import collect_rss_for_target
from src.common import article_link_url, is_google_news_url, parse_ts
from src.telegram_notify import is_telegram_enabled, notify_records


def load_decode_cache() -> Dict[str, str]:
    data = read_json(URL_DECODE_CACHE_PATH, default={})
    if not isinstance(data, dict):
        return {}
    return {str(k): str(v) for k, v in data.items() if k and v}


def save_decode_cache(cache: Dict[str, str]) -> None:
    write_json(URL_DECODE_CACHE_PATH, cache)


def _decode_google_news_url(url: str, *, interval: float = 0.15) -> Optional[str]:
    u = str(url or "").strip()
    if not u or not is_google_news_url(u):
        return u if u.startswith("http") else None
    try:
        from googlenewsdecoder import gnewsdecoder

        out = gnewsdecoder(u, interval=max(0.05, float(interval)))
        if isinstance(out, dict):
            dec = str(out.get("decoded_url") or out.get("url") or "").strip()
            if dec.startswith("http"):
                return dec
    except Exception:
        pass
    return None


def decode_batch(
    urls: List[str], *, workers: int = 4, interval: float = 0.15
) -> Dict[str, str]:
    """Decode song song + cache — chỉ gọi với URL chưa có trong history."""
    result: Dict[str, str] = {}
    cache = load_decode_cache()
    cache_dirty = False
    to_decode: List[str] = []

    for raw in urls:
        u = str(raw or "").strip()
        if not u or u in result:
            continue
        if not is_google_news_url(u):
            result[u] = u
            continue
        if u in cache and cache[u].startswith("http"):
            result[u] = cache[u]
            continue
        to_decode.append(u)

    if not to_decode:
        return result

    w = max(1, min(int(workers), 8))

    def _job(u: str) -> Tuple[str, Optional[str]]:
        return u, _decode_google_news_url(u, interval=interval)

    with ThreadPoolExecutor(max_workers=w) as pool:
        futures = [pool.submit(_job, u) for u in to_decode]
        for fut in as_completed(futures):
            try:
                u, dec = fut.result()
                if dec:
                    result[u] = dec
                    cache[u] = dec
                    cache_dirty = True
            except Exception:
                pass

    if cache_dirty:
        save_decode_cache(cache)
    return result


def _article_dedup_key(art: Dict[str, Any]) -> str:
    resolved = str(art.get("resolved_url") or "").strip()
    url = str(art.get("url") or "").strip()
    pick = resolved if resolved.startswith("http") and not is_google_news_url(resolved) else url
    if not pick.startswith("http"):
        return ""
    try:
        p = urlparse(pick)
        host = (p.netloc or "").lower()
        if host.startswith("www."):
            host = host[4:]
        path = (p.path or "/").rstrip("/") or "/"
        return f"{host}{path}"
    except Exception:
        return pick


_KIND_RANK = {"biendong": 2, "hoatdong": 1}


def _merge_article_pairs(
    pairs: List[Tuple[Dict[str, Any], str]],
) -> List[Tuple[Dict[str, Any], str]]:
    """
    Hai lượt quét GNews: (1) chỉ tên → hoatdong, (2) tên + từ khóa chức vụ → biendong.
    Cùng URL xuất hiện ở cả hai → giữ biendong, bỏ bản hoatdong (Gemini chỉ chạy một lần).
    """
    by_key: Dict[str, Tuple[Dict[str, Any], str]] = {}
    for art, kind in pairs:
        key = _article_dedup_key(art)
        if not key:
            continue
        prev = by_key.get(key)
        if prev is None or _KIND_RANK.get(kind, 0) > _KIND_RANK.get(prev[1], 0):
            by_key[key] = (art, kind)
    return list(by_key.values())


def _scan_perf_options(gn: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "use_rss": _gn_bool(gn.get("use_rss_feeds"), True),
        "rss_max_per_feed": max(5, min(80, int(gn.get("rss_max_per_feed") or 40))),
        "decode_workers": max(1, min(8, int(gn.get("decode_workers") or 4))),
        "gemini_workers": max(1, min(6, int(gn.get("gemini_workers") or 3))),
        "decode_interval": max(0.05, float(gn.get("decode_interval") or 0.15)),
    }


ROLE_QUERY_SUFFIX = (
    "(bổ nhiệm OR miễn nhiệm OR giữ chức OR phân công OR tân nhiệm OR quyết định)"
)

_ROLE_CHANGE_STRONG = re.compile(
    r"bổ\s*nhiệm|miễn\s*nhiệm|bãi\s*nhiệm|điều\s*động|bổ\s*nhiệm\s+giữ\s+chức|"
    r"luân\s+chuyển|thay\s+thế|bổ\s+nhiệm\s+lại|giữ\s+chức\s+vụ|được\s+giao\s+giữ",
    re.IGNORECASE,
)
_ACTIVITY_ROUTINE = re.compile(
    r"họp\b|hội\s+nghị|làm\s+việc|thăm\b|kiểm\s+tra|phát\s+biểu|"
    r"dự\s+(lễ|hội)|chủ\s+trì|dâng\s+hương|gặp\s+mặt|triển\s+khai|"
    r"động\s+viên|chúc\s+mừng|kỷ\s+niệm",
    re.IGNORECASE,
)


@dataclass
class Target:
    name: str
    position: str = ""


def load_config() -> Dict[str, Any]:
    cfg = read_json(CONFIG_PATH, default={})
    if not isinstance(cfg, dict):
        raise ValueError("config.json không hợp lệ")
    cfg.setdefault("gemini_api_key", "")
    cfg.setdefault("google_news", {})
    cfg.setdefault("targets", [])
    return cfg


def _gn_bool(val: Any, default: bool = True) -> bool:
    if isinstance(val, bool):
        return val
    return str(val).strip().lower() not in ("0", "false", "no", "off")


def is_chinh_thong_filter_enabled(cfg: Optional[Dict[str, Any]] = None) -> bool:
    data = cfg if cfg is not None else load_config()
    gn = data.get("google_news") if isinstance(data.get("google_news"), dict) else {}
    return _gn_bool(gn.get("filter_chinh_thong_only", True), True)


def _gnews_publisher_href(art: Dict[str, Any]) -> str:
    pub = art.get("publisher")
    if isinstance(pub, dict):
        return str(pub.get("href") or pub.get("url") or "").strip()
    if isinstance(pub, str) and pub.strip().startswith("http"):
        return pub.strip()
    return ""


def _quote_gnews_term(text: str) -> str:
    q = str(text or "").strip()
    if not q:
        return q
    if q.startswith('"') and q.endswith('"'):
        return q
    return f'"{q}"'


AI_SCAN_PROFILES: Dict[str, Dict[str, Any]] = {
    "keyword": {
        "label": "Từ khóa (không Gemini)",
        "hint": "Lưu/hiển thị mọi tin GNews & RSS tìm được, không gọi Gemini, không lọc tiêu đề.",
        "use_gemini": False,
        "ai_verify_target": False,
        "scan_role_change": False,
    },
    "activity": {
        "label": "AI — hoạt động & đúng đối tượng",
        "hint": "Gemini lọc hoạt động và xác nhận đúng tên; không quét truy vấn bổ nhiệm/miễn nhiệm.",
        "use_gemini": True,
        "ai_verify_target": True,
        "scan_role_change": False,
    },
    "full": {
        "label": "AI — đầy đủ (cả biến động chức vụ)",
        "hint": "Thêm lượt tìm bổ nhiệm/miễn nhiệm và kênh biến động; dễ lẫn tin người khác nếu tắt xác nhận đối tượng.",
        "use_gemini": True,
        "ai_verify_target": True,
        "scan_role_change": True,
    },
    "open": {
        "label": "AI — không lọc đối tượng (cũ)",
        "hint": "Gemini bật nhưng không bắt Matched_Target — dễ nhầm người. Nên chuyển sang «hoạt động & đúng đối tượng».",
        "use_gemini": True,
        "ai_verify_target": False,
        "scan_role_change": False,
    },
}

AI_SCAN_UI_MODES = ("keyword", "activity", "full")


def _gn_flags_snapshot(gn: Dict[str, Any]) -> Tuple[bool, bool, bool]:
    use_g = _gn_bool(gn.get("use_gemini_analysis", gn.get("use_ai", True)), True)
    verify = (
        _gn_bool(gn.get("ai_verify_target"), True)
        if "ai_verify_target" in gn
        else True
    )
    role = (
        _gn_bool(gn.get("scan_role_change"), True)
        if "scan_role_change" in gn
        else True
    )
    return use_g, verify, role


def detect_ai_scan_mode(cfg: Optional[Dict[str, Any]] = None) -> str:
    """Suy ra chế độ từ các cờ trong config (tương thích bản cũ)."""
    data = cfg if cfg is not None else load_config()
    gn = data.get("google_news") if isinstance(data.get("google_news"), dict) else {}
    use_g, verify, role = _gn_flags_snapshot(gn)
    if not use_g:
        return "keyword"
    if role:
        return "full"
    if verify:
        return "activity"
    return "open"


def apply_ai_scan_mode(gn: Dict[str, Any], mode: str) -> str:
    """Ghi đồng bộ 3 cờ AI theo một chế độ — tránh xung đột cài đặt."""
    key = str(mode or "activity").strip().lower()
    if key not in AI_SCAN_PROFILES:
        key = "activity"
    prof = AI_SCAN_PROFILES[key]
    gn["use_gemini_analysis"] = prof["use_gemini"]
    gn["use_ai"] = prof["use_gemini"]
    gn["ai_verify_target"] = prof["ai_verify_target"]
    gn["scan_role_change"] = prof["scan_role_change"]
    gn["ai_scan_mode"] = key
    return key


def _flags_match_profile(gn: Dict[str, Any], mode: str) -> bool:
    if mode not in AI_SCAN_PROFILES:
        return False
    prof = AI_SCAN_PROFILES[mode]
    use_g, verify, role = _gn_flags_snapshot(gn)
    return (
        use_g == prof["use_gemini"]
        and verify == prof["ai_verify_target"]
        and role == prof["scan_role_change"]
    )


def ensure_ai_scan_sync(gn: Dict[str, Any], cfg: Optional[Dict[str, Any]] = None) -> str:
    """
    Đồng bộ các cờ use_ai / verify / scan_role_change theo ai_scan_mode đã chọn.
    Không suy ngược từ cờ cũ — tránh đổi «từ khóa» thành «activity» khi quét.
    """
    mode = str(gn.get("ai_scan_mode") or "").strip().lower()
    if mode in AI_SCAN_PROFILES:
        if not _flags_match_profile(gn, mode):
            print(f"  [CONFIG] Đồng bộ cờ AI theo chế độ «{mode}»")
        return apply_ai_scan_mode(gn, mode)
    detected = detect_ai_scan_mode(
        cfg if cfg is not None else {"google_news": gn}
    )
    if detected not in AI_SCAN_PROFILES:
        detected = "activity"
    print(f"  [CONFIG] Chưa có ai_scan_mode hợp lệ — dùng «{detected}»")
    return apply_ai_scan_mode(gn, detected)


def resolve_ai_scan_options(cfg: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Một nguồn sự thật cho quét — luôn qua ensure_ai_scan_sync."""
    data = cfg if cfg is not None else load_config()
    gn = data.get("google_news") if isinstance(data.get("google_news"), dict) else {}
    if not isinstance(gn, dict):
        gn = {}
        data["google_news"] = gn
    mode = ensure_ai_scan_sync(gn, data)
    prof = AI_SCAN_PROFILES[mode]
    return {
        "mode": mode,
        "label": prof["label"],
        "hint": prof["hint"],
        "use_gemini": bool(prof["use_gemini"]),
        "ai_verify_target": bool(prof["ai_verify_target"]),
        "scan_role_change": bool(prof["scan_role_change"]),
    }


def set_and_persist_ai_scan_mode(mode: str) -> Dict[str, Any]:
    """
    Lưu chế độ quét do người dùng chọn — mọi lượt quét (thủ công + tự động) đọc từ đây.
    """
    key = str(mode or "activity").strip().lower()
    if key not in AI_SCAN_UI_MODES:
        key = "activity"
    cfg = load_config()
    gn = cfg.get("google_news") if isinstance(cfg.get("google_news"), dict) else {}
    if not isinstance(gn, dict):
        gn = {}
        cfg["google_news"] = gn
    apply_ai_scan_mode(gn, key)
    cfg["google_news"] = gn
    write_json(CONFIG_PATH, cfg)
    return resolve_ai_scan_options(cfg)


def build_keyword_only_ai_result(
    art: Dict[str, Any], target: Target, news_kind: str
) -> Dict[str, Any]:
    """Không gọi Gemini — chỉ lưu theo từ khóa tìm kiếm (không tự gán đổi chức vụ)."""
    title = str(art.get("title") or "").strip()
    desc = str(art.get("description") or "").strip()
    summary = title or desc[:200] or f"{target.name}: tin từ khóa quét"
    return {
        "Matched_Target": True,
        "Is_Activity": True,
        "Is_Change": False,
        "Summary": summary,
        "AI_Disabled": True,
        "Source": "keyword_scan",
    }


def _article_passes_ai_filters(
    ai_result: Dict[str, Any], *, verify_target: bool
) -> bool:
    if not ai_result.get("Is_Activity"):
        return False
    if verify_target and not ai_result.get("Matched_Target"):
        return False
    return True


def _target_name_appears(
    name: str, title: str, description: str, *, position: str = ""
) -> bool:
    """
    Tên có trong tiêu đề/mô tả — chỉ dùng hậu kiểm tin biến động chức vụ (sanitize).
    Bật AI: mọi bài đều qua Gemini. Tắt AI: lưu/hiển thị hết tin tìm được.
    """
    name = str(name or "").strip()
    if not name:
        return False
    blob = f"{title or ''} {description or ''}".lower()
    name_l = name.lower()
    if name_l in blob:
        if " " not in name and len(name_l) <= 4:
            return bool(re.search(rf"\b{re.escape(name_l)}\b", blob, re.IGNORECASE))
        return True
    parts = [p for p in name.split() if len(p) >= 2]
    if len(parts) >= 2:
        return all(p.lower() in blob for p in parts)
    return False


def _sanitize_ai_result(
    target: Target,
    article: Dict[str, Any],
    data: Dict[str, Any],
    *,
    news_kind: str,
    allow_role_change: bool = True,
) -> Dict[str, Any]:
    """Hậu kiểm Gemini — giảm nhầm đối tượng và nhầm hoạt động với đổi chức vụ."""
    title = str(article.get("title") or "")
    desc = str(article.get("description") or "")
    text = f"{title} {desc}"

    matched = bool(data.get("Matched_Target"))
    activity = bool(data.get("Is_Activity"))
    change = bool(data.get("Is_Change"))
    from_p = str(data.get("From_Position") or "").strip()
    to_p = str(data.get("To_Position") or "").strip()
    decision = str(data.get("Decision_Text") or "").strip()
    summary = str(data.get("Summary") or "")
    sl = summary.lower()
    notes: List[str] = []

    if matched and str(news_kind) == "biendong" and not _target_name_appears(
        target.name, title, desc
    ):
        matched = False
        activity = False
        change = False
        notes.append("biendong_ten_phai_co_trong_tieu_de")

    if "không liên quan đối tượng" in sl:
        matched = False
        activity = False
        change = False
        notes.append("summary_khong_lien_quan")
    elif "không liên quan hoạt động" in sl:
        activity = False
        change = False
        notes.append("summary_khong_hoat_dong")
    elif "không thay đổi chức vụ" in sl:
        change = False
        notes.append("summary_khong_doi_chuc")

    if matched and activity and change:
        has_fields = bool(from_p or to_p or decision)
        has_role_kw = bool(_ROLE_CHANGE_STRONG.search(text))
        has_routine = bool(_ACTIVITY_ROUTINE.search(text))
        if not has_fields and not has_role_kw:
            change = False
            notes.append("khong_co_truong_chuc_vu_va_tu_khoa")
        elif has_routine and not has_role_kw and not has_fields:
            change = False
            notes.append("hoat_dong_thuong_nhat")
        elif str(news_kind) == "hoatdong" and not has_fields:
            change = False
            notes.append("hoatdong_can_chung_cu_doi_chuc")

    try:
        conf = int(float(data.get("Confidence", 0)))
    except Exception:
        conf = 0
    if change and conf < 55 and not (from_p or to_p):
        change = False
        notes.append("do_tin_cay_thap")

    if not matched:
        activity = False
    if not activity:
        change = False
    if not allow_role_change:
        change = False
        if "tat_quet_bien_dong_chuc_vu" not in notes:
            notes.append("tat_quet_bien_dong_chuc_vu")

    out = dict(data)
    out["Matched_Target"] = matched
    out["Is_Activity"] = activity
    out["Is_Change"] = change
    if notes:
        out["Sanitize_Notes"] = notes
    return out


def chinh_thong_whitelist() -> PressWhitelist:
    return PressWhitelist.from_file(path_str(CHINH_THONG_PATH))


def record_is_chinh_thong(
    row: Dict[str, Any], whitelist: Optional[PressWhitelist] = None
) -> bool:
    """Tin thuộc báo trong danh sách chính thống (theo URL hoặc domain đã lưu)."""
    wl = whitelist if whitelist is not None else chinh_thong_whitelist()
    if not wl.domains:
        return False
    link = article_link_url(row)
    if link and wl.is_allowed_url(link):
        return True
    dom = str(row.get("press_domain") or "").strip()
    if dom and wl.is_allowed_url(f"https://{dom}/"):
        return True
    press = str(row.get("press_name") or "").strip()
    if press and press in wl.domain_to_name.values():
        return True
    return False


def record_matches_ai_display_mode(
    row: Dict[str, Any], ai_opts: Dict[str, Any]
) -> bool:
    """Lọc tin đã lưu theo chế độ AI hiện tại (đổi chế độ → đổi danh sách hiển thị)."""
    mode = str(ai_opts.get("mode") or "activity")
    if mode == "keyword" or not ai_opts.get("use_gemini"):
        return True
    ai = row.get("ai_result") if isinstance(row.get("ai_result"), dict) else {}
    if ai.get("AI_Disabled") or ai.get("Source") == "keyword_scan":
        return False
    return _article_passes_ai_filters(
        ai, verify_target=bool(ai_opts.get("ai_verify_target"))
    )


def filter_notifications_for_display(
    notifs: Dict[str, List[Dict[str, Any]]],
    cfg: Optional[Dict[str, Any]] = None,
) -> Dict[str, List[Dict[str, Any]]]:
    """Lọc theo báo chính thống + chế độ AI đang chọn."""
    data = cfg if cfg is not None else load_config()
    ai_opts = resolve_ai_scan_options(data)
    out: Dict[str, List[Dict[str, Any]]] = {
        "channel_hoatdong": list(notifs.get("channel_hoatdong") or []),
        "channel_biendong": list(notifs.get("channel_biendong") or []),
    }
    if not ai_opts.get("scan_role_change"):
        out["channel_biendong"] = []
    for ch in ("channel_hoatdong", "channel_biendong"):
        out[ch] = [
            r
            for r in out.get(ch) or []
            if isinstance(r, dict) and record_matches_ai_display_mode(r, ai_opts)
        ]
    if not is_chinh_thong_filter_enabled(cfg):
        return out
    wl = chinh_thong_whitelist()
    if not wl.domains:
        for ch in ("channel_hoatdong", "channel_biendong"):
            out[ch] = []
        return out
    for ch in ("channel_hoatdong", "channel_biendong"):
        rows = out.get(ch) or []
        out[ch] = [
            r for r in rows if isinstance(r, dict) and record_is_chinh_thong(r, wl)
        ]
    return out


def _remove_notification_by_key(
    notifs: Dict[str, List[Dict[str, Any]]], history_key: str
) -> None:
    for ch in ("channel_hoatdong", "channel_biendong"):
        rows = notifs.get(ch) or []
        if not isinstance(rows, list):
            continue
        notifs[ch] = [
            r
            for r in rows
            if not (
                isinstance(r, dict)
                and _history_key(
                    str(r.get("target_name") or ""),
                    str(r.get("url") or ""),
                )
                == history_key
            )
        ]


def enrich_record_for_api(row: Dict[str, Any]) -> Dict[str, Any]:
    out = dict(row)
    out["article_url"] = article_link_url(row)
    return out


def _history_key(target_name: str, url: str) -> str:
    return f"{str(target_name or '').strip()}|{str(url or '').strip()}"


def _notification_keys(notifs: Dict[str, List[Dict[str, Any]]]) -> Set[str]:
    """Khóa các bài đã lưu trong notifications — tránh trùng khi quét lại."""
    keys: Set[str] = set()
    for ch in ("channel_hoatdong", "channel_biendong"):
        for row in notifs.get(ch) or []:
            if isinstance(row, dict):
                k = _history_key(
                    str(row.get("target_name") or ""),
                    str(row.get("url") or ""),
                )
                if k.strip("|"):
                    keys.add(k)
    return keys


def load_history() -> List[str]:
    data = read_json(HISTORY_PATH, default=[])
    if not isinstance(data, list):
        return []
    out: List[str] = []
    for item in data:
        if isinstance(item, str) and item.strip():
            out.append(item.strip())
        elif isinstance(item, (list, tuple)) and len(item) >= 2:
            out.append(_history_key(str(item[0]), str(item[1])))
    return out


def save_history(history_urls: List[str]) -> None:
    write_json(HISTORY_PATH, history_urls)


def update_target_identity(old_name: str, new_name: str, position: str) -> None:
    """Đổi tên/chức vụ đối tượng trong notifications và history."""
    old = str(old_name or "").strip()
    new = str(new_name or "").strip()
    pos = str(position or "").strip()
    if not old or not new:
        return

    notifs = load_notifications()
    for channel in ("channel_hoatdong", "channel_biendong"):
        rows = notifs.get(channel) or []
        if not isinstance(rows, list):
            continue
        for row in rows:
            if not isinstance(row, dict):
                continue
            if str(row.get("target_name", "")).strip() != old:
                continue
            row["target_name"] = new
            row["target_position"] = pos
    save_notifications(notifs)

    if old != new:
        history = load_history()
        prefix_old = old + "|"
        updated: List[str] = []
        for key in history:
            if isinstance(key, str) and key.startswith(prefix_old):
                updated.append(new + key[len(old) :])
            else:
                updated.append(key)
        save_history(updated)


def load_notifications() -> Dict[str, List[Dict[str, Any]]]:
    data = read_json(
        NOTIFICATIONS_PATH,
        default={"channel_biendong": [], "channel_hoatdong": []},
    )
    if not isinstance(data, dict):
        data = {}
    data.setdefault("channel_biendong", [])
    data.setdefault("channel_hoatdong", [])
    if not isinstance(data["channel_biendong"], list):
        data["channel_biendong"] = []
    if not isinstance(data["channel_hoatdong"], list):
        data["channel_hoatdong"] = []
    return data


def save_notifications(notifs: Dict[str, List[Dict[str, Any]]]) -> None:
    write_json(NOTIFICATIONS_PATH, notifs)


def _google_news_search_feedparser(gnews: GNews, query: str) -> List[Dict[str, Any]]:
    """
    GNews gốc dùng feed_data.status — feedparser 6.x đôi khi không có .status
    (Google trả HTML lỗi) → AttributeError. Parse an toàn tại đây.
    """
    import feedparser
    from gnews.utils.constants import BASE_URL, USER_AGENT

    key = "%20".join(str(query or "").split(" "))
    path = f"/search?q={key}"
    url = BASE_URL + path + gnews._ceid()
    feed_data = feedparser.parse(url, agent=USER_AGENT)
    status = getattr(feed_data, "status", None)
    if status == 429:
        raise RuntimeError("GNews rate limit (429)")
    entries = list(getattr(feed_data, "entries", None) or [])
    out: List[Dict[str, Any]] = []
    for entry in entries[: max(1, int(gnews.max_results))]:
        item = gnews._process(entry)
        if isinstance(item, dict):
            out.append(item)
    return out


def _google_news_search_single(
    query: str, language: str, country: str, max_results: int
) -> List[Dict[str, Any]]:
    gnews = GNews(
        language=language, country=country, period="1d", max_results=max_results
    )
    try:
        out = gnews.get_news(query)
        return out if isinstance(out, list) else []
    except Exception as exc:
        msg = str(exc).lower()
        if "status" in msg or "failed to fetch or parse" in msg:
            return _google_news_search_feedparser(gnews, query)
        raise


def _google_news_search_by_domains(
    query_text: str,
    domains: List[str],
    *,
    language: str,
    country: str,
    max_results: int,
) -> List[Dict[str, Any]]:
    """Mỗi báo một truy vấn site: — tránh URL OR dài gây lỗi feedparser/GNews."""
    base = str(query_text or "").strip()
    doms = sorted({str(d).strip() for d in domains if str(d).strip()})
    if not base or not doms:
        return []

    per = max(3, (max_results + len(doms) - 1) // len(doms))
    merged: List[Dict[str, Any]] = []
    seen: Set[str] = set()
    term = _quote_gnews_term(base)

    for dom in doms:
        q = f"{term} site:{dom}"
        try:
            batch = _google_news_search_single(q, language, country, per)
        except Exception as exc:
            print(f"  [WARN] GNews site:{dom}: {exc}")
            continue
        for art in batch:
            if not isinstance(art, dict):
                continue
            u = str(art.get("url") or "").strip()
            if u and u not in seen:
                seen.add(u)
                merged.append(art)
        if len(merged) >= max_results:
            break
    return merged[:max_results]


def google_news_search(
    query: str,
    language: str,
    country: str,
    max_results: int,
    *,
    whitelist_domains: Optional[List[str]] = None,
) -> List[Dict[str, Any]]:
    if whitelist_domains:
        return _google_news_search_by_domains(
            query,
            list(whitelist_domains),
            language=language,
            country=country,
            max_results=max_results,
        )
    return _google_news_search_single(query, language, country, max_results)


def clean_json_text(text: str) -> str:
    text = text.strip()
    text = re.sub(r"^```json\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"^```\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"```$", "", text)
    return text.strip()


def call_gemini_for_change(
    gemini_api_key: str,
    target: Target,
    article: Dict[str, Any],
    *,
    news_kind: str = "hoatdong",
    allow_role_change: bool = True,
) -> Dict[str, Any]:
    genai.configure(api_key=gemini_api_key)

    title = article.get("title", "")
    description = article.get("description", "") or ""
    url = article.get("url", "")

    position_ref = target.position.strip() if isinstance(target.position, str) else ""
    position_or_default = position_ref or "chức vụ"
    kind = str(news_kind or "hoatdong").strip()
    kind_hint = (
        "Bài tìm qua truy vấn BIẾN ĐỘNG CHỨC VỤ — vẫn phải xác nhận đúng {name}; "
        "nếu bổ nhiệm/miễn nhiệm áp dụng cho người khác thì Matched_Target=false."
        if kind == "biendong"
        else "Bài tìm qua truy vấn HOẠT ĐỘNG — Is_Change=true rất hiếm; "
        "họp, thăm, phát biểu, làm việc KHÔNG phải đổi chức vụ."
    )

    prompt = (
        "Bạn là hệ thống phân tích tin tức. "

        "Hãy đọc bài báo sau và chỉ xét đúng đối tượng: {name} (không suy rộng sang người khác). "
        "Nếu bài KHÔNG nói về hoạt động/việc làm của đối tượng đó, hãy loại bài đó.\n\n"
        "Ngữ cảnh truy vấn: {kind_hint}\n\n"
        "QUY TẮC Matched_Target (rất quan trọng):\n"
        "- Matched_Target=true CHỈ KHI bài nói TRỰC TIẾP về {name} — là nhân vật chính, người hành động, hoặc người được bổ nhiệm/miễn nhiệm.\n"
        "- Matched_Target=false nếu chỉ nhắc tên qua loa, nhắc trong danh sách nhiều người, "
        "hay nhầm người khác cùng họ hoặc tên gần giống.\n"
        "- Việc bài có từ khóa bổ nhiệm/miễn nhiệm nhưng đối tượng là NGƯỜI KHÁC => Matched_Target=false.\n"
        "- Tiêu đề/mô tả có thể chỉ ghi chức danh (vd. Tổng Bí thư) không ghi đủ họ tên — "
        "vẫn Matched_Target=true nếu ngữ cảnh rõ là {name} (chức vụ tham chiếu: {position_ref}) "
        "và không thể hiểu là người khác.\n"
        "- Matched_Target=false nếu không đủ căn cứ xác định là {name} (bài chung chung nhiều lãnh đạo).\n\n"
        "QUY TẮC Is_Activity:\n"
        "- Is_Activity=true khi bài nói việc {name} đang làm (họp, thăm, chủ trì, phát biểu…).\n"
        "- Không nhầm bài chủ yếu về người/cơ quan khác.\n\n"
        "QUY TẮC Is_Change:\n"
        "- Is_Change=true CHỈ KHI có thông tin RÕ về thay đổi chức vụ/việc làm của đúng {name} "
        "(bổ nhiệm, miễn nhiệm, điều động, bổ nhiệm giữ chức, quyết định giao nhiệm vụ mới…).\n"
        "- Không coi họp, phát biểu, thăm hỏi, hoạt động thường nhật là đổi chức vụ.\n"
        "- Bắt buộc điền From_Position hoặc To_Position hoặc Decision_Text nếu Is_Change=true; "
        "thiếu cả ba => Is_Change=false.\n\n"
        "Đối tượng: {name}. Chức vụ tham chiếu: {position_ref}.\n\n"
        "Bài báo:\n"
        "- Tiêu đề: {title}\n"
        "- Mô tả: {description}\n"
        "- URL: {url}\n\n"
        "Trả về ĐÚNG một JSON (bắt buộc có đủ các khóa) với:\n"
        "Matched_Target (true/false) - bài có nói đúng đối tượng {name} không?\n"
        "Is_Activity (true/false) - (chỉ tính nếu Matched_Target=true) bài có nói về hoạt động/việc làm của đối tượng không?\n"
        "Is_Change (true/false) - (chỉ tính nếu Is_Activity=true) bài có nói về thay đổi chức vụ của đối tượng không?\n"
        "Change_Date (string ISO hoặc 'DD/MM/YYYY'; nếu không có thì để rỗng chuỗi '')\n"
        "From_Position (string; nếu không trích được thì để rỗng chuỗi '')\n"
        "To_Position (string; nếu không trích được thì để rỗng chuỗi '')\n"
        "Decision_Text (string; nếu có nêu quyết định/quyết định số thì trích, nếu không thì để rỗng chuỗi '')\n"
        "Summary (bắt buộc đúng luật)\n"
        "Confidence (0-100 số)\n"
        "Không thêm văn bản ngoài JSON.\n\n"
        "Luật Summary (BẮT BUỘC):\n"
        "- Nếu Matched_Target = false => Summary = 'Không liên quan đối tượng'\n"
        "- Nếu Matched_Target = true nhưng Is_Activity = false => Summary = 'Không liên quan hoạt động'\n"
        "- Nếu Is_Activity = true và Is_Change = false => Summary đúng 1 câu: '{name}: không thay đổi chức vụ, {position_or_default}.'\n"
        "- Nếu Is_Activity = true và Is_Change = true => Summary đúng 1 câu: '{name}: [DATE], chuyển từ [FROM] sang [TO] theo quyết định [DECISION]'\n"
        "Trong nhánh Is_Change=true: nếu KHÔNG trích chắc chắn được date/decision/from/to thì bắt buộc chuyển sang Is_Change=false (tức câu không đổi chức vụ).\n"
        "Chỉ viết đúng 1 câu Summary, không liệt kê nhiều câu."
    ).format(
        name=target.name,
        position_ref=position_ref,
        position_or_default=position_or_default,
        kind_hint=kind_hint.format(name=target.name),
        title=title,
        description=description,
        url=url,
    )

    cfg = load_config()
    from_cfg = str(cfg.get("gemini_model") or "").strip()
    preferred = str(os.environ.get("GEMINI_MODEL", "")).strip() or from_cfg
    candidate_models = [preferred, "gemini-2.5-flash", "gemini-1.5-flash"]

    resp = None
    tried: List[str] = []
    last_err: Optional[Exception] = None

    for m in candidate_models:
        if not m or m in tried:
            continue
        tried.append(m)
        try:
            model = genai.GenerativeModel(m)
            resp = model.generate_content(prompt)
            break
        except Exception as e:
            last_err = e
            msg = str(e).lower()
            if "429" in msg or "quota" in msg:
                return {
                    "Is_Activity": False,
                    "Is_Change": False,
                    "Matched_Target": False,
                    "Summary": "Bị giới hạn quota Gemini (429).",
                    "Confidence": 0,
                    "Gemini_Error": str(e),
                    "Gemini_Tries": tried,
                    "Should_Retry": True,
                }
            if "403" in msg or "leaked" in msg or "permission" in msg:
                return {
                    "Is_Activity": False,
                    "Is_Change": False,
                    "Matched_Target": False,
                    "Summary": "Gemini API key không hợp lệ hoặc đã bị vô hiệu.",
                    "Confidence": 0,
                    "Gemini_Error": str(e),
                    "Gemini_Tries": tried,
                    "Should_Retry": False,
                }
            continue

    if resp is None:
        raise RuntimeError(
            "Gemini model generation failed. Tried: "
            + ", ".join(tried)
            + (". Last error: " + str(last_err) if last_err else "")
        )

    raw = getattr(resp, "text", None) or str(resp)
    raw = clean_json_text(raw)

    try:
        data = json.loads(raw)
    except Exception as e:
        return {
            "Is_Activity": False,
            "Is_Change": False,
            "Matched_Target": False,
            "Summary": "Không parse được JSON từ Gemini.",
            "Confidence": 0,
            "Gemini_Error": f"json.loads failed: {e}",
            "Gemini_Raw": raw[:2000],
            "Should_Retry": False,
        }

    matched_target = data.get("Matched_Target")
    if isinstance(matched_target, str):
        matched_target = matched_target.strip().lower() in ("true", "yes", "1", "t")

    is_activity = data.get("Is_Activity")
    if isinstance(is_activity, str):
        is_activity = is_activity.strip().lower() in ("true", "yes", "1", "t")

    is_change = data.get("Is_Change")
    if isinstance(is_change, str):
        is_change = is_change.strip().lower() in ("true", "yes", "1", "t")

    if not bool(matched_target):
        is_activity = False
        is_change = False
    if bool(matched_target) and not bool(is_activity):
        is_change = False

    conf = data.get("Confidence")
    try:
        conf = int(float(conf))
    except Exception:
        conf = 0

    summary = str(data.get("Summary", ""))[:500]

    parsed: Dict[str, Any] = {
        "Is_Activity": bool(is_activity),
        "Is_Change": bool(is_change) and bool(is_activity),
        "Matched_Target": bool(matched_target),
        "Summary": summary,
        "Confidence": max(0, min(100, conf)),
        "Target_Name": target.name,
        "From_Position": str(data.get("From_Position") or "")[:300],
        "To_Position": str(data.get("To_Position") or "")[:300],
        "Decision_Text": str(data.get("Decision_Text") or "")[:500],
        "Change_Date": str(data.get("Change_Date") or "")[:80],
        "News_Kind": kind,
    }
    return _sanitize_ai_result(
        target, article, parsed, news_kind=kind, allow_role_change=allow_role_change
    )


def is_confirmed_role_change(ai_result: Dict[str, Any]) -> bool:
    """Đủ điều kiện đưa vào kênh biến động chức vụ."""
    if not ai_result.get("Is_Change"):
        return False
    if not ai_result.get("Matched_Target"):
        return False
    from_p = str(ai_result.get("From_Position") or "").strip()
    to_p = str(ai_result.get("To_Position") or "").strip()
    decision = str(ai_result.get("Decision_Text") or "").strip()
    return bool(from_p or to_p or decision)


def _collect_articles_for_target(
    target: Target,
    *,
    language: str,
    country: str,
    max_results: int,
    whitelist: Optional[PressWhitelist] = None,
    use_rss: bool = True,
    rss_max_per_feed: int = 40,
    scan_role_change: bool = True,
    filter_press: bool = False,
) -> List[Tuple[Dict[str, Any], str]]:
    """GNews + RSS; trùng URL ưu tiên biendong (bỏ hoatdong trùng)."""
    pairs: List[Tuple[Dict[str, Any], str]] = []

    q_hd = str(target.name).strip()
    q_bd = f"{target.name} {ROLE_QUERY_SUFFIX}".strip()

    scan_kinds: List[Tuple[str, str]] = [(q_hd, "hoatdong")]
    if scan_role_change:
        scan_kinds = [(q_bd, "biendong"), (q_hd, "hoatdong")]

    press_domains: Optional[List[str]] = None
    if filter_press and whitelist is not None and whitelist.domains:
        press_domains = sorted(whitelist.domains)

    for query, kind in scan_kinds:
        if press_domains:
            print(
                f"[SCAN] target={target.name} kind={kind} "
                f"GNews ({len(press_domains)} báo chính thống): {query[:80]}..."
            )
        else:
            print(f"[SCAN] target={target.name} kind={kind} query={query[:100]}...")
        try:
            batch = google_news_search(
                query,
                language=language,
                country=country,
                max_results=max_results,
                whitelist_domains=press_domains,
            )
        except Exception as exc:
            print(f"  [ERR] GNews: {exc}")
            continue
        for art in batch:
            if isinstance(art, dict):
                pairs.append((art, kind))

    if use_rss and whitelist is not None:
        print(f"[RSS] target={target.name} — quét feed báo chính thống...")
        rss_pairs = collect_rss_for_target(
            whitelist,
            target.name,
            max_per_feed=rss_max_per_feed,
            role_query_suffix=ROLE_QUERY_SUFFIX if scan_role_change else "",
        )
        if rss_pairs:
            print(f"  [RSS] {len(rss_pairs)} bài khớp tên")
        pairs.extend(rss_pairs)

    merged = _merge_article_pairs(pairs)
    skipped_hd = len(pairs) - len(merged)
    if skipped_hd > 0:
        print(f"  [DEDUP] bỏ {skipped_hd} bài trùng (ưu tiên biến động chức vụ)")
    return merged


def _apply_decode_and_whitelist(
    articles: List[Tuple[Dict[str, Any], str]],
    *,
    target_name: str,
    history_set: Set[str],
    saved_keys: Set[str],
    whitelist: PressWhitelist,
    filter_press: bool,
    use_ai: bool = True,
    decode_workers: int = 4,
    decode_interval: float = 0.15,
    ignore_saved: bool = False,
) -> Tuple[List[Tuple[Dict[str, Any], str]], int, int]:
    """Lọc history trước decode; chỉ decode URL Google News còn lại."""
    pending: List[Tuple[Dict[str, Any], str]] = []
    skipped_history = 0

    for art, kind in articles:
        url = str(art.get("url") or "").strip()
        key = _history_key(target_name, url)
        if not ignore_saved and key in saved_keys:
            skipped_history += 1
            continue
        if use_ai and key in history_set:
            skipped_history += 1
            continue
        pending.append((art, kind))

    urls_to_decode = list(
        {
            str(a.get("url") or "").strip()
            for a, _ in pending
            if is_google_news_url(str(a.get("url") or ""))
        }
    )
    decoded = decode_batch(
        urls_to_decode, workers=decode_workers, interval=decode_interval
    )

    kept: List[Tuple[Dict[str, Any], str]] = []
    skipped_whitelist = 0
    skipped_no_resolve = 0
    rejected_domains: Dict[str, int] = {}
    for art, kind in pending:
        url = str(art.get("url") or "").strip()
        pre_resolved = str(art.get("resolved_url") or "").strip()
        if pre_resolved.startswith("http"):
            resolved = pre_resolved
        else:
            resolved = decoded.get(url) or (url if not is_google_news_url(url) else "")
        pub_href = _gnews_publisher_href(art)
        if filter_press and not resolved and pub_href.startswith("http"):
            if whitelist.is_allowed_url(pub_href):
                resolved = pub_href
        if filter_press and not resolved:
            skipped_no_resolve += 1
            continue
        if filter_press and resolved and not whitelist.is_allowed_url(resolved):
            if pub_href.startswith("http") and whitelist.is_allowed_url(pub_href):
                resolved = pub_href
            else:
                skipped_whitelist += 1
                try:
                    dom = _norm_domain(urlparse(resolved).netloc)
                    if dom:
                        rejected_domains[dom] = rejected_domains.get(dom, 0) + 1
                except Exception:
                    pass
                continue
        art = dict(art)
        if resolved:
            art["resolved_url"] = resolved
            meta = whitelist.press_for_url(resolved)
            if meta.get("press_name") and not art.get("press_name"):
                art["press_name"] = meta["press_name"]
            if meta.get("press_domain") and not art.get("press_domain"):
                art["press_domain"] = meta["press_domain"]
        kept.append((art, kind))
    if skipped_whitelist:
        print(f"  [FILTER] bỏ {skipped_whitelist} bài ngoài danh sách báo chính thống")
        if rejected_domains:
            top = sorted(rejected_domains.items(), key=lambda x: -x[1])[:4]
            sample = ", ".join(f"{d}({n})" for d, n in top)
            print(
                f"  [FILTER] Nguồn bị loại (mẫu): {sample} — "
                "thêm báo vào Cài đặt hoặc tắt «Chỉ báo chính thống»"
            )
    if skipped_no_resolve:
        print(f"  [FILTER] bỏ {skipped_no_resolve} bài chưa decode được link báo")
    return kept, skipped_history, skipped_whitelist


def _process_gemini_batch(
    gemini_key: str,
    target: Target,
    pending: List[Tuple[Dict[str, Any], str]],
    *,
    gemini_workers: int,
    allow_role_change: bool = True,
) -> Tuple[List[Tuple[Dict[str, Any], str, Dict[str, Any]]], List[str]]:
    """Gọi Gemini song song; trả (kết quả, danh sách lỗi)."""
    if not pending:
        return [], []

    w = max(1, min(int(gemini_workers), 6))
    out: List[Tuple[Dict[str, Any], str, Dict[str, Any]]] = []
    errors: List[str] = []

    def _one(item: Tuple[Dict[str, Any], str]) -> Tuple[Dict[str, Any], str, Dict[str, Any]]:
        art, kind = item
        ai = call_gemini_for_change(
            gemini_key,
            target,
            art,
            news_kind=kind,
            allow_role_change=allow_role_change,
        )
        return art, kind, ai

    if w <= 1 or len(pending) == 1:
        for item in pending:
            try:
                out.append(_one(item))
            except Exception as exc:
                msg = str(exc)
                print(f"  [AI] worker error: {msg}")
                errors.append(msg)
        return out, errors

    with ThreadPoolExecutor(max_workers=w) as pool:
        futures = [pool.submit(_one, item) for item in pending]
        for fut in as_completed(futures):
            try:
                out.append(fut.result())
            except Exception as exc:
                msg = str(exc)
                print(f"  [AI] worker error: {msg}")
                errors.append(msg)
    return out, errors


def process_once(
    *,
    scan_hours: Optional[float] = None,
    target_name: Optional[str] = None,
    ignore_history: bool = False,
) -> Dict[str, Any]:
    """Mỗi lượt quét đọc lại config.json — chế độ AI theo ai_scan_mode người dùng đã chọn."""
    cfg = load_config()
    gn = cfg.get("google_news") if isinstance(cfg.get("google_news"), dict) else {}
    if not isinstance(gn, dict):
        gn = {}
        cfg["google_news"] = gn
    ensure_ai_scan_sync(gn, cfg)

    history = load_history()
    history_set = set(history)
    notifs = load_notifications()
    saved_keys = _notification_keys(notifs)

    ai_opts = resolve_ai_scan_options(cfg)
    use_gemini = ai_opts["use_gemini"]
    verify_target = ai_opts["ai_verify_target"]
    scan_role_change = ai_opts["scan_role_change"]
    ai_mode = ai_opts["mode"]
    gemini_key = str(cfg.get("gemini_api_key") or "").strip()
    if use_gemini and not gemini_key:
        raise ValueError("Thiếu gemini_api_key trong config.json")
    if not use_gemini:
        print(
            "[SCAN] Tắt phân tích Gemini — hiển thị/lưu mọi tin Google News & RSS trả về "
            "(không lọc tên trong tiêu đề)"
        )
    elif ai_mode == "open":
        print(
            "[SCAN] Cảnh báo: chế độ AI không lọc đối tượng — "
            "nên chọn «hoạt động & đúng đối tượng» trong Cài đặt"
        )
    print(f"[SCAN] Chế độ AI: {ai_opts['label']} ({ai_mode})")
    if ignore_history:
        print(
            "  → Quét thủ công: bỏ qua history (xử lý lại URL đã thấy — tránh +0 tin vì history đầy)"
        )
    if not scan_role_change and use_gemini:
        print("  → Không quét truy vấn bổ nhiệm/miễn nhiệm, không lưu kênh biendong")

    language = str(gn.get("language") or "vi")
    country = str(gn.get("country") or "VN")
    max_results = int(gn.get("max_results_per_target") or 15)

    targets: List[Target] = []
    for t in cfg.get("targets") or []:
        if not isinstance(t, dict):
            continue
        name = str(t.get("name", "")).strip()
        if name:
            targets.append(Target(name=name, position=str(t.get("position", ""))))

    filter_name = str(target_name or "").strip()
    if filter_name:
        targets = [t for t in targets if t.name == filter_name]
        if not targets:
            raise ValueError(f'Không tìm thấy đối tượng "{filter_name}" trong cấu hình')

    perf = _scan_perf_options(gn)
    filter_press = is_chinh_thong_filter_enabled(cfg)
    whitelist = chinh_thong_whitelist()
    if filter_press and not whitelist.domains:
        print(
            "[SCAN] Cảnh báo: Bật «Chỉ báo chính thống» nhưng danh sách báo trống — "
            "hãy thêm báo trong Cài đặt hệ thống. Bỏ qua lọc domain lần quét này."
        )
        filter_press = False
    use_rss_scan = perf["use_rss"] and filter_press
    if perf["use_rss"] and not use_rss_scan and not is_chinh_thong_filter_enabled(cfg):
        print("[SCAN] Tắt lọc báo chính thống — bỏ qua RSS danh sách chính thống")

    now_iso = datetime.now().isoformat(timespec="seconds")
    scan_results: List[Dict[str, Any]] = []
    saved_count = 0
    new_records: List[Dict[str, Any]] = []
    skipped_history_dup = 0
    skipped_pre_decode = 0
    skipped_whitelist_total = 0
    ai_errors: List[str] = []

    for ti, target in enumerate(targets, start=1):
        print(f"[SCAN] ({ti}/{len(targets)}) {target.name}")
        sys.stdout.flush()
        raw_pairs = _collect_articles_for_target(
            target,
            language=language,
            country=country,
            max_results=max_results,
            whitelist=whitelist,
            use_rss=use_rss_scan,
            rss_max_per_feed=perf["rss_max_per_feed"],
            scan_role_change=scan_role_change,
            filter_press=filter_press,
        )
        pairs, skipped_hist, skipped_wl = _apply_decode_and_whitelist(
            raw_pairs,
            target_name=target.name,
            history_set=history_set,
            saved_keys=saved_keys,
            whitelist=whitelist,
            filter_press=filter_press,
            use_ai=use_gemini and not ignore_history,
            decode_workers=perf["decode_workers"],
            decode_interval=perf["decode_interval"],
            ignore_saved=ignore_history,
        )
        skipped_history_dup += skipped_hist
        skipped_pre_decode += skipped_hist
        skipped_whitelist_total += skipped_wl
        pairs = _merge_article_pairs(pairs)

        if not pairs:
            if raw_pairs:
                print(
                    f"  [SCAN] {target.name}: {len(raw_pairs)} bài thô, "
                    f"0 bài sau lọc (history {skipped_hist}, chính thống {skipped_wl})"
                )
            continue

        for art, news_kind in pairs:
            url = str(art.get("url") or "").strip()
            print(f"  [ARTICLE] {target.name} [{news_kind}] {url[:72]}...")

        if use_gemini:
            to_analyze = list(pairs)
            if to_analyze:
                print(f"  [AI] Gửi {len(to_analyze)} bài cho Gemini (không lọc trước theo tiêu đề)")
            analyzed, batch_errors = _process_gemini_batch(
                gemini_key,
                target,
                to_analyze,
                gemini_workers=perf["gemini_workers"],
                allow_role_change=scan_role_change,
            )
            ai_errors.extend(batch_errors)
        else:
            analyzed = [
                (art, kind, build_keyword_only_ai_result(art, target, kind))
                for art, kind in pairs
            ]
            if analyzed:
                print(f"  [SCAN] Lưu {len(analyzed)} tin (không AI, không lọc tiêu đề)")
            batch_errors = []

        for art, news_kind, ai_result in analyzed:
            url = str(art.get("url") or "").strip()
            history_key = _history_key(target.name, url)
            notes = ai_result.get("Sanitize_Notes")
            if notes:
                print(f"  [AI] {target.name} sanitize={notes}")
            print(
                f"  [AI] {target.name} matched={ai_result.get('Matched_Target')} "
                f"activity={ai_result.get('Is_Activity')} change={ai_result.get('Is_Change')} "
                f"kind={news_kind} verify_target={verify_target}"
            )

            if not _article_passes_ai_filters(ai_result, verify_target=verify_target):
                scan_results.append({"url": url, "skipped": True, "ai_result": ai_result})
                continue

            record = {
                "timestamp": now_iso,
                "target_name": target.name,
                "target_position": target.position,
                "title": art.get("title", ""),
                "description": art.get("description", "") or "",
                "url": url,
                "published": art.get("published date")
                or art.get("published_at")
                or art.get("publishedAt")
                or art.get("date"),
                "news_kind": news_kind,
                "resolved_url": art.get("resolved_url", ""),
                "press_name": art.get("press_name", ""),
                "press_domain": art.get("press_domain", ""),
                "ai_result": ai_result,
            }

            _remove_notification_by_key(notifs, history_key)
            notifs["channel_hoatdong"].append(dict(record))
            if (
                scan_role_change
                and use_gemini
                and is_confirmed_role_change(ai_result)
            ):
                notifs["channel_biendong"].append(dict(record))

            scan_results.append(record)
            saved_count += 1
            new_records.append(record)
            history_set.add(history_key)
            saved_keys.add(history_key)

    save_notifications(notifs)
    save_history(list(history_set))

    report_hours = resolve_activity_report_hours(
        float(scan_hours) if scan_hours is not None else 24.0, gn
    )
    target_names = [t.name for t in targets]
    tg_result = notify_records(
        cfg,
        new_records,
        notifs=notifs,
        hours=report_hours,
        all_targets=target_names,
        scan_id=now_iso,
    )
    tg_enabled = is_telegram_enabled(cfg)

    if tg_enabled and saved_count and tg_result.get("sent", 0) == 0:
        print(
            f"  [TELEGRAM] 0 tin gửi / {saved_count} tin mới "
            f"(bỏ qua trùng TG: {tg_result.get('skipped_dup', 0)}, "
            f"lọc: {tg_result.get('skipped_filter', 0)})"
        )
    elif tg_result.get("sent", 0):
        print(f"  [TELEGRAM] đã gửi {tg_result.get('sent')} tin")

    if ai_errors:
        print(f"  [AI] tổng {len(ai_errors)} lỗi trong lượt quét này")

    print(
        f"[SCAN] Hoàn tất — {len(targets)} đối tượng, +{saved_count} tin mới, "
        f"{len(history_set)} URL trong history"
    )
    sys.stdout.flush()

    return {
        "success": True,
        "processed_new": saved_count,
        "processed": scan_results,
        "history_size": len(history_set),
        "skipped_history_dup": skipped_history_dup,
        "skipped_pre_decode": skipped_pre_decode,
        "skipped_whitelist": skipped_whitelist_total,
        "scan_use_rss": use_rss_scan,
        "scan_filter_chinh_thong": filter_press,
        "scan_use_ai": use_gemini,
        "scan_ai_verify_target": verify_target,
        "scan_role_change": scan_role_change,
        "scan_ai_mode": ai_mode,
        "scan_ai_mode_label": ai_opts["label"],
        "timestamp": now_iso,
        "scanned_target": filter_name or None,
        "scanned_targets": [t.name for t in targets],
        "ai_errors": ai_errors,
        "ai_error_count": len(ai_errors),
        "telegram_enabled": tg_enabled,
        "telegram_sent": tg_result.get("sent", 0),
        "telegram_skipped_dup": tg_result.get("skipped_dup", 0),
        "telegram_skipped_filter": tg_result.get("skipped_filter", 0),
        "telegram_errors": tg_result.get("errors") or [],
        "telegram_sent_empty": tg_result.get("sent_empty", 0),
        "telegram_skipped_already_notified": tg_result.get(
            "skipped_already_notified", 0
        ),
    }


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
        if ts is None:
            continue
        if ts >= cutoff:
            out.append(row)
    return out


def resolve_activity_report_hours(since_hours: float, gn: Optional[Dict[str, Any]] = None) -> float:
    """Ưu tiên cửa sổ giờ từ giao diện/API; config chỉ dùng khi không truyền."""
    try:
        h = float(since_hours)
        if h > 0:
            return h
    except (TypeError, ValueError):
        pass
    if gn and gn.get("activity_report_hours") is not None:
        try:
            return float(gn.get("activity_report_hours"))
        except (TypeError, ValueError):
            pass
    return 24.0


def resolve_role_report_hours(since_hours: float, gn: Optional[Dict[str, Any]] = None) -> float:
    try:
        h = float(since_hours)
        if h > 0:
            return h
    except (TypeError, ValueError):
        pass
    if gn and gn.get("role_change_report_hours") is not None:
        try:
            return float(gn.get("role_change_report_hours"))
        except (TypeError, ValueError):
            pass
    return 168.0


def _target_window_rows(
    notifs: Dict[str, List[Dict[str, Any]]],
    target_name: str,
    since_hours: float,
    *,
    gn: Optional[Dict[str, Any]] = None,
) -> Tuple[str, float, float, List[Dict[str, Any]], List[Dict[str, Any]]]:
    hrs_act = resolve_activity_report_hours(since_hours, gn)
    hrs_role = resolve_role_report_hours(since_hours, gn)
    cutoff_act = datetime.now() - timedelta(hours=max(0.1, hrs_act))
    cutoff_role = datetime.now() - timedelta(hours=max(0.1, hrs_role))
    name = str(target_name or "").strip()
    rows_hd = _rows_in_window(notifs.get("channel_hoatdong") or [], name, cutoff_act)
    rows_bd = _rows_in_window(
        [r for r in (notifs.get("channel_biendong") or []) if isinstance(r, dict)],
        name,
        cutoff_role,
    )
    return name, hrs_act, hrs_role, rows_hd, rows_bd


def _build_target_summary(
    name: str,
    hrs_act: float,
    hrs_role: float,
    rows_hd: List[Dict[str, Any]],
    rows_bd: List[Dict[str, Any]],
    since_hours: float,
) -> Dict[str, Any]:
    n_hd = len(rows_hd)
    n_bd = len(rows_bd)
    if n_bd > 0:
        status = "change"
    elif n_hd > 0:
        status = "stable_activity"
    elif n_hd == 0 and n_bd == 0:
        status = "no_data"
    else:
        status = "low_signal"

    lines: List[str] = []
    if n_hd:
        lines.append(f"Hoạt động ({hrs_act}h): {n_hd} tin")
        for r in rows_hd[:5]:
            ai = r.get("ai_result") if isinstance(r.get("ai_result"), dict) else {}
            s = str(ai.get("Summary") or r.get("title") or "").strip()
            if s:
                lines.append("  · " + s[:200])
    if n_bd:
        lines.append(f"Chức vụ ({hrs_role}h): {n_bd} tin")
    digest_text = "\n".join(lines) if lines else f"{name}: chưa có tin trong cửa sổ thời gian."

    if status == "change":
        headline = f"{name} — có tin biến động chức vụ ({n_bd})"
    elif status == "stable_activity":
        headline = f"{name} — {n_hd} tin hoạt động, chưa thấy đổi chức vụ"
    elif status == "no_data":
        headline = f"{name} — chưa có tin"
    else:
        headline = f"{name} — tín hiệu yếu"

    meta = _summary_card_meta(rows_hd, rows_bd)

    return {
        "target_name": name,
        "status": status,
        "headline": headline,
        "digest_short": digest_text[:500],
        "digest_text": digest_text,
        "activity_count": n_hd,
        "change_count": n_bd,
        "since_hours": since_hours,
        "window_hours_activity": hrs_act,
        "window_hours_role": hrs_role,
        **meta,
    }


def _summary_card_meta(
    rows_hd: List[Dict[str, Any]], rows_bd: List[Dict[str, Any]]
) -> Dict[str, Any]:
    all_rows = list(rows_hd) + list(rows_bd)
    confidences: List[float] = []
    sources: List[str] = []
    latest: Optional[datetime] = None

    for row in all_rows:
        if not isinstance(row, dict):
            continue
        ai = row.get("ai_result") if isinstance(row.get("ai_result"), dict) else {}
        try:
            c = float(ai.get("Confidence"))
            if c > 0:
                if c <= 1:
                    c *= 100
                confidences.append(min(100.0, max(0.0, c)))
        except (TypeError, ValueError):
            pass
        press = str(row.get("press_name") or row.get("press_domain") or "").strip()
        if press and press not in sources:
            sources.append(press)
        ts = parse_ts(row.get("timestamp"))
        if ts is not None and (latest is None or ts > latest):
            latest = ts

    avg_conf: Optional[int] = None
    if confidences:
        avg_conf = int(round(sum(confidences) / len(confidences)))

    is_new = False
    if latest is not None:
        is_new = (datetime.now() - latest).total_seconds() < 6 * 3600

    return {
        "confidence_avg": avg_conf,
        "sources": sources[:8],
        "latest_timestamp": latest.isoformat(timespec="seconds") if latest else None,
        "is_new": is_new,
        "article_total": len(all_rows),
    }


def collect_target_detail(
    notifs: Dict[str, List[Dict[str, Any]]],
    target_name: str,
    since_hours: float,
    *,
    gn: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    name, hrs_act, hrs_role, rows_hd, rows_bd = _target_window_rows(
        notifs, target_name, since_hours, gn=gn
    )
    summary = _build_target_summary(name, hrs_act, hrs_role, rows_hd, rows_bd, since_hours)
    report_lines = [summary.get("digest_text", ""), ""]
    report_lines.append(f"=== Tin hoạt động ({hrs_act}h) ===")
    for r in reversed(rows_hd):
        report_lines.append(f"- {r.get('title', '')} | {article_link_url(r)}")
    report_lines.append("")
    report_lines.append(f"=== Tin chức vụ ({hrs_role}h) ===")
    for r in reversed(rows_bd):
        report_lines.append(f"- {r.get('title', '')} | {article_link_url(r)}")

    return {
        "target_name": name,
        "activity_hours": hrs_act,
        "role_hours": hrs_role,
        "summary": summary,
        "report_text": "\n".join(report_lines).strip(),
        "records_hoatdong": [enrich_record_for_api(r) for r in reversed(rows_hd)],
        "records_biendong": [enrich_record_for_api(r) for r in reversed(rows_bd)],
    }


def summarize_target_in_window(
    notifs: Dict[str, List[Dict[str, Any]]],
    target_name: str,
    since_hours: float,
    *,
    gn: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    name, hrs_act, hrs_role, rows_hd, rows_bd = _target_window_rows(
        notifs, target_name, since_hours, gn=gn
    )
    return _build_target_summary(name, hrs_act, hrs_role, rows_hd, rows_bd, since_hours)


def summarize_targets_in_window(
    notifs: Dict[str, List[Dict[str, Any]]],
    target_names: List[str],
    since_hours: float,
    *,
    gn: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    return [
        summarize_target_in_window(notifs, name, since_hours, gn=gn)
        for name in target_names
    ]


if __name__ == "__main__":
    out = process_once()
    print(json.dumps(out, ensure_ascii=False, indent=2))

