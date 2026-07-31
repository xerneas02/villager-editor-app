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
}


def build(style, color="#C8B88C"):
    root = copy.deepcopy(load(HEAD_DIR / "villager_head.bdengine"))
    textures = root.setdefault("refs", {}).setdefault("paintTextures", [])
    first = len(textures)
    textures.extend(texture(tint(color, factor)) for factor in (1, .76, 1.14))
    pieces = []
    for side, sign in (("left", -1), ("right", 1)):
        pieces.append(hair_box(
            f"{side}_socket", (sign * .43, 2.02, -.18), (.16, .12, .17), (0, 0, 0), first + 1,
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
