"""Verified transparent PUBLIC artwork source bundles; opaque v1 is unchanged.

Exports source pixels from the existing pinned FrameRudiments plugin, checks
recomposition against actual saved native atlas pixels, and re-decodes outputs.
A separate qualification command runs the REAL compositor on black and white.
Unsigned evidence binds files and settings, not authorship or authorization.
"""
from __future__ import annotations

import html
import io
from pathlib import Path
from typing import Any
from PIL import Image

from tools.artwork_asset_bundle import (
    AssetBundleError, _Writer, _bytes, _file, _no_links, _expect, load_evidence,
    MAX_REPORT_BYTES, _prefix, _group_key,
)
from tools.artwork_native_benchmark import (
    _sha, _json, _read_json, _keys, _native_api, project_for_page, BACKGROUND, HEX,
)
from tools.artwork_atlas_readback import _decoded_image, FAMILIES, PALETTES
from bytefables_framerudiments.image_assets import (
    encode_raster, encode_icon, inspect_asset, require_formats, _frames, NATIVE_SIZES, encoder_environment,
)
from bytefables_framerudiments.transparent_assets import (
    PROFILE, source_rgba, generator_sha256, alpha_statistics, composite_rgb,
)

SCHEMA = 'bytefables.transparent-artwork-bundle.v1'
QUALIFICATION = 'bytefables.transparent-native-mattes.v1'
MAX_GROUPS = 1024
MAX_SOURCE_PIXELS = 32 * 1024 * 1024
MATTES = {'black': (0, 0, 0), 'white': (255, 255, 255)}


def _source_evidence(suite_file: Path, benchmark: Path):
    evidence = load_evidence(suite_file, benchmark)
    env = evidence.report.get('environment', {})
    _expect(type(env) is dict and env.get('artworkPythonSha256') == generator_sha256(),
            'Generator source hash differs from the completed native benchmark; rerun benchmark')
    pixels = sum(c.source_size ** 2 * c.plan['inputCount'] for c in evidence.suite.cases)
    groups = {_group_key(c, t) for c in evidence.suite.cases for p in c.plan['pages'] for t in p['tiles']}
    _expect(len(groups) <= MAX_GROUPS and pixels <= MAX_SOURCE_PIXELS,
            'Transparent source workload exceeds group/pixel budget')
    return evidence


def _pages(evidence):
    """Yield decoded, checksum-bound native pages, closing each after use."""
    for case in evidence.suite.cases:
        proofs = evidence.readbacks[case.id]['pages']
        for page, proof in zip(case.plan['pages'], proofs):
            path = _file(evidence.root, f"{case.id}/{proof['fileName']}")
            file_sha, count, decoded = _decoded_image(path, (page['width'], page['height']))
            try:
                _expect(file_sha == proof['fileSha256'] and count == proof['fileBytes'] and
                        _sha(decoded.tobytes()) == proof['decodedRGBAsha256'], 'Native atlas pixels changed')
                yield case, page, decoded
            finally:
                decoded.close()


def _new_output(output: Path, inputs: tuple[Path, ...]) -> Path:
    output = _no_links(output)
    _expect(not output.exists(), 'Output must be a new directory; never overwrite')
    for root in inputs:
        root = _no_links(root)
        _expect(not output.is_relative_to(root) and not root.is_relative_to(output),
                'Output must be separate from input evidence')
    return output


def _failure(root: Path, exc: Exception) -> None:
    # These names are created only inside our new directory.
    (root / 'manifest.json').unlink(missing_ok=True)
    (root / 'qualification.json').unlink(missing_ok=True)
    with (root / 'failure.json').open('xb') as stream:
        stream.write(_json({'status': 'failed', 'exception': type(exc).__name__, 'message': str(exc)[:1000]}))


def _viewer(writer: _Writer, assets: list[dict]) -> dict:
    cards = []
    for item in assets:
        size = 64 if 64 in item['nativeSizes'] else item['nativeSizes'][-1]
        file = f"{_prefix((item['family'], item['palette'], item['complexity'], item['digestHex']))}/{size}.png"
        label = f"{item['family']} / {item['palette']} / {size}px"
        links = ' '.join(f'<a href="{html.escape(f["file"], quote=True)}" download>{f["format"].upper()} '
                         f'{"/".join(str(fr["size"]) for fr in f["frames"])}</a>' for f in item['files'])
        images = ''.join(f'<figure class="{matte}"><img loading="lazy" width="{size}" height="{size}" '
                         f'src="{file}" alt="{label} {item["digestHex"]}"><figcaption>{matte}</figcaption></figure>'
                         for matte in ('checker', 'black', 'white'))
        cards.append(f'<article><h2>{label}</h2><div class="previews">{images}</div>'
                     f'<code>{item["digestHex"]}</code><p>{links}</p></article>')
    page = '''<!doctype html><html lang="en"><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; img-src 'self'; style-src 'unsafe-inline'; base-uri 'none'; form-action 'none'">
<title>ByteFables transparent source sprites</title>
<style>body{font:16px system-ui;margin:2rem;background:#17202a;color:#eee}h1{font-size:2rem}h2{font-size:1rem}
main{display:grid;grid-template-columns:repeat(auto-fit,minmax(330px,1fr));gap:1rem}article{border:1px solid #526272;padding:1rem;min-width:0}
.previews{display:flex;gap:8px;align-items:start;flex-wrap:wrap}figure{margin:0;padding:8px;text-align:center;color:#eee}figure.white{background:#fff;color:#111}figure.black{background:#000}
.checker{background:repeating-conic-gradient(#58616c 0% 25%,#a8b0b9 0% 50%) 0/16px 16px}img{display:block}figcaption{background:#333;color:#fff;font-size:.75rem}code{display:block;overflow-wrap:anywhere;font-size:.7rem;margin-top:1rem}a{color:#9ce2ff;line-height:2}</style>
<h1>Transparent source sprites</h1><p>Actual source RGBA; no background removal, no resampling. Each preview uses the same PNG on a different CSS background.</p>
<p>Public display artwork only, not a verifier or recoverable encoding. These are not opaque v1 runtime textures.</p><main>''' + ''.join(cards) + '</main></html>\n'
    return writer.write('index.html', page.encode('utf-8'))


def export_transparent_bundle(suite_file: Path, benchmark: Path, output: Path, *,
                              confirm_public: bool = False, formats=('png', 'webp', 'ico')) -> dict:
    if confirm_public is not True:
        raise AssetBundleError('Explicit --confirm-public consent required')
    formats = require_formats(formats)
    output = _new_output(output, (Path(suite_file).absolute().parent, Path(benchmark).absolute()))
    evidence = _source_evidence(suite_file, benchmark)
    output.mkdir(parents=True)
    writer = _Writer(output)
    groups: dict[tuple, dict[int, Image.Image]] = {}
    records: dict[tuple, dict[int, dict]] = {}
    try:
        for case, page, decoded in _pages(evidence):
            for tile in page['tiles']:
                key = _group_key(case, tile)
                images = groups.setdefault(key, {})
                _expect(case.source_size not in images, 'Duplicate transparent source size')
                source = source_rgba(case.source_size, tile['layer']['style'])
                images[case.source_size] = source
                with decoded.crop(tuple(tile['rect'])) as crop, crop.convert('RGB') as native:
                    with composite_rgb(source, BACKGROUND) as expected:
                        _expect(native.tobytes() == expected.tobytes(), 'Transparent source does not match native matte')
                    stats = alpha_statistics(source)
                    _expect(stats['transparentPixels'] > 0 and stats['opaquePixels'] + stats['partialPixels'] > 0,
                            'Expected visible source artwork with real transparency')
                    records.setdefault(key, {})[case.source_size] = {
                        'size': case.source_size, 'rgbaSha256': _sha(source.tobytes()), 'alpha': stats,
                        'nativeRGBsha256': _sha(native.tobytes()),
                        'caseId': case.id, 'pageIndex': page['index'], 'inputIndex': tile['inputIndex'],
                    }
        assets = []
        for key, images in sorted(groups.items()):
            family, palette, complexity, digest = key
            files = []
            for size, source in sorted(images.items()):
                for format in formats:
                    if format != 'ico':
                        files.append(writer.image(f'{_prefix(key)}/{size}.{format}', encode_raster(source, format), format))
            if 'ico' in formats:
                files.append(writer.image(f'{_prefix(key)}/icon.ico', encode_icon(images), 'ico'))
            assets.append({'family': family, 'palette': palette, 'complexity': complexity,
                           'digestHex': digest, 'nativeSizes': sorted(images),
                           'sources': [records[key][size] for size in sorted(images)], 'files': files})
        document = {'schema': SCHEMA, 'publicOnly': True, 'guarantee': 'presentation-only',
                    'profile': PROFILE, 'alpha': 'straight-unassociated-source-rgba', 'resampled': False,
                    'formats': list(formats), 'assetCount': len(assets), 'assets': assets,
                    'source': {'suiteFileSha256': evidence.suite.source_sha256,
                               'benchmarkReportSha256': evidence.report_sha,
                               'artworkPythonSha256': generator_sha256(),
                               'nativeHostRerunByExporter': False, 'nativeMatte': list(BACKGROUND),
                               'nativeMatteComparison': 'passed', 'additionalNativeMattes': 'not-run'},
                    'encoder': encoder_environment(), 'viewer': _viewer(writer, assets)}
        _verify(output, document)
        writer.write('manifest.json', _json(document))  # Success marker last.
        return document
    except Exception as exc:
        _failure(output, exc)
        raise
    finally:
        for images in groups.values():
            for image in images.values():
                image.close()


def _verify(root: Path, document: dict) -> dict:
    _keys(document, {'schema', 'publicOnly', 'guarantee', 'profile', 'alpha', 'resampled',
                     'formats', 'assetCount', 'assets', 'source', 'encoder', 'viewer'}, 'transparent manifest')
    _expect(document['schema'] == SCHEMA and document['profile'] == PROFILE and document['publicOnly'] is True and
            document['guarantee'] == 'presentation-only' and document['resampled'] is False and
            document['alpha'] == 'straight-unassociated-source-rgba', 'Unsupported transparent bundle contract')
    formats = require_formats(document['formats'])
    _expect(list(formats) == document['formats'], 'Noncanonical format order')
    src = document['source']
    _keys(src, {'suiteFileSha256', 'benchmarkReportSha256', 'artworkPythonSha256', 'nativeHostRerunByExporter',
                'nativeMatte', 'nativeMatteComparison', 'additionalNativeMattes'}, 'source evidence')
    _expect(all(type(src[k]) is str and HEX.fullmatch(src[k]) for k in
                ('suiteFileSha256', 'benchmarkReportSha256', 'artworkPythonSha256')) and
            src['nativeHostRerunByExporter'] is False and src['nativeMatte'] == list(BACKGROUND) and
            src['nativeMatteComparison'] == 'passed' and src['additionalNativeMattes'] == 'not-run',
            'Invalid transparent source evidence')
    assets = document['assets']
    _expect(type(assets) is list and 1 <= len(assets) <= MAX_GROUPS and
            type(document['assetCount']) is int and document['assetCount'] == len(assets), 'Invalid asset count')
    keys, files, pixels = set(), set(), 0
    for item in assets:
        _keys(item, {'family', 'palette', 'complexity', 'digestHex', 'nativeSizes', 'sources', 'files'}, 'asset')
        _expect(type(item['family']) is str and item['family'] in FAMILIES and
                type(item['palette']) is str and item['palette'] in PALETTES and
                type(item['complexity']) is int and 1 <= item['complexity'] <= 8 and
                type(item['digestHex']) is str and HEX.fullmatch(item['digestHex']), 'Invalid public artwork identity')
        key = (item['family'], item['palette'], item['complexity'], item['digestHex'])
        _expect(key not in keys, 'Duplicate artwork identity'); keys.add(key)
        sizes = item['nativeSizes']
        _expect(type(sizes) is list and 1 <= len(sizes) <= 4 and
                all(type(s) is int and s in NATIVE_SIZES for s in sizes) and sizes == sorted(set(sizes)), 'Invalid native sizes')
        pixels += sum(size * size for size in sizes)
        _expect(pixels <= MAX_SOURCE_PIXELS, 'Decoded pixel workload exceeded')
        _expect(type(item['sources']) is list and len(item['sources']) == len(sizes), 'Missing source frames')
        sources = {}
        for size, ref in zip(sizes, item['sources']):
            _keys(ref, {'size', 'rgbaSha256', 'alpha', 'nativeRGBsha256', 'caseId', 'pageIndex', 'inputIndex'}, 'source frame')
            _expect(type(ref['size']) is int and ref['size'] == size and
                    ref['caseId'] == f"{key[0]}-{key[1]}-{size}" and
                    all(type(ref[k]) is str and HEX.fullmatch(ref[k]) for k in ('rgbaSha256', 'nativeRGBsha256')) and
                    all(type(ref[k]) is int and 0 <= ref[k] < 1000 for k in ('pageIndex', 'inputIndex')),
                    'Invalid source frame reference')
            _keys(ref['alpha'], {'transparentPixels', 'partialPixels', 'opaquePixels', 'totalPixels', 'alphaSha256'}, 'alpha stats')
            _expect(all(type(ref['alpha'][k]) is int and 0 <= ref['alpha'][k] <= size*size for k in
                        ('transparentPixels', 'partialPixels', 'opaquePixels', 'totalPixels')) and
                    ref['alpha']['transparentPixels'] > 0 and ref['alpha']['totalPixels'] == size*size and
                    0 < ref['alpha']['partialPixels'] + ref['alpha']['opaquePixels'] < size*size and
                    sum(ref['alpha'][k] for k in ('transparentPixels', 'partialPixels', 'opaquePixels')) == size*size and
                    type(ref['alpha']['alphaSha256']) is str and HEX.fullmatch(ref['alpha']['alphaSha256']),
                    'Invalid source alpha statistics')
            sources[size] = ref
        expected_files = {f'{_prefix(key)}/{s}.{f}' for s in sizes for f in formats if f != 'ico'}
        if 'ico' in formats: expected_files.add(f'{_prefix(key)}/icon.ico')
        _expect(type(item['files']) is list and len(item['files']) == len(expected_files), 'Missing image files')
        for f in item['files']:
            _keys(f, {'file', 'byteLength', 'sha256', 'format', 'frames'}, 'image file')
            _expect(type(f['file']) is str and f['file'] in expected_files and f['file'] not in files and
                    f['format'] in formats and f['file'].endswith('.' + f['format']) and
                    type(f['byteLength']) is int and 0 < f['byteLength'] <= 2*1024*1024,
                    'Unexpected/duplicate image path or format')
            data = _bytes(_file(root, f['file']), 2*1024*1024)
            inspection = inspect_asset(data, f['format'])
            _expect(all(inspection[k] == f[k] for k in ('byteLength', 'sha256', 'format', 'frames')),
                    'Saved transparent image checksum/frames differ')
            frames = _frames(data, f['format'])
            wanted = sizes if f['format'] == 'ico' else [int(Path(f['file']).stem)]
            _expect(sorted(frames) == wanted, 'Native image size changed')
            for size, raw in frames.items():
                with Image.frombytes('RGBA', (size, size), raw) as image:
                    _expect(_sha(raw) == sources[size]['rgbaSha256'] and alpha_statistics(image) == sources[size]['alpha'],
                            'Transparent source pixels or alpha changed')
                    with composite_rgb(image, BACKGROUND) as composite:
                        _expect(_sha(composite.tobytes()) == sources[size]['nativeRGBsha256'], 'Native matte comparison differs')
            files.add(f['file'])
    viewer = document['viewer']
    _keys(viewer, {'file', 'byteLength', 'sha256'}, 'viewer')
    _expect(viewer['file'] == 'index.html' and type(viewer['byteLength']) is int, 'Invalid viewer path')
    content = _bytes(_file(root, 'index.html'), 4*1024*1024)
    _expect(len(content) == viewer['byteLength'] and _sha(content) == viewer['sha256'], 'Viewer integrity mismatch')
    _expect(type(document['encoder']) is dict, 'Invalid encoder evidence')
    return {'status': 'passed', 'assets': len(assets), 'imageFiles': len(files),
            'decodedPixelsVerified': True, 'nativeMatteRecompositionVerified': True,
            'additionalNativeMattes': 'not-run', 'warning': 'Unsigned consistency checks, not authentication.'}


def verify_transparent_bundle(bundle: Path) -> dict:
    root = _no_links(bundle)
    _expect(root.is_dir() and not (root / 'failure.json').exists(), 'Bundle missing or marked failed')
    document, sha = _read_json(_file(root, 'manifest.json'), MAX_REPORT_BYTES)
    return {**_verify(root, document), 'manifestSha256': sha}


def qualify_native_mattes(suite_file: Path, benchmark: Path, bundle: Path, output: Path, *,
                          confirm_public: bool = False) -> dict:
    """Re-run the real compositor against saved source PNGs on black AND white.

    No tolerance, fake registry, background removal or production fallback.
    Success is a separate evidence directory, never injected into the unsigned
    source bundle. Does not claim an independent artwork algorithm.
    """
    if confirm_public is not True:
        raise AssetBundleError('Explicit --confirm-public consent required')
    root = _no_links(bundle)
    check = verify_transparent_bundle(root)
    document, _ = _read_json(_file(root, 'manifest.json'), MAX_REPORT_BYTES)
    evidence = _source_evidence(suite_file, benchmark)
    _expect(document['source']['benchmarkReportSha256'] == evidence.report_sha and
            document['source']['suiteFileSha256'] == evidence.suite.source_sha256 and
            document['source']['artworkPythonSha256'] == generator_sha256(), 'Bundle source binding mismatch')
    expected_groups = {}
    for case in evidence.suite.cases:
        for page in case.plan['pages']:
            for tile in page['tiles']:
                expected_groups.setdefault(_group_key(case, tile), {})[case.source_size] = (
                    case.id, page['index'], tile['inputIndex'])
    actual_groups = {}
    for asset in document['assets']:
        key = (asset['family'], asset['palette'], asset['complexity'], asset['digestHex'])
        actual_groups[key] = {source['size']: (source['caseId'], source['pageIndex'], source['inputIndex'])
                              for source in asset['sources']}
    _expect(actual_groups == expected_groups, 'Bundle inventory differs from the bound native suite')
    output = _new_output(output, (root, evidence.root, Path(suite_file).absolute().parent))
    api = _native_api()  # Must succeed before output creation.
    _expect(api.environment['artworkPythonSha256'] == generator_sha256(), 'Native registry source mismatch')
    output.mkdir(parents=True)
    writer = _Writer(output)
    try:
        clock = _bytes(_file(evidence.root, 'fixture-clock.wav'), 100000)
        clock_sha = _sha(clock)
        writer.write('fixture-clock.wav', clock)
        lookup = {(a['family'], a['palette'], a['complexity'], a['digestHex']): a for a in document['assets']}
        native = []
        total_tiles = 0
        for case, page, saved in _pages(evidence):
            # Binding to original matte is rechecked, not merely trusted from the manifest.
            sources = []
            try:
                for tile in page['tiles']:
                    key = _group_key(case, tile)
                    _expect(key in lookup and case.source_size in lookup[key]['nativeSizes'], 'Bundle misses suite source')
                    data = _bytes(_file(root, f'{_prefix(key)}/{case.source_size}.png'), 2*1024*1024)
                    source = Image.frombytes('RGBA', (case.source_size, case.source_size), _frames(data, 'png')[case.source_size])
                    sources.append((tile, source))
                    with saved.crop(tuple(tile['rect'])) as crop, crop.convert('RGB') as rgb, composite_rgb(source, BACKGROUND) as expected:
                        _expect(rgb.tobytes() == expected.tobytes(), 'Saved native baseline differs from transparent sprite')
                for label, matte in MATTES.items():
                    data = project_for_page(page, clock_sha)
                    data['background'] = {'colour': '#%02x%02x%02x' % matte}
                    relative = f'{case.id}/project-{page["index"]:03d}-{label}.json'
                    writer.write(relative, _json(data))
                    project = api.Project.load(_file(output, relative))
                    _expect(project.output_quality.vector_scale == 1 and project.output_quality.time_samples == 1,
                            'Qualification must disable supersampling')
                    compositor = api.Compositor(project, renderers=api.registry)
                    try:
                        project.verify_inputs()
                        image, _ = compositor.frame(0, apply_quality=False)
                        try:
                            _expect(image.mode == 'RGB' and image.size == (page['width'], page['height']), 'Native frame contract mismatch')
                            # Saved-file comparison rather than in-memory-only acceptance.
                            stream = io.BytesIO(); image.save(stream, format='PNG', compress_level=6)
                            path = f'{case.id}/page-{page["index"]:03d}-{label}.png'
                            file = writer.write(path, stream.getvalue())
                            _, _, decoded = _decoded_image(_file(output, path), image.size)
                            try:
                                # Reference composition is QA only; it is never exported as native output.
                                with Image.new('RGBA', image.size, matte + (255,)) as expected:
                                    for tile, source in sources: expected.alpha_composite(source, dest=tuple(tile['rect'][:2]))
                                    with expected.convert('RGB') as expected_rgb, decoded.convert('RGB') as actual:
                                        _expect(actual.tobytes() == expected_rgb.tobytes(), f'Native {label} matte pixel mismatch')
                                        rgb_sha = _sha(actual.tobytes())
                                native.append({**file, 'caseId': case.id, 'pageIndex': page['index'], 'matte': label,
                                               'pixelRGBsha256': rgb_sha, 'tileCount': len(sources), 'pixelsMatch': True})
                            finally:
                                decoded.close()
                        finally:
                            image.close()
                        project.verify_inputs()
                    finally:
                        compositor.close()
                total_tiles += len(sources)
            finally:
                for _, image in sources: image.close()
        report = {'schema': QUALIFICATION, 'status': 'passed', 'publicOnly': True,
                  'guarantee': 'presentation-only', 'nativeHostExecuted': True,
                  'bundleManifestSha256': check['manifestSha256'], 'suiteFileSha256': evidence.suite.source_sha256,
                  'benchmarkReportSha256': evidence.report_sha, 'environment': api.environment,
                  'matteColours': {k: list(v) for k, v in MATTES.items()}, 'tilesPerMatte': total_tiles,
                  'pages': native, 'warning': 'Same source algorithm; this qualifies alpha/layout transport, not identity authenticity.'}
        writer.write('qualification.json', _json(report))
        return report
    except Exception as exc:
        _failure(output, exc)
        raise
