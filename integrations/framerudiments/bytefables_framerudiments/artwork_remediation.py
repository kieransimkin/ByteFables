"""Experimental deterministic redesign candidates for weak artwork families.

This module never replaces the production ArtworkRenderer. It is an A/B research
surface used to measure whether coarser, more asymmetric geometry improves
small-icon and colour-vision distinctiveness before any production promotion.
"""
from __future__ import annotations

import hashlib
import math
import random
from PIL import Image, ImageDraw

from .artwork import ArtworkRenderer

PROFILE = "bytefables.artwork-remediation-candidate.v1"
SUPPORTED_FAMILIES = frozenset({"mandala", "heraldry", "branching"})
DOMAIN = b"ByteFables:artwork-remediation:candidate:v1\0"


class RemediationArtworkRenderer:
    """Candidate-only renderer preserving the production input contract."""

    def __init__(self, size, style):
        self.baseline = ArtworkRenderer(size, style)  # central validation stays canonical
        self.size = self.baseline.size
        self.family = self.baseline.family
        self.palette = self.baseline.palette
        self.complexity = self.baseline.complexity
        self.colors = self.baseline.colors
        self.seed = hashlib.sha256(DOMAIN + self.baseline.seed).digest()

    def render(self, frame):
        if self.family not in SUPPORTED_FAMILIES:
            return self.baseline.render(frame)
        image = Image.new("RGBA", self.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(image)
        rng = random.Random(int.from_bytes(self.seed, "big"))
        w, h = self.size
        cx, cy = w / 2, h / 2
        r = max(4.0, min(w, h) * 0.40)
        u = max(1, round(min(w, h) / 42))
        if self.family == "mandala":
            self._mandala(draw, rng, cx, cy, r, u)
        elif self.family == "heraldry":
            self._heraldry(draw, rng, cx, cy, r, u)
        else:
            self._branching(draw, rng, cx, cy, r, u)
        return image

    def _mandala(self, draw, rng, cx, cy, r, u):
        # Macro silhouette first: 4..8 broad lobes, with seed-derived radial depths.
        lobes = 4 + self.seed[0] % 5
        rotation = math.tau * self.seed[1] / 255.0
        points = []
        for i in range(lobes * 2):
            a = rotation + math.pi * i / lobes
            if i % 2 == 0:
                rr = r * (0.83 + (self.seed[(i + 5) % 32] / 255.0) * 0.16)
            else:
                rr = r * (0.44 + (self.seed[(i + 11) % 32] / 255.0) * 0.15)
            points.append((cx + rr * math.cos(a), cy + rr * math.sin(a)))
        draw.polygon(points, fill=self.colors[2])
        draw.line(points + [points[0]], fill=self.colors[0], width=max(1, u * 2), joint="curve")

        # One deliberately asymmetric notch/badge breaks rotational aliases at tiny sizes.
        notch = self.seed[2] % lobes
        a = rotation + math.tau * notch / lobes
        bx, by = cx + r * 0.73 * math.cos(a), cy + r * 0.73 * math.sin(a)
        d = max(2, int(r * 0.14))
        draw.ellipse((bx-d, by-d, bx+d, by+d), fill=(0, 0, 0, 0))

        # Large central emblem: triangle..heptagon, seed-rotated and high contrast.
        sides = 3 + self.seed[3] % 5
        rr = r * (0.25 + 0.025 * (self.complexity % 4))
        emblem = []
        er = rotation / 2 + self.seed[4] / 255.0
        for i in range(sides):
            a = er + math.tau * i / sides
            emblem.append((cx + rr * math.cos(a), cy + rr * math.sin(a)))
        draw.polygon(emblem, fill=self.colors[0])
        if self.complexity >= 4:
            inner = r * 0.12
            draw.ellipse((cx-inner, cy-inner, cx+inner, cy+inner), fill=self.colors[3])

    def _heraldry(self, draw, rng, cx, cy, r, u):
        variant = self.seed[0] % 3
        offset = (self.seed[1] / 255.0 - 0.5) * r * 0.24
        if variant == 0:
            shield = [(cx-r*.78,cy-r*.84),(cx+r*.78,cy-r*.84),(cx+r*.64,cy+r*.22),(cx+offset,cy+r),(cx-r*.64,cy+r*.22)]
        elif variant == 1:
            shield = [(cx-r*.72,cy-r*.72),(cx-r*.35,cy-r*.9),(cx+r*.35,cy-r*.9),(cx+r*.72,cy-r*.72),(cx+r*.56,cy+r*.30),(cx+offset,cy+r),(cx-r*.56,cy+r*.30)]
        else:
            shield = [(cx-r*.76,cy-r*.82),(cx+r*.76,cy-r*.82),(cx+r*.70,cy+r*.05),(cx+r*.25,cy+r*.72),(cx+offset,cy+r),(cx-r*.32,cy+r*.68),(cx-r*.70,cy+r*.05)]
        # Seeded silhouette lugs make tiny shields distinguishable by shape, not hue.
        lug_w, lug_h = r * .18, r * .22
        lug_positions = [
            (cx-r*.86, cy-r*.58), (cx+r*.68, cy-r*.58),
            (cx-r*.86, cy-r*.08), (cx+r*.68, cy-r*.08),
        ]
        for bit, (lx, ly) in enumerate(lug_positions):
            if self.seed[5] & (1 << bit):
                draw.rectangle((lx, ly, lx+lug_w, ly+lug_h), fill=self.colors[2])
        draw.polygon(shield, fill=self.colors[2])
        # Optional top V-notch further diversifies the alpha silhouette.
        if self.seed[6] & 1:
            nw=r*(.12+.06*((self.seed[7]>>1)%3));
            draw.polygon([(cx-nw,cy-r*.86),(cx,cy-r*.66),(cx+nw,cy-r*.86)],fill=(0,0,0,0))
        draw.line(shield + [shield[0]], fill=self.colors[3], width=max(1, u * 2), joint="curve")

        field = self.seed[2] % 4
        if field == 0:  # diagonal sash
            draw.polygon([(cx-r*.62,cy-r*.65),(cx-r*.38,cy-r*.78),(cx+r*.55,cy+r*.48),(cx+r*.30,cy+r*.64)], fill=self.colors[0])
        elif field == 1:  # vertical split
            draw.polygon([(cx-r*.58,cy-r*.66),(cx,cy-r*.72),(cx+offset*.35,cy+r*.78),(cx-r*.48,cy+r*.20)], fill=self.colors[0])
        elif field == 2:  # broad chevron
            draw.line([(cx-r*.50,cy-r*.08),(cx,cy+r*.34),(cx+r*.50,cy-r*.08)], fill=self.colors[0], width=max(2, u*4), joint="curve")
        else:  # cross
            draw.rectangle((cx-r*.12,cy-r*.62,cx+r*.12,cy+r*.58),fill=self.colors[0])
            draw.rectangle((cx-r*.48,cy-r*.18,cx+r*.48,cy+r*.08),fill=self.colors[0])

        emblem = self.seed[3] % 5
        ex, ey = cx + offset * .25, cy + r * .16
        rr = r * .25
        if emblem == 0:
            draw.ellipse((ex-rr,ey-rr,ex+rr,ey+rr),fill=self.colors[1])
        elif emblem == 1:
            draw.polygon([(ex,ey-rr),(ex+rr,ey),(ex,ey+rr),(ex-rr,ey)],fill=self.colors[1])
        elif emblem == 2:
            draw.polygon([(ex,ey-rr),(ex+rr*.86,ey+rr*.62),(ex-rr*.86,ey+rr*.62)],fill=self.colors[1])
        elif emblem == 3:
            pts=[]
            for i in range(10):
                a=-math.pi/2+math.pi*i/5; rad=rr if i%2==0 else rr*.42
                pts.append((ex+rad*math.cos(a),ey+rad*math.sin(a)))
            draw.polygon(pts,fill=self.colors[1])
        else:
            draw.rectangle((ex-rr*.70,ey-rr*.70,ex+rr*.70,ey+rr*.70),fill=self.colors[1])
            draw.ellipse((ex-rr*.30,ey-rr*.30,ex+rr*.30,ey+rr*.30),fill=self.colors[3])

    def _branching(self, draw, rng, cx, cy, r, u):
        origin_x = cx + (self.seed[0] / 255.0 - 0.5) * r * 0.32
        origin_y = cy + r * 0.92
        primary = 2 + self.seed[1] % 3
        depth = 2 + min(3, self.complexity // 2)
        spread = math.radians(28 + self.seed[2] % 38)
        base = r * (0.50 + (self.seed[3] / 255.0) * 0.12)
        # Seed-derived root bar gives a strong low-frequency anchor.
        root_half = r * (0.18 + (self.seed[4] / 255.0) * 0.18)
        draw.line((origin_x-root_half,origin_y,origin_x+root_half,origin_y),fill=self.colors[3],width=max(2,u*3))

        def branch(x, y, angle, length, level, token):
            bend = (self.seed[token % 32] / 255.0 - 0.5) * 0.28
            a = angle + bend
            nx, ny = x + length * math.cos(a), y + length * math.sin(a)
            width = max(1, int(u * (depth - level + 2) / 1.7))
            draw.line((x,y,nx,ny),fill=self.colors[(level+token)%len(self.colors)],width=width)
            if level >= depth:
                d=max(1,int(r*(0.035 + (self.seed[(token+7)%32]/255.0)*0.025)))
                draw.ellipse((nx-d,ny-d,nx+d,ny+d),fill=self.colors[(token+1)%len(self.colors)])
                return
            left_scale = 0.58 + (self.seed[(token+3)%32]/255.0)*0.18
            right_scale = 0.58 + (self.seed[(token+9)%32]/255.0)*0.18
            branch(nx,ny,a-spread*(0.72+0.10*level),length*left_scale,level+1,token+5)
            # Seed bit deliberately makes some silhouettes one-sided at deeper levels.
            if level < 2 or self.seed[(token+13)%32] & 1:
                branch(nx,ny,a+spread*(0.72+0.10*level),length*right_scale,level+1,token+11)

        for arm in range(primary):
            if primary == 1: frac = 0.0
            else: frac = (arm/(primary-1)-0.5)
            angle = -math.pi/2 + frac * spread * 1.15
            scale = 0.82 + (self.seed[(arm+5)%32]/255.0)*0.25
            branch(origin_x,origin_y,angle,base*scale,0,17+arm*7)
