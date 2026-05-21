"""
So sánh tốc độ thu thập tin: GNews hiện tại vs truy vấn site:báo chính thống.

Chạy: python scripts/benchmark_search_modes.py
"""

from __future__ import annotations

import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Tuple
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.monitor import (  # noqa: E402
    ROLE_QUERY_SUFFIX,
    Target,
    google_news_search,
)
from src.paths import CHINH_THONG_PATH, CONFIG_PATH  # noqa: E402
from src.press_whitelist import PressWhitelist, _norm_domain  # noqa: E402
from src.json_io import read_json  # noqa: E402


def _domains(wl: PressWhitelist, limit: int = 0) -> List[str]:
    doms = sorted(wl.domains)
    if limit > 0:
        return doms[:limit]
    return doms


def _site_clause(domains: List[str]) -> str:
    parts = [f"site:{d}" for d in domains if d]
    if not parts:
        return ""
    if len(parts) == 1:
        return parts[0]
    return "(" + " OR ".join(parts) + ")"


def _count_chinh_thong(batch: List[Dict[str, Any]], wl: PressWhitelist) -> int:
    n = 0
    for art in batch:
        url = str(art.get("url") or art.get("link") or "")
        dom = _norm_domain(urlparse(url).netloc)
        if dom and wl.is_allowed_url(f"https://{dom}/"):
            n += 1
    return n


def run_current(
    target: Target, *, language: str, country: str, max_results: int
) -> Tuple[float, int, int, int]:
    t0 = time.perf_counter()
    queries = 0
    raw = 0
    chinh = 0
    q_hd = target.name.strip()
    q_bd = f"{target.name} {ROLE_QUERY_SUFFIX}".strip()
    wl = PressWhitelist.from_file(str(CHINH_THONG_PATH))
    for q in (q_bd, q_hd):
        queries += 1
        batch = google_news_search(q, language=language, country=country, max_results=max_results)
        raw += len(batch)
        chinh += _count_chinh_thong(batch, wl)
    elapsed = time.perf_counter() - t0
    return elapsed, queries, raw, chinh


def run_site_per_press(
    target: Target,
    wl: PressWhitelist,
    *,
    language: str,
    country: str,
    max_results: int,
    max_sites: int = 0,
) -> Tuple[float, int, int, int]:
    t0 = time.perf_counter()
    queries = 0
    raw = 0
    chinh = 0
    doms = _domains(wl, max_sites)
    kinds = (
        (f"{target.name} {ROLE_QUERY_SUFFIX}", "biendong"),
        (target.name.strip(), "hoatdong"),
    )
    for dom in doms:
        for base, _kind in kinds:
            q = f"{base} site:{dom}".strip()
            queries += 1
            batch = google_news_search(
                q, language=language, country=country, max_results=max_results
            )
            raw += len(batch)
            chinh += _count_chinh_thong(batch, wl)
    elapsed = time.perf_counter() - t0
    return elapsed, queries, raw, chinh


def run_site_or_bundle(
    target: Target,
    wl: PressWhitelist,
    *,
    language: str,
    country: str,
    max_results: int,
) -> Tuple[float, int, int, int]:
    t0 = time.perf_counter()
    queries = 0
    raw = 0
    chinh = 0
    site = _site_clause(_domains(wl))
    if not site:
        return 0.0, 0, 0, 0
    for base in (f"{target.name} {ROLE_QUERY_SUFFIX}", target.name.strip()):
        q = f"{base} {site}".strip()
        queries += 1
        batch = google_news_search(
            q, language=language, country=country, max_results=max_results
        )
        raw += len(batch)
        chinh += _count_chinh_thong(batch, wl)
    elapsed = time.perf_counter() - t0
    return elapsed, queries, raw, chinh


def main() -> int:
    cfg = read_json(CONFIG_PATH, default={})
    gn = cfg.get("google_news") if isinstance(cfg.get("google_news"), dict) else {}
    language = str(gn.get("language") or "vi")
    country = str(gn.get("country") or "VN")
    max_results = int(gn.get("max_results_per_target") or 15)

    targets = cfg.get("targets") or []
    name = ""
    if targets and isinstance(targets[0], dict):
        name = str(targets[0].get("name") or "").strip()
    if not name:
        name = "Tô Lâm"
    target = Target(name=name, position="")

    wl = PressWhitelist.from_file(str(CHINH_THONG_PATH))
    doms = _domains(wl)
    print(f"Đối tượng thử: {target.name}")
    print(f"Báo chính thống: {len(doms)} domain — {', '.join(doms)}")
    print(f"max_results_per_target={max_results}, language={language}, country={country}\n")

    rows: List[Tuple[str, float, int, int, int]] = []

    print("[1/3] Hiện tại — 2 truy vấn GNews (không site:)...")
    try:
        r = run_current(target, language=language, country=country, max_results=max_results)
        rows.append(("Hien tai (2 query)", *r))
    except Exception as e:
        print(f"  Lỗi: {e}")

    print("[2/3] site: — 1 query / báo / loại (hoatdong + biendong)...")
    try:
        r = run_site_per_press(
            target, wl, language=language, country=country, max_results=max_results
        )
        rows.append((f"site tung bao ({len(doms)*2} query)", *r))
    except Exception as e:
        print(f"  Lỗi: {e}")

    print("[3/3] site: — gộp OR tất cả báo, 2 query...")
    try:
        r = run_site_or_bundle(
            target, wl, language=language, country=country, max_results=max_results
        )
        rows.append(("site OR gop (2 query)", *r))
    except Exception as e:
        print(f"  Lỗi: {e}")

    print("\n=== KẾT QUẢ ===")
    print(f"{'Cách':<28} {'Giây':>8} {'Query':>7} {'Bài':>6} {'Bài CT':>8}")
    print("-" * 62)
    baseline_s = None
    for label, sec, nq, raw, chinh in rows:
        if baseline_s is None:
            baseline_s = sec
        ratio = f"  x{sec / baseline_s:.2f}" if baseline_s and baseline_s > 0 else ""
        print(f"{label:<28} {sec:8.2f} {nq:7} {raw:6} {chinh:8}{ratio}")

    if len(rows) >= 2:
        fastest = min(rows, key=lambda x: x[1])
        print(f"\nNhanh nhất: {fastest[0]} ({fastest[1]:.2f}s)")
        if fastest[0].startswith("Hien"):
            print("Kết luận: Giữ cách hiện tại — site: không nhanh hơn đáng kể.")
        else:
            print("Kết luận: Có thể cân nhắc tích hợp cách site: (cần thử thêm trên nhiều đối tượng).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
