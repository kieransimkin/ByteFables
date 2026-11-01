"""Package verified UASTC banks as raw GPU-native 4x4 block payloads.

The bundle is a deployment/qualification surface, not a new artwork format.
Khronos KTX performs every UASTC transcode. ByteFables only inventories,
bounds and hashes the resulting BC7 / ASTC 4x4 / ETC2 RGBA8 blocks.
"""
from __future__ import annotations

import json
import math
import re
import tempfile
from pathlib import Path

from tools.artwork_asset_bundle import _Writer, _bytes, _file, _no_links, _expect, MAX_REPORT_BYTES
from tools.artwork_native_benchmark import _read_json, _json, _sha, _keys
from tools.artwork_transparent_bundle import _new_output, _failure
from tools.artwork_ktx2_basis import verify_uastc_bundle, validate_manifest as validate_uastc_manifest, ktx_version, _run
from tools.artwork_alpha_textures import key_for, _hex, _int

SCHEMA = 'bytefables.gpu-block-texture-bundle.v1'
PROFILE = 'bytefables.gpu-blocks-4x4.v1'
DESCRIPTOR_SCHEMA = 'bytefables.unity-gpu-blocks.v1'
MAX_BYTES = 128 * 1024 * 1024
RAW_RE = re.compile(r'(?:^|_)level(\d+)(?:_face\d+)?_layer(\d+)(?:_depth\d+)?\.raw$', re.I)
TARGETS = {
    'bc7': {'ktxTarget': 'bc7', 'unityTextureFormat': 'BC7', 'blockWidth': 4, 'blockHeight': 4, 'blockBytes': 16},
    'astc4x4': {'ktxTarget': 'astc', 'unityTextureFormat': 'ASTC_4x4', 'blockWidth': 4, 'blockHeight': 4, 'blockBytes': 16},
    'etc2rgba8': {'ktxTarget': 'etc-rgba', 'unityTextureFormat': 'ETC2_RGBA8', 'blockWidth': 4, 'blockHeight': 4, 'blockBytes': 16},
}


def level_bytes(side: int, layers: int, target: dict) -> int:
    _expect(type(side) is int and side >= 1 and type(layers) is int and 1 <= layers <= 256, 'Invalid block geometry')
    blocks_x = max(1, (side + target['blockWidth'] - 1) // target['blockWidth'])
    blocks_y = max(1, (side + target['blockHeight'] - 1) // target['blockHeight'])
    return blocks_x * blocks_y * target['blockBytes'] * layers


def _extract_target(exe: Path, compressed: Path, target: dict, size: int, layers: int) -> tuple[bytes, ...]:
    levels = size.bit_length()
    with tempfile.TemporaryDirectory(prefix='bytefables-gpu-blocks-') as td:
        out = Path(td) / 'images'
        _run([str(exe), 'extract', '--transcode', target['ktxTarget'], '--all', '--raw', str(compressed), str(out)], timeout=240)
        found: dict[tuple[int, int], bytes] = {}
        for path in out.rglob('*.raw') if out.exists() else ():
            match = RAW_RE.search(path.name)
            _expect(match is not None, f'Unexpected Khronos block extraction name: {path.name}')
            level, layer = int(match.group(1)), int(match.group(2))
            _expect(0 <= level < levels and 0 <= layer < layers and (level, layer) not in found,
                    'Duplicate/out-of-range GPU block image')
            side = size >> level
            per = level_bytes(side, 1, target)
            raw = _bytes(_no_links(path), per)
            _expect(len(raw) == per, 'GPU block image byte count mismatch')
            found[(level, layer)] = raw
        _expect(len(found) == levels * layers, 'Khronos did not return every block-compressed mip/layer')
        return tuple(b''.join(found[(level, layer)] for layer in range(layers)) for level in range(levels))


def validate_manifest(doc: dict) -> dict:
    _keys(doc, {'schema','profile','status','publicOnly','guarantee','tool','sourceUastc','sourceManifest',
                'nativeSize','layersPerBank','spriteCount','levelCount','formats','sprites'}, 'GPU block manifest')
    _expect(doc['schema'] == SCHEMA and doc['profile'] == PROFILE and doc['status'] == 'passed' and
            doc['publicOnly'] is True and doc['guarantee'] == 'presentation-only', 'Unsupported GPU block bundle')
    _expect(doc['tool'] == {'name':'Khronos KTX-Software','version':'4.4.2'}, 'Unexpected GPU block tool')
    for key, name in (('sourceUastc','source-uastc.json'),('sourceManifest','source-manifest.json')):
        rec = doc[key]; _keys(rec, {'file','byteLength','sha256'}, key)
        _expect(rec['file'] == name and _int(rec['byteLength'],1,MAX_REPORT_BYTES) and _hex(rec['sha256']), 'Invalid GPU source binding')
    size, capacity, count, levels = doc['nativeSize'], doc['layersPerBank'], doc['spriteCount'], doc['levelCount']
    _expect(type(size) is int and size in (16,32,64,128) and _int(capacity,1,256) and _int(count,1,1024) and
            type(levels) is int and levels == size.bit_length(), 'Invalid GPU block geometry')
    formats = doc['formats']; _expect(type(formats) is list and len(formats) == len(TARGETS), 'GPU format inventory mismatch')
    expected_banks = (count + capacity - 1) // capacity
    seen = set()
    for fmt in formats:
        _keys(fmt, {'id','ktxTarget','unityTextureFormat','blockWidth','blockHeight','blockBytes','payloadBytes','banks'}, 'GPU format')
        target = TARGETS.get(fmt['id']); _expect(target is not None and all(fmt[k] == target[k] for k in target), 'Unsupported GPU target')
        _expect(fmt['id'] not in seen, 'Duplicate GPU target'); seen.add(fmt['id'])
        banks = fmt['banks']; _expect(type(banks) is list and len(banks) == expected_banks, 'GPU bank inventory mismatch')
        total = 0
        for bank_index, bank in enumerate(banks):
            _keys(bank, {'index','layerCount','levels'}, 'GPU bank')
            layers = min(capacity, count - bank_index * capacity)
            _expect(bank['index'] == bank_index and bank['layerCount'] == layers and type(bank['levels']) is list and
                    len(bank['levels']) == levels, 'GPU bank geometry mismatch')
            for level, rec in enumerate(bank['levels']):
                _keys(rec, {'level','size','file','byteLength','sha256'}, 'GPU level')
                side = size >> level; expected = level_bytes(side, layers, target)
                _expect(rec['level'] == level and rec['size'] == side and
                        rec['file'] == f"formats/{fmt['id']}/bank-{bank_index:03d}-mip-{level:02d}.bin" and
                        rec['byteLength'] == expected and _hex(rec['sha256']), 'GPU level record mismatch')
                total += expected
        _expect(fmt['payloadBytes'] == total and total <= MAX_BYTES, 'GPU payload budget mismatch')
    _expect(seen == set(TARGETS), 'Missing GPU target')
    sprites = doc['sprites']; _expect(type(sprites) is list and len(sprites) == count, 'GPU sprite inventory mismatch')
    previous = None
    for index, sprite in enumerate(sprites):
        _keys(sprite, {'spriteKey','digestHex','family','palette','complexity','nativeSize','bankIndex','layerIndex','sourceRGBAsha256'}, 'GPU sprite')
        _expect(_hex(sprite['digestHex']) and _hex(sprite['sourceRGBAsha256']) and type(sprite['family']) is str and
                type(sprite['palette']) is str and _int(sprite['complexity'],1,8) and sprite['nativeSize'] == size and
                sprite['bankIndex'] == index // capacity and sprite['layerIndex'] == index % capacity and
                sprite['spriteKey'] == key_for(sprite), 'GPU sprite identity changed')
        order = (sprite['family'],sprite['palette'],sprite['complexity'],sprite['digestHex'])
        _expect(previous is None or order > previous, 'GPU sprites duplicate/noncanonical'); previous = order
    return doc


def _verify_files(root: Path, doc: dict) -> dict:
    validate_manifest(doc)
    expected = {'manifest.json','gpu.bfgpu','source-uastc.json','source-manifest.json'}
    total = 0
    for fmt in doc['formats']:
        for bank in fmt['banks']:
            for rec in bank['levels']:
                raw = _bytes(_file(root,rec['file']),rec['byteLength'])
                _expect(len(raw) == rec['byteLength'] and _sha(raw) == rec['sha256'], 'GPU block checksum mismatch')
                expected.add(rec['file']); total += len(raw)
    descriptor, descriptor_sha = _read_json(_file(root,'gpu.bfgpu'),4096)
    _keys(descriptor, {'schema','publicOnly','manifestFile','manifestSha256'}, 'GPU block descriptor')
    _expect(descriptor['schema'] == DESCRIPTOR_SCHEMA and descriptor['publicOnly'] is True and descriptor['manifestFile'] == 'manifest.json' and
            descriptor['manifestSha256'] == _sha(_json(doc)), 'GPU block descriptor binding mismatch')
    actual = set()
    for path in root.rglob('*'):
        _no_links(path)
        if path.is_file(): actual.add(path.relative_to(root).as_posix())
    _expect(actual == expected, 'Unexpected or missing GPU block bundle files')
    return {'status':'passed','manifestSha256':_sha(_json(doc)),'sprites':doc['spriteCount'],
            'formats':[fmt['id'] for fmt in doc['formats']],'blockBytes':total,'descriptorSha256':descriptor_sha,
            'warning':'Raw GPU blocks are transport data. Unity orientation/quality requires real-device qualification.'}


def verify_gpu_bundle(bundle: Path, *, source_uastc: Path | None = None, ktx: Path | None = None) -> dict:
    root = _no_links(bundle); _expect(root.is_dir() and not (root/'failure.json').exists(), 'GPU block bundle absent or failed')
    doc, digest = _read_json(_file(root,'manifest.json'),MAX_REPORT_BYTES); result = _verify_files(root,doc)
    _expect(result['manifestSha256'] == digest, 'GPU block manifest checksum mismatch')
    if source_uastc is not None:
        _expect(ktx is not None, 'Khronos ktx executable required for source-backed GPU verification')
        source = _no_links(source_uastc); exe = _no_links(ktx); ktx_version(exe)
        verified = verify_uastc_bundle(source,ktx=exe)
        _expect(verified['manifestSha256'] == doc['sourceUastc']['sha256'], 'GPU bundle UASTC binding mismatch')
        source_doc, _ = _read_json(_file(source,'manifest.json'),MAX_REPORT_BYTES)
        for fmt in doc['formats']:
            target = TARGETS[fmt['id']]
            for bank, src_bank in zip(fmt['banks'],source_doc['banks']):
                extracted = _extract_target(exe,_file(source,src_bank['file']),target,doc['nativeSize'],bank['layerCount'])
                for raw, rec in zip(extracted,bank['levels']):
                    _expect(_sha(raw) == rec['sha256'] and len(raw) == rec['byteLength'], 'GPU target transcode changed')
        result['sourceRecomputed'] = True
    else:
        result['sourceRecomputed'] = False
    return result


def export_gpu_bundle(uastc_bundle: Path, output: Path, *, ktx: Path, confirm_public: bool=False) -> dict:
    _expect(confirm_public is True, 'Explicit --confirm-public consent required')
    root = _no_links(uastc_bundle); exe = _no_links(ktx); ktx_version(exe)
    verified = verify_uastc_bundle(root,ktx=exe)
    source_doc, source_sha = _read_json(_file(root,'manifest.json'),MAX_REPORT_BYTES); validate_uastc_manifest(source_doc)
    source_bytes = _bytes(_file(root,'source-manifest.json'),source_doc['sourceManifest']['byteLength'])
    source = json.loads(source_bytes)
    _expect(_sha(source_bytes) == source_doc['sourceManifest']['sha256'], 'UASTC source manifest changed')
    output = _new_output(output,(root,exe)); output.mkdir(parents=True); writer = _Writer(output)
    try:
        uastc_record = writer.write('source-uastc.json',_bytes(_file(root,'manifest.json'),MAX_REPORT_BYTES))
        source_record = writer.write('source-manifest.json',source_bytes)
        _expect(uastc_record['sha256'] == verified['manifestSha256'] == source_sha, 'UASTC manifest binding changed')
        formats=[]
        for fmt_id,target in TARGETS.items():
            banks=[]; total=0
            for bank in source_doc['banks']:
                levels = _extract_target(exe,_file(root,bank['file']),target,source['nativeSize'],bank['layerCount'])
                records=[]
                for level,raw in enumerate(levels):
                    rec=writer.write(f'formats/{fmt_id}/bank-{bank["index"]:03d}-mip-{level:02d}.bin',raw)
                    records.append({'level':level,'size':source['nativeSize']>>level,**rec}); total += len(raw)
                banks.append({'index':bank['index'],'layerCount':bank['layerCount'],'levels':records})
            formats.append({'id':fmt_id,**target,'payloadBytes':total,'banks':banks})
        sprites=[]
        for item in source['sprites']:
            sprites.append({k:item[k] for k in ('spriteKey','digestHex','family','palette','complexity','nativeSize','bankIndex','layerIndex','sourceRGBAsha256')})
        doc={'schema':SCHEMA,'profile':PROFILE,'status':'passed','publicOnly':True,'guarantee':'presentation-only',
             'tool':{'name':'Khronos KTX-Software','version':'4.4.2'},'sourceUastc':uastc_record,'sourceManifest':source_record,
             'nativeSize':source['nativeSize'],'layersPerBank':source['layersPerBank'],'spriteCount':source['spriteCount'],
             'levelCount':source['levelCount'],'formats':formats,'sprites':sprites}
        validate_manifest(doc); manifest_record=writer.write('manifest.json',_json(doc))
        writer.write('gpu.bfgpu',_json({'schema':DESCRIPTOR_SCHEMA,'publicOnly':True,'manifestFile':'manifest.json','manifestSha256':manifest_record['sha256']}))
        _verify_files(output,doc); return doc
    except Exception as exc:
        _failure(output,exc); raise
