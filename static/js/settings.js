/* Cài đặt hệ thống — modal */

(function () {
  let pressSources = [];
  let aiScanProfiles = [];

  async function readApiJson(res) {
    const text = await res.text();
    try {
      return JSON.parse(text);
    } catch {
      const isHtml = /^\s*</.test(text);
      if (res.status === 404 && isHtml) {
        throw new Error(
          "API xóa dữ liệu chưa có trên server đang chạy. " +
            "Dừng python He_thong.py (Ctrl+C) rồi chạy lại, sau đó Ctrl+F5 trang web."
        );
      }
      if (isHtml) {
        throw new Error(
          `Server trả trang HTML (${res.status}), không phải JSON. ` +
            "Khởi động lại python He_thong.py."
        );
      }
      throw new Error("Phản hồi server không hợp lệ (không phải JSON).");
    }
  }

  function escapeHtml(s) {
    return String(s ?? "").replace(/[&<>"']/g, (c) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c])
    );
  }

  function icons() {
    if (window.lucide) lucide.createIcons();
  }

  function openModal() {
    const el = document.getElementById("settingsModal");
    if (!el) return;
    el.classList.add("open");
    el.setAttribute("aria-hidden", "false");
    loadSettings();
    icons();
    if (window.lucide) lucide.createIcons();
  }

  function closeModal() {
    const el = document.getElementById("settingsModal");
    if (!el) return;
    el.classList.remove("open");
    el.setAttribute("aria-hidden", "true");
  }

  function renderPressList() {
    const box = document.getElementById("pressList");
    if (!box) return;
    if (!pressSources.length) {
      box.innerHTML = '<div class="empty" style="padding:16px">Chưa có báo nào</div>';
      return;
    }
    box.innerHTML = pressSources
      .map(
        (p, i) => `
      <div class="press-item">
        <div class="pinfo">
          <b>${escapeHtml(p.name)}</b>
          <small>${escapeHtml(p.homepage_url || p.url || "")}</small>
        </div>
        <button type="button" class="btn btn-danger btn-icon" data-press-del="${i}" title="Xóa">
          <i data-lucide="trash-2"></i>
        </button>
      </div>`
      )
      .join("");
    box.querySelectorAll("[data-press-del]").forEach((btn) => {
      btn.addEventListener("click", () => {
        const idx = Number(btn.getAttribute("data-press-del"));
        pressSources.splice(idx, 1);
        renderPressList();
        icons();
      });
    });
    icons();
  }

  const AI_MODE_ICONS = {
    keyword: "text-search",
    activity: "user-check",
    full: "briefcase",
  };

  const AI_MODE_FALLBACK = [
    {
      id: "keyword",
      label: "Từ khóa (không Gemini)",
      hint: "Lưu tin theo truy vấn Google News/RSS, không gọi AI, không kênh biến động.",
    },
    {
      id: "activity",
      label: "AI — hoạt động & đúng đối tượng",
      hint: "Gemini lọc hoạt động và xác nhận đúng tên; không quét truy vấn bổ nhiệm/miễn nhiệm.",
    },
    {
      id: "full",
      label: "AI — đầy đủ (cả biến động chức vụ)",
      hint: "Thêm lượt tìm bổ nhiệm/miễn nhiệm và kênh biến động.",
    },
  ];

  function getSelectedAiScanMode() {
    return document.getElementById("setAiScanMode")?.value || "activity";
  }

  function setAiScanModeValue(mode) {
    const hidden = document.getElementById("setAiScanMode");
    const picker = document.getElementById("setAiScanModePicker");
    const m = mode || "activity";
    if (hidden) hidden.value = m;
    if (picker) {
      picker.querySelectorAll(".ai-mode-card").forEach((card) => {
        const on = card.getAttribute("data-mode") === m;
        card.classList.toggle("is-selected", on);
        const radio = card.querySelector('input[type="radio"]');
        if (radio) radio.checked = on;
      });
    }
    updateAiScanModeHint(m, aiScanProfiles, "");
  }

  function renderAiScanModePicker(profiles, selected) {
    const picker = document.getElementById("setAiScanModePicker");
    if (!picker) return;
    const list =
      Array.isArray(profiles) && profiles.length ? profiles : AI_MODE_FALLBACK;
    const sel = selected || "activity";
    picker.innerHTML = list
      .map((p) => {
        const id = p.id || "activity";
        const icon = AI_MODE_ICONS[id] || "cpu";
        const isSel = id === sel;
        const badge =
          id === "activity"
            ? '<span class="ai-mode-card__badge">Khuyên dùng</span>'
            : "";
        return `
        <label class="ai-mode-card${isSel ? " is-selected" : ""}" data-mode="${escapeHtml(id)}">
          <input type="radio" name="aiScanMode" value="${escapeHtml(id)}"${
          isSel ? " checked" : ""
        } />
          <span class="ai-mode-card__icon" aria-hidden="true">
            <i data-lucide="${escapeHtml(icon)}"></i>
          </span>
          <span class="ai-mode-card__body">
            <span class="ai-mode-card__title">${escapeHtml(p.label || id)}${badge}</span>
            <span class="ai-mode-card__desc">${escapeHtml(p.hint || "")}</span>
          </span>
        </label>`;
      })
      .join("");
    setAiScanModeValue(sel);
    picker.querySelectorAll(".ai-mode-card").forEach((card) => {
      card.addEventListener("click", () => {
        const mode = card.getAttribute("data-mode");
        if (!mode) return;
        setAiScanModeValue(mode);
        saveAiScanModeImmediate(mode).catch((e) => {
          alert(e?.message || String(e));
          loadSettings().catch(() => {});
        });
        if (window.lucide) lucide.createIcons();
      });
    });
    if (window.lucide) lucide.createIcons();
  }

  function updateAiScanModeHint(mode, profiles, fallbackHint) {
    const hintEl = document.getElementById("setAiScanModeHint");
    if (!hintEl) return;
    const list = Array.isArray(profiles) ? profiles : [];
    const row = list.find((p) => p.id === mode);
    hintEl.textContent = row?.hint || fallbackHint || "";
  }

  function formatBytes(n) {
    const b = Number(n) || 0;
    if (b < 1024) return b + " B";
    if (b < 1024 * 1024) return (b / 1024).toFixed(1) + " KB";
    return (b / (1024 * 1024)).toFixed(2) + " MB";
  }

  function getSelectedTimeRange() {
    const checked = document.querySelector('input[name="clrTimeRange"]:checked');
    return checked?.value || "all";
  }

  function renderDataStats(stats) {
    const line = document.getElementById("dataStatsLine");
    const n = stats?.notifications || {};
    const h = stats?.history || {};
    const t = stats?.telegram_sent || {};
    const c = stats?.decode_cache || {};
    const rangeLabel = stats?.time_range_label || "Toàn bộ";
    const tr = stats?.time_range || "all";
    const inWin = Number(stats?.in_window_notifications ?? 0);

    if (line) {
      if (tr === "all") {
        line.textContent =
          `${n.total ?? 0} tin · ${h.entries ?? 0} URL history · ` +
          `${t.entries ?? 0} khóa Telegram · ${c.entries ?? 0} cache`;
      } else {
        line.textContent =
          `Khoảng «${rangeLabel}»: ${inWin} tin sẽ xóa (tổng ${n.total ?? 0} tin trong hệ thống)`;
      }
    }

    const scoped = (inRange, total, suffix) => {
      if (tr === "all") return `${total ?? 0} ${suffix}`;
      return `${inRange ?? 0} trong khoảng · tổng ${total ?? 0} ${suffix}`;
    };

    const setMeta = (id, text) => {
      const el = document.getElementById(id);
      if (el) el.textContent = text || "";
    };
    setMeta(
      "clrNotificationsMeta",
      scoped(inWin, n.total, "tin hoạt động/biến động") +
        ` · ${formatBytes(n.bytes)}`
    );
    setMeta(
      "clrHistoryMeta",
      scoped(h.entries, h.entries_total ?? h.entries, "mục") +
        ` · ${formatBytes(h.bytes)} — xóa để quét lại URL cũ`
    );
    setMeta(
      "clrTelegramSentMeta",
      scoped(t.entries, t.entries_total ?? t.entries, "mục") +
        ` · ${formatBytes(t.bytes)} — xóa để gửi lại tin`
    );
    setMeta(
      "clrDecodeCacheMeta",
      scoped(c.entries, c.entries_total ?? c.entries, "mục") +
        ` · ${formatBytes(c.bytes)}`
    );
  }

  async function loadDataStats() {
    const tr = getSelectedTimeRange();
    const res = await fetch(
      "/api/data/stats?time_range=" + encodeURIComponent(tr)
    );
    const data = await readApiJson(res);
    if (!data.success) throw new Error(data.error || "Không tải thống kê dữ liệu");
    renderDataStats(data.stats);
  }

  async function clearSelectedData() {
    const items = [];
    if (document.getElementById("clrNotifications")?.checked) items.push("notifications");
    if (document.getElementById("clrHistory")?.checked) items.push("history");
    if (document.getElementById("clrTelegramSent")?.checked) items.push("telegram_sent");
    if (document.getElementById("clrDecodeCache")?.checked) items.push("decode_cache");
    if (!items.length) {
      alert("Chọn ít nhất một loại dữ liệu cần xóa.");
      return;
    }

    const labels = {
      notifications: "tin đã lưu",
      history: "URL đã quét",
      telegram_sent: "đã gửi Telegram",
      decode_cache: "cache decode",
    };
    const timeRange = getSelectedTimeRange();
    let rangeLabel = "Toàn bộ";
    try {
      const preview = await fetch(
        "/api/data/stats?time_range=" + encodeURIComponent(timeRange)
      );
      const previewData = await readApiJson(preview);
      if (previewData.success) {
        rangeLabel = previewData.stats?.time_range_label || rangeLabel;
      }
    } catch {
      /* bỏ qua */
    }

    const desc = items.map((k) => labels[k] || k).join(", ");
    if (
      !confirm(
        "Xóa " +
          desc +
          " trong khoảng «" +
          rangeLabel +
          "»?\n\nKhông thể hoàn tác. Sau khi xóa history, lần quét sau có thể xử lý lại các URL cũ."
      )
    ) {
      return;
    }

    const btn = document.getElementById("btnClearData");
    if (btn) btn.disabled = true;
    try {
      const res = await fetch("/api/data/clear", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ items, confirm: "XOA", time_range: timeRange }),
      });
      const data = await readApiJson(res);
      if (!res.ok || !data.success) throw new Error(data.error || "Xóa thất bại");
      renderDataStats(data.stats);
      if (typeof window.refreshDashboardData === "function") {
        await window.refreshDashboardData();
      }
      const rangeNote = data.time_range_label
        ? " («" + data.time_range_label + "»)"
        : "";
      if (typeof window.flashStatus === "function") {
        window.flashStatus(
          "Đã xóa dữ liệu" + rangeNote + ": " + (data.cleared || []).join(", "),
          true
        );
      }
      const removed = data.removed_notifications;
      const extra =
        removed != null && removed > 0 ? "\nĐã xóa " + removed + " tin." : "";
      alert("Đã xóa xong." + extra);
    } finally {
      if (btn) btn.disabled = false;
    }
  }

  async function loadSettings() {
    const res = await fetch("/api/settings");
    const data = await res.json();
    if (!data.success) throw new Error(data.error || "Không tải được cài đặt");

    const s = data.settings || {};
    aiScanProfiles = s.ai_scan_profiles || [];
    renderAiScanModePicker(aiScanProfiles, s.ai_scan_mode || "activity");
    if (s.ai_scan_mode_hint) {
      updateAiScanModeHint(
        s.ai_scan_mode || "activity",
        aiScanProfiles,
        s.ai_scan_mode_hint
      );
    }
    document.getElementById("setFilterChinhThong").checked = !!s.filter_chinh_thong_only;
    document.getElementById("setMaxResults").value = String(s.max_results_per_target ?? 15);
    const rssEl = document.getElementById("setUseRss");
    if (rssEl) rssEl.checked = s.use_rss_feeds !== false;
    const autoEl = document.getElementById("setAutoScan");
    if (autoEl) autoEl.checked = s.auto_scan_enabled !== false;
    const intEl = document.getElementById("setScanInterval");
    if (intEl) intEl.value = String(s.scan_interval_minutes ?? 15);
    const uiEl = document.getElementById("setUiRefresh");
    if (uiEl) uiEl.value = String(s.ui_refresh_seconds ?? 30);
    document.getElementById("setTelegramEnabled").checked = !!s.enabled;
    document.getElementById("setTelegramRoleOnly").checked = !!s.notify_role_change_only;
    const tgEmpty = document.getElementById("setTelegramNotifyEmpty");
    if (tgEmpty) tgEmpty.checked = !!s.notify_on_empty;
    document.getElementById("setTelegramToken").value = s.bot_token || "";
    document.getElementById("setTelegramChatId").value = s.chat_id || "";

    pressSources = (data.press_sources || []).map((p) => ({
      name: p.name || "",
      homepage_url: p.homepage_url || p.url || "",
      rss_url: p.rss_url || "",
    }));
    renderPressList();
    await loadDataStats().catch(() => {
      const line = document.getElementById("dataStatsLine");
      if (line) line.textContent = "Không tải được thống kê dữ liệu";
    });
  }

  async function testTelegram() {
    const body = {
      bot_token: document.getElementById("setTelegramToken").value.trim(),
      chat_id: document.getElementById("setTelegramChatId").value.trim(),
    };
    const res = await fetch("/api/settings/telegram-test", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    const data = await res.json();
    if (!res.ok || !data.success) throw new Error(data.error || "Gửi thử thất bại");
    alert(data.message || "Đã gửi tin nhắn thử");
  }

  async function saveAiScanModeImmediate(mode) {
    const m = mode || getSelectedAiScanMode();
    const res = await fetch("/api/settings", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ ai_scan_mode: m }),
    });
    const text = await res.text();
    let data;
    try {
      data = JSON.parse(text);
    } catch {
      throw new Error("Không lưu được chế độ quét");
    }
    if (!res.ok || !data.success) throw new Error(data.error || "Lỗi lưu");
    if (window.__LAST_SETTINGS__) {
      window.__LAST_SETTINGS__.ai_scan_mode = data.ai_scan_mode || m;
      window.__LAST_SETTINGS__.ai_scan_mode_label = data.ai_scan_mode_label;
      window.__LAST_SETTINGS__.use_ai = m !== "keyword";
    }
    if (typeof window.flashStatus === "function") {
      const busy = data.rescan_started === false && /đang có lượt quét/i.test(data.message || "");
      window.flashStatus(
        data.message || "Đã lưu",
        !busy && !data.rescan_started
      );
    }
    if (typeof window.refreshDashboardData === "function") {
      await window.refreshDashboardData();
    }
  }

  async function saveFilterChinhThongImmediate() {
    const filter_chinh_thong_only =
      document.getElementById("setFilterChinhThong")?.checked !== false;
    const res = await fetch("/api/settings", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ filter_chinh_thong_only }),
    });
    const text = await res.text();
    let data;
    try {
      data = JSON.parse(text);
    } catch {
      throw new Error("Không lưu được cài đặt lọc báo");
    }
    if (!res.ok || !data.success) throw new Error(data.error || "Lỗi lưu");
    if (typeof window.refreshDashboardData === "function") {
      await window.refreshDashboardData();
    }
    if (typeof window.flashStatus === "function") {
      window.flashStatus(
        filter_chinh_thong_only
          ? "Đã bật lọc báo chính thống"
          : "Đã tắt lọc báo chính thống",
        true
      );
    }
  }

  async function saveSettings() {
    const body = {
      ai_scan_mode: getSelectedAiScanMode(),
      filter_chinh_thong_only: document.getElementById("setFilterChinhThong").checked,
      max_results_per_target: Number(document.getElementById("setMaxResults").value) || 15,
      use_rss_feeds: document.getElementById("setUseRss")?.checked !== false,
      auto_scan_enabled: document.getElementById("setAutoScan")?.checked !== false,
      scan_interval_minutes: Math.max(
        5,
        Number(document.getElementById("setScanInterval")?.value) || 15
      ),
      ui_refresh_seconds: Number(document.getElementById("setUiRefresh")?.value) || 30,
      enabled: document.getElementById("setTelegramEnabled").checked,
      notify_role_change_only: document.getElementById("setTelegramRoleOnly").checked,
      notify_on_empty: document.getElementById("setTelegramNotifyEmpty")?.checked === true,
      bot_token: document.getElementById("setTelegramToken").value.trim(),
      chat_id: document.getElementById("setTelegramChatId").value.trim(),
      press_sources: pressSources,
    };

    const res = await fetch("/api/settings", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ ...body, trigger_scan: false }),
    });
    const text = await res.text();
    let data;
    try {
      data = JSON.parse(text);
    } catch {
      throw new Error("Không lưu được — hãy khởi động lại Test.py");
    }
    if (!res.ok || !data.success) throw new Error(data.error || "Lỗi lưu");

    closeModal();
    if (typeof window.refreshDashboardData === "function") {
      await window.refreshDashboardData();
    }
    if (typeof window.flashStatus === "function") {
      window.flashStatus("Đã lưu cài đặt", true);
    }
  }

  function initSettings() {
    document.getElementById("btnOpenSettings")?.addEventListener("click", openModal);
    document.getElementById("btnCloseSettings")?.addEventListener("click", closeModal);
    document.getElementById("btnCancelSettings")?.addEventListener("click", closeModal);
    document.getElementById("settingsModal")?.addEventListener("click", (e) => {
      if (e.target.id === "settingsModal") closeModal();
    });

    document.getElementById("btnAddPress")?.addEventListener("click", () => {
      const name = document.getElementById("pressName")?.value.trim();
      const url = document.getElementById("pressUrl")?.value.trim();
      if (!name || !url) return;
      pressSources.push({ name, homepage_url: url });
      document.getElementById("pressName").value = "";
      document.getElementById("pressUrl").value = "";
      renderPressList();
    });

    document.getElementById("setEventIntel")?.addEventListener("change", (e) => {
      if (e.target.checked) {
        const ok = confirm(
          "Phân cụm sự kiện (AI) tải model nặng, quét chậm và dễ lỗi.\n\nBật anyway?"
        );
        if (!ok) e.target.checked = false;
      }
    });

    document.getElementById("setFilterChinhThong")?.addEventListener("change", () => {
      saveFilterChinhThongImmediate().catch((e) => {
        alert(e.message || String(e));
        loadSettings().catch(() => {});
      });
    });

    document.getElementById("btnSaveSettings")?.addEventListener("click", () => {
      saveSettings().catch((e) => alert(e.message || String(e)));
    });

    document.getElementById("btnTelegramTest")?.addEventListener("click", () => {
      testTelegram().catch((e) => alert(e.message || String(e)));
    });

    document.getElementById("btnClearData")?.addEventListener("click", () => {
      clearSelectedData().catch((e) => alert(e.message || String(e)));
    });

    document.querySelectorAll('input[name="clrTimeRange"]').forEach((el) => {
      el.addEventListener("change", () => {
        loadDataStats().catch(() => {
          const line = document.getElementById("dataStatsLine");
          if (line) line.textContent = "Không tải được thống kê dữ liệu";
        });
      });
    });

    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape") closeModal();
    });
  }

  document.addEventListener("DOMContentLoaded", () => {
    initSettings();
  });
})();
