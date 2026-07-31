"""Extract the hand-separated wizard hair and beard into editor components."""

import copy
from pathlib import Path

from generate_villager_examples import write
from generate_villager_hair import texture, tint
from preview_bdengine import load


ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "bdengine/characters/villagers/custom/wizard.bdengine"
IDENTITY = [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1]
PURPLE_BUN = {40, 41, 42, 43}


def multiply(left, right):
    return [sum(left[row * 4 + index] * right[index * 4 + column] for index in range(4))
            for row in range(4) for column in range(4)]


def find_with_world(root, name):
    stack = [(root, IDENTITY)]
    while stack:
        node, parent = stack.pop()
        world = multiply(parent, node.get("transforms", IDENTITY))
        if node.get("name") == name:
            return copy.deepcopy(node), world
        stack.extend((child, world) for child in node.get("children", []))
    raise ValueError(f"Groupe {name} introuvable")


def clear_texture(piece, tone):
    piece["paintTexture"] = tone
    piece["defaultTextureValue"] = ""
    piece["textureValueList"] = []
    piece.setdefault("tagHead", {})["Value"] = ""


def component(source, source_name, target_name, color, preserve=()):
    group, world = find_with_world(source, source_name)
    group["name"] = target_name
    group["transforms"] = world
    for index, piece in enumerate(group["children"]):
        if index in preserve:
            continue
        x, y, z = (multiply(world, piece.get("transforms", IDENTITY))[axis] for axis in (3, 7, 11))
        if source_name == "Hair":
            tone = 2 if y > 2.05 or z < -.25 else (1 if z > .05 or abs(x) > .55 else 0)
        else:
            tone = 2 if y > 1.3 else (1 if y < .85 or abs(x) > .25 else 0)
        clear_texture(piece, tone)
    return {
        "isCollection": True, "isBackCollection": False, "name": "Wizard component", "nbt": "",
        "transforms": IDENTITY, "children": [group],
        "refs": {"paintTextures": [texture(tint(color, factor)) for factor in (1, .82, 1.12)]},
    }


def main():
    source = load(SOURCE)
    hair = component(source, "Hair", "Hair - wizard_original", "#B8B5AE", PURPLE_BUN)
    beard = component(source, "Beard", "Facial Hair - wizard_original", "#B8B5AE")
    write([hair], ROOT / "bdengine/characters/villagers/hair/villager_hair_wizard_original.bdengine")
    write([beard], ROOT / "bdengine/characters/villagers/facial_hair/beards/villager_beard_wizard_original.bdengine")
    assert sum("paintTexture" not in piece for piece in hair["children"][0]["children"]) == 4
    print("Created wizard_original hair and beard")


if __name__ == "__main__":
    main()
