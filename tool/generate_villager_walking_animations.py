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

PROFILES = {
    "neutral": dict(duration=24, stride=25, arm=21, bob=.040, sway=1.5, lean=.5, head=1, twist=3),
    "brisk": dict(duration=20, stride=36, arm=31, bob=.065, sway=2.4, lean=2, head=2, twist=4),
    "heavy": dict(duration=32, stride=22, arm=17, bob=.075, sway=3.6, lean=2, head=2, twist=2.5),
    "cautious": dict(duration=36, stride=16, arm=11, bob=.030, sway=1.8, lean=2.5, head=4, twist=2),
    "elder": dict(duration=40, stride=13, arm=9, bob=.025, sway=3.2, lean=3, head=3, twist=1.5),
    "proud": dict(duration=32, stride=19, arm=8, bob=.032, sway=1.2, lean=0, head=1, twist=2.5),
}

SHOWCASES = {
    "neutral": "village_artisan", "brisk": "forest_huntress",
    "heavy": "village_blacksmith", "cautious": "road_traveler",
    "elder": "elder_farmer", "proud": "noblewoman",
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


def add_animations(root, styles, generic_name=False):
    reparent_head(root)
    character = reparent_character(root)
    upper = reparent_upper_body(root)
    remove_walking(root)
    first_id = max((entry["id"] for entry in root.get("listAnim", [])), default=0) + 1
    for offset, style in enumerate(styles):
        profile = PROFILES[style]
        duration, stride, arm = profile["duration"], profile["stride"], profile["arm"]
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
        root.setdefault("listAnim", []).append({
            "id": identifier, "name": "walking" if generic_name else f"walking_{style}",
        })
    root["walkingAnimations"] = list(styles)
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
