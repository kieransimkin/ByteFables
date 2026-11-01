"""Package verified PUBLIC native atlas pixels into lossless image asset bundles.

Rendering stays in FrameRudiments. This reads a completed native benchmark,
checks its saved pixels and emits portable per-identity assets through the host
integration's image exporter. Evidence is unsigned and is not authentication.
"""
from __future__ import annotations

from dataclasses import dataclass
import io
import json
import re
from pathlib import Path
import sys
from typing import Any

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'integrations' / 'framerudiments'))
from bytefables_framerudiments.image_assets import (
    PROFILE, NATIVE_SIZES, ImageAssetError, encode_raster, encode_icon,
    inspect_asset, require_formats, encoder_environment,
)
from tools.artwork_native_benchmark import (
    REPORT_SCHEMA, BACKGROUND, BenchmarkError, LoadedSuite, load_suite,
    project_for_page, _read_json, _json, _sha,
)
from tools.artwork_atlas_readback import _decoded_image, READBACK_SCHEMA, FAMILIES, PALETTES

BUNDLE_SCHEMA = 'bytefables.artwork-asset-bundle.v1'
MAX_REPORT_BYTES = 16 * 1024 * 1024
MAX_OUTPUT_BYTES = 512 * 1024 * 1024
MAX_FILES = 24576
HEX = re.compile(r'[0-9a-f]{64}\Z')
VIEW_FILES = ('index.html', 'gallery.js', 'gallery.css')


class AssetBundleError(ValueError):
    """Evidence mismatch, unsafe path, output collision, or failed image export."""


def _no_links(path: Path) -> Path:
    path = Path(path).absolute()
    for part in (path, *path.parents):
        # Include Windows junction/reparse points, including Python 3.11.
        try:
            info = part.lstat()
        except FileNotFoundError:
            continue
        if part.is_symlink() or getattr(info, 'st_file_attributes', 0) & 0x400:
            raise AssetBundleError('Symlink/reparse paths are not allowed')
    return path


def _file(root: Path, relative: str) -> Path:
    # All references are canonical package paths, not arbitrary URLs or commands.
    if (type(relative) is not str or not relative or relative.startswith('/') or
            '\\' in relative or ':' in relative or
            any(p in ('', '.', '..') for p in relative.split('/'))):
        raise AssetBundleError('Invalid relative asset path')
    path = _no_links(root / relative)
    if not path.is_relative_to(root):
        raise AssetBundleError('Asset path escapes its root')
    return path


def _bytes(path: Path, maximum: int) -> bytes:
    _no_links(path)
    if not path.is_file():
        raise AssetBundleError(f'Missing regular file: {path.name}')
    with path.open('rb') as stream:
        data = stream.read(maximum + 1)
    if len(data) > maximum:
        raise AssetBundleError('Input exceeds byte budget')
    return data


def _expect(condition: bool, message: str) -> None:
    if not condition:
        raise AssetBundleError(message)


@dataclass(frozen=True)
class Evidence:
    suite: LoadedSuite
    root: Path
    report: dict[str, Any]
    report_sha: str
    readbacks: dict[str, dict[str, Any]]


def load_evidence(suite_file: Path, benchmark: Path) -> Evidence:
    suite_file = _no_links(suite_file)
    # load_suite checks referenced plan files; this also rejects linked ancestors.
    _no_links(suite_file.parent / 'plans')
    suite = load_suite(suite_file)
    root = _no_links(benchmark)
    _expect(root.is_dir() and not (root / 'failure.json').exists(), 'Benchmark is missing or marked failed')
    report, report_sha = _read_json(_file(root, 'report.json'), MAX_REPORT_BYTES)
    _expect(type(report) is dict and report.get('schema') == REPORT_SCHEMA and
            report.get('status') == 'passed' and report.get('publicOnly') is True and
            report.get('guarantee') == 'presentation-only' and
            report.get('nativeHostExecuted') is True and
            report.get('renderAPI') == 'framerudiments.compositor.Compositor.frame',
            'Expected completed PUBLIC native benchmark evidence')
    _expect(report.get('suiteFileSha256') == suite.source_sha256 and report.get('corpus') == suite.corpus,
            'Benchmark suite/corpus binding mismatch')
    cases = report.get('cases')
    _expect(type(cases) is list and len(cases) == len(suite.cases), 'Benchmark case count mismatch')
    clock = report.get('clockFixture', {})
    _expect(type(clock) is dict and clock.get('kind') == 'explicit-synthetic-silent-pcm',
            'Missing synthetic benchmark clock provenance')
    _expect(_sha(_bytes(_file(root, 'fixture-clock.wav'), 100000)) == clock.get('sha256'),
            'Benchmark clock checksum mismatch')
    readbacks = {}
    for source, claimed in zip(suite.cases, cases):
        _expect(type(claimed) is dict and all(claimed.get(k) == v for k, v in {
            'id': source.id, 'family': source.family, 'palette': source.palette,
            'sourceSize': source.source_size, 'inputCount': source.plan['inputCount'],
            'inputPlanSha256': source.plan_sha256, 'compositedSourceComparison': 'passed',
        }.items()), 'Benchmark case metadata mismatch')
        saved_plan, _ = _read_json(_file(root, f'{source.id}/plan.json'))
        _expect(saved_plan == source.plan, 'Saved native plan differs from suite plan')
        rb, rb_sha = _read_json(_file(root, f'{source.id}/readback.json'), MAX_REPORT_BYTES)
        canonical = json.dumps(source.plan, sort_keys=True, separators=(',', ':'),
                               ensure_ascii=True, allow_nan=False).encode('ascii')
        _expect(type(rb) is dict and rb_sha == claimed.get('readbackSha256') and
                rb.get('schema') == READBACK_SCHEMA and rb.get('publicOnly') is True and
                rb.get('guarantee') == 'presentation-only' and
                rb.get('planCanonicalJsonSha256') == _sha(canonical) and
                rb.get('inputCount') == source.plan['inputCount'] and
                rb.get('pages') == claimed.get('pages'), 'Readback evidence binding mismatch')
        pages = rb.get('pages')
        measures = claimed.get('nativePageMeasurements')
        _expect(type(pages) is list and len(pages) == len(source.plan['pages']) and
                type(measures) is list and len(measures) == len(pages), 'Readback page count mismatch')
        for page, proof, measure in zip(source.plan['pages'], pages, measures):
            _expect(type(proof) is dict and type(measure) is dict, 'Invalid page evidence')
            index = page['index']
            _expect(all(proof.get(k) == v for k, v in {
                'pageIndex': index, 'fileName': f'atlas-page-{index:03d}.png',
                'width': page['width'], 'height': page['height'], 'tileCount': len(page['tiles']),
            }.items()), 'Readback page layout mismatch')
            reference = measure.get('compositedReference', {})
            _expect(measure.get('pageIndex') == index and measure.get('staticSeekPixelsMatch') is True and
                    type(reference) is dict and reference.get('pageIndex') == index and
                    reference.get('sourceAndMatteMatch') is True and reference.get('guttersMatch') is True,
                    'Native source/repeatability comparison did not pass')
            project, _ = _read_json(_file(root, f'{source.id}/project-{index:03d}.json'))
            _expect(project == project_for_page(page, clock['sha256']),
                    'Native project is not the exact unfiltered, non-supersampled benchmark contract')
        readbacks[source.id] = rb
    return Evidence(suite, root, report, report_sha, readbacks)


class _Writer:
    def __init__(self, root: Path):
        self.root, self.total, self.count = root, 0, 0

    def write(self, relative: str, data: bytes) -> dict:
        self.total += len(data)
        self.count += 1
        if self.total > MAX_OUTPUT_BYTES or self.count > MAX_FILES:
            raise AssetBundleError('Bundle exceeds output byte/file budget')
        path = _file(self.root, relative)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open('xb') as stream:
            stream.write(data)
        saved = _bytes(path, len(data))
        _expect(saved == data, 'Saved bytes differ from encoded asset')
        return {'file': relative, 'byteLength': len(saved), 'sha256': _sha(saved)}

    def image(self, relative: str, data: bytes, format: str) -> dict:
        item = self.write(relative, data)
        decoded = inspect_asset(_bytes(_file(self.root, relative), 2 * 1024 * 1024), format)
        return {**item, 'format': format, 'frames': decoded['frames']}


def _group_key(case, tile):
    return (case.family, case.palette, tile['layer']['style']['complexity'], tile['digestHex'])


def _prefix(key) -> str:
    family, palette, complexity, digest = key
    return f'assets/{family}-{palette}-c{complexity}/{digest}'


def _gallery(writer: _Writer, groups: list[dict]) -> list[dict]:
    source = ROOT / 'integrations' / 'web' / 'artwork-assets'
    outputs = [writer.write(name, _bytes(source / name, 256 * 1024)) for name in VIEW_FILES]
    # External classic JS avoids fetch/modules; file:// remains browser-policy dependent.
    data = [{'digest': g['digestHex'], 'family': g['family'], 'palette': g['palette'],
             'complexity': g['complexity'], 'sizes': g['nativeSizes'], 'files': g['files']}
            for g in groups]
    payload = json.dumps(data, separators=(',', ':'), ensure_ascii=True, allow_nan=False)
    return outputs + [writer.write('gallery-data.js', ('window.BYTEFABLES_ASSETS=' + payload + ';\n').encode('ascii'))]


def export_asset_bundle(suite_file: Path, benchmark: Path, output: Path, *,
                        confirm_public: bool = False, formats=('png', 'webp', 'ico')) -> dict:
    if confirm_public is not True:
        raise AssetBundleError('Explicit --confirm-public consent required')
    formats = require_formats(formats)
    output = _no_links(output)
    if output.exists():
        raise AssetBundleError('Output must be a new directory; no overwrite or reuse')
    evidence = load_evidence(suite_file, benchmark)
    source_root = evidence.root
    # Do not put generated artifacts inside either of the evidence trees.
    for root in (source_root, Path(suite_file).absolute().parent):
        if output.is_relative_to(root):
            raise AssetBundleError('Output must be outside the input evidence trees')
    output.parent.mkdir(parents=True, exist_ok=True)
    output.mkdir()
    writer = _Writer(output)
    try:
        groups = {}
        sources = []
        for case, case_proof in zip(evidence.suite.cases, evidence.report['cases']):
            rb = evidence.readbacks[case.id]
            for page, proof, measure in zip(case.plan['pages'], rb['pages'], case_proof['nativePageMeasurements']):
                filename = _file(source_root, f"{case.id}/{proof['fileName']}")
                file_sha, length, image = _decoded_image(filename, (page['width'], page['height']))
                try:
                    _expect(file_sha == proof.get('fileSha256') and length == proof.get('fileBytes') and
                            _sha(image.tobytes()) == proof.get('decodedRGBAsha256'),
                            'Saved atlas page no longer matches its readback receipt')
                    rgb = image.convert('RGB')
                    try:
                        _expect(_sha(rgb.tobytes()) == measure.get('pixelRGBsha256'),
                                'Atlas page differs from native render measurement')
                    finally:
                        rgb.close()
                    _expect(image.getchannel('A').getextrema() == (255, 255),
                            'Native matte benchmark must be fully opaque')
                    sources.append({'caseId': case.id, 'pageIndex': page['index'], **proof})
                    for tile in page['tiles']:
                        key = _group_key(case, tile)
                        group = groups.setdefault(key, {'family': key[0], 'palette': key[1],
                            'complexity': key[2], 'digestHex': key[3], 'inputIndex': tile['inputIndex'],
                            'nativeSizes': [], 'sourceTiles': [], 'files': []})
                        size = case.source_size
                        _expect(size not in group['nativeSizes'], 'Repeated native size for one asset')
                        cropped = image.crop(tuple(tile['rect']))
                        try:
                            pixel_sha = _sha(cropped.tobytes())
                            group['nativeSizes'].append(size)
                            group['sourceTiles'].append({'size': size, 'caseId': case.id,
                                'pageIndex': page['index'], 'rect': tile['rect'], 'rgbaSha256': pixel_sha})
                            for format in formats:
                                if format == 'ico':
                                    continue
                                data = encode_raster(cropped, format)
                                item = writer.image(f'{_prefix(key)}/{size}.{format}', data, format)
                                _expect(item['frames'] == [{'size': size, 'rgbaSha256': pixel_sha}],
                                        'Saved asset differs from original native tile')
                                group['files'].append(item)
                        finally:
                            cropped.close()
                finally:
                    image.close()
        ordered = []
        for key, group in sorted(groups.items()):
            group['nativeSizes'].sort()
            group['sourceTiles'].sort(key=lambda item: item['size'])
            if 'ico' in formats:
                images = {}
                try:
                    for size in group['nativeSizes']:
                        data = _bytes(_file(output, f'{_prefix(key)}/{size}.png'), 2 * 1024 * 1024)
                        with Image.open(io.BytesIO(data), formats=['PNG']) as source:
                            source.load()
                            images[size] = source.convert('RGBA')
                    item = writer.image(f'{_prefix(key)}/icon.ico', encode_icon(images), 'ico')
                    expected = [{'size': p['size'], 'rgbaSha256': p['rgbaSha256']} for p in group['sourceTiles']]
                    _expect(item['frames'] == expected, 'Saved ICO differs from supplied native-size tiles')
                    group['files'].append(item)
                finally:
                    for image in images.values():
                        image.close()
            group['files'].sort(key=lambda item: item['file'])
            identity = {'profile': PROFILE, 'family': group['family'], 'palette': group['palette'],
                        'complexity': group['complexity'], 'digestHex': group['digestHex'],
                        'frames': [{'size': p['size'], 'rgbaSha256': p['rgbaSha256']} for p in group['sourceTiles']]}
            group['assetKey'] = 'bfasset1-' + _sha(_json(identity))
            ordered.append(group)
        # References are verified in full; generated source readback is NOT rerendered here.
        manifest = {'schema': BUNDLE_SCHEMA, 'status': 'passed', 'publicOnly': True,
                    'guarantee': 'presentation-only', 'formats': list(formats),
                    'background': '#111827', 'alpha': 'opaque native compositor matte',
                    'colour': 'untagged RGB samples; no ICC transform', 'resampled': False,
                    'encoder': encoder_environment(),
                    'source': {'suiteFileSha256': evidence.suite.source_sha256,
                               'benchmarkReportSha256': evidence.report_sha,
                               'nativeHostRerunByExporter': False,
                               'evidenceTrust': 'unsigned local benchmark; not authentication',
                               'pages': sources},
                    'assetCount': len(ordered), 'assets': ordered,
                    'warning': 'Display assets only. No byte recovery, ownership or human-recognition guarantee.'}
        manifest['viewerFiles'] = _gallery(writer, ordered)
        # Final marker appears only after every saved asset's readback succeeds.
        writer.write('manifest.json', _json(manifest))
        return manifest
    except Exception as exc:
        (output / 'manifest.json').unlink(missing_ok=True)
        (output / 'failure.json').write_bytes(_json({'status': 'failed', 'exception': type(exc).__name__,
                                                    'message': str(exc)[:1000]}))
        raise


def verify_asset_bundle(directory: Path) -> dict:
    """Verify every exported file and decoded frame against an unsigned manifest."""
    root = _no_links(directory)
    _expect(not (root / 'failure.json').exists(), 'Bundle is marked failed')
    manifest, manifest_sha = _read_json(_file(root, 'manifest.json'), MAX_REPORT_BYTES)
    _expect(type(manifest) is dict and manifest.get('schema') == BUNDLE_SCHEMA and
            manifest.get('status') == 'passed' and manifest.get('publicOnly') is True and
            manifest.get('guarantee') == 'presentation-only' and manifest.get('resampled') is False,
            'Invalid PUBLIC asset bundle manifest')
    assets = manifest.get('assets')
    _expect(type(assets) is list and 1 <= len(assets) <= 8192 and
            type(manifest.get('assetCount')) is int and manifest['assetCount'] == len(assets),
            'Invalid asset count')
    formats = manifest.get('formats')
    _expect(type(formats) is list and formats == [f for f in ('png', 'webp', 'ico') if f in formats]
            and 'png' in formats, 'Invalid bundle format selection')
    seen, identities, total, count = {'manifest.json'}, set(), 0, 0
    for group in assets:
        _expect(type(group) is dict and type(group.get('files')) is list and
                1 <= len(group['files']) <= 9, 'Invalid asset files')
        family, palette = group.get('family'), group.get('palette')
        complexity, digest = group.get('complexity'), group.get('digestHex')
        _expect(type(family) is str and family in FAMILIES and type(palette) is str and palette in PALETTES
                and type(complexity) is int and 1 <= complexity <= 8 and
                type(digest) is str and HEX.fullmatch(digest) is not None and
                type(group.get('inputIndex')) is int and 0 <= group['inputIndex'] < 1000,
                'Invalid asset identity metadata')
        key = (family, palette, complexity, digest)
        _expect(key not in identities, 'Duplicate asset identity/style')
        identities.add(key)
        sizes, tiles = group.get('nativeSizes'), group.get('sourceTiles')
        _expect(type(sizes) is list and 1 <= len(sizes) <= 4 and
                all(type(size) is int and size in NATIVE_SIZES for size in sizes) and
                sizes == sorted(set(sizes)), 'Invalid native size list')
        _expect(type(tiles) is list and len(tiles) == len(sizes), 'Invalid source tile list')
        frames = []
        for size, tile in zip(sizes, tiles):
            _expect(type(tile) is dict and tile.get('size') == size and
                    tile.get('caseId') == f'{family}-{palette}-{size}' and
                    type(tile.get('pageIndex')) is int and 0 <= tile['pageIndex'] < 1000 and
                    type(tile.get('rgbaSha256')) is str and HEX.fullmatch(tile['rgbaSha256']) is not None,
                    'Invalid source tile binding')
            rect = tile.get('rect')
            _expect(type(rect) is list and len(rect) == 4 and
                    all(type(v) is int and 0 <= v <= 7680 for v in rect) and
                    rect[2]-rect[0] == size and rect[3]-rect[1] == size, 'Invalid source tile rectangle')
            frames.append({'size': size, 'rgbaSha256': tile['rgbaSha256']})
        identity = {'profile': PROFILE, 'family': family, 'palette': palette,
                    'complexity': complexity, 'digestHex': digest, 'frames': frames}
        _expect(group.get('assetKey') == 'bfasset1-' + _sha(_json(identity)), 'Asset pixel/cache key mismatch')
        expected_paths = {f'{_prefix(key)}/{size}.{fmt}' for fmt in formats if fmt != 'ico' for size in sizes}
        if 'ico' in formats:
            expected_paths.add(f'{_prefix(key)}/icon.ico')
        _expect(len(group['files']) == len(expected_paths), 'Missing or extra native asset output')
        for item in group['files']:
            _expect(type(item) is dict and type(item.get('file')) is str, 'Invalid asset path')
            path = _file(root, item['file'])
            _expect(item['file'] not in seen and item['file'] in expected_paths, 'Unexpected or repeated asset path')
            _expect(item.get('format') in formats and path.suffix == '.' + item['format'], 'Asset format mismatch')
            expected_frames = frames if item['format'] == 'ico' else [p for p in frames if str(p['size']) == path.stem]
            _expect(item.get('frames') == expected_frames, 'Asset/source pixel binding mismatch')
            data = _bytes(path, 2 * 1024 * 1024)
            count += 1
            total += len(data)
            _expect(count <= MAX_FILES and total <= MAX_OUTPUT_BYTES, 'Bundle exceeds readback budget')
            actual = inspect_asset(data, item['format'])
            _expect(all(actual.get(k) == item.get(k) for k in ('format', 'byteLength', 'sha256', 'frames')),
                    'Exported asset hash or decoded frame mismatch')
            seen.add(item['file'])
    viewers = manifest.get('viewerFiles')
    _expect(type(viewers) is list and len(viewers) == 4, 'Invalid viewer file inventory')
    _expect({v.get('file') for v in viewers if type(v) is dict} == {*VIEW_FILES, 'gallery-data.js'},
            'Unexpected viewer path')
    for item in viewers:
        data = _bytes(_file(root, item['file']), MAX_REPORT_BYTES)
        _expect(len(data) == item.get('byteLength') and _sha(data) == item.get('sha256'),
                'Viewer file checksum mismatch')
    return {'status': 'passed', 'manifestSha256': manifest_sha, 'assets': len(assets),
            'imageFiles': count, 'decodedPixelsVerified': True,
            'warning': 'Consistency against an unsigned manifest, not authenticity.'}
