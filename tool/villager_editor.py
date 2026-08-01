"""Dependency-free local web editor for modular animated villagers."""

import argparse
import base64
import copy
import json
import re
import threading
import unicodedata
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from generate_villager_action_animations import add_animations as add_actions, animation_field, specifications
from generate_villager_accessories import CATEGORIES as ACCESSORIES, combine_with_outfit, make_accessory, walk
from generate_villager_body import BODY_TYPES, group
from generate_villager_clothing import PRESETS as OUTFIT_PRESETS, build as build_outfit
from generate_villager_emotion_animations import EMOTIONS, add_animations as add_emotions
from generate_villager_examples import build, write
from generate_villager_population import APPEARANCE_OVERRIDES, COMMON, EYEBROWS, POPULATION, PUPILS, eyebrows, pupils
from generate_villager_talking_animations import PERSONALITIES as TALKING, add_animations as add_talking
from generate_villager_tails import animate_tail
from generate_villager_wings import animate_wings
from generate_villager_waiting_animations import (
    PERSONALITIES as WAITING, add_animations as add_waiting, reparent_character, reparent_head,
)
from generate_villager_walking_animations import PROFILES as WALKING, add_animations as add_walking
from preview_bdengine import boxes, load, loads, rasterizer_self_test, reference_player, render


ROOT = Path(__file__).resolve().parent.parent
WEB_DIR = ROOT / "villager_editor"
PREVIEW_DIR = ROOT / "previews" / "characters" / "villagers" / "editor"
EXPORT_DIR = ROOT / "bdengine" / "characters" / "villagers" / "custom"
ACTION_SPECS = {f"{category.removesuffix('s')}_{name}": (category, name, profile)
                for category, name, profile in specifications()}
BUILD_LOCK = threading.Lock()
PREVIEW_KEYS = ("eyebrows", "nose", "ears", "hair", "hairColor", "skinColor", "pupilColor", "pupilStyle", "facialHair", "hat", "horns", "tail", "wings", "bodyType", "outfit", "accessory", "scale", "scaleMode", "scaleHead", "headScale")
LAST_PREVIEW = None
DEFAULT_HEIGHT = 1.9
ADULT_HEIGHTS = {"female": 1.8, "male": 2.05}
PRESET_PROPORTIONS = {
    "alder_farmer": {"scale": 1.88},
    "elise_smith": {"scale": 1.42, "scaleHead": False, "headScale": .88},
    "bran_blacksmith": {"scale": 2.18},
    "edric_lord": {"scale": 2.16},
    "lyra_huntress": {"scale": 1.84},
    "goblin_raider": {"scale": 1.52},
    "chubby_villager": {"scale": 2.28},
    "luc_shepherd": {"scale": 1.48, "scaleHead": False, "headScale": .9},
    "varkos_dragonkin": {"scale": 2.25},
    "bryn_moose_warden": {"scale": 2.16},
    "yrsa_reindeer_oracle": {"scale": 1.84},
    "fenn_roe_scout": {"scale": 1.72},
    "maela_faun": {"scale": 1.78},
}
COMPONENT_IMPORTS = {
    "ears": ("heads/ears", "villager_ears_", "Ears -", "ears"),
    "nose": ("heads/noses", "villager_nose_", "Nose -", "nose"),
    "hair": ("hair", "villager_hair_", "Hair -", "hair"),
    "hat": ("headwear/custom", "villager_hat_", "Hat -", "hat"),
    "horns": ("headwear/horns/custom", "villager_horns_", "Horns -", "horns"),
    "tail": ("tails/custom", "villager_tail_", "Tail -", "tail"),
    "wings": ("wings/custom", "villager_wings_", "Wings -", "wings"),
    "beard": ("facial_hair/beards", "villager_beard_", "Facial Hair -", "facialHair"),
    "moustache": ("facial_hair/moustaches", "villager_moustache_", "Facial Hair -", "facialHair"),
    "outfit": ("clothing/outfits", "villager_outfit_", "Body Structure", "outfit"),
    "body": ("bodies", "villager_body_", "Body Structure", "bodyType"),
}


def stems(folder, prefix):
    return sorted(path.stem.removeprefix(prefix) for path in folder.rglob(f"{prefix}*.bdengine"))


def catalog():
    villagers = ROOT / "bdengine" / "characters" / "villagers"
    monster_bases = {"goblin", "orc", "brute"}
    custom_bodies = []
    monster_bodies = set(monster_bases)
    body_bases = {name: name for name in BODY_TYPES}
    for path in (villagers / "bodies").glob("*.bdengine"):
        metadata = load(path).get("customComponent", {})
        if metadata.get("category") == "body":
            custom_bodies.append(metadata["name"])
            body_bases[metadata["name"]] = metadata.get("baseBodyType", "standard")
            if metadata.get("baseBodyType") in monster_bases:
                monster_bodies.add(metadata["name"])
    outfits = stems(villagers / "clothing" / "outfits", "villager_outfit_")
    monster_outfits = []
    for name in outfits:
        source = load(next((villagers / "clothing" / "outfits").rglob(f"villager_outfit_{name}.bdengine")))
        metadata = source.get("customComponent", {})
        if source.get("clothing", {}).get("palette") == "monster" or metadata.get("baseBodyType") in monster_bases:
            monster_outfits.append(name)
    facial = stems(villagers / "facial_hair" / "beards", "villager_beard_")
    facial += [f"moustache_{name}" for name in stems(
        villagers / "facial_hair" / "moustaches", "villager_moustache_")]
    actions = {}
    for full_name, (category, name, _) in ACTION_SPECS.items():
        actions.setdefault(category, []).append({"value": full_name, "label": name.replace("_", " ").title()})
    presets = {}
    for name, (gender, role, model, waiting, talking, walking, emotions, extra) in POPULATION.items():
        nose, ears, hair, hair_color, facial_hair, hat, outfit, accessory = model
        source = load(villagers / "clothing" / "outfits" / f"villager_outfit_{outfit}.bdengine")
        body_type = source.get("clothing", {}).get("body") or OUTFIT_PRESETS[outfit][0]
        presets[name] = {
            "name": name.replace("_", " ").title(), "gender": gender, "role": role,
            "eyebrows": "thin" if gender == "female" else "thick",
            "nose": nose, "ears": ears, "hair": hair, "hairColor": hair_color,
            "skinColor": "#ECB880", "pupilColor": "#424039", "pupilStyle": "default",
            "facialHair": facial_hair or "", "hat": hat or "", "horns": "", "tail": "", "wings": "", "bodyType": body_type, "outfit": outfit,
            "accessory": accessory or "", "waiting": waiting, "talking": talking,
            "walking": walking, "emotions": list(emotions),
            "actions": list(dict.fromkeys(COMMON + extra)),
            "scale": ADULT_HEIGHTS[gender], "scaleMode": "uniform", "scaleHead": True, "headScale": 1.0,
        }
        presets[name].update(PRESET_PROPORTIONS.get(name, {}))
        presets[name].update(APPEARANCE_OVERRIDES.get(name, {}))
        presets[name]["walkSpeed"] = round(WALKING[walking]["speed"] * presets[name]["scale"] / DEFAULT_HEIGHT, 2)
    return {
        "components": {
            "nose": stems(villagers / "heads" / "noses", "villager_nose_"),
            "ears": stems(villagers / "heads" / "ears", "villager_ears_"),
            "hair": ["bald", *stems(villagers / "hair", "villager_hair_")],
            "facialHair": sorted(facial),
            "hat": stems(villagers / "headwear", "villager_hat_"),
            "horns": stems(villagers / "headwear" / "horns", "villager_horns_"),
            "tail": stems(villagers / "tails", "villager_tail_"),
            "wings": stems(villagers / "wings", "villager_wings_"),
            "outfit": outfits,
            "accessory": stems(villagers / "accessories", "villager_accessory_"),
            "bodyType": [*BODY_TYPES, *sorted(custom_bodies)],
            "eyebrows": list(EYEBROWS),
            "pupilStyle": list(PUPILS),
        },
        "randomization": {
            "monsterBodies": sorted(monster_bodies),
            "monsterOutfits": sorted(monster_outfits),
            "bodyBases": body_bases,
        },
        "animations": {
            "waiting": list(WAITING), "talking": list(TALKING), "walking": list(WALKING),
            "walkingSpeeds": {name: profile["speed"] for name, profile in WALKING.items()},
            "emotions": list(EMOTIONS), "actions": actions,
        },
        "presets": presets,
    }


CATALOG = catalog()


def choice(config, key, options, optional=False):
    value = config.get(key, "")
    if optional and value in ("", None):
        return None
    if value not in options:
        raise ValueError(f"Valeur invalide pour {key}: {value}")
    return value


def validate(config):
    if not isinstance(config, dict):
        raise ValueError("Configuration invalide")
    name = str(config.get("name", "Villageois")).strip()[:60] or "Villageois"
    gender = choice(config, "gender", ("male", "female"))
    components = CATALOG["components"]
    result = {
        "name": name, "gender": gender, "role": str(config.get("role", "custom"))[:40],
        "eyebrows": choice(config, "eyebrows", EYEBROWS) if "eyebrows" in config else ("thin" if gender == "female" else "thick"),
        "nose": choice(config, "nose", components["nose"]),
        "ears": choice(config, "ears", components["ears"]),
        "hair": choice(config, "hair", components["hair"]),
        "facialHair": choice(config, "facialHair", components["facialHair"], True),
        "hat": choice(config, "hat", components["hat"], True),
        "horns": choice(config, "horns", components["horns"], True),
        "tail": choice(config, "tail", components["tail"], True),
        "wings": choice(config, "wings", components["wings"], True),
        "pupilStyle": choice(config, "pupilStyle", PUPILS) if "pupilStyle" in config else "default",
        "bodyType": choice(config, "bodyType", components["bodyType"]),
        "outfit": choice(config, "outfit", components["outfit"]),
        "accessory": choice(config, "accessory", components["accessory"], True),
        "waiting": choice(config, "waiting", CATALOG["animations"]["waiting"]),
        "talking": choice(config, "talking", CATALOG["animations"]["talking"]),
        "walking": choice(config, "walking", CATALOG["animations"]["walking"]),
    }
    try:
        scale = float(config.get("scale", DEFAULT_HEIGHT))
    except (TypeError, ValueError) as error:
        raise ValueError("Taille invalide") from error
    if not .5 <= scale <= 10:
        raise ValueError("La taille doit être comprise entre 0,5 et 10 blocs")
    result["scale"] = scale
    try:
        walk_speed = float(config.get("walkSpeed", WALKING[result["walking"]]["speed"] * scale / DEFAULT_HEIGHT))
    except (TypeError, ValueError) as error:
        raise ValueError("Vitesse de marche invalide") from error
    if not .1 <= walk_speed <= 12:
        raise ValueError("La vitesse de marche doit être comprise entre 0,1 et 12 blocs/s")
    result["walkSpeed"] = walk_speed
    scale_mode = config.get("scaleMode", "uniform")
    if scale_mode not in ("uniform", "vertical"):
        raise ValueError("Mode d’échelle invalide")
    result["scaleMode"] = scale_mode
    scale_head = config.get("scaleHead", True)
    if not isinstance(scale_head, bool):
        raise ValueError("Option de tête invalide")
    result["scaleHead"] = scale_head
    try:
        head_scale = float(config.get("headScale", 1))
    except (TypeError, ValueError) as error:
        raise ValueError("Échelle de tête invalide") from error
    if not .5 <= head_scale <= 10:
        raise ValueError("L’échelle de tête doit être comprise entre 0,5 et 10")
    result["headScale"] = head_scale
    color_defaults = {"skinColor": "#ECB880", "pupilColor": "#424039"}
    for key, label in (("hairColor", "cheveux"), ("skinColor", "peau"), ("pupilColor", "pupilles")):
        color = str(config.get(key, color_defaults.get(key, "")))
        if not re.fullmatch(r"#[0-9a-fA-F]{6}", color):
            raise ValueError(f"Couleur de {label} invalide")
        result[key] = color.upper()
    emotions = config.get("emotions", [])
    actions = config.get("actions", [])
    if not isinstance(emotions, list) or any(value not in EMOTIONS for value in emotions):
        raise ValueError("Liste d’émotions invalide")
    if not isinstance(actions, list) or len(actions) > len(ACTION_SPECS) or any(value not in ACTION_SPECS for value in actions):
        raise ValueError("Liste d’actions invalide")
    result["emotions"] = list(dict.fromkeys(emotions))
    result["actions"] = list(dict.fromkeys(actions))
    return result


def anatomy(root):
    skull = next(child for child in root["children"] if child.get("name") == "Group 14")
    feet = min(point[1] for corners, _ in boxes(root) for point in corners)
    skull_points = [point[1] for corners, _ in boxes({"children": [skull], "refs": root.get("refs", {})}) for point in corners]
    return feet, min(skull_points), max(skull_points)


def body_scale(height, scale_head, head_scale, dimensions):
    feet, head_bottom, head_top = dimensions
    scale = float(height / (head_top - feet))
    if not scale_head:
        scale = float(max(.05, (height - (head_top - head_bottom) * head_scale) / (head_bottom - feet)))
    return scale


def apply_scale(root, height, mode, scale_head, head_scale, dimensions):
    feet, head_bottom, head_top = dimensions
    scale = body_scale(height, scale_head, head_scale, dimensions)
    head = reparent_head(root)
    character = reparent_character(root)
    axes = (scale, scale, scale) if mode == "uniform" else (1, scale, 1)
    scale_rig = group("Scale Rig", (0, 0, 0), [character])
    scale_rig["transforms"] = [axes[0], 0, 0, 0, 0, axes[1], 0, 0, 0, 0, axes[2], 0, 0, 0, 0, 1]
    scale_rig["defaultTransform"]["scale"] = list(axes)
    root["children"][root["children"].index(character)] = scale_rig
    if not scale_head:
        inverse = tuple(head_scale / value for value in axes)
        skull_group = next(child for child in head["children"] if child.get("name") == "Group 14")
        head_root = {"children": [skull_group], "refs": root.get("refs", {})}
        head_bottom = min(point[1] for corners, _ in boxes(head_root) for point in corners)
        offset_y = head_bottom * (1 - inverse[1])
        compensation = group("Head Scale Compensation", (0, 0, 0), head["children"])
        compensation["transforms"] = [inverse[0], 0, 0, 0, 0, inverse[1], 0, offset_y, 0, 0, inverse[2], 0, 0, 0, 0, 1]
        compensation["defaultTransform"]["position"] = [0, offset_y, 0]
        compensation["defaultTransform"]["scale"] = list(inverse)
        head["children"] = [compensation]
    root["characterScale"] = {"value": height, "factor": scale, "unit": "blocks",
                              "mode": mode, "head": scale_head, "headScale": head_scale}


def compose(config, animated=True):
    model = (config["nose"], config["ears"], config["hair"], config["hairColor"],
             config["facialHair"], config["hat"], config["outfit"], config["accessory"])
    root = build(config["name"], model, config["skinColor"], config["bodyType"], config["pupilColor"], config["horns"], config["tail"], config["wings"])[0]
    dimensions = anatomy(root)
    eyebrows(root, config["eyebrows"])
    pupils(root, config["pupilStyle"])
    if animated:
        add_waiting(root, (config["waiting"],), generic_name=True)
        add_talking(root, (config["talking"],), generic_name=True)
        leg = next(node for node in walk(root) if node.get("name") == "left_leg")
        leg_length = (leg["defaultTransform"]["position"][1] - dimensions[0]) * body_scale(
            config["scale"], config["scaleHead"], config["headScale"], dimensions)
        add_walking(root, (config["walking"],), generic_name=True,
                    movement_speed=config["walkSpeed"], leg_length=leg_length)
        add_emotions(root, tuple(config["emotions"]))
        add_actions(root, [ACTION_SPECS[name] for name in config["actions"]])
        animate_tail(root)
        animate_wings(root)
    apply_scale(root, config["scale"], config["scaleMode"], config["scaleHead"], config["headScale"], dimensions)
    root["name"] = config["name"]
    root["mainNBT"] = config["name"]
    root["nbt"] = str(config["walkSpeed"])
    root["editorConfig"] = config
    root["editorAnimationCount"] = len(root.get("listAnim", []))
    return root


def imported_config(root):
    config = dict(root.get("editorConfig") or {})
    if root.get("characterScale", {}).get("unit") != "blocks" and "scale" in config:
        config["scale"] = float(config["scale"]) * DEFAULT_HEIGHT
    return validate(config)


def slug(text):
    normalized = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "_", normalized).strip("_") or "villager"


def imported_component(data, category, name):
    if category not in COMPONENT_IMPORTS:
        raise ValueError("Type de composant invalide")
    clean_name = slug(str(name)[:60])
    folder, prefix, group_prefix, field = COMPONENT_IMPORTS[category]
    source = loads(data)

    def multiply(left, right):
        return [sum(left[row * 4 + index] * right[index * 4 + column] for index in range(4))
                for row in range(4) for column in range(4)]

    identity = [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1]
    records, stack = [], [(source, identity)]
    while stack:
        node, parent = stack.pop()
        world = multiply(parent, node.get("transforms", identity))
        records.append((node, world))
        stack.extend((child, world) for child in node.get("children", []))

    matches = [(node, world) for node, world in records
               if node.get("isCollection") and node.get("name", "").startswith(group_prefix)]
    if not matches:
        raise ValueError(f"Composant {group_prefix} introuvable dans ce modèle")
    group = copy.deepcopy(matches[0][0])
    group["transforms"] = matches[0][1]
    if category in ("body", "outfit"):
        parts = []
        for part_name in ("Torso", "left_arm", "right_arm", "left_leg", "right_leg"):
            match = next(((node, world) for node, world in records
                          if node.get("isCollection") and node.get("name") == part_name), None)
            if not match:
                raise ValueError(f"Groupe anatomique {part_name} introuvable")
            part = copy.deepcopy(match[0])
            part["transforms"] = match[1]
            parts.append(part)
        group["transforms"] = identity
        group["children"] = parts

    def remove_nested(node, prefixes):
        node["children"] = [child for child in node.get("children", [])
                            if not child.get("name", "").startswith(prefixes)]
        for child in node["children"]:
            if child.get("isCollection"):
                remove_nested(child, prefixes)

    if category == "body":
        remove_nested(group, ("Clothing -", "Accessory -"))
    elif category == "outfit":
        remove_nested(group, ("Accessory -",))
    if group_prefix != "Body Structure":
        group["name"] = f"{group_prefix} {clean_name}"

    source_textures = source.get("refs", {}).get("paintTextures", [])
    used = sorted({node["paintTexture"] for node in walk(group)
                   if isinstance(node.get("paintTexture"), int)
                   and 0 <= node["paintTexture"] < len(source_textures)})
    remap = {old: new for new, old in enumerate(used)}
    for node in walk(group):
        if isinstance(node.get("paintTexture"), int):
            if node["paintTexture"] in remap:
                node["paintTexture"] = remap[node["paintTexture"]]
            else:
                node.pop("paintTexture")

    config = source.get("editorConfig", {})
    asset = {
        "isCollection": True, "isBackCollection": False,
        "name": f"Custom {category} - {clean_name}", "nbt": "",
        "transforms": [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1],
        "children": [group],
        "refs": {"paintTextures": [source_textures[index] for index in used]},
        "customComponent": {
            "category": category, "name": clean_name,
            "baseBodyType": config.get("bodyType", "standard"),
        },
    }
    target_dir = ROOT / "bdengine" / "characters" / "villagers" / folder
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / f"{prefix}{clean_name}.bdengine"
    index = 2
    while target.exists():
        target = target_dir / f"{prefix}{clean_name}_{index}.bdengine"
        index += 1
    actual_name = target.stem.removeprefix(prefix)
    asset["customComponent"]["name"] = actual_name
    write([asset], target)
    value = f"moustache_{actual_name}" if category == "moustache" else actual_name
    return target, field, value


def available_export(name):
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    base = slug(name)
    candidate = EXPORT_DIR / f"villager_{base}.bdengine"
    index = 2
    while candidate.exists():
        candidate = EXPORT_DIR / f"villager_{base}_{index}.bdengine"
        index += 1
    return candidate


class Handler(BaseHTTPRequestHandler):
    def json_response(self, payload, status=200):
        data = json.dumps(payload, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def file_response(self, path, content_type):
        if not path.is_file():
            self.send_error(404)
            return
        data = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/api/catalog":
            self.json_response(CATALOG)
        elif path == "/preview.png":
            self.file_response(PREVIEW_DIR / "current_preview.png", "image/png")
        elif path in ("/", "/index.html"):
            self.file_response(WEB_DIR / "index.html", "text/html; charset=utf-8")
        elif path == "/app.css":
            self.file_response(WEB_DIR / "app.css", "text/css; charset=utf-8")
        elif path == "/app.js":
            self.file_response(WEB_DIR / "app.js", "text/javascript; charset=utf-8")
        else:
            self.send_error(404)

    def do_POST(self):
        global CATALOG, LAST_PREVIEW
        path = urlparse(self.path).path
        if path not in ("/api/preview", "/api/export", "/api/import", "/api/component/import"):
            self.send_error(404)
            return
        try:
            length = int(self.headers.get("Content-Length", 0))
            limit = 10 * 1024 * 1024 if path == "/api/component/import" else (5 * 1024 * 1024 if path == "/api/import" else 65536)
            if length <= 0 or length > limit:
                raise ValueError("Taille de requête invalide")
            if path == "/api/import":
                root = loads(self.rfile.read(length))
                config = imported_config(root)
                self.json_response({"config": config, "name": config["name"]})
                return
            payload = json.loads(self.rfile.read(length))
            if path == "/api/component/import":
                target, field, value = imported_component(
                    base64.b64decode(payload.get("data", "")), payload.get("category"), payload.get("name", "")
                )
                CATALOG = catalog()
                self.json_response({"field": field, "value": value, "file": str(target.relative_to(ROOT))})
                return
            config = validate(payload)
            with BUILD_LOCK:
                if path == "/api/preview":
                    PREVIEW_DIR.mkdir(parents=True, exist_ok=True)
                    temporary = PREVIEW_DIR / "current.bdengine"
                    signature = tuple(config[key] for key in PREVIEW_KEYS)
                    if signature != LAST_PREVIEW or not (PREVIEW_DIR / "current_preview.png").exists():
                        write([compose(config, animated=False)], temporary)
                        render(temporary, PREVIEW_DIR / "current_preview.png", dpi=100, player_reference=True)
                        LAST_PREVIEW = signature
                    self.json_response({"preview": "/preview.png", "name": config["name"]})
                else:
                    output = available_export(config["name"])
                    root = compose(config, animated=True)
                    write([root], output)
                    preview = PREVIEW_DIR / f"{output.stem}_preview.png"
                    render(output, preview)
                    self.json_response({
                        "file": str(output.relative_to(ROOT)), "preview": str(preview.relative_to(ROOT)),
                        "animations": len(root["listAnim"]),
                    })
        except (ValueError, KeyError, json.JSONDecodeError) as error:
            self.json_response({"error": str(error)}, 400)

    def log_message(self, fmt, *args):
        print(f"[editor] {fmt % args}")


def self_test():
    rasterizer_self_test()
    assert all(validate(preset) for preset in CATALOG["presets"].values())
    sample = validate(CATALOG["presets"]["mira_farmer"])
    root = compose(sample)
    assert root["faceStyle"] == "feminine_thin_eyebrows"
    assert (root["mainNBT"], root["nbt"]) == (sample["name"], str(sample["walkSpeed"]))
    for chain in (("left_arm", "left_elbow", "left_wrist"), ("right_arm", "right_elbow", "right_wrist"),
                  ("left_leg", "left_knee", "left_ankle"), ("right_leg", "right_knee", "right_ankle")):
        parent = next(node for node in walk(root) if node.get("name") == chain[0])
        for name in chain[1:]:
            parent = next(child for child in parent["children"] if child.get("name") == name)
        assert parent.get("defaultTransform")
    assert {node.get("name") for node in walk(root)} >= {"Left Ear Rig", "Right Ear Rig"}
    assert all(any(key == "animation" or key.startswith("animation_") for key in next(node for node in walk(root) if node.get("name") == limb))
               for limb in ("left_arm", "right_arm", "left_leg", "right_leg"))
    walk_control = root["walkingController"]["animations"]["walking"]
    assert walk_control["movementSpeed"] == sample["walkSpeed"]
    assert walk_control["cycleDurationTicks"] < WALKING[sample["walking"]]["duration"]
    faster = compose({**sample, "walkSpeed": sample["walkSpeed"] * 2})
    assert faster["walkingController"]["animations"]["walking"]["cycleDurationTicks"] < walk_control["cycleDurationTicks"]
    runner = compose(validate(CATALOG["presets"]["cedric_guard"]))
    run_control = runner["runningController"]
    runner_walk = runner["walkingController"]["animations"]["walking"]
    assert run_control["movementSpeed"] == runner_walk["movementSpeed"] * 2
    assert run_control["cycleDurationTicks"] < runner_walk["cycleDurationTicks"]
    running = ACTION_SPECS["locomotion_running"][2]
    assert len(running["left_leg"]) == 9 and max(abs(pose[1][0]) for pose in running["left_leg"]) >= 60
    assert all(len(running[joint]) >= 5 for joint in ("left_knee", "right_knee", "left_ankle", "right_ankle",
                                                     "left_elbow", "right_elbow", "left_wrist", "right_wrist"))
    assert all(pose[1][0] < 0 for pose in running["left_elbow"])
    assert max(pose[2][1] for pose in running["body_motion"]) >= .13
    walking_animation = next(item for item in root["listAnim"] if item["name"] == "walking")
    walking_field = animation_field(walking_animation["id"])
    assert min(key["rotation"]["x"] for key in next(
        node for node in walk(root) if node.get("name") == "left_elbow")[walking_field]) > 0
    assert all(max(pose[1][0] for pose in ACTION_SPECS[action][2]["left_elbow"]) < 0
               for action in ("locomotion_running", "locomotion_sneaking",
                              "locomotion_limping", "locomotion_carrying_walk"))
    ground_actions = ("daily_sit", "daily_kneel", "daily_sleep")
    assert all(ACTION_SPECS[action][2]["left_elbow"][1][1][0] < 0
               for action in ("daily_sit", "daily_kneel", "daily_sleep"))
    ground_root = compose({**sample, "actions": list(ground_actions)})
    for action in ground_actions:
        animation = next(item for item in ground_root["listAnim"] if item["name"] == action)
        field = animation_field(animation["id"])
        assert all(field in next(node for node in walk(ground_root) if node.get("name") == joint)
                   for joint in ("left_knee", "right_knee", "left_ankle", "right_ankle",
                                 "left_elbow", "right_elbow", "left_wrist", "right_wrist"))
        for joint in ("left_elbow", "right_elbow"):
            elbow = next(node for node in walk(ground_root) if node.get("name") == joint)
            assert min(key["rotation"]["x"] for key in elbow[field]) >= 0
    assert all(any(key == "animation" or key.startswith("animation_")
                   for key in next(node for node in walk(root) if node.get("name") == joint))
               for joint in ("left_knee", "right_knee", "left_ankle", "right_ankle",
                             "left_elbow", "right_elbow", "left_wrist", "right_wrist"))
    legacy_face = dict(sample)
    legacy_face.pop("eyebrows")
    assert validate(legacy_face)["eyebrows"] == "thin"
    legacy_walk = dict(sample)
    legacy_walk.pop("walkSpeed")
    assert validate(legacy_walk)["walkSpeed"] > 0
    assert set(CATALOG["components"]["eyebrows"]) == set(EYEBROWS)
    assert set(CATALOG["components"]["pupilStyle"]) == set(PUPILS)
    assert {"short", "long", "curved", "ram", "draconic", "moose", "reindeer", "roe_deer", "unicorn"} <= set(CATALOG["components"]["horns"])
    assert {"none", "cat", "wolf", "fox", "rabbit", "deer", "goat", "horse", "ogre"} <= set(CATALOG["components"]["ears"])
    assert {"wolf", "fox", "cat", "deer", "rabbit", "horse", "goat", "dragon",
            "lizard", "crocodile", "iguana", "serpent"} <= set(CATALOG["components"]["tail"])
    assert {"dragon", "bird", "angel", "demonic", "butterfly", "insect"} <= set(CATALOG["components"]["wings"])
    horned_presets = {"varkos_dragonkin", "bryn_moose_warden", "yrsa_reindeer_oracle", "fenn_roe_scout", "maela_faun"}
    assert horned_presets <= set(CATALOG["presets"])
    dragonkin = CATALOG["presets"]["varkos_dragonkin"]
    assert (dragonkin["horns"], dragonkin["tail"], dragonkin["wings"], dragonkin["pupilStyle"]) == ("draconic", "dragon", "dragon", "vertical_slit")
    for style in EYEBROWS:
        face = compose(validate({**sample, "eyebrows": style, "hair": "bald", "facialHair": "", "hat": ""}), animated=False)
        brow_counts = [len(next(node for node in walk(face) if node.get("name") == name)["children"])
                       for name in ("Group 17", "Group 18")]
        expected = {"none": [0, 0], "arched": [3, 3], "bushy": [2, 2]}.get(style, [1, 1])
        assert brow_counts == expected
    horned = compose(validate({**sample, "horns": "short"}), animated=False)
    head_rig = next(node for node in walk(horned) if node.get("name") == "Head Rig")
    assert any(node.get("name") == "Horns - short" for node in head_rig["children"])
    unicorn = compose(validate({**sample, "horns": "unicorn", "hair": "bald", "hat": ""}), animated=False)
    assert len(next(node for node in walk(unicorn) if node.get("name") == "Horns - unicorn")["children"]) == 6
    earless = compose(validate({**sample, "ears": "none"}), animated=False)
    assert not next(node for node in walk(earless) if node.get("name") == "Ears - none")["children"]
    default_pupil = next(node for node in walk(root) if node.get("name") == "left_eye")["children"][0]["transforms"]
    default_pupil_center = default_pupil[7] - default_pupil[5] / 4
    for style in PUPILS:
        face = compose(validate({**sample, "pupilStyle": style}), animated=False)
        assert all(len(next(node for node in walk(face) if node.get("name") == eye)["children"]) == (3 if style == "round" else 1)
                   for eye in ("left_eye", "right_eye"))
        pieces = next(node for node in walk(face) if node.get("name") == "left_eye")["children"]
        centers = [piece["transforms"][7] - piece["transforms"][5] / 4 for piece in pieces]
        assert abs(sum(centers) / len(centers) - default_pupil_center) < 1e-9
    tailed = compose(validate({**sample, "tail": "fox"}), animated=False)
    body = next(node for node in walk(tailed) if node.get("name") == "Body Structure")
    assert any(node.get("name") == "Tail - fox" for node in body["children"])
    moving_tail = compose(validate({**sample, "tail": "fox", "hairColor": "#345678"}))
    tail_rig = next(node for node in walk(moving_tail) if node.get("name") == "Tail - fox")
    tip_rig = next(node for node in tail_rig["children"] if node.get("name") == "Tail Tip Rig")
    assert tail_rig["tailColor"] == "#345678" and "animation" in tail_rig and "animation" in tip_rig
    winged = compose(validate({**sample, "wings": "angel"}))
    wing_group = next(node for node in walk(winged) if node.get("name") == "Wings - angel")
    wing_rigs = [node for node in walk(wing_group) if node.get("name", "").endswith("Wing Rig")]
    upper_rig = next(node for node in walk(winged) if node.get("name") == "Upper Body Rig")
    assert len(wing_rigs) == 4 and all("animation" in rig for rig in wing_rigs)
    assert any(node is wing_group for node in walk(upper_rig))
    assert root["editorAnimationCount"] == len(root["listAnim"]) == 21
    assert [animation["name"] for animation in root["listAnim"][:3]] == ["waiting", "talking", "walking"]
    special_animations = {"monster", "villain", "idiot", "barbarian"}
    assert special_animations <= set(WAITING) & set(TALKING) & set(WALKING)
    assert (CATALOG["presets"]["goblin_raider"]["waiting"], CATALOG["presets"]["goblin_raider"]["talking"],
            CATALOG["presets"]["goblin_raider"]["walking"]) == ("idiot", "monster", "monster")
    assert {"buzz_cut", "mohawk", "afro", "dreadlocks", "ponytail", "pigtails", "bun", "double_buns"} <= set(CATALOG["components"]["hair"])
    assert {"stubble", "moustache_stubble"} <= set(CATALOG["components"]["facialHair"])
    assert all(any((ROOT / "bdengine" / "characters" / "villagers" / "headwear").rglob(f"villager_hat_{name}.bdengine"))
               for name in CATALOG["components"]["hat"])
    assert not any(name.startswith("villager_horns_") for name in CATALOG["components"]["hat"])
    assert CATALOG["components"]["hair"][0] == "bald"
    assert {"monster_raider", "monster_shaman", "monster_warrior",
            "knight_plate", "knight_noble", "knight_black"} <= set(CATALOG["components"]["outfit"])
    assert "great_helm" in CATALOG["components"]["hat"]
    assert {"goblin", "orc", "brute", "chubby"} <= set(CATALOG["components"]["bodyType"])
    assert {"goblin", "orc", "brute"} <= set(CATALOG["randomization"]["monsterBodies"])
    assert set(CATALOG["randomization"]["monsterOutfits"]) == {"monster_raider", "monster_shaman", "monster_warrior"}
    for body_type in ("goblin", "orc", "brute", "chubby"):
        for _, top, bottom, palette in OUTFIT_PRESETS.values():
            assert build_outfit(body_type, top, bottom, palette)[1] > 0
    chubby_outfit = build_outfit("chubby", "plain_tunic", "plain_trousers", "common")[0][0]
    for accessory in ACCESSORIES:
        assert combine_with_outfit(accessory, chubby_outfit)[0]["accessories"] == [accessory]
    for profile in BODY_TYPES.values():
        scabbard = next(spec for spec in make_accessory("sword_scabbard", profile)["Torso"]
                        if spec[0] == "scabbard_body")
        assert max(profile["waist"], profile.get("belly", 0)) / 2 < scabbard[1][0] < profile["shoulder"]
    assert {"villain_threaten", "villain_evil_laugh", "villain_intimidate", "villain_slash"} <= set(ACTION_SPECS)
    goblin = CATALOG["presets"]["goblin_raider"]
    assert goblin["bodyType"] == "goblin" and goblin["skinColor"] == "#424D3D"
    assert {"villain_threaten", "villain_evil_laugh", "villain_intimidate", "villain_slash"} <= set(goblin["actions"])
    assert CATALOG["presets"]["chubby_villager"]["bodyType"] == "chubby"
    assert abs(sum(preset["scale"] for preset in CATALOG["presets"].values()) /
               len(CATALOG["presets"]) - 1.9) < .02
    women = [preset["scale"] for preset in CATALOG["presets"].values() if preset["gender"] == "female"]
    men = [preset["scale"] for preset in CATALOG["presets"].values() if preset["gender"] == "male"]
    assert sum(women) / len(women) < sum(men) / len(men) - .15
    for child in ("elise_smith", "luc_shepherd"):
        assert CATALOG["presets"][child]["scale"] < 1.5 and not CATALOG["presets"][child]["scaleHead"]
    assert CATALOG["presets"]["goblin_raider"]["scale"] == 1.52
    assert CATALOG["presets"]["chubby_villager"]["scale"] == 2.28
    assert CATALOG["presets"]["elise_smith"]["scaleHead"] is False
    scaled = compose(validate({**CATALOG["presets"]["mira_farmer"], "scale": 1.4,
                               "scaleMode": "uniform", "scaleHead": False, "headScale": .8,
                               "hair": "bald", "facialHair": "", "hat": "", "accessory": ""}), animated=False)
    factor = scaled["characterScale"]["factor"]
    assert scaled["characterScale"]["value"] == 1.4 and scaled["characterScale"]["unit"] == "blocks"
    assert next(node for node in walk(scaled) if node.get("name") == "Scale Rig")["defaultTransform"]["scale"] == [factor] * 3
    assert next(node for node in walk(scaled) if node.get("name") == "Head Scale Compensation")["defaultTransform"]["scale"] == [.8 / factor] * 3
    player = reference_player(boxes(scaled))
    player_y = [point[1] for corners, _ in player for point in corners]
    model_y = [point[1] for corners, _ in boxes(scaled) for point in corners]
    assert abs(max(model_y) - min(model_y) - 1.4) < 1e-9
    assert abs(min(player_y) - min(model_y)) < 1e-9 and abs(max(player_y) - min(player_y) - 1.8) < 1e-9
    legacy = dict(CATALOG["presets"]["mira_farmer"])
    for key in ("scale", "scaleMode", "scaleHead", "headScale"):
        legacy.pop(key)
    assert {key: validate(legacy)[key] for key in ("scale", "scaleMode", "scaleHead", "headScale")} == {
        "scale": DEFAULT_HEIGHT, "scaleMode": "uniform", "scaleHead": True, "headScale": 1.0,
    }
    assert imported_config({"editorConfig": {**sample, "scale": 1}, "characterScale": {"value": 1}})["scale"] == DEFAULT_HEIGHT
    assert compose(validate({**CATALOG["presets"]["mira_farmer"], "outfit": "monster_warrior",
                             "bodyType": "brute", "hair": "bald", "hat": "", "facialHair": "",
                             "accessory": ""}), animated=False)
    assert compose(validate({**CATALOG["presets"]["mira_farmer"], "outfit": "knight_plate",
                             "bodyType": "chubby", "hair": "bald", "hat": "great_helm",
                             "facialHair": "", "accessory": ""}), animated=False)
    assert slug("Élise du Pont") == "elise_du_pont"
    print("Villager editor self-test passed")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--no-browser", action="store_true")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test()
        return
    server = ThreadingHTTPServer((args.host, args.port), Handler)
    url = f"http://{args.host}:{args.port}"
    print(f"Villager editor: {url}")
    if not args.no_browser:
        threading.Timer(.5, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
