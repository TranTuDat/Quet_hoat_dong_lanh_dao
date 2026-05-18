/* Bảng giám sát — đối tượng & tín hiệu */

function escapeHtml(s) {
  return String(s ?? "").replace(/[&<>"']/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c])
  );
}

function cfgTargets() {
  return window.__CFG_TARGETS__ || [];
}

function editingTarget() {
  return window.__EDITING_TARGET__ || null;
}

async function postJson(url, body) {
  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  const text = await res.text();
  let data;
  try {
    data = JSON.parse(text);
  } catch {
    throw new Error(
      res.status === 404
        ? "Máy chủ chưa cập nhật. Dừng Test.py (Ctrl+C) rồi chạy lại: python Test.py"
        : "Không đọc được phản hồi từ máy chủ"
    );
  }
  if (!res.ok || data.success === false) {
    throw new Error(data.error || "Lỗi " + res.status);
  }
  return data;
}

function flashStatus(msg, ok = true) {
  const statusLine = document.getElementById("statusLine");
  if (!statusLine) return;
  statusLine.textContent = msg;
  statusLine.classList.toggle("live", ok);
}

function setEditMode(originalName, displayName, position, idx) {
  window.__EDITING_TARGET__ = originalName || null;
  const hint = document.getElementById("editHint");
  const hintText = document.getElementById("editHintText");
  const btnLabel = document.getElementById("btnTargetLabel");
  const btnIcon = document.getElementById("btnTargetIcon");
  const btnCancel = document.getElementById("btnCancelEdit");
  const btnAdd = document.getElementById("btnAddTarget");
  const formActions = document.getElementById("targetFormActions");
  const nameInp = document.getElementById("targetName");
  const posInp = document.getElementById("targetPos");

  if (originalName) {
    nameInp.value = displayName || originalName;
    posInp.value = position || "";
    hint?.classList.add("visible");
    if (hintText) hintText.textContent = "Đang sửa: " + originalName;
    if (btnLabel) btnLabel.textContent = "Lưu";
    if (btnIcon) btnIcon.setAttribute("data-lucide", "save");
    if (btnCancel) btnCancel.style.display = "inline-flex";
    if (btnAdd) btnAdd.style.gridColumn = "";
    if (formActions) formActions.style.gridTemplateColumns = "1fr 1fr";
    document.querySelectorAll(".t-item").forEach((el, i) => {
      el.classList.toggle("editing", i === idx);
    });
  } else {
    nameInp.value = "";
    posInp.value = "";
    hint?.classList.remove("visible");
    if (btnLabel) btnLabel.textContent = "Thêm";
    if (btnIcon) btnIcon.setAttribute("data-lucide", "plus");
    if (btnCancel) btnCancel.style.display = "none";
    if (btnAdd) btnAdd.style.gridColumn = "1 / -1";
    if (formActions) formActions.style.gridTemplateColumns = "";
    document.querySelectorAll(".t-item").forEach((el) => el.classList.remove("editing"));
  }
  if (window.lucide) lucide.createIcons();
}

function startEditTarget(idx) {
  const t = cfgTargets()[idx];
  if (!t) return;
  setEditMode(t.name || "", t.name || "", t.position || "", idx);
  document.getElementById("targetName")?.focus();
}

function initials(name) {
  const p = String(name || "")
    .trim()
    .split(/\s+/)
    .filter(Boolean);
  if (!p.length) return "?";
  if (p.length === 1) return p[0].slice(0, 2).toUpperCase();
  return (p[0][0] + p[p.length - 1][0]).toUpperCase();
}

function parseHoursRange() {
  const raw = (document.getElementById("hoursRangeInput")?.value ?? "")
    .toString()
    .trim();
  if (!raw) return 24;
  const v = Number(raw.replace(",", "."));
  return Number.isFinite(v) && v > 0 ? v : 24;
}

function statusChipClass(status) {
  if (status === "change") return "status-chip warn";
  if (status === "stable_activity") return "status-chip ok";
  return "status-chip neutral";
}

function statusLabel(status) {
  if (status === "change") return "Biến động CV";
  if (status === "stable_activity") return "Có hoạt động";
  if (status === "low_signal") return "Tín hiệu yếu";
  if (status === "no_data") return "Chưa có tin";
  return "—";
}

function formatTimeline(iso) {
  if (!iso) return "";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "";
  const diff = (Date.now() - d.getTime()) / 1000;
  if (diff < 3600) return `${Math.max(1, Math.floor(diff / 60))} phút trước`;
  if (diff < 86400) return `${Math.floor(diff / 3600)} giờ trước`;
  return d.toLocaleString("vi-VN", {
    day: "2-digit",
    month: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function renderTargets(cfg) {
  const targetsList = document.getElementById("targetsList");
  const targets = cfg.targets || [];
  targetsList.innerHTML = "";
  if (!targets.length) {
    targetsList.innerHTML =
      '<div class="empty" title="Thêm đối tượng bên trên"><i data-lucide="users"></i>Chưa có</div>';
    if (window.lucide) lucide.createIcons();
    return;
  }
  const hours = parseHoursRange();
  targets.forEach((t, idx) => {
    const name = t.name || "";
    const pos = t.position || "";
    const href =
      "/target?name=" +
      encodeURIComponent(name) +
      "&hours=" +
      encodeURIComponent(String(hours));
    const div = document.createElement("div");
    div.className = "t-item";
    div.innerHTML = `
      <div class="avatar">${escapeHtml(initials(name))}</div>
      <div>
        <div class="t-name">${escapeHtml(name)}</div>
        ${pos ? `<div class="t-pos">${escapeHtml(pos)}</div>` : ""}
      </div>
      <div class="t-ops">
        <button type="button" class="btn btn-glass btn-icon" data-edit="${idx}" title="Sửa">
          <i data-lucide="pencil"></i>
        </button>
        <a class="btn btn-glass btn-icon" href="${escapeHtml(href)}" title="Xem chi tiết">
          <i data-lucide="arrow-right"></i>
        </a>
        <button type="button" class="btn btn-danger btn-icon" data-del="${idx}" title="Xóa">
          <i data-lucide="trash-2"></i>
        </button>
      </div>`;
    targetsList.appendChild(div);
  });
  targetsList.querySelectorAll("button[data-edit]").forEach((btn) => {
    btn.addEventListener("click", (e) => {
      e.stopPropagation();
      startEditTarget(Number(btn.getAttribute("data-edit")));
    });
  });
  targetsList.querySelectorAll("button[data-del]").forEach((btn) => {
    btn.addEventListener("click", async (e) => {
      e.stopPropagation();
      const name =
        cfgTargets()[Number(btn.getAttribute("data-del"))]?.name || "";
      if (!confirm("Xóa đối tượng \"" + name + "\"?")) return;
      try {
        await postJson("/config/targets/delete", { name });
        if (editingTarget() === name) setEditMode(null);
        flashStatus("Đã xóa", true);
        await loadAll();
      } catch (err) {
        alert(err.message || String(err));
      }
    });
  });
  if (window.lucide) lucide.createIcons();
}

function renderSummaries(summaries) {
  const summariesList = document.getElementById("summariesList");
  summariesList.innerHTML = "";
  if (!summaries?.length) {
    summariesList.innerHTML =
      '<div class="empty" title="Bấm Quét để thu thập tin"><i data-lucide="radio"></i>Chưa có tín hiệu</div>';
    if (window.lucide) lucide.createIcons();
    return;
  }
  const hours = parseHoursRange();
  summaries.forEach((s) => {
    const name = s.target_name || "";
    const href =
      "/target?name=" +
      encodeURIComponent(name) +
      "&hours=" +
      encodeURIComponent(String(hours));
    const nHd = s.activity_count ?? 0;
    const nCv = s.change_count ?? 0;
    const snippet = (s.headline || s.digest_short || "").trim().split("\n")[0];
    const timeLbl = formatTimeline(s.latest_timestamp);
    const isNew = !!s.is_new;

    const card = document.createElement("article");
    card.className = "activity-card";
    card.dataset.status = s.status || "";
    card.innerHTML = `
      <div class="card-glow"></div>
      <div class="card-inner">
        <div class="card-top">
          <div class="card-title-area">
            <h3>${escapeHtml(name)}</h3>
            ${isNew ? '<span class="badge-new">Mới</span>' : ""}
          </div>
          <span class="${statusChipClass(s.status)}">${escapeHtml(statusLabel(s.status))}</span>
        </div>
        <div class="card-metrics">
          <span class="metric-pill hd">Hoạt động <b>${nHd}</b></span>
          <span class="metric-pill cv">Chức vụ <b>${nCv}</b></span>
        </div>
        ${snippet ? `<p class="card-snippet">${escapeHtml(snippet)}</p>` : ""}
        ${timeLbl ? `<div class="card-meta"><span><i data-lucide="clock"></i> ${escapeHtml(timeLbl)}</span></div>` : ""}
        <div class="card-actions">
          <a class="btn btn-glass btn-sm" href="${escapeHtml(href)}">
            <i data-lucide="arrow-right"></i> Chi tiết
          </a>
        </div>
      </div>`;

    card.querySelector(".card-inner")?.addEventListener("click", (e) => {
      if (e.target.closest("a")) return;
      location.href = href;
    });

    summariesList.appendChild(card);
  });
  if (window.lucide) lucide.createIcons();
}

async function loadAll() {
  flashStatus("Đang tải…", false);
  const hours = parseHoursRange();
  const [cfgRes, sumRes] = await Promise.all([
    fetch("/config"),
    fetch("/api/targets/summary?hours=" + encodeURIComponent(String(hours))),
  ]);
  const cfg = await cfgRes.json();
  const sumData = await sumRes.json();
  if (cfg.success === false) throw new Error(cfg.error || "Lỗi tải cấu hình");
  if (sumData.success === false) throw new Error(sumData.error || "Lỗi tải tín hiệu");
  window.__CFG_TARGETS__ = cfg.config.targets || [];
  renderTargets(cfg.config);
  renderSummaries(sumData.summaries || []);
  const n = (cfg.config.targets || []).length;
  const applied =
    sumData.hours_requested != null ? sumData.hours_requested : hours;
  flashStatus(`${n} đối tượng · hiển thị ${applied} giờ gần nhất`, true);
}

function initDashboard() {
  const btnRunNow = document.getElementById("btnRunNow");
  const runSpinner = document.getElementById("runSpinner");
  const btnRefresh = document.getElementById("btnRefresh");
  const targetName = document.getElementById("targetName");
  const targetPos = document.getElementById("targetPos");
  const btnAddTarget = document.getElementById("btnAddTarget");

  btnRunNow.addEventListener("click", async () => {
    try {
      btnRunNow.disabled = true;
      runSpinner.style.display = "inline-block";
      flashStatus("Đang quét…", false);
      const hours = parseHoursRange();
      const data = await postJson("/monitor/run", { scan_hours: hours });
      let msg = `Đã thêm ${data.processed_new || 0} tin`;
      if (data.skipped_history_dup > 0) {
        msg += ` · bỏ qua ${data.skipped_history_dup} tin trùng (đã quét)`;
      }
      if (data.telegram_enabled) {
        if (data.telegram_sent > 0) {
          msg += ` · Telegram: ${data.telegram_sent} tin`;
          if (data.telegram_sent_empty > 0) {
            msg += ` (${data.telegram_sent_empty} trống)`;
          }
        } else if (data.processed_new > 0 && data.telegram_errors?.length) {
          msg += ` · Telegram lỗi: ${data.telegram_errors[0]}`;
        } else if (data.processed_new === 0) {
          msg += ` · không có tin mới (URL đã quét trước — Telegram chỉ gửi khi có tin mới)`;
        } else if (data.telegram_skipped_dup > 0) {
          msg += ` · Telegram: tin đã gửi trước đó`;
        }
      }
      flashStatus(msg, true);
      await loadAll();
    } catch (e) {
      flashStatus(e?.message || String(e), false);
      alert(e?.message || String(e));
    } finally {
      runSpinner.style.display = "none";
      btnRunNow.disabled = false;
    }
  });

  btnRefresh.addEventListener("click", () =>
    loadAll().catch((e) => {
      flashStatus(e?.message || String(e), false);
    })
  );

  document.getElementById("btnCancelEdit")?.addEventListener("click", () => {
    setEditMode(null);
    flashStatus("Đã hủy sửa", true);
  });

  btnAddTarget.addEventListener("click", async () => {
    const name = targetName.value.trim();
    const pos = targetPos.value.trim();
    if (!name) {
      targetName.focus();
      return;
    }
    const original = editingTarget();
    const body = original
      ? { name, position: pos, original_name: original }
      : { name, position: pos };
    try {
      btnAddTarget.disabled = true;
      await postJson("/config/targets/add", body);
      setEditMode(null);
      flashStatus("Đã lưu vào hệ thống", true);
      await loadAll();
    } catch (e) {
      alert(e.message || String(e));
    } finally {
      btnAddTarget.disabled = false;
    }
  });

  function applyHoursFilter() {
    loadAll().catch((e) => {
      flashStatus(e?.message || String(e), false);
    });
  }

  document.getElementById("btnApplyHours")?.addEventListener("click", applyHoursFilter);
  document.getElementById("hoursRangeInput")?.addEventListener("keydown", (e) => {
    if (e.key === "Enter") {
      e.preventDefault();
      applyHoursFilter();
    }
  });
  document.getElementById("hoursRangeInput")?.addEventListener("change", applyHoursFilter);

  loadAll().catch((e) => {
    flashStatus(e?.message || String(e), false);
  });
}

window.flashStatus = flashStatus;

document.addEventListener("DOMContentLoaded", () => {
  if (window.lucide) lucide.createIcons();
  initDashboard();
});
