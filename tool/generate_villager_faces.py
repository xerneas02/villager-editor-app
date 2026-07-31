"""Create minimally modified face variants from the shared villager head."""

import argparse
import base64
import copy
import gzip
import json
from pathlib import Path

from generate_villager_hair import HEAD_DIR
from preview_bdengine import load


ROOT = Path(__file__).resolve().parent.parent
SOURCE = HEAD_DIR / "villager_head.bdengine"


def find(root, name):
    stack = [root]
    while stack:
        node = stack.pop()
        if node.get("name") == name:
            return node
        stack.extend(node.get("children", []))
    raise ValueError(f"Missing face group: {name}")


def scale_columns(transform, x=1, y=1, z=1):
    result = list(transform)
    for index in (0, 4, 8):
        result[index] *= x
    for index in (1, 5, 9):
        result[index] *= y
    for index in (2, 6, 10):
        result[index] *= z
    return result


def soften(root):
    changed = []
    for name in ("left_eye", "right_eye"):
        eye = find(root, name)["children"][0]
        eye["transforms"] = scale_columns(eye["transforms"], x=1.10, y=1.03)
        changed.append(name)

    for name in ("Group 17", "Group 18"):
        brow = find(root, name)["children"][0]
        brow["transforms"] = scale_columns(brow["transforms"], x=.86, y=.48)
        changed.append(name)

    head = find(root, "head")
    nose = [child for child in head["children"]
            if child.get("isItemDisplay") and abs(child.get("transforms", [0])[0] - 1.5) < .001]
    assert len(nose) == 2
    for index, piece in enumerate(nose):
        piece["transforms"] = scale_columns(piece["transforms"], x=.86, y=.88, z=.88)
        changed.append(f"nose_{index}")
    assert len(changed) == 6
    return changed


def build(source):
    root = copy.deepcopy(load(source))
    changed = soften(root)
    root["name"] = "Villager Head - soft face"
    root["faceStyle"] = "soft"
    root["faceModifiedParts"] = changed
    return [root]


def write(source, output):
    scene = build(source)
    encoded = base64.b64encode(gzip.compress(json.dumps(scene, separators=(",", ":")).encode(), mtime=0)).decode()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(encoded)
    decoded = json.loads(gzip.decompress(base64.b64decode(output.read_text())))[0]
    assert decoded["faceStyle"] == "soft"
    assert len(decoded["faceModifiedParts"]) == 6


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", type=Path, default=SOURCE)
    parser.add_argument("--output", type=Path, default=HEAD_DIR / "villager_face_soft.bdengine")
    args = parser.parse_args()
    write(args.base, args.output)
    print(f"Created {args.output.name}: 6 modified face pieces, unchanged outer head")


if __name__ == "__main__":
    main()
