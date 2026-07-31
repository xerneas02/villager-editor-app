"""Generate modular medieval clothing over existing villager body profiles."""

import argparse
import base64
import copy
import gzip
import json
from pathlib import Path

from PIL import ImageColor

from generate_villager_body import BODY_DIR, BODY_TYPES, group, pieces
from generate_villager_hair import VILLAGER_DIR, texture
from preview_bdengine import load


CLOTHING_DIR = VILLAGER_DIR / "clothing" / "outfits"

PALETTES = {
    "poor": ("#B7A57F", "#8E7A58", "#69543A", "#533923", "#C8B990"),
    "work": ("#9A9674", "#D1C8AA", "#66513A", "#503721", "#B59B55"),
    "smith": ("#5C5B54", "#B9B19B", "#493527", "#2F2925", "#8D918E"),
    "clergy": ("#D8D0B8", "#6E3940", "#A98A45", "#4B3432", "#EEE6CF"),
    "hunter": ("#687057", "#8B8666", "#493925", "#30271D", "#889071"),
    "guard": ("#6A7685", "#A7A18F", "#5B3840", "#453329", "#A99A62"),
    "noble": ("#65506F", "#D7C9A8", "#B09245", "#3F3047", "#E6D7B8"),
    "common": ("#71808A", "#D0C3A1", "#795A43", "#49382A", "#A88B52"),
    "monster": ("#ECB880", "#665039", "#896B45", "#493323", "#B99A62"),
}

TONE_NAMES = ("primary", "secondary", "trim", "leather", "accent")

PRESETS = {
    "poor_peasant_m": ("compact", "rough_tunic", "rough_trousers", "poor"),
    "poor_peasant_f": ("compact", "blouse", "simple_skirt", "poor"),
    "farmer_m": ("sturdy", "work_shirt", "work_trousers", "work"),
    "farmer_f": ("standard", "blouse", "work_skirt_apron", "work"),
    "blacksmith": ("sturdy", "blacksmith_apron", "work_trousers", "smith"),
    "clergy": ("standard", "clergy_tunic", "robe", "clergy"),
    "hunter": ("slender", "hunter_jerkin", "leggings", "hunter"),
    "guard": ("heroic", "guard_gambeson", "guard_chausses", "guard"),
    "noble_m": ("heroic", "noble_doublet", "fitted_trousers", "noble"),
    "noble_f": ("slender", "noble_bodice", "noble_skirt", "noble"),
    "common_m": ("standard", "plain_tunic", "plain_trousers", "common"),
    "common_f": ("standard", "long_blouse", "long_skirt", "common"),
    "rustic_m": ("compact", "belted_tunic", "knee_breeches", "poor"),
    "rustic_f": ("compact", "plain_tunic", "long_skirt", "poor"),
    "well_dressed_m": ("heroic", "laced_tunic", "fitted_trousers", "common"),
    "well_dressed_f": ("slender", "fitted_bodice", "noble_skirt", "common"),
    "traveler_m": ("slender", "sleeveless_surcoat", "leggings", "hunter"),
    "traveler_f": ("slender", "belted_tunic", "long_skirt", "hunter"),
    "monster_raider": ("orc", "bare_strapped", "hide_loincloth", "monster"),
    "monster_shaman": ("goblin", "bare_strapped", "hide_wrap", "monster"),
    "monster_warrior": ("brute", "hide_tunic", "hide_loincloth", "monster"),
}


def spec(name, center, size, tone, rotation=(0, 0, 0)):
    return name, center, size, rotation, tone


def base_top(profile, main="primary", sleeves="long", wide=0):
    depth = profile["depth"]
    chest_y, chest_h = profile["chest_y"], profile["chest_h"]
    result = {
        "Torso": [spec("garment_chest", (0, chest_y, -.22),
                       (profile["chest"] + .045, chest_h + .025, depth + .045), main)],
        "left_arm": [],
        "right_arm": [],
    }
    if profile.get("belly"):
        result["Torso"].extend([
            spec("garment_upper_belly", (0, .78, -.27),
                 (profile["belly"] * .90 + .045, .255, profile["belly_depth"] * .90 + .045), main),
            spec("garment_lower_belly", (0, .62, -.29),
                 (profile["belly"] + .045, .235, profile["belly_depth"] + .045), main),
        ])
    if sleeves == "none":
        return result
    sleeve_height = .34 if sleeves == "short" else .57
    sleeve_center = -.17 if sleeves == "short" else -.27
    for side, sign in (("left_arm", -1), ("right_arm", 1)):
        result[side].append(spec(
            f"{side}_sleeve", (sign * .015, sleeve_center, 0),
            (profile["arm"] + .035 + wide, sleeve_height, depth * .69 + .035),
            main, (0, 0, sign * -3),
        ))
        if sleeves == "rolled":
            result[side].append(spec(
                f"{side}_rolled_cuff", (sign * .02, -.43, -.01),
                (profile["arm"] + .045, .12, depth * .63 + .04), "secondary",
                (0, 0, sign * 2),
            ))
    return result


def add_torso(result, *items):
    result["Torso"].extend(items)
    return result


def fit_belly(profile, specs):
    """Keep thin front details and lower garments outside a protruding belly."""
    if not profile.get("belly"):
        return specs
    chest_front = -.22 - profile["depth"] / 2
    fitted = []
    for name, center, size, rotation, tone in specs:
        x, y, z = center
        bottom = y - size[1] / 2
        if size[2] <= .10 and z < -.22 and bottom < .92:
            belly_front = (-.29 - profile["belly_depth"] / 2 if bottom < .74
                           else -.27 - profile["belly_depth"] * .45)
            center = (x, y, z + belly_front - chest_front)
        fitted.append((name, center, size, rotation, tone))
    return fitted


def make_top(style, profile):
    d = profile["depth"]
    front = -.22 - d / 2 - .035
    bottom = profile["chest_y"] - profile["chest_h"] / 2

    if style in ("bare_strapped", "hide_tunic"):
        result = base_top(profile, sleeves="long")
        for side, sign in (("left_arm", -1), ("right_arm", 1)):
            result[side].append(spec(
                f"{side}_bare_shoulder", (sign * .01, -.13, 0),
                (profile["arm"] + .08, .34, profile["depth"] * .76 + .06), "primary",
                (0, 0, sign * -4),
            ))
        if style == "bare_strapped":
            result["Torso"].extend([
                spec("hide_belt", (0, bottom + .03, front - .02), (profile["waist"] + .12, .11, .06), "secondary"),
            ])
        else:
            result["Torso"].extend([
                spec("hide_tunic", (0, profile["chest_y"], front),
                     (profile["chest"] + .06, profile["chest_h"] + .04, .07), "secondary"),
                spec("hide_tunic_collar", (0, 1.17, front - .04), (.28, .11, .05), "trim"),
                spec("hide_tunic_belt", (0, bottom + .03, front - .03),
                     (profile["waist"] + .14, .12, .07), "leather"),
            ])
            for side, sign in (("left_arm", -1), ("right_arm", 1)):
                result[side].append(spec(
                    f"{side}_hide_sleeve", (sign * .01, -.15, 0),
                    (profile["arm"] + .10, .37, profile["depth"] * .78 + .07), "secondary",
                    (0, 0, sign * -4),
                ))
        return result

    if style == "plain_tunic":
        return add_torso(
            base_top(profile),
            spec("plain_tunic_collar", (0, 1.17, front), (.24, .10, .055), "secondary"),
            spec("plain_tunic_hem", (0, bottom + .03, front), (profile["waist"] + .10, .08, .05), "trim"),
        )
    if style == "belted_tunic":
        return add_torso(
            base_top(profile, sleeves="rolled"),
            spec("belted_tunic_neck_left", (-.035, 1.15, front), (.045, .15, .055), "secondary", (0, 0, -28)),
            spec("belted_tunic_neck_right", (.035, 1.15, front), (.045, .15, .055), "secondary", (0, 0, 28)),
            spec("belted_tunic_belt", (0, bottom + .04, front - .01), (profile["waist"] + .12, .10, .06), "leather"),
        )
    if style == "long_blouse":
        return add_torso(
            base_top(profile, main="secondary", wide=.045),
            spec("long_blouse_collar", (0, 1.17, front), (.27, .11, .06), "primary"),
            spec("long_blouse_panel", (0, .93, front - .01), (.10, .37, .055), "primary"),
            spec("long_blouse_hem", (0, bottom + .02, front), (profile["waist"] + .13, .10, .055), "trim"),
        )
    if style == "fitted_bodice":
        return add_torso(
            base_top(profile, main="secondary"),
            spec("fitted_bodice_upper", (0, 1.04, front - .02), (profile["chest"] * .68, .23, .07), "primary"),
            spec("fitted_bodice_lower", (0, .84, front - .025), (profile["waist"] * .72, .23, .075), "primary"),
            spec("fitted_bodice_lacing", (0, .91, front - .06), (.06, .30, .04), "accent"),
        )
    if style == "laced_tunic":
        result = base_top(profile)
        add_torso(
            result,
            spec("laced_tunic_collar", (0, 1.17, front), (.26, .11, .06), "secondary"),
            spec("laced_tunic_placket", (0, 1.02, front - .02), (.08, .24, .05), "trim"),
            spec("laced_tunic_belt", (0, bottom + .03, front), (profile["waist"] + .10, .09, .055), "accent"),
        )
        for y in (1.08, 1.02, .96):
            result["Torso"].append(spec(f"laced_tunic_lace_{y}", (0, y, front - .055), (.14, .025, .025), "accent"))
        return result
    if style == "sleeveless_surcoat":
        return add_torso(
            base_top(profile, sleeves="none"),
            spec("surcoat_front", (0, .98, front), (profile["chest"] * .72, .48, .075), "primary"),
            spec("surcoat_neck", (0, 1.17, front - .02), (.22, .12, .05), "secondary"),
            spec("surcoat_belt", (0, bottom + .03, front - .02), (profile["waist"] + .09, .10, .055), "leather"),
        )
    if style == "rough_tunic":
        return add_torso(
            base_top(profile, sleeves="short"),
            spec("rough_neck", (0, 1.17, front), (.18, .14, .055), "secondary"),
            spec("rough_hem", (0, bottom + .04, front), (profile["chest"] * .88, .10, .055), "trim"),
        )
    if style == "work_shirt":
        return add_torso(
            base_top(profile, sleeves="rolled"),
            spec("shirt_yoke", (0, 1.14, front), (profile["chest"] * .76, .15, .055), "secondary"),
            spec("shirt_placket", (0, .96, front - .005), (.08, .34, .06), "trim"),
            spec("shirt_belt", (0, bottom + .03, front), (profile["waist"] + .06, .10, .06), "leather"),
        )
    if style == "blouse":
        result = base_top(profile, sleeves="long", wide=.055)
        add_torso(
            result,
            spec("blouse_neck", (0, 1.16, front), (.24, .13, .055), "secondary"),
            spec("blouse_bodice", (0, .93, front - .005), (profile["waist"] * .72, .30, .06), "trim"),
        )
        for y, width in ((1.01, .18), (.94, .15), (.87, .12)):
            result["Torso"].append(spec(f"blouse_lace_{y}", (0, y, front - .04), (width, .035, .035), "accent"))
        return result
    if style == "blacksmith_apron":
        result = base_top(profile, main="secondary", sleeves="rolled")
        return add_torso(
            result,
            spec("apron_bib", (0, .99, front - .025), (profile["chest"] * .58, .42, .075), "leather"),
            spec("apron_skirt", (0, .67, front - .025), (profile["waist"] * .82, .35, .075), "leather"),
            spec("apron_left_strap", (-.22, 1.12, front - .035), (.07, .34, .05), "trim", (0, 0, -7)),
            spec("apron_right_strap", (.22, 1.12, front - .035), (.07, .34, .05), "trim", (0, 0, 7)),
            spec("apron_belt", (0, .78, front - .045), (profile["waist"] + .10, .09, .055), "trim"),
        )
    if style == "clergy_tunic":
        result = base_top(profile, sleeves="long", wide=.04)
        return add_torso(
            result,
            spec("clerical_lower_tunic", (0, .69, -.22), (profile["waist"] + .14, .32, d + .06), "primary"),
            spec("clerical_stole", (0, .91, front - .02), (.18, .58, .07), "secondary"),
            spec("clerical_stole_trim", (0, .63, front - .045), (.22, .08, .045), "accent"),
            spec("clerical_collar", (0, 1.19, front - .015), (.30, .11, .065), "accent"),
        )
    if style == "hunter_jerkin":
        result = base_top(profile, main="secondary", sleeves="rolled")
        return add_torso(
            result,
            spec("jerkin_left", (-profile["chest"] * .18, .99, front - .02),
                 (profile["chest"] * .34, .43, .07), "primary", (0, 0, -2)),
            spec("jerkin_right", (profile["chest"] * .18, .99, front - .02),
                 (profile["chest"] * .34, .43, .07), "primary", (0, 0, 2)),
            spec("jerkin_center", (0, .97, front - .05), (.055, .40, .035), "trim"),
            spec("jerkin_belt", (0, .77, front - .04), (profile["waist"] + .09, .10, .05), "leather"),
        )
    if style == "guard_gambeson":
        result = base_top(profile, sleeves="long", wide=.055)
        for index, y in enumerate((1.15, 1.02, .89, .76)):
            result["Torso"].append(spec(f"gambeson_band_{index}", (0, y, front - .02),
                                        (profile["chest"] * .86, .055, .045), "secondary"))
        return add_torso(
            result,
            spec("gambeson_collar", (0, 1.21, front - .015), (.34, .12, .065), "trim"),
            spec("gambeson_belt", (0, .71, front - .035), (profile["waist"] + .13, .11, .055), "leather"),
        )
    if style == "noble_doublet":
        result = base_top(profile, sleeves="long", wide=.04)
        return add_torso(
            result,
            spec("doublet_left", (-profile["chest"] * .18, .99, front - .02),
                 (profile["chest"] * .34, .44, .07), "primary", (0, 0, -2)),
            spec("doublet_right", (profile["chest"] * .18, .99, front - .02),
                 (profile["chest"] * .34, .44, .07), "primary", (0, 0, 2)),
            spec("doublet_center_trim", (0, .99, front - .055), (.055, .47, .04), "accent"),
            spec("doublet_collar", (0, 1.20, front - .02), (.32, .12, .065), "secondary"),
            spec("doublet_waist", (0, .75, front - .035), (profile["waist"] + .07, .09, .055), "accent"),
        )
    if style == "noble_bodice":
        result = base_top(profile, main="secondary", sleeves="long", wide=.04)
        return add_torso(
            result,
            spec("bodice_upper", (0, 1.03, front - .02), (profile["chest"] * .70, .25, .07), "primary"),
            spec("bodice_waist", (0, .83, front - .025), (profile["waist"] * .75, .25, .075), "primary"),
            spec("bodice_center", (0, .91, front - .055), (.07, .38, .04), "accent"),
            spec("bodice_neckline", (0, 1.16, front - .025), (.30, .08, .06), "trim"),
            spec("bodice_belt", (0, .72, front - .04), (profile["waist"] + .08, .09, .05), "accent"),
        )
    raise ValueError(f"Unknown top: {style}")


def trouser_bottom(profile, style):
    result = {"left_leg": [], "right_leg": [], "Torso": []}
    hip = profile["hip"]
    thigh_y = (.25 + hip + .03) / 2 - hip
    for side, sign in (("left_leg", -1), ("right_leg", 1)):
        result[side].extend([
            spec(f"{side}_trouser_thigh", (0, thigh_y, 0),
                 (profile["leg"] + .035, hip - .20, profile["depth"] * .81 + .035), "primary",
                 (0, 0, sign * -2)),
            spec(f"{side}_trouser_lower", (0, .20 - hip, 0),
                 (profile["lower"] + .035, .31, profile["depth"] * .69 + .035), "primary",
                 (0, 0, sign)),
        ])
        if style in ("rough_trousers", "guard_chausses"):
            result[side].append(spec(
                f"{side}_knee", (0, .30 - hip, -profile["depth"] * .36),
                (profile["leg"] * .72, .13, .055), "secondary",
            ))
        if style == "work_trousers":
            result[side].append(spec(
                f"{side}_cuff", (0, .08 - hip, 0),
                (profile["lower"] + .05, .10, profile["depth"] * .72 + .04), "trim",
            ))
        if style == "guard_chausses":
            result[side].append(spec(
                f"{side}_guard_strip", (0, .43 - hip, -profile["depth"] * .43),
                (profile["leg"] * .34, .28, .045), "trim",
            ))
        if style == "fitted_trousers":
            result[side].append(spec(
                f"{side}_noble_cuff", (0, .08 - hip, 0),
                (profile["lower"] + .04, .09, profile["depth"] * .71 + .035), "accent",
            ))
        if style == "knee_breeches":
            result[side].append(spec(
                f"{side}_breeches_cuff", (0, .28 - hip, 0),
                (profile["leg"] + .05, .11, profile["depth"] * .75 + .04), "trim",
            ))
    return result


def skirt_bottom(profile, style):
    d = max(profile["depth"], profile.get("belly_depth", 0))
    result = {"Torso": [], "left_leg": [], "right_leg": []}
    if style == "robe":
        layers = ((.58, .24, profile["pelvis"] + .10),
                  (.39, .28, profile["pelvis"] + .20),
                  (.16, .22, profile["pelvis"] + .28))
    elif style == "noble_skirt":
        layers = ((.58, .22, profile["pelvis"] + .08),
                  (.42, .22, profile["pelvis"] + .18),
                  (.25, .22, profile["pelvis"] + .30),
                  (.09, .13, profile["pelvis"] + .38))
    elif style == "long_skirt":
        layers = ((.56, .24, profile["pelvis"] + .07),
                  (.36, .24, profile["pelvis"] + .15),
                  (.16, .22, profile["pelvis"] + .23))
    else:
        layers = ((.56, .22, profile["pelvis"] + .06),
                  (.38, .25, profile["pelvis"] + .14),
                  (.18, .22, profile["pelvis"] + .22))
    for index, (y, height, width) in enumerate(layers):
        result["Torso"].append(spec(f"{style}_layer_{index}", (0, y, -.22),
                                    (width, height, d + .07 + index * .025),
                                    "primary" if index % 2 == 0 else "secondary"))
    front = -.22 - d / 2 - .07
    if style == "work_skirt_apron":
        result["Torso"].extend([
            spec("work_apron", (0, .37, front), (profile["pelvis"] * .68, .48, .065), "secondary"),
            spec("work_apron_hem", (0, .14, front - .035), (profile["pelvis"] * .72, .075, .04), "trim"),
        ])
    if style == "noble_skirt":
        result["Torso"].append(spec("noble_skirt_trim", (0, .08, front - .02),
                                    (profile["pelvis"] + .34, .07, .045), "accent"))
    if style == "robe":
        result["Torso"].append(spec("robe_front", (0, .35, front - .015),
                                    (.20, .52, .055), "secondary"))
    return result


def hide_bottom(profile, style, top):
    depth = max(profile["depth"], profile.get("belly_depth", 0))
    front = -.22 - depth / 2 - .05
    if style == "hide_wrap":
        front_y = profile["pelvis_y"] - .11
        ragged_y = (profile["pelvis_y"] - .0137, profile["pelvis_y"] - .0113)
        back_y, back_z = profile["pelvis_y"] - .0638, -.22 + profile["depth"] / 2 - .0038
        ragged_z = (front + .0038, front + .0188)
    elif top == "hide_tunic":
        front_y = profile["pelvis_y"] - .0425
        ragged_y = (profile["pelvis_y"] + .0275,) * 2
        back_y, back_z = profile["pelvis_y"] + .065, -.22 + profile["depth"] / 2 + .0012
        ragged_z = (front, front)
    else:
        front_y = profile["pelvis_y"] - .07875
        ragged_y = (profile["pelvis_y"] + .0275,) * 2
        back_y, back_z = profile["pelvis_y"] + .065, -.22 + profile["depth"] / 2 + .0012
        ragged_z = (front + .0225, front + .0131)
    result = {"Torso": [
        spec("hide_waist", (0, .57, -.22), (profile["pelvis"] + .12, .15, depth + .08), "leather"),
        spec("hide_front", (0, front_y, front), (profile["pelvis"] * .55, .35, .075), "secondary"),
        spec("hide_front_ragged_left", (-.13, ragged_y[0], ragged_z[0]), (.18, .14, .075), "secondary"),
        spec("hide_front_ragged_right", (.125, ragged_y[1], ragged_z[1]), (.18, .14, .075), "secondary"),
        spec("hide_back", (0, back_y, back_z),
             (profile["pelvis"] * 1.10, .70 if style == "hide_wrap" else .45, .075), "secondary"),
    ], "left_leg": [], "right_leg": []}
    hip = profile["hip"]
    thigh_y = (.25 + hip + .03) / 2 - hip
    for side in ("left_leg", "right_leg"):
        result[side].extend([
            spec(f"{side}_bare_thigh", (0, thigh_y, 0),
                 (profile["leg"] + .045, hip - .20, profile["depth"] * .81 + .045), "primary"),
            spec(f"{side}_bare_shin", (0, .20 - hip, 0),
                 (profile["lower"] + .045, .31, profile["depth"] * .69 + .045), "primary"),
            spec(f"{side}_hide_ankle_wrap", (0, .08 - hip, 0),
                 (profile["lower"] + .06, .10, profile["depth"] * .73 + .05), "secondary"),
        ])
    if style == "hide_wrap":
        result["Torso"].extend([
            spec("hide_side_left", (-profile["pelvis"] / 2, .36, -.22), (.10, .38, depth + .05), "trim", (0, 0, -3)),
            spec("hide_side_right", (profile["pelvis"] / 2, .39, -.22), (.10, .32, depth + .05), "trim", (0, 0, 3)),
        ])
    return result


TOPS = {
    name: name for name in (
        "rough_tunic", "work_shirt", "blouse", "blacksmith_apron", "clergy_tunic",
        "hunter_jerkin", "guard_gambeson", "noble_doublet", "noble_bodice",
        "plain_tunic", "belted_tunic", "long_blouse", "fitted_bodice",
        "laced_tunic", "sleeveless_surcoat",
        "bare_strapped", "hide_tunic",
    )
}

BOTTOMS = {
    name: name for name in (
        "rough_trousers", "work_trousers", "leggings", "guard_chausses",
        "fitted_trousers", "plain_trousers", "knee_breeches", "simple_skirt",
        "long_skirt", "work_skirt_apron", "robe", "noble_skirt",
        "hide_loincloth", "hide_wrap",
    )
}


def find(root, name):
    stack = [root]
    while stack:
        node = stack.pop()
        if node.get("name") == name:
            return node
        stack.extend(node.get("children", []))
    raise ValueError(f"Missing body group: {name}")


def body_file(body_type):
    name = "villager_body_structure.bdengine" if body_type == "standard" else f"villager_body_{body_type}.bdengine"
    return BODY_DIR / name


def build(body_type, top, bottom, palette_name):
    root = copy.deepcopy(load(body_file(body_type)))
    profile = BODY_TYPES[body_type]
    refs = root.setdefault("refs", {}).setdefault("paintTextures", [])
    first = len(refs)
    refs.extend(texture(ImageColor.getrgb(color)) for color in PALETTES[palette_name])
    palette = {name: first + index for index, name in enumerate(TONE_NAMES)}

    top_parts = make_top(top, profile)
    top_parts["Torso"] = fit_belly(profile, top_parts["Torso"])
    if bottom in ("hide_loincloth", "hide_wrap"):
        bottom_parts = hide_bottom(profile, bottom, top)
    elif bottom in ("simple_skirt", "long_skirt", "work_skirt_apron", "robe", "noble_skirt"):
        bottom_parts = skirt_bottom(profile, bottom)
    else:
        bottom_parts = trouser_bottom(profile, bottom)
    total = 0
    for target in ("Torso", "left_arm", "right_arm", "left_leg", "right_leg"):
        specs = top_parts.get(target, []) + bottom_parts.get(target, [])
        if specs:
            find(root, target)["children"].append(group(
                f"Clothing - {target}", (0, 0, 0), pieces(specs, palette)
            ))
            total += len(specs)
    root["name"] = f"Villager outfit - {top} + {bottom}"
    root["clothing"] = {"body": body_type, "top": top, "bottom": bottom, "palette": palette_name}
    return [root], total


def write(output, body_type, top, bottom, palette_name):
    scene, count = build(body_type, top, bottom, palette_name)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(base64.b64encode(gzip.compress(
        json.dumps(scene, separators=(",", ":")).encode(), mtime=0
    )).decode())
    decoded = json.loads(gzip.decompress(base64.b64decode(output.read_text())))[0]
    assert decoded["clothing"] == {
        "body": body_type, "top": top, "bottom": bottom, "palette": palette_name
    }
    assert count > 0
    return count


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--preset", choices=["all", *PRESETS])
    parser.add_argument("--body", choices=BODY_TYPES)
    parser.add_argument("--top", choices=TOPS)
    parser.add_argument("--bottom", choices=BOTTOMS)
    parser.add_argument("--palette", choices=PALETTES, default="work")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    if args.preset:
        presets = PRESETS if args.preset == "all" else (args.preset,)
        for name in presets:
            body_type, top, bottom, palette_name = PRESETS[name]
            output = args.output if args.output and len(presets) == 1 else CLOTHING_DIR / f"villager_outfit_{name}.bdengine"
            count = write(output, body_type, top, bottom, palette_name)
            print(f"Created {output}: {count} clothing pieces")
        return

    if not (args.body and args.top and args.bottom):
        parser.error("use --preset or provide --body, --top and --bottom")
    output = args.output or CLOTHING_DIR / f"villager_outfit_{args.body}_{args.top}_{args.bottom}.bdengine"
    count = write(output, args.body, args.top, args.bottom, args.palette)
    print(f"Created {output}: {count} clothing pieces")


if __name__ == "__main__":
    main()
