/* Assets Générator — frontend v2
 *
 * Two-tab UX:
 *  - Créer: 2 columns (icons | material cards with real preview PNGs),
 *    sticky bottom action bar with icon/material summary + format + button.
 *  - Galerie: full-width grid of all jobs (queued / in-progress / succeeded / failed),
 *    with status filters and click-to-open modal preview.
 *
 * Polling is auto-started/stopped based on whether anything is in flight.
 * Selections persist across queue submissions so the user can iterate quickly.
 */

const state = {
  selectedIcon: null,
  selectedMaterial: null,
  selectedMaterialLabel: null,
  selectedMaterialPreview: null,
  ratio: "1:1",
  size: 512,
  quality: "medium",
  jobs: [],
  galleryFilter: "all",
  concurrencyLimit: null,
  pollHandle: null,
  pollInterval: 1500,
  activeTab: "create",
};

const $ = (sel) => document.querySelector(sel);
const $$ = (sel) => document.querySelectorAll(sel);

// ---------- Init ----------
window.addEventListener("DOMContentLoaded", async () => {
  // Gate: if auth is enabled and we aren't authenticated, bounce to login.
  // We do this first so we never paint the app for a stranger.
  const me = await fetchMe();
  if (!me) return;  // redirect happened
  renderUser(me);

  await Promise.all([loadConfig(), loadMaterials(), refreshJobs()]);
  bindTabs();
  bindSearch();
  bindControls();
  bindGenerate();
  bindGalleryFilters();
  bindMisc();
  bindAuth();
  updateOutputLabel();
  ensurePolling();
});

async function fetchMe() {
  try {
    const r = await fetch("/api/me");
    if (r.status === 401) {
      location.href = "/login.html";
      return null;
    }
    return await r.json();
  } catch {
    // network error — let the app proceed; subsequent calls will fail too
    return { authenticated: true, auth_enabled: false };
  }
}

function renderUser(me) {
  if (!me?.auth_enabled) return;
  const chip = document.getElementById("user-chip");
  if (!chip) return;
  chip.classList.remove("hidden");
  const avatar = document.getElementById("user-avatar");
  const emailEl = document.getElementById("user-email");
  if (me.picture) avatar.src = me.picture;
  else avatar.style.display = "none";
  emailEl.textContent = me.email || "";
}

function bindAuth() {
  const btn = document.getElementById("logout-btn");
  if (!btn) return;
  btn.addEventListener("click", async () => {
    try {
      await fetch("/auth/logout", { method: "POST" });
    } catch {}
    location.href = "/login.html";
  });
}

// Wrap fetch to auto-redirect to login on 401 (session expired / revoked).
// This catches all the existing /api/* calls without touching them individually.
const _origFetch = window.fetch;
window.fetch = async function (...args) {
  const resp = await _origFetch.apply(this, args);
  if (resp.status === 401) {
    const url = typeof args[0] === "string" ? args[0] : args[0]?.url || "";
    // Don't loop on /api/me (handled separately) or auth endpoints.
    if (!url.startsWith("/auth/") && !url.endsWith("/api/me")) {
      location.href = "/login.html";
    }
  }
  return resp;
};

// ---------- Config ----------
async function loadConfig() {
  try {
    const r = await fetch("/api/config");
    const cfg = await r.json();
    state.concurrencyLimit = cfg.concurrency_limit;
    $("#meta-concurrency").textContent = `${cfg.concurrency_limit} parallèles`;
  } catch {
    $("#meta-concurrency").textContent = "—";
  }
}

// ---------- Tabs ----------
function bindTabs() {
  $$(".tab").forEach((tab) =>
    tab.addEventListener("click", () => switchTab(tab.dataset.tab)),
  );
}

function switchTab(tabName) {
  state.activeTab = tabName;
  $$(".tab").forEach((t) => t.classList.toggle("active", t.dataset.tab === tabName));
  $$(".tab-pane").forEach((p) => p.classList.toggle("active", p.dataset.pane === tabName));
}

// ---------- Materials ----------
async function loadMaterials() {
  try {
    const r = await fetch("/api/materials");
    const materials = await r.json();
    const grid = $("#material-grid");
    grid.innerHTML = "";
    for (const m of materials) {
      const card = document.createElement("button");
      card.className = "material-card";
      card.dataset.materialId = m.id;
      card.dataset.materialLabel = m.label;
      card.dataset.materialPreview = m.preview_url || "";
      card.title = m.description;
      const previewHtml = m.preview_url
        ? `<img src="${m.preview_url}" alt="${m.label}" loading="lazy">`
        : `<div class="placeholder-orb" style="background: ${m.swatch}"></div>`;
      card.innerHTML = `
        <div class="material-preview">${previewHtml}</div>
        <div class="material-label">${m.label}</div>
      `;
      card.addEventListener("click", () => selectMaterial(m));
      grid.appendChild(card);
    }
  } catch {
    toast("Impossible de charger les matériaux", "error");
  }
}

function selectMaterial(m) {
  state.selectedMaterial = m.id;
  state.selectedMaterialLabel = m.label;
  state.selectedMaterialPreview = m.preview_url;
  $$(".material-card").forEach((c) =>
    c.classList.toggle("selected", c.dataset.materialId === m.id),
  );
  // update summary in action bar
  const thumb = $("#sum-material");
  const value = $("#sum-material-value");
  if (m.preview_url) {
    thumb.innerHTML = `<img src="${m.preview_url}" alt="">`;
  } else {
    thumb.innerHTML = `<div class="placeholder-orb" style="background: ${m.swatch}"></div>`;
  }
  value.textContent = m.label;
  value.classList.remove("empty");
  updateGenerateButton();
}

// ---------- Search ----------
function bindSearch() {
  const input = $("#search-input");
  let timer = null;
  input.addEventListener("input", (e) => {
    clearTimeout(timer);
    timer = setTimeout(() => searchIcons(e.target.value), 280);
  });
  // Only search-suggestion chips (have data-q). The upload chip is handled separately.
  $$(".chip[data-q]").forEach((chip) =>
    chip.addEventListener("click", () => {
      input.value = chip.dataset.q;
      searchIcons(chip.dataset.q);
    }),
  );
  // Custom file upload
  const uploadBtn = $("#upload-btn");
  const uploadInput = $("#upload-input");
  if (uploadBtn && uploadInput) {
    uploadBtn.addEventListener("click", () => uploadInput.click());
    uploadInput.addEventListener("change", async (e) => {
      const file = e.target.files && e.target.files[0];
      if (file) await handleCustomUpload(file);
      e.target.value = ""; // allow re-selecting the same file
    });
  }
}

async function handleCustomUpload(file) {
  // 8 MB cap — matches the backend's /api/jobs limit
  if (file.size > 8 * 1024 * 1024) {
    toast("Fichier trop gros (max 8 MB)", "error");
    return;
  }
  const rawName = file.name.replace(/\.[^.]+$/, "").slice(0, 60);
  const safeName = rawName.replace(/[^a-zA-Z0-9-_]/g, "-").replace(/-+/g, "-").replace(/^-|-$/g, "") || "custom";
  try {
    const dataUrl = await new Promise((resolve, reject) => {
      const r = new FileReader();
      r.onload = () => resolve(r.result);
      r.onerror = () => reject(new Error("FileReader error"));
      r.readAsDataURL(file);
    });
    const customIcon = {
      id: `custom:${safeName}`,
      prefix: "custom",
      name: safeName,
      svg_url: dataUrl,        // used for thumbnail and to load into <img> when rasterising
      customDataUrl: dataUrl,
    };
    selectIcon(customIcon);
    toast(`Icône uploadée : ${file.name}`, "info");
  } catch (err) {
    toast(`Erreur d'upload : ${err.message}`, "error");
  }
}

async function searchIcons(query) {
  const q = (query || "").trim();
  const grid = $("#icon-grid");
  const status = $("#search-status");
  if (!q) {
    grid.innerHTML = `
      <div class="empty-state">
        <div class="empty-emoji">🔎</div>
        <div class="empty-text">Tape un terme pour rechercher.</div>
      </div>`;
    status.textContent = "";
    return;
  }
  status.textContent = "…";
  try {
    const r = await fetch(`/api/icons?q=${encodeURIComponent(q)}&limit=48`);
    if (!r.ok) throw new Error(`HTTP ${r.status}`);
    const data = await r.json();
    renderIcons(data.icons || []);
    status.textContent = `${(data.icons || []).length}`;
  } catch (e) {
    status.textContent = "";
    toast(`Erreur de recherche : ${e.message}`, "error");
  }
}

function renderIcons(icons) {
  const grid = $("#icon-grid");
  if (!icons.length) {
    grid.innerHTML = `
      <div class="empty-state">
        <div class="empty-emoji">🤷</div>
        <div class="empty-text">Aucun résultat.</div>
      </div>`;
    return;
  }
  grid.innerHTML = "";
  for (const ic of icons) {
    const card = document.createElement("button");
    card.className = "icon-card";
    card.dataset.iconId = ic.id;
    card.title = ic.id;
    card.innerHTML = `<img loading="lazy" src="${ic.svg_url}" alt="${ic.name}">`;
    card.addEventListener("click", () => selectIcon(ic));
    grid.appendChild(card);
  }
}

function selectIcon(ic) {
  state.selectedIcon = ic;
  $$(".icon-card").forEach((c) =>
    c.classList.toggle("selected", c.dataset.iconId === ic.id),
  );
  const thumb = $("#sum-icon");
  const value = $("#sum-icon-value");
  // Iconify icons are monochrome black SVGs → invert filter to display on dark UI.
  // Custom uploads keep their original colors → no filter.
  const cls = ic.prefix === "custom" ? "" : "icon-thumb";
  thumb.innerHTML = `<img src="${ic.svg_url}" alt="${ic.name}" class="${cls}">`;
  value.textContent = ic.prefix === "custom" ? `${ic.name} (upload)` : ic.name;
  value.classList.remove("empty");
  updateGenerateButton();
}

// ---------- Controls ----------
function bindControls() {
  $$("#ratio-row .pill").forEach((b) =>
    b.addEventListener("click", () => {
      $$("#ratio-row .pill").forEach((x) => x.classList.remove("active"));
      b.classList.add("active");
      state.ratio = b.dataset.ratio;
      updateOutputLabel();
    }),
  );
  $$("#size-row .pill").forEach((b) =>
    b.addEventListener("click", () => {
      $$("#size-row .pill").forEach((x) => x.classList.remove("active"));
      b.classList.add("active");
      state.size = parseInt(b.dataset.size, 10);
      updateOutputLabel();
    }),
  );
  $$("#quality-row .pill").forEach((b) =>
    b.addEventListener("click", () => {
      $$("#quality-row .pill").forEach((x) => x.classList.remove("active"));
      b.classList.add("active");
      state.quality = b.dataset.quality;
    }),
  );
}

function targetDimensions() {
  const s = state.size;
  switch (state.ratio) {
    case "1:1": return [s, s];
    case "3:2": return [Math.round(s * 1.5), s];
    case "2:3": return [s, Math.round(s * 1.5)];
    default:    return [s, s];
  }
}

function updateOutputLabel() {
  const [w, h] = targetDimensions();
  $("#output-size-label").textContent = `${w} × ${h} px`;
}

function updateGenerateButton() {
  const btn = $("#generate-btn");
  const ready = state.selectedIcon && state.selectedMaterial;
  btn.disabled = !ready;
  btn.querySelector(".btn-label").textContent = ready ? "+ Ajouter" : "Choisis icône + matériau";
}

// ---------- Generate / queue ----------
function bindGenerate() {
  $("#generate-btn").addEventListener("click", enqueueJob);
}

async function enqueueJob() {
  if (!state.selectedIcon || !state.selectedMaterial) return;
  const btn = $("#generate-btn");
  btn.disabled = true;
  const labelEl = btn.querySelector(".btn-label");
  const originalLabel = labelEl.textContent;
  labelEl.textContent = "Envoi…";

  try {
    const [genW, genH] = ({
      "1:1": [1024, 1024],
      "3:2": [1536, 1024],
      "2:3": [1024, 1536],
    })[state.ratio];
    const pngBlob = await rasterizeIconSvg(state.selectedIcon, genW, genH);

    const form = new FormData();
    form.append("image", pngBlob, "icon.png");
    form.append("material_id", state.selectedMaterial);
    form.append("ratio", state.ratio);
    const [w, h] = targetDimensions();
    form.append("width", String(w));
    form.append("height", String(h));
    form.append("quality", state.quality);
    form.append("icon_id", state.selectedIcon.id);
    form.append("icon_label", state.selectedIcon.name);
    form.append("icon_svg_url", state.selectedIcon.svg_url);

    const r = await fetch("/api/jobs", { method: "POST", body: form });
    if (!r.ok) {
      const body = await r.text();
      throw new Error(`${r.status} — ${body.slice(0, 200)}`);
    }
    const j = await r.json();
    toast(j.position > state.concurrencyLimit
      ? `Ajouté à la file • position ${j.position}`
      : "Ajouté à la file • démarrage immédiat", "info");
    await refreshJobs();
    ensurePolling();
  } catch (e) {
    console.error(e);
    toast(`Erreur : ${e.message}`, "error");
  } finally {
    labelEl.textContent = originalLabel;
    updateGenerateButton();
  }
}

async function rasterizeIconSvg(icon, width, height) {
  const shortest = Math.min(width, height);
  const iconBoxSize = Math.round(shortest * 0.8);
  const canvas = document.createElement("canvas");
  canvas.width = width;
  canvas.height = height;
  const ctx = canvas.getContext("2d");
  // White background: gives the model a clear high-contrast silhouette to anchor on.
  // The no-shadow / "erase the white" enforcement happens in the prompt.
  ctx.fillStyle = "#ffffff";
  ctx.fillRect(0, 0, width, height);

  if (icon.prefix === "custom") {
    // Custom upload (PNG/WebP/SVG/AVIF/GIF): draw the raster directly,
    // preserving its aspect ratio so non-square uploads aren't distorted.
    // svg_url falls back here for re-runs reconstructed from job params.
    const img = await loadImage(icon.customDataUrl || icon.svg_url);
    const ar = (img.width || 1) / (img.height || 1);
    let dw, dh;
    if (ar >= 1) { dw = iconBoxSize; dh = Math.round(iconBoxSize / ar); }
    else         { dh = iconBoxSize; dw = Math.round(iconBoxSize * ar); }
    const dx = Math.round((width - dw) / 2);
    const dy = Math.round((height - dh) / 2);
    ctx.drawImage(img, dx, dy, dw, dh);
  } else {
    // Iconify path — fetch the SVG via our backend proxy and inject explicit
    // width/height (Iconify SVGs use width="1em" which doesn't resolve cleanly
    // when loaded via Blob URL).
    const resp = await fetch(
      `/api/icon-svg?prefix=${encodeURIComponent(icon.prefix)}&name=${encodeURIComponent(icon.name)}`,
    );
    if (!resp.ok) throw new Error(`SVG fetch failed: ${resp.status}`);
    let svgText = await resp.text();
    if (/\swidth=/.test(svgText))  svgText = svgText.replace(/\swidth="[^"]+"/,  ` width="${iconBoxSize}"`);
    else                            svgText = svgText.replace(/<svg/, `<svg width="${iconBoxSize}"`);
    if (/\sheight=/.test(svgText)) svgText = svgText.replace(/\sheight="[^"]+"/, ` height="${iconBoxSize}"`);
    else                            svgText = svgText.replace(/<svg/, `<svg height="${iconBoxSize}"`);
    const blob = new Blob([svgText], { type: "image/svg+xml;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    try {
      const img = await loadImage(url);
      const dx = Math.round((width - iconBoxSize) / 2);
      const dy = Math.round((height - iconBoxSize) / 2);
      ctx.drawImage(img, dx, dy, iconBoxSize, iconBoxSize);
    } finally {
      URL.revokeObjectURL(url);
    }
  }

  return await new Promise((resolve, reject) =>
    canvas.toBlob((b) => (b ? resolve(b) : reject(new Error("toBlob failed"))), "image/png"),
  );
}

function loadImage(src) {
  return new Promise((resolve, reject) => {
    const img = new Image();
    img.onload = () => resolve(img);
    img.onerror = () => reject(new Error("Image load failed"));
    img.src = src;
  });
}

// ---------- Polling ----------
function ensurePolling() {
  if (state.pollHandle) return;
  state.pollHandle = setInterval(refreshJobs, state.pollInterval);
}

function maybeStopPolling() {
  const stillBusy = state.jobs.some(
    (j) => j.status === "queued" || j.status === "in_progress",
  );
  if (!stillBusy && state.pollHandle) {
    clearInterval(state.pollHandle);
    state.pollHandle = null;
  }
}

async function refreshJobs() {
  try {
    const r = await fetch("/api/jobs");
    if (!r.ok) throw new Error(`HTTP ${r.status}`);
    const data = await r.json();
    state.jobs = data.jobs || [];
    renderGallery(data);
    updateTopbarBadges(data);
    maybeStopPolling();
  } catch (e) {
    console.warn("poll failed", e);
  }
}

function updateTopbarBadges(data) {
  $("#tab-badge").textContent = state.jobs.length;
  $("#flight-count").textContent = data.in_flight;
  const pill = $("#meta-flight");
  pill.classList.toggle("active", data.in_flight > 0);
  // counts in gallery filter chips
  $("#count-all").textContent = state.jobs.length;
  $("#count-flight").textContent = data.in_flight;
  $("#count-done").textContent = data.completed;
  $("#count-fail").textContent = data.failed;
}

// ---------- Gallery ----------
function bindGalleryFilters() {
  $$(".filter-chip").forEach((chip) =>
    chip.addEventListener("click", () => {
      state.galleryFilter = chip.dataset.filter;
      $$(".filter-chip").forEach((c) => c.classList.toggle("active", c === chip));
      renderGallery();
    }),
  );
  $("#clear-completed").addEventListener("click", clearCompleted);
}

function renderGallery(data = null) {
  const grid = $("#gallery-grid");
  const f = state.galleryFilter;
  let items = state.jobs;
  if (f === "in_progress") {
    items = items.filter((j) => j.status === "queued" || j.status === "in_progress");
  } else if (f === "succeeded") {
    items = items.filter((j) => j.status === "succeeded");
  } else if (f === "failed") {
    items = items.filter((j) => j.status === "failed" || j.status === "cancelled");
  }
  if (!items.length) {
    const msg = state.jobs.length
      ? "Aucun job dans ce filtre."
      : "Pas encore de génération.<br>Va dans <b>Créer</b> pour ajouter ta première demande.";
    grid.innerHTML = `
      <div class="gallery-empty">
        <div class="empty-emoji">🎨</div>
        <div class="empty-text">${msg}</div>
      </div>`;
    return;
  }
  grid.innerHTML = "";
  for (const j of items) {
    grid.appendChild(renderGalleryCard(j));
  }
}

function renderGalleryCard(j) {
  const card = document.createElement("div");
  card.className = `gal-card s-${j.status}`;
  card.dataset.jobId = j.id;

  const elapsed = j.elapsed_ms
    ? `${(j.elapsed_ms / 1000).toFixed(1)}s`
    : j.started_at
      ? `${Math.round((Date.now() - new Date(j.started_at).getTime()) / 1000)}s`
      : "—";

  const thumbContent = (() => {
    if (j.status === "succeeded" && j.has_result) {
      return `<img src="/api/jobs/${j.id}/result.png?t=${encodeURIComponent(j.finished_at || "")}" alt="">`;
    }
    if (j.status === "in_progress") {
      return `
        <img src="${j.icon_svg_url}" class="source-icon" alt="">
        <div class="thumb-state">
          <div class="spinner"></div>
          <div>Génération… ${elapsed}</div>
        </div>`;
    }
    if (j.status === "queued") {
      return `
        <img src="${j.icon_svg_url}" class="source-icon" alt="">
        <div class="thumb-state">
          <div style="font-size:18px;opacity:.7">⏳</div>
          <div>En attente</div>
        </div>`;
    }
    if (j.status === "failed" || j.status === "cancelled") {
      return `
        <img src="${j.icon_svg_url}" class="source-icon" alt="">
        <div class="thumb-state">
          <div style="font-size:18px;color:var(--danger)">${j.status === "failed" ? "✕" : "⊘"}</div>
          <div>${j.status === "failed" ? "Échec" : "Annulé"}</div>
        </div>`;
    }
    return "";
  })();

  const statusLabel = ({
    queued: "En attente",
    in_progress: "En cours",
    succeeded: "Prêt",
    failed: "Échec",
    cancelled: "Annulé",
  })[j.status] || j.status;

  card.innerHTML = `
    <div class="gal-thumb">
      ${thumbContent}
      <div class="gal-status-pill s-${j.status}"><span class="dot-mini"></span>${statusLabel}</div>
    </div>
    <div class="gal-info">
      <div class="gal-title">${escapeHtml(j.params.icon_label || "icon")} · ${escapeHtml(j.params.material_label || j.params.material_id)}</div>
      <div class="gal-meta">${j.params.width}×${j.params.height} · ${qualityLabel(j.params.quality)}${j.status === "succeeded" ? " · " + elapsed : ""}</div>
    </div>
    <div class="gal-actions"></div>
  `;
  const actions = card.querySelector(".gal-actions");

  if (j.status === "succeeded") {
    const dl = document.createElement("button");
    dl.className = "btn-icon flex";
    dl.title = "Télécharger l'original";
    dl.innerHTML = "⬇ Télécharger";
    dl.addEventListener("click", (e) => { e.stopPropagation(); downloadJob(j); });
    actions.appendChild(dl);

    const crop = document.createElement("button");
    crop.className = "btn-icon";
    crop.title = "Auto-crop selon le contenu";
    crop.innerHTML = "✂";
    crop.addEventListener("click", (e) => {
      e.stopPropagation();
      openCropPopover(crop, j);
    });
    actions.appendChild(crop);

    card.addEventListener("click", () => openModal(j));
  }
  if (j.status === "failed" && j.error) {
    card.title = j.error;
  }

  const del = document.createElement("button");
  del.className = "btn-icon danger";
  del.title = "Supprimer";
  del.innerHTML = "✕";
  del.addEventListener("click", (e) => { e.stopPropagation(); deleteJob(j.id); });
  actions.appendChild(del);

  return card;
}

let activeCropPop = null;

function closeCropPopover() {
  if (activeCropPop) {
    activeCropPop.remove();
    activeCropPop = null;
    document.removeEventListener("click", _cropPopOutsideHandler, true);
  }
}

function _cropPopOutsideHandler(e) {
  if (activeCropPop && !activeCropPop.contains(e.target)) closeCropPopover();
}

function openCropPopover(anchor, j) {
  if (activeCropPop) { closeCropPopover(); return; }
  const pop = document.createElement("div");
  pop.className = "crop-pop";
  pop.innerHTML = `
    <button data-mode="square">
      <span class="pop-icon">▢</span>
      <span>Carré
        <span class="pop-sub">côté = plus grande dimension</span>
      </span>
    </button>
    <button data-mode="rectangle">
      <span class="pop-icon">▭</span>
      <span>Rectangle
        <span class="pop-sub">tight crop sur le contenu</span>
      </span>
    </button>
  `;
  document.body.appendChild(pop);
  const r = anchor.getBoundingClientRect();
  // anchor below-left of the button
  const pw = pop.offsetWidth;
  let left = Math.round(r.right - pw);
  if (left < 6) left = 6;
  pop.style.left = `${left}px`;
  pop.style.top = `${Math.round(r.bottom + 4)}px`;
  pop.querySelectorAll("button").forEach((b) =>
    b.addEventListener("click", (e) => {
      e.stopPropagation();
      const mode = b.dataset.mode;
      downloadJob(j, mode);
      closeCropPopover();
    }),
  );
  activeCropPop = pop;
  // close on outside click (next tick so this click doesn't trigger immediately)
  setTimeout(() => document.addEventListener("click", _cropPopOutsideHandler, true), 0);
}

function qualityLabel(q) {
  return { low: "Rapide", medium: "Standard", high: "Haute" }[q] || q;
}

function escapeHtml(s) {
  return String(s).replace(/[<>&"']/g, (c) => ({"<":"&lt;",">":"&gt;","&":"&amp;",'"':"&quot;","'":"&#39;"}[c]));
}

async function deleteJob(jobId) {
  try {
    const r = await fetch(`/api/jobs/${jobId}`, { method: "DELETE" });
    if (!r.ok) throw new Error(`HTTP ${r.status}`);
    await refreshJobs();
  } catch (e) {
    toast(`Erreur suppression : ${e.message}`, "error");
  }
}

async function clearCompleted() {
  try {
    const r = await fetch("/api/jobs/clear-completed", { method: "POST" });
    const data = await r.json();
    toast(`${data.removed} job${data.removed > 1 ? "s" : ""} retiré${data.removed > 1 ? "s" : ""}`, "info");
    await refreshJobs();
  } catch (e) {
    toast(`Erreur : ${e.message}`, "error");
  }
}

function downloadJob(j, cropMode = null) {
  const suffix = cropMode ? `-${cropMode}` : "";
  const base = `${j.params.icon_label || "asset"}-${j.params.material_id}-${j.params.width}x${j.params.height}${suffix}`;
  const cropParam = cropMode ? `&crop=${cropMode}` : "";
  const a = document.createElement("a");
  a.href = `/api/jobs/${j.id}/result.png?t=${encodeURIComponent(j.finished_at || "")}${cropParam}`;
  a.download = `${base}.png`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  const label = cropMode === "square" ? "carré" : cropMode === "rectangle" ? "rectangle" : "original";
  toast(`Téléchargement ${label} : ${base}.png`, "success");
}

// ---------- Modal ----------
let modalJob = null;

function _succeededJobsSorted() {
  // Sort by creation order so prev/next is intuitive (oldest first → newest last).
  return state.jobs
    .filter((j) => j.status === "succeeded" && j.has_result)
    .sort((a, b) => (a.created_at || "").localeCompare(b.created_at || ""));
}

function _modalNavInfo() {
  if (!modalJob) return { canPrev: false, canNext: false, position: 0, total: 0 };
  const list = _succeededJobsSorted();
  const idx = list.findIndex((j) => j.id === modalJob.id);
  return {
    canPrev: idx > 0,
    canNext: idx >= 0 && idx < list.length - 1,
    position: idx + 1,
    total: list.length,
    prev: idx > 0 ? list[idx - 1] : null,
    next: idx >= 0 && idx < list.length - 1 ? list[idx + 1] : null,
  };
}

function openModal(j) {
  modalJob = j;
  $("#modal-img").src = `/api/jobs/${j.id}/result.png?t=${encodeURIComponent(j.finished_at || "")}`;
  $("#modal-title").textContent = `${j.params.icon_label || "icon"} · ${j.params.material_label}`;
  const elapsedStr = j.elapsed_ms ? `${(j.elapsed_ms/1000).toFixed(1)}s` : "—";
  const nav = _modalNavInfo();
  const counter = nav.total > 1 ? ` · ${nav.position}/${nav.total}` : "";
  $("#modal-sub").textContent = `${j.params.width} × ${j.params.height} px · ${qualityLabel(j.params.quality)} · ${elapsedStr}${counter}`;
  // toggle prev/next buttons
  const prevBtn = $("#modal-prev");
  const nextBtn = $("#modal-next");
  if (prevBtn) prevBtn.disabled = !nav.canPrev;
  if (nextBtn) nextBtn.disabled = !nav.canNext;
  $("#result-modal").classList.remove("hidden");
}

function modalNavigate(direction) {
  const nav = _modalNavInfo();
  const target = direction === "prev" ? nav.prev : nav.next;
  if (target) openModal(target);
}

function closeModal() {
  $("#result-modal").classList.add("hidden");
  modalJob = null;
}

// ---------- Misc bindings ----------
function bindMisc() {
  $("#modal-close").addEventListener("click", closeModal);
  $(".modal-backdrop").addEventListener("click", closeModal);
  $("#modal-download").addEventListener("click", () => {
    if (modalJob) downloadJob(modalJob);
  });
  $("#modal-crop-square").addEventListener("click", () => {
    if (modalJob) downloadJob(modalJob, "square");
  });
  $("#modal-crop-rect").addEventListener("click", () => {
    if (modalJob) downloadJob(modalJob, "rectangle");
  });
  $("#modal-redo").addEventListener("click", () => {
    if (!modalJob) return;
    // Restore selections and queue again, then jump to Créer tab.
    const parts = (modalJob.params.icon_id || "").split(":");
    state.selectedIcon = {
      id: modalJob.params.icon_id,
      prefix: parts[0],
      name: parts[1],
      svg_url: modalJob.icon_svg_url,
    };
    // visually reflect icon
    $("#sum-icon").innerHTML = `<img src="${modalJob.icon_svg_url}" class="icon-thumb" alt="">`;
    $("#sum-icon-value").textContent = parts[1] || "icon";
    // material
    const mid = modalJob.params.material_id;
    state.selectedMaterial = mid;
    $$(".material-card").forEach((c) => {
      const sel = c.dataset.materialId === mid;
      c.classList.toggle("selected", sel);
      if (sel) {
        const previewUrl = c.dataset.materialPreview;
        const thumb = $("#sum-material");
        if (previewUrl) {
          thumb.innerHTML = `<img src="${previewUrl}" alt="">`;
        }
        $("#sum-material-value").textContent = c.dataset.materialLabel;
      }
    });
    closeModal();
    switchTab("create");
    updateGenerateButton();
    enqueueJob();
  });
  // Modal nav buttons (prev / next)
  $("#modal-prev")?.addEventListener("click", (e) => {
    e.stopPropagation();
    modalNavigate("prev");
  });
  $("#modal-next")?.addEventListener("click", (e) => {
    e.stopPropagation();
    modalNavigate("next");
  });
  window.addEventListener("keydown", (e) => {
    if (e.key === "Escape") closeModal();
    if (e.key === "1" && e.altKey) switchTab("create");
    if (e.key === "2" && e.altKey) switchTab("gallery");
    // Arrow keys navigate within the modal (only when it's open)
    const modalOpen = !$("#result-modal").classList.contains("hidden");
    if (modalOpen && (e.key === "ArrowLeft" || e.key === "ArrowRight")) {
      e.preventDefault();
      modalNavigate(e.key === "ArrowLeft" ? "prev" : "next");
    }
  });
}

// ---------- Toast ----------
let toastTimer = null;
function toast(message, kind = "") {
  const t = $("#toast");
  t.textContent = message;
  t.className = `toast ${kind}`;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => t.classList.add("hidden"), 4000);
}
