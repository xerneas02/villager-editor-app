"""Add recolourable fantasy hairstyles to the shared villager head."""

import argparse
import base64
import copy
import gzip
import io
import json
import sys
from pathlib import Path

from PIL import Image, ImageColor

from preview_bdengine import load


ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from math_utils import MathUtils

VILLAGER_DIR = ROOT / "bdengine" / "characters" / "villagers"
HEAD_DIR = VILLAGER_DIR / "heads"
HAIR_DIR = VILLAGER_DIR / "hair"
SOURCE = HEAD_DIR / "villager_head.bdengine"
FACE_REGIONS = ((8, 0), (16, 0), (8, 8), (24, 8), (0, 8), (16, 8))


def tint(color, factor):
    return tuple(max(0, min(255, round(channel * factor))) for channel in ImageColor.getrgb(color))


def texture(rgb):
    image = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    tile = Image.new("RGBA", (8, 8), rgb + (255,))
    for origin in FACE_REGIONS:
        image.paste(tile, origin)
    data = io.BytesIO()
    image.save(data, "PNG", optimize=True)
    return "data:image/png;base64," + base64.b64encode(data.getvalue()).decode()


def hair_box(name, center, size, rotation, texture_index):
    width, height, depth = size
    matrix = MathUtils.create_rotation_matrix(rotation)
    r = [matrix[0:3], matrix[4:7], matrix[8:11]]
    # A BDE head hangs below its transform origin; move the origin so rotation keeps
    # the requested geometric centre fixed.
    top_offset = [r[row][1] * height / 2 for row in range(3)]
    position = [center[i] + top_offset[i] for i in range(3)]
    sx, sy, sz = width * 2, height * 2, depth * 2
    return {
        "isItemDisplay": True,
        "name": "player_head[display=none]",
        "_part": name,
        "brightness": {"sky": 15, "block": 0},
        "nbt": "",
        "tagHead": {"Value": ""},
        "textureValueList": [],
        "paintTexture": texture_index,
        "transforms": [
            r[0][0] * sx, r[0][1] * sy, r[0][2] * sz, position[0],
            r[1][0] * sx, r[1][1] * sy, r[1][2] * sz, position[1],
            r[2][0] * sx, r[2][1] * sy, r[2][2] * sz, position[2],
            0, 0, 0, 1,
        ],
    }


def cap():
    return [
        # Thin continuous shell: detail locks may rotate without opening holes to the skull.
        ("scalp_top", (0, 2.045, -.23), (.80, .07, .52), (0, 0, 0), 0),
        ("scalp_back_top", (0, 1.95, .065), (.76, .20, .07), (0, 0, 0), 1),
        ("scalp_back_left", (-.27, 1.80, .067), (.24, .22, .075), (0, 0, -2), 1),
        ("scalp_back_mid_left", (-.09, 1.78, .067), (.20, .26, .075), (0, 0, -1), 0),
        ("scalp_back_mid_right", (.09, 1.78, .067), (.20, .26, .075), (0, 0, 1), 0),
        ("scalp_back_right", (.27, 1.80, .067), (.24, .22, .075), (0, 0, 2), 2),
        ("scalp_left", (-.425, 1.90, -.20), (.07, .28, .45), (0, 0, 0), 1),
        ("scalp_right", (.425, 1.90, -.20), (.07, .28, .45), (0, 0, 0), 0),
        ("scalp_hairline", (0, 2.005, -.515), (.72, .10, .055), (-3, 0, 0), 1),
        ("top_left", (-.19, 2.075, -.22), (.41, .11, .46), (0, -4, -4), 0),
        ("top_right", (.19, 2.07, -.22), (.41, .11, .46), (0, 4, 4), 2),
        ("top_seam", (0, 2.09, -.22), (.16, .10, .45), (0, 0, 0), 0),
        ("left_temple", (-.445, 1.81, -.25), (.09, .23, .29), (-3, 0, 5), 1),
        ("right_temple", (.445, 1.81, -.25), (.09, .23, .29), (-3, 0, -5), 0),
    ]


def short_heroic():
    return cap() + [
        ("fringe_0", (-.31, 1.99, -.535), (.13, .21, .075), (-8, 0, -13), 1),
        ("fringe_1", (-.16, 1.97, -.545), (.13, .25, .075), (-10, 0, -7), 0),
        ("fringe_2", (0, 1.98, -.55), (.13, .24, .075), (-11, 0, 3), 0),
        ("fringe_3", (.16, 1.99, -.545), (.13, .22, .075), (-9, 0, 8), 2),
        ("fringe_4", (.31, 2.00, -.535), (.12, .19, .075), (-7, 0, 14), 1),
        ("crown", (-.06, 2.145, -.16), (.31, .10, .27), (0, -7, -8), 2),
        ("left_nape", (-.20, 1.70, .105), (.20, .21, .08), (3, 0, -4), 1),
        ("right_nape", (.20, 1.71, .105), (.20, .19, .08), (3, 0, 4), 0),
    ]


def swept():
    return cap() + [
        ("swept_crown", (-.13, 2.145, -.21), (.55, .11, .34), (2, -8, -11), 2),
        ("swept_0", (-.23, 2.01, -.545), (.19, .15, .075), (-7, 0, 16), 1),
        ("swept_1", (-.05, 2.00, -.55), (.20, .17, .075), (-8, 0, 16), 0),
        ("swept_2", (.14, 1.98, -.55), (.20, .20, .075), (-9, 0, 15), 0),
        ("swept_3", (.30, 1.94, -.545), (.15, .26, .08), (-9, 0, 13), 2),
        ("long_front_lock", (.40, 1.84, -.53), (.11, .42, .09), (-7, 0, -11), 1),
        ("rear_flick", (-.35, 2.03, .07), (.25, .11, .25), (13, -16, -9), 2),
        ("crown_ridge", (.08, 2.19, -.17), (.30, .08, .23), (2, -7, 13), 2),
        ("opposite_nape", (-.25, 1.72, .105), (.24, .22, .08), (3, 0, -6), 1),
    ]


def long_wizard():
    locks = cap() + [
        ("forelock_0", (-.31, 1.91, -.55), (.13, .34, .08), (-7, 0, -7), 2),
        ("forelock_1", (-.15, 1.96, -.555), (.14, .26, .08), (-8, 0, -3), 0),
        ("forelock_2", (.01, 1.98, -.555), (.14, .23, .08), (-9, 0, 2), 0),
        ("forelock_3", (.17, 1.96, -.555), (.14, .26, .08), (-8, 0, 4), 1),
        ("forelock_4", (.32, 1.92, -.55), (.13, .32, .08), (-7, 0, 7), 1),
    ]
    for index, x in enumerate((-.36, -.18, 0, .18, .36)):
        locks.append((f"back_lock_{index}", (x, 1.60 - abs(x) * .12, .105),
                      (.16, .72 - abs(x) * .18, .11), (4, 0, x * 18), index % 3))
    locks += [
        ("left_side_lock", (-.47, 1.60, -.18), (.12, .70, .30), (-4, 0, 5), 1),
        ("right_side_lock", (.47, 1.63, -.18), (.12, .64, .30), (-4, 0, -5), 0),
    ]
    return locks


def braided():
    locks = cap() + [
        ("left_swept", (-.18, 2.09, -.37), (.44, .14, .31), (0, -5, -10), 2),
        ("right_swept", (.20, 2.08, -.36), (.43, .14, .31), (0, 5, 10), 0),
        ("braid_root", (0, 1.90, .11), (.27, .24, .17), (5, 0, 0), 1),
    ]
    for index, (x, y, angle) in enumerate(((.03, 1.71, 8), (-.03, 1.54, -8), (.025, 1.37, 7), (0, 1.22, 0))):
        locks.append((f"braid_{index}", (x, y, .14), (.22 - index * .02, .22, .18),
                      (4, 0, angle), index % 3))
    locks.append(("braid_tip", (0, 1.08, .14), (.11, .16, .11), (6, 0, 0), 1))
    return locks


def long_back_mass(bottom=.72):
    pieces = []
    for index, x in enumerate((-.32, -.16, 0, .16, .32)):
        local_bottom = bottom + abs(x) * .38
        height = 1.83 - local_bottom
        pieces.append((f"long_underlayer_{index}", (x, local_bottom + height / 2, .095),
                       (.18, height, .075), (2, 0, 0), 1 if index % 2 else 0))
    return pieces


def very_long_loose():
    locks = cap() + long_back_mass(.68) + [
        ("part_left", (-.18, 2.12, -.34), (.42, .11, .32), (0, -5, -8), 2),
        ("part_right", (.18, 2.11, -.34), (.42, .11, .32), (0, 5, 8), 0),
        ("left_face_lock", (-.44, 1.58, -.39), (.12, .84, .17), (-3, 0, 5), 1),
        ("right_face_lock", (.44, 1.60, -.39), (.12, .80, .17), (-3, 0, -5), 0),
        ("left_outer_length", (-.47, 1.15, -.10), (.14, 1.02, .20), (1, 0, 4), 0),
        ("right_outer_length", (.47, 1.18, -.10), (.14, .96, .20), (1, 0, -4), 2),
    ]
    for index, x in enumerate((-.36, -.24, -.12, 0, .12, .24, .36)):
        locks.append((f"loose_back_lock_{index}", (x, 1.13, .14),
                      (.12, 1.14 - abs(x) * .70, .09), (3, 0, x * 16), index % 3))
    return locks


def elven_cascade():
    locks = cap() + long_back_mass(.78) + [
        ("elven_part_left", (-.19, 2.12, -.34), (.43, .10, .31), (0, -6, -10), 2),
        ("elven_part_right", (.19, 2.11, -.34), (.43, .10, .31), (0, 6, 10), 0),
        ("left_swept_temple", (-.38, 1.91, -.42), (.13, .38, .12), (-7, 0, 12), 1),
        ("right_swept_temple", (.38, 1.91, -.42), (.13, .38, .12), (-7, 0, -12), 0),
        ("left_ear_lock", (-.48, 1.48, -.12), (.11, .70, .18), (-2, 0, 4), 0),
        ("right_ear_lock", (.48, 1.50, -.12), (.11, .67, .18), (-2, 0, -4), 2),
    ]
    for side, sign in (("left", -1), ("right", 1)):
        for index, (y, angle) in enumerate(((1.66, 9), (1.49, -8), (1.33, 7))):
            locks.append((f"{side}_temple_braid_{index}", (sign * (.47 + index * .01), y, -.30),
                          (.11 - index * .01, .20, .10), (-2, 0, sign * angle), index % 3))
    for index, x in enumerate((-.34, -.20, -.07, .07, .20, .34)):
        locks.append((f"cascade_lock_{index}", (x, 1.17, .145),
                      (.14, 1.03 - abs(x) * .65, .09), (3, 0, x * 13), (index + 1) % 3))
    return locks


def elven_half_up():
    locks = cap() + long_back_mass(.82) + [
        ("half_up_left", (-.19, 2.11, -.34), (.42, .10, .31), (0, -6, -9), 2),
        ("half_up_right", (.19, 2.10, -.34), (.42, .10, .31), (0, 6, 9), 0),
        ("left_front_tendril", (-.40, 1.72, -.48), (.09, .50, .09), (-6, 0, 6), 1),
        ("right_front_tendril", (.40, 1.74, -.48), (.09, .46, .09), (-6, 0, -6), 0),
        ("half_up_knot_left", (-.09, 1.82, .15), (.22, .22, .17), (4, 0, -8), 1),
        ("half_up_knot_right", (.09, 1.82, .15), (.22, .22, .17), (4, 0, 8), 2),
    ]
    for index, x in enumerate((-.28, -.14, 0, .14, .28)):
        locks.append((f"half_up_tail_{index}", (x, 1.12, .17),
                      (.14, 1.18 - abs(x) * .72, .10), (4, 0, x * 15), index % 3))
    for side, sign in (("left", -1), ("right", 1)):
        for index, (x, y, angle) in enumerate(((.40, 1.91, 10), (.44, 1.74, -9), (.46, 1.57, 8))):
            locks.append((f"half_up_{side}_braid_{index}", (sign * x, y, -.24),
                          (.10, .20, .09), (-2, 0, sign * angle), (index + 1) % 3))
    return locks


STYLES = {
    "short_heroic": short_heroic,
    "swept": swept,
    "long_wizard": long_wizard,
    "braided": braided,
    "very_long_loose": very_long_loose,
    "elven_cascade": elven_cascade,
    "elven_half_up": elven_half_up,
}


def color_eyebrows(root, texture_index):
    stack = [root]
    while stack:
        node = stack.pop()
        if node.get("name") in ("Group 17", "Group 18"):
            node["children"][0]["paintTexture"] = texture_index
        stack.extend(node.get("children", []))


def build(style, color, use_template=True):
    # Hand-cleaned exports are authoritative: preserve their exact geometry and only
    # replace the three palette entries when generating another colour.
    template = HAIR_DIR / f"villager_hair_{style}.bdengine"
    if use_template and template.exists():
        root = copy.deepcopy(load(template))
        hair = next(group for group in root["children"] if group.get("name") == f"Hair - {style}")
        textures = root.setdefault("refs", {}).setdefault("paintTextures", [])
        used = sorted({piece.get("paintTexture") for piece in hair["children"] if isinstance(piece.get("paintTexture"), int)})
        assert len(used) == 3
        for index, factor in zip(used, (1, .82, 1.12)):
            textures[index] = texture(tint(color, factor))
        color_eyebrows(root, used[0])
        root["hairStyle"] = style
        root["hairColor"] = color
        return [root], len(hair["children"])

    root = copy.deepcopy(load(SOURCE))
    textures = root.setdefault("refs", {}).setdefault("paintTextures", [])
    first_texture = len(textures)
    textures.extend(texture(tint(color, factor)) for factor in (1, .82, 1.12))
    pieces = [hair_box(name, center, size, rotation, first_texture + tone)
              for name, center, size, rotation, tone in STYLES[style]()]
    root["children"].append({
        "isCollection": True,
        "isBackCollection": False,
        "name": f"Hair - {style}",
        "nbt": "",
        "transforms": [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1],
        "children": pieces,
    })
    root["name"] = f"Villager Head - {style}"
    root["hairStyle"] = style
    root["hairColor"] = color
    color_eyebrows(root, first_texture)
    return [root], len(pieces)


def write(style, color, output, use_template=True):
    scene, count = build(style, color, use_template)
    encoded = base64.b64encode(gzip.compress(json.dumps(scene, separators=(",", ":")).encode(), mtime=0)).decode()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(encoded)
    decoded = json.loads(gzip.decompress(base64.b64decode(output.read_text())))
    hair = decoded[0]["children"][-1]
    assert hair["name"] == f"Hair - {style}"
    assert len(hair["children"]) == count
    assert any(abs(piece["transforms"][index]) > .001 for piece in hair["children"] for index in (1, 2, 4, 6, 8, 9))
    return count


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--style", choices=["all", *STYLES], default="all")
    parser.add_argument("--color", default="#806044")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--rebuild-geometry", action="store_true")
    args = parser.parse_args()
    ImageColor.getrgb(args.color)
    styles = STYLES if args.style == "all" else (args.style,)
    for style in styles:
        output = args.output if args.output and len(styles) == 1 else HAIR_DIR / f"villager_hair_{style}.bdengine"
        count = write(style, args.color, output, not args.rebuild_geometry)
        print(f"Created {output.name}: {count} rotated/recolourable hair pieces")


if __name__ == "__main__":
    main()
