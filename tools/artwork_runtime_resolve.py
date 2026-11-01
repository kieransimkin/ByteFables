"""Resolve verified PUBLIC texture transports into a lazy-runtime bank cache.

The cache is a derived presentation format. It preserves public sprite keys and
identity/style metadata, but records resolved mip hashes separately from the
original source hashes. Lossless KTX2 banks can be copied exactly; UASTC banks
are independently transcoded through the pinned Khronos KTX tool and rewrapped
in the already-qualified canonical RGBA8 KTX2 profile.
"""
from __future__ import annotations

import json
from pathlib import Path

from tools.artwork_asset_bundle import _Writer, _bytes, _file, _no_links, _expect, MAX_REPORT_BYTES
from tools.artwork_native_benchmark import _read_json, _json, _sha, _keys
from tools.artwork_transparent_bundle import _new_output, _failure
from tools.artwork_ktx2_bundle import verify_ktx2_bundle, validate_manifest as validate_lossless_manifest
from tools.artwork_ktx2_basis import verify_uastc_bundle, validate_manifest as validate_uastc_manifest, _extract_rgba8, ktx_version
from tools.artwork_alpha_textures import key_for, _hex, _int
from bytefables_framerudiments.ktx2_arrays import decode_ktx2, encode_ktx2, encoded_length, PROFILE as KTX_PROFILE

SCHEMA = 'bytefables.runtime-resolved-bundle.v1'
PROFILE = 'bytefables.runtime-rgba8-resolved.v1'
DESCRIPTOR_SCHEMA = 'bytefables.unity-lazy-runtime.v1'
MAX_BANKS = 16
MAX_PAYLOAD = 128 * 1024 * 1024


def _source_identity(source: dict, sprite: dict) -> dict:
    return {
        'spriteKey': sprite['spriteKey'], 'digestHex': sprite['digestHex'],
        'family': sprite['family'], 'palette': sprite['palette'], 'complexity': sprite['complexity'],
        'nativeSize': source['nativeSize'], 'bankIndex': sprite['bankIndex'], 'layerIndex': sprite['layerIndex'],
        'sourceRGBAsha256': sprite['sourceRGBAsha256'],
    }


def _resolved_records(levels: tuple[bytes, ...], layers: int, size: int) -> tuple[list[dict], list[list[str]]]:
    level_records = []
    layer_hashes = [[] for _ in range(layers)]
    for level, raw in enumerate(levels):
        side = size >> level
        per = side * side * 4
        _expect(len(raw) == per * layers, 'Resolved level byte count mismatch')
        level_records.append({'level': level, 'size': side, 'byteLength': len(raw), 'sha256': _sha(raw)})
        for layer in range(layers):
            layer_hashes[layer].append(_sha(raw[layer * per:(layer + 1) * per]))
    return level_records, layer_hashes


def _load_source_docs_from_lossless(root: Path):
    result = verify_ktx2_bundle(root)
    transport, transport_sha = _read_json(_file(root, 'manifest.json'), MAX_REPORT_BYTES)
    source, source_sha = _read_json(_file(root, 'source-manifest.json'), MAX_REPORT_BYTES)
    validate_lossless_manifest(transport, source)
    _expect(result['manifestSha256'] == transport_sha and transport['sourceManifest']['sha256'] == source_sha,
            'Lossless source metadata binding changed')
    return transport, transport_sha, source, source_sha


def _load_source_docs_from_uastc(root: Path, ktx: Path):
    result = verify_uastc_bundle(root, ktx=ktx)
    doc, uastc_sha = _read_json(_file(root, 'manifest.json'), MAX_REPORT_BYTES)
    validate_uastc_manifest(doc)
    transport_bytes = _bytes(_file(root, 'source-transport.json'), doc['sourceTransport']['byteLength'])
    source_bytes = _bytes(_file(root, 'source-manifest.json'), doc['sourceManifest']['byteLength'])
    _expect(_sha(transport_bytes) == doc['sourceTransport']['sha256'] and
            _sha(source_bytes) == doc['sourceManifest']['sha256'], 'UASTC copied metadata changed')
    transport = json.loads(transport_bytes); source = json.loads(source_bytes)
    validate_lossless_manifest(transport, source)
    _expect(result['manifestSha256'] == uastc_sha and transport['sourceManifest']['sha256'] == doc['sourceManifest']['sha256'],
            'UASTC source metadata binding mismatch')
    return doc, uastc_sha, transport, doc['sourceTransport']['sha256'], source, doc['sourceManifest']['sha256']


def validate_manifest(doc: dict) -> dict:
    _keys(doc, {'schema','profile','status','publicOnly','guarantee','sourceArtifact','sourceTransportSha256',
                'sourceManifestSha256','nativeSize','layersPerBank','spriteCount','levelCount','payloadBytes',
                'banks','sprites'}, 'runtime resolved manifest')
    _expect(doc['schema'] == SCHEMA and doc['profile'] == PROFILE and doc['status'] == 'passed' and
            doc['publicOnly'] is True and doc['guarantee'] == 'presentation-only', 'Unsupported runtime resolved bundle')
    artifact = doc['sourceArtifact']; _keys(artifact, {'kind','manifestSha256'}, 'source artifact')
    _expect(artifact['kind'] in ('lossless-ktx2','uastc-zstd') and _hex(artifact['manifestSha256']) and
            _hex(doc['sourceTransportSha256']) and _hex(doc['sourceManifestSha256']), 'Invalid runtime source binding')
    size = doc['nativeSize']; count = doc['spriteCount']; capacity = doc['layersPerBank']; levels = doc['levelCount']
    _expect(type(size) is int and size in (16,32,64,128) and _int(count,1,1024) and _int(capacity,1,256) and
            type(levels) is int and levels == size.bit_length(), 'Invalid runtime geometry')
    expected_payload = count * sum((size >> level) ** 2 * 4 for level in range(levels))
    _expect(type(doc['payloadBytes']) is int and doc['payloadBytes'] == expected_payload <= MAX_PAYLOAD,
            'Runtime payload byte budget mismatch')
    banks = doc['banks']; expected_banks = (count + capacity - 1) // capacity
    _expect(type(banks) is list and len(banks) == expected_banks <= MAX_BANKS, 'Runtime bank inventory mismatch')
    for index, bank in enumerate(banks):
        _keys(bank, {'index','layerCount','file','byteLength','sha256','levels'}, 'runtime bank')
        layers = min(capacity, count - index * capacity)
        _expect(bank['index'] == index and bank['layerCount'] == layers and
                bank['file'] == f'banks/bank-{index:03d}.ktx2' and
                bank['byteLength'] == encoded_length(size, layers) and _hex(bank['sha256']), 'Invalid runtime bank record')
        _expect(type(bank['levels']) is list and len(bank['levels']) == levels, 'Invalid runtime level inventory')
        for level, rec in enumerate(bank['levels']):
            _keys(rec, {'level','size','byteLength','sha256'}, 'runtime level')
            side = size >> level
            _expect(rec['level'] == level and rec['size'] == side and rec['byteLength'] == side*side*layers*4 and
                    _hex(rec['sha256']), 'Invalid runtime level record')
    sprites = doc['sprites']; _expect(type(sprites) is list and len(sprites) == count, 'Runtime sprite inventory mismatch')
    previous = None
    for index, sprite in enumerate(sprites):
        _keys(sprite, {'spriteKey','digestHex','family','palette','complexity','nativeSize','bankIndex','layerIndex',
                       'sourceRGBAsha256','resolvedLevelSha256'}, 'runtime sprite')
        _expect(_hex(sprite['digestHex']) and _hex(sprite['sourceRGBAsha256']) and
                type(sprite['family']) is str and type(sprite['palette']) is str and _int(sprite['complexity'],1,8) and
                sprite['nativeSize'] == size and sprite['bankIndex'] == index // capacity and
                sprite['layerIndex'] == index % capacity, 'Invalid runtime sprite identity/placement')
        canonical = key_for(sprite)
        _expect(sprite['spriteKey'] == canonical, 'Runtime sprite key changed')
        order = (sprite['family'], sprite['palette'], sprite['complexity'], sprite['digestHex'])
        _expect(previous is None or order > previous, 'Runtime sprites are duplicate/noncanonical'); previous = order
        _expect(type(sprite['resolvedLevelSha256']) is list and len(sprite['resolvedLevelSha256']) == levels and
                all(_hex(value) for value in sprite['resolvedLevelSha256']), 'Invalid runtime sprite mip hashes')
    return doc


def _verify(root: Path, doc: dict) -> dict:
    validate_manifest(doc)
    seen = {'manifest.json','runtime.bfresolved'}
    capacity = doc['layersPerBank']
    for bank in doc['banks']:
        raw = _bytes(_file(root, bank['file']), bank['byteLength'])
        _expect(len(raw) == bank['byteLength'] and _sha(raw) == bank['sha256'], 'Runtime bank checksum mismatch')
        parsed = decode_ktx2(raw)
        _expect(parsed.size == doc['nativeSize'] and parsed.layers == bank['layerCount'], 'Runtime bank geometry mismatch')
        for level, rec in enumerate(bank['levels']):
            _expect(len(parsed.levels[level]) == rec['byteLength'] and _sha(parsed.levels[level]) == rec['sha256'],
                    'Runtime resolved level checksum mismatch')
            side = parsed.size >> level; per = side*side*4
            for layer in range(parsed.layers):
                sprite = doc['sprites'][bank['index']*capacity + layer]
                _expect(_sha(parsed.levels[level][layer*per:(layer+1)*per]) == sprite['resolvedLevelSha256'][level],
                        'Runtime resolved sprite mip checksum mismatch')
        seen.add(bank['file'])
    descriptor, descriptor_sha = _read_json(_file(root, 'runtime.bfresolved'), 4096)
    _keys(descriptor, {'schema','publicOnly','manifestFile','manifestSha256'}, 'runtime descriptor')
    _expect(descriptor['schema'] == DESCRIPTOR_SCHEMA and descriptor['publicOnly'] is True and
            descriptor['manifestFile'] == 'manifest.json' and descriptor['manifestSha256'] == _sha(_json(doc)),
            'Runtime descriptor binding mismatch')
    actual = set()
    for path in root.rglob('*'):
        _no_links(path)
        if path.is_file(): actual.add(path.relative_to(root).as_posix())
    _expect(actual == seen, 'Unexpected or missing runtime resolved files')
    return {'status':'passed','manifestSha256':_sha(_json(doc)),'descriptorSha256':descriptor_sha,
            'sourceKind':doc['sourceArtifact']['kind'],'sprites':doc['spriteCount'],'banks':len(doc['banks']),
            'payloadBytes':doc['payloadBytes']}


def verify_runtime_bundle(bundle: Path) -> dict:
    root = _no_links(bundle)
    _expect(root.is_dir() and not (root/'failure.json').exists(), 'Runtime resolved bundle absent or failed')
    doc, digest = _read_json(_file(root, 'manifest.json'), MAX_REPORT_BYTES)
    result = _verify(root, doc); _expect(result['manifestSha256'] == digest, 'Runtime manifest checksum mismatch')
    return result


def _write_resolved(output: Path, *, source_kind: str, source_artifact_sha: str, transport_sha: str,
                    source_sha: str, source: dict, bank_levels: list[tuple[bytes, ...]]) -> dict:
    writer = _Writer(output); banks = []; sprites = []
    capacity = source['layersPerBank']; size = source['nativeSize']; levels = source['levelCount']
    for index, raw_levels in enumerate(bank_levels):
        layers = min(capacity, source['spriteCount'] - index*capacity)
        _expect(len(raw_levels) == levels, 'Resolved mip count mismatch')
        records, per_layer = _resolved_records(raw_levels, layers, size)
        encoded = encode_ktx2(size, layers, raw_levels)
        file_record = writer.write(f'banks/bank-{index:03d}.ktx2', encoded)
        banks.append({'index':index,'layerCount':layers,**file_record,'levels':records})
        for layer in range(layers):
            original = source['sprites'][index*capacity + layer]
            sprite = _source_identity(source, original); sprite['resolvedLevelSha256'] = per_layer[layer]
            sprites.append(sprite)
    doc = {'schema':SCHEMA,'profile':PROFILE,'status':'passed','publicOnly':True,'guarantee':'presentation-only',
           'sourceArtifact':{'kind':source_kind,'manifestSha256':source_artifact_sha},
           'sourceTransportSha256':transport_sha,'sourceManifestSha256':source_sha,
           'nativeSize':size,'layersPerBank':capacity,'spriteCount':source['spriteCount'],'levelCount':levels,
           'payloadBytes':source['payloadBytes'],'banks':banks,'sprites':sprites}
    validate_manifest(doc)
    manifest_record = writer.write('manifest.json', _json(doc))
    descriptor = {'schema':DESCRIPTOR_SCHEMA,'publicOnly':True,'manifestFile':'manifest.json',
                  'manifestSha256':manifest_record['sha256']}
    writer.write('runtime.bfresolved', _json(descriptor))
    _verify(output, doc)
    return doc


def resolve_lossless_bundle(bundle: Path, output: Path, *, confirm_public: bool = False) -> dict:
    _expect(confirm_public is True, 'Explicit --confirm-public consent required')
    root = _no_links(bundle); output = _new_output(output, (root,)); output.mkdir(parents=True)
    try:
        transport, transport_sha, source, source_sha = _load_source_docs_from_lossless(root)
        bank_levels = []
        for record in transport['banks']:
            raw = _bytes(_file(root, record['file']), record['byteLength'])
            _expect(len(raw) == record['byteLength'] and _sha(raw) == record['sha256'], 'Lossless source bank changed')
            bank_levels.append(decode_ktx2(raw).levels)
        return _write_resolved(output, source_kind='lossless-ktx2', source_artifact_sha=transport_sha,
                               transport_sha=transport_sha, source_sha=source_sha, source=source, bank_levels=bank_levels)
    except Exception as exc:
        _failure(output, exc); raise


def resolve_uastc_bundle(bundle: Path, output: Path, *, ktx: Path, confirm_public: bool = False) -> dict:
    _expect(confirm_public is True, 'Explicit --confirm-public consent required')
    exe = _no_links(ktx); ktx_version(exe)
    root = _no_links(bundle); output = _new_output(output, (root, exe)); output.mkdir(parents=True)
    try:
        uastc, uastc_sha, transport, transport_sha, source, source_sha = _load_source_docs_from_uastc(root, exe)
        bank_levels = []
        for bank in uastc['banks']:
            compressed = _file(root, bank['file'])
            raw = _bytes(compressed, bank['byteLength'])
            _expect(_sha(raw) == bank['sha256'], 'UASTC source bank changed during resolution')
            decoded = _extract_rgba8(exe, compressed, source['nativeSize'], bank['layerCount'])
            expected = bank['decodedLevels']
            _expect(len(decoded) == len(expected) and all(_sha(level) == record['sha256'] for level, record in zip(decoded, expected)),
                    'UASTC transcode result differs from qualified decoded levels')
            bank_levels.append(decoded)
        return _write_resolved(output, source_kind='uastc-zstd', source_artifact_sha=uastc_sha,
                               transport_sha=transport_sha, source_sha=source_sha, source=source, bank_levels=bank_levels)
    except Exception as exc:
        _failure(output, exc); raise
