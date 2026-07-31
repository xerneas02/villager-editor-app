const $ = (selector) => document.querySelector(selector);
const state = { catalog: null, gender: "female", role: "farmer", previewTimer: null, request: 0 };
const fields = ["name", "nose", "ears", "eyebrows", "hair", "hairColor", "skinColor", "pupilColor", "pupilStyle", "facialHair", "hat", "horns", "tail", "wings", "bodyType", "outfit", "accessory", "scale", "scaleMode", "headScale", "waiting", "talking", "walking", "walkSpeed"];
const pupilLabels = { default: "Carrées", small: "Petites", round: "Rondes voxel", vertical_slit: "Fente verticale", horizontal_slit: "Fente horizontale", large: "Grandes" };

function label(value) {
  const animationNames = { monster: "Monstre", villain: "Méchant", idiot: "Idiot", barbarian: "Barbare" };
  if (animationNames[value]) return animationNames[value];
  const hairNames = { buzz_cut: "Rasé court", mohawk: "Crête iroquoise", afro: "Afro", dreadlocks: "Dreadlocks", ponytail: "Queue-de-cheval", pigtails: "Couettes", bun: "Chignon", double_buns: "Doubles chignons", stubble: "Barbe rasée courte", moustache_stubble: "Moustache rasée courte" };
  if (hairNames[value]) return hairNames[value];
  const names = { thick: "Épais", thin: "Fins", arched: "Arqués", stern: "Sévères", worried: "Inquiets", bushy: "Broussailleux", unibrow: "Monosourcil", draconic: "Draconiques", moose: "Élan", reindeer: "Renne", roe_deer: "Chevreuil", unicorn: "Licorne", ogre: "Ogre", great_helm: "Grand heaume", knight_plate: "Chevalier en plates", knight_noble: "Chevalier noble", knight_black: "Chevalier noir", vertical_slit: "Fente verticale", horizontal_slit: "Fente horizontale", wolf: "Loup", fox: "Renard", cat: "Chat", deer: "Cerf", rabbit: "Lapin", horse: "Cheval", goat: "Chèvre", dragon: "Dragon", bird: "Oiseau", angel: "Ange — quatre ailes", demonic: "Démoniaque", butterfly: "Papillon", insect: "Insecte", lizard: "Lézard", crocodile: "Crocodile", iguana: "Iguane", serpent: "Serpent", none: "Aucun" };
  if (names[value]) return names[value];
  return value.replaceAll("_", " ").replace(/\b\w/g, c => c.toUpperCase());
}

function fillSelect(id, values, optional = false) {
  const select = $("#" + id);
  select.replaceChildren();
  if (optional) select.add(new Option("Aucun", ""));
  values.forEach(value => select.add(new Option(id === "pupilStyle" ? pupilLabels[value] : label(value), value)));
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
  result.scale = Number(result.scale);
  result.headScale = Number(result.headScale);
  result.walkSpeed = Number(result.walkSpeed);
  result.scaleHead = $("#scaleHead").checked;
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
  $("#scaleHead").checked = preset.scaleHead ?? true;
  document.querySelectorAll('input[data-kind]').forEach(input => {
    input.checked = input.dataset.kind === "emotion" ? preset.emotions.includes(input.value) : preset.actions.includes(input.value);
  });
  updateScaleLabel();
  updateHeadScale();
  updateWalkSpeed();
  updateSummary();
  schedulePreview(0);
}

function updateScaleLabel() {
  $("#scaleValue").textContent = `${Number($("#scale").value).toLocaleString("fr-FR", { minimumFractionDigits: 2, maximumFractionDigits: 2 })} blocs`;
}

function updateHeadScale() {
  const independent = !$("#scaleHead").checked;
  $("#headScale").disabled = !independent;
  $("#headScaleControl").classList.toggle("disabled", !independent);
  $("#headScaleValue").textContent = `×${Number($("#headScale").value).toLocaleString("fr-FR", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

function updateWalkSpeed() {
  $("#walkSpeedValue").textContent = `${Number($("#walkSpeed").value).toLocaleString("fr-FR", { minimumFractionDigits: 2, maximumFractionDigits: 2 })} blocs/s`;
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
  const rules = state.catalog.randomization;
  const pick = values => values[Math.floor(Math.random() * values.length)];
  state.gender = Math.random() < .5 ? "female" : "male";
  let body = pick(c.bodyType);
  let monster = rules.monsterBodies.includes(body);
  const child = !monster && Math.random() < .12;
  if (child) body = pick(c.bodyType.filter(value => ["compact", "slender"].includes(rules.bodyBases[value])));
  monster = rules.monsterBodies.includes(body);
  const base = rules.bodyBases[body] || "standard";
  const normalOutfits = c.outfit.filter(value => !rules.monsterOutfits.includes(value));
  const genderedOutfits = normalOutfits.filter(value => !value.endsWith(state.gender === "female" ? "_m" : "_f"));
  const animalEars = ["cat", "wolf", "fox", "rabbit", "deer", "goat", "horse"];
  const regularEars = c.ears.filter(value => !animalEars.includes(value));
  const ears = monster ? regularEars.filter(value => value.includes("elf") || ["broad", "ogre", "none"].includes(value)) : regularEars;
  $("#nose").value = pick(c.nose);
  $("#eyebrows").value = pick(c.eyebrows);
  $("#hair").value = monster && Math.random() < .35 ? "bald" : pick(c.hair);
  $("#bodyType").value = body;
  $("#outfit").value = pick(monster ? rules.monsterOutfits : genderedOutfits);
  $("#facialHair").value = Math.random() < (monster ? .2 : state.gender === "male" ? .55 : .05) ? pick(c.facialHair) : "";
  $("#hat").value = Math.random() < (monster ? .15 : .55) ? pick(c.hat) : "";
  const hornTail = { draconic: pick(["dragon", "lizard", "crocodile", "iguana", "serpent"]), moose: "deer", reindeer: "deer", roe_deer: "deer", ram: "goat", curved: "goat", unicorn: "horse" };
  const horn = Math.random() < (monster ? .35 : .03) ? pick(c.horns) : "";
  $("#horns").value = horn;
  const tail = Math.random() < (hornTail[horn] ? .75 : monster ? .2 : .06) ? (hornTail[horn] || pick(c.tail)) : "";
  $("#tail").value = tail;
  const wings = Math.random() < (monster ? .18 : .035) ? pick(monster
    ? c.wings.filter(value => ["dragon", "demonic", "insect"].includes(value))
    : c.wings.filter(value => ["bird", "angel", "butterfly"].includes(value))) : "";
  $("#wings").value = wings;
  $("#ears").value = ({ wolf: "wolf", fox: "fox", cat: "cat", rabbit: "rabbit", deer: "deer", goat: "goat", horse: "horse" })[tail] || pick(ears);
  const accessories = wings ? c.accessory.filter(value => !["quiver", "traveler_cloak"].includes(value)) : c.accessory;
  $("#accessory").value = Math.random() < (monster ? .35 : .6) ? pick(accessories) : "";
  $("#hairColor").value = pick(["#3e3028", "#6c3f28", "#8b5c3e", "#a4825d", "#c49a58", "#e0c58d"]);
  $("#skinColor").value = pick(monster
    ? ["#424d3d", "#586044", "#6b6947", "#65705a", "#795d43"]
    : ["#f2c894", "#ecb880", "#d99b68", "#b97850", "#8f573d", "#69402f"]);
  $("#pupilColor").value = pick(["#424039", "#5b3a29", "#3f6045", "#3d5870", "#655078"]);
  $("#pupilStyle").value = monster ? pick(c.pupilStyle) : Math.random() < .18 ? pick(c.pupilStyle) : "default";
  const specialAnimations = ["monster", "villain", "idiot", "barbarian"];
  for (const kind of ["waiting", "talking", "walking"])
    $("#" + kind).value = pick(state.catalog.animations[kind].filter(value => specialAnimations.includes(value) === monster));
  const ranges = {
    goblin: [1.35, 1.65], orc: [2.1, 2.45], brute: [2.35, 2.75],
    chubby: [1.95, 2.25], sturdy: [1.8, 2.1], heroic: [1.8, 2.1],
    compact: [1.65, 1.9], slender: [1.7, 1.95], standard: [1.75, 2.05],
  };
  const large = !child && !monster && Math.random() < .12;
  const range = child ? [1.2, 1.55] : large ? [2.15, 2.4] : (ranges[base] || ranges.standard);
  const genderOffset = child || monster ? 0 : state.gender === "female" ? -.1 : .05;
  $("#scale").value = (range[0] + Math.random() * (range[1] - range[0]) + genderOffset).toFixed(2);
  $("#walkSpeed").value = Math.min(12, Math.max(.1,
    state.catalog.animations.walkingSpeeds[$("#walking").value] * Number($("#scale").value) / 1.9)).toFixed(2);
  $("#scaleMode").value = "uniform";
  $("#scaleHead").checked = !child;
  $("#headScale").value = child ? (.78 + Math.random() * .12).toFixed(2) : 1;
  state.role = child ? "child" : large ? "large" : monster ? "monster" : "custom";
  updateScaleLabel();
  updateHeadScale();
  updateWalkSpeed();
  schedulePreview(0);
}

async function start() {
  const response = await fetch("/api/catalog");
  state.catalog = await response.json();
  Object.entries(state.catalog.components).forEach(([id, values]) => fillSelect(id, values, ["facialHair", "hat", "horns", "tail", "wings", "accessory"].includes(id)));
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
  ["nose", "ears", "eyebrows", "hair", "hairColor", "skinColor", "pupilColor", "pupilStyle", "facialHair", "hat", "horns", "tail", "wings", "bodyType", "outfit", "accessory"]
    .forEach(id => $("#" + id).addEventListener("change", () => schedulePreview()));
  $("#scale").addEventListener("input", () => { updateScaleLabel(); schedulePreview(); });
  $("#headScale").addEventListener("input", () => { updateHeadScale(); schedulePreview(); });
  $("#walkSpeed").addEventListener("input", updateWalkSpeed);
  $("#scaleMode").addEventListener("change", () => schedulePreview(0));
  $("#scaleHead").addEventListener("change", () => { updateHeadScale(); schedulePreview(0); });
  document.querySelectorAll("#waiting, #talking, #walking, input[data-kind]")
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
