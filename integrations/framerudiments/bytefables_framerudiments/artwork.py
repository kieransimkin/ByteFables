"""Reusable deterministic PUBLIC identity-art generators for FrameRudiments.

No off-host APIs, clocks, shaders, files, external seeds or post processing.
These render only source RGBA pixels; FrameRudiments owns animation/effects.
Not reversible and never acceptable as an identity-authentication signal.
"""
from __future__ import annotations

import colorsys
import hashlib
import math
import random
import re
from PIL import Image, ImageDraw

DOMAIN = b"ByteFables:framerudiments:artwork:v1\0"
PATTERNS = frozenset({"sigil", "constellation", "heraldry", "topography"})
PALETTES = frozenset({"neon", "pastel", "mono"})
BRIDGE = "bytefables.framerudiments.layer.v1"


def _rgb(hue, saturation, brightness, opacity=255):
    return tuple(int(round(255 * v)) for v in colorsys.hsv_to_rgb(hue % 1, saturation, brightness)) + (opacity,)


class ArtworkRenderer:
    """Deterministic synthetic identity drawing in a transparent host viewport."""

    def __init__(self, size, style):
        if (not isinstance(size, (tuple, list)) or len(size) != 2 or
                any(type(v) is not int or not 16 <= v <= 2048 for v in size) or
                size[0] * size[1] > 1024 * 1024):
            raise ValueError("Invalid ByteFables artwork size")
        self.size = tuple(size)
        if (type(style) is not dict or set(style) != {"bridge_version", "digest_hex", "style", "palette", "complexity"} or
                style.get("bridge_version") != BRIDGE or
                not isinstance(style.get("digest_hex"), str) or
                re.fullmatch(r"[0-9a-f]{64}", style["digest_hex"]) is None or
                style.get("style") not in PATTERNS or style.get("palette") not in PALETTES or
                type(style.get("complexity")) is not int or not 1 <= style["complexity"] <= 8):
            raise ValueError("Untrusted/unsupported ByteFables artwork style")
        self.family = style["style"]
        self.complexity = style["complexity"]
        self.palette = style["palette"]
        self.seed = hashlib.sha256(DOMAIN + bytes.fromhex(style["digest_hex"]) +
                                   self.family.encode("ascii")).digest()
        self.colors = self._colors()

    def _colors(self):
        hue = int.from_bytes(self.seed[:2], "big") / 65536
        if self.palette == "mono":
            return [(240, 240, 240, 255), (157, 157, 157, 255), (88, 88, 88, 255), (220, 220, 220, 255)]
        sat, v = (0.72, 0.98) if self.palette == "neon" else (0.35, 0.92)
        return [_rgb(hue + i * 0.15, sat, max(0.5, v - (i % 3) * 0.11)) for i in range(5)]

    def render(self, frame):
        rng = random.Random(int.from_bytes(self.seed, "big"))
        image = Image.new("RGBA", self.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(image)
        w, h = self.size
        cx, cy = w / 2, h / 2
        r = max(4, min(w, h) * 0.39)
        u = max(1, round(min(w, h) / 100))
        # Shared silhouette/outline anchors ensure use as compact fallback sprite.
        if self.family == "sigil":
            petals = 5 + self.seed[3] % 7
            for i in range(petals):
                a = 2 * math.pi * i / petals
                b = a + math.pi / petals
                rx = r * (0.5 + rng.random() * 0.45)
                p = [(cx + r * 0.18 * math.cos(a), cy + r * 0.18 * math.sin(a)),
                     (cx + rx * math.cos(a), cy + rx * math.sin(a)),
                     (cx + r * .43 * math.cos(b), cy + r * .43 * math.sin(b))]
                draw.polygon(p, fill=self.colors[i % len(self.colors)])
            for ring in range(1 + self.complexity // 2):
                rr = r * (0.20 + ring * .16)
                draw.ellipse((cx-rr,cy-rr,cx+rr,cy+rr), outline=self.colors[(ring+2)%len(self.colors)], width=u)
            draw.ellipse((cx-r*.12,cy-r*.12,cx+r*.12,cy+r*.12),fill=self.colors[0])
        elif self.family == "constellation":
            n = 9 + self.complexity * 3
            points = []
            for i in range(n):
                a = 2 * math.pi * rng.random()
                dist = r * math.sqrt(rng.random())
                points.append((cx + dist*math.cos(a), cy + dist*math.sin(a)))
            for i in range(n):
                a = points[i]
                nearest = sorted((j for j in range(n) if j != i),
                    key=lambda j: (points[j][0] - a[0])**2 + (points[j][1] - a[1])**2)
                for j in nearest[:1+(i % 2)]:
                    if j > i: draw.line((a, points[j]),fill=self.colors[2],width=u)
            for i,(x,y) in enumerate(points):
                d = max(1,round(min(w,h)*(0.012 + self.seed[i % 32]/255*0.017)))
                draw.ellipse((x-d,y-d,x+d,y+d),fill=self.colors[i%len(self.colors)])
        elif self.family == "heraldry":
            # Sharp polygon silhouette and wide outlines for icon readability.
            shield = [(cx-r*.75,cy-r*.85),(cx+r*.75,cy-r*.85),
                      (cx+r*.68,cy+r*.20),(cx,cy+r),(cx-r*.68,cy+r*.20)]
            draw.polygon(shield,fill=self.colors[2])
            inner = [(cx-r*.60,cy-r*.7),(cx+r*.60,cy-r*.7),
                     (cx+r*.52,cy+r*.15),(cx,cy+r*.77),(cx-r*.52,cy+r*.15)]
            draw.polygon(inner,fill=self.colors[0])
            bands = 1+self.complexity//2
            for k in range(bands):
                rr = r*(0.3 + 0.08*k)
                draw.line((cx-rr,cy-r*.38+k*u*5,cx+rr,cy-r*.38+k*u*5),fill=self.colors[(k+1)%len(self.colors)],width=u*2)
            sides=3+self.seed[4]%5
            star=[]
            for k in range(sides*2):
                a=-math.pi/2+math.pi*k/sides
                rr=r*(0.36 if k%2==0 else 0.16)
                star.append((cx+rr*math.cos(a),cy+rr*math.sin(a)+r*.24))
            draw.polygon(star,fill=self.colors[3])
        else:  # topography
            rings = 3 + self.complexity * 2
            harmonics = [(rng.randint(2,7),rng.random()*math.tau,rng.uniform(0.025,0.11)) for _ in range(3)]
            for j in range(rings,0,-1):
                rr = r*j/(rings+1)
                points=[]
                for a_i in range(0,128):
                    a=a_i*math.tau/128
                    noise=sum(math.sin(a*f + phase)*amp for f,phase,amp in harmonics)
                    radius=rr*(1+noise)
                    points.append((cx+radius*math.cos(a),cy+radius*math.sin(a)))
                points.append(points[0]);draw.line(points, fill=self.colors[j%len(self.colors)], width=max(1,u*2))
            draw.ellipse((cx-u*3,cy-u*3,cx+u*3,cy+u*3),fill=self.colors[0])
        return image
