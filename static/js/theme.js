/** Giao diện sáng / tối — dùng chung dashboard & trang chi tiết */

const THEME_KEY = "ui-theme";

function getTheme() {
  const t = localStorage.getItem(THEME_KEY);
  return t === "light" ? "light" : "dark";
}

function applyTheme(theme) {
  const next = theme === "light" ? "light" : "dark";
  document.documentElement.setAttribute("data-theme", next);
  localStorage.setItem(THEME_KEY, next);
  document.querySelectorAll("[data-theme-toggle]").forEach((btn) => {
    const icon = btn.querySelector("[data-theme-icon]");
    const label = btn.querySelector("[data-theme-label]");
    const isLight = next === "light";
    if (label) {
      label.textContent = isLight ? "Giao diện tối" : "Giao diện sáng";
    }
    if (icon) {
      icon.setAttribute("data-lucide", isLight ? "moon" : "sun");
    }
    btn.setAttribute(
      "title",
      isLight ? "Chuyển sang giao diện tối" : "Chuyển sang giao diện sáng"
    );
    btn.setAttribute("aria-pressed", isLight ? "true" : "false");
  });
  if (window.lucide) lucide.createIcons();
}

function toggleTheme() {
  applyTheme(getTheme() === "light" ? "dark" : "light");
}

function initTheme() {
  applyTheme(getTheme());
  document.querySelectorAll("[data-theme-toggle]").forEach((btn) => {
    if (btn.dataset.themeBound) return;
    btn.dataset.themeBound = "1";
    btn.addEventListener("click", toggleTheme);
  });
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", initTheme);
} else {
  initTheme();
}

window.initTheme = initTheme;
window.toggleTheme = toggleTheme;
