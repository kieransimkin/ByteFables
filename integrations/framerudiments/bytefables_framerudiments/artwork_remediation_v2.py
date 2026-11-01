"""Second-generation experimental remediation candidates.

Production ``ArtworkRenderer`` remains unchanged.  V2 keeps the successful v1
mandala/branching candidates but replaces heraldry with a coarse logical-grid
silhouette so identity-bearing bits survive at 16 px.
"""
from __future__ import annotations

import math
from PIL import ImageDraw

from .artwork_remediation import RemediationArtworkRenderer, SUPPORTED_FAMILIES

PROFILE = "bytefables.artwork-remediation-candidate.v2"


class RemediationArtworkRendererV2(RemediationArtworkRenderer):
    """Candidate v2; only heraldry differs from candidate v1."""

    def _heraldry(self, draw: ImageDraw.ImageDraw, rng, cx, cy, r, u):
        # Work in a logical 16x16 grid.  Coordinates therefore land on stable
        # coarse pixels at the smallest supported icon size instead of relying
        # on details that vanish during rasterisation.
        w, h = self.size
        sx, sy = w / 16.0, h / 16.0
        X = lambda x: x * sx
        Y = lambda y: y * sy

        seed = self.seed
        # Four top-edge grammars x three tip positions x two body widths already
        # yield 24 coarse silhouettes before side tabs/notches are considered.
        top_kind = seed[0] & 3
        tip = 6.0 + (seed[1] % 5) * 1.0  # logical x 6..10
        half = 5.0 + (seed[2] & 1) * 0.75
        left, right = 8.0 - half, 8.0 + half

        if top_kind == 0:  # flat
            top = [(left, 2.0), (right, 2.0)]
        elif top_kind == 1:  # shallow central crown
            top = [(left, 2.5), (5.8, 1.7), (8.0, 2.8), (10.2, 1.7), (right, 2.5)]
        elif top_kind == 2:  # asymmetric battlement
            if seed[3] & 1:
                top = [(left, 2.7), (5.2, 2.7), (5.2, 1.4), (7.0, 1.4), (7.0, 2.5), (right, 2.5)]
            else:
                top = [(left, 2.5), (9.0, 2.5), (9.0, 1.4), (10.8, 1.4), (10.8, 2.7), (right, 2.7)]
        else:  # deep V/cut crown with solid silhouette shoulders
            top = [(left, 2.0), (6.1, 2.0), (8.0, 3.8), (9.9, 2.0), (right, 2.0)]

        shield = top + [(right - 0.2, 8.8), (11.3, 12.2), (tip, 15.0), (4.7, 12.2), (left + 0.2, 8.8)]
        points = [(X(x), Y(y)) for x, y in shield]
        draw.polygon(points, fill=self.colors[2])

        # Four large 1.25x2.25 logical side tabs carry four more robust bits in
        # the alpha silhouette.  They are placed outside the main shield and
        # deliberately alternate vertical positions to avoid rotational aliases.
        tabs = ((1.0, 4.0), (13.75, 5.0), (1.0, 8.3), (13.75, 9.3))
        tab_mask = seed[4] | 1  # at least one tab, so the silhouette is asymmetric
        for bit, (x, y) in enumerate(tabs):
            if tab_mask & (1 << bit):
                draw.rectangle((X(x), Y(y), X(x + 1.25), Y(y + 2.25)), fill=self.colors[2])

        # One of four coarse field divisions.  All strokes are at least one full
        # logical pixel at 16px and therefore remain visible in greyscale/CVD.
        field = seed[5] & 3
        stroke = max(1, round(min(w, h) / 8))
        if field == 0:
            draw.polygon([(X(4.0),Y(4.0)),(X(5.7),Y(3.0)),(X(12.0),Y(11.2)),(X(10.4),Y(12.6))], fill=self.colors[0])
        elif field == 1:
            draw.rectangle((X(6.8),Y(3.0),X(9.2),Y(12.8)), fill=self.colors[0])
        elif field == 2:
            draw.line([(X(4.5),Y(7.0)),(X(8.0),Y(10.2)),(X(11.5),Y(7.0))], fill=self.colors[0], width=stroke, joint="curve")
        else:
            draw.rectangle((X(7.0),Y(3.3),X(9.0),Y(12.3)), fill=self.colors[0])
            draw.rectangle((X(4.5),Y(6.5),X(11.5),Y(8.5)), fill=self.colors[0])

        # Coarse emblem with digest-driven horizontal/vertical offsets.  The
        # offsets intentionally quantise to whole logical pixels at 16px.
        emblem = seed[6] % 6
        ex = 6.5 + (seed[7] % 4)  # 6.5..9.5
        ey = 8.0 + ((seed[8] % 3) - 1)  # 7..9
        rr = 2.0 + (seed[9] & 1) * 0.5
        if emblem == 0:
            draw.ellipse((X(ex-rr),Y(ey-rr),X(ex+rr),Y(ey+rr)), fill=self.colors[1])
        elif emblem == 1:
            draw.polygon([(X(ex),Y(ey-rr)),(X(ex+rr),Y(ey)),(X(ex),Y(ey+rr)),(X(ex-rr),Y(ey))], fill=self.colors[1])
        elif emblem == 2:
            draw.polygon([(X(ex),Y(ey-rr)),(X(ex+rr),Y(ey+rr)),(X(ex-rr),Y(ey+rr))], fill=self.colors[1])
        elif emblem == 3:
            draw.rectangle((X(ex-rr),Y(ey-rr),X(ex+rr),Y(ey+rr)), fill=self.colors[1])
        elif emblem == 4:
            draw.rectangle((X(ex-.65),Y(ey-rr),X(ex+.65),Y(ey+rr)), fill=self.colors[1])
            draw.rectangle((X(ex-rr),Y(ey-.65),X(ex+rr),Y(ey+.65)), fill=self.colors[1])
        else:
            # Five-point star, still broad enough to survive at 16 px.
            pts=[]
            for i in range(10):
                a=-math.pi/2+math.pi*i/5
                rad=rr if i%2==0 else rr*.46
                pts.append((X(ex+rad*math.cos(a)),Y(ey+rad*math.sin(a))))
            draw.polygon(pts, fill=self.colors[1])

        # High-contrast outline last so shape edges remain stable at tiny sizes.
        draw.line(points + [points[0]], fill=self.colors[3], width=max(1, round(min(w,h)/16)), joint="curve")
