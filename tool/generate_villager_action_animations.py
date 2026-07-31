"""Generate the reusable villager gesture, reaction, activity and profession library."""

import copy
from pathlib import Path

from generate_villager_accessories import walk
from generate_villager_clothing import find
from generate_villager_emotion_animations import EMOTIONS, brow_track, eye_track
from generate_villager_talking_animations import (
    animation_field, facial_hair_rigs, facial_hair_track, mouth_track,
)
from generate_villager_waiting_animations import (
    EXAMPLE_DIR, clear_animations, frame, reparent_character, reparent_head, reparent_upper_body, write,
)
from preview_bdengine import load


ROOT = Path(__file__).resolve().parent.parent
ANIMATION_ROOT = ROOT / "bdengine" / "characters" / "villagers" / "animations"

ACTIONS = {
    "gestures": {
        "wave": {"duration": 32, "head": [(0,), (6, (0, 8, 2)), (26, (0, 8, 2)), (32,)],
                 "right_arm": [(0,), (5, (-125, 0, 18)), (10, (-125, -18, 18)), (15, (-125, 18, 18)), (20, (-125, -18, 18)), (26, (-125, 12, 18)), (32,)]},
        "yes": {"duration": 28, "head": [(0,), (5, (12, 0, 0)), (9, (-5, 0, 0)), (14, (12, 0, 0)), (19, (-4, 0, 0)), (24, (7, 0, 0)), (28,)]},
        "no": {"duration": 30, "head": [(0,), (5, (0, -16, 0)), (10, (0, 16, 0)), (15, (0, -17, 0)), (20, (0, 16, 0)), (25, (0, -9, 0)), (30,)]},
        "point": {"duration": 36, "head": [(0,), (7, (0, -12, 0)), (29, (0, -12, 0)), (36,)],
                  "right_arm": [(0,), (7, (-82, -12, 7)), (29, (-82, -12, 7)), (36,)]},
        "shrug": {"duration": 34, "head": [(0,), (7, (0, 0, -7)), (25, (0, 0, -7)), (34,)],
                   "left_arm": [(0,), (7, (-28, 0, -34)), (25, (-28, 0, -34)), (34,)],
                   "right_arm": [(0,), (7, (-28, 0, 34)), (25, (-28, 0, 34)), (34,)]},
        "laugh": {"duration": 40, "face": "joy", "head": [(0,), (6, (-7, -4, -2)), (13, (7, 4, 2)), (21, (-8, -3, -2)), (29, (6, 3, 2)), (35, (-4, 0, 0)), (40,)],
                  "body": [(0,), (8, (-4, 0, -3)), (16, (3, 0, 3)), (24, (-4, 0, -3)), (32, (3, 0, 3)), (40,)],
                  "left_arm": [(0,), (7, (-13, 0, -14)), (33, (-13, 0, -14)), (40,)],
                  "right_arm": [(0,), (7, (-13, 0, 14)), (33, (-13, 0, 14)), (40,)]},
    },
    "reactions": {
        "hurt": {"duration": 20, "face": "fear", "body": [(0,), (3, (-12, 0, -8)), (7, (7, 0, 5)), (13, (-3, 0, -2)), (20,)],
                 "head": [(0,), (3, (-10, 8, 5)), (8, (7, -5, -3)), (14, (-3, 2, 1)), (20,)],
                 "left_arm": [(0,), (3, (-34, 0, -24)), (10, (12, 0, 8)), (20,)], "right_arm": [(0,), (3, (-28, 0, 22)), (10, (10, 0, -7)), (20,)]},
        "stunned": {"duration": 38, "face": "surprise", "head": [(0,), (5, (-8, -12, -8)), (11, (5, 13, 8)), (18, (-4, -10, -7)), (25, (3, 8, 5)), (32, (-2, -4, -3)), (38,)],
                    "body": [(0,), (6, (0, 0, -5)), (14, (0, 0, 5)), (23, (0, 0, -4)), (31, (0, 0, 3)), (38,)]},
        "suspicious": {"duration": 42, "face": "anger", "head": [(0,), (8, (1, -14, -6)), (20, (3, -18, -7)), (34, (1, -12, -5)), (42,)],
                       "body": [(0,), (8, (0, 0, -2)), (34, (0, 0, -2)), (42,)],
                       "left_arm": [(0,), (8, (-8, 0, -5)), (34, (-8, 0, -5)), (42,)]},
        "alert": {"duration": 30, "face": "surprise", "head": [(0,), (4, (-7, -15, -2)), (10, (-5, 16, 2)), (17, (-7, -8, -1)), (25, (-4, 0, 0)), (30,)],
                  "body": [(0,), (4, (-4, 0, 0)), (25, (-3, 0, 0)), (30,)],
                  "right_arm": [(0,), (5, (-25, 0, 12)), (25, (-25, 0, 12)), (30,)]},
        "cry": {"duration": 50, "face": "sadness", "head": [(0,), (8, (11, -3, -3)), (20, (14, 2, 2)), (36, (12, -2, -2)), (44, (8, 0, 0)), (50,)],
                "body": [(0,), (8, (7, 0, 0)), (42, (7, 0, 0)), (50,)],
                "left_arm": [(0,), (9, (-78, 0, -10)), (41, (-78, 0, -10)), (50,)],
                "right_arm": [(0,), (9, (-72, 0, 10)), (41, (-72, 0, 10)), (50,)]},
    },
    "locomotion": {
        "running": {"duration": 16, "body_motion": [(0, (5, 0, 1), (0, 0, 0)), (4, (5, 0, 0), (0, .085, 0)), (8, (5, 0, -1), (0, 0, 0)), (12, (5, 0, 0), (0, .085, 0)), (16, (5, 0, 1), (0, 0, 0))],
                    "left_leg": [(0, (48, 0, 0)), (4,), (8, (-48, 0, 0)), (12,), (16, (48, 0, 0))], "right_leg": [(0, (-48, 0, 0)), (4,), (8, (48, 0, 0)), (12,), (16, (-48, 0, 0))],
                    "left_arm": [(0, (-42, 0, -4)), (4,), (8, (42, 0, 4)), (12,), (16, (-42, 0, -4))], "right_arm": [(0, (42, 0, 4)), (4,), (8, (-42, 0, -4)), (12,), (16, (42, 0, 4))]},
        "sneaking": {"duration": 32, "body_motion": [(0, (9, 0, 1), (.012, -.08, 0)), (8, (9, 0, 0), (0, -.055, 0)), (16, (9, 0, -1), (-.012, -.08, 0)), (24, (9, 0, 0), (0, -.055, 0)), (32, (9, 0, 1), (.012, -.08, 0))],
                     "left_leg": [(0, (18, 0, 0)), (8,), (16, (-18, 0, 0)), (24,), (32, (18, 0, 0))], "right_leg": [(0, (-18, 0, 0)), (8,), (16, (18, 0, 0)), (24,), (32, (-18, 0, 0))],
                     "left_arm": [(0, (-12, 0, -4)), (16, (12, 0, 4)), (32, (-12, 0, -4))], "right_arm": [(0, (12, 0, 4)), (16, (-12, 0, -4)), (32, (12, 0, 4))]},
        "limping": {"duration": 40, "body_motion": [(0, (3, 0, 4), (.02, 0, 0)), (10, (5, 0, 1), (0, .045, 0)), (20, (3, 0, -2), (-.012, -.035, 0)), (30, (5, 0, 1), (0, .02, 0)), (40, (3, 0, 4), (.02, 0, 0))],
                    "left_leg": [(0, (12, 0, 0)), (10,), (20, (-8, 0, 0)), (30,), (40, (12, 0, 0))], "right_leg": [(0, (-7, 0, 0)), (10,), (20, (25, 0, 0)), (30,), (40, (-7, 0, 0))],
                    "left_arm": [(0, (-8, 0, -4)), (20, (7, 0, 3)), (40, (-8, 0, -4))], "right_arm": [(0, (5, 0, 2)), (20, (-5, 0, -2)), (40, (5, 0, 2))]},
        "carrying_walk": {"duration": 28, "body_motion": [(0, (3, 0, 1), (.01, 0, 0)), (7, (3, 0, 0), (0, .045, 0)), (14, (3, 0, -1), (-.01, 0, 0)), (21, (3, 0, 0), (0, .045, 0)), (28, (3, 0, 1), (.01, 0, 0))],
                          "left_leg": [(0, (22, 0, 0)), (7,), (14, (-22, 0, 0)), (21,), (28, (22, 0, 0))], "right_leg": [(0, (-22, 0, 0)), (7,), (14, (22, 0, 0)), (21,), (28, (-22, 0, 0))],
                          "left_arm": [(0, (-68, 0, -8)), (28, (-68, 0, -8))], "right_arm": [(0, (-68, 0, 8)), (28, (-68, 0, 8))]},
    },
    "daily": {
        "sit": {"duration": 52, "body_motion": [(0, (0, 0, 0), (0, 0, 0)), (12, (5, 0, 0), (0, -.34, .08)), (40, (5, 0, 0), (0, -.34, .08)), (52, (0, 0, 0), (0, 0, 0))],
                "left_leg": [(0,), (12, (-89, 0, -15)), (40, (-89, 0, -15)), (52,)], "right_leg": [(0,), (12, (-89, 0, 15)), (40, (-89, 0, 15)), (52,)],
                "left_arm": [(0,), (12, (18, 0, -5)), (40, (18, 0, -5)), (52,)], "right_arm": [(0,), (12, (18, 0, 5)), (40, (18, 0, 5)), (52,)]},
        "kneel": {"duration": 48, "upper_motion": True, "body_motion": [(0, (0, 0, 0), (0, 0, 0)), (12, (5, 0, 0), (.045, -.25, .04)), (36, (5, 0, 0), (.045, -.25, .04)), (48, (0, 0, 0), (0, 0, 0))],
                  "left_leg": [(0,), (12, (76, 0, 0)), (36, (76, 0, 0)), (48,)],
                  "right_leg": [(0,), (12, (76, 0, 0)), (36, (76, 0, 0)), (48,)],
                  "left_arm": [(0,), (12, (-30, 0, 0)), (36, (-25, 0, 0)), (48,)],
                  "right_arm": [(0,), (12, (-30, 0, 0)), (36, (-25, 0, 0)), (48,)],
                  "head": [(0,), (12, (9, 0, 0)), (36, (9, 0, 0)), (48,)]},
        "sleep": {"duration": 108, "body_motion": [(0, (0, 0, 0), (0, 0, 0)), (10, (-6, 0, 0), (0, 0, -.01)), (20, (-28, 0, 0), (0, .02, -.06)), (30, (-60, 0, 0), (0, .10, -.14)), (40, (-88, 0, 0), (0, .18, -.22)), (56, (-87, 0, 0), (0, .19, -.22)), (68, (-88, 0, 0), (0, .19, -.22)), (78, (-88, 0, 0), (0, .18, -.22)), (88, (-55, 0, 0), (0, .09, -.12)), (98, (-20, 0, 0), (0, .015, -.04)), (108, (0, 0, 0), (0, 0, 0))],
                  "head": [(0,), (20, (-4, 0, 0)), (40,), (56, (-2, 0, 0)), (68, (2, 0, 0)), (78,), (98, (-3, 0, 0)), (108,)],
                  "left_leg": [(0,), (20, (-70, 0, -3)), (30, (-88, 0, -5)), (40, (-8, 0, -3)), (78, (-8, 0, -3)), (88, (-72, 0, -4)), (98, (-45, 0, -2)), (108,)],
                  "right_leg": [(0,), (20, (-70, 0, 3)), (30, (-88, 0, 5)), (40, (-8, 0, 3)), (78, (-8, 0, 3)), (88, (-72, 0, 4)), (98, (-45, 0, 2)), (108,)],
                  "left_arm": [(0,), (18, (-35, 0, -12)), (30, (-55, 0, -20)), (40, (8, 0, -22)), (56, (6, 0, -24)), (68, (10, 0, -20)), (78, (8, 0, -22)), (90, (-34, 0, -14)), (108,)],
                  "right_arm": [(0,), (18, (-35, 0, 12)), (30, (-55, 0, 20)), (40, (8, 0, 22)), (56, (6, 0, 24)), (68, (10, 0, 20)), (78, (8, 0, 22)), (90, (-34, 0, 14)), (108,)],
                  "eyes": ((0, 1, 0, 0, 0), (38, 1, 0, 0, 0), (42, .025, 0, 0, 0), (78, .025, 0, 0, 0), (82, 1, 0, 0, 0), (108, 1, 0, 0, 0))},
        "eat": {"duration": 40, "head": [(0,), (8, (6, 0, 0)), (32, (6, 0, 0)), (40,)],
                 "right_arm": [(0,), (6, (-105, 0, 5)), (11, (-82, 0, 5)), (17, (-106, 0, 5)), (23, (-82, 0, 5)), (29, (-105, 0, 5)), (34, (-85, 0, 5)), (40,)]},
        "drink": {"duration": 42, "head": [(0,), (8, (-8, 0, 0)), (30, (-12, 0, 0)), (35, (-5, 0, 0)), (42,)],
                   "right_arm": [(0,), (7, (-118, 0, 7)), (31, (-118, 0, 7)), (36, (-85, 0, 4)), (42,)]},
        "pick_up": {"duration": 42, "upper_motion": True, "body_motion": [(0, (0, 0, 0), (0, 0, 0)), (10, (20, 0, 0), (0, -.06, .02)), (20, (38, 0, 0), (0, -.14, .08)), (28, (30, 0, 0), (0, -.11, .06)), (35, (12, 0, 0), (0, -.04, .02)), (42, (0, 0, 0), (0, 0, 0))],
                    "head": [(0,), (10, (-5, 0, 0)), (20, (-12, 0, 0)), (28, (-9, 0, 0)), (35, (-3, 0, 0)), (42,)],
                    "left_arm": [(0,), (10, (-38, 0, -6)), (20, (-72, 0, -8)), (28, (-58, 0, -6)), (35, (-32, 0, -4)), (42,)], "right_arm": [(0,), (10, (-38, 0, 6)), (20, (-72, 0, 8)), (28, (-58, 0, 6)), (35, (-32, 0, 4)), (42,)]},
        "put_down": {"duration": 42, "upper_motion": True, "body_motion": [(0, (0, 0, 0), (0, 0, 0)), (9, (16, 0, 0), (0, -.04, .02)), (20, (38, 0, 0), (0, -.14, .08)), (29, (30, 0, 0), (0, -.11, .06)), (36, (10, 0, 0), (0, -.03, .01)), (42, (0, 0, 0), (0, 0, 0))],
                     "head": [(0,), (9, (-4, 0, 0)), (20, (-12, 0, 0)), (29, (-9, 0, 0)), (36, (-3, 0, 0)), (42,)],
                     "left_arm": [(0, (-55, 0, -6)), (9, (-58, 0, -6)), (20, (-76, 0, -8)), (29, (-48, 0, -5)), (36, (-20, 0, -3)), (42,)], "right_arm": [(0, (-55, 0, 6)), (9, (-58, 0, 6)), (20, (-76, 0, 8)), (29, (-48, 0, 5)), (36, (-20, 0, 3)), (42,)]},
    },
    "professions": {
        "hoe": {"duration": 36, "body": [(0,), (7, (22, 0, 0)), (17, (38, 0, 0)), (27, (18, 0, 0)), (36,)],
                "left_arm": [(0,), (7, (-72, 0, -8)), (17, (-28, 0, -6)), (27, (-75, 0, -8)), (36,)], "right_arm": [(0,), (7, (-82, 0, 8)), (17, (-36, 0, 6)), (27, (-85, 0, 8)), (36,)]},
        "sow": {"duration": 40, "body": [(0,), (8, (18, 0, 0)), (32, (18, 0, 0)), (40,)],
                "right_arm": [(0,), (8, (-45, -15, 15)), (14, (-70, 24, 20)), (21, (-38, -18, 12)), (28, (-68, 22, 18)), (34, (-40, 0, 10)), (40,)]},
        "harvest": {"duration": 34, "body": [(0,), (6, (28, -8, 0)), (15, (36, 12, 0)), (24, (27, -10, 0)), (34,)],
                    "right_arm": [(0,), (6, (-62, -28, 12)), (15, (-78, 32, 16)), (24, (-60, -30, 12)), (34,)], "left_arm": [(0,), (7, (-38, 0, -7)), (27, (-38, 0, -7)), (34,)]},
        "hammer": {"duration": 30, "upper_motion": True, "body_motion": [(0, (0, 0, 0), (0, 0, 0)), (5, (-5, 0, 0), (0, 0, 0)), (12, (18, 0, 0), (0, 0, 0)), (19, (-5, 0, 0), (0, 0, 0)), (26, (18, 0, 0), (0, 0, 0)), (30, (0, 0, 0), (0, 0, 0))],
                   "head": [(0,), (5, (2, 0, 0)), (12, (-6, 0, 0)), (19, (2, 0, 0)), (26, (-6, 0, 0)), (30,)],
                   "right_arm": [(0,), (5, (-145, 0, 10)), (12, (-48, 0, 5)), (19, (-145, 0, 10)), (26, (-48, 0, 5)), (30,)], "left_arm": [(0,), (6, (-62, 0, -8)), (25, (-62, 0, -8)), (30,)]},
        "pray": {"duration": 52, "head": [(0,), (10, (13, 0, 0)), (42, (13, 0, 0)), (52,)],
                 "left_arm": [(0,), (10, (-86.97, -6.68, 29.62)), (42, (-78, -10, 38)), (52,)], "right_arm": [(0,), (10, (-86.93, 6.7, -29.58)), (42, (-78, 10, -38)), (52,)],
                 "eyes": ((0, 1, 0, 0, 0), (10, .0625, 0, 0, 0), (42, .0744, 0, 0, 0), (52, 1.0625, 0, 0, 0))},
        "shoot_bow": {"duration": 44, "head": [(0,), (8, (0, -12, 0)), (36, (0, -12, 0)), (44,)],
                       "body": [(0,), (8, (0, -18, 0)), (36, (0, -18, 0)), (44,)],
                       "left_arm": [(0,), (8, (-88, -8, -5)), (36, (-88, -8, -5)), (44,)], "right_arm": [(0,), (8, (-82, 40, 15)), (24, (-82, 55, 18)), (30, (-60, 5, 5)), (36, (-45, 0, 3)), (44,)]},
        "guard": {"duration": 56, "head": [(0,), (9, (0, -14, 0)), (20, (0, 12, 0)), (32, (0, 18, 0)), (44, (0, -10, 0)), (56,)],
                  "body": [(0,), (10, (0, 0, -2)), (28, (0, 0, 2)), (46, (0, 0, -2)), (56,)],
                  "right_arm": [(0,), (8, (-12, 0, 8)), (48, (-12, 0, 8)), (56,)]},
    },
}

SHOWCASES = {
    "gestures": "village_artisan", "reactions": "road_traveler",
    "locomotion": "elven_ranger", "daily": "elder_farmer", "professions": "village_blacksmith",
    "transitions": "young_cleric",
}

FACE_PEAKS = {
    "anger": (-15, -.035, .55, 0, -.015, .055, -.12),
    "joy": (5, .025, .35, 0, .01, 0, -.22),
    "sadness": (13, .035, .75, 0, -.065, .015, -.08),
    "fear": (14, .06, 1.14, .03, .015, 0, -.22),
    "surprise": (3, .085, 1.16, 0, .02, .012, -.32),
}


def body_motion_track(node, poses, rotate=True):
    return [frame(node, time, rotation=(-rotation[0], rotation[1], rotation[2]) if rotate else (0, 0, 0), position=position)
            for time, rotation, position in poses]


def pose_track(node, poses):
    result = []
    for pose in poses:
        rotation = pose[1] if len(pose) > 1 else (0, 0, 0)
        rotation = (-rotation[0], rotation[1], rotation[2])
        result.append(frame(node, pose[0], rotation=rotation))
    return result


def apply_face(root, field, face_name, duration, facial_rigs, transition=False):
    angle, brow_y, eye_y, gaze, eye_pos, converge, mouth_y = FACE_PEAKS[face_name]
    if transition:
        brow_poses = ((0, 0, 0), (duration, angle, brow_y))
        eye_poses = ((0, 1, 0, 0, 0), (duration, eye_y, gaze, eye_pos, converge))
        mouth_poses = ((0, 0), (duration, mouth_y))
    else:
        enter, leave = max(3, duration // 6), duration - max(4, duration // 6)
        brow_poses = ((0, 0, 0), (enter, angle, brow_y), (leave, angle, brow_y), (duration, 0, 0))
        eye_poses = ((0, 1, 0, 0, 0), (enter, eye_y, gaze, eye_pos, converge), (leave, eye_y, -gaze, eye_pos, converge), (duration, 1, 0, 0, 0))
        mouth_poses = ((0, 0), (enter, mouth_y), (leave, mouth_y), (duration, 0))
    find(root, "Group 17")[field] = brow_track(find(root, "Group 17"), brow_poses, 1)
    find(root, "Group 18")[field] = brow_track(find(root, "Group 18"), brow_poses, -1)
    find(root, "left_eye")[field] = eye_track(find(root, "left_eye"), eye_poses, 1)
    find(root, "right_eye")[field] = eye_track(find(root, "right_eye"), eye_poses, -1)
    find(root, "Group 19")[field] = mouth_track(find(root, "Group 19"), mouth_poses)
    for upper, jaw in facial_rigs:
        upper[field] = facial_hair_track(upper, mouth_poses, .25)
        if jaw:
            jaw[field] = facial_hair_track(jaw, mouth_poses, 1)


def specifications():
    result = [(category, name, profile) for category, actions in ACTIONS.items() for name, profile in actions.items()]
    for emotion in EMOTIONS:
        result.append(("transitions", f"to_{emotion}", {
            "duration": 12, "face": emotion, "transition": True,
            "head": [(0,), (12, EMOTIONS[emotion]["head"][1][1])],
        }))
    return result


def remove_actions(root):
    prefixes = tuple(f"{category.removesuffix('s')}_" for category in ACTIONS) + ("transition_",)
    identifiers = {entry["id"] for entry in root.get("listAnim", []) if entry["name"].startswith(prefixes)}
    for node in walk(root):
        for identifier in identifiers:
            node.pop(animation_field(identifier), None)
    root["listAnim"] = [entry for entry in root.get("listAnim", []) if entry["id"] not in identifiers]


def add_animations(root, specs, generic=False):
    reparent_head(root)
    character = reparent_character(root)
    upper = reparent_upper_body(root)
    facial_rigs = facial_hair_rigs(root)
    remove_actions(root)
    first_id = max((entry["id"] for entry in root.get("listAnim", [])), default=0) + 1
    targets = {"head": "Head Rig", "left_arm": "left_arm", "right_arm": "right_arm",
               "left_leg": "left_leg", "right_leg": "right_leg"}
    for offset, (category, name, profile) in enumerate(specs):
        field = animation_field(first_id + offset)
        for key, target_name in targets.items():
            if key in profile:
                node = find(root, target_name)
                node[field] = pose_track(node, profile[key])
        if "body" in profile:
            upper[field] = pose_track(upper, profile["body"])
        if "body_motion" in profile:
            if category == "locomotion" or profile.get("upper_motion"):
                character[field] = body_motion_track(character, profile["body_motion"], rotate=False)
                upper[field] = body_motion_track(upper, [
                    (time, rotation, (0, 0, 0)) for time, rotation, _ in profile["body_motion"]
                ])
                if category == "locomotion":
                    head = find(root, "Head Rig")
                    head[field] = body_motion_track(head, [
                        (time, (-rotation[0] * .35, 0, -rotation[2] * .35), (0, 0, 0))
                        for time, rotation, _ in profile["body_motion"]
                    ])
            else:
                character[field] = body_motion_track(character, profile["body_motion"])
        if "face" in profile:
            apply_face(root, field, profile["face"], profile["duration"], facial_rigs, profile.get("transition", False))
        elif "eyes" in profile:
            find(root, "left_eye")[field] = eye_track(find(root, "left_eye"), profile["eyes"], 1)
            find(root, "right_eye")[field] = eye_track(find(root, "right_eye"), profile["eyes"], -1)
        prefix = category.removesuffix("s")
        root.setdefault("listAnim", []).append({
            "id": first_id + offset, "name": name if generic else f"{prefix}_{name}",
        })
    root["actionAnimations"] = {
        category: [name for current, name, _ in specs if current == category]
        for category in dict.fromkeys(category for category, _, _ in specs)
    }
    return root


def main():
    specs = specifications()
    showcase_names = set(SHOWCASES.values())
    sources = {name: load(EXAMPLE_DIR / f"villager_example_{name}.bdengine") for name in showcase_names}
    for path in sorted(EXAMPLE_DIR.glob("villager_example_*.bdengine")):
        write(add_animations(load(path), specs), path)
        print(f"Added {len(specs)} action animations to {path.name}")
    for category, name, profile in specs:
        root = copy.deepcopy(sources[SHOWCASES[category]])
        clear_animations(root)
        root["listAnim"] = []
        for key in ("waitingAnimations", "talkingAnimations", "walkingAnimations", "emotionAnimations", "actionAnimations"):
            root.pop(key, None)
        add_animations(root, [(category, name, profile)], generic=True)
        root["name"] = f"Villager {category.removesuffix('s').title()} - {name}"
        folder = ANIMATION_ROOT / category
        write(root, folder / f"villager_{category.removesuffix('s')}_{name}.bdengine")
        print(f"Created {category}/{name}")


if __name__ == "__main__":
    main()
