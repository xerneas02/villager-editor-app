const $ = (selector) => document.querySelector(selector);
const state = { catalog: null, gender: "female", role: "farmer", previewTimer: null, request: 0 };
const fields = ["name", "nose", "ears", "hair", "hairColor", "skinColor", "pupilColor", "facialHair", "hat", "bodyType", "outfit", "accessory", "waiting", "talking", "walking"];

function label(value) {
  return value.replaceAll("_", " ").replace(/\b\w/g, c => c.toUpperCase());
}

function fillSelect(id, values, optional = false) {
  const select = $("#" + id);
  select.replaceChildren();
  if (optional) select.add(new Option("Aucun", ""));
  values.forEach(value => select.add(new Option(label(value), value)));
}

function checks(container, values, kind) {
  container.replaceChildren(...values.map(item => {
    const value = typeof item === "string" ? item : item.value;
    const text = typeof item === "string" ? label(item) : item.label;
    const wrapper = document.createElement("label");
    wrapper.className = "check";
    wrapper.innerHTML = `<input type="checkbox" data-kind="${kind}" value="${value}"><span>${text}</span>`;
    return wrapper;
  }));
}

function selected(kind) {
  return [...document.querySelectorAll(`input[data-kind="${kind}"]:checked`)].map(input => input.value);
}

function config() {
  const result = Object.fromEntries(fields.map(id => [id, $("#" + id).value]));
  result.gender = state.gender;
  result.role = state.role;
  result.emotions = selected("emotion");
  result.actions = selected("action");
  return result;
}

function applyConfig(preset) {
  state.gender = preset.gender;
  state.role = preset.role;
  fields.forEach(id => { if (preset[id] !== undefined) $("#" + id).value = preset[id]; });
  document.querySelectorAll("[data-gender]").forEach(button => button.classList.toggle("active", button.dataset.gender === state.gender));
  document.querySelectorAll('input[type="checkbox"]').forEach(input => {
    input.checked = input.dataset.kind === "emotion" ? preset.emotions.includes(input.value) : preset.actions.includes(input.value);
  });
  updateSummary();
  schedulePreview(0);
}

function applyPreset(key) {
  applyConfig(state.catalog.presets[key]);
}

function updateSummary() {
  const total = 3 + selected("emotion").length + selected("action").length;
  $("#animationCount").textContent = `${total} sélectionnées`;
  $("#summaryAnimations").textContent = total;
  $("#summaryName").textContent = $("#name").value || "Sans nom";
  $("#summaryRole").textContent = label(state.role || "custom");
}

function setStatus(text, mode = "") {
  $("#status").textContent = text;
  $(".stage").classList.toggle("busy", mode === "busy");
  $(".stage").classList.toggle("error", mode === "error");
}

function toast(message) {
  const node = $("#toast");
  node.textContent = message;
  node.classList.add("show");
  clearTimeout(node.timer);
  node.timer = setTimeout(() => node.classList.remove("show"), 4200);
}

async function preview() {
  const request = ++state.request;
  setStatus("Construction de l’aperçu…", "busy");
  try {
    const response = await fetch("/api/preview", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(config()) });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "Aperçu impossible");
    if (request !== state.request) return;
    const image = $("#preview");
    image.onload = () => { image.classList.add("ready"); $("#placeholder").classList.add("hidden"); setStatus("Aperçu à jour"); };
    image.src = `${data.preview}?v=${Date.now()}`;
  } catch (error) {
    setStatus(error.message, "error");
  }
}

function schedulePreview(delay = 420) {
  clearTimeout(state.previewTimer);
  updateSummary();
  state.previewTimer = setTimeout(preview, delay);
}

async function exportCharacter() {
  const button = $("#export");
  button.disabled = true;
  button.textContent = "Export…";
  setStatus("Génération du fichier animé…", "busy");
  try {
    const response = await fetch("/api/export", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(config()) });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "Export impossible");
    toast(`${data.animations} animations exportées · ${data.file}`);
    setStatus("Export terminé");
  } catch (error) {
    toast(error.message);
    setStatus(error.message, "error");
  } finally {
    button.disabled = false;
    button.textContent = "Exporter le personnage";
  }
}

async function importCharacter(file) {
  if (!file) return;
  setStatus("Import du personnage…", "busy");
  try {
    const response = await fetch("/api/import", { method: "POST", body: await file.arrayBuffer() });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "Import impossible");
    $("#preset").value = "";
    applyConfig(data.config);
    toast(`${data.name} importé`);
  } catch (error) {
    toast(error.message);
    setStatus(error.message, "error");
  }
}

async function importComponent() {
  const file = $("#componentFile").files[0];
  const name = $("#componentName").value.trim();
  if (!file || !name) return toast("Choisissez un modèle et un nom");
  const button = $("#addComponent");
  button.disabled = true;
  setStatus("Extraction du composant…", "busy");
  try {
    const bytes = new Uint8Array(await file.arrayBuffer());
    let binary = "";
    for (let offset = 0; offset < bytes.length; offset += 32768)
      binary += String.fromCharCode(...bytes.subarray(offset, offset + 32768));
    const response = await fetch("/api/component/import", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ category: $("#componentCategory").value, name, data: btoa(binary) }),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "Import impossible");
    state.catalog = await (await fetch("/api/catalog")).json();
    const select = $("#" + data.field);
    if (![...select.options].some(option => option.value === data.value))
      select.add(new Option(label(data.value), data.value));
    select.value = data.value;
    $("#componentName").value = "";
    $("#componentFile").value = "";
    toast(`${label(data.value)} ajouté à la bibliothèque`);
    schedulePreview(0);
  } catch (error) {
    toast(error.message);
    setStatus(error.message, "error");
  } finally {
    button.disabled = false;
  }
}

function randomize() {
  const c = state.catalog.components;
  const pick = values => values[Math.floor(Math.random() * values.length)];
  ["nose", "ears", "hair", "bodyType", "outfit"].forEach(id => $("#" + id).value = pick(c[id]));
  ["facialHair", "hat", "accessory"].forEach(id => $("#" + id).value = Math.random() < .3 ? "" : pick(c[id]));
  $("#hairColor").value = pick(["#3e3028", "#6c3f28", "#8b5c3e", "#a4825d", "#c49a58", "#e0c58d"]);
  $("#skinColor").value = pick(["#f2c894", "#ecb880", "#d99b68", "#b97850", "#8f573d", "#69402f"]);
  $("#pupilColor").value = pick(["#424039", "#5b3a29", "#3f6045", "#3d5870", "#655078"]);
  state.role = "custom";
  schedulePreview(0);
}

async function start() {
  const response = await fetch("/api/catalog");
  state.catalog = await response.json();
  Object.entries(state.catalog.components).forEach(([id, values]) => fillSelect(id, values, ["facialHair", "hat", "accessory"].includes(id)));
  ["waiting", "talking", "walking"].forEach(id => fillSelect(id, state.catalog.animations[id]));
  fillSelect("preset", Object.keys(state.catalog.presets));
  checks($("#emotions"), state.catalog.animations.emotions, "emotion");
  const groups = $("#actions");
  Object.entries(state.catalog.animations.actions).forEach(([category, items], index) => {
    const details = document.createElement("details");
    details.className = "action-group";
    if (index < 2) details.open = true;
    details.innerHTML = `<summary>${label(category)}</summary><div class="checks"></div>`;
    checks(details.querySelector(".checks"), items, "action");
    groups.append(details);
  });
  $("#preset").value = "mira_farmer";
  applyPreset("mira_farmer");

  $("#preset").addEventListener("change", event => applyPreset(event.target.value));
  document.querySelectorAll("[data-gender]").forEach(button => button.addEventListener("click", () => {
    state.gender = button.dataset.gender;
    document.querySelectorAll("[data-gender]").forEach(item => item.classList.toggle("active", item === button));
    schedulePreview(0);
  }));
  ["nose", "ears", "hair", "hairColor", "skinColor", "pupilColor", "facialHair", "hat", "bodyType", "outfit", "accessory"]
    .forEach(id => $("#" + id).addEventListener("change", () => schedulePreview()));
  document.querySelectorAll("#waiting, #talking, #walking, input[type=checkbox]")
    .forEach(input => input.addEventListener("change", updateSummary));
  $("#name").addEventListener("input", updateSummary);
  $("#refresh").addEventListener("click", preview);
  $("#import").addEventListener("click", () => $("#importFile").click());
  $("#importFile").addEventListener("change", event => {
    importCharacter(event.target.files[0]);
    event.target.value = "";
  });
  $("#addComponent").addEventListener("click", importComponent);
  $("#randomize").addEventListener("click", randomize);
  $("#export").addEventListener("click", exportCharacter);
}

start().catch(error => setStatus(error.message, "error"));
