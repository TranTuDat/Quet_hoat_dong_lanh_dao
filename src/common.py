"""Tiện ích dùng chung — tránh copy giữa monitor, web, telegram, data_store."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Optional


def as_bool(val: Any, default: bool = False) -> bool:
    if isinstance(val, bool):
        return val
    if val is None:
        return default
    return str(val).strip().lower() not in ("0", "false", "no", "off", "")


def parse_ts(value: Any) -> Optional[datetime]:
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

        dt = parsedate_to_datetime(s)
        if dt.tzinfo:
            return dt.astimezone(timezone.utc).replace(tzinfo=None)
        return dt
    except Exception:
        return None


def is_google_news_url(url: str) -> bool:
    u = str(url or "").lower()
    return "news.google.com" in u or "google.com/rss/articles" in u


def article_link_url(row: Dict[str, Any]) -> str:
    resolved = str(row.get("resolved_url") or "").strip()
    url = str(row.get("url") or "").strip()
    if resolved.startswith("http"):
        return resolved
    if url.startswith("http") and not is_google_news_url(url):
        return url
    return resolved or url
