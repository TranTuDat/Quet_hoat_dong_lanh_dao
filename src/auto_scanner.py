"""Quét nền theo chu kỳ — cập nhật tin gần real-time."""

from __future__ import annotations

import threading
import time
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

from src.monitor import load_config, process_once

_MIN_INTERVAL_MIN = 5


class AutoScanner:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._config_wake = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._started = False
        self._state: Dict[str, Any] = {
            "enabled": False,
            "interval_minutes": 60,
            "is_scanning": False,
            "last_scan_at": None,
            "last_scan_source": None,
            "last_scan_ok": None,
            "last_error": None,
            "last_warning": None,
            "last_ai_error_count": 0,
            "last_processed_new": 0,
            "next_scan_at": None,
            "scan_count": 0,
        }

    def get_status(self) -> Dict[str, Any]:
        st = dict(self._state)
        st["thread_alive"] = bool(self._thread and self._thread.is_alive())
        return st

    def wake_reconfig(self) -> None:
        """Đánh thức vòng lặp và đồng bộ cài đặt mới lên trạng thái hiển thị."""
        enabled, interval, _ = self._read_schedule()
        self._state["enabled"] = enabled
        self._state["interval_minutes"] = interval
        self._config_wake.set()

    def start(self) -> None:
        if self._started and self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._started = True
        self._thread = threading.Thread(target=self._loop, name="auto-scanner", daemon=True)
        print("[AUTO] Background scanner started")
        self._thread.start()

    def ensure_running(self) -> None:
        """Khởi động lại thread quét nền nếu đã chết (crash, lỗi encoding cũ…)."""
        if self._stop.is_set():
            return
        if self._thread and self._thread.is_alive():
            return
        print("[AUTO] Thread nền không còn — khởi động lại")
        self._started = False
        self.start()

    def stop(self) -> None:
        self._stop.set()
        self._config_wake.set()

    def _read_schedule(self) -> tuple[bool, int, float]:
        cfg = load_config()
        enabled = _as_bool(cfg.get("auto_scan_enabled"), True)
        try:
            interval = int(cfg.get("scan_interval_minutes") or 60)
        except (TypeError, ValueError):
            interval = 60
        interval = max(_MIN_INTERVAL_MIN, min(1440, interval))

        gn = cfg.get("google_news") if isinstance(cfg.get("google_news"), dict) else {}
        try:
            hours = float(gn.get("activity_report_hours") or 24)
        except (TypeError, ValueError):
            hours = 24.0
        if hours <= 0:
            hours = 24.0
        return enabled, interval, hours

    def _wait_until_next_cycle(self, cycle_start: float, interval_minutes: int) -> bool:
        """Chờ đến lượt quét tiếp (tính từ đầu chu kỳ). True nếu bị đánh thức do đổi config."""
        elapsed = time.time() - cycle_start
        wait_sec = max(1.0, interval_minutes * 60 - elapsed)
        next_at = datetime.now() + timedelta(seconds=wait_sec)
        self._state["next_scan_at"] = next_at.isoformat(timespec="seconds")

        woke = self._config_wake.wait(timeout=wait_sec)
        if woke:
            self._config_wake.clear()
            return True
        return False

    def _loop(self) -> None:
        time.sleep(3)
        while not self._stop.is_set():
            cycle_start = time.time()
            enabled, interval, hours = self._read_schedule()
            self._state["enabled"] = enabled
            self._state["interval_minutes"] = interval

            if enabled:
                try:
                    self._run_scan(hours=hours, source="auto", blocking=False)
                except Exception as exc:
                    print(f"[AUTO] scan failed (retry next cycle): {exc}")

            enabled, interval, hours = self._read_schedule()
            self._state["enabled"] = enabled
            self._state["interval_minutes"] = interval

            if self._stop.is_set():
                break

            if self._wait_until_next_cycle(cycle_start, interval):
                print("[AUTO] settings changed — next cycle sooner")
                continue

    def _run_scan(
        self,
        *,
        hours: float,
        source: str,
        blocking: bool,
        target_name: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        acquired = self._lock.acquire(blocking=blocking)
        if not acquired:
            print("  [AUTO] skip — scan already running")
            return None

        try:
            self._state["is_scanning"] = True
            self._state["last_scan_source"] = source
            label = f"[AUTO] Scan start ({source})"
            if target_name:
                label += f" target={target_name}"
            print(label)

            result = process_once(scan_hours=hours, target_name=target_name)
            now = datetime.now().isoformat(timespec="seconds")

            ai_errs = [str(e) for e in (result.get("ai_errors") or []) if e]
            ai_count = int(result.get("ai_error_count") or len(ai_errs))
            warning = None
            scan_ok = True
            if ai_errs:
                warning = ai_errs[0]
                if len(ai_errs) > 1:
                    warning += f" (+{len(ai_errs) - 1} lỗi AI khác)"
                low = warning.lower()
                if "leaked" in low or "403" in low or "api key" in low:
                    scan_ok = False
                    warning = (
                        "Gemini API key không hợp lệ hoặc đã bị Google vô hiệu hóa. "
                        "Tạo key mới tại Google AI Studio và cập nhật config.json."
                    )

            self._state["is_scanning"] = False
            self._state["last_scan_at"] = result.get("timestamp") or now
            self._state["last_scan_ok"] = scan_ok
            self._state["last_error"] = warning if not scan_ok else None
            self._state["last_warning"] = warning if scan_ok and warning else None
            self._state["last_ai_error_count"] = ai_count
            self._state["last_processed_new"] = int(result.get("processed_new") or 0)
            self._state["scan_count"] = int(self._state.get("scan_count") or 0) + 1

            tg = result.get("telegram_sent", 0)
            tg_skip = result.get("telegram_skipped_already_notified", 0)
            suffix = f", ai_errors={ai_count}" if ai_count else ""
            print(
                f"  [AUTO] done — +{result.get('processed_new', 0)} new, "
                f"telegram={tg}, tg_skip_old={tg_skip}{suffix}"
            )
            if warning:
                print(f"  [AUTO] warning: {warning}")
            return result
        except Exception as exc:
            self._state["is_scanning"] = False
            self._state["last_scan_ok"] = False
            self._state["last_error"] = str(exc)
            self._state["last_warning"] = None
            self._state["last_ai_error_count"] = 0
            self._state["last_scan_at"] = datetime.now().isoformat(timespec="seconds")
            print(f"  [AUTO] error: {exc}")
            if source != "auto":
                raise
            return None
        finally:
            self._lock.release()

    def run_scan(
        self,
        *,
        scan_hours: Optional[float] = None,
        source: str = "manual",
        target_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        if scan_hours is None:
            _, _, scan_hours = self._read_schedule()
        out = self._run_scan(
            hours=float(scan_hours),
            source=source,
            blocking=True,
            target_name=target_name,
        )
        if out is None:
            if self._state.get("is_scanning"):
                raise RuntimeError("Không thể quét — đang có lượt quét khác")
            err = self._state.get("last_error")
            if err:
                raise RuntimeError(str(err))
            raise RuntimeError("Không thể quét — đang bận")
        return out


def _as_bool(val: Any, default: bool = False) -> bool:
    if isinstance(val, bool):
        return val
    if val is None:
        return default
    return str(val).strip().lower() not in ("0", "false", "no", "off", "")


_scanner: Optional[AutoScanner] = None


def get_auto_scanner() -> AutoScanner:
    global _scanner
    if _scanner is None:
        _scanner = AutoScanner()
    return _scanner
