"""Generate modular human and elven ear shapes from the shared villager head."""

import argparse
import base64
import copy
import gzip
import json
from pathlib import Path

from generate_villager_faces import find
from generate_villager_body import group
from generate_villager_hair import HEAD_DIR, hair_box
from preview_bdengine import load


SOURCE = HEAD_DIR / "villager_head.bdengine"
EAR_DIR = HEAD_DIR / "ears"

STYLES = {
    "none": [],
    "small": [
        ("ear", .37, 1.72, -.345, (.13, .18, .09), 0),
    ],
    "broad": [
        ("ear", .40, 1.72, -.345, (.23, .26, .10), 0),
    ],
    "rounded": [
        ("ear_center", .39, 1.72, -.345, (.20, .18, .10), 0),
        ("ear_top", .38, 1.81, -.345, (.15, .08, .09), 0),
        ("ear_lobe", .37, 1.63, -.345, (.13, .09, .09), 0),
    ],
    "elf_short": [
        ("ear_base", .39, 1.72, -.345, (.20, .22, .10), 0),
        ("ear_mid", .50, 1.75, -.345, (.18, .16, .09), 8),
        ("ear_tip", .61, 1.79, -.345, (.15, .09, .075), 12),
    ],
    "elf_long": [
        ("ear_base", .39, 1.72, -.345, (.21, .23, .10), 0),
        ("ear_mid", .51, 1.75, -.345, (.20, .18, .09), 7),
        ("ear_outer", .65, 1.79, -.345, (.19, .13, .08), 11),
        ("ear_tip", .79, 1.84, -.345, (.16, .075, .065), 15),
    ],
    "cat": [
        ("socket", .34, 1.99, -.18, (.20, .14, .16), 0),
        ("lower", .35, 2.08, -.18, (.18, .16, .15), 2),
        ("upper", .36, 2.20, -.18, (.13, .16, .12), 4),
        ("tip", .37, 2.30, -.18, (.075, .10, .08), 6),
    ],
    "wolf": [
        ("socket", .36, 1.98, -.17, (.22, .15, .17), 0),
        ("lower", .39, 2.10, -.17, (.20, .20, .16), 7),
        ("middle", .43, 2.25, -.17, (.15, .19, .13), 10),
        ("tip", .47, 2.38, -.17, (.085, .13, .09), 13),
    ],
    "fox": [
        ("socket", .35, 1.98, -.18, (.23, .15, .18), 0),
        ("lower", .40, 2.10, -.18, (.23, .20, .17), 8),
        ("middle", .47, 2.26, -.18, (.18, .21, .14), 12),
        ("upper", .53, 2.41, -.18, (.12, .18, .11), 15),
        ("tip", .57, 2.53, -.18, (.07, .11, .075), 18),
    ],
    "rabbit": [
        ("socket", .28, 1.99, -.16, (.18, .14, .15), 0),
        ("lower", .29, 2.12, -.16, (.17, .22, .14), 1),
        ("middle", .30, 2.31, -.16, (.15, .22, .13), 2),
        ("upper", .31, 2.49, -.16, (.12, .19, .11), 3),
        ("tip", .32, 2.62, -.16, (.075, .12, .08), 4),
    ],
    "deer": [
        ("socket", .39, 1.82, -.24, (.20, .20, .13), 0),
        ("inner", .50, 1.89, -.22, (.20, .16, .12), 12),
        ("outer", .64, 1.98, -.20, (.20, .14, .11), 18),
        ("tip", .77, 2.06, -.18, (.13, .09, .085), 22),
    ],
    "goat": [
        ("socket", .39, 1.82, -.23, (.19, .19, .13), 0),
        ("stalk", .51, 1.84, -.21, (.20, .13, .12), 8),
        ("droop", .65, 1.79, -.19, (.20, .13, .11), -12),
        ("tip", .78, 1.73, -.18, (.13, .08, .08), -16),
    ],
    "horse": [
        ("socket", .33, 1.98, -.16, (.20, .15, .16), 0),
        ("lower", .34, 2.10, -.16, (.18, .19, .15), 2),
        ("upper", .35, 2.25, -.16, (.13, .18, .12), 4),
        ("tip", .36, 2.37, -.16, (.08, .12, .08), 6),
    ],
    "ogre": [
        ("socket", .39, 1.73, -.29, (.22, .22, .14), 0),
        ("stalk", .52, 1.75, -.29, (.20, .14, .13), 5),
        ("bell_center", .66, 1.78, -.29, (.22, .20, .14), 8),
        ("bell_top", .68, 1.88, -.29, (.17, .08, .13), 8),
        ("bell_lower", .68, 1.68, -.29, (.17, .08, .13), 8),
    ],
}


def original_ears(head):
    ears = [
        child for child in head["children"]
        if child.get("isItemDisplay")
        and abs(child["transforms"][0] - 2.375) < .001
        and abs(child["transforms"][10] - 1) < .001
    ]
    assert len(ears) == 2
    return ears


def anchor_ears(root):
    ears = next((node for node in _walk(root) if node.get("name", "").startswith("Ears -")), None)
    if not ears or not ears.get("children") or any(child.get("name", "").endswith("Ear Rig") for child in ears["children"]):
        return root
    style = ears["name"].removeprefix("Ears - ")
    specs = STYLES.get(style)
    if not specs:
        return root
    _, x, y, z, size, _ = specs[0]
    rigs = []
    for side, sign in (("left", -1), ("right", 1)):
        pivot = (sign * (x - size[0] / 2), y, z)
        children = [child for child in ears["children"] if child.get("_part", "").startswith(f"{side}_")]
        for child in children:
            for index, value in zip((3, 7, 11), pivot):
                child["transforms"][index] -= value
        rigs.append(group(f"{side.title()} Ear Rig", pivot, children))
    ears["children"] = rigs
    return root


def _walk(node):
    yield node
    for child in node.get("children", []):
        yield from _walk(child)


def build(style):
    root = copy.deepcopy(load(SOURCE))
    head = find(root, "head")
    originals = original_ears(head)
    head["children"] = [child for child in head["children"] if child not in originals]

    pieces = []
    for side, sign, source in (("left", -1, originals[0]), ("right", 1, originals[1])):
        for name, x, y, z, size, angle in STYLES[style]:
            piece = copy.deepcopy(source)
            piece["_part"] = f"{side}_{name}"
            piece["transforms"] = hair_box("", (sign * x, y, z), size, (0, 0, sign * angle), 0)["transforms"]
            pieces.append(piece)

    root["children"].append({
        "isCollection": True,
        "isBackCollection": False,
        "name": f"Ears - {style}",
        "nbt": "",
        "transforms": [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1],
        "children": pieces,
    })
    root["name"] = f"Villager Head - {style} ears"
    root["earStyle"] = style
    anchor_ears(root)
    return [root], len(pieces)


def write(style, output):
    scene, count = build(style)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(base64.b64encode(gzip.compress(
        json.dumps(scene, separators=(",", ":")).encode(), mtime=0
    )).decode())
    decoded = load(output)
    ears = decoded["children"][-1]
    assert decoded["earStyle"] == style
    assert ears["name"] == f"Ears - {style}"
    assert sum(len(rig["children"]) for rig in ears["children"]) == count
    return count


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--style", choices=["all", *STYLES], default="all")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    styles = STYLES if args.style == "all" else (args.style,)
    for style in styles:
        output = args.output if args.output and len(styles) == 1 else EAR_DIR / f"villager_ears_{style}.bdengine"
        count = write(style, output)
        print(f"Created {output.name}: {count} ear voxels")


if __name__ == "__main__":
    main()
