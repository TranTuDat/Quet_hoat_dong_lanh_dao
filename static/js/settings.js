/* Cài đặt hệ thống — modal */

(function () {
  let pressSources = [];

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

  async function loadSettings() {
    const res = await fetch("/api/settings");
    const data = await res.json();
    if (!data.success) throw new Error(data.error || "Không tải được cài đặt");

    const s = data.settings || {};
    document.getElementById("setFilterChinhThong").checked = !!s.filter_chinh_thong_only;
    document.getElementById("setMergeDup").checked = !!s.merge_duplicate_articles;
    document.getElementById("setEventIntel").checked = !!s.use_event_intelligence;
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
    document.getElementById("setTelegramToken").value = s.bot_token || "";
    document.getElementById("setTelegramChatId").value = s.chat_id || "";

    pressSources = (data.press_sources || []).map((p) => ({
      name: p.name || "",
      homepage_url: p.homepage_url || p.url || "",
      rss_url: p.rss_url || "",
    }));
    renderPressList();
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

  async function saveSettings() {
    const body = {
      filter_chinh_thong_only: document.getElementById("setFilterChinhThong").checked,
      merge_duplicate_articles: document.getElementById("setMergeDup").checked,
      use_event_intelligence: document.getElementById("setEventIntel").checked,
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
      bot_token: document.getElementById("setTelegramToken").value.trim(),
      chat_id: document.getElementById("setTelegramChatId").value.trim(),
      press_sources: pressSources,
    };

    const res = await fetch("/api/settings", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
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
    if (typeof window.applySettingsSaved === "function") {
      await window.applySettingsSaved();
    }
    if (typeof window.flashStatus === "function") {
      window.flashStatus("Đã lưu cài đặt hệ thống", true);
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

    document.getElementById("btnSaveSettings")?.addEventListener("click", () => {
      saveSettings().catch((e) => alert(e.message || String(e)));
    });

    document.getElementById("btnTelegramTest")?.addEventListener("click", () => {
      testTelegram().catch((e) => alert(e.message || String(e)));
    });

    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape") closeModal();
    });
  }

  document.addEventListener("DOMContentLoaded", () => {
    initSettings();
  });
})();
