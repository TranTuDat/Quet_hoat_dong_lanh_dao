"""Đường dẫn thư mục dự án — dùng chung cho toàn bộ module."""

from __future__ import annotations

import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

CONFIG_DIR = ROOT / "config"
DATA_DIR = ROOT / "data"
TEMPLATES_DIR = ROOT / "templates"
STATIC_DIR = ROOT / "static"

CONFIG_PATH = CONFIG_DIR / "config.json"
CHINH_THONG_PATH = CONFIG_DIR / "Chinh_thong.json"
NOTIFICATIONS_PATH = DATA_DIR / "notifications.json"
HISTORY_PATH = DATA_DIR / "history.json"
TELEGRAM_SENT_PATH = DATA_DIR / "telegram_sent.json"
URL_DECODE_CACHE_PATH = DATA_DIR / "url_decode_cache.json"

_LEGACY = {
    CONFIG_PATH: ROOT / "config.json",
    CHINH_THONG_PATH: ROOT / "Chinh_thong.json",
    NOTIFICATIONS_PATH: ROOT / "notifications.json",
    HISTORY_PATH: ROOT / "history.json",
    TELEGRAM_SENT_PATH: ROOT / "telegram_sent.json",
    URL_DECODE_CACHE_PATH: ROOT / "url_decode_cache.json",
}


def ensure_project_dirs() -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def _chinh_thong_is_empty(path: Path) -> bool:
    if not path.is_file():
        return True
    try:
        import json

        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        return not (isinstance(data, list) and len(data) > 0)
    except Exception:
        return True


def migrate_chinh_thong_if_empty() -> None:
    """Khôi phục danh sách báo nếu config/Chinh_thong.json trống."""
    ensure_project_dirs()
    if not _chinh_thong_is_empty(CHINH_THONG_PATH):
        return
    for src in (
        ROOT / "Phan_mem" / "config" / "Chinh_thong.json",
        ROOT / "Chinh_thong.json",
    ):
        if _chinh_thong_is_empty(src):
            continue
        shutil.copy2(src, CHINH_THONG_PATH)
        return


def migrate_legacy_files() -> None:
    """Chuyển file JSON cũ ở thư mục gốc sang config/ và data/ (một lần)."""
    ensure_project_dirs()
    for new_path, legacy_path in _LEGACY.items():
        if new_path.exists() or not legacy_path.exists():
            continue
        shutil.copy2(legacy_path, new_path)
    migrate_chinh_thong_if_empty()


def path_str(path: Path) -> str:
    return str(path)
