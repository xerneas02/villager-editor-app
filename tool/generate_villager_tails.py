"""Generate animal-inspired tails fitted to villager body profiles."""

import argparse
import base64
import copy
import gzip
import json

from generate_villager_body import BODY_TYPES
from generate_villager_hair import HEAD_DIR, VILLAGER_DIR, hair_box, texture, tint
from preview_bdengine import load


TAIL_DIR = VILLAGER_DIR / "tails"
TAILS = ("wolf", "fox", "cat", "deer", "rabbit", "horse", "goat", "dragon")
COLORS = {
    "wolf": "#746C62", "fox": "#A95F35", "cat": "#51463F", "deer": "#8A684B",
    "rabbit": "#B8AA96", "horse": "#5C4030", "goat": "#8B806E", "dragon": "#5D5148",
}


def s(name, center, size, tone=0, rotation=(0, 0, 0)):
    return name, center, size, tone, rotation


def specs(style, profile):
    y = profile["pelvis_y"]
    back = -.22 + max(profile["depth"], profile.get("belly_depth", 0)) / 2
    if style == "wolf":
        return [
            s("root", (0, y + .03, back + .08), (.18, .17, .18), 1, (28, 0, 0)),
            s("upper", (0, y - .04, back + .22), (.22, .22, .24), 0, (35, 0, 0)),
            s("middle", (0, y - .14, back + .39), (.24, .24, .26), 0, (31, 0, 0)),
            s("lower", (0, y - .24, back + .56), (.21, .22, .24), 1, (28, 0, 0)),
            s("tip", (0, y - .31, back + .70), (.15, .18, .19), 2, (24, 0, 0)),
        ]
    if style == "fox":
        return [
            s("root", (0, y + .03, back + .08), (.20, .18, .20), 1, (26, 0, 0)),
            s("upper", (0, y - .03, back + .23), (.28, .25, .28), 0, (31, 0, 0)),
            s("middle", (0, y - .12, back + .43), (.31, .28, .31), 0, (28, 0, 0)),
            s("lower", (0, y - .21, back + .63), (.27, .26, .29), 0, (25, 0, 0)),
            s("white_tip", (0, y - .28, back + .80), (.20, .21, .23), 2, (22, 0, 0)),
        ]
    if style == "cat":
        return [
            s("root", (0, y + .03, back + .08), (.11, .16, .12), 1, (35, 0, 0)),
            s("lower", (0, y + .07, back + .22), (.12, .19, .13), 0, (-24, 0, 0)),
            s("middle", (0, y + .22, back + .30), (.12, .20, .13), 0, (-10, 0, 0)),
            s("upper", (0, y + .39, back + .30), (.11, .19, .12), 0, (5, 0, 0)),
            s("curl", (0, y + .52, back + .22), (.10, .17, .11), 2, (34, 0, 0)),
        ]
    if style == "deer":
        return [
            s("root", (0, y + .04, back + .08), (.18, .16, .17), 1, (-22, 0, 0)),
            s("tuft", (0, y + .13, back + .18), (.23, .20, .21), 0, (-34, 0, 0)),
            s("light_tip", (0, y + .21, back + .27), (.17, .15, .16), 2, (-38, 0, 0)),
        ]
    if style == "rabbit":
        return [
            s("base", (0, y + .04, back + .07), (.18, .16, .16), 1),
            s("center", (0, y + .08, back + .18), (.25, .25, .24), 0),
            s("top", (0, y + .20, back + .18), (.18, .13, .18), 2),
            s("left", (-.11, y + .08, back + .18), (.12, .17, .16), 2),
            s("right", (.11, y + .08, back + .18), (.12, .17, .16), 2),
        ]
    if style == "horse":
        return [
            s("dock", (0, y + .03, back + .09), (.18, .19, .18), 1, (24, 0, 0)),
            s("upper", (0, y - .08, back + .20), (.24, .27, .20), 0, (14, 0, 0)),
            s("left_strand", (-.08, y - .28, back + .25), (.13, .31, .15), 0, (5, 0, -3)),
            s("center_strand", (0, y - .31, back + .27), (.14, .37, .16), 1, (4, 0, 0)),
            s("right_strand", (.08, y - .27, back + .25), (.13, .30, .15), 2, (5, 0, 3)),
            s("lower_tuft", (0, y - .52, back + .29), (.24, .18, .18), 0, (3, 0, 0)),
        ]
    if style == "goat":
        return [
            s("root", (0, y + .03, back + .08), (.14, .15, .14), 1, (-24, 0, 0)),
            s("middle", (0, y + .12, back + .18), (.16, .17, .17), 0, (-35, 0, 0)),
            s("tip", (0, y + .20, back + .29), (.13, .14, .14), 2, (-42, 0, 0)),
        ]
    if style == "dragon":
        return [
            s("root", (0, y + .02, back + .08), (.22, .18, .20), 1, (32, 0, 0)),
            s("segment_1", (0, y - .04, back + .24), (.20, .18, .23), 0, (30, 0, 0)),
            s("segment_2", (0, y - .11, back + .41), (.17, .16, .22), 0, (27, 0, 0)),
            s("segment_3", (0, y - .17, back + .57), (.14, .14, .20), 0, (24, 0, 0)),
            s("segment_4", (0, y - .22, back + .71), (.11, .12, .17), 2, (21, 0, 0)),
            s("tip", (0, y - .25, back + .82), (.07, .09, .13), 2, (18, 0, 0)),
            s("ridge", (0, y + .08, back + .27), (.07, .13, .08), 2, (-8, 0, 0)),
        ]
    raise ValueError(f"Unknown tail: {style}")


def build(style, body_type="standard", color=None):
    root = copy.deepcopy(load(HEAD_DIR / "villager_head.bdengine"))
    refs = root.setdefault("refs", {}).setdefault("paintTextures", [])
    first = len(refs)
    color = color or COLORS[style]
    refs.extend(texture(tint(color, factor)) for factor in (1, .72, 1.18))
    tail = {
        "isCollection": True, "isBackCollection": False, "name": f"Tail - {style}", "nbt": "",
        "transforms": [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1],
        "children": [hair_box(name, center, size, rotation, first + tone)
                     for name, center, size, tone, rotation in specs(style, BODY_TYPES[body_type])],
    }
    root["children"].append(tail)
    root["tailStyle"] = style
    root["tailBodyType"] = body_type
    return [root], len(tail["children"])


def write(style, output):
    scene, count = build(style)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(base64.b64encode(gzip.compress(
        json.dumps(scene, separators=(",", ":")).encode(), mtime=0
    )).decode())
    assert load(output)["tailStyle"] == style
    return count


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--style", choices=["all", *TAILS], default="all")
    args = parser.parse_args()
    styles = TAILS if args.style == "all" else (args.style,)
    for style in styles:
        output = TAIL_DIR / f"villager_tail_{style}.bdengine"
        print(f"Created {output.name}: {write(style, output)} tail voxels")


if __name__ == "__main__":
    main()
