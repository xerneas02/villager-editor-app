"""Generate modular human and elven ear shapes from the shared villager head."""

import argparse
import base64
import copy
import gzip
import json
from pathlib import Path

from generate_villager_faces import find
from generate_villager_hair import HEAD_DIR, hair_box
from preview_bdengine import load


SOURCE = HEAD_DIR / "villager_head.bdengine"
EAR_DIR = HEAD_DIR / "ears"

STYLES = {
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
    assert len(ears["children"]) == count
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
