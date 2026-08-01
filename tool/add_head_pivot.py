#!/usr/bin/env python3
"""Add an independently rotatable head/neck pivot to a BDEngine datapack.

Usage:
    python tool/add_head_pivot.py PACK MODEL.bdengine OUTPUT_PACK

The source model is required because BDEngine datapacks only retain numbered
display tags; the semantic ``Head Rig`` hierarchy has already been flattened.

Generated API:
    execute as <npc_root> run function <namespace>:head_pivot/enable
    tag <look_target> add <namespace>_head_target   # optional; otherwise player
    execute as <npc_root> run function <namespace>:head_pivot/disable
"""

import argparse
import base64
import gzip
import json
import re
import shutil
from pathlib import Path


IDENTITY = [1.0, 0.0, 0.0, 0.0,
            0.0, 1.0, 0.0, 0.0,
            0.0, 0.0, 1.0, 0.0,
            0.0, 0.0, 0.0, 1.0]


def multiply(a, b):
    return [sum(a[row * 4 + k] * b[k * 4 + column] for k in range(4))
            for row in range(4) for column in range(4)]


def inverse(matrix):
    rows = [[matrix[row * 4 + column] for column in range(4)]
            + [float(row == column) for column in range(4)] for row in range(4)]
    for column in range(4):
        pivot = max(range(column, 4), key=lambda row: abs(rows[row][column]))
        if abs(rows[pivot][column]) < 1e-10:
            raise ValueError("Matrice de transformation non inversible")
        rows[column], rows[pivot] = rows[pivot], rows[column]
        divisor = rows[column][column]
        rows[column] = [value / divisor for value in rows[column]]
        for row in range(4):
            if row != column:
                factor = rows[row][column]
                rows[row] = [value - factor * other
                             for value, other in zip(rows[row], rows[column])]
    return [rows[row][column] for row in range(4) for column in range(4, 8)]


def transform_point(matrix, point):
    vector = (*point, 1.0)
    return tuple(sum(matrix[row * 4 + column] * vector[column] for column in range(4))
                 for row in range(3))


def parse_matrix(value):
    return [float(part.strip().rstrip("fFdD")) for part in value.split(",")]


def number(value):
    value = 0.0 if abs(value) < 5e-11 else value
    return f"{value:.10g}"


def matrix_text(matrix):
    return ",".join(f"{number(value)}f" for value in matrix)


def load_model(path):
    try:
        return json.loads(gzip.decompress(base64.b64decode(path.read_text())))[0]
    except Exception as error:
        raise ValueError(f"Modèle bdengine illisible: {path}") from error


def model_parts(root, group_name):
    leaves = []
    head_matrix = None

    def visit(node, parent, inside_head=False, chain=()):
        nonlocal head_matrix
        current = multiply(parent, node.get("transforms", IDENTITY))
        inside_head = inside_head or node.get("name") == group_name
        if node.get("name") == group_name:
            if head_matrix is not None:
                raise ValueError(f"Plusieurs groupes {group_name!r} dans le modèle")
            head_matrix = current
            chain = ()
        elif inside_head:
            chain += (node,)
        children = node.get("children", [])
        if children:
            for child in children:
                visit(child, current, inside_head, chain)
        else:
            leaves.append((inside_head, chain, current))

    visit(root, IDENTITY)
    if head_matrix is None:
        raise ValueError(f"Groupe {group_name!r} absent du modèle")
    head_indices = {index for index, (inside, _, _) in enumerate(leaves) if inside}
    if not head_indices:
        raise ValueError(f"Le groupe {group_name!r} ne contient aucun display")

    def independently_animated(chain):
        return any(any(key == "animation" or key.startswith("animation_") for key in node)
                   for node in chain)

    candidates = [(len(chain), index, matrix) for index, (inside, chain, matrix) in enumerate(leaves)
                  if inside and not independently_animated(chain)]
    if not candidates:
        raise ValueError("Aucun display de tête stable utilisable comme repère")
    _, anchor_index, anchor_matrix = min(candidates)
    return leaves, head_indices, anchor_index, anchor_matrix, (head_matrix[3], head_matrix[7], head_matrix[11])


def discover_pack(pack):
    creates = list(pack.glob("data/*/function/_/create.mcfunction"))
    if len(creates) != 1:
        raise ValueError("Le datapack doit contenir exactement un function/_/create.mcfunction")
    create = creates[0]
    return create.parts[-4], create


def install(pack, model_path, output, group_name="Head Rig", tracking_range=16):
    pack, output = pack.resolve(), output.resolve()
    if not pack.is_dir() or not model_path.is_file():
        raise ValueError("Le datapack ou le modèle bdengine est introuvable")
    if output == pack or pack in output.parents:
        raise ValueError("La sortie ne peut pas être placée dans le datapack source")
    namespace, source_create = discover_pack(pack)
    root = load_model(model_path)
    leaves, head_indices, anchor_index, source_anchor, source_pivot = model_parts(root, group_name)
    create_text = source_create.read_text(encoding="utf-8")
    if f"{namespace}_head_root" in create_text:
        raise ValueError("Ce datapack possède déjà un pivot de tête")

    create_pattern = re.compile(
        rf"(transformation:\[)([^\]]+)(\][^\n]*?Tags:\[\"{re.escape(namespace)}_(\d+)\"\])")
    initial = {int(match.group(4)): parse_matrix(match.group(2))
               for match in create_pattern.finditer(create_text)}
    if set(initial) != set(range(len(leaves))):
        raise ValueError(f"Le modèle contient {len(leaves)} displays mais le datapack en exporte {len(initial)}")

    pack_from_source = multiply(initial[anchor_index], inverse(source_anchor))
    pivot0 = transform_point(pack_from_source, source_pivot)
    anchor_inverse = inverse(initial[anchor_index])

    if output.exists():
        raise ValueError(f"La sortie existe déjà: {output}")
    shutil.copytree(pack, output)
    create = output / source_create.relative_to(pack)

    def rebase_create(match):
        index = int(match.group(4))
        matrix = parse_matrix(match.group(2))
        if index in head_indices:
            matrix[3], matrix[7], matrix[11] = (matrix[3] - pivot0[0], matrix[7] - pivot0[1],
                                                matrix[11] - pivot0[2])
        return match.group(1) + matrix_text(matrix) + match.group(3)

    create_text = create_pattern.sub(rebase_create, create_text).rstrip() + "\n"
    coordinates = ",".join(f'{axis}:"{number(value)}"' for axis, value in zip("xyz", pivot0))
    setup = [
        "",
        "# Head/neck pivot generated by tool/add_head_pivot.py",
        f'execute as @e[type=minecraft:block_display,tag={namespace}_root,limit=1,sort=nearest] at @s positioned ^{number(pivot0[0])} ^{number(pivot0[1])} ^{number(pivot0[2])} run summon minecraft:block_display ~ ~ ~ '
        f'{{block_state:{{Name:"minecraft:air"}},teleport_duration:2,data:{{{coordinates}}},Tags:["{namespace}","{namespace}_head_root"]}}',
    ]
    setup.extend(
        f'execute as @e[type=minecraft:block_display,tag={namespace}_root,limit=1,sort=nearest] at @s run ride '
        f'@e[type=minecraft:item_display,tag={namespace}_{index},distance=..{tracking_range},limit=1,sort=nearest] mount '
        f'@e[type=minecraft:block_display,tag={namespace}_head_root,distance=..{tracking_range},limit=1,sort=nearest]'
        for index in sorted(head_indices)
    )
    create.write_text(create_text + "\n".join(setup) + "\n", encoding="utf-8")

    line_pattern = re.compile(
        rf"(tag={re.escape(namespace)}_(\d+),[^\n]*?\{{transformation:\[)([^\]]+)(\])")
    keyframes = list((output / "data" / namespace / "function" / "k").glob("**/keyframe_*.mcfunction"))
    if not keyframes:
        raise ValueError("Aucune keyframe BDEngine trouvée")
    groups = {}
    for keyframe in keyframes:
        groups.setdefault(keyframe.parent, []).append(keyframe)
    for frames in groups.values():
        anchor = initial[anchor_index]
        for keyframe in sorted(frames, key=lambda path: int(path.stem.rsplit("_", 1)[1])):
            text = keyframe.read_text(encoding="utf-8")
            matrices = {int(match.group(2)): parse_matrix(match.group(3))
                        for match in line_pattern.finditer(text)}
            anchor = matrices.get(anchor_index, anchor)
            pivot = transform_point(multiply(anchor, anchor_inverse), pivot0)

            def rebase_keyframe(match):
                index = int(match.group(2))
                matrix = parse_matrix(match.group(3))
                if index in head_indices:
                    matrix[3], matrix[7], matrix[11] = (matrix[3] - pivot[0], matrix[7] - pivot[1],
                                                        matrix[11] - pivot[2])
                    prefix = match.group(1).replace("distance=..1", f"distance=..{tracking_range}")
                else:
                    prefix = match.group(1)
                return prefix + matrix_text(matrix) + match.group(4)

            text = line_pattern.sub(rebase_keyframe, text).rstrip() + "\n"
            offset = ",".join(f'{axis}:"{number(value)}"' for axis, value in zip("xyz", pivot))
            update = (f'data merge entity @e[type=minecraft:block_display,tag={namespace}_head_root,'
                      f'distance=..{tracking_range},limit=1,sort=nearest] {{data:{{{offset}}}}}\n')
            schedule = text.rfind("schedule function ")
            text = text[:schedule] + update + text[schedule:] if schedule >= 0 else text + update
            keyframe.write_text(text, encoding="utf-8")

    functions = output / "data" / namespace / "function" / "head_pivot"
    functions.mkdir(parents=True, exist_ok=True)
    (functions / "sync.mcfunction").write_text(
        f'$tp @e[type=minecraft:block_display,tag={namespace}_head_root,distance=..{tracking_range},limit=1,sort=nearest] ^$(x) ^$(y) ^$(z)\n',
        encoding="utf-8")
    (functions / "tick.mcfunction").write_text(
        f'execute as @e[type=minecraft:block_display,tag={namespace}_root] at @s run function {namespace}:head_pivot/sync with entity '
        f'@e[type=minecraft:block_display,tag={namespace}_head_root,distance=..{tracking_range},limit=1,sort=nearest] data\n'
        f'execute as @e[type=minecraft:block_display,tag={namespace}_root] at @s run data modify entity '
        f'@e[type=minecraft:block_display,tag={namespace}_head_root,distance=..{tracking_range},limit=1,sort=nearest] Rotation set from entity @s Rotation\n'
        f'execute as @e[type=minecraft:block_display,tag={namespace}_root,tag={namespace}_head_track] at @s if entity '
        f'@e[tag={namespace}_head_target,distance=..{tracking_range},limit=1] run rotate '
        f'@e[type=minecraft:block_display,tag={namespace}_head_root,distance=..{tracking_range},limit=1,sort=nearest] facing entity '
        f'@e[tag={namespace}_head_target,distance=..{tracking_range},limit=1,sort=nearest] eyes\n'
        f'execute as @e[type=minecraft:block_display,tag={namespace}_root,tag={namespace}_head_track] at @s unless entity '
        f'@e[tag={namespace}_head_target,distance=..{tracking_range},limit=1] if entity @p[distance=..{tracking_range}] run rotate '
        f'@e[type=minecraft:block_display,tag={namespace}_head_root,distance=..{tracking_range},limit=1,sort=nearest] facing entity '
        f'@p[distance=..{tracking_range},limit=1,sort=nearest] eyes\n', encoding="utf-8")
    (functions / "enable.mcfunction").write_text(f"tag @s add {namespace}_head_track\n", encoding="utf-8")
    (functions / "disable.mcfunction").write_text(f"tag @s remove {namespace}_head_track\n", encoding="utf-8")

    tick_tag = output / "data" / "minecraft" / "tags" / "function" / "tick.json"
    tick_tag.parent.mkdir(parents=True, exist_ok=True)
    values = json.loads(tick_tag.read_text(encoding="utf-8")).get("values", []) if tick_tag.exists() else []
    tick_function = f"{namespace}:head_pivot/tick"
    if tick_function not in values:
        values.append(tick_function)
    tick_tag.write_text(json.dumps({"values": values}, indent=2) + "\n", encoding="utf-8")

    result = create.read_text(encoding="utf-8")
    assert result.count(f"tag={namespace}_head_root") >= len(head_indices)
    assert all(f"tag={namespace}_{index}" in result for index in head_indices)
    return namespace, len(head_indices), len(keyframes)


def main():
    parser = argparse.ArgumentParser(description="Ajoute un pivot tête/cou à un datapack BDEngine")
    parser.add_argument("pack", type=Path)
    parser.add_argument("model", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--head-group", default="Head Rig")
    parser.add_argument("--range", type=int, default=16, dest="tracking_range")
    args = parser.parse_args()
    if args.tracking_range < 1:
        parser.error("--range doit être positif")
    output_existed = args.output.exists()
    try:
        namespace, parts, keyframes = install(args.pack, args.model, args.output, args.head_group,
                                              args.tracking_range)
    except (OSError, ValueError) as error:
        if not output_existed and args.output.exists():
            shutil.rmtree(args.output)
        parser.error(str(error))
    print(f"Pivot {namespace}: {parts} éléments de tête, {keyframes} keyframes adaptées -> {args.output}")


if __name__ == "__main__":
    main()
