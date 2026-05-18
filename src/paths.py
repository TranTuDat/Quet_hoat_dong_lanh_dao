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

_LEGACY = {
    CONFIG_PATH: ROOT / "config.json",
    CHINH_THONG_PATH: ROOT / "Chinh_thong.json",
    NOTIFICATIONS_PATH: ROOT / "notifications.json",
    HISTORY_PATH: ROOT / "history.json",
    TELEGRAM_SENT_PATH: ROOT / "telegram_sent.json",
}


def ensure_project_dirs() -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def migrate_legacy_files() -> None:
    """Chuyển file JSON cũ ở thư mục gốc sang config/ và data/ (một lần)."""
    ensure_project_dirs()
    for new_path, legacy_path in _LEGACY.items():
        if new_path.exists() or not legacy_path.exists():
            continue
        shutil.copy2(legacy_path, new_path)


def path_str(path: Path) -> str:
    return str(path)
