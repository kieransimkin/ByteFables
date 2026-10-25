"""Reusable ByteFables generator factories plugged into FrameRudiments.

Only the host may execute these trusted factories. FrameRudiments still owns
clock sampling, composite, masks, all scoped/graph effects, render quality,
Butterchurn/projectM, FFmpeg, output QA and render provenance.
No secrets; no arbitrary paths, network, code execution or dynamic imports.
"""
from __future__ import annotations

import colorsys
import hashlib
import re
from PIL import Image, ImageDraw

BRIDGE_VERSION = "bytefables.framerudiments.layer.v1"
DIGEST = re.compile(r"[0-9a-f]{64}\Z")
FORMAT_ID = re.compile(r"[a-z][a-z0-9-]*(?:/[a-z][a-z0-9-]*)+\Z")
RGB = re.compile(r"#[0-9a-fA-F]{6}\Z")


def _size(size):
    if (not isinstance(size, (tuple, list)) or len(size) != 2 or
            any(type(v) is not int or not 1 <= v <= 7680 for v in size) or
            size[0] * size[1] > 16_777_216):
        raise ValueError("Invalid FrameRudiments viewport")
    return tuple(size)


def _style(style, required, optional=()):
    if type(style) is not dict or set(style) - (set(required) | set(optional)) or any(
            key not in style for key in required):
        raise ValueError("Unknown/missing ByteFables renderer style field")
    if style.get("bridge_version") != BRIDGE_VERSION:
        raise ValueError("Unsupported ByteFables bridge version")


def _color(hex_value):
    if type(hex_value) is not str or not RGB.fullmatch(hex_value):
        raise ValueError("Expected a six-digit hex colour")
    return tuple(bytes.fromhex(hex_value[1:])) + (255,)


def _pixel_palette(seed, profile):
    if profile == "mono":
        return ((255, 255, 255, 255), (180, 180, 180, 255))
    hue = ((seed[16] << 8) | seed[17]) / 65536
    saturation = 0.7 if profile == "neon" else 0.45
    value = 0.95 if profile == "neon" else 0.92
    rgb1 = colorsys.hsv_to_rgb(hue, saturation, value)
    rgb2 = colorsys.hsv_to_rgb((hue + 0.37) % 1, saturation, value)
    return tuple(tuple(round(v * 255) for v in rgb) + (255,) for rgb in (rgb1, rgb2))


class PixelRenderer:
    """Static 5x5 mirrored seed image; all movement/effects remain in host."""

    def __init__(self, size, style):
        self.size = _size(size)
        _style(style, {"bridge_version", "digest_hex", "palette"})
        if type(style["digest_hex"]) is not str or not DIGEST.fullmatch(style["digest_hex"]):
            raise ValueError("Identity generator requires a full 256-bit public digest")
        if style["palette"] not in {"neon", "mono", "pastel"}:
            raise ValueError("Unknown ByteFables identity palette")
        self.seed = hashlib.sha256(
            b"ByteFables:framerudiments:pixel:v1\0" + bytes.fromhex(style["digest_hex"])
        ).digest()
        self.palette = _pixel_palette(self.seed, style["palette"])

    def render(self, frame):
        image = Image.new("RGBA", self.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(image)
        left = (self.size[0] - min(self.size)) // 2
        top = (self.size[1] - min(self.size)) // 2
        cell = min(self.size) / 5
        for y in range(5):
            for x in range(3):
                bit = y * 3 + x
                if not self.seed[bit >> 3] & (1 << (bit & 7)):
                    continue
                color = self.palette[(self.seed[18] >> (bit % 8)) & 1]
                for xx in ([2] if x == 2 else [x, 4 - x]):
                    x0 = left + round(xx * cell)
                    y0 = top + round(y * cell)
                    x1 = left + round((xx + 1) * cell) - 1
                    y1 = top + round((y + 1) * cell) - 1
                    draw.rectangle((x0, y0, x1, y1), fill=color)
        return image


class MatrixRenderer:
    """Pixel-perfect public module grid; external scanner must qualify exported QR."""

    def __init__(self, size, style):
        self.size = _size(size)
        _style(style, {"bridge_version", "format_id", "width", "height", "quiet_zone", "modules"})
        if type(style["format_id"]) is not str or not FORMAT_ID.fullmatch(style["format_id"]):
            raise ValueError("Invalid public module format")
        self.width, self.height, self.quiet = (
            style["width"], style["height"], style["quiet_zone"])
        if (type(self.width) is not int or type(self.height) is not int or
                not 1 <= self.width <= 256 or not 1 <= self.height <= 256 or
                self.width * self.height > 65536 or type(self.quiet) is not int or
                not 0 <= self.quiet <= 32):
            raise ValueError("Invalid module dimensions or quiet zone")
        self.modules = style["modules"]
        if (type(self.modules) is not str or len(self.modules) != self.width * self.height or
                set(self.modules) - {"0", "1"}):
            raise ValueError("Modules must be row-major binary string")
        self.cols = self.width + 2 * self.quiet
        self.rows = self.height + 2 * self.quiet
        self.pitch = min(self.size[0] // self.cols, self.size[1] // self.rows)
        if self.pitch < 1:
            raise ValueError("FrameRudiments viewport cannot fit the module grid at 1 px per cell")

    def render(self, frame):
        image = Image.new("RGBA", self.size, (255, 255, 255, 255))
        draw = ImageDraw.Draw(image)
        left = (self.size[0] - self.cols * self.pitch) // 2
        top = (self.size[1] - self.rows * self.pitch) // 2
        for y in range(self.height):
            for x in range(self.width):
                if self.modules[y * self.width + x] == "1":
                    x0 = left + (x + self.quiet) * self.pitch
                    y0 = top + (y + self.quiet) * self.pitch
                    draw.rectangle((x0, y0, x0 + self.pitch - 1, y0 + self.pitch - 1), fill=(0, 0, 0, 255))
        return image


def _coordinates(value, maximum=16384):
    if type(value) is not int or not 0 <= value <= maximum:
        raise ValueError("Vector scene coordinate must be a bounded nonnegative integer")
    return value


def _valid_primitive(p):
    if type(p) is not dict:
        raise ValueError("Invalid vector primitive")
    kind = p.get("kind")
    fields = {
        "rect": {"kind", "x", "y", "width", "height", "fill"},
        "circle": {"kind", "cx", "cy", "radius", "fill"},
        "line": {"kind", "x1", "y1", "x2", "y2", "stroke", "strokeWidth"},
        "path": {"kind", "d", "fill"},
    }.get(kind)
    if fields is None or set(p) != fields:
        raise ValueError("Invalid vector primitive fields")
    for key, value in p.items():
        if key in {"kind", "fill", "stroke", "d"}:
            continue
        _coordinates(value)
    _color(p.get("fill", p.get("stroke")))
    if kind in {"rect", "circle"} and p["width" if kind == "rect" else "radius"] < 1:
        raise ValueError("Invalid zero-size vector primitive")
    if kind == "rect" and p["height"] < 1:
        raise ValueError("Invalid zero-size vector primitive")
    if kind == "line" and p["strokeWidth"] < 1:
        raise ValueError("Invalid zero-width line")
    if kind == "path":
        d = p["d"]
        if (type(d) is not str or not 1 <= len(d) <= 4096 or
                re.fullmatch(r"[0-9.,+\-\sMLHVZ]+", d) is None):
            raise ValueError("ByteFables path uses absolute M/L/H/V/Z only")
    return p


def _draw_path(draw, text, scale_x, scale_y, colour):
    """Fill canonical absolute M/L/H/V/Z closed polygons; fail on ambiguity."""
    tokens = re.findall(r"[MLHVZ]|[+-]?(?:\d+(?:\.\d*)?|\.\d+)", text)
    if not tokens or re.sub(r"[MLHVZ]|[+-]?(?:\d+(?:\.\d*)?|\.\d+)|[\s,]", "", text):
        raise ValueError("Malformed vector path")
    i, command = 0, None
    cursor = (0, 0)
    points = []
    closed = False
    while i < len(tokens):
        token = tokens[i]
        if token in {"M", "L", "H", "V", "Z"}:
            command = token
            i += 1
        if command is None:
            raise ValueError("Unspecified path command")
        if command == "Z":
            if len(points) < 3:
                raise ValueError("Cannot close undersized path")
            draw.polygon([(round(x * scale_x), round(y * scale_y)) for x, y in points], fill=colour)
            points, command, closed = [], None, True
            continue
        arity = 2 if command in {"M", "L"} else 1
        if i + arity > len(tokens) or any(tokens[j] in {"M", "L", "H", "V", "Z"} for j in range(i, i + arity)):
            raise ValueError("Invalid path coordinate count")
        numeric = [float(t) for t in tokens[i:i + arity]]
        i += arity
        if command in {"M", "L"}:
            cursor = tuple(numeric)
        elif command == "H":
            cursor = (numeric[0], cursor[1])
        else:
            cursor = (cursor[0], numeric[0])
        if any(not 0 <= v <= 16384 for v in cursor):
            raise ValueError("Path coordinate outside bounds")
        points.append(cursor)
        if len(points) > 2048:
            raise ValueError("Too many path points")
        if command == "M":
            command = "L"
    if points or not closed:
        raise ValueError("Only closed vector paths supported")


class VectorSceneRenderer:
    """Bounded public scene IR with raster/presentation effects owned by host."""

    def __init__(self, size, style):
        self.size = _size(size)
        _style(style, {"bridge_version", "scene"})
        scene = style["scene"]
        if type(scene) is not dict or set(scene) != {"width", "height", "primitives"}:
            raise ValueError("Invalid scene description")
        self.width, self.height = _coordinates(scene["width"]), _coordinates(scene["height"])
        if (not self.width or not self.height or self.width > 8192 or self.height > 8192):
            raise ValueError("Invalid scene dimensions")
        primitives = scene["primitives"]
        if type(primitives) is not list or len(primitives) > 1000:
            raise ValueError("Too many scene primitives")
        self.primitives = [_valid_primitive(p) for p in primitives]

    def render(self, frame):
        image = Image.new("RGBA", self.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(image)
        sx, sy = self.size[0] / self.width, self.size[1] / self.height
        for p in self.primitives:
            kind = p["kind"]
            if kind == "rect":
                draw.rectangle((round(p["x"] * sx), round(p["y"] * sy),
                    round((p["x"] + p["width"]) * sx) - 1,
                    round((p["y"] + p["height"]) * sy) - 1), fill=_color(p["fill"]))
            elif kind == "circle":
                cx, cy, radius = p["cx"] * sx, p["cy"] * sy, p["radius"]
                draw.ellipse((round(cx-radius*sx), round(cy-radius*sy),
                    round(cx+radius*sx), round(cy+radius*sy)), fill=_color(p["fill"]))
            elif kind == "line":
                draw.line((round(p["x1"] * sx), round(p["y1"] * sy),
                    round(p["x2"] * sx), round(p["y2"] * sy)),
                    fill=_color(p["stroke"]), width=max(1,round(p["strokeWidth"] * (sx+sy)/2)))
            else:
                _draw_path(draw, p["d"], sx, sy, _color(p["fill"]))
        return image


def register_bytefables_renderers(registry):
    """Register reusable generators into a FrameRudiments RendererRegistry.

    The caller MUST use the same registry for FrameRudiments ``preflight`` and
    ``render``. These deliberately do not implement custom post-processing;
    the host's layer-scoped ``post_effects``, ``effect_graph`` and native
    DanceRudiments modulation remain the only effect pipelines.
    """
    from .fractals import FractalRenderer
    from .artwork import ArtworkRenderer

    for key, renderer in (
        ("bytefables-fractal-v1", FractalRenderer),
        ("bytefables-artwork-v1", ArtworkRenderer),
        ("bytefables-pixel-v1", PixelRenderer),
        ("bytefables-matrix-v1", MatrixRenderer),
        ("bytefables-scene-v1", VectorSceneRenderer),
    ):
        registry.register(key, renderer)
    return registry
