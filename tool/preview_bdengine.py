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
from matplotlib.colors import to_rgb
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


def rasterize(cuboids, camera, center, radius, size=500):
    """Orthographic software rasterizer with a real per-pixel depth buffer."""
    camera = camera / np.linalg.norm(camera)
    right = np.cross((0, 0, 1), camera)
    right /= np.linalg.norm(right)
    up = np.cross(camera, right)
    scale = size / (radius * 2.2)
    image = np.full((size, size, 3), (32, 32, 32), dtype=np.uint8)
    depth_buffer = np.full((size, size), -np.inf)
    edges = []

    def triangle(points, depths, shade):
        low = np.maximum(np.floor(points.min(axis=0)).astype(int), 0)
        high = np.minimum(np.ceil(points.max(axis=0)).astype(int), size - 1)
        if np.any(high < low):
            return
        x, y = np.meshgrid(np.arange(low[0], high[0] + 1), np.arange(low[1], high[1] + 1))
        a, b, c = points
        denominator = (b[1] - c[1]) * (a[0] - c[0]) + (c[0] - b[0]) * (a[1] - c[1])
        if abs(denominator) < 1e-9:
            return
        first = ((b[1] - c[1]) * (x - c[0]) + (c[0] - b[0]) * (y - c[1])) / denominator
        second = ((c[1] - a[1]) * (x - c[0]) + (a[0] - c[0]) * (y - c[1])) / denominator
        third = 1 - first - second
        inside = (first >= -1e-6) & (second >= -1e-6) & (third >= -1e-6)
        depth = first * depths[0] + second * depths[1] + third * depths[2]
        target = depth_buffer[low[1]:high[1] + 1, low[0]:high[0] + 1]
        visible = inside & (depth > target)
        target[visible] = depth[visible]
        image[low[1]:high[1] + 1, low[0]:high[0] + 1][visible] = shade

    for corners, shades in cuboids:
        corners = corners[:, (0, 2, 1)]
        local_center = corners.mean(axis=0)
        relative = corners - center
        screen = np.column_stack((relative @ right, -(relative @ up))) * scale + size / 2
        depths = relative @ camera
        for face, shade in zip(FACES, shades):
            polygon = corners[list(face)]
            normal = np.cross(polygon[1] - polygon[0], polygon[2] - polygon[0])
            if np.dot(normal, polygon.mean(axis=0) - local_center) < 0:
                normal = -normal
            if np.dot(normal, camera) <= 0:
                continue
            indices = list(face)
            color = np.asarray(to_rgb(shade)) * 255
            triangle(screen[indices[:3]], depths[indices[:3]], color)
            triangle(screen[[indices[0], indices[2], indices[3]]], depths[[indices[0], indices[2], indices[3]]], color)
            edges.extend((screen[a], screen[b], depths[a], depths[b])
                         for a, b in zip(indices, indices[1:] + indices[:1]))

    tolerance = radius / size * 3
    for start, end, first_depth, last_depth in edges:
        steps = max(1, int(np.max(np.abs(end - start))))
        ratio = np.linspace(0, 1, steps + 1)
        points = np.rint(start + (end - start) * ratio[:, None]).astype(int)
        depths = first_depth + (last_depth - first_depth) * ratio
        valid = ((points[:, 0] >= 0) & (points[:, 0] < size) &
                 (points[:, 1] >= 0) & (points[:, 1] < size))
        points, depths = points[valid], depths[valid]
        visible = depths >= depth_buffer[points[:, 1], points[:, 0]] - tolerance
        image[points[visible, 1], points[visible, 0]] = (40, 40, 40)
    return image


def rasterizer_self_test():
    def cube(z, shade):
        corners = np.array([[x, y, z + dz] for x in (-.5, .5) for y in (-.5, .5) for dz in (-.1, .1)])
        return corners, (shade,) * 6

    image = rasterize([cube(0, "#0000ff"), cube(-.4, "#ff0000")],
                      np.array((0, -1, 0)), np.zeros(3), 1, 32)
    assert tuple(image[16, 16]) == (255, 0, 0)


def reference_player(cuboids, horizontal=(-1, 0)):
    points = np.concatenate([corners for corners, _ in cuboids])
    low, high = points.min(axis=0), points.max(axis=0)
    direction = np.asarray(horizontal, dtype=float)
    direction /= np.linalg.norm(direction)
    ground = points[np.isclose(points[:, 1], low[1])]
    center = (ground.min(axis=0) + ground.max(axis=0)) / 2
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
        axis = figure.add_subplot(1, 5, index)
        elevation_rad, azimuth_rad = np.radians((elevation, azimuth))
        camera = np.array((np.cos(elevation_rad) * np.cos(azimuth_rad),
                           np.cos(elevation_rad) * np.sin(azimuth_rad), np.sin(elevation_rad)))
        player = reference_player(cuboids, (np.sin(azimuth_rad), -np.cos(azimuth_rad))) if player_reference else []
        if player:
            model_points = np.concatenate([corners for corners, _ in cuboids])
            player_points = np.concatenate([corners for corners, _ in player])
            model_ground = model_points[np.isclose(model_points[:, 1], model_points[:, 1].min())][:, (0, 2, 1)]
            player_ground = player_points[np.isclose(player_points[:, 1], player_points[:, 1].min())][:, (0, 2, 1)]
            ground_camera = camera * (1, 1, 0)
            ground_camera /= np.linalg.norm(ground_camera)
            shift = (model_ground @ ground_camera).max() - (player_ground @ ground_camera).max()
            for corners, _ in player:
                corners[:, 0] += ground_camera[0] * shift
                corners[:, 2] += ground_camera[1] * shift
        view_cuboids = cuboids + player
        points = np.concatenate([corners for corners, _ in view_cuboids])[:, (0, 2, 1)]
        low, high = points.min(axis=0), points.max(axis=0)
        center, radius = (low + high) / 2, (high - low).max() / 2
        axis.imshow(rasterize(view_cuboids, camera, center, radius), interpolation="lanczos")
        axis.set_title(title, color="white")
        axis.set_axis_off()
        axis.set_facecolor("#202020")
    figure.tight_layout(rect=(0, 0, 1, .94))
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
