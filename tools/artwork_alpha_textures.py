"""Package verified transparent artwork as isolated, premultiplied texture arrays.

No background removal, renderer, remote model, PNG decoder in JS or page-wide
mipmap generation. Output contains bounded raw RGBA levels; each array layer
contains ONE sprite. Checksums establish consistency, not authenticity.
"""
from __future__ import annotations

import io
from pathlib import Path
from PIL import Image

from tools.artwork_asset_bundle import (
    AssetBundleError, _Writer, _bytes, _file, _no_links, _expect, _prefix, MAX_REPORT_BYTES,
)
from tools.artwork_native_benchmark import _sha, _json, _read_json, _keys, HEX
from tools.artwork_atlas_readback import FAMILIES, PALETTES
from tools.artwork_transparent_bundle import verify_transparent_bundle, _new_output, _failure
from bytefables_framerudiments.alpha_mips import PROFILE, NATIVE_SIZES, mip_chain, validate_premultiplied

SCHEMA = 'bytefables.alpha-texture-array-bundle.v1'
MAX_SPRITES = 1024
MAX_BYTES = 128*1024*1024
VIEW_FILES = ('index.html', 'runtime.js', 'demo.js', 'demo.css')
SAMPLING = {'storage': 'RGBA8', 'alpha': 'premultiplied', 'origin': 'top-left',
            'colourSpace': 'stored-samples-no-transfer', 'wrap': 'clamp-to-edge',
            'filters': ['nearest', 'linear-mipmap-linear'], 'mipSource': 'isolated-original-area',
            'generatedOnGPU': False}
ROOT = Path(__file__).resolve().parents[1]


def _int(value, low, high):
    return type(value) is int and low <= value <= high


def _hex(value):
    return type(value) is str and HEX.fullmatch(value) is not None


def key_for(sprite: dict) -> str:
    # Fixed property order and newline match JSON.stringify(..., null, 2) in JS.
    return 'bfalpha1-' + _sha(_json({'profile': PROFILE, 'digestHex': sprite['digestHex'],
        'family': sprite['family'], 'palette': sprite['palette'], 'complexity': sprite['complexity'],
        'nativeSize': sprite['nativeSize'], 'sourceRGBAsha256': sprite['sourceRGBAsha256']}))


def _load_sources(root: Path, native_size: int):
    result = verify_transparent_bundle(root)
    doc, digest = _read_json(_file(root, 'manifest.json'), MAX_REPORT_BYTES)
    _expect(digest == result['manifestSha256'] and 'png' in doc['formats'], 'Verified source PNGs required')
    items = sorted(doc['assets'], key=lambda a: (a['family'], a['palette'], a['complexity'], a['digestHex']))
    for item in items:
        _expect(native_size in item['nativeSizes'], 'Every sprite must have the requested native size; no resize')
    return doc, digest, items


def _png_source(root: Path, item: dict, size: int) -> tuple[dict, Image.Image]:
    file = f"{_prefix((item['family'],item['palette'],item['complexity'],item['digestHex']))}/{size}.png"
    record = next((f for f in item['files'] if f['file'] == file and f['format'] == 'png'), None)
    _expect(record is not None, 'Source PNG missing from inventory')
    raw = _bytes(_file(root, file), 2*1024*1024)
    _expect(len(raw) == record['byteLength'] and _sha(raw) == record['sha256'], 'Source PNG changed')
    with Image.open(io.BytesIO(raw)) as encoded:
        _expect(encoded.format == 'PNG' and encoded.mode == 'RGBA' and encoded.size == (size,size) and
                getattr(encoded, 'n_frames', 1) == 1, 'Unexpected source image')
        encoded.load()
        image = encoded.copy()
    source = next(s for s in item['sources'] if s['size'] == size)
    if _sha(image.tobytes()) != source['rgbaSha256']:
        image.close()
        raise AssetBundleError('Source decoded pixels changed')
    return record, image


def validate_manifest(doc: dict) -> dict:
    _keys(doc, {'schema','profile','status','publicOnly','guarantee','nativeSize','layersPerBank','spriteCount',
                'levelCount','payloadBytes','sourceManifestSha256','sampling','banks','sprites','viewerFiles'}, 'alpha manifest')
    _expect(doc['schema'] == SCHEMA and doc['profile'] == PROFILE and doc['status'] == 'passed' and
            doc['publicOnly'] is True and doc['guarantee'] == 'presentation-only', 'Invalid public alpha contract')
    size, count, capacity = doc['nativeSize'], doc['spriteCount'], doc['layersPerBank']
    _expect(type(size) is int and size in NATIVE_SIZES and _int(count,1,MAX_SPRITES) and
            _int(capacity,1,256) and _hex(doc['sourceManifestSha256']), 'Invalid texture dimensions/count')
    levels = size.bit_length()
    total = count*sum((size >> level)**2*4 for level in range(levels))
    _expect(type(doc['levelCount']) is int and doc['levelCount'] == levels and
            type(doc['payloadBytes']) is int and doc['payloadBytes'] == total and total <= MAX_BYTES,
            'Texture byte budget/count mismatch')
    _expect(doc['sampling'] == SAMPLING, 'Unsupported sampling/alpha convention')
    banks = doc['banks']; bank_count = (count+capacity-1)//capacity
    _expect(type(banks) is list and len(banks) == bank_count, 'Bank inventory mismatch')
    for index, bank in enumerate(banks):
        _keys(bank, {'index','layerCount','levels'}, 'bank')
        layers = min(capacity,count-index*capacity)
        _expect(type(bank['index']) is int and bank['index'] == index and
                type(bank['layerCount']) is int and bank['layerCount'] == layers and
                type(bank['levels']) is list and len(bank['levels']) == levels, 'Invalid bank dimensions')
        for level, record in enumerate(bank['levels']):
            _keys(record, {'level','size','file','byteLength','sha256'}, 'mip record')
            side = size >> level
            _expect(type(record['level']) is int and record['level'] == level and
                    type(record['size']) is int and record['size'] == side and
                    record['file'] == f'levels/bank-{index:03d}-mip-{level:02d}.rgba' and
                    type(record['byteLength']) is int and record['byteLength'] == side*side*layers*4 and
                    _hex(record['sha256']), 'Invalid mip geometry/path')
    sprites = doc['sprites']; previous = None
    _expect(type(sprites) is list and len(sprites) == count, 'Sprite count mismatch')
    for index, sprite in enumerate(sprites):
        _keys(sprite, {'spriteKey','digestHex','family','palette','complexity','nativeSize','bankIndex','layerIndex',
                      'sourceFile','sourceFileSha256','sourceRGBAsha256','levelSha256'}, 'sprite')
        _expect(type(sprite['family']) is str and sprite['family'] in FAMILIES and
                type(sprite['palette']) is str and sprite['palette'] in PALETTES and
                _int(sprite['complexity'],1,8) and _hex(sprite['digestHex']) and
                type(sprite['nativeSize']) is int and sprite['nativeSize'] == size and
                _hex(sprite['sourceFileSha256']) and _hex(sprite['sourceRGBAsha256']), 'Invalid sprite identity')
        key = (sprite['family'],sprite['palette'],sprite['complexity'],sprite['digestHex'])
        _expect(previous is None or key > previous, 'Duplicate/noncanonical sprite order'); previous = key
        _expect(type(sprite['bankIndex']) is int and sprite['bankIndex'] == index//capacity and
                type(sprite['layerIndex']) is int and sprite['layerIndex'] == index%capacity and
                sprite['sourceFile'] == f'{_prefix(key)}/{size}.png' and sprite['spriteKey'] == key_for(sprite),
                'Sprite source/key/placement mismatch')
        _expect(type(sprite['levelSha256']) is list and len(sprite['levelSha256']) == levels and
                all(_hex(d) for d in sprite['levelSha256']), 'Invalid per-layer mip hashes')
    viewers = doc['viewerFiles']
    _expect(type(viewers) is list and len(viewers) == len(VIEW_FILES), 'Viewer inventory mismatch')
    for name, record in zip(VIEW_FILES, viewers):
        _keys(record, {'file','byteLength','sha256'}, 'viewer record')
        _expect(record['file'] == name and _int(record['byteLength'],1,256*1024) and _hex(record['sha256']),
                'Invalid viewer file')
    return doc


def _verify(root: Path, doc: dict, source: Path | None = None) -> dict:
    validate_manifest(doc)
    files = {'manifest.json'}; payloads = []
    for bank in doc['banks']:
        data_levels = []
        for record in bank['levels']:
            raw = _bytes(_file(root,record['file']),record['byteLength'])
            _expect(len(raw) == record['byteLength'] and _sha(raw) == record['sha256'], 'Mip file checksum mismatch')
            validate_premultiplied(raw)
            data_levels.append(raw); files.add(record['file'])
        payloads.append(data_levels)
    for sprite in doc['sprites']:
        for level, digest in enumerate(sprite['levelSha256']):
            length = (doc['nativeSize'] >> level)**2*4; start = sprite['layerIndex']*length
            _expect(_sha(payloads[sprite['bankIndex']][level][start:start+length]) == digest,
                    'Sprite layer checksum mismatch')
    for record in doc['viewerFiles']:
        data = _bytes(_file(root,record['file']),record['byteLength'])
        _expect(len(data) == record['byteLength'] and _sha(data) == record['sha256'], 'Viewer integrity mismatch')
        files.add(record['file'])
    actual = set()
    for path in root.rglob('*'):
        _no_links(path)
        if path.is_file(): actual.add(path.relative_to(root).as_posix())
    _expect(actual - {'manifest.json'} == files - {'manifest.json'}, 'Unexpected or missing bundle files')
    if source is not None:
        _, digest, items = _load_sources(source,doc['nativeSize'])
        _expect(digest == doc['sourceManifestSha256'] and len(items) == doc['spriteCount'], 'Source bundle binding mismatch')
        for item, sprite in zip(items, doc['sprites']):
            record, image = _png_source(source,item,doc['nativeSize'])
            try:
                _expect(record['file'] == sprite['sourceFile'] and record['sha256'] == sprite['sourceFileSha256'] and
                        _sha(image.tobytes()) == sprite['sourceRGBAsha256'], 'Source identity/file mismatch')
                expected = mip_chain(image)
            finally:
                image.close()
            for level, raw in enumerate(expected):
                start = sprite['layerIndex']*len(raw)
                _expect(raw == payloads[sprite['bankIndex']][level][start:start+len(raw)], 'Source mip recomputation mismatch')
    return {'status':'passed', 'sprites':doc['spriteCount'], 'banks':len(doc['banks']),
            'levelsPerSprite':doc['levelCount'], 'payloadBytes':doc['payloadBytes'],
            'sourceRecomputed':source is not None, 'warning':'Unsigned consistency, not identity authenticity.'}


def verify_alpha_textures(bundle: Path, *, source_bundle: Path | None = None) -> dict:
    root = _no_links(bundle)
    _expect(root.is_dir() and not (root/'failure.json').exists(), 'Bundle missing or failed')
    doc, sha = _read_json(_file(root,'manifest.json'), MAX_REPORT_BYTES)
    result = _verify(root,doc,None if source_bundle is None else _no_links(source_bundle))
    return {**result, 'manifestSha256':sha}


def export_alpha_textures(source_bundle: Path, output: Path, *, confirm_public: bool = False,
                          native_size: int = 64, layers_per_bank: int = 128) -> dict:
    _expect(confirm_public is True, 'Explicit --confirm-public consent required')
    _expect(type(native_size) is int and native_size in NATIVE_SIZES and _int(layers_per_bank,1,256),
            'Invalid native size/layers per bank')
    source = _no_links(source_bundle); output = _new_output(output,(source,))
    _, source_sha, items = _load_sources(source,native_size)
    total = len(items)*sum((native_size >> level)**2*4 for level in range(native_size.bit_length()))
    _expect(total <= MAX_BYTES, 'Texture memory budget exceeded')
    output.mkdir(parents=True); writer = _Writer(output)
    try:
        sprites, banks = [], []
        for start in range(0,len(items),layers_per_bank):
            batch = items[start:start+layers_per_bank]; bank_index = len(banks)
            data_levels = [bytearray() for _ in range(native_size.bit_length())]
            for layer, item in enumerate(batch):
                record, image = _png_source(source,item,native_size)
                try:
                    levels = mip_chain(image); source_pixels_sha = _sha(image.tobytes())
                finally:
                    image.close()
                sprite = {k:item[k] for k in ('digestHex','family','palette','complexity')}
                sprite.update(nativeSize=native_size, bankIndex=bank_index, layerIndex=layer,
                              sourceFile=record['file'], sourceFileSha256=record['sha256'],
                              sourceRGBAsha256=source_pixels_sha, levelSha256=[_sha(raw) for raw in levels])
                sprite['spriteKey'] = key_for(sprite); sprites.append(sprite)
                for target, raw in zip(data_levels, levels): target.extend(raw)
            records = []
            for level, data in enumerate(data_levels):
                record = writer.write(f'levels/bank-{bank_index:03d}-mip-{level:02d}.rgba',bytes(data))
                records.append({'level':level,'size':native_size >> level,**record})
            banks.append({'index':bank_index,'layerCount':len(batch),'levels':records})
        viewer = ROOT/'integrations/web/artwork-alpha-textures'
        viewers = [writer.write(name,_bytes(viewer/name,256*1024)) for name in VIEW_FILES]
        doc = {'schema':SCHEMA,'profile':PROFILE,'status':'passed','publicOnly':True,'guarantee':'presentation-only',
               'nativeSize':native_size,'layersPerBank':layers_per_bank,'spriteCount':len(sprites),
               'levelCount':native_size.bit_length(),'payloadBytes':total,'sourceManifestSha256':source_sha,
               'sampling':SAMPLING.copy(),'banks':banks,'sprites':sprites,'viewerFiles':viewers}
        # Re-read every file and independently recompute all mips from original PNGs.
        _verify(output,doc,source)
        writer.write('manifest.json',_json(doc))
        return doc
    except Exception as exc:
        _failure(output,exc)
        raise
