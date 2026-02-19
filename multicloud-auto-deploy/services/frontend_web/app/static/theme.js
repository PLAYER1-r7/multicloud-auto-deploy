(function () {
  const toggle = document.getElementById("theme-toggle");
  const root = document.documentElement;
  const storageKey = "theme";
  const media = window.matchMedia ? window.matchMedia("(prefers-color-scheme: dark)") : null;

  function resolveTheme() {
    const saved = localStorage.getItem(storageKey);
    if (saved === "dark" || saved === "light") {
      return saved;
    }
    if (media && media.matches) {
      return "dark";
    }
    return "light";
  }

  function applyTheme(theme) {
    root.setAttribute("data-theme", theme);
    if (toggle) {
      const isDark = theme === "dark";
      toggle.setAttribute("aria-pressed", String(isDark));
      toggle.setAttribute("aria-label", isDark ? "Switch to light" : "Switch to dark");
    }
  }

  applyTheme(resolveTheme());

  if (toggle) {
    toggle.addEventListener("click", () => {
      const nextTheme = root.getAttribute("data-theme") === "dark" ? "light" : "dark";
      localStorage.setItem(storageKey, nextTheme);
      applyTheme(nextTheme);
    });
  }

  if (media) {
    media.addEventListener("change", (event) => {
      if (localStorage.getItem(storageKey)) {
        return;
      }
      applyTheme(event.matches ? "dark" : "light");
    });
  }
})();
