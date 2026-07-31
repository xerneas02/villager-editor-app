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

from generate_villager_action_animations import add_animations as add_actions, specifications
from generate_villager_accessories import walk
from generate_villager_body import BODY_TYPES
from generate_villager_clothing import PRESETS as OUTFIT_PRESETS, build as build_outfit
from generate_villager_emotion_animations import EMOTIONS, add_animations as add_emotions
from generate_villager_examples import build, write
from generate_villager_population import COMMON, POPULATION, thin_eyebrows
from generate_villager_talking_animations import PERSONALITIES as TALKING, add_animations as add_talking
from generate_villager_waiting_animations import PERSONALITIES as WAITING, add_animations as add_waiting
from generate_villager_walking_animations import PROFILES as WALKING, add_animations as add_walking
from preview_bdengine import load, loads, render


ROOT = Path(__file__).resolve().parent.parent
WEB_DIR = ROOT / "villager_editor"
PREVIEW_DIR = ROOT / "previews" / "characters" / "villagers" / "editor"
EXPORT_DIR = ROOT / "bdengine" / "characters" / "villagers" / "custom"
ACTION_SPECS = {f"{category.removesuffix('s')}_{name}": (category, name, profile)
                for category, name, profile in specifications()}
BUILD_LOCK = threading.Lock()
PREVIEW_KEYS = ("gender", "nose", "ears", "hair", "hairColor", "skinColor", "pupilColor", "facialHair", "hat", "bodyType", "outfit", "accessory")
LAST_PREVIEW = None
COMPONENT_IMPORTS = {
    "ears": ("heads/ears", "villager_ears_", "Ears -", "ears"),
    "nose": ("heads/noses", "villager_nose_", "Nose -", "nose"),
    "hair": ("hair", "villager_hair_", "Hair -", "hair"),
    "hat": ("headwear/custom", "villager_hat_", "Hat -", "hat"),
    "beard": ("facial_hair/beards", "villager_beard_", "Facial Hair -", "facialHair"),
    "moustache": ("facial_hair/moustaches", "villager_moustache_", "Facial Hair -", "facialHair"),
    "outfit": ("clothing/outfits", "villager_outfit_", "Body Structure", "outfit"),
    "body": ("bodies", "villager_body_", "Body Structure", "bodyType"),
}


def stems(folder, prefix):
    return sorted(path.stem.removeprefix(prefix) for path in folder.rglob("*.bdengine"))


def catalog():
    villagers = ROOT / "bdengine" / "characters" / "villagers"
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
            "nose": nose, "ears": ears, "hair": hair, "hairColor": hair_color,
            "skinColor": "#ECB880", "pupilColor": "#424039",
            "facialHair": facial_hair or "", "hat": hat or "", "bodyType": body_type, "outfit": outfit,
            "accessory": accessory or "", "waiting": waiting, "talking": talking,
            "walking": walking, "emotions": list(emotions),
            "actions": list(dict.fromkeys(COMMON + extra)),
        }
    return {
        "components": {
            "nose": stems(villagers / "heads" / "noses", "villager_nose_"),
            "ears": stems(villagers / "heads" / "ears", "villager_ears_"),
            "hair": ["bald", *stems(villagers / "hair", "villager_hair_")],
            "facialHair": sorted(facial),
            "hat": stems(villagers / "headwear", "villager_hat_"),
            "outfit": stems(villagers / "clothing" / "outfits", "villager_outfit_"),
            "accessory": stems(villagers / "accessories", "villager_accessory_"),
            "bodyType": [*BODY_TYPES, *sorted(
                load(path).get("customComponent", {}).get("name")
                for path in (villagers / "bodies").glob("*.bdengine")
                if load(path).get("customComponent", {}).get("category") == "body"
            )],
        },
        "animations": {
            "waiting": list(WAITING), "talking": list(TALKING), "walking": list(WALKING),
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
        "nose": choice(config, "nose", components["nose"]),
        "ears": choice(config, "ears", components["ears"]),
        "hair": choice(config, "hair", components["hair"]),
        "facialHair": choice(config, "facialHair", components["facialHair"], True),
        "hat": choice(config, "hat", components["hat"], True),
        "bodyType": choice(config, "bodyType", components["bodyType"]),
        "outfit": choice(config, "outfit", components["outfit"]),
        "accessory": choice(config, "accessory", components["accessory"], True),
        "waiting": choice(config, "waiting", CATALOG["animations"]["waiting"]),
        "talking": choice(config, "talking", CATALOG["animations"]["talking"]),
        "walking": choice(config, "walking", CATALOG["animations"]["walking"]),
    }
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


def compose(config, animated=True):
    model = (config["nose"], config["ears"], config["hair"], config["hairColor"],
             config["facialHair"], config["hat"], config["outfit"], config["accessory"])
    root = build(config["name"], model, config["skinColor"], config["bodyType"], config["pupilColor"])[0]
    if config["gender"] == "female":
        thin_eyebrows(root)
    if animated:
        add_waiting(root, (config["waiting"],), generic_name=True)
        add_talking(root, (config["talking"],), generic_name=True)
        add_walking(root, (config["walking"],), generic_name=True)
        add_emotions(root, tuple(config["emotions"]))
        add_actions(root, [ACTION_SPECS[name] for name in config["actions"]])
    root["name"] = config["name"]
    root["editorConfig"] = config
    root["editorAnimationCount"] = len(root.get("listAnim", []))
    return root


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
                config = validate(root.get("editorConfig"))
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
                        render(temporary, PREVIEW_DIR / "current_preview.png", dpi=100)
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
    sample = validate(CATALOG["presets"]["mira_farmer"])
    root = compose(sample)
    assert root["faceStyle"] == "feminine_thin_eyebrows"
    assert root["editorAnimationCount"] == len(root["listAnim"]) == 21
    assert [animation["name"] for animation in root["listAnim"][:3]] == ["waiting", "talking", "walking"]
    assert CATALOG["components"]["hair"][0] == "bald"
    assert {"monster_raider", "monster_shaman", "monster_warrior"} <= set(CATALOG["components"]["outfit"])
    assert {"goblin", "orc", "brute"} <= set(CATALOG["components"]["bodyType"])
    for body_type in ("goblin", "orc", "brute"):
        for _, top, bottom, palette in OUTFIT_PRESETS.values():
            assert build_outfit(body_type, top, bottom, palette)[1] > 0
    assert {"villain_threaten", "villain_evil_laugh", "villain_intimidate", "villain_slash"} <= set(ACTION_SPECS)
    assert compose(validate({**CATALOG["presets"]["mira_farmer"], "outfit": "monster_warrior",
                             "bodyType": "brute", "hair": "bald", "hat": "", "facialHair": "",
                             "accessory": ""}), animated=False)
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
