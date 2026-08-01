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
    "neutral": dict(duration=24, speed=1.00, stride=25, arm=21, knee=34, ankle=10, elbow=13, wrist=3, bob=.040, sway=1.5, lean=.5, head=1, twist=3, arm_bias=0, arm_roll=2, asym=0, look=0),
    "brisk": dict(duration=20, speed=1.45, stride=40, arm=36, knee=52, ankle=16, elbow=24, wrist=6, bob=.075, sway=2.8, lean=4, head=2, twist=5, arm_bias=-3, arm_roll=4, asym=.08, look=-1),
    "heavy": dict(duration=32, speed=.85, stride=25, arm=19, knee=36, ankle=10, elbow=24, wrist=5, bob=.100, sway=5.5, lean=4, head=3, twist=3, arm_bias=5, arm_roll=8, asym=.12, look=2),
    "cautious": dict(duration=36, speed=.65, stride=14, arm=9, knee=29, ankle=8, elbow=27, wrist=5, bob=.025, sway=1.2, lean=6, head=8, twist=2, arm_bias=-15, arm_roll=3, asym=.18, look=5),
    "elder": dict(duration=40, speed=.50, stride=12, arm=7, knee=27, ankle=7, elbow=30, wrist=5, bob=.035, sway=4.5, lean=9, head=4, twist=1.5, arm_bias=-12, arm_roll=5, asym=.15, look=4),
    "proud": dict(duration=32, speed=.90, stride=22, arm=7, knee=30, ankle=8, elbow=10, wrist=2, bob=.025, sway=.8, lean=-3, head=1, twist=3, arm_bias=4, arm_roll=1, asym=0, look=-5),
    "monster": dict(duration=28, speed=1.05, stride=32, arm=18, knee=45, ankle=14, elbow=38, wrist=8, bob=.085, sway=6.5, lean=11, head=7, twist=8, arm_bias=-18, arm_roll=12, asym=.28, look=7),
    "villain": dict(duration=28, speed=1.00, stride=27, arm=10, knee=38, ankle=11, elbow=26, wrist=5, bob=.030, sway=1.2, lean=4, head=6, twist=9, arm_bias=-10, arm_roll=4, asym=.32, look=-2),
    "idiot": dict(duration=24, speed=1.20, stride=37, arm=44, knee=57, ankle=18, elbow=32, wrist=10, bob=.120, sway=8.0, lean=-4, head=10, twist=11, arm_bias=3, arm_roll=11, asym=.35, look=-6),
    "barbarian": dict(duration=24, speed=1.35, stride=39, arm=34, knee=53, ankle=17, elbow=34, wrist=8, bob=.105, sway=7.0, lean=7, head=4, twist=9, arm_bias=-8, arm_roll=10, asym=.18, look=2),
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
        arm_bias, arm_roll, asym = (profile[key] for key in ("arm_bias", "arm_roll", "asym"))
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
            (((lean * .35) + profile["look"], -head, -sway * .45),
             ((lean * .35) + profile["look"], 0, 0),
             ((lean * .35) + profile["look"], head, sway * .45),
             ((lean * .35) + profile["look"], 0, 0),
             ((lean * .35) + profile["look"], -head, -sway * .45)),
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
            ((-arm * (1 + asym) + arm_bias, 0, -arm_roll), (arm_bias, 0, 0),
             (arm * (1 + asym) + arm_bias, 0, arm_roll), (arm_bias, 0, 0),
             (-arm * (1 + asym) + arm_bias, 0, -arm_roll)),
        )
        find(root, "right_arm")[field] = cycle_frames(
            find(root, "right_arm"), duration,
            ((arm * (1 - asym) + arm_bias, 0, arm_roll), (arm_bias, 0, 0),
             (-arm * (1 - asym) + arm_bias, 0, -arm_roll), (arm_bias, 0, 0),
             (arm * (1 - asym) + arm_bias, 0, arm_roll)),
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
        name = "walking" if generic_name and offset == 0 else f"walking_{style}"
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
