"""Build a varied, role-aware population of animated villagers."""

import copy
from math import cos, radians, sin
from pathlib import Path

from PIL import Image, ImageDraw

from generate_villager_action_animations import add_animations as add_actions, specifications
from generate_villager_emotion_animations import add_animations as add_emotions
from generate_villager_examples import build, write
from generate_villager_faces import find, scale_columns
from generate_villager_talking_animations import add_animations as add_talking
from generate_villager_waiting_animations import add_animations as add_waiting
from generate_villager_walking_animations import add_animations as add_walking
from preview_bdengine import render


ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = ROOT / "bdengine" / "characters" / "villagers" / "population"
PREVIEW_DIR = ROOT / "previews" / "characters" / "villagers" / "population"

COMMON = ("gesture_yes", "gesture_no", "gesture_wave", "reaction_hurt", "reaction_alert",
          "daily_sit", "daily_sleep", "daily_eat", "daily_drink", "daily_pick_up", "daily_put_down")
FARMER = ("profession_hoe", "profession_sow", "profession_harvest", "locomotion_carrying_walk")
SMITH = ("profession_hammer", "locomotion_carrying_walk")
GUARD = ("profession_guard", "gesture_point", "reaction_suspicious", "locomotion_running")
HUNTER = ("profession_shoot_bow", "reaction_suspicious", "locomotion_sneaking", "locomotion_running")
CLERGY = ("profession_pray", "daily_kneel", "reaction_cry")
NOBLE = ("gesture_point", "gesture_shrug", "profession_pray")
TRADER = ("gesture_point", "gesture_shrug", "locomotion_carrying_walk")
WORKER = ("locomotion_carrying_walk", "profession_harvest")
TRAVELER = ("locomotion_running", "locomotion_sneaking", "locomotion_carrying_walk")
GOBLIN_RAIDER = ("villain_threaten", "villain_evil_laugh", "villain_intimidate", "villain_slash",
                  "locomotion_running", "locomotion_sneaking", "reaction_suspicious")

APPEARANCE_OVERRIDES = {
    "goblin_raider": {"skinColor": "#424D3D", "pupilColor": "#621609", "bodyType": "goblin"},
    "chubby_villager": {"bodyType": "chubby"},
}

# gender, role, model preset, waiting, talking, walking, emotions, extra actions
POPULATION = {
    "alder_farmer": ("male", "farmer", ("broad", "broad", "short_heroic", "#76604A", "trimmed", "straw_hat", "farmer_m", "tool_belt"), "elder", "storyteller", "elder", ("joy", "sadness", "surprise"), FARMER),
    "mira_farmer": ("female", "farmer", ("rounded", "small", "braided", "#8A5B3D", None, "straw_hat", "farmer_f", "tool_belt"), "hardworking", "lively", "neutral", ("joy", "anger", "surprise"), FARMER),
    "bran_blacksmith": ("male", "blacksmith", ("broad", "rounded", "swept", "#3E3028", "forked", None, "blacksmith", "leather_bracers"), "hardworking", "authoritative", "heavy", ("anger", "joy", "surprise"), SMITH),
    "elise_smith": ("female", "child_smith_apprentice", ("small", "small", "braided", "#6F4430", None, "round_cap", "rustic_f", "leather_bracers"), "hardworking", "lively", "brisk", ("joy", "anger", "fear"), SMITH),
    "cedric_guard": ("male", "guard", ("default", "rounded", "short_heroic", "#544238", "moustache_classic", "kettle_helmet", "guard", "sword_scabbard"), "vigilant", "authoritative", "proud", ("anger", "fear", "surprise"), GUARD),
    "helena_guard": ("female", "guard", ("aquiline", "small", "very_long_loose", "#5F3C2E", None, "kettle_helmet", "guard", "sword_scabbard"), "vigilant", "authoritative", "brisk", ("anger", "fear", "surprise"), GUARD),
    "rowan_hunter": ("male", "hunter", ("long", "broad", "swept", "#4A3428", "moustache_drooping", "felt_hat", "hunter", "quiver"), "vigilant", "calm", "cautious", ("fear", "anger", "surprise"), HUNTER),
    "lyra_huntress": ("female", "hunter", ("small", "small", "braided", "#6C3F28", None, None, "hunter", "quiver"), "vigilant", "shy", "brisk", ("joy", "fear", "surprise"), HUNTER),
    "owen_priest": ("male", "clergy", ("long", "rounded", "swept", "#9A7658", "trimmed", "soft_cap", "clergy", "amulet"), "calm", "storyteller", "neutral", ("joy", "sadness", "fear"), CLERGY),
    "ameline_sister": ("female", "clergy", ("rounded", "small", "very_long_loose", "#B48A62", None, "soft_cap", "clergy", "amulet"), "calm", "calm", "neutral", ("joy", "sadness", "fear"), CLERGY),
    "edric_lord": ("male", "noble", ("aquiline", "broad", "short_heroic", "#684B38", "moustache_handlebar", "noble_cap", "noble_m", "shoulder_mantle"), "proud", "authoritative", "proud", ("anger", "joy", "surprise"), NOBLE),
    "isolde_lady": ("female", "noble", ("upturned", "small", "very_long_loose", "#C49A58", None, "noble_cap", "noble_f", "shoulder_mantle"), "proud", "authoritative", "proud", ("joy", "anger", "surprise"), NOBLE),
    "martin_innkeeper": ("male", "innkeeper", ("rounded", "rounded", "swept", "#76523A", "moustache_walrus", "round_cap", "well_dressed_m", "belt_pouch"), "calm", "lively", "neutral", ("joy", "anger", "surprise"), TRADER),
    "clara_baker": ("female", "baker", ("upturned", "rounded", "braided", "#B77B4F", None, "round_cap", "common_f", "neck_scarf"), "hardworking", "lively", "neutral", ("joy", "sadness", "surprise"), WORKER),
    "hugo_merchant": ("male", "merchant", ("aquiline", "small", "short_heroic", "#443329", "moustache_goatee", "felt_hat", "well_dressed_m", "satchel"), "proud", "authoritative", "neutral", ("joy", "anger", "fear"), TRADER),
    "elena_seamstress": ("female", "seamstress", ("small", "rounded", "elven_half_up", "#9A6541", None, "round_cap", "well_dressed_f", "belt_pouch"), "hardworking", "calm", "neutral", ("joy", "sadness", "surprise"), WORKER),
    "tomas_woodcutter": ("male", "woodcutter", ("broad", "broad", "long_wizard", "#493429", "braided", None, "rustic_m", "tool_belt"), "hardworking", "calm", "heavy", ("anger", "joy", "fear"), WORKER),
    "maeve_herbalist": ("female", "herbalist", ("rounded", "small", "elven_cascade", "#8B6747", None, None, "rustic_f", "satchel"), "calm", "storyteller", "cautious", ("joy", "sadness", "surprise"), CLERGY),
    "luc_shepherd": ("male", "shepherd_boy", ("default", "broad", "swept", "#7B6048", None, "felt_hat", "poor_peasant_m", "waterskin"), "nervous", "excited", "brisk", ("joy", "fear", "sadness"), WORKER),
    "anna_washerwoman": ("female", "washerwoman", ("broad", "rounded", "braided", "#665044", None, None, "poor_peasant_f", "neck_scarf"), "hardworking", "lively", "neutral", ("joy", "anger", "sadness"), WORKER),
    "gareth_traveler": ("male", "traveler", ("aquiline", "broad", "swept", "#4A3428", "moustache_handlebar", "felt_hat", "traveler_m", "traveler_cloak"), "nervous", "excited", "cautious", ("fear", "surprise", "joy"), TRAVELER),
    "selene_traveler": ("female", "traveler", ("small", "small", "very_long_loose", "#4F3028", None, None, "traveler_f", "traveler_cloak"), "nervous", "shy", "cautious", ("fear", "surprise", "sadness"), TRAVELER),
    "faelar_ranger": ("male", "elven_ranger", ("small", "elf_long", "elven_half_up", "#BCA06C", None, None, "traveler_m", "quiver"), "vigilant", "calm", "brisk", ("fear", "anger", "surprise"), HUNTER),
    "aelwen_healer": ("female", "elven_healer", ("small", "elf_short", "elven_cascade", "#E0C58D", None, "pointed_cap", "well_dressed_f", "amulet"), "calm", "storyteller", "neutral", ("joy", "sadness", "fear"), CLERGY),
    "goblin_raider": ("male", "goblin_raider", ("upturned", "elf_long", "bald", "#4D2E1F", None, None, "monster_raider", "sword_scabbard"), "nervous", "excited", "cautious", ("anger", "fear", "surprise"), GOBLIN_RAIDER),
    "chubby_villager": ("male", "chubby", ("broad", "rounded", "short_heroic", "#6B4A35", "moustache_walrus", None, "common_m", "belt_pouch"), "calm", "lively", "heavy", ("joy", "surprise", "fear"), TRADER),
}


EYEBROWS = ("thick", "thin", "arched", "stern", "worried", "bushy", "unibrow", "none")


def eyebrows(root, style):
    if style not in EYEBROWS:
        raise ValueError(f"Unknown eyebrow style: {style}")
    groups = [find(root, name) for name in ("Group 17", "Group 18")]
    if style == "none":
        for brow in groups:
            brow["children"] = []
    elif style == "thin":
        for group in groups:
            piece = group["children"][0]
            piece["transforms"] = scale_columns(piece["transforms"], x=.86, y=.48)
    elif style == "bushy":
        for index, group in enumerate(groups):
            source = group["children"][0]
            main, tuft = copy.deepcopy(source), copy.deepcopy(source)
            main["transforms"] = scale_columns(main["transforms"], x=1.05, y=.92)
            tuft["transforms"] = scale_columns(tuft["transforms"], x=.48, y=.64)
            tuft["transforms"][3] += (-1, 1)[index] * source["transforms"][0] * .18
            tuft["transforms"][7] += source["transforms"][5] * .20
            group["children"] = [main, tuft]
    elif style in ("stern", "worried"):
        for index, group in enumerate(groups):
            piece = group["children"][0]
            angle = (-12, 12)[index] * (1 if style == "stern" else -1)
            matrix = scale_columns(piece["transforms"], y=.72)
            width, height, turn = matrix[0], matrix[5], radians(angle)
            matrix[0], matrix[1], matrix[4], matrix[5] = (
                width * cos(turn), -height * sin(turn), width * sin(turn), height * cos(turn)
            )
            piece["transforms"] = matrix
    elif style == "arched":
        for group in groups:
            source = group["children"][0]
            pieces = []
            for side in (-1, 0, 1):
                piece = copy.deepcopy(source)
                matrix = scale_columns(piece["transforms"], x=.36, y=.58)
                matrix[3] += side * source["transforms"][0] * .16
                matrix[7] += (1 - abs(side)) * source["transforms"][5] * .18
                piece["transforms"] = matrix
                pieces.append(piece)
            group["children"] = pieces
    elif style == "unibrow":
        for index, group in enumerate(groups):
            piece = group["children"][0]
            piece["transforms"] = scale_columns(piece["transforms"], x=1.30, y=.88)
            piece["transforms"][3] += (1, -1)[index] * piece["transforms"][0] * .05
    root["faceStyle"] = "feminine_thin_eyebrows" if style == "thin" else f"eyebrows_{style}"


def thin_eyebrows(root):
    eyebrows(root, "thin")


def animate(root, waiting, talking, walking, emotions, action_names):
    add_waiting(root, (waiting,), generic_name=True)
    add_talking(root, (talking,), generic_name=True)
    add_walking(root, (walking,), generic_name=True)
    add_emotions(root, emotions)
    catalog = {f"{category.removesuffix('s')}_{name}": (category, name, profile)
               for category, name, profile in specifications()}
    selected = [catalog[name] for name in dict.fromkeys(COMMON + action_names)]
    add_actions(root, selected)


def overview(previews):
    columns, width, image_height, title_height = 4, 420, 162, 26
    rows = (len(previews) + columns - 1) // columns
    canvas = Image.new("RGB", (width * columns, (image_height + title_height) * rows), "#202020")
    draw = ImageDraw.Draw(canvas)
    for index, (name, path) in enumerate(previews):
        image = Image.open(path).convert("RGB").resize((width, image_height))
        x, y = index % columns * width, index // columns * (image_height + title_height)
        draw.text((x + 9, y + 6), name.replace("_", " ").title(), fill="white")
        canvas.paste(image, (x, y + title_height))
    canvas.save(PREVIEW_DIR / "village_population_overview.png")


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    PREVIEW_DIR.mkdir(parents=True, exist_ok=True)
    previews = []
    for name, (gender, role, preset, waiting, talking, walking, emotions, actions) in POPULATION.items():
        appearance = APPEARANCE_OVERRIDES.get(name, {})
        root = build(name, preset, appearance.get("skinColor", "#ECB880"),
                     appearance.get("bodyType"), appearance.get("pupilColor", "#424039"))[0]
        if gender == "female":
            thin_eyebrows(root)
        animate(root, waiting, talking, walking, emotions, actions)
        root["name"] = name.replace("_", " ").title()
        root["populationProfile"] = {"gender": gender, "role": role, "animationCount": len(root["listAnim"])}
        output = OUTPUT_DIR / f"villager_{name}.bdengine"
        preview = PREVIEW_DIR / f"villager_{name}_preview.png"
        write([root], output)
        render(output, preview)
        previews.append((name, preview))
        print(f"Created {output.name}: {len(root['listAnim'])} animations")
    overview(previews)
    print(f"Created {len(previews)} villagers and village_population_overview.png")


if __name__ == "__main__":
    main()
