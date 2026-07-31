"""Generate recolourable medieval hats and hair compatibility previews."""

import argparse
import base64
import copy
import gzip
import json
import tempfile
from pathlib import Path

from generate_villager_hair import (
    HEAD_DIR, VILLAGER_DIR, STYLES as HAIR_STYLES, build as build_hair,
    hair_box, texture, tint,
)
from preview_bdengine import load, render


HAT_DIR = VILLAGER_DIR / "headwear" / "hats"
PREVIEW_DIR = VILLAGER_DIR.parents[2] / "previews" / "characters" / "villagers" / "headwear"
HAIR_TESTS = tuple(HAIR_STYLES)
HAIR_HAT_Y_OFFSET = -.20
BALD_HAT_Y_OFFSET = -.26
TOP_HAIR_PARTS = {
    "scalp_top", "top_left", "top_right", "top_seam", "crown",
    "swept_crown", "crown_ridge", "rear_flick", "left_swept", "right_swept",
    "part_left", "part_right", "elven_part_left", "elven_part_right",
    "half_up_left", "half_up_right",
}


def p(name, center, size, tone=0, rotation=(0, 0, 0)):
    return name, center, size, rotation, tone


HATS = {
    "straw_hat": ("#C6A64C", [
        p("brim_center", (0, 2.30, -.22), (.88, .06, .76)),
        p("brim_left", (-.49, 2.295, -.22), (.14, .055, .56), 1, (0, -4, 0)),
        p("brim_right", (.49, 2.295, -.22), (.14, .055, .56), 1, (0, 4, 0)),
        p("brim_front", (0, 2.285, -.63), (.82, .055, .13), 2, (-5, 0, 0)),
        p("brim_back", (0, 2.305, .19), (.80, .05, .12), 1),
        p("crown_lower", (0, 2.40, -.22), (.74, .18, .52)),
        p("crown_middle", (0, 2.53, -.22), (.70, .13, .49), 2),
        p("crown_upper", (0, 2.63, -.22), (.66, .10, .46)),
        p("crown_top", (0, 2.70, -.22), (.62, .05, .43), 2),
        p("band_front", (0, 2.39, -.495), (.68, .085, .045), 1),
        p("band_back", (0, 2.39, .055), (.68, .085, .045), 1),
        p("band_left", (-.385, 2.39, -.22), (.045, .085, .51), 1),
        p("band_right", (.385, 2.39, -.22), (.045, .085, .51), 1),
        p("woven_ridge_front", (0, 2.56, -.485), (.61, .035, .035), 1),
        p("woven_ridge_back", (0, 2.56, .045), (.61, .035, .035), 1),
        p("woven_ridge_left", (-.365, 2.56, -.22), (.035, .035, .47), 1),
        p("woven_ridge_right", (.365, 2.56, -.22), (.035, .035, .47), 1),
    ]),
    "felt_hat": ("#69513C", [
        p("brim", (0, 2.32, -.22), (1.02, .07, .76), 1),
        p("brim_front", (0, 2.30, -.60), (.72, .06, .14), 2, (-5, 0, 0)),
        p("crown_lower", (0, 2.44, -.22), (.68, .23, .50)),
        p("crown_upper", (-.02, 2.61, -.22), (.58, .17, .43), 2, (0, 0, -2)),
        p("crown_top", (-.02, 2.70, -.22), (.54, .06, .40), 1, (0, 0, -2)),
        p("band_front", (0, 2.45, -.49), (.66, .08, .05), 1),
        p("band_back", (0, 2.45, .05), (.66, .08, .05), 1),
    ]),
    "soft_cap": ("#73805F", [
        p("cap_band", (0, 2.32, -.22), (.86, .10, .61), 1),
        p("cap_left", (-.20, 2.42, -.22), (.45, .20, .55), 0, (0, -3, -7)),
        p("cap_right", (.20, 2.42, -.22), (.45, .20, .55), 2, (0, 3, 7)),
        p("cap_top", (0, 2.53, -.22), (.58, .08, .47), 2),
        p("front_bill", (0, 2.31, -.58), (.45, .06, .20), 1, (-7, 0, 0)),
        p("left_fold", (-.25, 2.47, -.50), (.14, .06, .07), 1, (0, 0, -8)),
        p("right_fold", (.25, 2.47, -.50), (.14, .06, .07), 1, (0, 0, 8)),
    ]),
    "round_cap": ("#7B4E45", [
        p("cap_band", (0, 2.32, -.22), (.88, .10, .63), 1),
        p("cap_lower", (0, 2.41, -.22), (.82, .14, .58)),
        p("cap_upper", (0, 2.51, -.22), (.70, .10, .50), 2),
        p("cap_top", (0, 2.58, -.22), (.62, .05, .45), 1),
        p("front_band", (0, 2.34, -.55), (.76, .07, .05), 2),
        p("back_band", (0, 2.34, .11), (.76, .07, .05), 2),
    ]),
    "noble_cap": ("#66506F", [
        p("lower_band", (0, 2.32, -.22), (.90, .11, .64), 2),
        p("cap_body", (0, 2.43, -.22), (.80, .17, .57)),
        p("cap_top", (0, 2.55, -.22), (.69, .09, .49), 1),
        p("front_trim", (0, 2.35, -.56), (.78, .06, .05), 1),
        p("back_trim", (0, 2.35, .12), (.78, .06, .05), 1),
        p("left_trim", (-.46, 2.35, -.22), (.05, .06, .59), 1),
        p("right_trim", (.46, 2.35, -.22), (.05, .06, .59), 1),
        p("top_left", (-.18, 2.61, -.22), (.31, .05, .35), 2, (0, -4, -3)),
        p("top_right", (.18, 2.61, -.22), (.31, .05, .35), 2, (0, 4, 3)),
    ]),
    "pointed_cap": ("#586B53", [
        p("cap_band", (0, 2.32, -.22), (.87, .10, .62), 1),
        p("point_0", (0, 2.43, -.20), (.75, .18, .54)),
        p("point_1", (-.04, 2.57, -.17), (.63, .16, .46), 2, (0, 0, -3)),
        p("point_2", (-.10, 2.69, -.13), (.50, .14, .37), 0, (0, 0, -7)),
        p("point_3", (-.18, 2.79, -.08), (.36, .12, .29), 2, (0, 0, -13)),
        p("point_4", (-.27, 2.86, -.02), (.23, .10, .21), 0, (0, 0, -21)),
        p("point_tip", (-.36, 2.88, .05), (.14, .08, .15), 1, (0, 0, -31)),
        p("front_band", (0, 2.35, -.55), (.74, .06, .05), 1),
    ]),
    "kettle_helmet": ("#8B9190", [
        p("helmet_brim", (0, 2.32, -.22), (1.08, .08, .80), 1),
        p("bowl_lower", (0, 2.43, -.22), (.82, .20, .59)),
        p("bowl_mid", (0, 2.58, -.22), (.70, .16, .51), 2),
        p("bowl_upper", (0, 2.69, -.22), (.55, .12, .42), 0),
        p("bowl_top", (0, 2.77, -.22), (.38, .07, .30), 2),
        p("front_ridge", (0, 2.58, -.49), (.08, .35, .06), 1),
        p("left_rim", (-.48, 2.34, -.22), (.08, .08, .63), 2),
        p("right_rim", (.48, 2.34, -.22), (.08, .08, .63), 2),
    ]),
}


def build(style, color=None, hair_style=None):
    if hair_style:
        root = copy.deepcopy(build_hair(hair_style, "#806044")[0][0])
    else:
        root = copy.deepcopy(load(HEAD_DIR / "villager_head.bdengine"))
    color = color or HATS[style][0]
    textures = root.setdefault("refs", {}).setdefault("paintTextures", [])
    first = len(textures)
    textures.extend(texture(tint(color, factor)) for factor in (1, .78, 1.16))
    hidden = []
    if hair_style:
        hair = next(group for group in root["children"] if group.get("name", "").startswith("Hair -"))
        hidden = [piece.get("_part") for piece in hair["children"] if piece.get("_part") in TOP_HAIR_PARTS]
        hair["children"] = [piece for piece in hair["children"] if piece.get("_part") not in TOP_HAIR_PARTS]
    offset = HAIR_HAT_Y_OFFSET if hair_style else BALD_HAT_Y_OFFSET
    hat = {
        "isCollection": True,
        "isBackCollection": False,
        "name": f"Hat - {style}",
        "nbt": "",
        "transforms": [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1],
        "children": [hair_box(name, (center[0], center[1] + offset, center[2]), size, rotation, first + tone)
                     for name, center, size, rotation, tone in HATS[style][1]],
    }
    root["children"].append(hat)
    root["name"] = f"Villager Head - {style}"
    root["hatStyle"] = style
    root["hatColor"] = color
    root["hatHairClearance"] = 2.08 if hair_style else 2.02
    root["hatHiddenHairParts"] = hidden
    return [root], len(hat["children"])


def write(scene, output):
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(base64.b64encode(gzip.compress(
        json.dumps(scene, separators=(",", ":")).encode(), mtime=0
    )).decode())
    decoded = json.loads(gzip.decompress(base64.b64decode(output.read_text())))[0]
    assert decoded["hatStyle"] in HATS
    assert decoded["children"][-1]["name"] == f"Hat - {decoded['hatStyle']}"


def compatibility_previews(styles):
    for style in styles:
        target = PREVIEW_DIR / "compatibility" / style
        target.mkdir(parents=True, exist_ok=True)
        for hair_style in HAIR_TESTS:
            with tempfile.TemporaryDirectory() as directory:
                source = Path(directory) / "model.bdengine"
                write(build(style, hair_style=hair_style)[0], source)
                render(source, target / f"{style}_with_{hair_style}.png")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--style", choices=["all", *HATS], default="all")
    parser.add_argument("--color")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--compatibility-previews", action="store_true")
    args = parser.parse_args()
    styles = HATS if args.style == "all" else (args.style,)
    for style in styles:
        output = args.output if args.output and len(styles) == 1 else HAT_DIR / f"villager_hat_{style}.bdengine"
        scene, count = build(style, args.color)
        write(scene, output)
        print(f"Created {output.name}: {count} hat pieces")
    if args.compatibility_previews:
        compatibility_previews(styles)
        print(f"Created {len(styles) * len(HAIR_TESTS)} hair compatibility previews")


if __name__ == "__main__":
    main()
