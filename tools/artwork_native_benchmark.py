"""Bounded PUBLIC atlas benchmark driven by the real FrameRudiments compositor.

There is no fallback renderer here. A synthetic clock fixture is explicit,
checksum-pinned and labelled as synthetic; it is never music-analysis evidence.
Pillow is used for saved-PNG readback/reference checks, not source generation.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import html
import importlib.metadata
import inspect
import json
from pathlib import Path
import platform
import re
import statistics
import sys
import time
from types import SimpleNamespace
from typing import Any
import wave

from PIL import Image, ImageChops, ImageStat, __version__ as PILLOW_VERSION
from tools.artwork_atlas_readback import (
    AtlasReadbackError, FAMILIES, PALETTES, MAX_PLAN_BYTES,
    validate_atlas_plan, readback_artwork_atlas, _decoded_image,
)

SUITE_SCHEMA = 'bytefables.artwork-native-benchmark-suite.v1'
REPORT_SCHEMA = 'bytefables.artwork-native-benchmark-report.v1'
BACKGROUND = (17, 24, 39)
MAX_CASES = 108
MAX_TOTAL_TILES = 8192
MAX_TOTAL_PIXELS = 268_435_456
MAX_PAIRS = 16_000_000
SIZES = (16, 32, 64, 128)
HEX = re.compile(r'[0-9a-f]{64}\Z')


class BenchmarkError(ValueError):
    """Bad input, unavailable native host or failed exported-image evidence."""


@dataclass(frozen=True)
class LoadedCase:
    id: str
    family: str
    palette: str
    source_size: int
    plan: dict[str, Any]
    plan_sha256: str


@dataclass(frozen=True)
class LoadedSuite:
    cases: tuple[LoadedCase, ...]
    source_sha256: str
    corpus: dict[str, Any]


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _json(data: Any) -> bytes:
    return (json.dumps(data, indent=2, ensure_ascii=True, allow_nan=False) + '\n').encode('ascii')


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise BenchmarkError(f'Duplicate JSON key: {key}')
        result[key] = value
    return result


def _reject_constant(value):
    raise BenchmarkError(f'Non-finite JSON value: {value}')


def _read_json(path: Path, limit: int = MAX_PLAN_BYTES) -> tuple[Any, str]:
    if path.is_symlink() or not path.is_file():
        raise BenchmarkError('Input must be a regular, non-symlink JSON file')
    with path.open('rb') as stream:
        data = stream.read(limit + 1)
    if len(data) > limit:
        raise BenchmarkError('JSON exceeds byte budget')
    try:
        value = json.loads(data.decode('utf-8'), object_pairs_hook=_unique_object,
                           parse_constant=_reject_constant)
    except (ValueError, UnicodeError) as exc:
        raise BenchmarkError(f'Invalid JSON: {path.name}') from exc
    return value, _sha(data)


def _keys(value: Any, keys: set[str], label: str) -> None:
    if type(value) is not dict or set(value) != keys:
        raise BenchmarkError(f'Unknown/missing {label} fields')


def _integer(value: Any, low: int, high: int, label: str) -> int:
    if type(value) is not int or not low <= value <= high:
        raise BenchmarkError(f'Invalid {label}')
    return value


def load_suite(filename: Path) -> LoadedSuite:
    filename = Path(filename).absolute()
    document, document_sha = _read_json(filename)
    _keys(document, {'schema', 'publicOnly', 'guarantee', 'corpus', 'cases'}, 'suite')
    if (document['schema'] != SUITE_SCHEMA or document['publicOnly'] is not True or
            document['guarantee'] != 'presentation-only'):
        raise BenchmarkError('Expected public-only native artwork benchmark suite')
    corpus = document['corpus']
    _keys(corpus, {'id', 'seed', 'count'}, 'corpus')
    if (corpus['id'] != 'bytefables.public-benchmark-corpus.v1' or
            type(corpus['seed']) is not str or
            re.fullmatch(r'[a-zA-Z0-9_-]{1,64}', corpus['seed']) is None):
        raise BenchmarkError('Invalid synthetic public corpus')
    count = _integer(corpus['count'], 1, 1000, 'corpus count')
    cases = document['cases']
    if type(cases) is not list or not 1 <= len(cases) <= MAX_CASES:
        raise BenchmarkError('Invalid suite case count')
    if (count * len(cases) > MAX_TOTAL_TILES or
            count * (count - 1) // 2 * 4 * len(cases) > MAX_PAIRS):
        raise BenchmarkError('Suite exceeds tile/pair workload budget')
    root = filename.parent.resolve()
    loaded = []
    ids = set()
    total_pixels = 0
    reference_digests = None
    for case in cases:
        _keys(case, {'id', 'plan', 'planSha256', 'family', 'palette', 'sourceSize'}, 'case')
        if (type(case['family']) is not str or case['family'] not in FAMILIES or
                type(case['palette']) is not str or case['palette'] not in PALETTES or
                type(case['sourceSize']) is not int or case['sourceSize'] not in SIZES):
            raise BenchmarkError('Invalid family, palette or native source size')
        name = f"{case['family']}-{case['palette']}-{case['sourceSize']}"
        if case['id'] != name or name in ids or case['plan'] != f'plans/{name}.json':
            raise BenchmarkError('Invalid/repeated case ID or noncanonical plan path')
        ids.add(name)
        path = root / case['plan']
        if (path.parent.is_symlink() or path.is_symlink() or
                not path.resolve().is_relative_to(root)):
            raise BenchmarkError('Plan path escapes suite or uses a symlink')
        plan, plan_sha = _read_json(path)
        if type(case['planSha256']) is not str or not HEX.fullmatch(case['planSha256']) or plan_sha != case['planSha256']:
            raise BenchmarkError('Atlas plan checksum mismatch')
        validate_atlas_plan(plan)
        _keys(plan, {'version', 'guarantee', 'publicOnly', 'inputCount', 'pages'}, 'atlas')
        if plan['inputCount'] != count:
            raise BenchmarkError('Case does not use the declared corpus count')
        digests = [None] * count
        for page in plan['pages']:
            _keys(page, {'index', 'width', 'height', 'tiles'}, 'page')
            _integer(page['index'], 0, 999, 'page index')
            if page['width'] % 2 or page['height'] % 2:
                raise BenchmarkError('Native compositor requires even page dimensions')
            total_pixels += page['width'] * page['height']
            if total_pixels > MAX_TOTAL_PIXELS:
                raise BenchmarkError('Suite exceeds total pixel budget')
            for tile in page['tiles']:
                _keys(tile, {'inputIndex', 'digestHex', 'rect', 'uv', 'layer'}, 'tile')
                layer = tile['layer']
                _keys(layer, {'id', 'type', 'renderer', 'bounds', 'motion', 'axes', 'history_frames', 'style'}, 'layer')
                if (layer['motion'] != {'kind': 'named', 'pattern': 'circle'} or
                        layer['axes'] != [0] or type(layer['axes'][0]) is not int or
                        type(layer['history_frames']) is not int or layer['history_frames'] != 1):
                    raise BenchmarkError('Benchmark requires the static atlas motion contract')
                rect = tile['rect']
                style = layer['style']
                if (rect[2] - rect[0] != case['sourceSize'] or rect[3] - rect[1] != case['sourceSize'] or
                        style['style'] != case['family'] or style['palette'] != case['palette']):
                    raise BenchmarkError('Case metadata differs from native tile source')
                digests[tile['inputIndex']] = tile['digestHex']
        if len(set(digests)) != count:
            raise BenchmarkError('Synthetic benchmark requires distinct public identities')
        if reference_digests is not None and digests != reference_digests:
            raise BenchmarkError('Cases must compare the same ordered public identity corpus')
        reference_digests = digests
        loaded.append(LoadedCase(name, case['family'], case['palette'], case['sourceSize'], plan, plan_sha))
    return LoadedSuite(tuple(loaded), document_sha, dict(corpus))


def _source_tree(package_file: str) -> dict[str, Any]:
    root = Path(package_file).resolve().parent
    entries = [(p.relative_to(root).as_posix(), _sha(p.read_bytes()))
               for p in sorted(root.rglob('*.py')) if '__pycache__' not in p.parts]
    return {'pythonFileCount': len(entries), 'pythonTreeSha256': _sha(_json(entries))}


def _native_api():
    # The runner cannot silently substitute plugin-only or mocked composition.
    try:
        import framerudiments
        from framerudiments import Project, RendererRegistry
        from framerudiments.compositor import Compositor
    except ImportError as exc:
        raise BenchmarkError('FrameRudiments native host is required; no renderer fallback is available. '
                             'Install FrameRudiments in this Python environment.') from exc
    root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(root / 'integrations' / 'framerudiments'))
    from bytefables_framerudiments.artwork import ArtworkRenderer
    registry = RendererRegistry()
    # Exact same factory/name as register_bytefables_renderers; deliberately no
    # unused built-ins or arbitrary caller factories in this bounded benchmark.
    registry.register('bytefables-artwork-v1', ArtworkRenderer)
    versions = {}
    for package in ('framerudiments', 'dancerudiments', 'Pillow'):
        try:
            versions[package] = importlib.metadata.version(package)
        except importlib.metadata.PackageNotFoundError:
            versions[package] = 'source-checkout'
    return SimpleNamespace(Project=Project, Compositor=Compositor, registry=registry,
                           reference=ArtworkRenderer, environment={
                               'python': platform.python_version(), 'platform': platform.platform(),
                               'packages': versions, 'pillow': PILLOW_VERSION,
                               'hostVersion': getattr(framerudiments, '__version__', 'unknown'),
                               'hostSources': _source_tree(framerudiments.__file__),
                               'artworkPythonSha256': _sha(Path(inspect.getfile(ArtworkRenderer)).read_bytes()),
                           })


def create_fixture_clock(filename: Path) -> str:
    """One second of silent public PCM; only called after explicit fixture consent."""
    with Path(filename).open('xb') as raw:
        with wave.open(raw, 'wb') as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(48000)
            wav.writeframes(b'\x00\x00' * 48000)
    return _sha(Path(filename).read_bytes())


def project_for_page(page: dict[str, Any], clock_sha: str) -> dict[str, Any]:
    if not HEX.fullmatch(clock_sha):
        raise BenchmarkError('Invalid synthetic clock checksum')
    # Page project lives under output/<case>/; clock is one directory above.
    # Only allowlisted atlas layers enter the native project, never arbitrary effects.
    return {'schema': 'framerudiments.project.v1',
            'title': 'PUBLIC synthetic artwork benchmark', 'artist': 'ByteFables',
            'purpose': 'canvas', 'width': page['width'], 'height': page['height'], 'fps': 60,
            'audio': {'source': {'path': '../fixture-clock.wav', 'sha256': clock_sha},
                      'sample_rate': 48000, 'start_sample': 0, 'end_sample': 48000,
                      'repeats': 1, 'fade_seconds': 0},
            'clock': {'bpm': 120, 'origin': 0, 'status': 'synthetic',
                      'authority': 'ByteFables synthetic benchmark fixture; not music analysis'},
            'background': {'colour': '#111827'},
            # apply_quality=False skips final AA only, not spatial/time sampling.
            'render_quality': {'enabled': False},
            'layers': [tile['layer'] for tile in page['tiles']],
            'notes': 'Native static benchmark. No fonts, captions, effects, models or secret inputs.'}


def verify_composited_page(page: dict[str, Any], path: Path, reference_factory) -> dict[str, Any]:
    """Check saved pixels, including gutters, against native source on a fixed matte.

    The reference shares the artwork algorithm; it tests export/layout integrity,
    not independently proved artwork identity. It never writes rendered imagery.
    """
    _, _, decoded = _decoded_image(path, (page['width'], page['height']))
    source_coverage = []
    try:
        rgb = decoded.convert('RGB')
        residue = ImageChops.difference(rgb, Image.new('RGB', rgb.size, BACKGROUND))
        for tile in page['tiles']:
            rect = tuple(tile['rect'])
            size = (rect[2] - rect[0], rect[3] - rect[1])
            source = reference_factory(size, tile['layer']['style']).render(None)
            if source.mode != 'RGBA' or source.size != size:
                raise BenchmarkError('Reference generator returned wrong mode/size')
            matte = Image.new('RGBA', size, BACKGROUND + (255,))
            matte.alpha_composite(source)
            expected = matte.convert('RGB')
            actual = rgb.crop(rect)
            if actual.tobytes() != expected.tobytes():
                raise BenchmarkError(f"Composited source mismatch at tile {tile['inputIndex']}")
            source_coverage.append({'inputIndex': tile['inputIndex'],
                                    'sourceAlphaCoverage': round(ImageStat.Stat(source.getchannel('A')).mean[0] / 255, 6)})
            residue.paste((0, 0, 0), rect)
            for image in (source, matte, expected, actual):
                image.close()
        if residue.getbbox() is not None:
            raise BenchmarkError('Unexpected pixels in atlas gutters or unused cells')
        rgb.close()
        residue.close()
    finally:
        decoded.close()
    return {'pageIndex': page['index'], 'sourceAndMatteMatch': True,
            'guttersMatch': True, 'tiles': source_coverage}


def _render_page(api, data, case_dir, page, samples):
    path = case_dir / f"project-{page['index']:03d}.json"
    path.write_bytes(_json(data))
    start = time.perf_counter()
    project = api.Project.load(path)
    if project.output_quality.vector_scale != 1 or project.output_quality.time_samples != 1:
        raise BenchmarkError('Native benchmark must disable spatial and temporal supersampling')
    compositor = api.Compositor(project, renderers=api.registry)
    try:
        project.verify_inputs()
        setup_seconds = time.perf_counter() - start
        start = time.perf_counter()
        image, _context = compositor.frame(0, apply_quality=False)
        cold_seconds = time.perf_counter() - start
        if image.mode != 'RGB' or image.size != (page['width'], page['height']):
            raise BenchmarkError('Native frame contract changed: expected page-sized RGB')
        baseline = _sha(image.tobytes())
        filename = case_dir / f"atlas-page-{page['index']:03d}.png"
        start = time.perf_counter()
        image.save(filename, format='PNG', optimize=False, compress_level=6)
        encode_seconds = time.perf_counter() - start
        image.close()
        timings = []
        frames = [1 if i % 2 == 0 else 0 for i in range(samples)]
        for frame in frames:
            start = time.perf_counter()
            image, _context = compositor.frame(frame, apply_quality=False)
            timings.append(time.perf_counter() - start)
            try:
                if image.mode != 'RGB' or image.size != (page['width'], page['height']) or _sha(image.tobytes()) != baseline:
                    raise BenchmarkError('Native static artwork is not repeatable across frame seeks')
            finally:
                image.close()
        project.verify_inputs()
        check = verify_composited_page(page, filename, api.reference)
        return {'pageIndex': page['index'], 'pixelRGBsha256': baseline,
                'setupSeconds': setup_seconds, 'coldFrameSeconds': cold_seconds,
                'pngEncodeSeconds': encode_seconds, 'sampleFrames': frames,
                'warmFrameSeconds': timings, 'warmMedianSeconds': statistics.median(timings),
                'staticSeekPixelsMatch': True, 'compositedReference': check}
    finally:
        close = getattr(compositor, 'close', None)
        if callable(close):
            close()


def _write_gallery(report: dict[str, Any], filename: Path) -> None:
    sections = []
    for case in report['cases']:
        title = html.escape(case['id'])
        pictures = ''.join(
            f'<figure><a href="{case["id"]}/{p["fileName"]}"><img loading="lazy" '
            f'src="{case["id"]}/{p["fileName"]}" alt="{title}, page {p["pageIndex"]}" '
            f'width="{p["width"]}" height="{p["height"]}"></a>'
            f'<figcaption>Page {p["pageIndex"]}; SHA-256 {p["fileSha256"]}</figcaption></figure>'
            for p in case['pages'])
        native_stats = case['similarity'][str(case['sourceSize'])]
        sections.append(f'<section><h2>{title}</h2><p>{case["inputCount"]} identities; '
                        f'{case["sourceSize"]}px native sources; '
                        f'{native_stats["dhashExactCollisions"]} exact dHash matches in '
                        f'{native_stats["distinctIdentityPairs"]} distinct-identity pairs. '
                        f'<a href="{case["id"]}/readback.json">Readback details</a></p>{pictures}</section>')
    document = '''<!doctype html><html lang="en"><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; img-src 'self'; style-src 'unsafe-inline';">
<title>ByteFables native artwork benchmark</title>
<style>body{background:#111827;color:#f3f4f6;font:16px system-ui;margin:2rem;max-width:1400px}
a{color:#bae6fd}section{margin:2rem 0;padding:1rem;border:1px solid #475569}
figure{overflow:auto;margin:1rem 0}img{max-width:100%;height:auto;image-rendering:auto}
figcaption{font:12px monospace;overflow-wrap:anywhere}p{max-width:85ch;line-height:1.5}</style>
<h1>ByteFables native artwork benchmark</h1>
<p>Real FrameRudiments compositor outputs. Click a page to inspect its original pixels.
Public synthetic fixtures only. dHash is a similarity diagnostic, not identity authentication,
recoverability, measured human recognition or a security collision estimate.</p>
<p>Each size is rendered natively. Readback also reports resampled viewing sizes separately.
Opaque-frame alpha coverage is not source coverage. No model inference or remote rendering.</p>
<p><a href="report.json">Machine-readable report and environment</a></p>'''
    filename.write_text(document + ''.join(sections) + '</html>\n', encoding='utf-8')


def run_benchmark(suite_file: Path, output: Path, *, confirm_public: bool = False,
                  synthetic_fixture: bool = False, samples: int = 3) -> dict[str, Any]:
    if confirm_public is not True or synthetic_fixture is not True:
        raise BenchmarkError('Explicit --confirm-public and --synthetic-fixture consent required')
    _integer(samples, 1, 5, 'timing samples')
    suite = load_suite(suite_file)
    output = Path(output).absolute()
    if output.exists() or output.is_symlink():
        raise BenchmarkError('Output must be a new directory; no overwrite or reuse')
    api = _native_api()  # Fail before writing any output if the native host is absent.
    output.parent.mkdir(parents=True, exist_ok=True)
    output.mkdir()  # Exclusive directory creation; another run cannot share this destination.
    started = time.perf_counter()
    try:
        clock_sha = create_fixture_clock(output / 'fixture-clock.wav')
        cases = []
        for case in suite.cases:
            case_dir = output / case.id
            case_dir.mkdir()
            (case_dir / 'plan.json').write_bytes(_json(case.plan))
            page_reports = [_render_page(api, project_for_page(page, clock_sha), case_dir, page, samples)
                            for page in case.plan['pages']]
            check_started = time.perf_counter()
            readback = readback_artwork_atlas(case.plan, case_dir)
            readback_seconds = time.perf_counter() - check_started
            payload = _json(readback)
            (case_dir / 'readback.json').write_bytes(payload)
            cases.append({'id': case.id, 'family': case.family, 'palette': case.palette,
                          'sourceSize': case.source_size, 'inputCount': case.plan['inputCount'],
                          'inputPlanSha256': case.plan_sha256,
                          'readbackSha256': _sha(payload), 'readbackSeconds': readback_seconds,
                          'pages': readback['pages'], 'similarity': readback['similarity'],
                          'blankOrUniformTiles': sum(t['quality']['blankOrUniform'] for t in readback['tiles']),
                          'nativePageMeasurements': page_reports,
                          'compositedSourceComparison': 'passed'})
        report = {'schema': REPORT_SCHEMA, 'status': 'passed', 'publicOnly': True,
                  'guarantee': 'presentation-only', 'nativeHostExecuted': True,
                  'renderAPI': 'framerudiments.compositor.Compositor.frame',
                  'framePostprocessing': 'disabled; fixed opaque matte; no effects',
                  'suiteFileSha256': suite.source_sha256, 'corpus': suite.corpus,
                  'clockFixture': {'kind': 'explicit-synthetic-silent-pcm', 'sha256': clock_sha,
                                   'sampleRate': 48000, 'samples': 48000},
                  'environment': api.environment, 'cases': cases,
                  'totalSeconds': time.perf_counter() - started,
                  'warning': 'Experimental visual diagnostics, not human-recognition or identity-security qualification. '
                             'Timing is machine-dependent; the reference uses the same artwork generator.'}
        _write_gallery(report, output / 'index.html')
        # Final success marker is written only after all exports, readbacks and gallery succeed.
        marker = output / 'report.json.tmp'
        marker.write_bytes(_json(report))
        marker.replace(output / 'report.json')
        return report
    except Exception as exc:
        # Preserve diagnostics without leaving a stale success marker or deleting user data.
        (output / 'failure.json').write_bytes(_json({'schema': REPORT_SCHEMA, 'status': 'failed',
            'exception': type(exc).__name__, 'message': str(exc),
            'warning': 'Partial output; not a completed/qualified benchmark.'}))
        raise
