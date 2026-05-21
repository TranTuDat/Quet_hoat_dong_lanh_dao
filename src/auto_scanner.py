"""Quét nền theo chu kỳ — cập nhật tin gần real-time."""

from __future__ import annotations

import sys
import threading
import time
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

from src.common import as_bool
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
            "last_scan_summary": None,
            "next_scan_at": None,
            "scan_count": 0,
            "ai_scan_mode": "activity",
            "ai_scan_mode_label": "",
        }

    def get_status(self) -> Dict[str, Any]:
        st = dict(self._state)
        st["thread_alive"] = bool(self._thread and self._thread.is_alive())
        return st

    def _sync_ai_mode_state(self) -> None:
        from src.monitor import resolve_ai_scan_options

        opts = resolve_ai_scan_options()
        self._state["ai_scan_mode"] = opts["mode"]
        self._state["ai_scan_mode_label"] = opts["label"]

    def wake_reconfig(self, *, scan_soon: bool = False) -> None:
        """Đồng bộ cài đặt; scan_soon=True → lượt auto chạy ngay (đổi chế độ AI)."""
        enabled, interval, _ = self._read_schedule()
        self._state["enabled"] = enabled
        self._state["interval_minutes"] = interval
        self._sync_ai_mode_state()
        self._config_wake.set()
        if scan_soon:
            print(
                f"[AUTO] Chế độ quét đổi → «{self._state.get('ai_scan_mode_label')}» "
                f"— lượt tự động tiếp theo dùng chế độ mới",
                flush=True,
            )

    def start(self) -> None:
        if self._started and self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._started = True
        self._sync_ai_mode_state()
        self._thread = threading.Thread(target=self._loop, name="auto-scanner", daemon=True)
        print(
            f"[AUTO] Background scanner started — chế độ: "
            f"{self._state.get('ai_scan_mode_label') or self._state.get('ai_scan_mode')}",
            flush=True,
        )
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
        enabled = as_bool(cfg.get("auto_scan_enabled"), True)
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
        mins = max(1, int(wait_sec // 60))
        print(
            f"[AUTO] Chờ {mins} phút đến lượt quét tiếp "
            f"(~{next_at.strftime('%H:%M:%S')}) — server vẫn chạy bình thường"
        )
        sys.stdout.flush()

        remaining = wait_sec
        ping_sec = 300.0
        while remaining > 0 and not self._stop.is_set():
            chunk = min(remaining, ping_sec)
            woke = self._config_wake.wait(timeout=chunk)
            if woke:
                self._config_wake.clear()
                return True
            remaining -= chunk
            if remaining >= ping_sec:
                left_m = max(1, int(remaining // 60))
                print(
                    f"[AUTO] Đang chờ lượt quét tiếp — còn ~{left_m} phút "
                    f"(~{next_at.strftime('%H:%M:%S')})"
                )
                sys.stdout.flush()
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
                self._sync_ai_mode_state()
                continue

    def _run_scan(
        self,
        *,
        hours: float,
        source: str,
        blocking: bool,
        target_name: Optional[str] = None,
        ignore_history: bool = False,
    ) -> Optional[Dict[str, Any]]:
        acquired = self._lock.acquire(blocking=blocking)
        if not acquired:
            print("  [SCAN] Bỏ qua — đang có lượt quét khác (auto/manual)", flush=True)
            return None

        try:
            self._state["is_scanning"] = True
            self._state["last_scan_source"] = source
            label = f"[SCAN] === Bắt đầu lượt quét ({source}) ==="
            if target_name:
                label += f" · đối tượng: {target_name}"
            print(label, flush=True)

            self._sync_ai_mode_state()
            result = process_once(
                scan_hours=hours,
                target_name=target_name,
                ignore_history=ignore_history,
            )
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
            self._state["last_scan_summary"] = {
                "processed_new": int(result.get("processed_new") or 0),
                "scan_ai_mode_label": result.get("scan_ai_mode_label"),
                "telegram_sent": int(result.get("telegram_sent") or 0),
                "ai_error_count": ai_count,
            }
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
            sys.stdout.flush()
            return result
        except Exception as exc:
            self._state["is_scanning"] = False
            self._state["last_scan_summary"] = None
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

    def request_rescan_for_mode_change(self) -> bool:
        """Quét lại toàn bộ với chế độ AI mới — không xếp hàng nếu đang quét."""
        if self._state.get("is_scanning"):
            print(
                "[CONFIG] Đổi chế độ AI — bỏ qua quét lại vì đang có lượt quét khác",
                flush=True,
            )
            return False

        def _worker() -> None:
            try:
                print(
                    "[CONFIG] Đổi chế độ AI — bắt đầu quét lại toàn bộ (ignore history)",
                    flush=True,
                )
                self.run_scan(
                    source="mode_change",
                    ignore_history=True,
                )
            except Exception as exc:
                print(f"[CONFIG] Quét lại sau đổi chế độ lỗi: {exc}", flush=True)

        threading.Thread(
            target=_worker, name="mode-change-rescan", daemon=True
        ).start()
        return True

    def run_scan(
        self,
        *,
        scan_hours: Optional[float] = None,
        source: str = "manual",
        target_name: Optional[str] = None,
        ignore_history: Optional[bool] = None,
    ) -> Dict[str, Any]:
        if scan_hours is None:
            _, _, scan_hours = self._read_schedule()
        if ignore_history is None:
            ignore_history = source in ("manual", "mode_change", "settings")
        out = self._run_scan(
            hours=float(scan_hours),
            source=source,
            blocking=True,
            target_name=target_name,
            ignore_history=bool(ignore_history),
        )
        if out is None:
            if self._state.get("is_scanning"):
                raise RuntimeError("Không thể quét — đang có lượt quét khác")
            err = self._state.get("last_error")
            if err:
                raise RuntimeError(str(err))
            raise RuntimeError("Không thể quét — đang bận")
        return out


_scanner: Optional[AutoScanner] = None


def get_auto_scanner() -> AutoScanner:
    global _scanner
    if _scanner is None:
        _scanner = AutoScanner()
    return _scanner
