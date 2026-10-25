"""Public-only, deterministic fractal generators for FrameRudiments' registry.

Static RGBA source layers: NO independent media encoder, timeline, animation,
postprocess pipeline or unsafe wallet-backup functionality. The host owns all
composition/effects/quality/export and records renderer source hashes.
"""
from __future__ import annotations

import colorsys
import hashlib
import math
import re

from PIL import Image

BRIDGE_VERSION = 'bytefables.framerudiments.layer.v1'
FAMILIES = ('julia', 'burning-ship', 'ifs-fern', 'fbm')
PALETTES = ('neon', 'pastel', 'mono')
HEX_256 = re.compile(r'[0-9a-f]{64}\Z')
BITS_8 = re.compile(r'[01]{8}\Z')
UINT64 = (1 << 64) - 1


def _splitmix(value):
    value = (value + 0x9E3779B97F4A7C15) & UINT64
    z = value
    z = ((z ^ (z >> 30)) * 0xBF58476D1CE4E5B9) & UINT64
    z = ((z ^ (z >> 27)) * 0x94D049BB133111EB) & UINT64
    return z ^ (z >> 31)


def _hsv(hue, saturation, brightness):
    r, g, b = colorsys.hsv_to_rgb(hue % 1, max(0, min(1, saturation)), max(0, min(1, brightness)))
    return (round(255 * r), round(255 * g), round(255 * b), 255)


class FractalRenderer:
    """One static public identity sprite generated entirely inside FrameRudiments.

    The first eight source bits explicitly choose opposing presentation axes.
    The full public-record digest drives pseudorandom detail/geometry. Neither
    approach guarantees 8 visually decodable bits, let alone a full hash.
    """

    def __init__(self, size, style):
        if (not isinstance(size, (tuple, list)) or len(size) != 2 or
                any(type(v) is not int or not 16 <= v <= 1024 for v in size) or
                size[0] * size[1] > 262144):
            raise ValueError('Fractal viewport must be 16..1024 px, <=262144 pixels')
        if (type(style) is not dict or set(style) != {
                'bridge_version', 'family', 'palette', 'seed_hex', 'feature_bits', 'quality'}):
            raise ValueError('Unknown or missing public fractal style field')
        if style['bridge_version'] != BRIDGE_VERSION:
            raise ValueError('Unsupported FrameRudiments bridge version')
        if style['family'] not in FAMILIES or style['palette'] not in PALETTES or style['quality'] not in ('draft', 'standard'):
            raise ValueError('Unsupported fractal family, palette or quality')
        if type(style['seed_hex']) is not str or not HEX_256.fullmatch(style['seed_hex']):
            raise ValueError('Fractal seed must be a full lowercase SHA-256 public digest')
        if type(style['feature_bits']) is not str or not BITS_8.fullmatch(style['feature_bits']):
            raise ValueError('Exactly eight public opposing feature bits required')
        self.size = tuple(size)
        self.seed = bytes.fromhex(style['seed_hex'])
        self.family = style['family']
        self.palette = style['palette']
        self.bits = style['feature_bits']
        self.quality = style['quality']
        self._key = int.from_bytes(self.seed[:8], 'big')
        self.hue = (int.from_bytes(self.seed[16:18], 'big') / 65536 + (0.48 if self.bits[6] == '1' else 0.015)) % 1
        self.saturation = 0.68 if self.bits[2] == '1' else 0.24
        self.saturation *= 0.55 if self.palette == 'pastel' else 1
        self.amp = 1.0 if self.bits[0] == '1' else 0.15
        self.brightness = 0.98 if self.bits[1] == '1' else 0.66

    def _tone(self, value, *, band=0):
        value = max(0., min(1., value))
        background = 0.2 if self.bits[1] == '0' else 0.72
        shade = background + (self.brightness - background) * value
        if self.bits[3] == '1':  # glossy, distinct specular band
            shade = min(1., shade + .18 * max(0., 1 - abs(value - .73) * 7))
        hue = self.hue + value * .2 + band * .22
        if self.palette == 'mono':
            v = round(255 * shade)
            return (v, v, v, 255)
        return _hsv(hue, self.saturation, shade)

    def _warp(self, x, y):
        # Bit 4 affects horizontal symmetry, bit 0 affects fine radial spikes.
        if self.bits[4] == '0':
            x = abs(x)
        r = math.hypot(x, y)
        angle = math.atan2(y, x)
        teeth = 5 + (self.seed[5] % 8)
        ring = 1 + self.amp * .14 * math.cos(teeth * angle + (self.seed[6] / 255.) * math.pi)
        return x * ring, y * ring

    def _escape(self):
        width, height = self.size
        # Favor known nondegenerate Julia neighbourhoods, with small seeded jitters.
        anchors = [(-.74543,.11301),(-.8,.156),(-.70176,-.3842),(-.4,.6),
                   (.285,.01),(-.7269,.1889),(-.12,-.77),(.355,.355)]
        ar, ai = anchors[self.seed[0] % len(anchors)]
        cr = ar + ((self.seed[1] / 255) - .5) * .028
        ci = ai + ((self.seed[2] / 255) - .5) * .028
        max_iter = (70 if self.quality == 'draft' else 140) + (42 if self.bits[5] == '1' else 0)
        zoom = 1.15 + (self.seed[3] / 255.) * .55
        rotation = 2 * math.pi * int.from_bytes(self.seed[10:12], 'big') / 65536
        cosr, sinr = math.cos(rotation), math.sin(rotation)
        out = Image.new('RGBA', self.size)
        pixels = out.load()
        for py in range(height):
            yy = ((py + .5) / height - .5) * 3 / zoom
            for px in range(width):
                xx = ((px + .5) / width - .5) * 3 / zoom
                wx, wy = self._warp(xx, yy)
                zx, zy = wx * cosr - wy * sinr, wx * sinr + wy * cosr
                for i in range(max_iter):
                    if self.family == 'burning-ship':
                        zx, zy = abs(zx), abs(zy)
                    nxt = zx*zx - zy*zy + cr
                    zy = 2*zx*zy + ci
                    zx = nxt
                    if zx*zx + zy*zy > 64:
                        break
                if i == max_iter - 1:
                    pixels[px,py] = self._tone(.04)
                else:
                    # Fixed deterministic expression avoids precision-dependent
                    # complex-log branches, still illustrative only (not byte-stable cross-GPU).
                    mu = (i + 1) / max_iter
                    shade = .28 + .72 * ((mu * 12 + self.seed[7] / 255.) % 1)
                    pixels[px,py] = self._tone(shade)
        return out

    def _ifs_fern(self):
        width, height = self.size
        counts = [0] * (width * height)
        count = (28000 if self.quality == 'draft' else 100000) * (2 if self.bits[5] == '1' else 1)
        state = self._key
        x, y = 0., 0.
        for k in range(count+50):
            state = _splitmix(state)
            t = (state >> 11) / float(1 << 53)
            if t < .01:
                x, y = 0, .16*y
            elif t < .86:
                x,y = (.85*x + .04*y, -.04*x + .85*y + 1.6)
            elif t < .93:
                x,y = (.2*x - .26*y, .23*x + .22*y + 1.6)
            else:
                x,y = (-.15*x + .28*y, .26*x + .24*y + .44)
            if k < 50:continue
            u = (x + 2.3) / 5.0 * width
            v = (1 - y / 10.1) * height
            if self.bits[4] == '0':u=abs(u-width/2)*2
            if self.bits[0] == '1':u+=(math.sin(y*3.6) * .08 * width)
            ix,iy=int(u),int(v)
            if 0 <= ix < width and 0 <= iy < height:
                counts[iy*width+ix]+=1
        maximum = max(counts) or 1
        scale = math.log1p(maximum)
        out = Image.new('RGBA',self.size)
        out.putdata([self._tone(math.log1p(n)/scale) for n in counts])
        return out

    def _value_noise(self, x, y, octave):
        ix, iy = math.floor(x), math.floor(y)
        fx, fy = x - ix, y - iy
        fx,fy=fx*fx*(3-2*fx),fy*fy*(3-2*fy)
        def lattice(xx, yy):
            key = (self._key ^ (xx * 0xD1B54A32D192ED03) ^
                   (yy * 0xABC98388FB8FAC03) ^ (octave * 0x8CB92BA72F3D8DD7)) & UINT64
            return (_splitmix(key) & 0xffff) / 65535
        a = lattice(ix,iy)*(1-fx) + lattice(ix+1,iy)*fx
        b = lattice(ix,iy+1)*(1-fx) + lattice(ix+1,iy+1)*fx
        return a*(1-fy)+b*fy

    def _fbm(self):
        width,height = self.size
        data=[]
        octaves=(4 if self.quality == 'draft' else 6) + (1 if self.bits[5]=='1' else 0)
        offset_x = (self.seed[11]/255.-.5)*5
        offset_y = (self.seed[12]/255.-.5)*5
        for y in range(height):
            yy=(y+.5)/height*4-2
            for x in range(width):
                xx=(x+.5)/width*4-2
                wx,wy=self._warp(xx,yy)
                if self.bits[7] == '1':wx,wy=wx+wy*.45,wy-wx*.25
                amp,freq,acc,total=1.,1.,0.,0.
                for octave in range(octaves):
                    acc+=amp*self._value_noise((wx+offset_x)*freq,(wy+offset_y)*freq,octave)
                    total+=amp
                    amp*=.52
                    freq*=2
                value = acc/total
                if self.bits[0] == '1':value = round(value*8)/8
                data.append(self._tone(value))
        out=Image.new('RGBA',self.size)
        out.putdata(data)
        return out

    def render(self, frame):
        if self.family in {'julia','burning-ship'}:return self._escape()
        if self.family == 'ifs-fern':return self._ifs_fern()
        return self._fbm()
