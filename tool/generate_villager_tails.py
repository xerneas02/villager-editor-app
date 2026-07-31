"""Generate animal-inspired tails fitted to villager body profiles."""

import argparse
import base64
import copy
import gzip
import json
from math import radians

from generate_villager_body import BODY_TYPES, group
from generate_villager_hair import HEAD_DIR, VILLAGER_DIR, hair_box, texture, tint
from preview_bdengine import load


TAIL_DIR = VILLAGER_DIR / "tails"
TAILS = ("wolf", "fox", "cat", "deer", "rabbit", "horse", "goat", "dragon",
         "lizard", "crocodile", "iguana", "serpent")
REPTILE = {"dragon", "lizard", "crocodile", "iguana", "serpent"}
FURRY = set(TAILS) - REPTILE
RIG_SPLITS = {"wolf": 2, "fox": 2, "cat": 2, "horse": 2, "dragon": 3,
              "lizard": 2, "crocodile": 3, "iguana": 3, "serpent": 3}
COLORS = {
    "wolf": "#746C62", "fox": "#A95F35", "cat": "#51463F", "deer": "#8A684B",
    "rabbit": "#B8AA96", "horse": "#5C4030", "goat": "#8B806E", "dragon": "#5D5148",
    "lizard": "#65705A", "crocodile": "#4E5B45", "iguana": "#66764A", "serpent": "#59664A",
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
    if style == "lizard":
        return [
            s("root", (0, y + .02, back + .09), (.25, .20, .26), 1, (28, 0, 0)),
            s("segment_1", (0, y - .05, back + .29), (.23, .18, .31), 0, (25, 0, 0)),
            s("segment_2", (0, y - .12, back + .51), (.20, .16, .30), 0, (22, 0, 0)),
            s("segment_3", (0, y - .18, back + .72), (.16, .14, .28), 0, (18, 0, 0)),
            s("segment_4", (0, y - .23, back + .91), (.12, .11, .25), 2, (15, 0, 0)),
            s("tip", (0, y - .26, back + 1.07), (.07, .08, .19), 2, (11, 0, 0)),
        ]
    if style == "crocodile":
        return [
            s("root", (0, y + .01, back + .09), (.43, .25, .30), 1, (27, 0, 0)),
            s("segment_1", (0, y - .06, back + .32), (.40, .23, .36), 0, (24, 0, 0)),
            s("segment_2", (0, y - .14, back + .58), (.34, .20, .36), 0, (21, 0, 0)),
            s("segment_3", (0, y - .21, back + .83), (.27, .17, .33), 0, (18, 0, 0)),
            s("segment_4", (0, y - .27, back + 1.04), (.20, .14, .28), 2, (15, 0, 0)),
            s("tip", (0, y - .31, back + 1.21), (.11, .10, .21), 2, (11, 0, 0)),
            s("plate_1", (0, y + .12, back + .35), (.14, .16, .13), 2, (-8, 0, 0)),
            s("plate_2", (0, y + .01, back + .68), (.12, .15, .12), 2, (-4, 0, 0)),
            s("plate_3", (0, y - .11, back + .96), (.09, .13, .10), 2, (0, 0, 0)),
        ]
    if style == "iguana":
        return [
            s("root", (0, y + .02, back + .09), (.31, .23, .28), 1, (29, 0, 0)),
            s("segment_1", (0, y - .05, back + .31), (.29, .21, .34), 0, (26, 0, 0)),
            s("segment_2", (0, y - .13, back + .55), (.25, .19, .33), 0, (23, 0, 0)),
            s("segment_3", (0, y - .20, back + .78), (.20, .16, .31), 0, (20, 0, 0)),
            s("segment_4", (0, y - .26, back + .99), (.15, .13, .27), 2, (16, 0, 0)),
            s("tip", (0, y - .30, back + 1.16), (.08, .09, .21), 2, (12, 0, 0)),
            s("spine_1", (0, y + .15, back + .30), (.07, .20, .09), 2, (-10, 0, 0)),
            s("spine_2", (0, y + .08, back + .55), (.065, .18, .08), 2, (-7, 0, 0)),
            s("spine_3", (0, y - .01, back + .78), (.055, .15, .07), 2, (-4, 0, 0)),
            s("spine_4", (0, y - .11, back + .98), (.045, .12, .06), 2, (0, 0, 0)),
        ]
    if style == "serpent":
        return [
            s("root", (0, y + .02, back + .09), (.20, .18, .26), 1, (27, 0, 0)),
            s("segment_1", (.04, y - .04, back + .29), (.19, .17, .30), 0, (24, -10, 0)),
            s("segment_2", (.12, y - .10, back + .50), (.18, .16, .29), 0, (20, -18, 0)),
            s("segment_3", (.17, y - .15, back + .70), (.16, .14, .27), 0, (17, -7, 0)),
            s("segment_4", (.12, y - .20, back + .89), (.14, .12, .25), 0, (14, 14, 0)),
            s("segment_5", (.02, y - .23, back + 1.06), (.11, .10, .22), 2, (11, 22, 0)),
            s("segment_6", (-.09, y - .25, back + 1.20), (.085, .085, .18), 2, (8, 18, 0)),
            s("tip", (-.17, y - .26, back + 1.30), (.05, .065, .13), 2, (5, 12, 0)),
        ]
    if style == "dragon":
        return [
            s("root", (0, y + .03, back + .09), (.34, .27, .29), 1, (29, 0, 0)),
            s("segment_1", (0, y - .05, back + .31), (.32, .25, .36), 0, (27, 0, 0)),
            s("segment_2", (0, y - .14, back + .56), (.29, .23, .35), 0, (24, 0, 0)),
            s("segment_3", (0, y - .23, back + .80), (.25, .21, .33), 0, (21, 0, 0)),
            s("segment_4", (0, y - .31, back + 1.02), (.20, .18, .29), 0, (18, 0, 0)),
            s("segment_5", (0, y - .37, back + 1.20), (.15, .15, .24), 2, (15, 0, 0)),
            s("tip", (0, y - .41, back + 1.34), (.09, .11, .18), 2, (12, 0, 0)),
            s("ridge_1", (0, y + .13, back + .34), (.09, .17, .11), 2, (-7, 0, 0)),
            s("ridge_2", (0, y + .02, back + .69), (.08, .15, .10), 2, (-4, 0, 0)),
            s("ridge_3", (0, y - .12, back + 1.00), (.07, .13, .09), 2, (0, 0, 0)),
        ]
    raise ValueError(f"Unknown tail: {style}")


def build(style, body_type="standard", color=None):
    root = copy.deepcopy(load(HEAD_DIR / "villager_head.bdengine"))
    refs = root.setdefault("refs", {}).setdefault("paintTextures", [])
    first = len(refs)
    color = color or COLORS[style]
    refs.extend(texture(tint(color, factor)) for factor in (1, .72, 1.18))
    parts = specs(style, BODY_TYPES[body_type])
    pivot = (0, BODY_TYPES[body_type]["pelvis_y"], parts[0][1][2])

    def boxes(items, origin):
        return [hair_box(name, tuple(value - offset for value, offset in zip(center, origin)), size,
                         rotation, first + tone) for name, center, size, tone, rotation in items]

    split = RIG_SPLITS.get(style)
    children = boxes(parts[:split] if split else parts, pivot)
    if split:
        tip_pivot = parts[split][1]
        tip = group("Tail Tip Rig", tuple(value - offset for value, offset in zip(tip_pivot, pivot)),
                    boxes(parts[split:], tip_pivot))
        children.append(tip)
    tail = group(f"Tail - {style}", pivot, children)
    tail["tailColor"] = color
    root["children"].append(tail)
    root["tailStyle"] = style
    root["tailBodyType"] = body_type
    return [root], len(parts)


def animate_tail(root):
    tail = next((node for node in nodes(root) if node.get("name", "").startswith("Tail -")), None)
    if not tail:
        return root
    style = tail["name"].removeprefix("Tail -")
    tip = next((node for node in tail.get("children", []) if node.get("name") == "Tail Tip Rig"), None)
    for animation in root.get("listAnim", []):
        field = "animation" if animation["id"] == 1 else f"animation_{animation['id']}"
        duration = max((frame["time"] for node in nodes(root) for frame in node.get(field, [])), default=0)
        if not duration:
            continue
        name = animation["name"]
        amplitude = (12 if "walking" in name or any(word in name for word in ("joy", "laugh", "wave"))
                     else 3 if any(word in name for word in ("sleep", "sit", "kneel", "pray")) else 7)
        amplitude *= {"dragon": .7, "crocodile": .55, "iguana": .7,
                      "rabbit": .55, "cat": 1.15, "lizard": 1.1, "serpent": 1.25}.get(style, 1)
        tail[field] = sway(tail, duration, amplitude)
        if tip:
            tip[field] = sway(tip, duration, amplitude * .7, lagged=True)
    root["tailAnimations"] = [entry["name"] for entry in root.get("listAnim", [])]
    return root


def nodes(root):
    yield root
    for child in root.get("children", []):
        yield from nodes(child)


def sway(node, duration, amplitude, lagged=False):
    angles = (-amplitude * .3, amplitude * .5, amplitude * .25, -amplitude * .7, -amplitude * .3) if lagged else (0, amplitude, 0, -amplitude, 0)
    default = node["defaultTransform"]
    return [{
        "time": duration * index / 4,
        "position": dict(zip("xyz", default["position"])),
        "rotation": {"x": radians(default["rotation"]["x"] + abs(angle) * .12),
                     "y": radians(default["rotation"]["y"] + angle),
                     "z": radians(default["rotation"]["z"])},
        "scale": dict(zip("xyz", default["scale"])),
    } for index, angle in enumerate(angles)]


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
