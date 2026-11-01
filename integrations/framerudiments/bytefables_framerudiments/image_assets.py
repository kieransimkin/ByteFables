"""Lossless image export helpers for already-rendered FrameRudiments pixels.

No drawing, effects, resizing, model inference or alternate renderer. Every
encoded image is decoded again and must preserve its exact RGBA sample bytes.
"""
from __future__ import annotations

import hashlib
import io
import struct
from typing import Mapping

from PIL import Image, features, __version__ as PILLOW_VERSION

PROFILE = 'bytefables.native-image-assets.v1'
NATIVE_SIZES = (16, 32, 64, 128)
MAX_ASSET_BYTES = 2 * 1024 * 1024


class ImageAssetError(ValueError):
    """Unsupported pixel input, codec unavailable, or failed lossless readback."""


def encoder_environment() -> dict:
    return {'pillow': PILLOW_VERSION, 'libwebp': features.version('webp'),
            'profile': PROFILE, 'pngCompressLevel': 6, 'webpLossless': True,
            'webpExact': True, 'webpMethod': 6, 'webpQuality': 100,
            'icoEncoding': 'native-size PNG entries; no resampling',
            'metadata': 'stripped; untagged RGB samples; no colour conversion'}


def require_formats(formats) -> tuple[str, ...]:
    if (not isinstance(formats, (tuple, list)) or not formats or
            any(type(f) is not str for f in formats) or len(set(formats)) != len(formats) or
            set(formats) - {'png', 'webp', 'ico'} or 'png' not in formats):
        raise ImageAssetError('Select unique formats from png,webp,ico; png is required')
    if 'webp' in formats and not features.check('webp'):
        raise ImageAssetError('Lossless WebP support is unavailable; request png,ico explicitly')
    return tuple(f for f in ('png', 'webp', 'ico') if f in formats)


def clean_pixels(image: Image.Image) -> Image.Image:
    if (not isinstance(image, Image.Image) or image.mode != 'RGBA' or
            image.width != image.height or image.width not in NATIVE_SIZES):
        raise ImageAssetError('Expected native 16/32/64/128 square RGBA pixels')
    # frombytes avoids retaining EXIF, XMP, ICC, text, filenames or encoder hints.
    return Image.frombytes('RGBA', image.size, image.tobytes())


def _frames(data: bytes, format: str) -> dict[int, bytes]:
    """Decode only the selected container, never Pillow's wider format registry."""
    if type(data) is not bytes or not 1 <= len(data) <= MAX_ASSET_BYTES:
        raise ImageAssetError('Invalid image asset byte budget')
    if format not in ('png', 'webp', 'ico'):
        raise ImageAssetError('Unsupported image asset format')
    if format == 'webp':
        if (data[:4] != b'RIFF' or data[8:12] != b'WEBP' or
                int.from_bytes(data[4:8], 'little') + 8 != len(data)):
            raise ImageAssetError('Malformed WebP container or trailing data')
    if format == 'ico':
        if len(data) < 6:
            raise ImageAssetError('Truncated ICO directory')
        reserved, kind, count = struct.unpack_from('<HHH', data)
        if reserved != 0 or kind != 1 or not 1 <= count <= 4 or len(data) < 6 + count * 16:
            raise ImageAssetError('Invalid ICO directory')
        seen, offset = set(), 6 + 16 * count
        for i in range(count):
            w, h, colours, zero, planes, depth, length, start = struct.unpack_from('<BBBBHHII', data, 6 + 16*i)
            if (w != h or w not in NATIVE_SIZES or w in seen or colours or zero or
                    planes not in (0, 1) or depth != 32 or start != offset or
                    length < 57 or start + length > len(data) or
                    data[start:start+8] != b'\x89PNG\r\n\x1a\n' or
                    data[start+8:start+16] != b'\0\0\0\rIHDR' or
                    struct.unpack_from('>II', data, start+16) != (w, h)):
                raise ImageAssetError('ICO must contain distinct contiguous native-size PNG entries')
            seen.add(w)
            offset += length
        if offset != len(data):
            raise ImageAssetError('ICO has trailing or unindexed data')
    try:
        if format == 'png':
            if not data.startswith(b'\x89PNG\r\n\x1a\n') or data[-12:] != b'\0\0\0\0IEND\xaeB`\x82':
                raise ImageAssetError('Malformed PNG container or trailing data')
            with Image.open(io.BytesIO(data), formats=['PNG']) as probe:
                probe.verify()
        with Image.open(io.BytesIO(data), formats=[format.upper()]) as source:
            if source.format != format.upper() or getattr(source, 'n_frames', 1) != 1:
                raise ImageAssetError('Unexpected format or animated asset')
            if any(source.info.get(key) for key in ('exif', 'xmp', 'icc_profile')):
                raise ImageAssetError('Unexpected exported image metadata')
            sizes = source.ico.sizes() if format == 'ico' else {source.size}
            if (not 1 <= len(sizes) <= 4 or any(w != h or w not in NATIVE_SIZES for w, h in sizes)):
                raise ImageAssetError('Unexpected decoded asset size')
            if format == 'ico' and {w for w, _ in sizes} != seen:
                raise ImageAssetError('ICO directory and decoder disagree')
            result = {}
            for size in sorted(sizes):
                frame = source.ico.getimage(size) if format == 'ico' else source
                frame.load()
                rgba = frame.convert('RGBA')
                try:
                    if rgba.size != size:
                        raise ImageAssetError('Decoded asset dimensions mismatch')
                    result[size[0]] = rgba.tobytes()
                finally:
                    rgba.close()
                    # ICO PNG entries share the directory stream. Closing an
                    # entry here would close it before the next entry is read.
                    # The owning source context closes that stream below.
            return result
    except (OSError, SyntaxError, KeyError, struct.error) as exc:
        raise ImageAssetError('Image asset could not be decoded') from exc


def inspect_asset(data: bytes, format: str) -> dict:
    decoded = _frames(data, format)
    return {'format': format, 'byteLength': len(data),
            'sha256': hashlib.sha256(data).hexdigest(),
            'frames': [{'size': size, 'rgbaSha256': hashlib.sha256(pixels).hexdigest()}
                       for size, pixels in sorted(decoded.items())]}


def encode_raster(image: Image.Image, format: str) -> bytes:
    if format not in ('png', 'webp'):
        raise ImageAssetError('Raster export format must be png or webp')
    require_formats(('png', format) if format == 'webp' else ('png',))
    clean = clean_pixels(image)
    try:
        stream = io.BytesIO()
        options = ({'compress_level': 6, 'optimize': False} if format == 'png' else
                   {'lossless': True, 'exact': True, 'quality': 100, 'method': 6})
        clean.save(stream, format=format.upper(), **options)
        data = stream.getvalue()
        if _frames(data, format) != {clean.width: clean.tobytes()}:
            raise ImageAssetError('Lossless export changed RGBA pixels')
        return data
    finally:
        clean.close()


def encode_icon(images: Mapping[int, Image.Image]) -> bytes:
    if (not isinstance(images, Mapping) or not 1 <= len(images) <= 4 or
            any(type(size) is not int or size not in NATIVE_SIZES for size in images)):
        raise ImageAssetError('ICO needs supplied native images; no implicit resizing')
    clean = []
    try:
        for size, image in sorted(images.items()):
            copy = clean_pixels(image)
            clean.append(copy)
            if copy.size != (size, size):
                raise ImageAssetError('ICO size key does not match its native image')
        stream = io.BytesIO()
        clean[-1].save(stream, format='ICO', sizes=[im.size for im in clean],
                       append_images=clean[:-1], bitmap_format='png')
        data = stream.getvalue()
        if _frames(data, 'ico') != {im.width: im.tobytes() for im in clean}:
            raise ImageAssetError('ICO silently resized, lost, or changed a native image')
        return data
    finally:
        for image in clean:
            image.close()
