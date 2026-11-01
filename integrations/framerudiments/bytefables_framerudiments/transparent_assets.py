"""Exact source-RGBA export for the existing registered artwork generator.

This does not infer transparency from a flattened image or implement a renderer.
No post effects, interpolation, colour conversion or alpha premultiplication.
"""
from __future__ import annotations

import hashlib
import inspect
from pathlib import Path
from PIL import Image

from .artwork import ArtworkRenderer
from .image_assets import NATIVE_SIZES, ImageAssetError, clean_pixels

PROFILE = 'bytefables.transparent-artwork-source.v1'


def generator_sha256() -> str:
    return hashlib.sha256(Path(inspect.getfile(ArtworkRenderer)).read_bytes()).hexdigest()


def source_rgba(size: int, style: dict) -> Image.Image:
    """Call the unchanged FrameRudiments plugin source, before any matte exists."""
    if type(size) is not int or size not in NATIVE_SIZES:
        raise ImageAssetError('Unsupported transparent native size')
    renderer = ArtworkRenderer((size, size), style)
    with renderer.render(None) as first, renderer.render(None) as second:
        if first.mode != 'RGBA' or first.size != (size, size) or first.tobytes() != second.tobytes():
            raise ImageAssetError('Source RGBA generator is not byte-repeatable')
        return clean_pixels(first)


def alpha_statistics(image: Image.Image) -> dict:
    with clean_pixels(image) as copy, copy.getchannel('A') as alpha:
        histogram = alpha.histogram()
        total = image.width * image.height
        return {'transparentPixels': histogram[0], 'partialPixels': sum(histogram[1:255]),
                'opaquePixels': histogram[255], 'totalPixels': total,
                'alphaSha256': hashlib.sha256(alpha.tobytes()).hexdigest()}


def composite_rgb(image: Image.Image, matte: tuple[int, int, int]) -> Image.Image:
    """Reference alpha-over in the host's stored-sample Pillow convention.

    NOT a linear-light/colour-managed rendering claim. PNG stores straight alpha.
    The returned reference must never be confused with a native-host frame.
    """
    if (type(matte) is not tuple or len(matte) != 3 or
            any(type(n) is not int or not 0 <= n <= 255 for n in matte)):
        raise ImageAssetError('Matte must be three byte channels')
    with clean_pixels(image) as copy, Image.new('RGBA', image.size, matte + (255,)) as background:
        background.alpha_composite(copy)
        return background.convert('RGB')
