"""Strict, uncompressed KTX2 transport for the v1 premultiplied array profile.

This is a bounded profile codec, NOT a general KTX2 decoder. No compression,
colour conversion, mip generation, file access or dynamic code execution.
"""
from __future__ import annotations

from dataclasses import dataclass
import struct

from .alpha_mips import NATIVE_SIZES, validate_premultiplied

PROFILE = 'bytefables.ktx2-rgba8-array.v1'
IDENTIFIER = b'\xabKTX 20\xbb\r\n\x1a\n'
VK_FORMAT = 37  # VK_FORMAT_R8G8B8A8_UNORM; NOT sRGB hardware conversion.
MAX_BYTES = 32 * 1024 * 1024


def _dfd() -> bytes:
    # Basic descriptor: Khronos vendor/type 0, version 2, 88-byte block;
    # RGBSDA, unspecified primaries, identity transfer, PREMULTIPLIED flag.
    data = struct.pack('<IIHH4B4B8B', 92, 0, 2, 88, 1, 0, 1, 1,
                       0, 0, 0, 0, 4, 0, 0, 0, 0, 0, 0, 0)
    for offset, channel in ((0, 0), (8, 1), (16, 2), (24, 15)):
        data += struct.pack('<HBB4BII', offset, 7, channel, 0, 0, 0, 0, 0, 255)
    return data


def _kvd() -> bytes:
    result = b''
    for key, value in ((b'KTXorientation', b'rd'), (b'KTXwriter', b'ByteFables KTX2 transport v1'),
                       (b'org.bytefables.profile', PROFILE.encode('ascii'))):
        entry = key + b'\0' + value + b'\0'
        result += struct.pack('<I', len(entry)) + entry + b'\0' * (-len(entry) % 4)
    return result


DFD = _dfd()
KVD = _kvd()


def _geometry(size: int, layers: int) -> tuple[int, ...]:
    if type(size) is not int or size not in NATIVE_SIZES or type(layers) is not int or not 1 <= layers <= 256:
        raise ValueError('KTX2 requires native square 16/32/64/128px and 1..256 layers')
    return tuple((size >> level) ** 2 * layers * 4 for level in range(size.bit_length()))


def encoded_length(size: int, layers: int) -> int:
    lengths = _geometry(size, layers)
    return 80 + 24 * len(lengths) + len(DFD) + len(KVD) + sum(lengths)


@dataclass(frozen=True)
class Ktx2Array:
    size: int
    layers: int
    levels: tuple[bytes, ...]  # Largest level first, unlike physical file order.


def encode_ktx2(size: int, layers: int, levels: tuple[bytes, ...] | list[bytes]) -> bytes:
    """Wrap complete original mip bytes with canonical headers and descriptors."""
    lengths = _geometry(size, layers)
    if not isinstance(levels, (tuple, list)) or len(levels) != len(lengths):
        raise ValueError('Complete mip chain through 1x1 required')
    for data, length in zip(levels, lengths):
        if not isinstance(data, bytes) or len(data) != length:
            raise ValueError('KTX2 level byte count/type mismatch')
        validate_premultiplied(data)
    dfd_offset = 80 + 24 * len(lengths)
    kvd_offset = dfd_offset + len(DFD)
    cursor = kvd_offset + len(KVD)
    offsets = [0] * len(lengths)
    for level in reversed(range(len(lengths))):
        offsets[level] = cursor
        cursor += lengths[level]  # RGBA8 levels are already 4-byte aligned.
    header = IDENTIFIER + struct.pack('<13I2Q', VK_FORMAT, 1, size, size, 0, layers, 1,
        len(lengths), 0, dfd_offset, len(DFD), kvd_offset, len(KVD), 0, 0)
    index = b''.join(struct.pack('<QQQ', at, length, length) for at, length in zip(offsets, lengths))
    return header + index + DFD + KVD + b''.join(reversed(levels))


def decode_ktx2(data: bytes) -> Ktx2Array:
    """Reject unsupported encodings and noncanonical offsets before slicing data.

    Intentionally rejects valid KTX2 files outside this exact ByteFables profile,
    including alternative metadata. All 64-bit fields are checked, not truncated.
    """
    if not isinstance(data, bytes) or not 80 <= len(data) <= MAX_BYTES or data[:12] != IDENTIFIER:
        raise ValueError('Invalid or oversized KTX2 container')
    (fmt, typ, width, height, depth, layers, faces, count, compression,
     dfd_at, dfd_len, kvd_at, kvd_len, sgd_at, sgd_len) = struct.unpack_from('<13I2Q', data, 12)
    lengths = _geometry(width, layers)
    if (fmt, typ, height, depth, faces, count, compression, sgd_at, sgd_len) != (
            VK_FORMAT, 1, width, 0, 1, len(lengths), 0, 0, 0):
        raise ValueError('Unsupported KTX2 format/array/mip/compression profile')
    if len(data) != encoded_length(width, layers):
        raise ValueError('KTX2 truncated, trailing data or byte budget mismatch')
    if (dfd_at, dfd_len, kvd_at, kvd_len) != (80 + count * 24, len(DFD), 80 + count * 24 + len(DFD), len(KVD)):
        raise ValueError('KTX2 descriptor/metadata offsets differ from canonical profile')
    if data[dfd_at:dfd_at + dfd_len] != DFD or data[kvd_at:kvd_at + kvd_len] != KVD:
        raise ValueError('KTX2 alpha/colour/orientation/metadata mismatch')
    cursor = kvd_at + kvd_len
    result = [b''] * count
    for level in reversed(range(count)):
        at, length, inflated = struct.unpack_from('<QQQ', data, 80 + level * 24)
        if (at, length, inflated) != (cursor, lengths[level], lengths[level]):
            raise ValueError('KTX2 overlapping, misordered, unaligned or invalid level index')
        result[level] = data[at:at + length]
        validate_premultiplied(result[level])
        cursor += length
    if cursor != len(data):
        raise ValueError('Unexpected KTX2 trailing bytes')
    return Ktx2Array(width, layers, tuple(result))
