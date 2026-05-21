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

function updateTargetScopeMeta(targetCount, hours) {
  const el = document.getElementById("targetScopeMeta");
  if (!el) return;
  const n = Number(targetCount);
  const h = Number(hours);
  const nLabel = Number.isFinite(n) && n >= 0 ? `${n} đối tượng` : "— đối tượng";
  const hLabel =
    Number.isFinite(h) && h > 0 ? `hiển thị ${h} giờ gần nhất` : "hiển thị — giờ gần nhất";
  el.textContent = `${nLabel} · ${hLabel}`;
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

function normalizeSearchText(s) {
  return String(s ?? "")
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase()
    .trim();
}

function getTargetSearchQuery() {
  return normalizeSearchText(document.getElementById("targetSearchInput")?.value);
}

function positionForTargetName(name) {
  const n = String(name || "").trim();
  const hit = (cfgTargets() || []).find((t) => String(t?.name || "").trim() === n);
  return String(hit?.position || "").trim();
}

function matchesTargetSearch(name, position, snippet, q) {
  if (!q) return true;
  const n = normalizeSearchText(name);
  const p = normalizeSearchText(position);
  const s = normalizeSearchText(snippet);
  return n.includes(q) || p.includes(q) || s.includes(q);
}

function applyTargetSearch() {
  const q = getTargetSearchQuery();
  const clearBtn = document.getElementById("targetSearchClear");
  const hint = document.getElementById("targetSearchHint");
  if (clearBtn) clearBtn.hidden = !q;

  let visTargets = 0;
  let totalTargets = 0;
  document.querySelectorAll("#targetsList .t-item").forEach((el) => {
    totalTargets += 1;
    const name = el.querySelector(".t-name")?.textContent || "";
    const pos = el.querySelector(".t-pos")?.textContent || "";
    const ok = matchesTargetSearch(name, pos, "", q);
    el.classList.toggle("is-filtered-out", !ok);
    if (ok) visTargets += 1;
  });

  const targetsEmpty = document.getElementById("targetsFilterEmpty");
  if (targetsEmpty) {
    targetsEmpty.hidden = !q || visTargets > 0 || totalTargets === 0;
  }

  let visCards = 0;
  let totalCards = 0;
  document.querySelectorAll("#summariesList .activity-card").forEach((el) => {
    totalCards += 1;
    const name = el.dataset.targetName || "";
    const pos = el.dataset.targetPosition || "";
    const snippet = el.dataset.targetSnippet || "";
    const ok = matchesTargetSearch(name, pos, snippet, q);
    el.classList.toggle("is-filtered-out", !ok);
    if (ok) visCards += 1;
  });

  const sumEmpty = document.getElementById("summariesFilterEmpty");
  if (sumEmpty) {
    sumEmpty.hidden = !q || visCards > 0 || totalCards === 0;
  }

  document.querySelectorAll("#recentFeedBody .feed-item").forEach((el) => {
    const name = el.dataset.targetName || "";
    const pos = positionForTargetName(name);
    const snippet = el.querySelector(".fi-meta")?.textContent || "";
    const ok = matchesTargetSearch(name, pos, snippet, q);
    el.classList.toggle("is-filtered-out", !ok);
  });

  if (hint) {
    if (!q) {
      hint.hidden = true;
      hint.textContent = "";
    } else {
      hint.hidden = false;
      const parts = [];
      if (visTargets !== totalTargets) parts.push(`${visTargets}/${totalTargets} ĐT`);
      if (totalCards && visCards !== totalCards) parts.push(`${visCards}/${totalCards} thẻ`);
      hint.textContent = parts.length ? parts.join(" · ") : "0 kết quả";
    }
  }
}

function initTargetSearch() {
  const inp = document.getElementById("targetSearchInput");
  const clearBtn = document.getElementById("targetSearchClear");
  if (!inp) return;

  let debounce = null;
  const refresh = () => applyTargetSearch();

  inp.addEventListener("input", () => {
    clearTimeout(debounce);
    debounce = setTimeout(refresh, 120);
  });
  inp.addEventListener("keydown", (e) => {
    if (e.key === "Escape") {
      inp.value = "";
      refresh();
      inp.blur();
    }
  });
  clearBtn?.addEventListener("click", () => {
    inp.value = "";
    inp.focus();
    refresh();
  });
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

function formatDateTime(iso) {
  if (!iso) return "—";
  const d = new Date(String(iso).replace(" ", "T"));
  if (Number.isNaN(d.getTime())) return String(iso || "—");
  return d.toLocaleString("vi-VN", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
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
    div.dataset.targetName = name;
    div.dataset.targetPosition = pos;
    div.innerHTML = `
      <div class="avatar">${escapeHtml(initials(name))}</div>
      <div>
        <div class="t-name">${escapeHtml(name)}</div>
        ${pos ? `<div class="t-pos">${escapeHtml(pos)}</div>` : ""}
      </div>
      <div class="t-ops">
        <button type="button" class="btn btn-glass btn-icon btn-scan-target" data-scan-target="${escapeHtml(name)}" title="Quét riêng đối tượng này (không quét các đối tượng khác)">
          <i data-lucide="play"></i>
        </button>
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
  targetsList.querySelectorAll("button[data-scan-target]").forEach((btn) => {
    btn.addEventListener("click", (e) => {
      e.stopPropagation();
      if (isScanLocked()) return;
      const name = btn.getAttribute("data-scan-target") || "";
      if (name) runMonitorScan({ targetName: name });
    });
  });
  applyScanLockUi();
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
  applyTargetSearch();
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
    const pos = positionForTargetName(name);
    const card = document.createElement("article");
    card.className = "activity-card";
    card.dataset.status = s.status || "";
    card.dataset.targetName = name;
    card.dataset.targetPosition = pos;
    card.dataset.targetSnippet = snippet;
    card.innerHTML = `
      <div class="card-glow"></div>
      <div class="card-inner">
        <div class="card-top">
          <div class="card-title-area">
            <h3>${escapeHtml(name)}</h3>
            ${pos ? `<p class="card-sub-pos">${escapeHtml(pos)}</p>` : ""}
          </div>
          <span class="${statusChipClass(s.status)}">${escapeHtml(statusLabel(s.status))}</span>
        </div>
        <div class="card-metrics">
          <span class="metric-pill hd">Hoạt động <b>${nHd}</b></span>
          <span class="metric-pill cv">Chức vụ <b>${nCv}</b></span>
        </div>
        ${snippet ? `<p class="card-snippet">${escapeHtml(snippet)}</p>` : ""}
        <div class="card-actions">
          <button type="button" class="btn btn-glass btn-sm btn-scan-target" data-scan-target="${escapeHtml(name)}" title="Quét riêng đối tượng này (không quét các đối tượng khác)">
            <i data-lucide="play"></i> Quét riêng
          </button>
          <a class="btn btn-glass btn-sm" href="${escapeHtml(href)}">
            <i data-lucide="arrow-right"></i> Chi tiết
          </a>
        </div>
      </div>`;

    card.querySelector(".card-inner")?.addEventListener("click", (e) => {
      if (e.target.closest("a, button")) return;
      location.href = href;
    });

    card.querySelector("button[data-scan-target]")?.addEventListener("click", (e) => {
      e.stopPropagation();
      if (isScanLocked()) return;
      runMonitorScan({ targetName: name });
    });

    summariesList.appendChild(card);
  });
  applyScanLockUi();
  if (window.lucide) lucide.createIcons();
  applyTargetSearch();
}

function parseRecordTime(iso) {
  if (!iso) return 0;
  const d = new Date(String(iso).replace(" ", "T"));
  return Number.isNaN(d.getTime()) ? 0 : d.getTime();
}

function articleUrl(row) {
  const resolved = String(row?.resolved_url || "").trim();
  const url = String(row?.url || "").trim();
  return resolved.startsWith("http") ? resolved : url;
}

function buildRecentFeed(notifs, hours, limit = 10) {
  const cutoff = Date.now() - hours * 3600000;
  const seen = new Set();
  const rows = [];
  // Trùng URL: ưu tiên kênh biến động (giống quét GNews — biendong thắng hoatdong)
  for (const ch of ["channel_biendong", "channel_hoatdong"]) {
    for (const r of notifs?.[ch] || []) {
      if (!r || typeof r !== "object") continue;
      const ts = parseRecordTime(r.timestamp);
      if (ts && ts < cutoff) continue;
      const key = `${r.target_name || ""}|${articleUrl(r)}`;
      if (!key || seen.has(key)) continue;
      seen.add(key);
      rows.push({ ...r, _ts: ts || 0, _channel: ch });
    }
  }
  rows.sort((a, b) => b._ts - a._ts);
  return rows.slice(0, limit);
}

function renderKpiRow(summaries) {
  const list = summaries || [];
  let nChange = 0;
  let nAct = 0;
  for (const s of list) {
    if (s.status === "change") nChange += 1;
    if ((s.activity_count || 0) > 0) nAct += 1;
  }
  return `
    <div class="side-kpi-row side-kpi-row-3">
      <div class="side-kpi"><b>${list.length}</b><span>Đối tượng</span></div>
      <div class="side-kpi"><b>${nChange}</b><span>Biến động</span></div>
      <div class="side-kpi"><b>${nAct}</b><span>Có hoạt động</span></div>
    </div>`;
}

function renderSystemPanel(st, settings) {
  const el = document.getElementById("systemPanelBody");
  if (!el) return;
  const tgOn = !!settings?.enabled;
  const scanning = !!st?.is_scanning;
  const autoOn =
    settings?.auto_scan_enabled !== undefined
      ? !!settings.auto_scan_enabled
      : st?.enabled !== false;
  const intervalMin =
    settings?.scan_interval_minutes ?? st?.interval_minutes ?? "—";

  let scanVal = "—";
  if (st?.last_scan_at) {
    scanVal = formatDateTime(st.last_scan_at);
    if (st.last_processed_new > 0) scanVal += ` (+${st.last_processed_new} tin)`;
  }

  const errMsg = st?.last_scan_ok === false && st?.last_error ? st.last_error : "";
  const warnMsg =
    st?.last_warning ||
    (st?.last_ai_error_count > 0 && st?.last_scan_ok !== false
      ? `AI lỗi ${st.last_ai_error_count} bài (xem terminal)`
      : "");

  el.innerHTML =
    renderKpiRow(window.__LAST_SUMMARIES__ || []) +
    `
    <div class="sys-row"><span class="lbl">Chế độ quét</span><span class="val ok">${escapeHtml(st?.ai_scan_mode_label || settings?.ai_scan_mode_label || "—")}</span></div>
    <div class="sys-row"><span class="lbl">Áp dụng</span><span class="val">Quét thủ công + quét tự động (config)</span></div>
    <div class="sys-row"><span class="lbl">Quét tự động</span><span class="val ${autoOn ? "ok" : ""}">${autoOn ? "Bật" : "Tắt"}</span></div>
    <div class="sys-row"><span class="lbl">Chu kỳ</span><span class="val">${intervalMin} phút</span></div>
    <div class="sys-row"><span class="lbl">Trạng thái</span><span class="val ${scanning ? "busy" : st?.last_scan_ok === false ? "warn" : "ok"}">${scanning ? "Đang quét" : st?.last_scan_ok === false ? "Lỗi" : "Chờ"}</span></div>
    <div class="sys-row"><span class="lbl">Lần quét cuối</span><span class="val">${escapeHtml(scanVal)}${st?.last_scan_source ? ` · ${escapeHtml(st.last_scan_source === "auto" ? "tự động" : "thủ công")}` : ""}</span></div>
    ${errMsg ? `<div class="sys-row"><span class="lbl">Lỗi</span><span class="val warn">${escapeHtml(errMsg)}</span></div>` : ""}
    ${warnMsg && !errMsg ? `<div class="sys-row"><span class="lbl">Cảnh báo</span><span class="val warn">${escapeHtml(warnMsg)}</span></div>` : ""}
    ${st?.thread_alive === false && autoOn ? `<div class="sys-row"><span class="lbl">Thread nền</span><span class="val warn">Đã dừng — hệ thống đang thử khởi động lại</span></div>` : ""}
    <div class="sys-row"><span class="lbl">Telegram</span><span class="val ${tgOn ? "ok" : ""}">${tgOn ? "Bật" : "Tắt"}</span></div>
  `;
}

function renderRecentFeed(notifs, hours) {
  const el = document.getElementById("recentFeedBody");
  if (!el) return;
  const rows = buildRecentFeed(notifs, hours, 10);
  if (!rows.length) {
    el.innerHTML = '<p class="side-empty">Chưa có tin trong cửa sổ thời gian.</p>';
    return;
  }
  el.innerHTML = rows
    .map((r) => {
      const name = r.target_name || "";
      const title = String(r.title || "").trim() || "(Không có tiêu đề)";
      const link = articleUrl(r);
      const ai = r.ai_result && typeof r.ai_result === "object" ? r.ai_result : {};
      const summary = String(ai.Summary || "").trim();
      const press = r.press_name || "";
      const when = formatTimeline(r.timestamp) || "";
      const isRole =
        r._channel === "channel_biendong" ||
        (ai.Is_Change && ai.Matched_Target);
      const kind = isRole ? "Biến động chức vụ" : "Hoạt động";
      return `
        <article class="feed-item" data-target-name="${escapeHtml(name)}">
          <div class="fi-top">
            <span class="fi-target">${escapeHtml(name)}</span>
            <span class="fi-time">${escapeHtml(when)}${when ? " · " : ""}${escapeHtml(kind)}</span>
          </div>
          <div class="fi-title">${link ? `<a href="${escapeHtml(link)}" target="_blank" rel="noopener">${escapeHtml(title)}</a>` : escapeHtml(title)}</div>
          <div class="fi-meta">${escapeHtml(summary || press || "")}</div>
        </article>`;
    })
    .join("");
  applyTargetSearch();
}

async function loadAll() {
  flashStatus("Đang tải…", false);
  const hours = parseHoursRange();
  const [tgtRes, sumRes, notifRes, settingsRes, statusRes] = await Promise.all([
    fetch("/api/targets"),
    fetch("/api/targets/summary?hours=" + encodeURIComponent(String(hours))),
    fetch("/notifications"),
    fetch("/api/settings"),
    fetch("/api/monitor/status"),
  ]);
  const cfg = await tgtRes.json();
  const sumData = await sumRes.json();
  const notifData = await notifRes.json();
  const settingsData = await settingsRes.json();
  const statusData = await statusRes.json();
  if (statusData.success !== false) {
    setServerScanning(!!(statusData.status || {}).is_scanning);
  }
  if (cfg.success === false) throw new Error(cfg.error || "Lỗi tải đối tượng");
  if (sumData.success === false) throw new Error(sumData.error || "Lỗi tải tín hiệu");
  const targetList = { targets: cfg.targets || [] };
  window.__CFG_TARGETS__ = targetList.targets;
  window.__LAST_SUMMARIES__ = sumData.summaries || [];
  renderTargets(targetList);
  renderSummaries(window.__LAST_SUMMARIES__);
  const notifs = notifData.notifications || {};
  const settings = settingsData.settings || {};
  window.__LAST_SETTINGS__ = settings;
  renderSystemPanel(statusData.status || {}, settings);
  renderRecentFeed(notifs, hours);
  if (window.lucide) lucide.createIcons();
  if (window.initTheme) initTheme();
  const n = (cfg.targets || []).length;
  const applied =
    sumData.hours_requested != null ? sumData.hours_requested : hours;
  updateTargetScopeMeta(n, applied);
  if (!isScanLocked()) {
    flashStatus("Đã cập nhật", true);
  }
}

let lastKnownScanAt = null;
let uiRefreshTimer = null;
let scanBusy = false;
let serverScanning = false;

function isScanLocked() {
  return scanBusy || serverScanning;
}

function applyScanLockUi() {
  const locked = isScanLocked();
  document.body.classList.toggle("scan-in-progress", locked);

  const btnRunNow = document.getElementById("btnRunNow");
  const runSpinner = document.getElementById("runSpinner");
  if (btnRunNow) {
    btnRunNow.disabled = locked;
    btnRunNow.title = locked
      ? serverScanning
        ? "Đang quét — vui lòng đợi"
        : "Đang gửi yêu cầu quét…"
      : "Quét tất cả đối tượng trong danh sách";
  }
  if (runSpinner) {
    runSpinner.style.display = locked ? "inline-block" : "none";
  }

  document.querySelectorAll("[data-scan-target], .btn-scan-target").forEach((btn) => {
    btn.disabled = locked;
    btn.title = locked
      ? "Đang quét — vui lòng đợi"
      : "Quét riêng đối tượng này (không quét các đối tượng khác)";
    btn.classList.remove("scanning");
  });
}

function setServerScanning(active) {
  serverScanning = !!active;
  applyScanLockUi();
}

function formatScanResultMessage(data, targetName) {
  const who = targetName ? ` · ${targetName}` : "";
  let msg = `Đã thêm ${data.processed_new || 0} tin${who}`;
  if (data.scan_ai_mode_label) {
    msg += " · " + data.scan_ai_mode_label;
  } else if (data.scan_use_ai === false) {
    msg += " · không dùng Gemini";
  }
  if (data.skipped_history_dup > 0) {
    msg += ` · bỏ qua ${data.skipped_history_dup} tin đã lưu/trùng`;
  }
  if (data.skipped_whitelist > 0) {
    msg += ` · ${data.skipped_whitelist} bài ngoài báo chính thống`;
  }
  if (
    (data.processed_new || 0) === 0 &&
    data.scan_use_ai === false &&
    (data.skipped_history_dup || 0) === 0 &&
    (data.skipped_whitelist || 0) === 0
  ) {
    msg += " · không có bài mới từ Google News/RSS (thử tắt «Chỉ báo chính thống» trên hiển thị hoặc quét lại sau)";
  }
  if (data.telegram_enabled) {
    if (data.telegram_sent > 0) {
      msg += ` · Telegram: ${data.telegram_sent} tin nhắn`;
      if (data.telegram_sent_empty > 0) {
        msg += ` (${data.telegram_sent_empty} đối tượng trống)`;
      }
    } else if (data.processed_new > 0 && data.telegram_errors?.length) {
      msg += ` · Telegram lỗi: ${data.telegram_errors[0]}`;
    } else if (data.processed_new === 0) {
      msg += ` · không có tin mới (URL đã quét trước — Telegram chỉ gửi khi có tin mới)`;
    } else if (data.telegram_skipped_dup > 0) {
      msg += ` · Telegram: tin đã gửi trước đó`;
    }
  }
  if (data.ai_error_count > 0) {
    msg += ` · AI lỗi ${data.ai_error_count} bài`;
    const first = (data.ai_errors || [])[0] || "";
    if (/leaked|403|api key/i.test(first)) {
      msg += " — cần đổi Gemini API key trong config.json";
    }
  }
  return msg;
}

async function waitForScanComplete(maxMs = 900000) {
  const start = Date.now();
  while (Date.now() - start < maxMs) {
    const res = await fetch("/api/monitor/status");
    const data = await res.json();
    const st = data.status || {};
    setServerScanning(!!st.is_scanning);
    if (!st.is_scanning) return st;
    await new Promise((r) => setTimeout(r, 1500));
  }
  throw new Error("Quét quá lâu — xem log trong cửa sổ python He_thong.py");
}

function formatStatusScanMessage(st, targetName) {
  const who = targetName ? ` · ${targetName}` : "";
  const n = Number(st?.last_processed_new ?? 0);
  let msg = `Đã quét xong${who} — +${n} tin`;
  const label = st?.last_scan_summary?.scan_ai_mode_label;
  if (label) msg += ` · ${label}`;
  const tg = Number(st?.last_scan_summary?.telegram_sent ?? 0);
  if (tg > 0) msg += ` · Telegram: ${tg} tin nhắn`;
  if (st?.last_scan_ok === false && st?.last_error) {
    msg += ` · Lỗi: ${st.last_error}`;
  } else if (st?.last_warning) {
    msg += ` · ${st.last_warning}`;
  }
  return msg;
}

async function runMonitorScan({ targetName = null } = {}) {
  if (isScanLocked()) {
    return;
  }
  scanBusy = true;
  applyScanLockUi();
  try {
    const label = targetName ? `Đang quét: ${targetName}…` : "Đang quét tất cả…";
    flashStatus(label, false);
    const hours = parseHoursRange();
    const body = { scan_hours: hours, ignore_history: true };
    if (targetName) body.target_name = targetName;
    const data = await postJson("/monitor/run", body);
    if (data.started) {
      setServerScanning(true);
      const st = await waitForScanComplete();
      flashStatus(formatStatusScanMessage(st, targetName), st?.last_scan_ok !== false);
      await loadAll();
      return;
    }
    flashStatus(formatScanResultMessage(data, targetName), true);
    await loadAll();
  } catch (e) {
    flashStatus(e?.message || String(e), false);
    alert(e?.message || String(e));
  } finally {
    scanBusy = false;
    applyScanLockUi();
  }
}

window.runMonitorScan = runMonitorScan;
window.isScanLocked = isScanLocked;

function formatAutoScanStatus(st) {
  if (!st) return "—";
  if (st.is_scanning) return "Đang quét nền…";
  if (!st.enabled) return "Quét tự động: tắt";
  const parts = [];
  if (st.last_scan_at) {
    const t = new Date(st.last_scan_at.replace(" ", "T"));
    const when = Number.isNaN(t.getTime())
      ? st.last_scan_at
      : t.toLocaleString("vi-VN", { hour: "2-digit", minute: "2-digit", day: "2-digit", month: "2-digit" });
    parts.push(`Thời điểm quét: ${when}`);
    if (st.last_processed_new > 0) parts.push(`+${st.last_processed_new} tin`);
  }
  if (st.next_scan_at && !st.is_scanning) {
    const n = new Date(st.next_scan_at.replace(" ", "T"));
    if (!Number.isNaN(n.getTime())) {
      const mins = Math.max(0, Math.round((n.getTime() - Date.now()) / 60000));
      parts.push(`Lần quét tiếp theo trong: ${mins} phút`);
    }
  }
  parts.push(`Chu kỳ: ${st.interval_minutes || "?"} phút/lần`);
  if (st.ai_scan_mode_label) parts.push(`Chế độ: ${st.ai_scan_mode_label}`);
  if (st.is_scanning) {
    return parts.filter((p) => !p.startsWith("Tiếp:")).join(" · ");
  }
  return parts.join(" · ");
}

async function pollMonitorStatus() {
  try {
    const res = await fetch("/api/monitor/status");
    const data = await res.json();
    if (!data.success) return;
    const st = data.status || {};
    setServerScanning(!!st.is_scanning);
    renderSystemPanel(st, window.__LAST_SETTINGS__ || {});

    const scanAt = st.last_scan_at || null;
    if (scanAt && scanAt !== lastKnownScanAt) {
      lastKnownScanAt = scanAt;
      if (!st.is_scanning) {
        await loadAll();
      }
    }
  } catch {
    /* bỏ qua lỗi mạng tạm */
  }
}

function startLiveRefresh(seconds) {
  if (uiRefreshTimer) clearInterval(uiRefreshTimer);
  const sec = Math.max(10, Math.min(120, Number(seconds) || 30));
  uiRefreshTimer = setInterval(() => {
    pollMonitorStatus();
  }, sec * 1000);
  pollMonitorStatus();
}

async function refreshDashboardData() {
  await loadAll();
  const sec = window.__LAST_SETTINGS__?.ui_refresh_seconds ?? 30;
  startLiveRefresh(sec);
}

window.refreshDashboardData = refreshDashboardData;
window.applySettingsSaved = refreshDashboardData;

function initDashboard() {
  const btnRunNow = document.getElementById("btnRunNow");
  const runSpinner = document.getElementById("runSpinner");
  const btnRefresh = document.getElementById("btnRefresh");
  const targetName = document.getElementById("targetName");
  const targetPos = document.getElementById("targetPos");
  const btnAddTarget = document.getElementById("btnAddTarget");

  btnRunNow.addEventListener("click", () => runMonitorScan());

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
    const h = parseHoursRange();
    updateTargetScopeMeta((cfgTargets() || []).length, h);
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

  initTargetSearch();

  loadAll()
    .then(() => {
      const sec = window.__LAST_SETTINGS__?.ui_refresh_seconds ?? 30;
      startLiveRefresh(sec);
    })
    .catch((e) => {
      flashStatus(e?.message || String(e), false);
    });
}

window.flashStatus = flashStatus;

document.addEventListener("DOMContentLoaded", () => {
  if (window.lucide) lucide.createIcons();
  initDashboard();
});
