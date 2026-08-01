"""Compose ten example villagers from the modular character collection."""

import base64
import copy
import gzip
import io
import json
from pathlib import Path

from PIL import Image, ImageColor, ImageDraw

from generate_villager_accessories import OUTFIT_DIR, combine_with_outfit, walk
from generate_villager_body import BODY_DIR, BODY_TYPES, anchor_joints
from generate_villager_clothing import PRESETS as OUTFIT_PRESETS, build as build_outfit
from generate_villager_ears import EAR_DIR, anchor_ears, original_ears
from generate_villager_faces import find
from generate_villager_hair import HAIR_DIR, HEAD_DIR, STYLES as HAIR_STYLES, build as build_hair, texture, tint
from generate_villager_hats import HATS, build as build_hat
from generate_villager_horns import HORN_DIR
from generate_villager_noses import NOSE_DIR
from generate_villager_tails import FURRY, TAIL_DIR, TAILS, build as build_tail
from generate_villager_wings import WING_DIR, WINGS, build as build_wings
from preview_bdengine import load, render, url_texture


ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = ROOT / "bdengine" / "characters" / "villagers" / "examples"
PREVIEW_DIR = ROOT / "previews" / "characters" / "villagers" / "examples"
FACIAL_DIR = OUTPUT_DIR.parent / "facial_hair"
BASE_SKIN = (236, 184, 128)
SKIN_COLORS = {BASE_SKIN, (214, 178, 123)}

EXAMPLES = {
    "elder_farmer": ("broad", "broad", "short_heroic", "#76604A", "trimmed", "straw_hat", "farmer_m", "tool_belt"),
    "village_blacksmith": ("rounded", "small", "swept", "#3E3028", "forked", None, "blacksmith", "leather_bracers"),
    "town_guard": ("default", "rounded", "short_heroic", "#5C4637", "moustache_classic", "kettle_helmet", "guard", "sword_scabbard"),
    "forest_huntress": ("small", "small", "braided", "#6C3F28", None, None, "hunter", "quiver"),
    "young_cleric": ("long", "rounded", "swept", "#A4825D", None, "soft_cap", "clergy", "amulet"),
    "noblewoman": ("upturned", "small", "very_long_loose", "#C49A58", None, "noble_cap", "noble_f", "shoulder_mantle"),
    "road_traveler": ("aquiline", "broad", "swept", "#4A3428", "moustache_handlebar", "felt_hat", "traveler_m", "satchel"),
    "village_artisan": ("rounded", "rounded", "braided", "#8B5C3E", None, "round_cap", "common_f", "neck_scarf"),
    "elven_ranger": ("small", "elf_long", "elven_half_up", "#BCA06C", None, None, "traveler_f", "quiver"),
    "elven_scholar": ("aquiline", "elf_short", "elven_cascade", "#E0C58D", None, "pointed_cap", "well_dressed_f", "amulet"),
}


def groups(root, prefix):
    return [node for node in root.get("children", []) if node.get("name", "").startswith(prefix)]


def merge_groups(target, source, selected):
    clones = copy.deepcopy(selected)
    source_textures = source.get("refs", {}).get("paintTextures", [])
    target_textures = target.setdefault("refs", {}).setdefault("paintTextures", [])
    used = sorted({
        node["paintTexture"] for group in clones for node in walk(group)
        if isinstance(node.get("paintTexture"), int)
    })
    remap = {index: len(target_textures) + offset for offset, index in enumerate(used)}
    target_textures.extend(source_textures[index] for index in used)
    for group in clones:
        for node in walk(group):
            if node.get("paintTexture") in remap:
                node["paintTexture"] = remap[node["paintTexture"]]
    target["children"].extend(clones)
    return remap


def library_file(folder, prefix, name):
    path = next(folder.rglob(f"{prefix}{name}.bdengine"), None)
    if path is None:
        raise ValueError(f"Composant introuvable : {name}")
    return path


def replace_body(target, source):
    source_textures = source.get("refs", {}).get("paintTextures", [])
    target_textures = target.setdefault("refs", {}).setdefault("paintTextures", [])
    for name in ("Torso", "left_arm", "right_arm", "left_leg", "right_leg"):
        destination = find(target, name)
        originals = [copy.deepcopy(node) for node in find(source, name).get("children", [])
                     if not node.get("isCollection")]
        used = sorted({node["paintTexture"] for item in originals for node in walk(item)
                       if isinstance(node.get("paintTexture"), int) and node["paintTexture"] < len(source_textures)})
        remap = {old: len(target_textures) + index for index, old in enumerate(used)}
        target_textures.extend(source_textures[index] for index in used)
        for item in originals:
            for node in walk(item):
                if node.get("paintTexture") in remap:
                    node["paintTexture"] = remap[node["paintTexture"]]
        destination["children"] = originals + [node for node in destination.get("children", []) if node.get("isCollection")]


def match_eyebrows(root, hair_source, remap):
    hair = groups(hair_source, "Hair -")
    primary = min(node["paintTexture"] for node in walk(hair[0])
                  if isinstance(node.get("paintTexture"), int))
    for name in ("Group 17", "Group 18"):
        find(root, name)["children"][0]["paintTexture"] = remap[primary]


def color_eyebrows(root, color):
    textures = root.setdefault("refs", {}).setdefault("paintTextures", [])
    textures.append(texture(tint(color, .82)))
    for name in ("Group 17", "Group 18"):
        find(root, name)["children"][0]["paintTexture"] = len(textures) - 1


def color_pupils(root, color):
    textures = root.setdefault("refs", {}).setdefault("paintTextures", [])
    textures.append(texture(ImageColor.getrgb(color)))
    for name in ("left_eye", "right_eye"):
        eye = find(root, name)["children"][0]
        eye["paintTexture"] = len(textures) - 1
        eye["defaultTextureValue"] = ""
        eye["textureValueList"] = []
        eye.setdefault("tagHead", {})["Value"] = ""


def recolor_skin(root, color):
    target = ImageColor.getrgb(color)
    if target == BASE_SKIN:
        return

    def recolored(data):
        image = Image.open(io.BytesIO(data)).convert("RGBA")
        pixels = image.load()
        for y in range(image.height):
            for x in range(image.width):
                if pixels[x, y][:3] in SKIN_COLORS:
                    pixels[x, y] = target + (pixels[x, y][3],)
        output = io.BytesIO()
        image.save(output, "PNG", optimize=True)
        return "data:image/png;base64," + base64.b64encode(output.getvalue()).decode()

    textures = root.setdefault("refs", {}).setdefault("paintTextures", [])
    for index, value in enumerate(textures):
        encoded = (value or "").partition(",")[2]
        if encoded:
            textures[index] = recolored(base64.b64decode(encoded))

    added = {}
    for node in walk(root):
        value = node.get("defaultTextureValue")
        if not value:
            continue
        if node.get("paintTexture") is None:
            payload = json.loads(base64.b64decode(value))
            url = payload["textures"]["SKIN"]["url"]
            if url not in added:
                textures.append(recolored(url_texture(url)))
                added[url] = len(textures) - 1
            node["paintTexture"] = added[url]
        node["defaultTextureValue"] = ""
        node["textureValueList"] = []
        node.setdefault("tagHead", {})["Value"] = ""


def recolor(root, prefix, color):
    selected = groups(root, prefix)
    used = sorted({
        node["paintTexture"] for group in selected for node in walk(group)
        if isinstance(node.get("paintTexture"), int)
    })
    for index, factor in zip(used, (1, .82, 1.12)):
        root["refs"]["paintTextures"][index] = texture(tint(color, factor))


def facial_source(style):
    if style.startswith("moustache_") and style != "moustache_goatee":
        return FACIAL_DIR / "moustaches" / f"villager_moustache_{style.removeprefix('moustache_')}.bdengine"
    return FACIAL_DIR / "beards" / f"villager_beard_{style}.bdengine"


def build(name, preset, skin_color="#ECB880", body_type=None, pupil_color="#424039", horns=None, tail=None, wings=None):
    nose, ears, hair, hair_color, facial, hat, outfit, accessory = preset
    nose_source = load(NOSE_DIR / f"villager_nose_{nose}.bdengine")
    if nose_source.get("customComponent", {}).get("category") == "nose":
        root = copy.deepcopy(load(HEAD_DIR / "villager_head.bdengine"))
        base_texture_count = len(root.get("refs", {}).get("paintTextures", []))
        for node in walk(root):
            if isinstance(node.get("paintTexture"), int) and node["paintTexture"] >= base_texture_count:
                node.pop("paintTexture")
        merge_groups(root, nose_source, groups(nose_source, "Nose -"))
    else:
        root = copy.deepcopy(nose_source)
    texture_count = len(root.get("refs", {}).get("paintTextures", []))
    for node in walk(root):
        if isinstance(node.get("paintTexture"), int) and node["paintTexture"] >= texture_count:
            node.pop("paintTexture")

    ear_source = load(EAR_DIR / f"villager_ears_{ears}.bdengine")
    head = find(root, "head")
    old_ears = original_ears(head)
    head["children"] = [child for child in head["children"] if child not in old_ears]
    merge_groups(root, ear_source, groups(ear_source, "Ears -"))

    outfit_source = load(library_file(OUTFIT_DIR, "villager_outfit_", outfit))
    custom_outfit = outfit_source.get("customComponent", {}).get("category") == "outfit"
    clothing = outfit_source.get("clothing")
    if not clothing:
        if custom_outfit:
            clothing = {"body": outfit_source["customComponent"]["baseBodyType"]}
        else:
            body, top, bottom, palette = OUTFIT_PRESETS[outfit]
            clothing = {"body": body, "top": top, "bottom": bottom, "palette": palette}
    selected_body = body_type or clothing["body"]
    custom_body = None
    build_body = selected_body
    if selected_body not in BODY_TYPES:
        custom_body = load(library_file(BODY_DIR, "villager_body_", selected_body))
        build_body = custom_body["customComponent"]["baseBodyType"]
    if not custom_outfit and build_body != clothing["body"]:
        outfit_source = build_outfit(build_body, clothing["top"], clothing["bottom"], clothing["palette"])[0][0]
    if custom_body:
        replace_body(outfit_source, custom_body)
    elif custom_outfit and build_body != clothing["body"]:
        body_name = "villager_body_structure.bdengine" if build_body == "standard" else f"villager_body_{build_body}.bdengine"
        replace_body(outfit_source, load(BODY_DIR / body_name))
    dressed = combine_with_outfit(accessory, outfit_source)[0]
    merge_groups(root, dressed, groups(dressed, "Body Structure"))

    native_hat_combo = hat in HATS and (hair == "bald" or hair in HAIR_STYLES)
    if hat and native_hat_combo:
        headwear = build_hat(hat, hair_style=None if hair == "bald" else hair)[0][0]
        selected = groups(headwear, "Hat -")
        if hair != "bald":
            recolor(headwear, "Hair -", hair_color)
            selected = groups(headwear, "Hair -") + selected
        remap = merge_groups(root, headwear, selected)
        if hair != "bald":
            match_eyebrows(root, headwear, remap)
    else:
        hairstyle = None
        if hair != "bald":
            hairstyle = (build_hair(hair, hair_color)[0][0] if hair in HAIR_STYLES else
                         load(library_file(HAIR_DIR, "villager_hair_", hair)))
            if hair not in HAIR_STYLES:
                recolor(hairstyle, "Hair -", hair_color)
        if hairstyle:
            remap = merge_groups(root, hairstyle, groups(hairstyle, "Hair -"))
            match_eyebrows(root, hairstyle, remap)
        if hat:
            headwear = (build_hat(hat)[0][0] if hat in HATS else
                        load(library_file(ROOT / "bdengine" / "characters" / "villagers" / "headwear", "villager_hat_", hat)))
            merge_groups(root, headwear, groups(headwear, "Hat -"))

    if horns:
        horn_source = load(library_file(HORN_DIR, "villager_horns_", horns))
        merge_groups(root, horn_source, groups(horn_source, "Horns -"))

    if tail:
        tail_source = (build_tail(tail, build_body, hair_color if tail in FURRY else None)[0][0] if tail in TAILS else
                       load(library_file(TAIL_DIR, "villager_tail_", tail)))
        merge_groups(root, tail_source, groups(tail_source, "Tail -"))
        tail_group = root["children"].pop()
        find(root, "Body Structure")["children"].append(tail_group)

    if wings:
        wing_source = (build_wings(wings, build_body)[0][0] if wings in WINGS else
                       load(library_file(WING_DIR, "villager_wings_", wings)))
        merge_groups(root, wing_source, groups(wing_source, "Wings -"))
        wing_group = root["children"].pop()
        find(root, "Body Structure")["children"].append(wing_group)

    if hair == "bald":
        color_eyebrows(root, hair_color)

    if facial:
        facial_hair = load(facial_source(facial))
        recolor(facial_hair, "Facial Hair -", hair_color)
        merge_groups(root, facial_hair, groups(facial_hair, "Facial Hair -"))

    recolor_skin(root, skin_color)
    color_pupils(root, pupil_color)
    anchor_ears(root)
    anchor_joints(root, build_body)

    root["name"] = f"Villager Example - {name}"
    root["examplePreset"] = {
        "nose": nose, "ears": ears, "hair": hair, "facialHair": facial,
        "hat": hat, "outfit": outfit, "accessory": accessory, "skinColor": skin_color,
        "bodyType": selected_body,
        "pupilColor": pupil_color, "horns": horns, "tail": tail, "wings": wings,
    }
    return [root]


def write(scene, output):
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(base64.b64encode(gzip.compress(
        json.dumps(scene, separators=(",", ":")).encode(), mtime=0
    )).decode())


def overview(previews):
    width, image_height, title_height = 600, 231, 28
    canvas = Image.new("RGB", (width * 2, (image_height + title_height) * 5), "#202020")
    draw = ImageDraw.Draw(canvas)
    for index, (name, path) in enumerate(previews):
        image = Image.open(path).convert("RGB").resize((width, image_height))
        x, y = index % 2 * width, index // 2 * (image_height + title_height)
        draw.text((x + 12, y + 7), name.replace("_", " ").title(), fill="white")
        canvas.paste(image, (x, y + title_height))
    canvas.save(PREVIEW_DIR / "villager_examples_overview.png")


def main():
    PREVIEW_DIR.mkdir(parents=True, exist_ok=True)
    previews = []
    for name, preset in EXAMPLES.items():
        output = OUTPUT_DIR / f"villager_example_{name}.bdengine"
        preview = PREVIEW_DIR / f"villager_example_{name}_preview.png"
        write(build(name, preset), output)
        render(output, preview)
        previews.append((name, preview))
        print(f"Created {output.name}")
    overview(previews)
    print("Created villager_examples_overview.png")


if __name__ == "__main__":
    main()
