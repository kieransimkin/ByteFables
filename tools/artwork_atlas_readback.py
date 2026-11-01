"""Independent, bounded PNG pixel readback for PUBLIC ByteFables artwork atlases.

FrameRudiments owns rendering. This module only verifies already-exported PNGs
with Pillow; optional *source-only* comparison calls the existing, registered
ByteFables ArtworkRenderer from the FrameRudiments plugin (not a second renderer).

This does not establish ownership, identity authenticity or byte recovery.
"""
from __future__ import annotations

import hashlib
import inspect
import io
import json
import math
from pathlib import Path
import re
import sys
import zlib
from typing import Any

from PIL import Image, ImageStat, UnidentifiedImageError, __version__ as PILLOW_VERSION

ATLAS_VERSION = "bytefables.artwork-atlas.v1"
READBACK_SCHEMA = "bytefables.artwork-atlas-readback.v1"
EXPORT_RECEIPT_VERSION = "bytefables.artwork-export-receipt.v1"
BRIDGE_VERSION = "bytefables.framerudiments.layer.v1"
FAMILIES = frozenset({"sigil", "constellation", "heraldry", "topography", "crystal",
                     "mandala", "cellular", "branching", "orbital"})
PALETTES = frozenset({"neon", "pastel", "mono"})
SCALES = (16, 32, 64, 128)
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
MAX_PLAN_BYTES = 4 * 1024 * 1024
MAX_PNG_BYTES = 128 * 1024 * 1024
MAX_PAGE_PIXELS = 16_777_216
MAX_PAGES = 1000
MAX_TILES = 1000
_DH_BITS = 64
_DIGEST_RE = re.compile(r"[0-9a-f]{64}\Z")
_LAYER_ID_RE = re.compile(r"[a-z][a-z0-9_-]{0,63}\Z")


class AtlasReadbackError(ValueError):
    """Invalid public plan, corrupt raster, or failed source-only comparison."""


def _int(value: Any, lower: int, upper: int, name: str) -> int:
    if type(value) is not int or not lower <= value <= upper:
        raise AtlasReadbackError(f"Invalid {name}: expected integer {lower}..{upper}")
    return value


def _rect(value: Any, width: int, height: int, label: str) -> tuple[int, int, int, int]:
    if not isinstance(value, list) or len(value) != 4:
        raise AtlasReadbackError(f"Invalid {label} rectangle")
    x0 = _int(value[0], 0, width, f"{label}.x0")
    y0 = _int(value[1], 0, height, f"{label}.y0")
    x1 = _int(value[2], 0, width, f"{label}.x1")
    y1 = _int(value[3], 0, height, f"{label}.y1")
    if x0 >= x1 or y0 >= y1:
        raise AtlasReadbackError(f"Invalid {label}: non-positive tile extent")
    if x1 - x0 > 2048 or y1 - y0 > 2048 or (x1 - x0) * (y1 - y0) > 1_048_576:
        raise AtlasReadbackError(f"Invalid {label}: exceeds native ArtworkRenderer bounds")
    return (x0, y0, x1, y1)


def _style(value: Any, digest: str) -> dict[str, Any]:
    if type(value) is not dict or set(value) != {
        "bridge_version", "digest_hex", "style", "palette", "complexity"
    }:
        raise AtlasReadbackError("Unknown or missing renderer style field")
    if (value["bridge_version"] != BRIDGE_VERSION or value["digest_hex"] != digest or
            type(value["style"]) is not str or value["style"] not in FAMILIES or
            type(value["palette"]) is not str or value["palette"] not in PALETTES):
        raise AtlasReadbackError("Noncanonical renderer style or digest mismatch")
    _int(value["complexity"], 1, 8, "artwork complexity")
    return value


def validate_atlas_plan(plan: Any) -> dict[str, Any]:
    """Validate the exact TypeScript artwork-atlas.v1 shape relevant to pixel readback.

    No arbitrary path, import, executable or raw input bytes are read from JSON.
    IDs and digests are only public identifiers; these checks do not authenticate.
    """
    if (type(plan) is not dict or plan.get("version") != ATLAS_VERSION or
            plan.get("publicOnly") is not True or plan.get("guarantee") != "presentation-only"):
        raise AtlasReadbackError("Expected public-only artwork-atlas.v1 plan")
    count = _int(plan.get("inputCount"), 1, MAX_TILES, "inputCount")
    pages = plan.get("pages")
    if not isinstance(pages, list) or not 1 <= len(pages) <= MAX_PAGES:
        raise AtlasReadbackError("Invalid atlas page list")
    used_indices: set[int] = set()
    used_ids: set[str] = set()
    for expected_page_index, page in enumerate(pages):
        if type(page) is not dict or page.get("index") != expected_page_index:
            raise AtlasReadbackError("Atlas pages must be sequential and zero-indexed")
        width = _int(page.get("width"), 16, 7680, "page width")
        height = _int(page.get("height"), 16, 7680, "page height")
        if width * height > MAX_PAGE_PIXELS:
            raise AtlasReadbackError("Atlas page exceeds readback pixel budget")
        tiles = page.get("tiles")
        if not isinstance(tiles, list) or not 1 <= len(tiles) <= MAX_TILES:
            raise AtlasReadbackError("Page must contain bounded artwork tiles")
        rects: list[tuple[int, int, int, int]] = []
        for tile in tiles:
            if type(tile) is not dict:
                raise AtlasReadbackError("Invalid atlas tile")
            idx = _int(tile.get("inputIndex"), 0, count - 1, "tile inputIndex")
            if idx in used_indices:
                raise AtlasReadbackError("Duplicate atlas inputIndex")
            used_indices.add(idx)
            digest = tile.get("digestHex")
            if type(digest) is not str or _DIGEST_RE.fullmatch(digest) is None:
                raise AtlasReadbackError("Atlas tile missing full public digest")
            rect = _rect(tile.get("rect"), width, height, "tile")
            if any(rect[0] < r[2] and r[0] < rect[2] and rect[1] < r[3] and r[1] < rect[3]
                   for r in rects):
                raise AtlasReadbackError("Overlapping atlas tile rectangles")
            rects.append(rect)
            uv = tile.get("uv")
            expected_uv = (rect[0] / width, rect[1] / height,
                           rect[2] / width, rect[3] / height)
            if (not isinstance(uv, list) or len(uv) != 4 or
                    any(type(a) not in (int, float) or not math.isfinite(a) or
                        not math.isclose(a, b, rel_tol=0, abs_tol=1e-10)
                        for a, b in zip(uv, expected_uv))):
                raise AtlasReadbackError("Noncanonical atlas UV coordinates")
            layer = tile.get("layer")
            if (type(layer) is not dict or layer.get("renderer") != "bytefables-artwork-v1" or
                    layer.get("type") != "rudiment" or layer.get("bounds") != list(rect)):
                raise AtlasReadbackError("Tile is not a valid FrameRudiments artwork layer")
            name = layer.get("id")
            if type(name) is not str or _LAYER_ID_RE.fullmatch(name) is None or name in used_ids:
                raise AtlasReadbackError("Invalid or repeated native layer ID")
            used_ids.add(name)
            _style(layer.get("style"), digest)
    if used_indices != set(range(count)):
        raise AtlasReadbackError("Atlas input indices are missing or unexpected")
    return plan


def load_atlas_plan(path: Path) -> dict[str, Any]:
    path = Path(path)
    if not path.is_file() or path.stat().st_size > MAX_PLAN_BYTES:
        raise AtlasReadbackError("Missing or oversized public atlas plan")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (ValueError, UnicodeError) as exc:
        raise AtlasReadbackError("Invalid public atlas JSON") from exc
    return validate_atlas_plan(data)


def _inspect_png_container(data: bytes) -> tuple[int, int]:
    """Independent zlib CRC-32 chunk validation before asking Pillow to decode."""
    if len(data) < 57 or len(data) > MAX_PNG_BYTES or not data.startswith(PNG_SIGNATURE):
        raise AtlasReadbackError("Invalid PNG signature or byte budget")
    pos = len(PNG_SIGNATURE)
    have_header = have_data = have_end = False
    after_data = False
    width = height = None
    color_type = None
    have_palette = False
    while pos < len(data):
        if len(data) - pos < 12:
            raise AtlasReadbackError("Truncated PNG chunk")
        length = int.from_bytes(data[pos:pos + 4], "big")
        end = pos + 12 + length
        if end > len(data):
            raise AtlasReadbackError("PNG chunk size exceeds file")
        kind = data[pos + 4:pos + 8]
        chunk = data[pos + 8:end - 4]
        if (len(kind) != 4 or not all((65 <= c <= 90 or 97 <= c <= 122) for c in kind) or
                kind[2] & 0x20):
            raise AtlasReadbackError("Invalid PNG chunk type")
        crc = int.from_bytes(data[end - 4:end], "big")
        if zlib.crc32(kind + chunk) != crc:
            raise AtlasReadbackError(f"PNG chunk CRC mismatch: {kind!r}")
        if not have_header:
            if kind != b"IHDR" or length != 13:
                raise AtlasReadbackError("PNG must start with IHDR")
            have_header = True
            width = int.from_bytes(chunk[0:4], "big")
            height = int.from_bytes(chunk[4:8], "big")
            color_type = chunk[9]
            if not (1 <= width <= 7680 and 1 <= height <= 7680 and
                    width * height <= MAX_PAGE_PIXELS and chunk[8] == 8 and
                    chunk[9] in (0, 2, 3, 4, 6) and chunk[10:] == b"\0\0\0"):
                raise AtlasReadbackError("Unsupported PNG IHDR")
        elif kind == b"IHDR":
            raise AtlasReadbackError("Duplicate PNG header")
        if kind == b"PLTE":
            if (have_palette or have_data or color_type in (0, 4) or
                    length == 0 or length > 768 or length % 3 != 0):
                raise AtlasReadbackError("Invalid PNG palette")
            have_palette = True
        if kind == b"IDAT":
            if color_type == 3 and not have_palette:
                raise AtlasReadbackError("Indexed PNG missing palette")
            if after_data:
                raise AtlasReadbackError("Noncontiguous PNG IDAT stream")
            have_data = True
        elif have_data:
            after_data = True
        if kind == b"IEND":
            if not have_data or length != 0 or end != len(data):
                raise AtlasReadbackError("Invalid PNG end chunk")
            have_end = True
            pos = end
            break
        if (kind[0] & 0x20) == 0 and kind not in (b"IHDR", b"IDAT", b"PLTE"):
            raise AtlasReadbackError("Unsupported critical PNG chunk")
        pos = end
    if not have_header or not have_data or not have_end or pos != len(data):
        raise AtlasReadbackError("Incomplete PNG")
    return width, height


def _decoded_image(filename: Path, expected_size: tuple[int, int]) -> tuple[str, int, Image.Image]:
    if not filename.is_file() or filename.stat().st_size > MAX_PNG_BYTES:
        raise AtlasReadbackError(f"Missing/oversized PNG page: {filename.name}")
    data = filename.read_bytes()
    if len(data) > MAX_PNG_BYTES or _inspect_png_container(data) != expected_size:
        raise AtlasReadbackError(f"PNG dimensions do not match atlas: {filename.name}")
    # Pillow decodes zlib+PNG filters independently from the TS chunk inspector.
    # verify() checks the container, load() forces actual raster decoding.
    try:
        with Image.open(io.BytesIO(data)) as probe:
            if probe.format != "PNG" or probe.size != expected_size:
                raise AtlasReadbackError("Expected PNG with exact page dimensions")
            probe.verify()
        with Image.open(io.BytesIO(data)) as source:
            source.load()
            image = source.convert("RGBA")
    except (OSError, SyntaxError, ValueError, UnidentifiedImageError) as exc:
        raise AtlasReadbackError(f"PNG decompression/pixel readback failed: {filename.name}") from exc
    return hashlib.sha256(data).hexdigest(), len(data), image


def _composited(image: Image.Image) -> Image.Image:
    # Fixed viewing background; avoids hiding errors behind transparent RGB.
    base = Image.new("RGBA", image.size, (17, 24, 39, 255))
    return Image.alpha_composite(base, image).convert("RGB")


def _dhash(image: Image.Image) -> str:
    # Perceptual proxy only, not a cryptographic or collision-safe fingerprint.
    luminance = image.convert("L").resize((9, 8), Image.Resampling.LANCZOS)
    pixels = luminance.tobytes()
    value = 0
    for y in range(8):
        for x in range(8):
            value = (value << 1) | int(pixels[y * 9 + x] > pixels[y * 9 + x + 1])
    return f"{value:016x}"


def _quality(tile: Image.Image) -> dict[str, Any]:
    alpha = tile.getchannel("A")
    composited = _composited(tile)
    thumb = composited.resize((32, 32), Image.Resampling.LANCZOS)
    contrast = ImageStat.Stat(thumb.convert("L")).stddev[0]
    coverage = ImageStat.Stat(alpha).mean[0] / 255
    # Metadata from the rendered PNG pixels, not from the original hash bits.
    resized = {}
    for size in SCALES:
        sampled = composited.resize((size, size), Image.Resampling.LANCZOS)
        resized[str(size)] = {
            "pixelSha256": hashlib.sha256(sampled.tobytes()).hexdigest(),
            "dhash64": _dhash(sampled),
        }
    return {
        "decodedRGBAsha256": hashlib.sha256(tile.tobytes()).hexdigest(),
        "alphaCoverage": round(coverage, 6),
        "contrastStddev32": round(contrast, 4),
        "blankOrUniform": alpha.getextrema()[1] == 0 or contrast < 0.5,
        "scales": resized,
    }


def _similarity(tiles: list[dict[str, Any]]) -> dict[str, Any]:
    """Compute true distinct-identity collision statistics without overclaiming."""
    results: dict[str, Any] = {}
    for scale in SCALES:
        hashes = [(tile["digestHex"], int(tile["quality"]["scales"][str(scale)]["dhash64"], 16),
                   tile["inputIndex"]) for tile in tiles]
        compared = collisions = near = 0
        minimum = 65
        nearest: list[tuple[int, int, int]] = []
        for i in range(len(hashes)):
            for j in range(i + 1, len(hashes)):
                # Repeated public identities are expected to resemble themselves.
                if hashes[i][0] == hashes[j][0]:
                    continue
                distance = (hashes[i][1] ^ hashes[j][1]).bit_count()
                compared += 1
                collisions += int(distance == 0)
                near += int(distance <= 4)
                if distance < minimum:
                    minimum = distance
                    nearest = [(hashes[i][2], hashes[j][2], distance)]
                elif distance == minimum and len(nearest) < 12:
                    nearest.append((hashes[i][2], hashes[j][2], distance))
        results[str(scale)] = {
            "distinctIdentityPairs": compared,
            "dhashExactCollisions": collisions,
            "dhashWithinFourBits": near,
            "minimumHammingDistance": None if minimum == 65 else minimum,
            "nearestPairs": [list(pair) for pair in nearest],
        }
    return results


def readback_artwork_atlas(plan: dict[str, Any], directory: Path, *,
                           compare_source: bool = False,
                           fail_on_blank: bool = False,
                           expected_receipt: dict[str, Any] | None = None) -> dict[str, Any]:
    """Verify complete exported pages, decode RGBA pixels and analyse every tile.

    ``compare_source`` is only valid for unmodified source-only exports, not
    composite output with backgrounds, masks, colour transforms or effects.
    """
    validate_atlas_plan(plan)
    directory = Path(directory)
    if not directory.is_dir():
        raise AtlasReadbackError("Atlas PNG directory does not exist")
    artwork_renderer = None
    source_checksum = None
    if compare_source:
        # Import exactly the checked-in trusted FrameRudiments source generator.
        root = Path(__file__).resolve().parents[1]
        sys.path.insert(0, str(root / "integrations" / "framerudiments"))
        from bytefables_framerudiments.artwork import ArtworkRenderer
        artwork_renderer = ArtworkRenderer
        source_checksum = hashlib.sha256(Path(inspect.getfile(ArtworkRenderer)).read_bytes()).hexdigest()
    pages = []
    all_tiles: list[dict[str, Any]] = []
    for page in plan["pages"]:
        filename = directory / f'atlas-page-{page["index"]:03d}.png'
        size = (page["width"], page["height"])
        file_digest, file_length, image = _decoded_image(filename, size)
        decoded_digest = hashlib.sha256(image.tobytes()).hexdigest()
        entries = []
        for tile in page["tiles"]:
            rect = tile["rect"]
            extracted = image.crop(tuple(rect))
            metrics = _quality(extracted)
            if fail_on_blank and metrics["blankOrUniform"]:
                raise AtlasReadbackError(f"Blank/uniform image for tile {tile['inputIndex']}")
            same_source = None
            if artwork_renderer is not None:
                reference = artwork_renderer(extracted.size, tile["layer"]["style"]).render(None)
                same_source = reference.mode == "RGBA" and reference.tobytes() == extracted.tobytes()
                if not same_source:
                    raise AtlasReadbackError(f"Source-only pixel mismatch for tile {tile['inputIndex']}")
            item = {
                "inputIndex": tile["inputIndex"], "pageIndex": page["index"],
                "digestHex": tile["digestHex"], "layerId": tile["layer"]["id"],
                "family": tile["layer"]["style"]["style"],
                "palette": tile["layer"]["style"]["palette"],
                "rect": rect, "quality": metrics,
                "sourcePixelsMatch": same_source,
            }
            entries.append(item)
            all_tiles.append(item)
        pages.append({
            "pageIndex": page["index"], "fileName": filename.name,
            "width": size[0], "height": size[1],
            "fileBytes": file_length,
            "fileSha256": file_digest,
            "decodedRGBAsha256": decoded_digest,
            "tileCount": len(entries),
        })
        image.close()
    all_tiles.sort(key=lambda x: x["inputIndex"])
    if expected_receipt is not None:
        verify_export_receipt(expected_receipt, plan, pages)
    encoded_plan = json.dumps(plan, sort_keys=True, separators=(",", ":"),
                              ensure_ascii=True, allow_nan=False).encode("ascii")
    return {
        "schema": READBACK_SCHEMA,
        "sourceFormat": ATLAS_VERSION,
        "publicOnly": True,
        "guarantee": "presentation-only",
        "sourcePixelsComparison": "passed" if compare_source else "not-run",
        "sourceRendererPythonSha256": source_checksum,
        "exportReceiptComparison": "passed" if expected_receipt is not None else "not-run",
        "pngDecoder": f"Pillow-{PILLOW_VERSION}",
        "planCanonicalJsonSha256": hashlib.sha256(encoded_plan).hexdigest(),
        "inputCount": plan["inputCount"],
        "pages": pages,
        "tiles": all_tiles,
        "similarity": _similarity(all_tiles),
        "warning": "Pixel/dHash similarity is diagnostic only; never proof of identity, authorisation, or byte recoverability.",
    }


def verify_export_receipt(receipt: Any, plan: dict[str, Any],
                          pages: list[dict[str, Any]]) -> None:
    """Independently reconcile the TS exact-file SHA-256 receipts with decoded PNGs."""
    if (type(receipt) is not dict or receipt.get("version") != EXPORT_RECEIPT_VERSION or
            receipt.get("atlasVersion") != ATLAS_VERSION or
            receipt.get("publicOnly") is not True or
            receipt.get("guarantee") != "presentation-only" or
            receipt.get("inputCount") != plan["inputCount"]):
        raise AtlasReadbackError("Unrecognised or mismatched public export receipt")
    claimed = receipt.get("pages")
    if not isinstance(claimed, list) or len(claimed) != len(pages):
        raise AtlasReadbackError("Export receipt page count mismatch")
    entries = {p["pageIndex"]: p for p in claimed if type(p) is dict and
               type(p.get("pageIndex")) is int}
    if len(entries) != len(pages):
        raise AtlasReadbackError("Duplicate/invalid export receipt page indices")
    for source_page, decoded in zip(plan["pages"], pages):
        target = entries.get(decoded["pageIndex"])
        if not target or any((
            target.get("sha256Hex") != decoded["fileSha256"],
            target.get("width") != decoded["width"],
            target.get("height") != decoded["height"],
            target.get("byteLength") != decoded["fileBytes"],
            target.get("tileCount") != len(source_page["tiles"]),
        )):
            raise AtlasReadbackError(f"PNG does not match export receipt page {decoded['pageIndex']}")


def load_expected_receipt(path: Path) -> dict[str, Any]:
    path = Path(path)
    if not path.is_file() or path.stat().st_size > MAX_PLAN_BYTES:
        raise AtlasReadbackError("Missing or oversized export receipt")
    try:
        result = json.loads(path.read_text(encoding="utf-8"))
    except (UnicodeError, ValueError) as exc:
        raise AtlasReadbackError("Invalid export receipt JSON") from exc
    if type(result) is not dict:
        raise AtlasReadbackError("Expected export receipt object")
    return result
