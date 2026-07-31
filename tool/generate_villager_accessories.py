"""Generate modular medieval accessories on villager body attachment groups."""

import argparse
import base64
import copy
import gzip
import json
import tempfile
from math import atan2, cos, degrees, hypot, radians, sin
from pathlib import Path

from PIL import ImageColor

from generate_villager_body import BODY_TYPES, group, pieces
from generate_villager_clothing import PRESETS, body_file, find
from generate_villager_hair import VILLAGER_DIR, texture, tint
from preview_bdengine import load, render


ACCESSORY_DIR = VILLAGER_DIR / "accessories"
OUTFIT_DIR = VILLAGER_DIR / "clothing" / "outfits"
PREVIEW_DIR = VILLAGER_DIR.parents[2] / "previews" / "characters" / "villagers" / "accessories"
OUTFIT_TESTS = ("common_m", "guard", "noble_f")

CATEGORIES = {
    "belt_pouch": "utility",
    "tool_belt": "utility",
    "satchel": "travel",
    "waterskin": "travel",
    "traveler_cloak": "travel",
    "neck_scarf": "travel",
    "quiver": "combat",
    "sword_scabbard": "combat",
    "leather_bracers": "combat",
    "amulet": "status",
    "shoulder_mantle": "status",
}

COLORS = {
    "belt_pouch": "#765238", "tool_belt": "#68462E",
    "satchel": "#79543A", "waterskin": "#6D4D35",
    "traveler_cloak": "#66705A", "neck_scarf": "#8A5B4C",
    "quiver": "#5E4933", "sword_scabbard": "#59402F",
    "leather_bracers": "#68462E", "amulet": "#8A6B39",
    "shoulder_mantle": "#6B526F",
}
MANUAL_TEMPLATES = {"amulet", "neck_scarf", "quiver", "satchel", "sword_scabbard", "traveler_cloak"}


def s(name, center, size, tone="primary", rotation=(0, 0, 0)):
    return name, center, size, rotation, tone


def belt(profile, tone="dark"):
    y = profile["waist_y"]
    d = max(profile["depth"], profile.get("belly_depth", 0))
    w = max(profile["waist"], profile.get("belly", 0))
    center_z = -.22 - (d - profile["depth"]) / 2
    return [
        s("belt_front", (0, y, center_z - d / 2 - .035), (w + .09, .09, .05), tone),
        s("belt_back", (0, y, center_z + d / 2 + .035), (w + .09, .09, .05), tone),
        s("belt_left", (-w / 2 - .035, y, center_z), (.05, .09, d), tone),
        s("belt_right", (w / 2 + .035, y, center_z), (.05, .09, d), tone),
    ]


def make_accessory(style, profile):
    d, chest = profile["depth"], profile["chest"]
    waist = max(profile["waist"], profile.get("belly", 0))
    waist_depth = max(d, profile.get("belly_depth", 0))
    front, back = -.22 - d / 2, -.22 + d / 2
    upper_front = -.27 - profile.get("belly_depth", d) * .45 if profile.get("belly") else front
    waist_front = -.29 - waist_depth / 2 if profile.get("belly") else front
    result = {"Torso": [], "left_arm": [], "right_arm": []}

    def fitted_strap(name, center, length, angle):
        if not profile.get("belly"):
            return [s(name, center, (.075, length, .055), "dark", (0, 0, angle))]
        dx, dy = sin(radians(angle)) * length / 4, cos(radians(angle)) * length / 4
        return [
            s(f"{name}_upper", (center[0] - dx, center[1] + dy, front - .04),
              (.075, length / 2 + .03, .055), "dark", (0, 0, angle)),
            s(f"{name}_lower", (center[0] + dx, center[1] - dy, waist_front - .04),
              (.075, length / 2 + .03, .055), "dark", (0, 0, angle)),
        ]

    if style == "belt_pouch":
        result["Torso"] = belt(profile) + [
            s("pouch_loop", (waist * .32, profile["waist_y"] - .07, waist_front - .05), (.09, .16, .06), "metal"),
            s("pouch_body", (waist * .34, profile["waist_y"] - .20, waist_front - .07), (.25, .25, .12)),
            s("pouch_flap", (waist * .34, profile["waist_y"] - .10, waist_front - .14), (.23, .09, .05), "light"),
            s("pouch_clasp", (waist * .34, profile["waist_y"] - .15, waist_front - .18), (.055, .07, .035), "metal"),
        ]
    elif style == "tool_belt":
        result["Torso"] = belt(profile) + [
            s("tool_loop_left", (-waist * .35, profile["waist_y"] - .07, waist_front - .05), (.09, .16, .06), "light"),
            s("tool_loop_right", (waist * .35, profile["waist_y"] - .07, waist_front - .05), (.09, .16, .06), "light"),
            s("tool_handle_left", (-waist * .36, profile["waist_y"] - .23, waist_front - .07), (.07, .30, .07), "dark", (0, 0, -7)),
            s("tool_head_left", (-waist * .43, profile["waist_y"] - .34, waist_front - .07), (.20, .09, .10), "metal", (0, 0, -7)),
            s("tool_handle_right", (waist * .36, profile["waist_y"] - .22, waist_front - .07), (.06, .27, .06), "dark", (0, 0, 6)),
        ]
    elif style == "satchel":
        result["Torso"] = fitted_strap("satchel_strap", (.05, .92, 0), .86, 32) + [
            s("satchel_body", (waist / 2 + .10, .59, -.22), (.27, .31, waist_depth * .72), "primary", (0, 0, -3)),
            s("satchel_flap", (waist / 2 + .10, .67, waist_front - .08), (.25, .12, .07), "light", (0, 0, -3)),
            s("satchel_buckle", (waist / 2 + .10, .62, waist_front - .13), (.055, .065, .035), "metal"),
        ]
    elif style == "waterskin":
        result["Torso"] = belt(profile) + [
            s("waterskin_neck", (-waist / 2 - .07, .66, waist_front - .02), (.09, .14, .09), "dark"),
            s("waterskin_upper", (-waist / 2 - .08, .54, waist_front - .03), (.18, .17, .13), "primary", (0, 0, -4)),
            s("waterskin_lower", (-waist / 2 - .08, .40, waist_front - .03), (.23, .20, .16), "primary", (0, 0, 3)),
            s("waterskin_stop", (-waist / 2 - .08, .70, waist_front - .03), (.075, .07, .075), "metal"),
        ]
    elif style == "traveler_cloak":
        result["Torso"] = [
            s("cloak_collar", (0, 1.21, back + .04), (chest + .10, .13, .12), "light"),
            s("cloak_back_upper", (0, .94, back + .08), (chest + .08, .48, .10), "primary"),
            s("cloak_back_left", (-chest * .22, .55, back + .09), (chest * .48, .48, .11), "primary", (2, 0, -3)),
            s("cloak_back_right", (chest * .22, .55, back + .09), (chest * .48, .48, .11), "light", (2, 0, 3)),
            s("cloak_hem", (0, .30, back + .10), (chest + .14, .09, .12), "dark"),
            s("cloak_fastener_left", (-.12, 1.16, front - .07), (.08, .27, .06), "dark", (0, 0, -45)),
            s("cloak_fastener_right", (.12, 1.16, front - .07), (.08, .27, .06), "dark", (0, 0, 45)),
            s("cloak_clasp", (0, 1.08, front - .11), (.12, .11, .055), "metal", (0, 0, 45)),
        ]
    elif style == "neck_scarf":
        result["Torso"] = [
            s("scarf_front", (0, 1.22, front - .05), (.35, .14, .08)),
            s("scarf_back", (0, 1.22, back + .04), (.35, .14, .08), "dark"),
            s("scarf_left", (-.20, 1.22, -.22), (.08, .14, d + .04), "light"),
            s("scarf_right", (.20, 1.22, -.22), (.08, .14, d + .04), "primary"),
            s("scarf_tail_left", (-.06, 1.02, upper_front - .051), (.10, .30, .07), "primary", (0, 0, -4)),
            s("scarf_tail_right", (.057, 1.032, upper_front - .057), (.09, .313, .065), "light", (0, 0, 5)),
        ]
    elif style == "quiver":
        result["Torso"] = fitted_strap("quiver_front_strap", (-chest * .05, .94, 0), .78, 24) + [
            s("quiver_back_strap", (0, .94, back + .05), (.075, .78, .055), "dark", (0, 0, 24)),
            s("quiver_mount", (.24, .86, back + .07), (.22, .44, .09), "dark", (3, 0, -12)),
            s("quiver_lower_tie", (.13, .64, back + .08), (.40, .07, .08), "light", (0, 0, -8)),
            s("quiver_body", (.25, .84, back + .12), (.23, .62, .18), "primary", (5, 0, -12)),
            s("quiver_rim", (.30, 1.13, back + .12), (.27, .09, .21), "light", (5, 0, -12)),
            s("quiver_bottom", (.19, .55, back + .12), (.20, .12, .17), "metal", (5, 0, -12)),
            s("arrow_0", (.20, 1.27, back + .13), (.035, .46, .035), "dark", (3, 0, -10)),
            s("arrow_1", (.29, 1.29, back + .13), (.035, .48, .035), "dark", (3, 0, -12)),
            s("arrow_2", (.38, 1.25, back + .13), (.035, .43, .035), "dark", (3, 0, -14)),
            s("fletching_0", (.14, 1.47, back + .13), (.10, .10, .045), "light", (3, 0, -10)),
            s("fletching_1", (.20, 1.50, back + .13), (.10, .10, .045), "light", (3, 0, -12)),
            s("fletching_2", (.29, 1.45, back + .13), (.10, .10, .045), "light", (3, 0, -14)),
        ]
    elif style == "sword_scabbard":
        angle, length = -8, .58
        sx, sy = min(waist / 2 + .08, profile["shoulder"] - .02), .43
        ux, uy = -sin(radians(angle)), cos(radians(angle))
        bottom = (sx - ux * length / 2, sy - uy * length / 2)
        top = (sx + ux * length / 2, sy + uy * length / 2)
        ring = (waist / 2 + .06, profile["waist_y"])
        baldric_angle = -degrees(atan2(top[0] - ring[0], top[1] - ring[1]))
        result["Torso"] = belt(profile) + [
            s("sword_baldric", ((ring[0] + top[0]) / 2, (ring[1] + top[1]) / 2, -.19),
              (.065, hypot(top[0] - ring[0], top[1] - ring[1]) + .06, .07),
              "dark", (0, 0, baldric_angle)),
            s("sword_belt_ring", (ring[0], ring[1], -.22), (.10, .11, .10), "metal"),
            s("scabbard_body", (sx, sy, -.19), (.12, length, .12), "primary", (0, 0, angle)),
            s("scabbard_mouth", (top[0] - ux * .02, top[1] - uy * .02, -.19),
              (.16, .09, .16), "metal", (0, 0, angle)),
            s("scabbard_chape", (bottom[0] + ux * .02, bottom[1] + uy * .02, -.19),
              (.12, .10, .12), "metal", (0, 0, angle)),
            s("sword_guard", (top[0] + ux * .035, top[1] + uy * .035, -.19),
              (.30, .055, .10), "metal", (0, 0, angle)),
            s("sword_grip", (top[0] + ux * .14, top[1] + uy * .14, -.19),
              (.07, .20, .08), "dark", (0, 0, angle)),
            s("sword_pommel", (top[0] + ux * .25, top[1] + uy * .25, -.19),
              (.11, .085, .10), "metal", (0, 0, angle)),
        ]
    elif style == "leather_bracers":
        for side, sign in (("left_arm", -1), ("right_arm", 1)):
            result[side] = [
                s(f"{side}_bracer", (sign * .015, -.52, -.01),
                  (profile["forearm"] + .05, .25, d * .57 + .045), "primary", (0, 0, sign * -2)),
                s(f"{side}_bracer_cuff", (sign * .015, -.42, -.01),
                  (profile["forearm"] + .065, .07, d * .59 + .055), "light", (0, 0, sign * -2)),
                s(f"{side}_bracer_band", (sign * .015, -.60, -.01),
                  (profile["forearm"] + .06, .06, d * .58 + .05), "dark", (0, 0, sign * -2)),
            ]
    elif style == "amulet":
        result["Torso"] = [
            s("amulet_cord_left", (-.04, 1.08, front - .055), (.035, .31, .035), "dark", (0, 0, -13)),
            s("amulet_cord_right", (.04, 1.08, front - .055), (.035, .31, .035), "dark", (0, 0, 13)),
            s("amulet_setting", (0, .92, upper_front - .075), (.13, .13, .055), "metal", (0, 0, 45)),
            s("amulet_stone", (0, .92, upper_front - .11), (.075, .075, .035), "light", (0, 0, 45)),
        ]
    elif style == "shoulder_mantle":
        result["Torso"] = [
            s("mantle_collar", (0, 1.20, -.22), (chest + .10, .14, d + .10), "primary"),
            s("mantle_front", (0, 1.12, front - .07), (chest * .72, .15, .09), "light"),
            s("mantle_back", (0, 1.10, back + .07), (chest + .08, .18, .10), "dark"),
            s("mantle_clasp", (0, 1.12, front - .13), (.11, .10, .045), "metal"),
        ]
        for side, sign in (("left_arm", -1), ("right_arm", 1)):
            result[side] = [
                s(f"{side}_mantle_cap", (sign * .015, -.12, 0),
                  (profile["arm"] + .13, .24, d * .75 + .10), "primary", (0, 0, sign * -5)),
                s(f"{side}_mantle_edge", (sign * .02, -.23, -.01),
                  (profile["arm"] + .12, .065, d * .73 + .09), "light", (0, 0, sign * -5)),
            ]
    else:
        raise ValueError(f"Unknown accessory: {style}")
    return result


def build(style, body_type="standard", color=None):
    template = ACCESSORY_DIR / CATEGORIES[style] / f"villager_accessory_{style}.bdengine"
    if style in MANUAL_TEMPLATES and body_type == "standard" and color is None and template.exists():
        root = copy.deepcopy(load(template))
        attached, count = [], 0
        for target in ("Torso", "left_arm", "right_arm", "left_leg", "right_leg"):
            groups = [
                node for node in find(root, target).get("children", [])
                if node.get("name", "").startswith(f"Accessory - {style} -")
            ]
            if groups:
                attached.append(target)
                count += sum(len(node.get("children", [])) for node in groups)
        root["accessory"] = {
            "style": style, "category": CATEGORIES[style],
            "body": body_type, "attachmentTargets": attached,
        }
        return [root], count
    root = copy.deepcopy(load(body_file(body_type)))
    profile = BODY_TYPES[body_type]
    color = color or COLORS[style]
    refs = root.setdefault("refs", {}).setdefault("paintTextures", [])
    first = len(refs)
    refs.extend([
        texture(tint(color, 1)),
        texture(tint(color, .72)),
        texture(tint(color, 1.16)),
        texture(ImageColor.getrgb("#7F827D" if style == "sword_scabbard" else "#A9AAA3")),
    ])
    palette = {"primary": first, "dark": first + 1, "light": first + 2, "metal": first + 3}
    attached, total = [], 0
    for target, specs in make_accessory(style, profile).items():
        if not specs:
            continue
        find(root, target)["children"].append(group(
            f"Accessory - {style} - {target}", (0, 0, 0), pieces(specs, palette)
        ))
        attached.append(target)
        total += len(specs)
    root["name"] = f"Villager accessory - {style}"
    root["accessory"] = {
        "style": style, "category": CATEGORIES[style],
        "body": body_type, "attachmentTargets": attached,
    }
    return [root], total


def write(style, body_type, color, output):
    scene, count = build(style, body_type, color)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(base64.b64encode(gzip.compress(
        json.dumps(scene, separators=(",", ":")).encode(), mtime=0
    )).decode())
    decoded = json.loads(gzip.decompress(base64.b64decode(output.read_text())))[0]
    assert decoded["accessory"]["style"] == style
    assert decoded["accessory"]["attachmentTargets"]
    assert count > 0
    return count


def walk(node):
    yield node
    for child in node.get("children", []):
        yield from walk(child)


def combine_with_outfit(style, outfit):
    root = copy.deepcopy(outfit if isinstance(outfit, dict) else load(outfit))
    if not style:
        return [root]
    preset = "" if isinstance(outfit, dict) else Path(outfit).stem.removeprefix("villager_outfit_")
    body_type = root.get("clothing", {}).get("body") or PRESETS.get(preset, ("standard",))[0]
    accessory = build(style, body_type)[0][0]
    source_textures = accessory.get("refs", {}).get("paintTextures", [])
    target_textures = root.setdefault("refs", {}).setdefault("paintTextures", [])
    for target in accessory["accessory"]["attachmentTargets"]:
        source_group = next(
            child for child in find(accessory, target)["children"]
            if child.get("name") == f"Accessory - {style} - {target}"
        )
        clone = copy.deepcopy(source_group)
        used = sorted({
            node["paintTexture"] for node in walk(clone)
            if isinstance(node.get("paintTexture"), int)
        })
        remap = {}
        for index in used:
            remap[index] = len(target_textures)
            target_textures.append(source_textures[index])
        for node in walk(clone):
            if node.get("paintTexture") in remap:
                node["paintTexture"] = remap[node["paintTexture"]]
        find(root, target)["children"].append(clone)
    root.setdefault("accessories", []).append(style)
    return [root]


def compatibility_previews(styles):
    for style in styles:
        target = PREVIEW_DIR / "compatibility" / style
        target.mkdir(parents=True, exist_ok=True)
        for outfit in OUTFIT_TESTS:
            with tempfile.TemporaryDirectory() as directory:
                source = Path(directory) / "model.bdengine"
                source.write_text(base64.b64encode(gzip.compress(
                    json.dumps(combine_with_outfit(
                        style, OUTFIT_DIR / f"villager_outfit_{outfit}.bdengine"
                    ), separators=(",", ":")).encode(), mtime=0
                )).decode())
                render(source, target / f"{style}_with_{outfit}.png")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--style", choices=["all", *CATEGORIES], default="all")
    parser.add_argument("--body", choices=BODY_TYPES, default="standard")
    parser.add_argument("--color")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--compatibility-previews", action="store_true")
    args = parser.parse_args()
    if args.color:
        ImageColor.getrgb(args.color)
    styles = CATEGORIES if args.style == "all" else (args.style,)
    for style in styles:
        suffix = "" if args.body == "standard" else f"_{args.body}"
        output = args.output if args.output and len(styles) == 1 else (
            ACCESSORY_DIR / CATEGORIES[style] / f"villager_accessory_{style}{suffix}.bdengine"
        )
        count = write(style, args.body, args.color, output)
        print(f"Created {output.name}: {count} pieces attached to {build(style, args.body, args.color)[0][0]['accessory']['attachmentTargets']}")
    if args.compatibility_previews:
        compatibility_previews(styles)
        print(f"Created {len(styles) * len(OUTFIT_TESTS)} clothing compatibility previews")


if __name__ == "__main__":
    main()
