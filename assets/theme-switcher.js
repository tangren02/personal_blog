(() => {
  const root = document.documentElement;
  const toggle = document.querySelector("[data-theme-toggle]");
  if (!toggle) return;

  const label = toggle.querySelector("[data-theme-label]");
  const glyph = toggle.querySelector("[data-theme-glyph]");

  const sync = () => {
    const isAurora = root.dataset.theme === "aurora";
    toggle.setAttribute("aria-pressed", String(isAurora));
    toggle.setAttribute("aria-label", isAurora ? "切换到亮色主题" : "切换到暗色主题");
    if (label) label.textContent = isAurora ? "亮色" : "暗色";
    if (glyph) glyph.textContent = isAurora ? "☼" : "◐";
  };

  toggle.addEventListener("click", () => {
    const next = root.dataset.theme === "aurora" ? "sky" : "aurora";
    root.dataset.theme = next;
    try { localStorage.setItem("personal-blog-theme", next); } catch (_) {}
    sync();
  });

  sync();
})();
