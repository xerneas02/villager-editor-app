"""Add reusable personality-driven in-place walking cycles to villagers."""

import copy
from pathlib import Path

from generate_villager_accessories import walk
from generate_villager_clothing import find
from generate_villager_waiting_animations import (
    EXAMPLE_DIR, clear_animations, frame, reparent_character, reparent_head, reparent_upper_body, write,
)
from preview_bdengine import load


ROOT = Path(__file__).resolve().parent.parent
ANIMATION_DIR = ROOT / "bdengine" / "characters" / "villagers" / "animations" / "walking"
TICKS_PER_SECOND = 20
DEFAULT_SPEEDUP = 1.2
REFERENCE_LEG_LENGTH = .52

PROFILES = {
    "neutral": dict(duration=24, speed=1.00, stride=25, arm=21, knee=34, ankle=10, elbow=11, wrist=3, bob=.040, sway=1.5, lean=.5, head=1, twist=3),
    "brisk": dict(duration=20, speed=1.45, stride=36, arm=31, knee=46, ankle=14, elbow=20, wrist=5, bob=.065, sway=2.4, lean=2, head=2, twist=4),
    "heavy": dict(duration=32, speed=.85, stride=22, arm=17, knee=31, ankle=9, elbow=16, wrist=4, bob=.075, sway=3.6, lean=2, head=2, twist=2.5),
    "cautious": dict(duration=36, speed=.65, stride=16, arm=11, knee=26, ankle=8, elbow=10, wrist=3, bob=.030, sway=1.8, lean=2.5, head=4, twist=2),
    "elder": dict(duration=40, speed=.50, stride=13, arm=9, knee=23, ankle=7, elbow=14, wrist=4, bob=.025, sway=3.2, lean=3, head=3, twist=1.5),
    "proud": dict(duration=32, speed=.90, stride=19, arm=8, knee=28, ankle=8, elbow=6, wrist=2, bob=.032, sway=1.2, lean=0, head=1, twist=2.5),
    "monster": dict(duration=28, speed=1.05, stride=27, arm=15, knee=38, ankle=12, elbow=24, wrist=6, bob=.060, sway=4.0, lean=7, head=5, twist=5),
    "villain": dict(duration=28, speed=1.00, stride=25, arm=11, knee=34, ankle=10, elbow=14, wrist=4, bob=.035, sway=1.6, lean=1, head=2, twist=6),
    "idiot": dict(duration=24, speed=1.20, stride=31, arm=35, knee=48, ankle=15, elbow=25, wrist=7, bob=.085, sway=5.0, lean=-1, head=6, twist=7),
    "barbarian": dict(duration=24, speed=1.35, stride=34, arm=28, knee=46, ankle=14, elbow=22, wrist=6, bob=.080, sway=4.8, lean=3, head=3, twist=6),
}

SHOWCASES = {
    "neutral": "village_artisan", "brisk": "forest_huntress",
    "heavy": "village_blacksmith", "cautious": "road_traveler",
    "elder": "elder_farmer", "proud": "noblewoman",
    "monster": "village_blacksmith", "villain": "town_guard",
    "idiot": "road_traveler", "barbarian": "village_blacksmith",
}


def animation_field(identifier):
    return "animation" if identifier == 1 else f"animation_{identifier}"


def remove_walking(root):
    walking = {entry["id"] for entry in root.get("listAnim", []) if entry["name"].startswith("walking")}
    for node in walk(root):
        for identifier in walking:
            node.pop(animation_field(identifier), None)
    root["listAnim"] = [entry for entry in root.get("listAnim", []) if entry["id"] not in walking]


def cycle_frames(node, duration, rotations, heights=None, sides=None):
    assert duration % 4 == 0
    quarter = duration // 4
    times = (0, quarter, quarter * 2, quarter * 3, duration)
    heights = heights or (0, 0, 0, 0, 0)
    sides = sides or (0, 0, 0, 0, 0)
    return [frame(node, time, rotation=rotation, position=(side, height, 0))
            for time, rotation, height, side in zip(times, rotations, heights, sides)]


def cycle_duration(profile, movement_speed=None, leg_length=REFERENCE_LEG_LENGTH):
    natural_duration = profile["duration"] / DEFAULT_SPEEDUP
    if movement_speed is not None:
        cycle_distance = profile["speed"] * natural_duration / TICKS_PER_SECOND
        natural_duration = cycle_distance * leg_length / REFERENCE_LEG_LENGTH / movement_speed * TICKS_PER_SECOND
    return max(4, min(400, round(natural_duration / 4) * 4))


def add_animations(root, styles, generic_name=False, movement_speed=None, leg_length=REFERENCE_LEG_LENGTH):
    reparent_head(root)
    character = reparent_character(root)
    upper = reparent_upper_body(root)
    remove_walking(root)
    first_id = max((entry["id"] for entry in root.get("listAnim", [])), default=0) + 1
    controller = {}
    for offset, style in enumerate(styles):
        profile = PROFILES[style]
        duration = cycle_duration(profile, movement_speed, leg_length)
        stride, arm = profile["stride"], profile["arm"]
        sway, lean, head = profile["sway"], profile["lean"], profile["head"]
        twist = profile["twist"]
        identifier = first_id + offset
        field = animation_field(identifier)

        character[field] = cycle_frames(
            character, duration,
            ((0, 0, 0),) * 5,
            (0, profile["bob"], 0, profile["bob"], 0),
            (sway / 150, 0, -sway / 150, 0, sway / 150),
        )
        upper[field] = cycle_frames(
            upper, duration,
            ((-lean, twist, sway * .2), (-lean, 0, 0), (-lean, -twist, -sway * .2), (-lean, 0, 0), (-lean, twist, sway * .2)),
        )
        find(root, "Head Rig")[field] = cycle_frames(
            find(root, "Head Rig"), duration,
            ((lean * .35, -head, -sway * .45), (lean * .35, 0, 0), (lean * .35, head, sway * .45), (lean * .35, 0, 0), (lean * .35, -head, -sway * .45)),
        )
        find(root, "left_leg")[field] = cycle_frames(
            find(root, "left_leg"), duration,
            ((stride, 0, 0), (0, 0, 0), (-stride, 0, 0), (0, 0, 0), (stride, 0, 0)),
        )
        find(root, "right_leg")[field] = cycle_frames(
            find(root, "right_leg"), duration,
            ((-stride, 0, 0), (0, 0, 0), (stride, 0, 0), (0, 0, 0), (-stride, 0, 0)),
        )
        find(root, "left_arm")[field] = cycle_frames(
            find(root, "left_arm"), duration,
            ((-arm, 0, -2), (0, 0, 0), (arm, 0, 2), (0, 0, 0), (-arm, 0, -2)),
        )
        find(root, "right_arm")[field] = cycle_frames(
            find(root, "right_arm"), duration,
            ((arm, 0, 2), (0, 0, 0), (-arm, 0, -2), (0, 0, 0), (arm, 0, 2)),
        )
        knee, ankle, elbow, wrist = (profile[key] for key in ("knee", "ankle", "elbow", "wrist"))
        joint_cycles = {
            "left_knee": (-4, -8, -18, -knee, -4),
            "right_knee": (-18, -knee, -4, -8, -18),
            "left_ankle": (ankle, 0, -ankle * .8, ankle * .5, ankle),
            "right_ankle": (-ankle * .8, ankle * .5, ankle, 0, -ankle * .8),
            "left_elbow": (elbow * .65, elbow * .8, elbow, elbow * .8, elbow * .65),
            "right_elbow": (elbow, elbow * .8, elbow * .65, elbow * .8, elbow),
            "left_wrist": (-wrist, 0, wrist, 0, -wrist),
            "right_wrist": (wrist, 0, -wrist, 0, wrist),
        }
        for joint, rotations in joint_cycles.items():
            node = find(root, joint)
            node[field] = cycle_frames(node, duration, tuple((rotation, 0, 0) for rotation in rotations))
        name = "walking" if generic_name else f"walking_{style}"
        root.setdefault("listAnim", []).append({"id": identifier, "name": name})
        speed = movement_speed or profile["speed"] * leg_length / REFERENCE_LEG_LENGTH
        controller[name] = {
            "movementSpeed": round(speed, 3), "unit": "blocks_per_second",
            "cycleDurationTicks": duration, "playbackMultiplier": "actual_speed / movementSpeed",
        }
    root["walkingAnimations"] = list(styles)
    root["walkingController"] = {"ticksPerSecond": TICKS_PER_SECOND, "animations": controller}
    return root


def main():
    source = {name: load(EXAMPLE_DIR / f"villager_example_{name}.bdengine")
              for name in set(SHOWCASES.values())}
    styles = tuple(PROFILES)
    for path in sorted(EXAMPLE_DIR.glob("villager_example_*.bdengine")):
        root = add_animations(load(path), styles)
        write(root, path)
        print(f"Added {len(styles)} walking animations to {path.name}")
    for style, example in SHOWCASES.items():
        root = copy.deepcopy(source[example])
        clear_animations(root)
        root["listAnim"] = []
        root.pop("waitingAnimations", None)
        root.pop("talkingAnimations", None)
        add_animations(root, (style,), generic_name=True)
        root["name"] = f"Villager Walking - {style}"
        write(root, ANIMATION_DIR / f"villager_walking_{style}.bdengine")
        print(f"Created villager_walking_{style}.bdengine")


if __name__ == "__main__":
    main()
