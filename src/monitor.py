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
    migrate_legacy_files,
    path_str,
)
from src.press_whitelist import PressWhitelist
from src.rss_fetch import collect_rss_for_target
from src.telegram_notify import is_telegram_enabled, notify_records

migrate_legacy_files()


def is_google_news_url(url: str) -> bool:
    u = str(url or "").lower()
    return "news.google.com" in u or "google.com/rss/articles" in u


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
    """Trùng URL: ưu tiên biendong (bỏ hoatdong trùng — không phân tích 2 lần)."""
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


def article_link_url(row: Dict[str, Any]) -> str:
    resolved = str(row.get("resolved_url") or "").strip()
    url = str(row.get("url") or "").strip()
    if resolved.startswith("http"):
        return resolved
    if url.startswith("http") and not is_google_news_url(url):
        return url
    return resolved or url


def enrich_record_for_api(row: Dict[str, Any]) -> Dict[str, Any]:
    out = dict(row)
    out["article_url"] = article_link_url(row)
    return out


def _history_key(target_name: str, url: str) -> str:
    return f"{str(target_name or '').strip()}|{str(url or '').strip()}"


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


def google_news_search(query: str, language: str, country: str, max_results: int) -> List[Dict[str, Any]]:
    gnews = GNews(language=language, country=country, period="1d", max_results=max_results)
    return gnews.get_news(query)


def clean_json_text(text: str) -> str:
    text = text.strip()
    text = re.sub(r"^```json\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"^```\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"```$", "", text)
    return text.strip()


def call_gemini_for_change(gemini_api_key: str, target: Target, article: Dict[str, Any]) -> Dict[str, Any]:
    genai.configure(api_key=gemini_api_key)

    title = article.get("title", "")
    description = article.get("description", "") or ""
    url = article.get("url", "")

    position_ref = target.position.strip() if isinstance(target.position, str) else ""
    position_or_default = position_ref or "chức vụ"

    # NOTE: prompt là chuỗi f-string-like nhưng thực tế dùng .format().
    # Tránh để các placeholder {date}/{from}/{to}/{decision} trong prompt bị Python .format() hiểu nhầm.
    prompt = (
        "Bạn là hệ thống phân tích tin tức. "

        "Hãy đọc bài báo sau và chỉ xét đúng đối tượng: {name} (không suy rộng sang người khác). "
        "Nếu bài KHÔNG nói về hoạt động/việc làm của đối tượng đó, hãy loại bài đó.\n\n"
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
        title=title,
        description=description,
        url=url,
    )

    preferred = str(os.environ.get("GEMINI_MODEL", "")).strip() or ""
    candidate_models = [preferred, "gemini-1.5-flash", "gemini-2.5-flash"]

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

    return {
        "Is_Activity": bool(is_activity),
        "Is_Change": bool(is_change) and bool(is_activity),
        "Matched_Target": bool(matched_target),
        "Summary": summary,
        "Confidence": max(0, min(100, conf)),
        "Target_Name": target.name,
    }


def _collect_articles_for_target(
    target: Target,
    *,
    language: str,
    country: str,
    max_results: int,
    whitelist: Optional[PressWhitelist] = None,
    use_rss: bool = True,
    rss_max_per_feed: int = 40,
) -> List[Tuple[Dict[str, Any], str]]:
    """GNews + RSS; trùng URL ưu tiên biendong (bỏ hoatdong trùng)."""
    pairs: List[Tuple[Dict[str, Any], str]] = []

    q_hd = str(target.name).strip()
    q_bd = f"{target.name} {ROLE_QUERY_SUFFIX}".strip()

    # Biến động chức vụ trước — cùng bài với hoạt động sẽ giữ loại biendong
    for query, kind in ((q_bd, "biendong"), (q_hd, "hoatdong")):
        print(f"[SCAN] target={target.name} kind={kind} query={query[:100]}...")
        try:
            batch = google_news_search(query, language=language, country=country, max_results=max_results)
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
            role_query_suffix=ROLE_QUERY_SUFFIX,
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
    whitelist: PressWhitelist,
    filter_press: bool,
    decode_workers: int = 4,
    decode_interval: float = 0.15,
) -> Tuple[List[Tuple[Dict[str, Any], str]], int]:
    """Lọc history trước decode; chỉ decode URL Google News còn lại."""
    pending: List[Tuple[Dict[str, Any], str]] = []
    skipped_history = 0

    for art, kind in articles:
        url = str(art.get("url") or "").strip()
        if _history_key(target_name, url) in history_set:
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
    for art, kind in pending:
        url = str(art.get("url") or "").strip()
        pre_resolved = str(art.get("resolved_url") or "").strip()
        if pre_resolved.startswith("http"):
            resolved = pre_resolved
        else:
            resolved = decoded.get(url) or (url if not is_google_news_url(url) else "")
        if filter_press and resolved and not whitelist.is_allowed_url(resolved):
            continue
        if filter_press and not resolved:
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
    return kept, skipped_history


def _process_gemini_batch(
    gemini_key: str,
    target: Target,
    pending: List[Tuple[Dict[str, Any], str]],
    *,
    gemini_workers: int,
) -> Tuple[List[Tuple[Dict[str, Any], str, Dict[str, Any]]], List[str]]:
    """Gọi Gemini song song; trả (kết quả, danh sách lỗi)."""
    if not pending:
        return [], []

    w = max(1, min(int(gemini_workers), 6))
    out: List[Tuple[Dict[str, Any], str, Dict[str, Any]]] = []
    errors: List[str] = []

    def _one(item: Tuple[Dict[str, Any], str]) -> Tuple[Dict[str, Any], str, Dict[str, Any]]:
        art, kind = item
        ai = call_gemini_for_change(gemini_key, target, art)
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


def process_once(*, scan_hours: Optional[float] = None, target_name: Optional[str] = None) -> Dict[str, Any]:
    cfg = load_config()
    gn = cfg.get("google_news") if isinstance(cfg.get("google_news"), dict) else {}

    history = load_history()
    history_set = set(history)
    notifs = load_notifications()

    gemini_key = str(cfg.get("gemini_api_key") or "").strip()
    if not gemini_key:
        raise ValueError("Thiếu gemini_api_key trong config.json")

    language = str(gn.get("language") or "vi")
    country = str(gn.get("country") or "VN")
    max_results = int(gn.get("max_results_per_target") or 15)
    filter_press = is_chinh_thong_filter_enabled(cfg)
    whitelist = PressWhitelist.from_file(path_str(CHINH_THONG_PATH))

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
    now_iso = datetime.now().isoformat(timespec="seconds")
    scan_results: List[Dict[str, Any]] = []
    saved_count = 0
    new_records: List[Dict[str, Any]] = []
    skipped_history_dup = 0
    skipped_pre_decode = 0
    ai_errors: List[str] = []

    for target in targets:
        raw_pairs = _collect_articles_for_target(
            target,
            language=language,
            country=country,
            max_results=max_results,
            whitelist=whitelist,
            use_rss=perf["use_rss"],
            rss_max_per_feed=perf["rss_max_per_feed"],
        )
        pairs, skipped_hist = _apply_decode_and_whitelist(
            raw_pairs,
            target_name=target.name,
            history_set=history_set,
            whitelist=whitelist,
            filter_press=filter_press,
            decode_workers=perf["decode_workers"],
            decode_interval=perf["decode_interval"],
        )
        skipped_history_dup += skipped_hist
        skipped_pre_decode += skipped_hist
        pairs = _merge_article_pairs(pairs)

        if not pairs:
            continue

        for art, news_kind in pairs:
            url = str(art.get("url") or "").strip()
            print(f"  [ARTICLE] {target.name} [{news_kind}] {url[:72]}...")

        analyzed, batch_errors = _process_gemini_batch(
            gemini_key,
            target,
            pairs,
            gemini_workers=perf["gemini_workers"],
        )
        ai_errors.extend(batch_errors)

        for art, news_kind, ai_result in analyzed:
            url = str(art.get("url") or "").strip()
            history_key = _history_key(target.name, url)
            print(
                f"  [AI] {target.name} matched={ai_result.get('Matched_Target')} "
                f"activity={ai_result.get('Is_Activity')} change={ai_result.get('Is_Change')}"
            )

            if not ai_result.get("Matched_Target") or not ai_result.get("Is_Activity"):
                history_set.add(history_key)
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

            notifs["channel_hoatdong"].append(dict(record))
            if ai_result.get("Is_Change"):
                notifs["channel_biendong"].append(dict(record))

            scan_results.append(record)
            saved_count += 1
            new_records.append(record)
            history_set.add(history_key)

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

    return {
        "success": True,
        "processed_new": saved_count,
        "processed": scan_results,
        "history_size": len(history_set),
        "skipped_history_dup": skipped_history_dup,
        "skipped_pre_decode": skipped_pre_decode,
        "scan_use_rss": perf["use_rss"],
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


def _parse_ts(value: Any) -> Optional[datetime]:
    if not value:
        return None
    s = str(value).strip()
    for fmt in (
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%dT%H:%M",
    ):
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
        ts = _parse_ts(row.get("timestamp"))
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

