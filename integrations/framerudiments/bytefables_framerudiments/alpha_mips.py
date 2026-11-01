"""Versioned, isolated sprite mip packaging; never a procedural renderer.

All levels are area averages of the ORIGINAL straight RGBA bytes. RGB is
alpha-weighted before averaging; transparent hidden colour cannot leak into
visible samples. Arithmetic is integer round-half-up in stored sample space,
NOT linear-light filtering, a colour-profile transform, or alpha-test coverage
preservation. The original lossless PNG remains authoritative source evidence.
"""
from __future__ import annotations

from PIL import Image

PROFILE = 'bytefables.premultiplied-area-mips.v1'
NATIVE_SIZES = (16, 32, 64, 128)


def mip_chain(image: Image.Image) -> tuple[bytes, ...]:
    """Top-left row-major, premultiplied RGBA8 levels, including size 1x1.

    For N source pixels: A=round(sum(a)/N), RGB=round(sum(c*a)/(255*N)).
    Compute each level directly from source sums, not rounded prior levels.
    """
    if (not isinstance(image, Image.Image) or image.mode != 'RGBA' or
            image.width != image.height or image.width not in NATIVE_SIZES):
        raise ValueError('Mip input must be square native 16/32/64/128px RGBA')
    side = image.width
    raw = image.tobytes()
    # Unrounded sums (R*A,G*A,B*A,A) permit exact repeated 2x2 aggregation.
    sums = [(raw[i]*raw[i+3], raw[i+1]*raw[i+3], raw[i+2]*raw[i+3], raw[i+3])
            for i in range(0, len(raw), 4)]
    levels, count = [], 1
    while True:
        out = bytearray(side*side*4)
        denominator = 255*count
        for i, (r, g, b, a) in enumerate(sums):
            out[i*4:i*4+4] = bytes(((r+denominator//2)//denominator,
                                      (g+denominator//2)//denominator,
                                      (b+denominator//2)//denominator,
                                      (a+count//2)//count))
        levels.append(bytes(out))
        if side == 1:
            return tuple(levels)
        reduced = []
        for y in range(0, side, 2):
            for x in range(0, side, 2):
                indices = (y*side+x, y*side+x+1, (y+1)*side+x, (y+1)*side+x+1)
                reduced.append(tuple(sum(sums[k][channel] for k in indices) for channel in range(4)))
        sums, side, count = reduced, side//2, count*4


def validate_premultiplied(data: bytes) -> None:
    if not isinstance(data, bytes) or len(data) % 4:
        raise ValueError('Expected complete RGBA8 pixels')
    if any(max(data[i:i+3]) > data[i+3] for i in range(0, len(data), 4)):
        raise ValueError('Invalid premultiplied pixel: RGB exceeds alpha')
