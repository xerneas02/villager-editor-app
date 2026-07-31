"""Add reusable personality-driven talking animations to modular villagers."""

import copy
from pathlib import Path

from generate_villager_accessories import walk
from generate_villager_body import group
from generate_villager_clothing import find
from generate_villager_waiting_animations import (
    EXAMPLE_DIR, clear_animations, eye_track, frame, reparent_character, reparent_head, reparent_upper_body, track, write,
)
from preview_bdengine import load


ROOT = Path(__file__).resolve().parent.parent
ANIMATION_DIR = ROOT / "bdengine" / "characters" / "villagers" / "animations" / "talking"
MOUTH_INTENSITY = 1.2
MOUTH_TO_WORLD_Y = .2109

PERSONALITIES = {
    "calm": {
        "duration": 40,
        "head": [(0,), (10, (2, -4, 0)), (20, (-1, 4, 0)), (30, (2, -2, 0)), (40,)],
        "torso": [(0,), (12, (0, 0, -1)), (24, (0, 0, 1)), (40,)],
        "left_arm": [(0,), (10, (4, 0, -5)), (22, (1, 0, -2)), (32, (4, 0, -5)), (40,)],
        "mouth": ((0, 0), (3, -.30), (5, -.06), (8, -.24), (11, 0), (15, -.32), (18, -.08), (22, -.25), (26, 0), (30, -.27), (34, 0), (40, 0)),
        "brow": ((0, 0), (8, 4), (18, 0), (28, 3), (36, 0), (40, 0)),
        "blinks": (19,), "gaze": ((0, 0), (12, -.04), (24, .04), (34, 0)),
    },
    "lively": {
        "duration": 34,
        "head": [(0,), (5, (-3, -8, -2)), (10, (4, 7, 2)), (17, (-2, -5, -1)), (24, (5, 8, 2)), (30, (-2, -3, 0)), (34,)],
        "torso": [(0,), (7, (0, 0, -3)), (15, (0, 0, 3)), (24, (0, 0, -2)), (34,)],
        "left_arm": [(0,), (5, (-5, 0, -12)), (12, (6, 0, 5)), (20, (-4, 0, -10)), (28, (4, 0, 3)), (34,)],
        "right_arm": [(0,), (7, (6, 0, 8)), (14, (-5, 0, -12)), (22, (5, 0, 9)), (29, (-3, 0, -5)), (34,)],
        "mouth": ((0, 0), (2, -.35), (4, -.08), (6, -.30), (8, -.12), (11, -.38), (13, 0), (16, -.28), (18, -.06), (21, -.36), (24, -.10), (27, -.31), (30, 0), (32, -.22), (34, 0)),
        "brow": ((0, 0), (4, 9), (10, -3), (16, 7), (23, 2), (29, 8), (34, 0)),
        "blinks": (15,), "gaze": ((0, 0), (6, -.08), (14, .08), (23, -.05), (30, 0)),
    },
    "shy": {
        "duration": 48,
        "head": [(0,), (8, (9, -7, -3)), (20, (11, -3, -4)), (30, (8, 5, 2)), (40, (10, -2, -3)), (48,)],
        "torso": [(0,), (10, (3, 0, -1)), (38, (3, 0, 1)), (48,)],
        "left_arm": [(0,), (8, (4, 0, -8)), (40, (4, 0, -8)), (48,)],
        "right_arm": [(0,), (8, (4, 0, 8)), (40, (4, 0, 8)), (48,)],
        "mouth": ((0, 0), (5, -.16), (8, 0), (13, -.20), (16, -.05), (21, 0), (27, -.18), (30, -.04), (35, 0), (40, -.15), (43, 0), (48, 0)),
        "brow": ((0, 0), (8, -5), (20, -7), (32, -4), (42, -6), (48, 0)),
        "blinks": (11, 34), "gaze": ((0, 0), (7, -.10), (23, -.04), (31, .05), (42, 0)),
    },
    "authoritative": {
        "duration": 44,
        "head": [(0,), (8, (-5, -5, 0)), (18, (-7, 5, 0)), (30, (-5, -3, 0)), (40, (-6, 2, 0)), (44,)],
        "torso": [(0,), (8, (-2, 0, 0), (1.025, 1.02, 1)), (36, (-2, 0, 0), (1.025, 1.02, 1)), (44,)],
        "right_arm": [(0,), (6, (-12, 0, 11)), (14, (-20, 0, 18)), (22, (-8, 0, 8)), (30, (-18, 0, 15)), (38, (-6, 0, 5)), (44,)],
        "left_arm": [(0,), (8, (-4, 0, -3)), (36, (-4, 0, -3)), (44,)],
        "mouth": ((0, 0), (3, -.34), (6, -.08), (10, -.38), (14, 0), (18, -.31), (21, -.10), (25, -.37), (29, 0), (33, -.35), (37, -.08), (41, -.28), (44, 0)),
        "brow": ((0, 0), (5, -8), (16, -4), (24, -9), (35, -5), (44, 0)),
        "blinks": (27,), "gaze": ((0, 0), (9, -.05), (20, .05), (32, 0)),
    },
    "storyteller": {
        "duration": 64,
        "head": [(0,), (10, (5, -8, -2)), (22, (-1, 7, 2)), (34, (7, -3, -2)), (46, (2, 9, 2)), (56, (6, -4, -1)), (64,)],
        "torso": [(0,), (14, (1, 0, -2)), (28, (0, 0, 2)), (44, (2, 0, -2)), (64,)],
        "left_arm": [(0,), (8, (-8, 0, -12)), (18, (-14, 0, -20)), (30, (-5, 0, -8)), (42, (-12, 0, -17)), (54, (-4, 0, -6)), (64,)],
        "right_arm": [(0,), (16, (4, 0, 5)), (34, (-5, 0, 10)), (50, (3, 0, 4)), (64,)],
        "mouth": ((0, 0), (3, -.25), (6, -.08), (9, -.32), (13, 0), (18, -.28), (22, -.05), (26, -.35), (30, 0), (36, -.22), (39, -.08), (43, -.34), (48, 0), (53, -.30), (57, -.06), (61, -.24), (64, 0)),
        "brow": ((0, 0), (8, 6), (18, 2), (28, 9), (40, -3), (52, 7), (60, 2), (64, 0)),
        "blinks": (31, 58), "gaze": ((0, 0), (10, -.06), (24, .07), (38, -.04), (51, .05), (61, 0)),
    },
    "excited": {
        "duration": 30,
        "head": [(0,), (4, (-7, -9, -3)), (9, (6, 9, 3)), (14, (-5, -7, -2)), (20, (7, 8, 3)), (26, (-3, -4, -1)), (30,)],
        "torso": [(0,), (5, (-3, 0, -4), (1.03, 1.04, 1)), (11, (2, 0, 4)), (17, (-3, 0, -4)), (23, (2, 0, 4)), (30,)],
        "left_arm": [(0,), (4, (-15, 0, -18)), (9, (8, 0, 8)), (15, (-18, 0, -20)), (22, (7, 0, 7)), (27, (-10, 0, -12)), (30,)],
        "right_arm": [(0,), (4, (-15, 0, 18)), (9, (8, 0, -8)), (15, (-18, 0, 20)), (22, (7, 0, -7)), (27, (-10, 0, 12)), (30,)],
        "mouth": ((0, 0), (2, -.40), (4, -.10), (6, -.34), (8, -.06), (10, -.42), (13, 0), (15, -.36), (17, -.09), (19, -.40), (22, 0), (24, -.35), (27, -.08), (30, 0)),
        "brow": ((0, 0), (3, 12), (9, 5), (15, 13), (22, 6), (27, 11), (30, 0)),
        "blinks": (12,), "gaze": ((0, 0), (5, -.09), (11, .09), (18, -.07), (25, 0)),
    },
}

SHOWCASES = {
    "calm": "young_cleric", "lively": "village_artisan",
    "shy": "forest_huntress", "authoritative": "town_guard",
    "storyteller": "elder_farmer", "excited": "road_traveler",
}


def mouth_track(node, poses):
    return [frame(node, time, position=(0, y * MOUTH_INTENSITY, 0)) for time, y in poses]


def brow_track(node, poses, sign):
    return [frame(node, time, rotation=(0, 0, sign * angle * 1.35)) for time, angle in poses]


def facial_hair_rigs(root):
    result = []
    for facial_hair in [node for node in walk(root) if node.get("name", "").startswith("Facial Hair -")]:
        existing = {child.get("name"): child for child in facial_hair.get("children", [])}
        if "Upper Facial Hair Rig" in existing:
            result.append((existing["Upper Facial Hair Rig"], existing.get("Jaw Beard Rig")))
            continue
        style = facial_hair["name"].removeprefix("Facial Hair - ")
        moustache_only = style.startswith("moustache_") and style != "moustache_goatee"
        split = len(facial_hair["children"]) if moustache_only else min(5, len(facial_hair["children"]))
        upper, lower = facial_hair["children"][:split], facial_hair["children"][split:]
        upper_rig = group("Upper Facial Hair Rig", (0, 0, 0), upper)
        jaw_rig = group("Jaw Beard Rig", (0, 0, 0), lower) if lower else None
        facial_hair["children"] = [upper_rig] + ([jaw_rig] if jaw_rig else [])
        result.append((upper_rig, jaw_rig))
    return result


def facial_hair_track(node, poses, ratio):
    return [frame(node, time, position=(0, y * MOUTH_INTENSITY * MOUTH_TO_WORLD_Y * ratio, 0))
            for time, y in poses]


def animation_field(identifier):
    return "animation" if identifier == 1 else f"animation_{identifier}"


def remove_talking(root):
    talking = {entry["id"] for entry in root.get("listAnim", []) if entry["name"].startswith("talking")}
    for node in walk(root):
        for identifier in talking:
            node.pop(animation_field(identifier), None)
    root["listAnim"] = [entry for entry in root.get("listAnim", []) if entry["id"] not in talking]


def add_animations(root, styles, generic_name=False):
    reparent_head(root)
    reparent_character(root)
    upper = reparent_upper_body(root)
    facial_rigs = facial_hair_rigs(root)
    remove_talking(root)
    first_id = max((entry["id"] for entry in root.get("listAnim", [])), default=0) + 1
    for offset, style in enumerate(styles):
        identifier = first_id + offset
        field = animation_field(identifier)
        profile = PERSONALITIES[style]
        targets = {
            "head": find(root, "Head Rig"),
            "left_arm": find(root, "left_arm"), "right_arm": find(root, "right_arm"),
        }
        for target, poses in profile.items():
            if target in targets:
                targets[target][field] = track(targets[target], poses)
            elif target == "torso":
                upper[field] = track(upper, [(pose[0], pose[1] if len(pose) > 1 else (0, 0, 0)) for pose in poses])
                torso = find(root, "Torso")
                torso[field] = track(torso, [(pose[0], (0, 0, 0), pose[2] if len(pose) > 2 else (1, 1, 1)) for pose in poses])
        find(root, "Group 19")[field] = mouth_track(find(root, "Group 19"), profile["mouth"])
        for upper, jaw in facial_rigs:
            upper[field] = facial_hair_track(upper, profile["mouth"], .25)
            if jaw:
                jaw[field] = facial_hair_track(jaw, profile["mouth"], 1)
        find(root, "Group 17")[field] = brow_track(find(root, "Group 17"), profile["brow"], 1)
        find(root, "Group 18")[field] = brow_track(find(root, "Group 18"), profile["brow"], -1)
        for eye in (find(root, "left_eye"), find(root, "right_eye")):
            eye[field] = eye_track(eye, profile["duration"], profile["blinks"], profile["gaze"])
        root.setdefault("listAnim", []).append({
            "id": identifier, "name": "talking" if generic_name else f"talking_{style}",
        })
    root["talkingAnimations"] = list(styles)
    return root


def main():
    source = {name: load(EXAMPLE_DIR / f"villager_example_{name}.bdengine")
              for name in set(SHOWCASES.values())}
    styles = tuple(PERSONALITIES)
    for path in sorted(EXAMPLE_DIR.glob("villager_example_*.bdengine")):
        root = add_animations(load(path), styles)
        write(root, path)
        print(f"Added {len(styles)} talking animations to {path.name}")
    for style, example in SHOWCASES.items():
        root = copy.deepcopy(source[example])
        clear_animations(root)
        root["listAnim"] = []
        root.pop("waitingAnimations", None)
        add_animations(root, (style,), generic_name=True)
        root["name"] = f"Villager Talking - {style}"
        write(root, ANIMATION_DIR / f"villager_talking_{style}.bdengine")
        print(f"Created villager_talking_{style}.bdengine")


if __name__ == "__main__":
    main()
