"""Generate modular voxel horns for villager heads."""

import argparse
import base64
import copy
import gzip
import json
from pathlib import Path

from generate_villager_hair import HEAD_DIR, VILLAGER_DIR, hair_box, texture, tint
from preview_bdengine import load


HORN_DIR = VILLAGER_DIR / "headwear" / "horns"
HORN_Y_OFFSET = -.07


def p(name, center, size, tone=0, angle=0):
    return name, center, size, tone, angle


STYLES = {
    "short": [
        p("root", (.47, 2.18, -.18), (.14, .18, .16), 1, 8),
        p("middle", (.56, 2.29, -.18), (.13, .17, .14), 0, 18),
        p("tip", (.63, 2.40, -.18), (.10, .14, .11), 2, 28),
    ],
    "long": [
        p("root", (.47, 2.17, -.18), (.15, .19, .17), 1, 8),
        p("lower", (.57, 2.29, -.18), (.14, .19, .15), 0, 18),
        p("middle", (.65, 2.43, -.18), (.12, .18, .13), 0, 25),
        p("upper", (.71, 2.56, -.18), (.10, .15, .11), 2, 31),
        p("tip", (.75, 2.67, -.18), (.07, .11, .08), 2, 36),
    ],
    "curved": [
        p("root", (.47, 2.18, -.16), (.15, .19, .17), 1, 8),
        p("outer", (.59, 2.25, -.16), (.17, .14, .15), 0, 48),
        p("bend", (.69, 2.34, -.16), (.14, .16, .13), 0, 24),
        p("rise", (.72, 2.47, -.16), (.11, .16, .11), 2, 5),
        p("tip", (.70, 2.58, -.16), (.08, .11, .08), 2, -13),
    ],
    "ram": [
        p("root", (.47, 2.22, -.08), (.16, .19, .18), 1, 8),
        p("crest", (.57, 2.34, -.06), (.16, .17, .17), 0, 28),
        p("outer", (.68, 2.34, -.05), (.16, .14, .16), 0, 72),
        p("lower", (.72, 2.23, -.07), (.13, .16, .14), 1, -5),
        p("curl", (.68, 2.12, -.13), (.11, .13, .12), 2, -24),
        p("tip", (.61, 2.06, -.22), (.08, .10, .09), 2, -48),
    ],
    "draconic": [
        p("root", (.47, 2.17, -.10), (.17, .20, .19), 1, 8),
        p("lower", (.58, 2.28, -.03), (.15, .20, .16), 0, 20),
        p("ridge", (.68, 2.39, .06), (.14, .19, .14), 0, 30),
        p("upper", (.77, 2.49, .16), (.12, .17, .12), 2, 38),
        p("tip", (.84, 2.56, .27), (.08, .14, .09), 2, 48),
        p("brow_spur", (.55, 2.34, -.15), (.08, .14, .09), 2, -14),
    ],
    "moose": [
        p("root", (.47, 2.14, -.10), (.17, .18, .15), 1, 10),
        p("beam", (.59, 2.25, -.09), (.18, .15, .13), 0, 42),
        p("palm_lower", (.72, 2.38, -.08), (.20, .22, .12), 0, 26),
        p("palm_upper", (.84, 2.52, -.08), (.25, .24, .12), 0, 34),
        p("inner_tine", (.68, 2.59, -.08), (.08, .22, .09), 2, -7),
        p("middle_tine", (.83, 2.70, -.08), (.08, .21, .09), 2, 2),
        p("outer_tine", (.98, 2.68, -.08), (.08, .20, .09), 2, 12),
    ],
    "reindeer": [
        p("root", (.47, 2.14, -.10), (.15, .19, .14), 1, 8),
        p("beam_lower", (.56, 2.27, -.09), (.13, .19, .12), 0, 20),
        p("beam_middle", (.66, 2.40, -.08), (.12, .19, .11), 0, 28),
        p("beam_outer", (.78, 2.51, -.08), (.13, .18, .11), 0, 42),
        p("beam_tip", (.90, 2.60, -.08), (.09, .17, .09), 2, 52),
        p("inner_tine", (.54, 2.43, -.08), (.08, .20, .08), 2, -8),
        p("middle_tine", (.68, 2.57, -.08), (.08, .20, .08), 2, -3),
        p("outer_tine", (.82, 2.68, -.08), (.07, .18, .08), 2, 8),
    ],
    "roe_deer": [
        p("root", (.46, 2.14, -.10), (.13, .18, .12), 1, 4),
        p("stem", (.49, 2.28, -.10), (.11, .18, .10), 0, 5),
        p("upper", (.50, 2.42, -.10), (.09, .17, .09), 0, 0),
        p("tip", (.50, 2.55, -.10), (.07, .14, .07), 2, -3),
        p("inner_branch", (.43, 2.43, -.10), (.07, .15, .07), 2, -25),
        p("outer_branch", (.58, 2.48, -.10), (.07, .15, .07), 2, 30),
    ],
}

STYLE_COLORS = {
    "draconic": "#645447", "moose": "#896A48",
    "reindeer": "#957650", "roe_deer": "#A08059",
}


def build(style, color=None):
    root = copy.deepcopy(load(HEAD_DIR / "villager_head.bdengine"))
    textures = root.setdefault("refs", {}).setdefault("paintTextures", [])
    first = len(textures)
    color = color or STYLE_COLORS.get(style, "#C8B88C")
    textures.extend(texture(tint(color, factor)) for factor in (1, .76, 1.14))
    pieces = []
    for side, sign in (("left", -1), ("right", 1)):
        pieces.append(hair_box(
            f"{side}_socket", (sign * .40, 2.01, -.18), (.20, .16, .19), (0, 0, 0), first + 1,
        ))
        for name, center, size, tone, angle in STYLES[style]:
            pieces.append(hair_box(
                f"{side}_{name}", (sign * center[0], center[1] + HORN_Y_OFFSET, center[2]), size,
                (0, 0, -sign * angle), first + tone,
            ))
    root["children"].append({
        "isCollection": True, "isBackCollection": False,
        "name": f"Horns - {style}", "nbt": "",
        "transforms": [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1],
        "children": pieces,
    })
    root["hornStyle"] = style
    return [root], len(pieces)


def write(style, output):
    scene, count = build(style)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(base64.b64encode(gzip.compress(
        json.dumps(scene, separators=(",", ":")).encode(), mtime=0
    )).decode())
    assert load(output)["hornStyle"] == style
    return count


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--style", choices=["all", *STYLES], default="all")
    args = parser.parse_args()
    styles = STYLES if args.style == "all" else (args.style,)
    for style in styles:
        output = HORN_DIR / f"villager_horns_{style}.bdengine"
        print(f"Created {output.name}: {write(style, output)} horn voxels")


if __name__ == "__main__":
    main()
