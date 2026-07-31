"""Generate modular nose shapes from the shared villager head."""

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
NOSE_DIR = HEAD_DIR / "noses"

STYLES = {
    "default": [
        ("bridge", (0, 1.63, -.52), (.16, .19, .12), (0, 0, 0)),
        ("tip", (0, 1.56, -.575), (.16, .11, .11), (0, 0, 0)),
    ],
    "small": [
        ("bridge", (0, 1.65, -.515), (.12, .15, .10), (0, 0, 0)),
        ("tip", (0, 1.56, -.575), (.13, .08, .11), (0, 0, 0)),
    ],
    "broad": [
        ("bridge", (0, 1.65, -.52), (.20, .18, .12), (0, 0, 0)),
        ("tip", (0, 1.55, -.60), (.24, .11, .15), (0, 0, 0)),
    ],
    "rounded": [
        ("bridge", (0, 1.66, -.515), (.14, .17, .10), (0, 0, 0)),
        ("middle", (0, 1.57, -.57), (.16, .12, .13), (0, 0, 0)),
        ("round_tip", (0, 1.52, -.635), (.20, .12, .17), (0, 0, 0)),
    ],
    "long": [
        ("long_bridge", (0, 1.64, -.525), (.15, .27, .12), (-4, 0, 0)),
        ("low_tip", (0, 1.48, -.61), (.16, .13, .15), (5, 0, 0)),
    ],
    "aquiline": [
        ("upper_bridge", (0, 1.68, -.515), (.15, .17, .11), (-6, 0, 0)),
        ("arched_bridge", (0, 1.57, -.575), (.16, .15, .14), (10, 0, 0)),
        ("hook_tip", (0, 1.48, -.64), (.17, .10, .14), (16, 0, 0)),
    ],
    "upturned": [
        ("short_bridge", (0, 1.65, -.515), (.14, .16, .10), (4, 0, 0)),
        ("raised_tip", (0, 1.57, -.625), (.19, .11, .16), (-12, 0, 0)),
        ("base", (0, 1.53, -.58), (.14, .07, .11), (0, 0, 0)),
    ],
}


def original_nose(head):
    nose = [
        child for child in head["children"]
        if child.get("isItemDisplay")
        and abs(child["transforms"][0] - 1.5) < .001
    ]
    assert len(nose) == 2
    return nose


def nose_group(root, style):
    target, stack = f"nose - {style}".casefold(), [root]
    while stack:
        node = stack.pop()
        if node.get("name", "").casefold() == target:
            return node
        stack.extend(node.get("children", []))


def build(style, use_template=True):
    template = NOSE_DIR / f"villager_nose_{style}.bdengine"
    if use_template and template.exists():
        root = copy.deepcopy(load(template))
        nose = nose_group(root, style)
        assert nose
        root["noseStyle"] = style
        return [root], len(nose["children"])

    root = copy.deepcopy(load(SOURCE))
    head = find(root, "head")
    originals = original_nose(head)
    head["children"] = [child for child in head["children"] if child not in originals]

    pieces = []
    for index, (name, center, size, rotation) in enumerate(STYLES[style]):
        piece = copy.deepcopy(originals[min(index, 1)])
        piece["_part"] = name
        piece["transforms"] = hair_box("", center, size, rotation, 0)["transforms"]
        pieces.append(piece)

    root["children"].append({
        "isCollection": True,
        "isBackCollection": False,
        "name": f"Nose - {style}",
        "nbt": "",
        "transforms": [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1],
        "children": pieces,
    })
    root["name"] = f"Villager Head - {style} nose"
    root["noseStyle"] = style
    return [root], len(pieces)


def write(style, output, use_template=True):
    scene, count = build(style, use_template)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(base64.b64encode(gzip.compress(
        json.dumps(scene, separators=(",", ":")).encode(), mtime=0
    )).decode())
    decoded = load(output)
    assert decoded["noseStyle"] == style
    nose = nose_group(decoded, style)
    assert nose and count == len(nose["children"])
    return count


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--style", choices=["all", *STYLES], default="all")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--rebuild-geometry", action="store_true")
    args = parser.parse_args()
    styles = STYLES if args.style == "all" else (args.style,)
    for style in styles:
        output = args.output if args.output and len(styles) == 1 else NOSE_DIR / f"villager_nose_{style}.bdengine"
        count = write(style, output, not args.rebuild_geometry)
        print(f"Created {output.name}: {count} nose voxels")


if __name__ == "__main__":
    main()
