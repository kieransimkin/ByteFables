"""Stage a verified PUBLIC KTX2 bundle for Unity without executing its web assets."""
from __future__ import annotations
from pathlib import Path
from tools.artwork_asset_bundle import _bytes, _file, _no_links, _expect, _Writer, MAX_REPORT_BYTES
from tools.artwork_native_benchmark import _read_json, _json, _sha, _keys
from tools.artwork_transparent_bundle import _new_output, _failure
from tools.artwork_ktx2_bundle import verify_ktx2_bundle, validate_manifest
from bytefables_framerudiments.ktx2_arrays import decode_ktx2

SCHEMA = 'bytefables.unity-texture-import.v1'
DESCRIPTOR = 'artwork.bftextures'
MAX_PAYLOAD = 128 * 1024 * 1024


def _payload(root: Path, transport: dict, source: dict, budget: int) -> dict:
    validate_manifest(transport, source)
    _expect(type(budget) is int and 1 <= budget <= MAX_PAYLOAD, 'Invalid Unity payload budget')
    _expect(source['payloadBytes'] <= budget, 'Unity payload budget exceeded')
    record = transport['sourceManifest']
    raw = _bytes(_file(root, 'source-manifest.json'), record['byteLength'])
    _expect(len(raw) == record['byteLength'] and _sha(raw) == record['sha256'], 'Source manifest binding mismatch')
    for bank, original in zip(transport['banks'], source['banks']):
        raw = _bytes(_file(root, bank['file']), bank['byteLength'])
        _expect(len(raw) == bank['byteLength'] and _sha(raw) == bank['sha256'], 'KTX2 bank changed')
        parsed = decode_ktx2(raw)
        _expect(parsed.size == source['nativeSize'] and parsed.layers == bank['layerCount'], 'KTX2 geometry mismatch')
        for level, (pixels, record) in enumerate(zip(parsed.levels, original['levels'])):
            _expect(len(pixels) == record['byteLength'] and _sha(pixels) == record['sha256'], 'Mip hash mismatch')
            length = (parsed.size >> level)**2 * 4
            for layer in range(parsed.layers):
                sprite = source['sprites'][bank['index']*source['layersPerBank'] + layer]
                _expect(_sha(pixels[layer*length:(layer+1)*length]) == sprite['levelSha256'][level], 'Layer hash mismatch')
    return {'sprites': source['spriteCount'], 'banks': len(transport['banks']), 'nativeSize': source['nativeSize'],
            'levelsPerSprite': source['levelCount'], 'payloadBytes': source['payloadBytes']}


def verify_unity_stage(output: Path, *, max_payload_bytes: int = 64*1024*1024) -> dict:
    root = _no_links(output)
    _expect(root.is_dir() and not (root/'failure.json').exists(), 'Staging absent or failed')
    descriptor, descriptor_sha = _read_json(_file(root, DESCRIPTOR), 4096)
    _keys(descriptor, {'schema', 'publicOnly', 'manifestFile', 'manifestSha256'}, 'Unity descriptor')
    _expect(descriptor['schema'] == SCHEMA and descriptor['publicOnly'] is True and descriptor['manifestFile'] == 'transport.json', 'Invalid Unity descriptor')
    transport, digest = _read_json(_file(root, 'transport.json'), MAX_REPORT_BYTES)
    _expect(digest == descriptor['manifestSha256'], 'Transport manifest pin mismatch')
    source, _ = _read_json(_file(root, 'source-manifest.json'), MAX_REPORT_BYTES)
    result = _payload(root, transport, source, max_payload_bytes)
    expected = {DESCRIPTOR, 'transport.json', 'source-manifest.json', *(b['file'] for b in transport['banks'])}
    actual = set()
    for path in root.rglob('*'):
        _no_links(path)
        if path.is_file() and not path.name.endswith('.meta'):
            actual.add(path.relative_to(root).as_posix())
    _expect(actual == expected, 'Unexpected or missing staged files')
    return {'status': 'passed', 'descriptorSha256': descriptor_sha, 'manifestSha256': digest, **result,
            'unityExecuted': False, 'warning': 'Verified staging only; neither Unity execution nor identity authenticity.'}


def stage_unity_bundle(bundle: Path, output: Path, *, confirm_public: bool = False,
                       max_payload_bytes: int = 64*1024*1024) -> dict:
    _expect(confirm_public is True, 'Explicit --confirm-public consent required')
    source_root = _no_links(bundle); output = _new_output(output, (source_root,))
    result = verify_ktx2_bundle(source_root)
    transport, digest = _read_json(_file(source_root, 'manifest.json'), MAX_REPORT_BYTES)
    _expect(digest == result['manifestSha256'], 'KTX2 manifest changed')
    source, _ = _read_json(_file(source_root, 'source-manifest.json'), MAX_REPORT_BYTES)
    _payload(source_root, transport, source, max_payload_bytes)
    output.mkdir(parents=True); writer = _Writer(output)
    try:
        record = writer.write('transport.json', _bytes(_file(source_root, 'manifest.json'), MAX_REPORT_BYTES))
        _expect(record['sha256'] == digest, 'Transport changed while copying')
        ref = transport['sourceManifest']
        record = writer.write('source-manifest.json', _bytes(_file(source_root, ref['file']), ref['byteLength']))
        _expect(record['sha256'] == ref['sha256'], 'Source changed while copying')
        for bank in transport['banks']:
            record = writer.write(bank['file'], _bytes(_file(source_root, bank['file']), bank['byteLength']))
            _expect(record['sha256'] == bank['sha256'], 'Bank changed while copying')
        _payload(output, transport, source, max_payload_bytes)
        writer.write(DESCRIPTOR, _json({'schema': SCHEMA, 'publicOnly': True, 'manifestFile': 'transport.json', 'manifestSha256': digest}))
        return verify_unity_stage(output, max_payload_bytes=max_payload_bytes)
    except Exception as exc:
        (output/DESCRIPTOR).unlink(missing_ok=True)
        _failure(output, exc)
        raise
