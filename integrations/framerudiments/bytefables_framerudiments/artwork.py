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
PATTERNS = frozenset({"sigil", "constellation", "heraldry", "topography",
                      "crystal", "mandala", "cellular", "branching", "orbital"})
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
        elif self.family == "topography":
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
        elif self.family == "crystal":
            # Facet fan anchored on a stable silhouette; pure geometry, no model.
            vertex_count = 5 + self.seed[2] % 5
            ring = []
            for i in range(vertex_count):
                a = math.tau * i / vertex_count - math.pi / 2
                dist = r * (0.75 + 0.24 * rng.random())
                ring.append((cx + dist * math.cos(a), cy + dist * math.sin(a)))
            draw.polygon(ring, fill=self.colors[2])
            focus = (cx + (self.seed[5] / 255 - 0.5) * r * 0.35,
                     cy + (self.seed[6] / 255 - 0.5) * r * 0.35)
            for i in range(vertex_count):
                draw.polygon((focus, ring[i], ring[(i+1) % vertex_count]),
                             fill=self.colors[(i + self.seed[7]) % len(self.colors)])
            for i in range(vertex_count):
                draw.line((focus, ring[i]), fill=self.colors[3], width=u)
            for i in range(self.complexity):
                ax, ay = ring[i % vertex_count]
                bx, by = ring[(i+2) % vertex_count]
                f = 0.2 + i * 0.06
                draw.line((ax * (1-f) + focus[0] * f, ay * (1-f) + focus[1] * f,
                           bx * (1-f) + focus[0] * f, by * (1-f) + focus[1] * f),
                          fill=self.colors[1], width=u)
        elif self.family == "mandala":
            petals = 6 + self.seed[6] % 11
            rings = 1 + self.complexity // 2
            for layer in range(rings, 0, -1):
                rr = r * layer / (rings + 1)
                for i in range(petals):
                    a = math.tau * i / petals
                    b = math.tau * (i + 0.46) / petals
                    c = math.tau * (i + 0.92) / petals
                    path = [(cx+rr*0.25*math.cos(a), cy+rr*0.25*math.sin(a)),
                            (cx+rr*1.16*math.cos(b), cy+rr*1.16*math.sin(b)),
                            (cx+rr*0.25*math.cos(c), cy+rr*0.25*math.sin(c))]
                    draw.polygon(path, fill=self.colors[(i + layer) % len(self.colors)])
            draw.ellipse((cx-r*.15,cy-r*.15,cx+r*.15,cy+r*.15), fill=self.colors[0])
        elif self.family == "cellular":
            # Hash-seeded Conway cellular automaton. Cell count is bounded.
            n = 11 + self.complexity * 2
            cells = [[rng.random() > 0.61 for _ in range(n)] for _ in range(n)]
            for _ in range(1 + self.complexity // 2):
                neighbors = lambda x, y: sum(cells[(y+dy)%n][(x+dx)%n]
                    for dy in (-1, 0, 1) for dx in (-1, 0, 1) if dx or dy)
                cells = [[neighbors(x, y) == 3 or (cells[y][x] and neighbors(x,y) == 2)
                          for x in range(n)] for y in range(n)]
            side = min(w, h) * 0.82
            pitch = side / n
            x0, y0 = cx - side / 2, cy - side / 2
            visible = 0
            for y in range(n):
                for x in range(n):
                    if cells[y][x]:
                        visible += 1
                        draw.rectangle((x0+x*pitch,y0+y*pitch,x0+(x+1)*pitch-1,
                                        y0+(y+1)*pitch-1), fill=self.colors[(x+y)%len(self.colors)])
            if not visible:
                draw.rectangle((cx-u*3,cy-u*3,cx+u*3,cy+u*3),fill=self.colors[0])
        elif self.family == "branching":
            # Bounded binary branching tree, each branch coloured deterministically.
            depth = min(8, 3 + self.complexity // 2)
            angle = math.radians(17 + self.seed[3] % 28)
            branches = [(cx,cy+r*0.92,-math.pi/2,r*0.47,0)]
            while branches:
                x,y,a,length,level = branches.pop()
                nx = x + length*math.cos(a)
                ny = y + length*math.sin(a)
                draw.line((x,y,nx,ny),fill=self.colors[level%len(self.colors)],
                          width=max(1,int(u*(depth-level+1)/2)))
                if level < depth:
                    twist = (self.seed[(level+5)%len(self.seed)]/255-0.5)*0.18
                    branches.append((nx,ny,a+angle+twist,length*0.73,level+1))
                    branches.append((nx,ny,a-angle+twist,length*0.73,level+1))
        elif self.family == "orbital":
            count=2+self.complexity//2
            for i in range(count):
                rx = r*(0.35+i*0.15)
                ry = rx*(0.65+0.22*rng.random())
                colour=self.colors[i % len(self.colors)]
                angle=(self.seed[(i+10)%32]/255-0.5)*1.5
                orbit=[]
                for j in range(100):
                    t=math.tau*j/99
                    orbit.append((cx+rx*math.cos(t)*math.cos(angle)-ry*math.sin(t)*math.sin(angle),
                                  cy+rx*math.cos(t)*math.sin(angle)+ry*math.sin(t)*math.cos(angle)))
                draw.line(orbit,fill=colour,width=max(1,u))
                theta=math.tau*rng.random()
                px=cx+rx*math.cos(theta)*math.cos(angle)-ry*math.sin(theta)*math.sin(angle)
                py=cy+rx*math.cos(theta)*math.sin(angle)+ry*math.sin(theta)*math.cos(angle)
                radius=max(2,u*(2+i%3))
                draw.ellipse((px-radius,py-radius,px+radius,py+radius), fill=self.colors[(i+2)%len(self.colors)])
            draw.ellipse((cx-r*.13,cy-r*.13,cx+r*.13,cy+r*.13),fill=self.colors[0])
        return image
