"""Generate articulated fantasy wings fitted to villager bodies."""

import argparse
import base64
import copy
import gzip
import json
from math import pi, radians, sin

from generate_villager_body import BODY_TYPES, group
from generate_villager_hair import HEAD_DIR, VILLAGER_DIR, hair_box, texture, tint
from preview_bdengine import load


WING_DIR = VILLAGER_DIR / "wings"
WINGS = ("dragon", "bird", "angel", "demonic", "butterfly", "insect")
LAYERS = {
    "dragon": ("upper",), "bird": ("upper",), "demonic": ("upper",),
    "angel": ("upper", "lower"), "butterfly": ("upper", "lower"),
    "insect": ("upper", "lower"),
}
COLORS = {
    "dragon": "#66554B", "bird": "#8A7966", "angel": "#E7E1D2",
    "demonic": "#4D3540", "butterfly": "#745A9B", "insect": "#769A91",
}


def p(name, center, size, tone=0, rotation=(0, 0, 0)):
    return name, center, size, tone, rotation


def specs(style, layer):
    if style == "dragon":
        return [
            p("inner_bone", (.22, .13, 0), (.48, .10, .10), 1, (0, -6, 26)),
            p("outer_bone", (.62, .34, 0), (.55, .085, .09), 1, (0, -4, 17)),
            p("upper_membrane", (.34, .22, .01), (.47, .28, .065), 0, (0, -5, 25)),
            p("middle_membrane", (.62, .16, .01), (.43, .38, .06), 0, (0, -4, 8)),
            p("lower_membrane", (.81, -.03, .01), (.34, .30, .055), 0, (0, -2, -13)),
            p("outer_claw", (.98, -.14, 0), (.14, .08, .08), 2, (0, 0, -24)),
        ]
    if style == "demonic":
        return [
            p("shoulder", (.20, .10, 0), (.43, .11, .11), 1, (0, -7, 29)),
            p("finger_top", (.56, .36, 0), (.52, .075, .08), 1, (0, -5, 20)),
            p("finger_mid", (.67, .10, .01), (.55, .07, .075), 1, (0, -3, 2)),
            p("membrane_top", (.42, .24, .02), (.48, .29, .055), 0, (0, -5, 24)),
            p("membrane_mid", (.65, .15, .02), (.42, .28, .05), 0, (0, -3, 4)),
            p("membrane_notch", (.82, -.05, .02), (.28, .19, .045), 2, (0, 0, -18)),
            p("hook", (.96, -.14, 0), (.15, .07, .07), 2, (0, 0, -28)),
        ]
    if style == "bird":
        return [
            p("shoulder", (.18, .05, 0), (.40, .20, .11), 1, (0, -4, 12)),
            p("covert_top", (.42, .08, .01), (.45, .20, .10), 2, (0, -3, 5)),
            p("feather_1", (.43, -.10, .02), (.49, .15, .085), 0, (0, -2, -8)),
            p("feather_2", (.59, -.22, .02), (.57, .14, .08), 0, (0, -2, -15)),
            p("feather_3", (.73, -.35, .02), (.60, .125, .075), 1, (0, -1, -22)),
            p("feather_tip", (.86, -.47, .02), (.50, .10, .065), 1, (0, 0, -27)),
        ]
    if style == "angel":
        if layer == "upper":
            return [
                p("shoulder", (.18, .08, 0), (.42, .21, .11), 1, (0, -3, 15)),
                p("covert", (.43, .16, .01), (.48, .22, .10), 2, (0, -2, 10)),
                p("feather_1", (.53, .01, .02), (.58, .15, .08), 0, (0, -2, -4)),
                p("feather_2", (.72, -.12, .02), (.68, .14, .075), 0, (0, -1, -11)),
                p("feather_3", (.88, -.26, .02), (.72, .12, .07), 1, (0, 0, -18)),
                p("feather_tip", (1.01, -.39, .02), (.60, .095, .06), 1, (0, 0, -23)),
            ]
        return [
            p("lower_shoulder", (.16, -.02, .025), (.34, .17, .09), 1, (0, -2, 2)),
            p("lower_covert", (.36, -.10, .03), (.40, .17, .08), 2, (0, -1, -8)),
            p("lower_feather_1", (.43, -.24, .035), (.46, .13, .07), 0, (0, 0, -18)),
            p("lower_feather_2", (.55, -.37, .035), (.50, .11, .065), 0, (0, 0, -25)),
            p("lower_tip", (.64, -.48, .035), (.42, .085, .055), 1, (0, 0, -30)),
        ]
    if style == "butterfly":
        if layer == "upper":
            return [
                p("upper_base", (.18, .14, 0), (.35, .27, .07), 1, (0, -4, 18)),
                p("upper_center", (.40, .35, .01), (.43, .43, .065), 0, (0, -3, 23)),
                p("upper_outer", (.63, .53, .01), (.38, .37, .06), 2, (0, -2, 28)),
                p("upper_tip", (.79, .65, .01), (.23, .22, .055), 1, (0, 0, 32)),
            ]
        return [
            p("lower_base", (.16, -.06, .025), (.31, .24, .065), 1, (0, -3, -12)),
            p("lower_center", (.35, -.25, .03), (.38, .38, .06), 0, (0, -2, -24)),
            p("lower_outer", (.53, -.42, .03), (.31, .32, .055), 2, (0, 0, -32)),
        ]
    if style == "insect":
        if layer == "upper":
            return [
                p("upper_root", (.18, .10, 0), (.36, .11, .07), 1, (0, -5, 18)),
                p("upper_wing", (.53, .27, .01), (.70, .24, .055), 0, (0, -4, 14)),
                p("upper_tip", (.88, .39, .01), (.25, .16, .05), 2, (0, -2, 18)),
            ]
        return [
            p("lower_root", (.16, -.04, .025), (.32, .10, .065), 1, (0, -4, -13)),
            p("lower_wing", (.48, -.20, .03), (.64, .22, .05), 0, (0, -3, -17)),
            p("lower_tip", (.79, -.31, .03), (.23, .14, .045), 2, (0, -1, -21)),
        ]
    raise ValueError(f"Unknown wings: {style}")


def build(style, body_type="standard", color=None):
    root = copy.deepcopy(load(HEAD_DIR / "villager_head.bdengine"))
    refs = root.setdefault("refs", {}).setdefault("paintTextures", [])
    first = len(refs)
    color = color or COLORS[style]
    refs.extend(texture(tint(color, factor)) for factor in (1, .68, 1.22))
    profile = BODY_TYPES[body_type]
    back = -.22 + max(profile["depth"], profile.get("belly_depth", 0)) / 2 + .035
    rigs, count = [], 0
    for layer in LAYERS[style]:
        y = profile["chest_y"] + (.15 if layer == "upper" else -.10)
        for side, sign in (("Left", -1), ("Right", 1)):
            children = []
            for name, center, size, tone, rotation in specs(style, layer):
                position = (sign * center[0], center[1], center[2])
                turned = (rotation[0], sign * rotation[1], sign * rotation[2])
                children.append(hair_box(f"{side.lower()}_{name}", position, size, turned, first + tone))
            rig = group(f"{side} {layer.title()} Wing Rig", (sign * profile["chest"] * .22, y, back), children)
            rig.update({"wingSide": sign, "wingLayer": layer})
            rigs.append(rig)
            count += len(children)
    wings = group(f"Wings - {style}", (0, 0, 0), rigs)
    wings.update({"wingStyle": style, "wingColor": color})
    root["children"].append(wings)
    root["wingStyle"] = style
    root["wingBodyType"] = body_type
    return [root], count


def nodes(root):
    yield root
    for child in root.get("children", []):
        yield from nodes(child)


def animate_wings(root):
    wings = next((node for node in nodes(root) if node.get("name", "").startswith("Wings -")), None)
    if not wings:
        return root
    style = wings["name"].removeprefix("Wings -")
    rigs = [node for node in nodes(wings) if node.get("name", "").endswith("Wing Rig")]
    if not rigs and wings.get("defaultTransform"):
        rigs = [wings]
    for animation in root.get("listAnim", []):
        field = "animation" if animation["id"] == 1 else f"animation_{animation['id']}"
        duration = max((frame["time"] for node in nodes(root) for frame in node.get(field, [])), default=0)
        if not duration:
            continue
        name = animation["name"]
        amplitude = (16 if "walking" in name or any(word in name for word in ("joy", "fear", "surprise"))
                     else 4 if any(word in name for word in ("sleep", "sit", "kneel", "pray")) else 9)
        amplitude *= {"dragon": .8, "angel": .75, "demonic": .85,
                      "butterfly": 1.35, "insect": 1.6}.get(style, 1)
        beats = 2 if style in {"butterfly", "insect"} else 1
        for rig in rigs:
            rig[field] = wing_track(rig, duration, amplitude, beats)
    root["wingAnimations"] = [entry["name"] for entry in root.get("listAnim", [])]
    return root


def wing_track(rig, duration, amplitude, beats):
    default = rig["defaultTransform"]
    side = rig.get("wingSide", 1)
    phase = pi / 3 if rig.get("wingLayer") == "lower" else 0
    frames = []
    for index in range(beats * 4 + 1):
        angle = sin(index / 4 * 2 * pi + phase) * amplitude
        frames.append({
            "time": duration * index / (beats * 4),
            "position": dict(zip("xyz", default["position"])),
            "rotation": {"x": radians(default["rotation"]["x"]),
                         "y": radians(default["rotation"]["y"] + side * angle),
                         "z": radians(default["rotation"]["z"] + side * abs(angle) * .12)},
            "scale": dict(zip("xyz", default["scale"])),
        })
    return frames


def write(style, output):
    scene, count = build(style)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(base64.b64encode(gzip.compress(
        json.dumps(scene, separators=(",", ":")).encode(), mtime=0
    )).decode())
    assert load(output)["wingStyle"] == style
    return count


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--style", choices=["all", *WINGS], default="all")
    args = parser.parse_args()
    styles = WINGS if args.style == "all" else (args.style,)
    for style in styles:
        output = WING_DIR / f"villager_wings_{style}.bdengine"
        print(f"Created {output.name}: {write(style, output)} wing voxels")


if __name__ == "__main__":
    main()
