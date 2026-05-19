"""Lấy tin từ RSS báo chính thống — URL trực tiếp, không cần decode Google News."""

from __future__ import annotations

import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse

try:
    import feedparser
except ImportError:
    feedparser = None  # type: ignore

from src.press_whitelist import PressWhitelist, _norm_domain

# RSS mặc định theo domain (khi Chinh_thong.json chưa có rss_url)
_DEFAULT_RSS_BY_DOMAIN: Dict[str, str] = {
    "vnexpress.net": "https://vnexpress.net/rss/tin-moi-nhat.rss",
    "tuoitre.vn": "https://tuoitre.vn/rss/tin-moi-nhat.htm",
    "thanhnien.vn": "https://thanhnien.vn/rss/home.rss",
}

_ROLE_HINT = re.compile(
    r"bổ nhiệm|miễn nhiệm|bãi nhiệm|phân công|tân nhiệm|quyết định|giữ chức",
    re.IGNORECASE,
)


def guess_rss_url(homepage_url: str) -> str:
    dom = _norm_domain(urlparse(str(homepage_url or "")).netloc)
    if not dom:
        return ""
    if dom in _DEFAULT_RSS_BY_DOMAIN:
        return _DEFAULT_RSS_BY_DOMAIN[dom]
    for key, rss in _DEFAULT_RSS_BY_DOMAIN.items():
        if dom == key or dom.endswith("." + key):
            return rss
    return ""


def press_rss_url(row: Dict[str, Any]) -> str:
    explicit = str(row.get("rss_url") or row.get("feed_url") or "").strip()
    if explicit.startswith("http"):
        return explicit
    return guess_rss_url(str(row.get("homepage_url") or row.get("url") or ""))


def _entry_text(entry: Any) -> str:
    title = str(getattr(entry, "title", "") or "")
    summary = str(getattr(entry, "summary", "") or getattr(entry, "description", "") or "")
    return f"{title} {summary}"


def _entry_link(entry: Any) -> str:
    link = str(getattr(entry, "link", "") or "").strip()
    if link.startswith("http"):
        return link
    for key in ("id", "guid"):
        val = getattr(entry, key, None)
        if val and str(val).strip().startswith("http"):
            return str(val).strip()
    return ""


def _classify_kind(text: str, query_suffix: str) -> str:
    if _ROLE_HINT.search(text) or _ROLE_HINT.search(query_suffix):
        return "biendong"
    return "hoatdong"


def fetch_one_feed(
    press_row: Dict[str, Any],
    rss_url: str,
    target_name: str,
    *,
    max_items: int,
    role_query_suffix: str,
) -> List[Tuple[Dict[str, Any], str]]:
    if feedparser is None:
        return []  # type: ignore[return-value]
    name = str(target_name or "").strip()
    if not name or not rss_url:
        return []

    try:
        parsed = feedparser.parse(rss_url)
    except Exception as exc:
        print(f"  [RSS] FAIL {rss_url[:60]}: {exc}")
        return []

    press_name = str(press_row.get("name") or "").strip()
    homepage = str(press_row.get("homepage_url") or "").strip()
    dom = _norm_domain(urlparse(homepage).netloc) if homepage else ""

    needle = name.lower()
    out: List[Tuple[Dict[str, Any], str]] = []
    entries = getattr(parsed, "entries", None) or []
    for entry in entries[: max(1, max_items)]:
        text = _entry_text(entry)
        if needle not in text.lower():
            continue
        link = _entry_link(entry)
        if not link.startswith("http"):
            continue
        title = str(getattr(entry, "title", "") or "").strip()
        published = ""
        if getattr(entry, "published", None):
            published = str(entry.published)
        elif getattr(entry, "updated", None):
            published = str(entry.updated)

        kind = _classify_kind(text, role_query_suffix)
        art = {
            "title": title,
            "description": str(getattr(entry, "summary", "") or "")[:2000],
            "url": link,
            "resolved_url": link,
            "press_name": press_name,
            "press_domain": dom,
            "published date": published,
            "source": "rss",
        }
        out.append((art, kind))
    return out


def collect_rss_for_target(
    whitelist: PressWhitelist,
    target_name: str,
    *,
    max_per_feed: int = 40,
    role_query_suffix: str = "",
    workers: int = 4,
) -> List[Tuple[Dict[str, Any], str]]:
    """Trả (article, news_kind) từ các RSS trong whitelist."""
    feeds: List[Tuple[Dict[str, Any], str]] = []
    for row in whitelist.entries:
        if not isinstance(row, dict):
            continue
        rss = press_rss_url(row)
        if rss:
            feeds.append((row, rss))

    if not feeds:
        return []

    articles: List[Tuple[Dict[str, Any], str]] = []
    w = max(1, min(int(workers), 8))

    def _job(item: Tuple[Dict[str, Any], str]) -> List[Tuple[Dict[str, Any], str]]:
        row, rss = item
        return fetch_one_feed(
            row,
            rss,
            target_name,
            max_items=max_per_feed,
            role_query_suffix=role_query_suffix,
        )

    with ThreadPoolExecutor(max_workers=w) as pool:
        futures = [pool.submit(_job, f) for f in feeds]
        for fut in as_completed(futures):
            try:
                articles.extend(fut.result())
            except Exception as exc:
                print(f"  [RSS] worker error: {exc}")

    return articles
