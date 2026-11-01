"""Verified PUBLIC image assets -> deterministic, runtime-ready texture pages.

This packages existing FrameRudiments pixels; no native artwork is regenerated.
Manifests are unsigned consistency records, never authentication or backups.
"""
from __future__ import annotations

import io
from pathlib import Path
from PIL import Image

from tools.artwork_asset_bundle import (
    ROOT, MAX_REPORT_BYTES, AssetBundleError, _no_links, _file, _bytes,
    _read_json, _json, _sha, _expect, _Writer, verify_asset_bundle,
)
from tools.artwork_atlas_readback import FAMILIES, PALETTES
from bytefables_framerudiments.texture_atlas import (
    PROFILE, SIZES, MAX_PAGE_BYTES, TextureAtlasError, layout, extrude,
    encode_page, decode_page, verify_page,
)

SCHEMA = 'bytefables.artwork-texture-bundle.v1'
VIEW_FILES = ('index.html', 'runtime.js', 'demo.js', 'demo.css')
SAMPLING = {'origin': 'top-left', 'wrap': 'clamp-to-edge', 'mipmaps': False,
            'filters': ['nearest', 'linear'], 'colourConversion': 'none',
            'premultipliedAlpha': False}


def _source(directory: Path) -> tuple[Path, dict, str]:
    root = _no_links(directory)
    checked = verify_asset_bundle(root)
    manifest, digest = _read_json(_file(root, 'manifest.json'), MAX_REPORT_BYTES)
    _expect(digest == checked['manifestSha256'], 'Source manifest changed during verification')
    return root, manifest, digest


def _identity(sprite: dict) -> dict:
    return {k: sprite[k] for k in ('digestHex', 'family', 'palette', 'complexity', 'nativeSize', 'rgbaSha256')}


def sprite_key(sprite: dict) -> str:
    return 'bftexture1-' + _sha(_json({'profile': PROFILE, **_identity(sprite)}))


def _sort(sprite: dict) -> tuple:
    return (sprite['family'], sprite['palette'], sprite['complexity'], sprite['digestHex'])


def _entries(manifest: dict, size: int) -> list[dict]:
    entries = []
    for asset in manifest['assets']:
        _expect(size in asset['nativeSizes'], 'Requested native size is missing; implicit resizing is forbidden')
        file = next(f for f in asset['files'] if f['format'] == 'png' and f['frames'][0]['size'] == size)
        entry = {k: asset[k] for k in ('digestHex', 'family', 'palette', 'complexity')}
        entry.update(nativeSize=size, rgbaSha256=file['frames'][0]['rgbaSha256'],
                     sourceFile=file['file'], sourceFileSha256=file['sha256'])
        entry['spriteKey'] = sprite_key(entry)
        entries.append(entry)
    return sorted(entries, key=_sort)


def _source_image(root: Path, sprite: dict) -> Image.Image:
    data = _bytes(_file(root, sprite['sourceFile']), 2 * 1024 * 1024)
    _expect(_sha(data) == sprite['sourceFileSha256'], 'Source PNG changed during export')
    try:
        with Image.open(io.BytesIO(data), formats=['PNG']) as image:
            n = sprite['nativeSize']
            _expect(image.size == (n, n) and getattr(image, 'n_frames', 1) == 1, 'Source native size mismatch')
            image.load()
            result = image.convert('RGBA')
        if _sha(result.tobytes()) != sprite['rgbaSha256']:
            result.close()
            raise AssetBundleError('Source decoded pixels changed')
        return result
    except (OSError, SyntaxError) as exc:
        raise AssetBundleError('Source image decode failed') from exc


def export_texture_bundle(source: Path, output: Path, *, confirm_public: bool = False,
                          native_size: int = 64, page_size: int = 1024, padding: int = 2) -> dict:
    if confirm_public is not True:
        raise AssetBundleError('Explicit --confirm-public consent required')
    # Validate numeric settings before decoding a source bundle or writing anything.
    layout(1, native_size, page_size, padding)
    output, source = _no_links(output), _no_links(source)
    _expect(not output.exists(), 'Output must be a new directory; no overwrite or reuse')
    _expect(not output.is_relative_to(source), 'Output must be outside the source bundle')
    source, manifest, source_sha = _source(source)
    sprites = _entries(manifest, native_size)
    packing = layout(len(sprites), native_size, page_size, padding)
    for sprite, slot in zip(sprites, packing['slots']):
        sprite.update(slot)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.mkdir()
    writer = _Writer(output)
    try:
        pages = []
        for index in range(packing['pageCount']):
            batch = sprites[index * packing['capacity']:(index + 1) * packing['capacity']]
            with Image.new('RGBA', (page_size, page_size)) as page:
                for sprite in batch:
                    with _source_image(source, sprite) as image:
                        with extrude(image, padding) as padded:
                            x, y = sprite['rect'][:2]
                            page.paste(padded, (x - padding, y - padding))
                data = encode_page(page)
                saved = writer.write(f'pages/page-{index:03d}.png', data)
                # Reopen the saved bytes, not only the in-memory encoder result.
                with decode_page(_bytes(_file(output, saved['file']), MAX_PAGE_BYTES), page_size) as decoded:
                    verify_page(decoded, batch, padding)
                    pages.append({**saved, 'index': index, 'width': page_size, 'height': page_size,
                                  'rgbaSha256': _sha(decoded.tobytes()), 'spriteCount': len(batch)})
        viewer_root = ROOT / 'integrations' / 'web' / 'artwork-textures'
        viewer_files = [writer.write(name, _bytes(viewer_root / name, 256 * 1024)) for name in VIEW_FILES]
        result = {'schema': SCHEMA, 'profile': PROFILE, 'status': 'passed', 'publicOnly': True,
                  'guarantee': 'presentation-only', 'sourceManifestSha256': source_sha,
                  'nativeSize': native_size, 'pageSize': page_size, 'padding': padding,
                  'spriteCount': len(sprites), 'pages': pages, 'sprites': sprites,
                  'sampling': SAMPLING, 'resampled': False,
                  'spriteAlpha': 'opaque native compositor matte; page gaps transparent',
                  'viewerFiles': viewer_files,
                  'warning': 'Unsigned consistency metadata. Display only; not ownership or binary recovery.'}
        writer.write('manifest.json', _json(result))
        verify_texture_bundle(output)  # Validate published schema as well as page pixels.
        return result
    except Exception as exc:
        (output / 'manifest.json').unlink(missing_ok=True)
        (output / 'failure.json').write_bytes(_json({'status': 'failed', 'exception': type(exc).__name__,
                                                    'message': str(exc)[:1000]}))
        raise


def _hex(value: object) -> bool:
    return type(value) is str and len(value) == 64 and all(c in '0123456789abcdef' for c in value)


def validate_manifest(manifest: dict) -> dict:
    _expect(type(manifest) is dict and manifest.get('schema') == SCHEMA and
            manifest.get('profile') == PROFILE and manifest.get('status') == 'passed' and
            manifest.get('publicOnly') is True and manifest.get('guarantee') == 'presentation-only' and
            manifest.get('resampled') is False and manifest.get('sampling') == SAMPLING and
            _hex(manifest.get('sourceManifestSha256')), 'Invalid PUBLIC texture manifest')
    packing = layout(manifest.get('spriteCount'), manifest.get('nativeSize'),
                     manifest.get('pageSize'), manifest.get('padding'))
    sprites, pages = manifest.get('sprites'), manifest.get('pages')
    _expect(type(sprites) is list and len(sprites) == manifest['spriteCount'] and
            type(pages) is list and len(pages) == packing['pageCount'], 'Texture inventory count mismatch')
    identities = set()
    for sprite, slot in zip(sprites, packing['slots']):
        _expect(type(sprite) is dict and _hex(sprite.get('digestHex')) and
                type(sprite.get('family')) is str and sprite['family'] in FAMILIES and
                type(sprite.get('palette')) is str and sprite['palette'] in PALETTES and
                type(sprite.get('complexity')) is int and 1 <= sprite['complexity'] <= 8 and
                type(sprite.get('nativeSize')) is int and sprite['nativeSize'] == manifest['nativeSize'] and
                _hex(sprite.get('rgbaSha256')) and _hex(sprite.get('sourceFileSha256')),
                'Invalid texture identity metadata')
        _expect(sprite.get('spriteKey') == sprite_key(sprite), 'Sprite pixel/identity key mismatch')
        identity = _sort(sprite)
        _expect(identity not in identities, 'Duplicate texture identity/style')
        identities.add(identity)
        prefix = f"assets/{sprite['family']}-{sprite['palette']}-c{sprite['complexity']}/{sprite['digestHex']}"
        _expect(sprite.get('sourceFile') == f"{prefix}/{manifest['nativeSize']}.png", 'Invalid source asset reference')
        _expect(type(sprite.get('pageIndex')) is int and
                type(sprite.get('rect')) is list and all(type(v) is int for v in sprite['rect']) and
                all(sprite.get(k) == v for k, v in slot.items()), 'Sprite geometry or UV mismatch')
    _expect(sprites == sorted(sprites, key=_sort), 'Sprite order is not canonical')
    for index, page in enumerate(pages):
        count = min(packing['capacity'], len(sprites) - index * packing['capacity'])
        _expect(type(page) is dict and type(page.get('index')) is int and page['index'] == index and
                page.get('file') == f'pages/page-{index:03d}.png' and
                type(page.get('width')) is int and page['width'] == manifest['pageSize'] and
                type(page.get('height')) is int and page['height'] == manifest['pageSize'] and
                type(page.get('spriteCount')) is int and page['spriteCount'] == count and
                type(page.get('byteLength')) is int and 57 <= page['byteLength'] <= min(MAX_PAGE_BYTES, manifest['pageSize'] ** 2 * 5 + 65536) and
                _hex(page.get('sha256')) and _hex(page.get('rgbaSha256')), 'Invalid texture page metadata')
    _expect(sum(page['byteLength'] for page in pages) <= 512 * 1024 * 1024, 'Texture file byte budget exceeded')
    viewers = manifest.get('viewerFiles')
    _expect(type(viewers) is list and len(viewers) == len(VIEW_FILES) and
            all(type(v) is dict and type(v.get('byteLength')) is int and
                0 < v['byteLength'] <= 256 * 1024 and _hex(v.get('sha256')) for v in viewers) and
            [v.get('file') for v in viewers] == list(VIEW_FILES), 'Invalid texture viewer inventory')
    return packing


def verify_texture_bundle(directory: Path, *, source_bundle: Path | None = None) -> dict:
    root = _no_links(directory)
    _expect(not (root / 'failure.json').exists(), 'Texture bundle is marked failed')
    manifest, digest = _read_json(_file(root, 'manifest.json'), MAX_REPORT_BYTES)
    packing = validate_manifest(manifest)
    source_root, sources = None, None
    if source_bundle is not None:
        source_root, source_manifest, source_sha = _source(source_bundle)
        _expect(source_sha == manifest['sourceManifestSha256'], 'Source manifest checksum mismatch')
        sources = _entries(source_manifest, manifest['nativeSize'])
        _expect(len(sources) == manifest['spriteCount'], 'Source sprite count mismatch')
    seen = {'manifest.json'}
    for page in manifest['pages']:
        data = _bytes(_file(root, page['file']), MAX_PAGE_BYTES)
        _expect(len(data) == page['byteLength'] and _sha(data) == page['sha256'], 'Texture PNG file checksum mismatch')
        start = page['index'] * packing['capacity']
        sprites = manifest['sprites'][start:start + packing['capacity']]
        with decode_page(data, manifest['pageSize']) as image:
            _expect(_sha(image.tobytes()) == page['rgbaSha256'], 'Texture decoded page checksum mismatch')
            verify_page(image, sprites, manifest['padding'])
            if sources is not None:
                for sprite, source in zip(sprites, sources[start:start + len(sprites)]):
                    _expect(all(sprite.get(k) == v for k, v in source.items()), 'Source identity binding mismatch')
                    with _source_image(source_root, source) as expected:
                        with image.crop(tuple(sprite['rect'])) as actual:
                            _expect(actual.tobytes() == expected.tobytes(), 'Packed sprite differs from original source')
        seen.add(page['file'])
    for item in manifest['viewerFiles']:
        data = _bytes(_file(root, item['file']), 256 * 1024)
        _expect(_sha(data) == item['sha256'] and len(data) == item['byteLength'], 'Viewer checksum mismatch')
        seen.add(item['file'])
    actual = set()
    for path in root.rglob('*'):
        _no_links(path)
        if path.is_file():
            actual.add(path.relative_to(root).as_posix())
    _expect(actual == seen, 'Unexpected or missing files in texture bundle')
    return {'status': 'passed', 'manifestSha256': digest, 'sprites': manifest['spriteCount'],
            'pages': len(manifest['pages']), 'decodedPixelsVerified': True,
            'guttersVerified': True, 'sourceCompared': sources is not None,
            'warning': 'Consistency with unsigned metadata, not authenticity.'}
