"""Source alpha and lossless transport tests; fixtures are explicitly not native CI evidence."""
from __future__ import annotations
import copy
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from PIL import Image, features

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'integrations/framerudiments'))
from tools.artwork_transparent_bundle import (
    SCHEMA, export_transparent_bundle, verify_transparent_bundle, qualify_native_mattes,
)
from tools.artwork_asset_bundle import AssetBundleError
from tools.artwork_native_benchmark import _sha, _json, _native_api, run_benchmark
from bytefables_framerudiments.transparent_assets import (
    source_rgba, generator_sha256, alpha_statistics, composite_rgb,
)
from bytefables_framerudiments.image_assets import encode_raster, encode_icon, _frames
from test_artwork_image_assets import write_test_evidence
from test_artwork_native_benchmark import write_suite


def fixture(root: Path, sizes=(16, 32), count=2):
    suite, benchmark = write_test_evidence(root, sizes=sizes, count=count)
    # Fixture provenance remains explicit. Production source check additionally
    # requires the identical algorithm file used by the saved benchmark.
    report = json.loads((benchmark / 'report.json').read_text())
    report['environment']['artworkPythonSha256'] = generator_sha256()
    (benchmark / 'report.json').write_bytes(_json(report))
    return suite, benchmark


def export(root, sizes=(16, 32), formats=('png',)):
    suite, bench = fixture(root, sizes)
    output = root / 'transparent'
    doc = export_transparent_bundle(suite, bench, output, confirm_public=True, formats=formats)
    return suite, bench, output, doc


def rewrite_manifest(root, change):
    doc = json.loads((root / 'manifest.json').read_text())
    change(doc)
    (root / 'manifest.json').write_bytes(_json(doc))


class TransparentSourceContracts(unittest.TestCase):
    def test_all_nine_families_have_repeatable_source_alpha(self):
        from tools.artwork_atlas_readback import FAMILIES, PALETTES
        for family in FAMILIES:
            for palette in PALETTES:
                for size in (16, 32, 64, 128):
                    style = {'bridge_version': 'bytefables.framerudiments.layer.v1',
                             'digest_hex': '12' * 32, 'style': family, 'palette': palette, 'complexity': 4}
                    with source_rgba(size, style) as first, source_rgba(size, style) as other:
                        self.assertEqual(first.tobytes(), other.tobytes())
                        stats = alpha_statistics(first)
                        self.assertGreater(stats['transparentPixels'], 0)
                        self.assertGreater(stats['opaquePixels'] + stats['partialPixels'], 0)
                        self.assertEqual(stats['totalPixels'], size * size)

    def test_fractional_alpha_dark_colours_and_hidden_rgb_are_not_removed(self):
        with Image.new('RGBA', (16, 16), (199, 73, 22, 0)) as source:
            source.putpixel((0, 0), (17, 24, 39, 255))  # Same as old matte: must stay visible.
            source.putpixel((1, 0), (240, 10, 128, 127))
            stats = alpha_statistics(source)
            self.assertEqual((stats['transparentPixels'], stats['partialPixels'], stats['opaquePixels']), (254, 1, 1))
            for fmt in ('png', 'webp'):
                if fmt == 'webp' and not features.check('webp'): continue
                self.assertEqual(_frames(encode_raster(source, fmt), fmt)[16], source.tobytes())
            self.assertEqual(_frames(encode_icon({16: source}), 'ico')[16], source.tobytes())
            with composite_rgb(source, (0, 0, 0)) as black, composite_rgb(source, (255, 255, 255)) as white:
                self.assertEqual(black.getpixel((0, 0)), (17, 24, 39))
                self.assertEqual(white.getpixel((0, 0)), (17, 24, 39))
                self.assertNotEqual(black.getpixel((1, 0)), white.getpixel((1, 0)))
                self.assertEqual(white.getpixel((2, 0)), (255, 255, 255))

    @unittest.skipUnless(importlib.util.find_spec('cv2'), 'Optional independent OpenCV decoder unavailable')
    def test_independent_opencv_preserves_full_rgba_samples(self):
        import cv2
        import numpy as np
        with Image.new('RGBA', (32, 32)) as image:
            image.putdata([((x*7)%256, (y*13)%256, (x*11+y*3)%256, [0, 1, 127, 254, 255][(x+y)%5])
                           for y in range(32) for x in range(32)])
            for fmt in ('png', 'webp'):
                if fmt == 'webp' and not features.check('webp'): continue
                data = encode_raster(image, fmt)
                decoded = cv2.imdecode(np.frombuffer(data, dtype=np.uint8), cv2.IMREAD_UNCHANGED)
                self.assertIsNotNone(decoded)
                self.assertEqual(decoded.shape, (32, 32, 4))
                self.assertEqual(cv2.cvtColor(decoded, cv2.COLOR_BGRA2RGBA).tobytes(), image.tobytes())

    def test_input_shape_style_and_boolean_sizes_rejected(self):
        for size in (True, 1, 17, 256):
            with self.assertRaises(ValueError): source_rgba(size, {})
        with self.assertRaises(ValueError): source_rgba(16, {'secret': 'fixture'})
        with Image.new('RGBA', (16, 16)) as source:
            for matte in ((0, 0, True), (1, 2), [0, 0, 0], (0, 0, 256)):
                with self.assertRaises(ValueError): composite_rgb(source, matte)


class TransparentBundleTests(unittest.TestCase):
    def test_roundtrip_four_native_sizes_all_codecs_and_determinism(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            formats = ('png', 'webp', 'ico') if features.check('webp') else ('png', 'ico')
            suite, bench, output, doc = export(root, (16, 32, 64, 128), formats)
            other = export_transparent_bundle(suite, bench, root/'other', confirm_public=True, formats=formats)
            self.assertEqual(doc, other)
            self.assertEqual(doc['schema'], SCHEMA)
            self.assertFalse(doc['resampled']); self.assertFalse(doc['source']['nativeHostRerunByExporter'])
            self.assertEqual(verify_transparent_bundle(output)['assets'], 2)
            for item in doc['assets']:
                self.assertEqual(item['nativeSizes'], [16, 32, 64, 128])
                self.assertTrue(all(s['alpha']['transparentPixels'] for s in item['sources']))
            self.assertIn('checker', (output/'index.html').read_text())
            self.assertNotIn('<script', (output/'index.html').read_text())

    def test_generator_provenance_mismatch_rejected_before_creation(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); suite, bench = fixture(root)
            report = json.loads((bench/'report.json').read_text()); report['environment']['artworkPythonSha256'] = '0'*64
            (bench/'report.json').write_bytes(_json(report))
            with self.assertRaisesRegex(ValueError, 'Generator source hash'):
                export_transparent_bundle(suite, bench, root/'out', confirm_public=True)
            self.assertFalse((root/'out').exists())

    def test_opt_in_and_output_reuse_and_input_overlap(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); suite, bench, output, _ = export(root)
            for dest, consent in ((root/'no', False), (output, True), (bench/'nested', True)):
                with self.assertRaises(ValueError):
                    export_transparent_bundle(suite, bench, dest, confirm_public=consent)
            self.assertFalse((root/'no').exists()); self.assertFalse((bench/'nested').exists())

    def test_actual_source_mismatch_cannot_publish_a_manifest(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); suite, bench = fixture(root)
            def altered(size, style):
                image = source_rgba(size, style); image.putpixel((0, 0), (255, 0, 0, 255)); return image
            with patch('tools.artwork_transparent_bundle.source_rgba', side_effect=altered):
                with self.assertRaisesRegex(ValueError, 'native matte'):
                    export_transparent_bundle(suite, bench, root/'out', confirm_public=True, formats=('png',))
            self.assertFalse((root/'out/manifest.json').exists()); self.assertTrue((root/'out/failure.json').exists())

    def test_changed_native_page_rejected_and_failure_preserved(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); suite, bench = fixture(root)
            file = next(bench.glob('*/atlas-page-000.png'))
            with Image.open(file) as image:
                copy_image = image.copy()
            copy_image.putpixel((0, 0), (0, 0, 0)); copy_image.save(file); copy_image.close()
            with self.assertRaises(ValueError): export_transparent_bundle(suite, bench, root/'out', confirm_public=True)
            self.assertFalse((root/'out/manifest.json').exists())

    def test_saved_asset_viewer_and_alpha_tampering_are_detected(self):
        for mode in ('file', 'alpha', 'viewer', 'source-rgb'):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp); _, _, output, doc = export(root)
                if mode == 'file':
                    path = output/doc['assets'][0]['files'][0]['file']; path.write_bytes(path.read_bytes() + b'extra')
                elif mode == 'viewer': (output/'index.html').write_text('substituted')
                elif mode == 'alpha':
                    rewrite_manifest(output, lambda d: d['assets'][0]['sources'][0]['alpha'].update(alphaSha256='0'*64))
                else:
                    rewrite_manifest(output, lambda d: d['assets'][0]['sources'][0].update(nativeRGBsha256='0'*64))
                with self.assertRaises(ValueError): verify_transparent_bundle(output)

    def test_inventory_duplicate_missing_frames_and_bad_metadata_rejected(self):
        changes = [lambda d: d['assets'].append(copy.deepcopy(d['assets'][0])),
                   lambda d: d['assets'][0]['files'].pop(),
                   lambda d: d['assets'][0].update(nativeSizes=[16, 16]),
                   lambda d: d['assets'][0]['sources'][0].update(pageIndex=True),
                   lambda d: d['assets'][0].update(complexity=True),
                   lambda d: d.update(publicOnly=False),
                   lambda d: d['source'].update(additionalNativeMattes='passed')]
        for change in changes:
            with tempfile.TemporaryDirectory() as tmp:
                _, _, output, _ = export(Path(tmp)); rewrite_manifest(output, change)
                with self.assertRaises(ValueError): verify_transparent_bundle(output)

    def test_path_escape_and_symlinks_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); _, _, output, _ = export(root)
            rewrite_manifest(output, lambda d: d['assets'][0]['files'][0].update(file='../outside.png'))
            with self.assertRaises(ValueError): verify_transparent_bundle(output)
            link = root/'linked'
            try: link.symlink_to(output, target_is_directory=True)
            except OSError: self.skipTest('Symlink creation unavailable')
            with self.assertRaises(ValueError): verify_transparent_bundle(link)

    def test_workload_budget_failure_precedes_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); suite, bench = fixture(root)
            with patch('tools.artwork_transparent_bundle.MAX_GROUPS', 1):
                with self.assertRaisesRegex(ValueError, 'budget'):
                    export_transparent_bundle(suite, bench, root/'out', confirm_public=True)
            self.assertFalse((root/'out').exists())

    def test_missing_native_host_does_not_claim_qualification(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); suite, bench, output, _ = export(root)
            with patch('tools.artwork_transparent_bundle._native_api', side_effect=RuntimeError('Missing host')):
                with self.assertRaisesRegex(RuntimeError, 'Missing host'):
                    qualify_native_mattes(suite, bench, output, root/'qual', confirm_public=True)
            self.assertFalse((root/'qual').exists())

    def test_qualification_requires_exact_suite_inventory_before_host_import(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); suite, bench, output, _ = export(root)
            def change(doc):
                doc['assets'].pop(); doc['assetCount'] -= 1
            rewrite_manifest(output, change)
            # Local bundle consistency alone cannot certify full suite coverage.
            self.assertEqual(verify_transparent_bundle(output)['assets'], 1)
            with patch('tools.artwork_transparent_bundle._native_api') as host:
                with self.assertRaisesRegex(ValueError, 'inventory'):
                    qualify_native_mattes(suite, bench, output, root/'qual', confirm_public=True)
                host.assert_not_called()
            self.assertFalse((root/'qual').exists())

    def test_qualification_pixel_failure_keeps_diagnostics_without_success_marker(self):
        # Failure-path test double only; this is not a native rendering test.
        closed = []
        class TestProject:
            @staticmethod
            def load(path):
                data = json.loads(path.read_text())
                return SimpleNamespace(data=data, output_quality=SimpleNamespace(vector_scale=1, time_samples=1),
                                       verify_inputs=lambda: None)
        class WrongCompositor:
            def __init__(self, project, **kwargs): self.data = project.data
            def frame(self, *args, **kwargs):
                return Image.new('RGB', (self.data['width'], self.data['height']), (0, 0, 0)), None
            def close(self): closed.append(True)
        api = SimpleNamespace(Project=TestProject, Compositor=WrongCompositor, registry=None,
                              environment={'artworkPythonSha256': generator_sha256(), 'TEST_DOUBLE_ONLY': True})
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); suite, bench, output, _ = export(root)
            with patch('tools.artwork_transparent_bundle._native_api', return_value=api):
                with self.assertRaisesRegex(ValueError, 'black matte pixel mismatch'):
                    qualify_native_mattes(suite, bench, output, root/'qual', confirm_public=True)
            self.assertTrue(closed)
            self.assertTrue((root/'qual/failure.json').exists())
            self.assertFalse((root/'qual/qualification.json').exists())

    def test_cli_export_verify_and_nonzero_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); suite, bench = fixture(root)
            script = ROOT/'scripts/export-artwork-transparent.py'
            command = [sys.executable, str(script), '--confirm-public']
            run = subprocess.run(command + ['export', '--suite', str(suite), '--benchmark', str(bench),
                    '--output', str(root/'out'), '--formats', 'png,ico'], capture_output=True, text=True, timeout=30)
            self.assertEqual(run.returncode, 0, run.stderr)
            run = subprocess.run(command + ['verify', '--bundle', str(root/'out')], capture_output=True, text=True, timeout=30)
            self.assertEqual(run.returncode, 0, run.stderr)
            self.assertTrue(json.loads(run.stdout)['decodedPixelsVerified'])
            run = subprocess.run(command + ['verify', '--bundle', str(root/'missing')], capture_output=True, text=True, timeout=30)
            self.assertNotEqual(run.returncode, 0); self.assertIn('failed', run.stderr)


class NativeTwoMatteQualification(unittest.TestCase):
    def test_real_compositor_black_and_white_against_saved_rgba(self):
        try: _native_api()
        except Exception:
            if os.environ.get('BYTEFABLES_REQUIRE_NATIVE') == '1': raise
            self.skipTest('Real FrameRudiments host unavailable; CI requires this test')
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            suite = write_suite(root/'suite', (('sigil', 16), ('cellular', 32)), 2)
            run_benchmark(suite, root/'native', confirm_public=True, synthetic_fixture=True, samples=2)
            export_transparent_bundle(suite, root/'native', root/'alpha', confirm_public=True, formats=('png',))
            result = qualify_native_mattes(suite, root/'native', root/'alpha', root/'qualified', confirm_public=True)
            self.assertTrue(result['nativeHostExecuted'])
            self.assertEqual(result['tilesPerMatte'], 4)
            self.assertEqual({p['matte'] for p in result['pages']}, {'black', 'white'})
            self.assertTrue((root/'qualified/qualification.json').exists())
