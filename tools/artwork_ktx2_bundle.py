"""Lossless KTX2 packaging of verified PUBLIC premultiplied mip-array bundles."""
from __future__ import annotations

from pathlib import Path

from tools.artwork_asset_bundle import _Writer, _bytes, _file, _no_links, _expect, MAX_REPORT_BYTES
from tools.artwork_native_benchmark import _read_json, _json, _sha, _keys
from tools.artwork_transparent_bundle import _new_output, _failure
from tools.artwork_alpha_textures import verify_alpha_textures, validate_manifest as validate_source, _hex, _int
from bytefables_framerudiments.ktx2_arrays import PROFILE, encode_ktx2, decode_ktx2, encoded_length

SCHEMA = 'bytefables.ktx2-alpha-bundle.v1'
VIEW_FILES = ('index.html', 'alpha-runtime.js', 'ktx2-runtime.js', 'demo.js', 'demo.css')
ROOT = Path(__file__).resolve().parents[1]


def validate_manifest(doc: dict, source: dict) -> dict:
    validate_source(source)
    _keys(doc, {'schema', 'profile', 'status', 'publicOnly', 'guarantee', 'sourceManifest', 'banks', 'viewerFiles'}, 'KTX2 manifest')
    _expect(doc['schema'] == SCHEMA and doc['profile'] == PROFILE and doc['status'] == 'passed'
            and doc['publicOnly'] is True and doc['guarantee'] == 'presentation-only', 'Unsupported KTX2 bundle')
    record = doc['sourceManifest']
    _keys(record, {'file', 'sha256', 'byteLength'}, 'source manifest record')
    _expect(record['file'] == 'source-manifest.json' and _hex(record['sha256']) and
            _int(record['byteLength'], 1, MAX_REPORT_BYTES), 'Invalid source manifest reference')
    _expect(type(doc['banks']) is list and len(doc['banks']) == len(source['banks']), 'KTX2 bank inventory mismatch')
    for index, (bank, original) in enumerate(zip(doc['banks'], source['banks'])):
        _keys(bank, {'index', 'layerCount', 'file', 'byteLength', 'sha256'}, 'KTX2 bank')
        _expect(type(bank['index']) is int and bank['index'] == index and type(bank['layerCount']) is int and
                bank['layerCount'] == original['layerCount'] and bank['file'] == f'banks/bank-{index:03d}.ktx2' and
                type(bank['byteLength']) is int and bank['byteLength'] == encoded_length(source['nativeSize'], bank['layerCount'])
                and _hex(bank['sha256']), 'KTX2 bank geometry/path/size mismatch')
    _expect(type(doc['viewerFiles']) is list and len(doc['viewerFiles']) == len(VIEW_FILES), 'KTX2 viewer inventory mismatch')
    for name, record in zip(VIEW_FILES, doc['viewerFiles']):
        _keys(record, {'file', 'sha256', 'byteLength'}, 'viewer record')
        _expect(record['file'] == name and _hex(record['sha256']) and _int(record['byteLength'], 1, 256*1024), 'Invalid viewer record')
    return doc


def _bound_record(root: Path, record: dict, limit: int) -> bytes:
    _keys(record, {'file', 'sha256', 'byteLength'}, 'file record')
    _expect(_int(record['byteLength'], 1, limit) and _hex(record['sha256']), 'Invalid file size/hash')
    data = _bytes(_file(root, record['file']), record['byteLength'])
    _expect(len(data) == record['byteLength'] and _sha(data) == record['sha256'], 'KTX2 file checksum mismatch')
    return data


def _verify(root: Path, doc: dict, source: dict, source_bundle: Path | None) -> dict:
    validate_manifest(doc, source)
    # Verify original manifest bytes, not reserialised or relaxed JSON.
    _bound_record(root, doc['sourceManifest'], MAX_REPORT_BYTES)
    if source_bundle is not None:
        result = verify_alpha_textures(source_bundle)
        _expect(result['manifestSha256'] == doc['sourceManifest']['sha256'], 'Original alpha bundle binding mismatch')
    inventory = {'source-manifest.json'}
    for bank, original in zip(doc['banks'], source['banks']):
        raw = _bytes(_file(root, bank['file']), bank['byteLength'])
        _expect(len(raw) == bank['byteLength'] and _sha(raw) == bank['sha256'], 'KTX2 bank checksum mismatch')
        decoded = decode_ktx2(raw)
        _expect(decoded.size == source['nativeSize'] and decoded.layers == original['layerCount'], 'Decoded bank geometry mismatch')
        for level, (data, reference) in enumerate(zip(decoded.levels, original['levels'])):
            _expect(len(data) == reference['byteLength'] and _sha(data) == reference['sha256'], 'KTX2 mip bytes differ from original')
            per_layer = (decoded.size >> level)**2*4
            for layer in range(decoded.layers):
                sprite = source['sprites'][bank['index']*source['layersPerBank'] + layer]
                _expect(_sha(data[layer*per_layer:(layer+1)*per_layer]) == sprite['levelSha256'][level], 'KTX2 sprite layer mismatch')
            if source_bundle is not None:
                _expect(data == _bytes(_file(source_bundle, reference['file']), reference['byteLength']), 'Original mip bytes changed')
        inventory.add(bank['file'])
    for record in doc['viewerFiles']:
        _bound_record(root, record, 256*1024)
        inventory.add(record['file'])
    actual = set()
    for path in root.rglob('*'):
        _no_links(path)
        if path.is_file(): actual.add(path.relative_to(root).as_posix())
    _expect(actual - {'manifest.json'} == inventory, 'Unexpected or missing KTX2 bundle files')
    return {'status': 'passed', 'sprites': source['spriteCount'], 'banks': len(doc['banks']),
            'levelsPerSprite': source['levelCount'], 'payloadBytes': source['payloadBytes'],
            'ktx2Bytes': sum(b['byteLength'] for b in doc['banks']), 'originalBytesCompared': source_bundle is not None,
            'warning': 'Unsigned consistency, not identity authenticity. No Basis compression or colour conversion.'}


def verify_ktx2_bundle(bundle: Path, *, source_bundle: Path | None = None) -> dict:
    root = _no_links(bundle)
    _expect(root.is_dir() and not (root/'failure.json').exists(), 'KTX2 bundle absent or failed')
    doc, digest = _read_json(_file(root, 'manifest.json'), MAX_REPORT_BYTES)
    source, source_sha = _read_json(_file(root, 'source-manifest.json'), MAX_REPORT_BYTES)
    validate_manifest(doc, source)
    _expect(source_sha == doc['sourceManifest']['sha256'], 'Source manifest checksum mismatch')
    result = _verify(root, doc, source, None if source_bundle is None else _no_links(source_bundle))
    return {**result, 'manifestSha256': digest}


def export_ktx2_bundle(bundle: Path, output: Path, *, confirm_public: bool = False) -> dict:
    _expect(confirm_public is True, 'Explicit --confirm-public consent required')
    root = _no_links(bundle); output = _new_output(output, (root,))
    result = verify_alpha_textures(root)
    source, digest = _read_json(_file(root, 'manifest.json'), MAX_REPORT_BYTES)
    _expect(digest == result['manifestSha256'], 'Alpha manifest changed during export')
    output.mkdir(parents=True); writer = _Writer(output)
    try:
        source_record = writer.write('source-manifest.json', _bytes(_file(root, 'manifest.json'), MAX_REPORT_BYTES))
        _expect(source_record['sha256'] == digest, 'Alpha manifest changed during export')
        banks = []
        for original in source['banks']:
            levels = []
            for record in original['levels']:
                raw = _bytes(_file(root, record['file']), record['byteLength'])
                _expect(len(raw) == record['byteLength'] and _sha(raw) == record['sha256'], 'Source mip changed during export')
                levels.append(raw)
            encoded = encode_ktx2(source['nativeSize'], original['layerCount'], levels)
            record = writer.write(f"banks/bank-{original['index']:03d}.ktx2", encoded)
            banks.append({'index': original['index'], 'layerCount': original['layerCount'], **record})
        web = ROOT/'integrations/web/artwork-ktx2'
        viewers = []
        for name in VIEW_FILES:
            file = ROOT/'integrations/web/artwork-alpha-textures/runtime.js' if name == 'alpha-runtime.js' else web/name
            viewers.append(writer.write(name, _bytes(file, 256*1024)))
        doc = {'schema': SCHEMA, 'profile': PROFILE, 'status': 'passed', 'publicOnly': True,
               'guarantee': 'presentation-only', 'sourceManifest': source_record, 'banks': banks, 'viewerFiles': viewers}
        _verify(output, doc, source, root)
        writer.write('manifest.json', _json(doc))
        return doc
    except Exception as exc:
        _failure(output, exc)
        raise
