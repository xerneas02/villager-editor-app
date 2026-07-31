"""Attach a neutral modular body structure to a shared villager head."""

import argparse
import base64
import copy
import gzip
import json
from pathlib import Path

from PIL import ImageColor

from generate_villager_hair import HEAD_DIR, ROOT, VILLAGER_DIR, hair_box, texture
from preview_bdengine import load


SOURCE = HEAD_DIR / "villager_head.bdengine"
BODY_DIR = VILLAGER_DIR / "bodies"

BODY_TYPES = {
    "standard": dict(chest=.72, depth=.36, waist=.60, pelvis=.62, shoulder=.45,
                     arm=.22, forearm=.17, hand=.19, hip=.55, leg=.25, lower=.22, foot=.25,
                     chest_y=1.00, chest_h=.48, waist_y=.72, pelvis_y=.58),
    "slender": dict(chest=.62, depth=.32, waist=.48, pelvis=.52, shoulder=.40,
                    arm=.18, forearm=.14, hand=.16, hip=.59, leg=.20, lower=.18, foot=.21,
                    chest_y=.99, chest_h=.50, waist_y=.75, pelvis_y=.62),
    "sturdy": dict(chest=.82, depth=.42, waist=.74, pelvis=.74, shoulder=.50,
                   arm=.25, forearm=.21, hand=.22, hip=.52, leg=.29, lower=.26, foot=.30,
                   chest_y=.96, chest_h=.56, waist_y=.67, pelvis_y=.54),
    "heroic": dict(chest=.88, depth=.40, waist=.58, pelvis=.66, shoulder=.52,
                   arm=.25, forearm=.20, hand=.21, hip=.57, leg=.26, lower=.23, foot=.28,
                   chest_y=1.00, chest_h=.49, waist_y=.73, pelvis_y=.59),
    "compact": dict(chest=.76, depth=.40, waist=.68, pelvis=.70, shoulder=.47,
                    arm=.24, forearm=.20, hand=.21, hip=.47, leg=.28, lower=.25, foot=.29,
                    chest_y=.94, chest_h=.62, waist_y=.64, pelvis_y=.49),
    "goblin": dict(chest=.64, depth=.38, waist=.58, pelvis=.62, shoulder=.42,
                   arm=.22, forearm=.18, hand=.20, hip=.43, leg=.25, lower=.22, foot=.27,
                   chest_y=.93, chest_h=.62, waist_y=.63, pelvis_y=.48),
    "orc": dict(chest=.92, depth=.48, waist=.80, pelvis=.78, shoulder=.55,
                arm=.30, forearm=.25, hand=.27, hip=.49, leg=.31, lower=.28, foot=.34,
                chest_y=.96, chest_h=.58, waist_y=.66, pelvis_y=.52),
    "brute": dict(chest=1.02, depth=.52, waist=.90, pelvis=.86, shoulder=.60,
                  arm=.34, forearm=.28, hand=.30, hip=.46, leg=.34, lower=.30, foot=.37,
                  chest_y=.94, chest_h=.62, waist_y=.63, pelvis_y=.49),
    "chubby": dict(chest=.84, depth=.52, waist=.86, pelvis=.82, shoulder=.51,
                   arm=.28, forearm=.23, hand=.24, hip=.50, leg=.31, lower=.28, foot=.33,
                   chest_y=.96, chest_h=.54, waist_y=.67, pelvis_y=.53,
                   belly=.94, belly_depth=.66),
}


def group(name, position, children):
    x, y, z = position
    return {
        "isCollection": True,
        "isBackCollection": False,
        "name": name,
        "nbt": "",
        "transforms": [1, 0, 0, x, 0, 1, 0, y, 0, 0, 1, z, 0, 0, 0, 1],
        "defaultTransform": {
            "position": list(position),
            "rotation": {"x": 0, "y": 0, "z": 0},
            "scale": [1, 1, 1],
        },
        "children": children,
    }


def pieces(specs, textures):
    return [hair_box(name, center, size, rotation, textures[tone])
            for name, center, size, rotation, tone in specs]


def build(source, skin, tunic, trousers, boots, body_type="standard"):
    profile = BODY_TYPES[body_type]
    root = copy.deepcopy(load(source))
    refs = root.setdefault("refs", {}).setdefault("paintTextures", [])
    first = len(refs)
    refs.extend(texture(ImageColor.getrgb(color)) for color in (tunic, "#C8C1AB", skin, trousers, boots))
    palette = {"tunic": first, "shadow": first + 1, "skin": first + 2,
               "trousers": first + 3, "boots": first + 4}

    core_specs = [
        ("neck", (0, 1.27, -.22), (.25, .12, .23), (0, 0, 0), "skin"),
        ("chest", (0, profile["chest_y"], -.22), (profile["chest"], profile["chest_h"], profile["depth"]), (0, 0, 0), "tunic"),
        ("waist", (0, profile["waist_y"], -.22), (profile["waist"], .18, profile["depth"] - .04), (0, 0, 0), "shadow"),
        ("pelvis", (0, profile["pelvis_y"], -.22), (profile["pelvis"], .18, profile["depth"] - .02), (0, 0, 0), "trousers"),
    ]
    if profile.get("belly"):
        core_specs.extend([
            ("upper_belly", (0, .78, -.27), (profile["belly"] * .90, .24, profile["belly_depth"] * .90), (0, 0, 0), "tunic"),
            ("lower_belly", (0, .62, -.29), (profile["belly"], .22, profile["belly_depth"]), (0, 0, 0), "tunic"),
        ])

    arms = []
    for side, sign in (("left", -1), ("right", 1)):
        arm_specs = [
            (f"{side}_shoulder", (sign * .015, -.14, 0), (profile["arm"], .32, profile["depth"] * .69), (0, 0, sign * -4), "shadow"),
            (f"{side}_upper_arm", (sign * .025, -.36, 0), (profile["arm"] * .86, .25, profile["depth"] * .61), (0, 0, sign * 3), "tunic"),
            (f"{side}_forearm", (sign * .015, -.54, -.01), (profile["forearm"], .24, profile["depth"] * .53), (0, 0, sign * -2), "skin"),
            (f"{side}_hand", (0, -.69, -.02), (profile["hand"], .18, profile["depth"] * .56), (0, 0, 0), "skin"),
        ]
        arms.append(group(f"{side}_arm", (sign * profile["shoulder"], 1.17, -.22), pieces(arm_specs, palette)))

    legs = []
    for side, sign in (("left", -1), ("right", 1)):
        leg_specs = [
            (f"{side}_thigh", (0, (.25 + profile["hip"] + .03) / 2 - profile["hip"], 0),
             (profile["leg"], profile["hip"] - .22, profile["depth"] * .81), (0, 0, sign * -2), "trousers"),
            (f"{side}_lower_leg", (0, .20 - profile["hip"], 0),
             (profile["lower"], .30, profile["depth"] * .69), (0, 0, sign), "trousers"),
            (f"{side}_foot", (0, .07 - profile["hip"], -.07),
             (profile["foot"], .16, profile["depth"] + .02), (0, 0, 0), "boots"),
        ]
        legs.append(group(f"{side}_leg", (sign * profile["pelvis"] * .29, profile["hip"], -.22), pieces(leg_specs, palette)))

    body = group("Body Structure", (0, 0, 0), [
        group("Torso", (0, 0, 0), pieces(core_specs, palette)), *arms, *legs,
    ])
    root["children"].append(body)
    root["name"] = f"Villager - {body_type} body structure"
    root["bodyStructure"] = f"{body_type}_v1"
    return [root]


def write(source, output, skin, tunic, trousers, boots, body_type="standard"):
    scene = build(source, skin, tunic, trousers, boots, body_type)
    encoded = base64.b64encode(gzip.compress(json.dumps(scene, separators=(",", ":")).encode(), mtime=0)).decode()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(encoded)
    decoded = json.loads(gzip.decompress(base64.b64decode(output.read_text())))[0]
    body = decoded["children"][-1]
    assert body["name"] == "Body Structure"
    assert [child["name"] for child in body["children"]] == ["Torso", "left_arm", "right_arm", "left_leg", "right_leg"]
    assert sum(len(child["children"]) for child in body["children"]) == 18 + (2 if BODY_TYPES[body_type].get("belly") else 0)
    assert decoded["bodyStructure"] == f"{body_type}_v1"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", type=Path, default=SOURCE)
    parser.add_argument("--type", choices=["all", *BODY_TYPES], default="all")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--skin", default="#D6B27B")
    parser.add_argument("--tunic", default="#DDD7C3")
    parser.add_argument("--trousers", default="#74715F")
    parser.add_argument("--boots", default="#51402F")
    args = parser.parse_args()
    for color in (args.skin, args.tunic, args.trousers, args.boots):
        ImageColor.getrgb(color)
    body_types = BODY_TYPES if args.type == "all" else (args.type,)
    for body_type in body_types:
        default_name = "villager_body_structure.bdengine" if body_type == "standard" else f"villager_body_{body_type}.bdengine"
        output = args.output if args.output and len(body_types) == 1 else BODY_DIR / default_name
        write(args.base, output, args.skin, args.tunic, args.trousers, args.boots, body_type)
        print(f"Created {output}: {body_type} modular body")


if __name__ == "__main__":
    main()
