"""Add reusable personality-driven waiting animations to modular villagers."""

import base64
import copy
import gzip
import json
from math import radians
from pathlib import Path

import numpy as np

from generate_villager_accessories import walk
from generate_villager_body import group
from generate_villager_clothing import find
from preview_bdengine import boxes, load


ROOT = Path(__file__).resolve().parent.parent
EXAMPLE_DIR = ROOT / "bdengine" / "characters" / "villagers" / "examples"
ANIMATION_DIR = ROOT / "bdengine" / "characters" / "villagers" / "animations" / "waiting"
HEAD_PIVOT = (0, 1.72, -.22)
UPPER_BODY_PIVOT = (0, .88, -.22)
ANIMATION_INTENSITY = 1.5

PERSONALITIES = {
    "calm": {
        "duration": 80,
        "head": [(0,), (20, (1, -3, 0)), (40, (-1, 4, 0)), (60, (1, -2, 0)), (80,)],
        "torso": [(0,), (20, (0, 0, 0), (1, 1.025, 1)), (40,), (60, (0, 0, 0), (1, 1.025, 1)), (80,)],
        "left_arm": [(0,), (20, (0, 0, -1.5)), (40,), (60, (0, 0, -1.5)), (80,)],
        "right_arm": [(0,), (20, (0, 0, 1.5)), (40,), (60, (0, 0, 1.5)), (80,)],
        "blinks": (17, 56), "gaze": (),
    },
    "hardworking": {
        "duration": 72,
        "head": [(0,), (14, (6, -5, -1)), (30, (4, 5, 1)), (50, (7, 0, 0)), (72,)],
        "torso": [(0,), (18, (0, 0, -2)), (36, (0, 0, 2)), (54, (0, 0, -1)), (72,)],
        "left_arm": [(0,), (18, (5, 0, -5)), (36, (-2, 0, 3)), (54, (4, 0, -4)), (72,)],
        "right_arm": [(0,), (18, (-3, 0, 4)), (36, (5, 0, -5)), (54, (-2, 0, 3)), (72,)],
        "blinks": (25, 61), "gaze": ((12, -.06), (32, .05), (50, 0)),
    },
    "nervous": {
        "duration": 60,
        "head": [(0,), (8, (2, -11, -2)), (16, (-1, 13, 2)), (25, (4, -7, -1)), (39, (1, 9, 1)), (48, (3, -4, 0)), (60,)],
        "torso": [(0,), (10, (0, 0, -1.5)), (20, (0, 0, 1.5)), (31, (0, 0, -1)), (43, (0, 0, 1)), (60,)],
        "left_arm": [(0,), (9, (0, 0, -6)), (14, (0, 0, 2)), (28, (0, 0, -5)), (34, (0, 0, 1)), (60,)],
        "right_arm": [(0,), (12, (0, 0, 5)), (18, (0, 0, -2)), (38, (0, 0, 6)), (44, (0, 0, -1)), (60,)],
        "right_leg": [(0,), (10, (5, 0, 0)), (14,), (29, (5, 0, 0)), (33,), (47, (4, 0, 0)), (51,), (60,)],
        "blinks": (6, 22, 42, 54), "gaze": ((7, -.10), (17, .11), (27, -.06), (40, .08), (51, 0)),
    },
    "proud": {
        "duration": 84,
        "head": [(0,), (18, (-6, -4, 0)), (38, (-5, 5, 0)), (62, (-7, 0, 0)), (84,)],
        "torso": [(0,), (16, (0, 0, 0), (1.035, 1.025, 1)), (68, (0, 0, 0), (1.035, 1.025, 1)), (84,)],
        "left_arm": [(0,), (18, (-5, 0, -3)), (66, (-5, 0, -3)), (84,)],
        "right_arm": [(0,), (18, (-5, 0, 3)), (66, (-5, 0, 3)), (84,)],
        "blinks": (31, 70), "gaze": ((20, -.04), (42, .05), (64, 0)),
    },
    "elder": {
        "duration": 92,
        "head": [(0,), (18, (8, -3, -2)), (38, (10, 3, 2)), (60, (7, -2, -2)), (78, (9, 2, 1)), (92,)],
        "torso": [(0,), (22, (2, 0, -2)), (46, (3, 0, 2)), (70, (2, 0, -2)), (92,)],
        "left_arm": [(0,), (24, (2, 0, -3)), (48, (-1, 0, 2)), (72, (2, 0, -3)), (92,)],
        "right_arm": [(0,), (24, (-1, 0, 2)), (48, (2, 0, -3)), (72, (-1, 0, 2)), (92,)],
        "blinks": (28, 66), "gaze": ((16, -.04), (43, .04), (74, 0)),
    },
    "vigilant": {
        "duration": 76,
        "head": [(0,), (10, (0, -15, -1)), (27, (1, -15, -1)), (38, (0, 16, 1)), (58, (1, 16, 1)), (76,)],
        "torso": [(0,), (12, (0, -2, -1)), (28, (0, -2, -1)), (40, (0, 2, 1)), (60, (0, 2, 1)), (76,)],
        "left_arm": [(0,), (12, (-7, 0, -4)), (60, (-7, 0, -4)), (76,)],
        "right_arm": [(0,), (12, (-7, 0, 4)), (60, (-7, 0, 4)), (76,)],
        "left_leg": [(0,), (16, (0, 0, -1.5)), (32,), (48, (0, 0, 1.5)), (64,), (76,)],
        "blinks": (33, 67), "gaze": ((9, -.11), (29, 0), (38, .11), (61, 0)),
    },
    "monster": {
        "duration": 64,
        "head": [(0,), (9, (5, -12, -3)), (22, (7, 10, 3)), (34, (4, -7, -2)), (49, (8, 5, 2)), (64,)],
        "torso": [(0,), (12, (4, 0, -2), (1.025, 1.035, 1)), (28, (3, 0, 2)), (45, (5, 0, -2), (1.025, 1.035, 1)), (64,)],
        "left_arm": [(0,), (10, (-9, 0, -10)), (31, (-13, 0, -6)), (51, (-8, 0, -11)), (64,)],
        "right_arm": [(0,), (10, (-12, 0, 8)), (31, (-7, 0, 13)), (51, (-13, 0, 7)), (64,)],
        "left_leg": [(0,), (12, (0, 0, -3)), (52, (0, 0, -3)), (64,)],
        "right_leg": [(0,), (12, (0, 0, 3)), (52, (0, 0, 3)), (64,)],
        "blinks": (29,), "gaze": ((7, -.12), (23, .12), (37, -.08), (52, 0)),
    },
    "villain": {
        "duration": 88,
        "head": [(0,), (16, (-4, -9, -1)), (36, (-6, 7, 1)), (60, (-5, -4, 0)), (76, (-7, 2, 0)), (88,)],
        "torso": [(0,), (18, (-2, 0, -1), (1.025, 1.02, 1)), (70, (-2, 0, 1), (1.025, 1.02, 1)), (88,)],
        "left_arm": [(0,), (18, (-7, 0, -4)), (70, (-7, 0, -4)), (88,)],
        "right_arm": [(0,), (18, (-5, 0, 5)), (42, (-10, 0, 9)), (70, (-5, 0, 5)), (88,)],
        "blinks": (32, 73), "gaze": ((12, -.08), (38, .06), (63, -.03), (80, 0)),
    },
    "idiot": {
        "duration": 56,
        "head": [(0,), (7, (-2, -13, -7)), (16, (7, 8, 6)), (27, (-4, 3, -8)), (40, (5, -7, 5)), (49, (1, 10, -3)), (56,)],
        "torso": [(0,), (8, (0, 0, -3)), (17, (0, 0, 3)), (29, (1, 0, -4)), (42, (-1, 0, 3)), (56,)],
        "left_arm": [(0,), (7, (-28, 0, -16)), (16, (-38, 0, -22)), (25, (-8, 0, -5)), (56,)],
        "right_arm": [(0,), (12, (8, 0, 10)), (23, (-4, 0, -5)), (37, (7, 0, 8)), (49, (-3, 0, -4)), (56,)],
        "right_leg": [(0,), (8, (6, 0, 2)), (13,), (31, (5, 0, 2)), (36,), (56,)],
        "blinks": (5, 19, 44), "gaze": ((4, -.13), (12, .13), (24, -.05), (36, .10), (49, 0)),
    },
    "barbarian": {
        "duration": 68,
        "head": [(0,), (14, (-3, -5, -2)), (30, (2, 6, 2)), (47, (-4, -4, -2)), (68,)],
        "torso": [(0,), (16, (-2, 0, -2), (1.045, 1.04, 1)), (34,), (51, (-2, 0, 2), (1.045, 1.04, 1)), (68,)],
        "left_arm": [(0,), (12, (-12, 0, -12)), (56, (-12, 0, -12)), (68,)],
        "right_arm": [(0,), (12, (-12, 0, 12)), (56, (-12, 0, 12)), (68,)],
        "left_leg": [(0,), (12, (0, 0, -4)), (56, (0, 0, -4)), (68,)],
        "right_leg": [(0,), (12, (0, 0, 4)), (56, (0, 0, 4)), (68,)],
        "blinks": (27, 59), "gaze": ((11, -.05), (31, .05), (52, 0)),
    },
}

SHOWCASES = {
    "calm": "village_artisan", "hardworking": "village_blacksmith",
    "nervous": "road_traveler", "proud": "noblewoman",
    "elder": "elder_farmer", "vigilant": "elven_ranger",
    "monster": "village_blacksmith", "villain": "town_guard",
    "idiot": "road_traveler", "barbarian": "village_blacksmith",
}


def static_bounds(root):
    corners = np.concatenate([corner for corner, _ in boxes(root)])
    return corners.min(axis=0), corners.max(axis=0)


def reparent_head(root):
    existing = next((node for node in walk(root) if node.get("name") == "Head Rig"), None)
    if existing:
        return existing
    prefixes = ("Group 14", "Nose -", "Ears -", "Hair -", "Hat -", "Horns -", "Facial Hair -")
    members = [node for node in root["children"] if node.get("name", "").startswith(prefixes)]
    assert any(node.get("name") == "Group 14" for node in members)
    inverse = np.eye(4)
    inverse[:3, 3] = [-value for value in HEAD_PIVOT]
    for node in members:
        matrix = np.asarray(node.get("transforms", np.eye(4)), dtype=float).reshape(4, 4)
        node["transforms"] = (inverse @ matrix).reshape(-1).tolist()
        if node.get("defaultTransform"):
            node["defaultTransform"]["position"] = [
                value - offset for value, offset in zip(node["defaultTransform"]["position"], HEAD_PIVOT)
            ]
    root["children"] = [node for node in root["children"] if node not in members]
    rig = group("Head Rig", HEAD_PIVOT, members)
    root["children"].insert(0, rig)
    return rig


def reparent_character(root):
    existing = next((node for node in walk(root) if node.get("name") == "Character Rig"), None)
    if existing:
        return existing
    head = next(node for node in root["children"] if node.get("name") == "Head Rig")
    body = next(node for node in root["children"] if node.get("name") == "Body Structure")
    root["children"] = [node for node in root["children"] if node not in (head, body)]
    rig = group("Character Rig", (0, 0, 0), [head, body])
    root["children"].insert(0, rig)
    return rig


def reparent_upper_body(root):
    existing = next((node for node in walk(root) if node.get("name") == "Upper Body Rig"), None)
    if existing:
        return existing
    character = next(node for node in walk(root) if node.get("name") == "Character Rig")
    body = next(node for node in character["children"] if node.get("name") == "Body Structure")
    head = next(node for node in character["children"] if node.get("name") == "Head Rig")
    upper_names = {"Torso", "left_arm", "right_arm"}
    members = [head] + [node for node in body["children"]
                        if node.get("name") in upper_names or node.get("name", "").startswith("Wings -")]
    inverse = np.eye(4)
    inverse[:3, 3] = [-value for value in UPPER_BODY_PIVOT]
    for node in members:
        matrix = np.asarray(node.get("transforms", np.eye(4)), dtype=float).reshape(4, 4)
        node["transforms"] = (inverse @ matrix).reshape(-1).tolist()
        node["defaultTransform"]["position"] = [
            value - offset for value, offset in zip(node["defaultTransform"]["position"], UPPER_BODY_PIVOT)
        ]
    character["children"] = [node for node in character["children"] if node is not head]
    body["children"] = [node for node in body["children"] if node not in members]
    rig = group("Upper Body Rig", UPPER_BODY_PIVOT, members)
    character["children"].insert(0, rig)
    return rig


def frame(node, time, rotation=(0, 0, 0), scale=(1, 1, 1), position=(0, 0, 0)):
    default = node["defaultTransform"]
    base_scale = default["scale"]
    return {
        "time": time,
        "position": {axis: default["position"][index] + position[index] for index, axis in enumerate("xyz")},
        "rotation": {axis: radians(default["rotation"][axis] + rotation[index]) for index, axis in enumerate("xyz")},
        "scale": {axis: base_scale[index] * scale[index] for index, axis in enumerate("xyz")},
    }


def track(node, poses):
    return [frame(
        node, pose[0],
        tuple(value * ANIMATION_INTENSITY for value in (pose[1] if len(pose) > 1 else (0, 0, 0))),
        tuple(1 + (value - 1) * ANIMATION_INTENSITY for value in (pose[2] if len(pose) > 2 else (1, 1, 1))),
    ) for pose in poses]


def eye_track(node, duration, blinks, gaze):
    times = {0, duration, *(time for event in blinks for time in (event - 1, event, event + 1)),
             *(time for time, _ in gaze)}
    result = []
    for time in sorted(times):
        offset = next((value for event, value in reversed(gaze) if event <= time), 0) * 1.25
        result.append(frame(node, time, scale=(1, .025 if time in blinks else 1, 1), position=(offset, 0, 0)))
    return result


def clear_animations(root):
    for node in walk(root):
        for key in [key for key in node if key == "animation" or key.startswith("animation_")]:
            del node[key]


def add_animations(root, styles, generic_name=False):
    before = static_bounds(root)
    rig = reparent_head(root)
    reparent_character(root)
    upper = reparent_upper_body(root)
    after = static_bounds(root)
    assert np.allclose(before[0], after[0]) and np.allclose(before[1], after[1])
    clear_animations(root)
    root["listAnim"] = []
    for identifier, style in enumerate(styles, 1):
        profile = PERSONALITIES[style]
        field = "animation" if identifier == 1 else f"animation_{identifier}"
        targets = {
            "head": rig,
            "left_arm": find(root, "left_arm"), "right_arm": find(root, "right_arm"),
            "left_leg": find(root, "left_leg"), "right_leg": find(root, "right_leg"),
        }
        for target, poses in profile.items():
            if target in targets:
                targets[target][field] = track(targets[target], poses)
            elif target == "torso":
                upper[field] = track(upper, [(pose[0], pose[1] if len(pose) > 1 else (0, 0, 0)) for pose in poses])
                torso = find(root, "Torso")
                torso[field] = track(torso, [(pose[0], (0, 0, 0), pose[2] if len(pose) > 2 else (1, 1, 1)) for pose in poses])
        for eye in (find(root, "left_eye"), find(root, "right_eye")):
            eye[field] = eye_track(eye, profile["duration"], profile["blinks"], profile["gaze"])
        root["listAnim"].append({"id": identifier, "name": "waiting" if generic_name else f"waiting_{style}"})
    root["waitingAnimations"] = list(styles)
    return root


def write(root, output):
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(base64.b64encode(gzip.compress(
        json.dumps([root], separators=(",", ":")).encode(), mtime=0
    )).decode())


def main():
    source = {name: load(EXAMPLE_DIR / f"villager_example_{name}.bdengine")
              for name in set(SHOWCASES.values())}
    styles = tuple(PERSONALITIES)
    for path in sorted(EXAMPLE_DIR.glob("villager_example_*.bdengine")):
        root = add_animations(load(path), styles)
        write(root, path)
        print(f"Added {len(styles)} waiting animations to {path.name}")
    for style, example in SHOWCASES.items():
        root = add_animations(copy.deepcopy(source[example]), (style,), generic_name=True)
        root["name"] = f"Villager Waiting - {style}"
        write(root, ANIMATION_DIR / f"villager_waiting_{style}.bdengine")
        print(f"Created villager_waiting_{style}.bdengine")


if __name__ == "__main__":
    main()
