// ---------- Loader ----------
function showLoader(msg) {
  const l = document.getElementById("loader");
  if (!l) return;
  document.getElementById("loader-text").textContent = msg || "Working…";
  l.classList.add("visible");
  l.setAttribute("aria-hidden", "false");
}
function hideLoader() {
  const l = document.getElementById("loader");
  if (!l) return;
  l.classList.remove("visible");
  l.setAttribute("aria-hidden", "true");
}

// ---------- Theme toggle ----------
(function initTheme() {
  const root = document.documentElement;
  const saved = localStorage.getItem("df-theme");
  if (saved) root.setAttribute("data-theme", saved);
  const btn = document.getElementById("theme-toggle");
  if (!btn) return;
  btn.addEventListener("click", () => {
    const current = root.getAttribute("data-theme") || "dark";
    const next = current === "dark" ? "light" : "dark";
    root.setAttribute("data-theme", next);
    localStorage.setItem("df-theme", next);
  });
})();

// ---------- Flash toast ----------
function flash(msg, type) {
  const d = document.createElement("div");
  d.className = `flash ${type || "success"}`;
  d.textContent = msg;
  const main = document.querySelector("main.container");
  if (main) main.prepend(d);
  setTimeout(() => d.remove(), 4000);
}

// ---------- Plotly config (shared) ----------
window.PLOTLY_CONFIG = {
  responsive: true,
  displaylogo: false,
  modeBarButtonsToRemove: ["lasso2d", "select2d"],
  toImageButtonOptions: {
    format: "png", filename: "dataforge-chart",
    height: 800, width: 1400, scale: 2
  }
};

// ---------- Auto loader on plain link clicks ----------
document.addEventListener("click", (e) => {
  const a = e.target.closest("a");
  if (!a) return;

  // Never trigger loader for Plotly modebar buttons
  if (a.closest(".modebar")) return;

  // Browser-native downloads
  if (a.target === "_blank") return;
  if (a.hasAttribute("download")) return;
  if (a.dataset.noLoader !== undefined) return;

  const href = a.getAttribute("href") || "";
  if (!href) return;                          
  if (href.startsWith("#")) return;
  if (href.startsWith("mailto:")) return;
  if (href.startsWith("javascript:")) return;
  if (href.startsWith("/api/export/")) return;   

  showLoader("Loading…");
});

function exportPipeline() {
  showLoader("Generating pipeline file…");
  window.location.href = "/api/pipeline/export";
  setTimeout(hideLoader, 800);
}

function previewPipeline() {
  fetch("/api/pipeline/preview", { method: "POST" })
    .then(r => r.json())
    .then(d => {
      const el = document.getElementById("pipeline-preview");
      if (!d.recipe) { alert("Run preprocessing first."); return; }
      el.textContent = d.yaml;
      el.style.display = "block";
    });
}
