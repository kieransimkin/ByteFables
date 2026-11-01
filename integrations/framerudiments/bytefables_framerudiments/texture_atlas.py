"""Lossless packing of existing native artwork; never generates or resizes art.

v1 has explicit integer rectangles, edge-extruded gutters, and no mipmaps.
Packing/export belongs to the FrameRudiments integration, not a new renderer.
"""
from __future__ import annotations

import hashlib
import io
import math
from PIL import Image

PROFILE = 'bytefables.texture-layout.v1'
SIZES = (16, 32, 64, 128)
MAX_PIXELS = 64 * 1024 * 1024
MAX_PAGE_BYTES = 64 * 1024 * 1024


class TextureAtlasError(ValueError):
    pass


def _integer(value: int, low: int, high: int, label: str) -> int:
    if type(value) is not int or not low <= value <= high:
        raise TextureAtlasError(f'Invalid {label}')
    return value


def layout(count: int, size: int, page_size: int = 1024, padding: int = 2) -> dict:
    _integer(count, 1, 8192, 'sprite count')
    _integer(size, 16, 128, 'native size')
    _integer(page_size, 64, 4096, 'page size')
    _integer(padding, 1, 16, 'padding')
    if size not in SIZES or page_size & (page_size - 1):
        raise TextureAtlasError('Unsupported native size or non-power-of-two page')
    pitch = size + 2 * padding
    columns = page_size // pitch
    if not columns:
        raise TextureAtlasError('Page cannot fit a padded sprite')
    capacity = columns * columns
    pages = math.ceil(count / capacity)
    if pages > 128 or pages * page_size * page_size > MAX_PIXELS:
        raise TextureAtlasError('Texture pixel/page budget exceeded')
    slots = []
    for index in range(count):
        cell = index % capacity
        x, y = cell % columns * pitch + padding, cell // columns * pitch + padding
        slots.append({'pageIndex': index // capacity, 'rect': [x, y, x + size, y + size],
                      'uvTopLeft': [x / page_size, y / page_size,
                                    (x + size) / page_size, (y + size) / page_size],
                      'uvBottomLeft': [x / page_size, 1 - (y + size) / page_size,
                                       (x + size) / page_size, 1 - y / page_size]})
    return {'pageCount': pages, 'capacity': capacity, 'slots': slots}


def extrude(image: Image.Image, padding: int) -> Image.Image:
    """Duplicate edge pixels into a gutter. The original interior is unchanged."""
    _integer(padding, 1, 16, 'padding')
    if not isinstance(image, Image.Image) or image.mode != 'RGBA' or image.size not in [(s, s) for s in SIZES]:
        raise TextureAtlasError('Expected native-size RGBA sprite')
    n = image.width
    result = Image.new('RGBA', (n + 2 * padding, n + 2 * padding))
    result.paste(image, (padding, padding))
    edges = [((0, 0, n, 1), (n, padding), (padding, 0)),
             ((0, n - 1, n, n), (n, padding), (padding, n + padding)),
             ((0, 0, 1, n), (padding, n), (0, padding)),
             ((n - 1, 0, n, n), (padding, n), (n + padding, padding))]
    for box, extent, position in edges:
        with image.crop(box) as edge:
            with edge.resize(extent, Image.Resampling.NEAREST) as repeated:
                result.paste(repeated, position)
    for sx, sy, dx, dy in [(0, 0, 0, 0), (n - 1, 0, n + padding, 0),
                           (0, n - 1, 0, n + padding), (n - 1, n - 1, n + padding, n + padding)]:
        result.paste(image.getpixel((sx, sy)), (dx, dy, dx + padding, dy + padding))
    return result


def decode_page(data: bytes, page_size: int) -> Image.Image:
    _integer(page_size, 64, 4096, 'page size')
    if not isinstance(data, bytes) or not 57 <= len(data) <= min(MAX_PAGE_BYTES, page_size * page_size * 5 + 65536):
        raise TextureAtlasError('Invalid texture PNG size')
    if (data[:16] != b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR' or
            data[-12:] != b'\x00\x00\x00\x00IEND\xaeB`\x82'):
        raise TextureAtlasError('Invalid texture PNG container')
    try:
        with Image.open(io.BytesIO(data), formats=['PNG']) as source:
            if (source.size != (page_size, page_size) or source.mode != 'RGBA' or
                    getattr(source, 'n_frames', 1) != 1 or source.info):
                raise TextureAtlasError('Unexpected texture dimensions, mode, frames or metadata')
            source.verify()  # CRC/structure first, then a fresh decoder for pixels.
        with Image.open(io.BytesIO(data), formats=['PNG']) as source:
            source.load()
            return source.copy()
    except (OSError, SyntaxError) as exc:
        raise TextureAtlasError('Texture PNG decode failed') from exc


def encode_page(image: Image.Image) -> bytes:
    if (not isinstance(image, Image.Image) or image.mode != 'RGBA' or
            image.width != image.height or image.width & (image.width - 1)):
        raise TextureAtlasError('Expected square power-of-two RGBA texture')
    _integer(image.width, 64, 4096, 'page size')
    with Image.frombytes('RGBA', image.size, image.tobytes()) as clean:
        stream = io.BytesIO()
        clean.save(stream, format='PNG', compress_level=6, optimize=False)
        data = stream.getvalue()
        with decode_page(data, image.width) as decoded:
            if decoded.tobytes() != clean.tobytes():
                raise TextureAtlasError('Saved texture pixels changed')
        return data


def verify_page(image: Image.Image, sprites: list[dict], padding: int) -> None:
    """Check every interior, gutter and unused pixel, including hidden RGB."""
    _integer(padding, 1, 16, 'padding')
    if image.mode != 'RGBA':
        raise TextureAtlasError('Texture must be RGBA')
    with Image.new('RGBA', image.size) as reconstructed:
        for sprite in sprites:
            x0, y0, x1, y1 = sprite['rect']
            with image.crop((x0, y0, x1, y1)) as tile:
                if hashlib.sha256(tile.tobytes()).hexdigest() != sprite['rgbaSha256']:
                    raise TextureAtlasError('Texture tile pixel checksum mismatch')
                with tile.getchannel('A') as alpha:
                    if alpha.getextrema() != (255, 255):
                        raise TextureAtlasError('v1 source sprites must retain their opaque native matte')
                with extrude(tile, padding) as padded:
                    reconstructed.paste(padded, (x0 - padding, y0 - padding))
        if image.tobytes() != reconstructed.tobytes():
            raise TextureAtlasError('Texture gutter or unused pixels differ from canonical packing')
