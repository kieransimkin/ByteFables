"""Deterministic UASTC+Zstd KTX2 transport and quality verification.

This module delegates compression/transcoding to a pinned Khronos KTX executable.
It never implements a second Basis codec. The existing lossless ByteFables KTX2
bundle remains the reference and identity contract.
"""
from __future__ import annotations

import math
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

from tools.artwork_asset_bundle import _Writer, _bytes, _file, _no_links, _expect, MAX_REPORT_BYTES
from tools.artwork_native_benchmark import _read_json, _json, _sha, _keys
from tools.artwork_transparent_bundle import _new_output, _failure
from tools.artwork_ktx2_bundle import verify_ktx2_bundle, validate_manifest as validate_lossless_manifest
from bytefables_framerudiments.ktx2_arrays import decode_ktx2

SCHEMA = 'bytefables.ktx2-uastc-bundle.v1'
PROFILE = 'bytefables.ktx2-uastc-zstd.v1'
KTX_VERSION = '4.4.2'
MAX_BANK_BYTES = 32 * 1024 * 1024
MAX_COMPRESSED_BYTES = 32 * 1024 * 1024

ENCODER = {
    'codec': 'uastc',
    'uastcQuality': 4,
    'uastcRdo': True,
    'uastcRdoLambda': 0.5,
    'uastcRdoNoMultithreading': True,
    'threads': 1,
    'zstdLevel': 18,
}
LEGACY_QUALITY_POLICY = {
    'minPsnrDb': 30.0,
    'maxMeanAbsoluteError': 8.0,
    'maxAbsoluteError': 96,
    'minAlphaPsnrDb': 34.0,
    'maxAlphaMeanAbsoluteError': 6.0,
    'maxPremultipliedOvershoot': 32,
    'maxPremultipliedViolationFraction': 0.10,
}
QUALITY_POLICY = {
    'version': 'bytefables.uastc-quality-policy.v2',
    'minPsnrDb': 30.0,
    'maxMeanAbsoluteError': 8.0,
    'minAlphaPsnrDb': 34.0,
    'maxAlphaMeanAbsoluteError': 6.0,
    'maxPremultipliedOvershoot': 32,
    'maxPremultipliedViolationFraction': 0.10,
}
RAW_RE = re.compile(r'(?:^|_)level(\d+)(?:_face\d+)?_layer(\d+)(?:_depth\d+)?\.raw$', re.I)
HEX = re.compile(r'^[0-9a-f]{64}$')


def _int(value, lo, hi):
    return type(value) is int and lo <= value <= hi


def _hex(value):
    return type(value) is str and HEX.fullmatch(value) is not None


def _run(command: list[str], *, timeout: int = 180) -> subprocess.CompletedProcess:
    result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            text=True, timeout=timeout, check=False)
    if result.returncode != 0:
        tail = (result.stderr or result.stdout or '')[-4000:]
        raise ValueError(f"KTX command failed ({result.returncode}): {' '.join(command[:4])}\n{tail}")
    return result


def ktx_version(executable: Path) -> str:
    path = _no_links(executable)
    _expect(path.is_file(), 'A concrete Khronos ktx executable is required')
    result = _run([str(path), '--version'], timeout=30)
    text = (result.stdout + '\n' + result.stderr).strip()
    match = re.search(r'(?<!\d)(\d+\.\d+\.\d+)(?!\d)', text)
    _expect(match is not None and match.group(1) == KTX_VERSION,
            f'KTX {KTX_VERSION} is required; got {text[:200]!r}')
    return match.group(1)


def encode_command(executable: Path, source: Path, output: Path) -> list[str]:
    return [str(executable), 'encode', '--codec', ENCODER['codec'],
            '--uastc-quality', str(ENCODER['uastcQuality']), '--uastc-rdo',
            '--uastc-rdo-l', str(ENCODER['uastcRdoLambda']), '--uastc-rdo-m',
            '--threads', str(ENCODER['threads']), '--zstd', str(ENCODER['zstdLevel']),
            str(source), str(output)]


def _validate_ktx(executable: Path, file: Path) -> None:
    # ByteFables' frozen lossless profile carries one intentional custom K/V key,
    # org.bytefables.profile. Khronos KTX 4.4.2 reports that standards-compliant
    # extension metadata as warning-7010; --warnings-as-errors therefore rejects
    # our own canonical files after UASTC encoding. Run normal validation, then
    # fail closed on every warning except that exact known key/code.
    result = _run([str(executable), 'validate', str(file)], timeout=90)
    text = (result.stdout + '\n' + result.stderr).strip()
    warnings = re.findall(r'warning-(\d+)', text, flags=re.I)
    if warnings:
        _expect(all(code == '7010' for code in warnings) and 'org.bytefables.profile' in text,
                f'Unexpected KTX validation warning: {text[-2000:]}')


def _extract_rgba8(executable: Path, file: Path, size: int, layers: int) -> tuple[bytes, ...]:
    levels = size.bit_length()
    with tempfile.TemporaryDirectory(prefix='bytefables-uastc-extract-') as td:
        out = Path(td) / 'images'
        _run([str(executable), 'extract', '--transcode', 'rgba8', '--all', '--raw', str(file), str(out)], timeout=180)
        found: dict[tuple[int, int], bytes] = {}
        for path in out.rglob('*.raw') if out.exists() else ():
            match = RAW_RE.search(path.name)
            _expect(match is not None, f'Unexpected Khronos raw extraction name: {path.name}')
            level, layer = int(match.group(1)), int(match.group(2))
            _expect(0 <= level < levels and 0 <= layer < layers and (level, layer) not in found,
                    'Duplicate/out-of-range extracted image')
            side = size >> level
            raw = _bytes(_no_links(path), side * side * 4)
            _expect(len(raw) == side * side * 4, 'Transcoded image byte count mismatch')
            found[(level, layer)] = raw
        _expect(len(found) == levels * layers, 'Khronos extraction did not return every mip/layer')
        result = []
        for level in range(levels):
            result.append(b''.join(found[(level, layer)] for layer in range(layers)))
        return tuple(result)


def _accumulator() -> dict:
    return {'samples': 0, 'pixels': 0, 'abs': 0, 'sq': 0, 'max': 0,
            'alphaSamples': 0, 'alphaAbs': 0, 'alphaSq': 0, 'alphaMax': 0,
            'violations': 0, 'maxOvershoot': 0}


def _accumulate(acc: dict, reference: bytes, decoded: bytes) -> None:
    _expect(len(reference) == len(decoded) and len(reference) % 4 == 0, 'Metric byte count mismatch')
    for at in range(0, len(reference), 4):
        acc['pixels'] += 1
        alpha_error = abs(reference[at + 3] - decoded[at + 3])
        acc['alphaSamples'] += 1; acc['alphaAbs'] += alpha_error; acc['alphaSq'] += alpha_error * alpha_error
        acc['alphaMax'] = max(acc['alphaMax'], alpha_error)
        for c in range(4):
            error = abs(reference[at + c] - decoded[at + c])
            acc['samples'] += 1; acc['abs'] += error; acc['sq'] += error * error; acc['max'] = max(acc['max'], error)
        overshoot = max(decoded[at], decoded[at + 1], decoded[at + 2]) - decoded[at + 3]
        if overshoot > 0:
            acc['violations'] += 1; acc['maxOvershoot'] = max(acc['maxOvershoot'], overshoot)


def _psnr(square_sum: int, samples: int) -> float:
    if square_sum == 0:
        return 999.0
    mse = square_sum / samples
    return 20.0 * math.log10(255.0 / math.sqrt(mse))


def _summary(acc: dict) -> dict:
    _expect(acc['samples'] > 0 and acc['pixels'] > 0 and acc['alphaSamples'] > 0, 'Empty compression metrics')
    return {
        'sampleBytes': acc['samples'], 'pixelCount': acc['pixels'],
        'meanAbsoluteError': round(acc['abs'] / acc['samples'], 6),
        'maxAbsoluteError': acc['max'], 'psnrDb': round(_psnr(acc['sq'], acc['samples']), 6),
        'alphaMeanAbsoluteError': round(acc['alphaAbs'] / acc['alphaSamples'], 6),
        'alphaMaxAbsoluteError': acc['alphaMax'], 'alphaPsnrDb': round(_psnr(acc['alphaSq'], acc['alphaSamples']), 6),
        'premultipliedViolations': acc['violations'],
        'premultipliedViolationFraction': round(acc['violations'] / acc['pixels'], 8),
        'maxPremultipliedOvershoot': acc['maxOvershoot'],
    }


def _validate_metrics(metrics: dict) -> None:
    _keys(metrics, {'sampleBytes','pixelCount','meanAbsoluteError','maxAbsoluteError','psnrDb',
                    'alphaMeanAbsoluteError','alphaMaxAbsoluteError','alphaPsnrDb',
                    'premultipliedViolations','premultipliedViolationFraction','maxPremultipliedOvershoot'}, 'UASTC metrics')
    for k in ('sampleBytes','pixelCount','maxAbsoluteError','alphaMaxAbsoluteError','premultipliedViolations','maxPremultipliedOvershoot'):
        _expect(_int(metrics[k],0,1<<31), f'Invalid metric {k}')
    for k in ('meanAbsoluteError','psnrDb','alphaMeanAbsoluteError','alphaPsnrDb','premultipliedViolationFraction'):
        _expect(type(metrics[k]) in (int,float) and math.isfinite(metrics[k]), f'Invalid metric {k}')


def _quality(metrics: dict, policy: dict = QUALITY_POLICY) -> None:
    _validate_metrics(metrics)
    _expect(metrics['psnrDb'] >= policy['minPsnrDb'], 'UASTC PSNR below policy')
    _expect(metrics['meanAbsoluteError'] <= policy['maxMeanAbsoluteError'], 'UASTC mean error above policy')
    if 'maxAbsoluteError' in policy:
        _expect(metrics['maxAbsoluteError'] <= policy['maxAbsoluteError'], 'UASTC peak error above legacy policy')
    _expect(metrics['alphaPsnrDb'] >= policy['minAlphaPsnrDb'], 'UASTC alpha PSNR below policy')
    _expect(metrics['alphaMeanAbsoluteError'] <= policy['maxAlphaMeanAbsoluteError'], 'UASTC alpha mean error above policy')
    _expect(metrics['maxPremultipliedOvershoot'] <= policy['maxPremultipliedOvershoot'], 'UASTC premultiplied overshoot above policy')
    _expect(metrics['premultipliedViolationFraction'] <= policy['maxPremultipliedViolationFraction'],
            'UASTC premultiplied violation rate above policy')


def _decoded_records(levels: tuple[bytes, ...], size: int) -> list[dict]:
    return [{'level': level, 'size': size >> level, 'byteLength': len(raw), 'sha256': _sha(raw)}
            for level, raw in enumerate(levels)]


def validate_manifest(doc: dict) -> dict:
    _keys(doc, {'schema','profile','status','publicOnly','guarantee','tool','encoder','qualityPolicy',
                'sourceTransport','sourceManifest','banks','totals'}, 'UASTC manifest')
    _expect(doc['schema'] == SCHEMA and doc['profile'] == PROFILE and doc['status'] == 'passed' and
            doc['publicOnly'] is True and doc['guarantee'] == 'presentation-only', 'Unsupported UASTC bundle')
    _expect(doc['encoder'] == ENCODER and doc['qualityPolicy'] in (QUALITY_POLICY, LEGACY_QUALITY_POLICY), 'Unexpected UASTC encoder/quality policy')
    tool = doc['tool']; _keys(tool, {'name','version'}, 'UASTC tool')
    _expect(tool == {'name':'Khronos KTX-Software','version':KTX_VERSION}, 'Unexpected UASTC tool version')
    for key, name in (('sourceTransport','source-transport.json'),('sourceManifest','source-manifest.json')):
        rec = doc[key]; _keys(rec, {'file','byteLength','sha256'}, key)
        _expect(rec['file'] == name and _int(rec['byteLength'],1,MAX_REPORT_BYTES) and _hex(rec['sha256']), 'Invalid source binding')
    _expect(type(doc['banks']) is list and 1 <= len(doc['banks']) <= 16, 'Invalid UASTC bank count')
    source_total = compressed_total = 0
    aggregate = _accumulator()
    for index, bank in enumerate(doc['banks']):
        _keys(bank, {'index','layerCount','sourceFile','sourceByteLength','sourceSha256','file','byteLength','sha256',
                     'compressionRatio','decodedLevels','metrics'}, 'UASTC bank')
        _expect(bank['index'] == index and _int(bank['layerCount'],1,256) and
                bank['sourceFile'] == f'banks/bank-{index:03d}.ktx2' and bank['file'] == f'banks/bank-{index:03d}.uastc.ktx2' and
                _int(bank['sourceByteLength'],80,MAX_BANK_BYTES) and _hex(bank['sourceSha256']) and
                _int(bank['byteLength'],80,MAX_COMPRESSED_BYTES) and _hex(bank['sha256']), 'Invalid UASTC bank record')
        _expect(type(bank['compressionRatio']) in (int,float) and bank['compressionRatio'] > 0, 'Invalid compression ratio')
        levels = bank['decodedLevels']; _expect(type(levels) is list and 5 <= len(levels) <= 8, 'Invalid decoded mip inventory')
        for level, rec in enumerate(levels):
            _keys(rec, {'level','size','byteLength','sha256'}, 'decoded level')
            _expect(rec['level'] == level and _int(rec['size'],1,128) and _int(rec['byteLength'],4,MAX_BANK_BYTES) and _hex(rec['sha256']), 'Invalid decoded level')
        metrics = bank['metrics']; _quality(metrics)
        source_total += bank['sourceByteLength']; compressed_total += bank['byteLength']
        # Aggregate summaries are separately recomputed during source-backed verification.
    totals = doc['totals']; _keys(totals, {'sourceBytes','compressedBytes','compressionRatio','metrics'}, 'UASTC totals')
    _expect(totals['sourceBytes'] == source_total and totals['compressedBytes'] == compressed_total and
            type(totals['compressionRatio']) in (int,float) and totals['compressionRatio'] > 0, 'UASTC total bytes mismatch')
    _quality(totals['metrics'])
    return doc


def _source_docs(root: Path):
    result = verify_ktx2_bundle(root)
    transport, transport_sha = _read_json(_file(root,'manifest.json'), MAX_REPORT_BYTES)
    source, source_sha = _read_json(_file(root,'source-manifest.json'), MAX_REPORT_BYTES)
    _expect(transport_sha == result['manifestSha256'] and transport['sourceManifest']['sha256'] == source_sha,
            'Lossless KTX2 source changed')
    return transport, transport_sha, source, source_sha


def _verify_bank(exe: Path, compressed: Path, source_bytes: bytes, size: int, layers: int,
                 expected_levels: list[dict] | None = None) -> tuple[tuple[bytes,...], dict]:
    _validate_ktx(exe, compressed)
    decoded = _extract_rgba8(exe, compressed, size, layers)
    source = decode_ktx2(source_bytes)
    _expect(source.size == size and source.layers == layers and len(source.levels) == len(decoded), 'Source/transcode geometry mismatch')
    if expected_levels is not None:
        _expect(_decoded_records(decoded,size) == expected_levels, 'UASTC transcode bytes changed')
    acc = _accumulator()
    for a,b in zip(source.levels, decoded): _accumulate(acc,a,b)
    metrics = _summary(acc); _quality(metrics)
    return decoded, metrics


def export_uastc_bundle(bundle: Path, output: Path, *, ktx: Path, confirm_public: bool = False,
                        verify_determinism: bool = True) -> dict:
    _expect(confirm_public is True, 'Explicit --confirm-public consent required')
    exe = _no_links(ktx); ktx_version(exe)
    root = _no_links(bundle); output = _new_output(output,(root,exe)); output.mkdir(parents=True)
    transport, transport_sha, source, source_sha = _source_docs(root)
    writer = _Writer(output); quality_diagnostics = []
    try:
        source_transport = writer.write('source-transport.json', _bytes(_file(root,'manifest.json'),MAX_REPORT_BYTES))
        source_manifest = writer.write('source-manifest.json', _bytes(_file(root,'source-manifest.json'),MAX_REPORT_BYTES))
        _expect(source_transport['sha256'] == transport_sha and source_manifest['sha256'] == source_sha, 'Copied source metadata changed')
        banks = []; total_acc = _accumulator(); total_source = total_compressed = 0
        for record in transport['banks']:
            index = record['index']; src_path = _file(root,record['file']); src = _bytes(src_path,record['byteLength'])
            _expect(len(src) == record['byteLength'] and _sha(src) == record['sha256'], 'Lossless source bank changed')
            dest_rel = f'banks/bank-{index:03d}.uastc.ktx2'; dest = output/dest_rel; dest.parent.mkdir(parents=True,exist_ok=True)
            _run(encode_command(exe,src_path,dest),timeout=300)
            _validate_ktx(exe,dest)
            encoded = _bytes(_no_links(dest),MAX_COMPRESSED_BYTES)
            _expect(80 <= len(encoded) <= MAX_COMPRESSED_BYTES, 'Compressed bank size invalid')
            if verify_determinism:
                with tempfile.TemporaryDirectory(prefix='bytefables-uastc-repeat-') as td:
                    repeat = Path(td)/'repeat.ktx2'; _run(encode_command(exe,src_path,repeat),timeout=300)
                    _expect(_bytes(_no_links(repeat),MAX_COMPRESSED_BYTES) == encoded, 'Pinned UASTC encoding is not deterministic')
            decoded, metrics = _verify_bank(exe,dest,src,source['nativeSize'],record['layerCount'])
            quality_diagnostics.append({'bank': index, 'metrics': metrics})
            _quality(metrics)
            acc_source = decode_ktx2(src)
            for a,b in zip(acc_source.levels,decoded): _accumulate(total_acc,a,b)
            banks.append({'index':index,'layerCount':record['layerCount'],'sourceFile':record['file'],
                          'sourceByteLength':record['byteLength'],'sourceSha256':record['sha256'],
                          'file':dest_rel,'byteLength':len(encoded),'sha256':_sha(encoded),
                          'compressionRatio':round(len(encoded)/record['byteLength'],6),
                          'decodedLevels':_decoded_records(decoded,source['nativeSize']),'metrics':metrics})
            total_source += record['byteLength']; total_compressed += len(encoded)
        total_metrics = _summary(total_acc); quality_diagnostics.append({'aggregate': True, 'metrics': total_metrics}); _quality(total_metrics)
        doc = {'schema':SCHEMA,'profile':PROFILE,'status':'passed','publicOnly':True,'guarantee':'presentation-only',
               'tool':{'name':'Khronos KTX-Software','version':KTX_VERSION},'encoder':ENCODER.copy(),
               'qualityPolicy':QUALITY_POLICY.copy(),'sourceTransport':source_transport,'sourceManifest':source_manifest,
               'banks':banks,'totals':{'sourceBytes':total_source,'compressedBytes':total_compressed,
                   'compressionRatio':round(total_compressed/total_source,6),'metrics':total_metrics}}
        validate_manifest(doc); writer.write('manifest.json',_json(doc))
        return doc
    except Exception as exc:
        if quality_diagnostics:
            (output/'quality-failure.json').write_bytes(_json({'schema':'bytefables.uastc-quality-diagnostics.v1','qualityPolicy':QUALITY_POLICY,'completed':quality_diagnostics}))
        _failure(output,exc); raise


def verify_uastc_bundle(bundle: Path, *, ktx: Path, source_bundle: Path | None = None) -> dict:
    exe = _no_links(ktx); ktx_version(exe); root = _no_links(bundle)
    _expect(root.is_dir() and not (root/'failure.json').exists(), 'UASTC bundle absent or failed')
    doc, digest = _read_json(_file(root,'manifest.json'),MAX_REPORT_BYTES); validate_manifest(doc)
    transport_bytes = _bytes(_file(root,'source-transport.json'),doc['sourceTransport']['byteLength'])
    source_bytes = _bytes(_file(root,'source-manifest.json'),doc['sourceManifest']['byteLength'])
    _expect(_sha(transport_bytes)==doc['sourceTransport']['sha256'] and _sha(source_bytes)==doc['sourceManifest']['sha256'], 'UASTC source metadata changed')
    transport = __import__('json').loads(transport_bytes); source = __import__('json').loads(source_bytes)
    validate_lossless_manifest(transport, source)
    _expect(_sha(source_bytes) == transport['sourceManifest']['sha256'], 'Copied lossless source-manifest binding changed')
    reference_root = root
    if source_bundle is not None:
        reference_root = _no_links(source_bundle); result = verify_ktx2_bundle(reference_root)
        _expect(result['manifestSha256']==doc['sourceTransport']['sha256'], 'UASTC source bundle binding mismatch')
    total_acc = _accumulator(); source_total = compressed_total = 0
    for bank, source_record in zip(doc['banks'],transport['banks']):
        _expect(bank['index']==source_record['index'] and bank['layerCount']==source_record['layerCount'] and
                bank['sourceFile']==source_record['file'] and bank['sourceByteLength']==source_record['byteLength'] and
                bank['sourceSha256']==source_record['sha256'], 'UASTC source bank binding mismatch')
        if source_bundle is not None:
            src = _bytes(_file(reference_root,source_record['file']),source_record['byteLength'])
        else:
            # Internal-only verification proves deterministic transcode bytes and manifest/checksum integrity.
            # Error metrics need original source bytes and are therefore trusted from the signed-by-checksum manifest here.
            src = None
        compressed = _file(root,bank['file']); raw = _bytes(compressed,bank['byteLength'])
        _expect(len(raw)==bank['byteLength'] and _sha(raw)==bank['sha256'],'UASTC compressed bank checksum mismatch')
        _validate_ktx(exe,compressed)
        decoded = _extract_rgba8(exe,compressed,source['nativeSize'],bank['layerCount'])
        _expect(_decoded_records(decoded,source['nativeSize'])==bank['decodedLevels'],'UASTC decoded image checksums changed')
        if src is not None:
            parsed=decode_ktx2(src); acc=_accumulator()
            for a,b in zip(parsed.levels,decoded): _accumulate(acc,a,b); _accumulate(total_acc,a,b)
            metrics=_summary(acc); _expect(metrics==bank['metrics'],'UASTC quality metrics changed'); _quality(metrics)
        source_total+=bank['sourceByteLength'];compressed_total+=bank['byteLength']
    if source_bundle is not None:
        total_metrics=_summary(total_acc); _expect(total_metrics==doc['totals']['metrics'],'UASTC aggregate metrics changed'); _quality(total_metrics)
    _expect(source_total==doc['totals']['sourceBytes'] and compressed_total==doc['totals']['compressedBytes'],'UASTC totals changed')
    actual=set()
    for p in root.rglob('*'):
        _no_links(p)
        if p.is_file():actual.add(p.relative_to(root).as_posix())
    expected={'manifest.json','source-transport.json','source-manifest.json',*(b['file'] for b in doc['banks'])}
    _expect(actual==expected,'Unexpected or missing UASTC bundle files')
    return {'status':'passed','manifestSha256':digest,'banks':len(doc['banks']),
            'sourceBytes':source_total,'compressedBytes':compressed_total,
            'compressionRatio':doc['totals']['compressionRatio'],'sourceCompared':source_bundle is not None,
            'quality':doc['totals']['metrics']}
