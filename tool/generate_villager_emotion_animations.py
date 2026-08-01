"""Add reusable facial and body emotion animations to modular villagers."""

import copy
from pathlib import Path

from generate_villager_accessories import walk
from generate_villager_clothing import find
from generate_villager_talking_animations import (
    animation_field, facial_hair_rigs, facial_hair_track, mouth_track,
)
from generate_villager_waiting_animations import (
    EXAMPLE_DIR, JOINTS, clear_animations, frame, reparent_character, reparent_head, reparent_upper_body, track, write,
)
from preview_bdengine import load


ROOT = Path(__file__).resolve().parent.parent
ANIMATION_DIR = ROOT / "bdengine" / "characters" / "villagers" / "animations" / "emotions"

EMOTIONS = {
    "anger": {
        "duration": 32,
        "head": [(0,), (5, (-3, 0, 0)), (12, (-5, -3, 0)), (20, (-5, 3, 0)), (27, (-3, 0, 0)), (32,)],
        "body": [(0,), (5, (-6, 0, 0), (1.04, 1.02, 1)), (27, (-6, 0, 0), (1.04, 1.02, 1)), (32,)],
        "left_arm": [(0,), (5, (-25, 0, -12)), (12, (-31, 0, -14)), (27, (-25, 0, -12)), (32,)],
        "right_arm": [(0,), (5, (-25, 0, 12)), (20, (-31, 0, 14)), (27, (-25, 0, 12)), (32,)],
        "mouth": ((0, 0), (5, -.08), (11, -.16), (16, -.05), (22, -.14), (27, -.08), (32, 0)),
        "brows": ((0, 0, 0), (5, -15, -.035), (27, -15, -.035), (32, 0, 0)),
        "eyes": ((0, 1, 0, 0, 0), (5, .62, 0, -.015, .045), (12, .55, .018, -.015, .055), (20, .55, -.018, -.015, .055), (27, .62, 0, -.015, .045), (32, 1, 0, 0, 0)),
    },
    "joy": {
        "duration": 36,
        "head": [(0,), (5, (-4, -5, -2)), (11, (2, 5, 2)), (18, (-3, -4, -2)), (25, (2, 4, 2)), (31, (-2, 0, 0)), (36,)],
        "body": [(0,), (6, (-4, 0, -3), (1.045, 1.04, 1)), (12, (2, 0, 3)),
                 (20, (-4, 0, -3), (1.045, 1.04, 1)), (28, (2, 0, 3)), (36,)],
        "left_arm": [(0,), (6, (-42, 0, -28)), (12, (-58, 0, -34)), (20, (-38, 0, -25)),
                     (28, (-54, 0, -32)), (36,)],
        "right_arm": [(0,), (6, (-42, 0, 28)), (12, (-58, 0, 34)), (20, (-38, 0, 25)),
                      (28, (-54, 0, 32)), (36,)],
        "mouth": ((0, 0), (5, -.18), (10, -.25), (15, -.12), (21, -.26), (27, -.15), (32, -.20), (36, 0)),
        "brows": ((0, 0, 0), (5, 5, .025), (31, 5, .025), (36, 0, 0)),
        "eyes": ((0, 1, 0, 0, 0), (5, .48, 0, .01, 0), (10, .32, -.018, .01, 0), (18, .42, .018, .01, 0), (27, .32, 0, .01, 0), (32, .55, 0, 0, 0), (36, 1, 0, 0, 0)),
    },
    "sadness": {
        "duration": 44,
        "head": [(0,), (8, (8, -3, -2)), (18, (11, 2, 2)), (34, (9, -2, -2)), (40, (6, 0, 0)), (44,)],
        "body": [(0,), (8, (9, 0, 0), (.96, .98, 1)), (36, (9, 0, 0), (.96, .98, 1)), (44,)],
        "left_arm": [(0,), (8, (12, 0, -11)), (18, (16, 0, -13)), (36, (12, 0, -11)), (44,)],
        "right_arm": [(0,), (8, (18, 0, 9)), (18, (21, 0, 11)), (36, (18, 0, 9)), (44,)],
        "mouth": ((0, 0), (10, -.06), (20, -.10), (30, -.05), (38, -.08), (44, 0)),
        "brows": ((0, 0, 0), (8, 13, .035), (36, 13, .035), (44, 0, 0)),
        "eyes": ((0, 1, 0, 0, 0), (8, .82, 0, -.055, .015), (18, .75, -.012, -.065, .015), (28, .75, .012, -.065, .015), (36, .82, 0, -.05, .015), (44, 1, 0, 0, 0)),
    },
    "fear": {
        "duration": 32,
        "head": [(0,), (4, (-7, -5, -2)), (9, (-9, 6, 2)), (15, (-7, -6, -2)), (22, (-9, 5, 2)), (28, (-6, 0, 0)), (32,)],
        "body": [(0,), (4, (-10, 0, 3), (.97, 1.02, 1)), (15, (-12, 0, -3), (.97, 1.02, 1)),
                 (28, (-10, 0, 2), (.97, 1.02, 1)), (32,)],
        "left_arm": [(0,), (4, (-48, 0, -12)), (9, (-56, 0, -8)), (15, (-50, 0, -15)),
                     (22, (-58, 0, -9)), (28, (-48, 0, -12)), (32,)],
        "right_arm": [(0,), (4, (-52, 0, 12)), (9, (-46, 0, 16)), (15, (-58, 0, 8)),
                      (22, (-48, 0, 15)), (28, (-52, 0, 12)), (32,)],
        "mouth": ((0, 0), (4, -.18), (10, -.24), (16, -.16), (22, -.25), (28, -.18), (32, 0)),
        "brows": ((0, 0, 0), (4, 14, .06), (28, 14, .06), (32, 0, 0)),
        "eyes": ((0, 1, 0, 0, 0), (4, 1.14, -.035, .015, 0), (8, 1.14, .04, .015, 0), (13, 1.14, -.04, .015, 0), (19, 1.14, .035, .015, 0), (25, 1.14, 0, .015, 0), (28, 1.08, 0, .01, 0), (32, 1, 0, 0, 0)),
    },
    "surprise": {
        "duration": 28,
        "head": [(0,), (3, (-10, 0, 0)), (7, (-7, -3, -1)), (14, (-9, 3, 1)), (23, (-7, 0, 0)), (28,)],
        "body": [(0,), (3, (-9, 0, 0), (1.05, 1.04, 1)), (7, (-6, 0, 0), (1.03, 1.02, 1)),
                 (23, (-5, 0, 0), (1.02, 1.01, 1)), (28,)],
        "left_arm": [(0,), (3, (-42, 0, -31)), (7, (-34, 0, -27)), (22, (-30, 0, -24)), (28,)],
        "right_arm": [(0,), (3, (-42, 0, 31)), (7, (-34, 0, 27)), (22, (-30, 0, 24)), (28,)],
        "mouth": ((0, 0), (3, -.32), (21, -.32), (25, -.18), (28, 0)),
        "brows": ((0, 0, 0), (3, 3, .085), (23, 3, .085), (28, 0, 0)),
        "eyes": ((0, 1, 0, 0, 0), (3, 1.16, 0, .02, .012), (9, 1.14, -.012, .02, .012), (17, 1.14, .012, .02, .012), (23, 1.12, 0, .015, .01), (28, 1, 0, 0, 0)),
    },
}

POSTURES = {
    "anger": {
        "left_leg": [(0,), (5, (0, 0, -5)), (27, (0, 0, -5)), (32,)],
        "right_leg": [(0,), (5, (0, 0, 5)), (27, (0, 0, 5)), (32,)],
        "left_knee": [(0,), (5, (18, 0, 0)), (12, (24, 0, 0)), (27, (18, 0, 0)), (32,)],
        "right_knee": [(0,), (5, (24, 0, 0)), (20, (18, 0, 0)), (27, (24, 0, 0)), (32,)],
        "left_ankle": [(0,), (5, (-9, 0, 0)), (27, (-9, 0, 0)), (32,)],
        "right_ankle": [(0,), (5, (-12, 0, 0)), (27, (-12, 0, 0)), (32,)],
        "left_elbow": [(0,), (5, (62, 0, 0)), (12, (72, 0, 0)), (27, (62, 0, 0)), (32,)],
        "right_elbow": [(0,), (5, (68, 0, 0)), (20, (76, 0, 0)), (27, (68, 0, 0)), (32,)],
        "left_wrist": [(0,), (5, (18, -7, -12)), (27, (18, -7, -12)), (32,)],
        "right_wrist": [(0,), (5, (20, 7, 12)), (27, (20, 7, 12)), (32,)],
    },
    "joy": {
        "left_leg": [(0,), (6, (0, 0, -4)), (12, (-4, 0, -6)), (20, (2, 0, -4)), (28, (-3, 0, -6)), (36,)],
        "right_leg": [(0,), (6, (0, 0, 4)), (12, (-3, 0, 6)), (20, (2, 0, 4)), (28, (-4, 0, 6)), (36,)],
        "left_knee": [(0,), (6, (22, 0, 0)), (12, (5, 0, 0)), (20, (18, 0, 0)), (28, (6, 0, 0)), (36,)],
        "right_knee": [(0,), (6, (18, 0, 0)), (12, (6, 0, 0)), (20, (22, 0, 0)), (28, (5, 0, 0)), (36,)],
        "left_ankle": [(0,), (6, (-11, 0, 0)), (12, (4, 0, 0)), (20, (-9, 0, 0)), (28, (4, 0, 0)), (36,)],
        "right_ankle": [(0,), (6, (-9, 0, 0)), (12, (4, 0, 0)), (20, (-11, 0, 0)), (28, (4, 0, 0)), (36,)],
        "left_elbow": [(0,), (6, (18, 0, 0)), (12, (28, 0, 0)), (20, (16, 0, 0)), (28, (26, 0, 0)), (36,)],
        "right_elbow": [(0,), (6, (22, 0, 0)), (12, (30, 0, 0)), (20, (18, 0, 0)), (28, (28, 0, 0)), (36,)],
        "left_wrist": [(0,), (6, (6, -5, -18)), (12, (10, -8, -22)), (28, (8, -6, -20)), (36,)],
        "right_wrist": [(0,), (6, (6, 5, 18)), (12, (10, 8, 22)), (28, (8, 6, 20)), (36,)],
    },
    "sadness": {
        "left_leg": [(0,), (8, (3, 0, -2)), (36, (3, 0, -2)), (44,)],
        "right_leg": [(0,), (8, (6, 0, 2)), (36, (6, 0, 2)), (44,)],
        "left_knee": [(0,), (8, (18, 0, 0)), (18, (22, 0, 0)), (36, (18, 0, 0)), (44,)],
        "right_knee": [(0,), (8, (12, 0, 0)), (18, (16, 0, 0)), (36, (12, 0, 0)), (44,)],
        "left_ankle": [(0,), (8, (-9, 0, 0)), (36, (-9, 0, 0)), (44,)],
        "right_ankle": [(0,), (8, (-6, 0, 0)), (36, (-6, 0, 0)), (44,)],
        "left_elbow": [(0,), (8, (52, 0, 0)), (18, (60, 0, 0)), (36, (52, 0, 0)), (44,)],
        "right_elbow": [(0,), (8, (58, 0, 0)), (18, (66, 0, 0)), (36, (58, 0, 0)), (44,)],
        "left_wrist": [(0,), (8, (16, 5, 9)), (18, (20, 7, 12)), (36, (16, 5, 9)), (44,)],
        "right_wrist": [(0,), (8, (18, -5, -9)), (18, (22, -7, -12)), (36, (18, -5, -9)), (44,)],
    },
    "fear": {
        "left_leg": [(0,), (4, (8, 0, -3)), (15, (12, 0, -5)), (28, (8, 0, -3)), (32,)],
        "right_leg": [(0,), (4, (-12, 0, 4)), (15, (-16, 0, 6)), (28, (-12, 0, 4)), (32,)],
        "left_knee": [(0,), (4, (28, 0, 0)), (9, (38, 0, 0)), (15, (30, 0, 0)), (22, (40, 0, 0)), (28, (28, 0, 0)), (32,)],
        "right_knee": [(0,), (4, (38, 0, 0)), (9, (28, 0, 0)), (15, (42, 0, 0)), (22, (30, 0, 0)), (28, (38, 0, 0)), (32,)],
        "left_ankle": [(0,), (4, (-14, 0, 0)), (15, (-17, 0, 0)), (28, (-14, 0, 0)), (32,)],
        "right_ankle": [(0,), (4, (-18, 0, 0)), (15, (-20, 0, 0)), (28, (-18, 0, 0)), (32,)],
        "left_elbow": [(0,), (4, (78, 0, 0)), (9, (88, 0, 0)), (15, (80, 0, 0)), (22, (90, 0, 0)), (28, (78, 0, 0)), (32,)],
        "right_elbow": [(0,), (4, (84, 0, 0)), (9, (76, 0, 0)), (15, (92, 0, 0)), (22, (80, 0, 0)), (28, (84, 0, 0)), (32,)],
        "left_wrist": [(0,), (4, (24, 8, 15)), (15, (30, 10, 18)), (28, (24, 8, 15)), (32,)],
        "right_wrist": [(0,), (4, (26, -8, -15)), (15, (32, -10, -18)), (28, (26, -8, -15)), (32,)],
    },
    "surprise": {
        "left_leg": [(0,), (3, (-4, 0, -4)), (7, (1, 0, -3)), (23, (1, 0, -3)), (28,)],
        "right_leg": [(0,), (3, (-4, 0, 4)), (7, (1, 0, 3)), (23, (1, 0, 3)), (28,)],
        "left_knee": [(0,), (3, (27, 0, 0)), (7, (16, 0, 0)), (23, (14, 0, 0)), (28,)],
        "right_knee": [(0,), (3, (27, 0, 0)), (7, (16, 0, 0)), (23, (14, 0, 0)), (28,)],
        "left_ankle": [(0,), (3, (-14, 0, 0)), (7, (-7, 0, 0)), (23, (-6, 0, 0)), (28,)],
        "right_ankle": [(0,), (3, (-14, 0, 0)), (7, (-7, 0, 0)), (23, (-6, 0, 0)), (28,)],
        "left_elbow": [(0,), (3, (30, 0, 0)), (7, (38, 0, 0)), (22, (34, 0, 0)), (28,)],
        "right_elbow": [(0,), (3, (30, 0, 0)), (7, (38, 0, 0)), (22, (34, 0, 0)), (28,)],
        "left_wrist": [(0,), (3, (5, -10, -24)), (7, (10, -7, -20)), (22, (8, -6, -18)), (28,)],
        "right_wrist": [(0,), (3, (5, 10, 24)), (7, (10, 7, 20)), (22, (8, 6, 18)), (28,)],
    },
}

SHOWCASES = {
    "anger": "town_guard", "joy": "village_artisan", "sadness": "young_cleric",
    "fear": "road_traveler", "surprise": "forest_huntress",
}


def brow_track(node, poses, sign):
    return [frame(node, time, rotation=(0, 0, sign * angle), position=(0, height, 0))
            for time, angle, height in poses]


def eye_track(node, poses, side):
    return [frame(node, time, scale=(1, height, 1),
                  position=(gaze + side * converge, vertical, 0))
            for time, height, gaze, vertical, converge in poses]


def remove_emotions(root):
    identifiers = {entry["id"] for entry in root.get("listAnim", [])
                   if entry["name"].startswith("emotion_")}
    for node in walk(root):
        for identifier in identifiers:
            node.pop(animation_field(identifier), None)
    root["listAnim"] = [entry for entry in root.get("listAnim", []) if entry["id"] not in identifiers]


def add_animations(root, styles, generic_name=False):
    reparent_head(root)
    reparent_character(root)
    upper = reparent_upper_body(root)
    facial_rigs = facial_hair_rigs(root)
    remove_emotions(root)
    first_id = max((entry["id"] for entry in root.get("listAnim", [])), default=0) + 1
    for offset, style in enumerate(styles):
        profile = EMOTIONS[style]
        identifier = first_id + offset
        field = animation_field(identifier)
        targets = ("head", "left_arm", "right_arm", "left_leg", "right_leg", *JOINTS)
        for name in targets:
            poses = profile[name] if name in profile else POSTURES[style][name]
            find(root, "Head Rig" if name == "head" else name)[field] = track(
                find(root, "Head Rig" if name == "head" else name), poses)
        upper[field] = track(upper, profile["body"])
        mouth = find(root, "Group 19")
        mouth[field] = mouth_track(mouth, profile["mouth"])
        for upper, jaw in facial_rigs:
            upper[field] = facial_hair_track(upper, profile["mouth"], .25)
            if jaw:
                jaw[field] = facial_hair_track(jaw, profile["mouth"], 1)
        find(root, "Group 17")[field] = brow_track(find(root, "Group 17"), profile["brows"], 1)
        find(root, "Group 18")[field] = brow_track(find(root, "Group 18"), profile["brows"], -1)
        find(root, "left_eye")[field] = eye_track(find(root, "left_eye"), profile["eyes"], 1)
        find(root, "right_eye")[field] = eye_track(find(root, "right_eye"), profile["eyes"], -1)
        root.setdefault("listAnim", []).append({
            "id": identifier, "name": "emotion" if generic_name else f"emotion_{style}",
        })
    root["emotionAnimations"] = list(styles)
    return root


def main():
    source = {name: load(EXAMPLE_DIR / f"villager_example_{name}.bdengine")
              for name in set(SHOWCASES.values())}
    styles = tuple(EMOTIONS)
    for path in sorted(EXAMPLE_DIR.glob("villager_example_*.bdengine")):
        write(add_animations(load(path), styles), path)
        print(f"Added {len(styles)} emotion animations to {path.name}")
    for style, example in SHOWCASES.items():
        root = copy.deepcopy(source[example])
        clear_animations(root)
        root["listAnim"] = []
        for key in ("waitingAnimations", "talkingAnimations", "walkingAnimations"):
            root.pop(key, None)
        add_animations(root, (style,), generic_name=True)
        root["name"] = f"Villager Emotion - {style}"
        write(root, ANIMATION_DIR / f"villager_emotion_{style}.bdengine")
        print(f"Created villager_emotion_{style}.bdengine")


if __name__ == "__main__":
    main()
