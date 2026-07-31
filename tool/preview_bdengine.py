"""Render a quick local preview of a .bdengine model."""

import base64
import gzip
import io
import json
import struct
import sys
import urllib.request
from functools import lru_cache
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
from PIL import Image


def loads(data):
    try:
        if data[:2] == b"\x1f\x8b":
            raw = gzip.decompress(data)
            name_length = struct.unpack_from("<H", raw, 9)[0]
            offset = 11 + name_length
            size = struct.unpack_from("<I", raw, offset)[0]
            scene = json.loads(raw[offset + 4:offset + 4 + size])
        else:
            scene = json.loads(gzip.decompress(base64.b64decode(data)))
        if not isinstance(scene, list) or not scene or not isinstance(scene[0], dict):
            raise ValueError
        return scene[0]
    except (ValueError, OSError, struct.error, json.JSONDecodeError) as error:
        raise ValueError("Fichier .bdengine invalide") from error


def load(path):
    return loads(Path(path).read_bytes())


def mean_color(image):
    opaque = image[:, :, :3][image[:, :, 3] > 0]
    return tuple(channel / 255 for channel in opaque.mean(axis=0))


@lru_cache(maxsize=128)
def encoded_face_colors(encoded):
    image = np.asarray(Image.open(io.BytesIO(base64.b64decode(encoded))).convert("RGBA"))
    if image.shape[:2] == (64, 64):
        regions = ((16, 8), (0, 8), (16, 0), (8, 0), (8, 8), (24, 8))
        return tuple(mean_color(image[y:y + 8, x:x + 8]) for x, y in regions)
    return (mean_color(image),) * 6


@lru_cache(maxsize=128)
def url_texture(url):
    cache = Path(__file__).resolve().parent.parent / ".cache" / "minecraft_textures" / url.rsplit("/", 1)[-1]
    if not cache.exists():
        with urllib.request.urlopen(url.replace("http://", "https://"), timeout=5) as response:
            data = response.read()
        cache.parent.mkdir(parents=True, exist_ok=True)
        cache.write_bytes(data)
    return cache.read_bytes()


@lru_cache(maxsize=128)
def url_face_colors(url):
    image = np.asarray(Image.open(io.BytesIO(url_texture(url))).convert("RGBA"))
    regions = ((16, 8), (0, 8), (16, 0), (8, 0), (8, 8), (24, 8))
    return tuple(mean_color(image[y:y + 8, x:x + 8]) for x, y in regions)


def color(node, textures=()):
    block_colors = {
        "yellow_terracotta": "#BA8524", "yellow_concrete": "#F0AF15", "yellow_wool": "#E8B735",
        "terracotta": "#985E43", "orange_terracotta": "#A95425",
        "gray_wool": "#474F52", "light_gray_wool": "#9D9D97",
        "white_concrete": "#CFD5D6", "green_concrete": "#495B24", "black_concrete": "#080A0F",
        "red_wool": "#A12722", "red_terracotta": "#8E3C2E", "red_concrete": "#8E2020",
        "blue_wool": "#35399D", "light_blue_wool": "#3A8EBA",
        "brown_wool": "#724728", "brown_concrete": "#603B1F", "iron_block": "#D8D8D8",
    }
    if node.get("isBlockDisplay"):
        return block_colors.get(node["name"].split("[")[0], "#888888")
    texture = node.get("paintTexture")
    if isinstance(texture, int) and texture < len(textures):
        texture = textures[texture]
    encoded = (texture or "").partition(",")[2]
    if not encoded:
        try:
            payload = json.loads(base64.b64decode(node.get("defaultTextureValue", "")))
            return url_face_colors(payload["textures"]["SKIN"]["url"])[4]
        except Exception:
            return "#888888"
    return encoded_face_colors(encoded)[4]


def face_colors(node, textures=()):
    texture = node.get("paintTexture")
    if isinstance(texture, int) and texture < len(textures):
        texture = textures[texture]
    encoded = (texture or "").partition(",")[2]
    if encoded:
        return encoded_face_colors(encoded)
    if node.get("defaultTextureValue") and not node.get("paintTexture"):
        try:
            payload = json.loads(base64.b64decode(node["defaultTextureValue"]))
            return url_face_colors(payload["textures"]["SKIN"]["url"])
        except Exception:
            pass
    return (color(node, textures),) * 6


def boxes(root):
    result = []
    textures = root.get("refs", {}).get("paintTextures", [])
    stack = [(root, np.eye(4))]
    while stack:
        node, parent = stack.pop()
        matrix = parent @ np.asarray(node.get("transforms", np.eye(4)), dtype=float).reshape(4, 4)
        if node.get("isItemDisplay") or node.get("isBlockDisplay"):
            if node.get("isBlockDisplay"):
                corners = np.array([[x, y, z, 1] for x in (0, 1) for y in (0, 1) for z in (0, 1)])
            else:
                # A player head is 0.5 blocks wide and hangs below its transform origin.
                corners = np.array([[x, y, z, 1] for x in (-.25, .25) for y in (-.5, 0) for z in (-.25, .25)])
            result.append(((matrix @ corners.T).T[:, :3], face_colors(node, textures)))
        stack.extend((child, matrix) for child in node.get("children", []))
    return result


FACES = ((0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1),
         (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3))


def reference_player(cuboids, horizontal=(-1, 0)):
    points = np.concatenate([corners for corners, _ in cuboids])
    low, high = points.min(axis=0), points.max(axis=0)
    direction = np.asarray(horizontal, dtype=float)
    direction /= np.linalg.norm(direction)
    center = (low + high) / 2
    distance = max(high[0] - low[0], high[2] - low[2]) / 2 + .8
    origin = np.array((center[0] + direction[0] * distance, low[1], center[2] + direction[1] * distance))

    def part(center, size, shade):
        center = origin + np.asarray(center)
        half = np.asarray(size) / 2
        corners = np.array([center + (x, y, z) * half for x in (-1, 1) for y in (-1, 1) for z in (-1, 1)])
        return corners, (shade,) * 6

    return [
        part((-.14, .35, 0), (.25, .70, .25), "#555955"),
        part((.14, .35, 0), (.25, .70, .25), "#555955"),
        part((0, 1.05, 0), (.60, .70, .30), "#555955"),
        part((-.40, 1.05, 0), (.20, .70, .25), "#555955"),
        part((.40, 1.05, 0), (.20, .70, .25), "#555955"),
        part((0, 1.55, 0), (.50, .50, .50), "#555955"),
    ]


def render(source, output, dpi=180, player_reference=False):
    cuboids = boxes(load(source))

    figure = plt.figure(figsize=(19, 5), facecolor="#202020")
    for index, (title, elevation, azimuth) in enumerate((
        ("Front", 8, -90), ("Three-quarter front", 18, -55),
        ("Profile", 8, 0), ("Three-quarter back", 18, 55), ("Back", 8, 90),
    ), 1):
        axis = figure.add_subplot(1, 5, index, projection="3d")
        polygons, colors = [], []
        elevation_rad, azimuth_rad = np.radians((elevation, azimuth))
        view_cuboids = cuboids + (reference_player(
            cuboids, (np.sin(azimuth_rad), -np.cos(azimuth_rad))
        ) if player_reference else [])
        points = np.concatenate([corners for corners, _ in view_cuboids])[:, (0, 2, 1)]
        low, high = points.min(axis=0), points.max(axis=0)
        center, radius = (low + high) / 2, (high - low).max() / 2
        camera = np.array((np.cos(elevation_rad) * np.cos(azimuth_rad),
                           np.cos(elevation_rad) * np.sin(azimuth_rad), np.sin(elevation_rad)))
        for corners, shades in view_cuboids:
            corners = corners[:, (0, 2, 1)]
            cuboid_center = corners.mean(axis=0)
            for face, shade in zip(FACES, shades):
                polygon = np.array([corners[i] for i in face])
                normal = np.cross(polygon[1] - polygon[0], polygon[2] - polygon[0])
                if np.dot(normal, polygon.mean(axis=0) - cuboid_center) < 0:
                    normal = -normal
                if np.dot(normal, camera) > 0:
                    polygons.append(polygon)
                    colors.append(shade)
        # A single collection lets Matplotlib depth-sort every face together;
        # separate cuboid collections caused rear voxels to cover faces and eyes.
        axis.add_collection3d(Poly3DCollection(
            polygons, facecolors=colors, edgecolor="#282828", linewidth=.25, zsort="average",
        ))
        axis.set_xlim(center[0] - radius, center[0] + radius)
        axis.set_ylim(center[1] - radius, center[1] + radius)
        axis.set_zlim(center[2] - radius, center[2] + radius)
        axis.set_box_aspect((1, 1, 1))
        axis.view_init(elevation, azimuth)
        axis.set_title(title, color="white")
        axis.set_axis_off()
        axis.set_facecolor("#202020")
    figure.tight_layout()
    figure.savefig(output, dpi=dpi, facecolor=figure.get_facecolor())
    plt.close(figure)


if __name__ == "__main__":
    root = Path(__file__).resolve().parent.parent
    source = Path(sys.argv[1] if len(sys.argv) > 1 else root / "bdengine" / "characters" / "references" / "farmer.bdengine")
    resolved = source.resolve()
    try:
        category = resolved.relative_to(root / "bdengine").parent
    except ValueError:
        category = Path("examples") if "examples" in resolved.parts else Path("misc")
    output = root / "previews" / category / (source.stem + "_preview.png")
    output.parent.mkdir(parents=True, exist_ok=True)
    render(source, output)
    print(output)
