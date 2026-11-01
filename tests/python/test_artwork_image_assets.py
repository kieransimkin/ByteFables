"""Real codec roundtrips and bundle tests. Test evidence is NOT a native-host run."""
from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from PIL import Image, features
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'integrations' / 'framerudiments'))
from bytefables_framerudiments.image_assets import (
    ImageAssetError, encode_raster, encode_icon, inspect_asset, require_formats,
)
from tools.artwork_asset_bundle import (
    AssetBundleError, export_asset_bundle, verify_asset_bundle, load_evidence,
)
from tools.artwork_native_benchmark import (
    REPORT_SCHEMA, BACKGROUND, load_suite, create_fixture_clock, project_for_page,
    verify_composited_page, _json, _sha,
)
from tools.artwork_atlas_readback import readback_artwork_atlas
from bytefables_framerudiments.artwork import ArtworkRenderer
from test_artwork_native_benchmark import write_suite


def write_test_evidence(root, sizes=(16, 32, 64, 128), count=2):
    """Real test images + synthetic receipts, for exporter tests only.

    Production exporter never makes source imagery. Do not publish these fixtures
    as native compositor evidence. Native end-to-end evidence remains a CI gate.
    """
    suite_file = write_suite(root / 'suite', tuple(('sigil', size) for size in sizes), count)
    suite = load_suite(suite_file)
    benchmark = root / 'benchmark'
    benchmark.mkdir()
    clock_sha = create_fixture_clock(benchmark / 'fixture-clock.wav')
    report = {'schema': REPORT_SCHEMA, 'status': 'passed', 'publicOnly': True,
              'guarantee': 'presentation-only', 'nativeHostExecuted': True,
              'renderAPI': 'framerudiments.compositor.Compositor.frame',
              'suiteFileSha256': suite.source_sha256, 'corpus': suite.corpus,
              'clockFixture': {'kind': 'explicit-synthetic-silent-pcm', 'sha256': clock_sha},
              'environment': {'TEST_FIXTURE_ONLY': True}, 'cases': []}
    for case in suite.cases:
        case_dir = benchmark / case.id
        case_dir.mkdir()
        (case_dir / 'plan.json').write_bytes(_json(case.plan))
        measurements = []
        for page in case.plan['pages']:
            index = page['index']
            (case_dir / f'project-{index:03d}.json').write_bytes(_json(project_for_page(page, clock_sha)))
            frame = Image.new('RGBA', (page['width'], page['height']), BACKGROUND + (255,))
            for tile in page['tiles']:
                ink = ArtworkRenderer((case.source_size, case.source_size), tile['layer']['style']).render(None)
                frame.alpha_composite(ink, dest=tuple(tile['rect'][:2]))
                ink.close()
            rgb = frame.convert('RGB')
            image_file = case_dir / f'atlas-page-{index:03d}.png'
            rgb.save(image_file, format='PNG')
            measurements.append({'pageIndex': index, 'staticSeekPixelsMatch': True,
                'pixelRGBsha256': _sha(rgb.tobytes()),
                'compositedReference': verify_composited_page(page, image_file, ArtworkRenderer)})
            rgb.close(); frame.close()
        rb = readback_artwork_atlas(case.plan, case_dir)
        rb_bytes = _json(rb)
        (case_dir / 'readback.json').write_bytes(rb_bytes)
        report['cases'].append({'id': case.id, 'family': case.family, 'palette': case.palette,
            'sourceSize': case.source_size, 'inputCount': count, 'inputPlanSha256': case.plan_sha256,
            'readbackSha256': _sha(rb_bytes), 'pages': rb['pages'],
            'nativePageMeasurements': measurements, 'compositedSourceComparison': 'passed'})
    (benchmark / 'report.json').write_bytes(_json(report))
    return suite_file, benchmark


class CodecRoundtrips(unittest.TestCase):
    def test_png_strips_metadata_and_preserves_transparent_rgb(self):
        image = Image.new('RGBA', (16, 16), (231, 17, 88, 0))
        image.info.update(exif=b'secret-fixture', xmp=b'private-fixture', comment='unapproved')
        try:
            data = encode_raster(image, 'png')
            self.assertNotIn(b'secret-fixture', data)
            self.assertNotIn(b'private-fixture', data)
            expected = _sha(image.tobytes())
            self.assertEqual(inspect_asset(data, 'png')['frames'], [{'size': 16, 'rgbaSha256': expected}])
            self.assertEqual(data, encode_raster(image, 'png'))
        finally:
            image.close()

    @unittest.skipUnless(features.check('webp'), 'Pillow WebP backend not available')
    def test_lossless_webp_preserves_all_rgba_including_invisible_rgb(self):
        image = Image.new('RGBA', (32, 32), (27, 221, 56, 0))
        for i in range(32):
            image.putpixel((i, i), (i * 7, 255 - i * 7, 71, i * 8))
        try:
            data = encode_raster(image, 'webp')
            self.assertEqual(inspect_asset(data, 'webp')['frames'],
                             [{'size': 32, 'rgbaSha256': _sha(image.tobytes())}])
            self.assertEqual(data, encode_raster(image, 'webp'))
            with self.assertRaises(ImageAssetError): inspect_asset(data + b'x', 'webp')
        finally:
            image.close()

    def test_ico_retains_distinct_native_size_art_not_resized_largest(self):
        images = {size: Image.new('RGBA', (size, size), (size, 255-size, 17, 255))
                  for size in (16, 32, 64, 128)}
        try:
            data = encode_icon(images)
            expected = [{'size': size, 'rgbaSha256': _sha(image.tobytes())} for size, image in images.items()]
            self.assertEqual(inspect_asset(data, 'ico')['frames'], expected)
            self.assertEqual(data, encode_icon(images))
            self.assertEqual(len(inspect_asset(encode_icon({32: images[32]}), 'ico')['frames']), 1)
            # Corrupt second directory size to duplicate the first.
            bad = bytearray(data); bad[22:24] = bad[6:8]
            with self.assertRaises(ImageAssetError): inspect_asset(bytes(bad), 'ico')
            with self.assertRaises(ImageAssetError): inspect_asset(data + b'x', 'ico')
            # A small ICO directory must not hide a huge embedded PNG allocation.
            bad = bytearray(data)
            start = int.from_bytes(bad[18:22], 'little')
            bad[start+16:start+20] = (100000).to_bytes(4, 'big')
            with self.assertRaises(ImageAssetError): inspect_asset(bytes(bad), 'ico')
        finally:
            for image in images.values(): image.close()

    def test_rejects_unsupported_inputs_and_implicit_resize(self):
        for size, mode in ((17, 'RGBA'), (16, 'RGB')):
            with Image.new(mode, (size, size)) as image:
                with self.assertRaises(ImageAssetError): encode_raster(image, 'png')
        with Image.new('RGBA', (16, 16)) as image:
            with self.assertRaises(ImageAssetError): encode_icon({32: image})
            with self.assertRaises(ImageAssetError): encode_raster(image, 'jpeg')
        for formats in ([], ['webp'], ['png', 'png'], ['png', 'jpeg'], ['png', {}]):
            with self.assertRaises(ImageAssetError): require_formats(formats)
        with patch('bytefables_framerudiments.image_assets.features.check', return_value=False):
            with self.assertRaisesRegex(ImageAssetError, 'unavailable'): require_formats(['png', 'webp'])
        with self.assertRaises(ImageAssetError): inspect_asset(b'not image', 'png')

    @unittest.skipUnless(importlib.util.find_spec('cv2'), 'Optional independent OpenCV codec readback')
    def test_independent_opencv_png_and_webp_pixel_readback(self):
        import cv2
        import numpy as np
        with Image.new('RGBA', (32, 32)) as image:
            image.putdata([((x*17+y*7)%256, (x*3+y*19)%256, (x*11+y*5)%256, 255)
                           for y in range(32) for x in range(32)])
            for format in ('png', 'webp'):
                if format == 'webp' and not features.check('webp'): continue
                data = encode_raster(image, format)
                decoded = cv2.imdecode(np.frombuffer(data, dtype=np.uint8), cv2.IMREAD_UNCHANGED)
                self.assertIsNotNone(decoded)
                if decoded.shape[2] == 3:
                    actual = cv2.cvtColor(decoded, cv2.COLOR_BGR2RGBA)
                else:
                    actual = cv2.cvtColor(decoded, cv2.COLOR_BGRA2RGBA)
                self.assertEqual(actual.tobytes(), image.tobytes())


class AssetBundlePipeline(unittest.TestCase):
    def test_real_images_roundtrip_deterministic_manifest_and_native_icons(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); suite, benchmark = write_test_evidence(root)
            formats = ['png', 'ico'] + (['webp'] if features.check('webp') else [])
            first = export_asset_bundle(suite, benchmark, root/'one', confirm_public=True, formats=formats)
            second = export_asset_bundle(suite, benchmark, root/'two', confirm_public=True, formats=formats)
            self.assertEqual(first, second)
            self.assertEqual(first['assetCount'], 2)
            self.assertFalse(first['resampled'])
            self.assertFalse(first['source']['nativeHostRerunByExporter'])
            self.assertEqual(first['alpha'], 'opaque native compositor matte')
            for group in first['assets']:
                self.assertEqual(group['nativeSizes'], [16, 32, 64, 128])
                self.assertEqual(len(group['files']), 9 if 'webp' in formats else 5)
                icon = next(f for f in group['files'] if f['format'] == 'ico')
                self.assertEqual([f['size'] for f in icon['frames']], [16, 32, 64, 128])
            verification = verify_asset_bundle(root/'one')
            self.assertEqual(verification['status'], 'passed')
            self.assertEqual(verification['manifestSha256'], _sha((root/'one/manifest.json').read_bytes()))
            self.assertEqual((root/'one/manifest.json').read_bytes(), (root/'two/manifest.json').read_bytes())
            self.assertTrue((root/'one/index.html').is_file())
            self.assertFalse((root/'one/failure.json').exists())

    def test_default_output_requires_opt_in_and_never_overwrites(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); suite, benchmark = write_test_evidence(root, (16,))
            out = root/'out'
            with self.assertRaisesRegex(AssetBundleError, 'consent'):
                export_asset_bundle(suite, benchmark, out, formats=['png'])
            self.assertFalse(out.exists())
            out.mkdir(); (out/'keep.txt').write_text('keep')
            with self.assertRaisesRegex(AssetBundleError, 'new directory'):
                export_asset_bundle(suite, benchmark, out, confirm_public=True, formats=['png'])
            self.assertEqual((out/'keep.txt').read_text(), 'keep')
            with self.assertRaisesRegex(AssetBundleError, 'outside'):
                export_asset_bundle(suite, benchmark, benchmark/'out', confirm_public=True, formats=['png'])
            self.assertFalse((benchmark/'out').exists())

    def test_report_missing_failed_or_substituted_is_rejected_before_output(self):
        mutations = [lambda d: d.update(status='failed'),
                     lambda d: d.update(nativeHostExecuted=False),
                     lambda d: d.update(suiteFileSha256='00'*32),
                     lambda d: d['cases'][0].update(sourceSize=128),
                     lambda d: d['cases'][0].update(readbackSha256='00'*32),
                     lambda d: d['cases'][0]['pages'][0].update(fileName='../outside.png'),
                     lambda d: d['cases'][0]['nativePageMeasurements'][0].update(staticSeekPixelsMatch=False)]
        for mutate in mutations:
            with self.subTest(mutation=mutate), tempfile.TemporaryDirectory() as tmp:
                root=Path(tmp);suite, benchmark=write_test_evidence(root,(16,))
                path=benchmark/'report.json'; document=json.loads(path.read_text());mutate(document)
                path.write_bytes(_json(document))
                with self.assertRaises(AssetBundleError):
                    export_asset_bundle(suite,benchmark,root/'out',confirm_public=True,formats=['png'])
                self.assertFalse((root/'out').exists())

    def test_project_quality_and_clock_must_match(self):
        for kind in ('quality','clock','failure','duplicate-json'):
            with self.subTest(kind=kind),tempfile.TemporaryDirectory() as tmp:
                root=Path(tmp);suite,benchmark=write_test_evidence(root,(16,))
                if kind=='quality':
                    path=benchmark/'sigil-neon-16/project-000.json'
                    data=json.loads(path.read_text());data.pop('render_quality');path.write_bytes(_json(data))
                elif kind=='clock': (benchmark/'fixture-clock.wav').write_bytes(b'not clock')
                elif kind=='failure': (benchmark/'failure.json').write_text('{}')
                else: (benchmark/'report.json').write_text('{"schema":1,"schema":2}')
                with self.assertRaises(ValueError): load_evidence(suite,benchmark)

    def test_page_corruption_leaves_no_success_marker(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);suite,benchmark=write_test_evidence(root,(16,))
            path=benchmark/'sigil-neon-16/atlas-page-000.png'
            with Image.open(path) as im:
                im.load();changed=im.copy()
            changed.putpixel((5,5),(255,0,0));changed.save(path);changed.close()
            with self.assertRaisesRegex(AssetBundleError, 'receipt'):
                export_asset_bundle(suite,benchmark,root/'out',confirm_public=True,formats=['png'])
            self.assertTrue((root/'out/failure.json').exists())
            self.assertFalse((root/'out/manifest.json').exists())

    def test_budget_failure_does_not_publish_manifest(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);suite,benchmark=write_test_evidence(root,(16,))
            with patch('tools.artwork_asset_bundle.MAX_OUTPUT_BYTES', 1):
                with self.assertRaisesRegex(AssetBundleError, 'budget'):
                    export_asset_bundle(suite,benchmark,root/'out',confirm_public=True,formats=['png'])
            self.assertFalse((root/'out/manifest.json').exists())
            self.assertTrue((root/'out/failure.json').exists())

    def test_output_asset_and_viewer_tampering_are_detected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);suite,benchmark=write_test_evidence(root,(16,))
            result=export_asset_bundle(suite,benchmark,root/'out',confirm_public=True,formats=['png'])
            for path in (root/'out'/result['assets'][0]['files'][0]['file'], root/'out/gallery.js'):
                original=path.read_bytes();path.write_bytes(original+b'corruption')
                with self.assertRaises(ValueError): verify_asset_bundle(root/'out')
                path.write_bytes(original)
            self.assertEqual(verify_asset_bundle(root/'out')['status'],'passed')

    def test_symlink_paths_and_manifest_traversal_fail_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);suite,benchmark=write_test_evidence(root,(16,))
            result=export_asset_bundle(suite,benchmark,root/'out',confirm_public=True,formats=['png'])
            bad=copy.deepcopy(result);bad['assets'][0]['files'][0]['file']='../outside.png'
            (root/'out/manifest.json').write_bytes(_json(bad))
            with self.assertRaisesRegex(AssetBundleError, 'relative'): verify_asset_bundle(root/'out')
            try:(root/'alias').symlink_to(benchmark,target_is_directory=True)
            except OSError:self.skipTest('OS does not permit symlinks')
            with self.assertRaisesRegex(AssetBundleError, 'Symlink'): load_evidence(suite,root/'alias')

    def test_manifest_identity_frames_and_inventory_must_remain_consistent(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);suite,benchmark=write_test_evidence(root,(16,))
            result=export_asset_bundle(suite,benchmark,root/'out',confirm_public=True,formats=['png','ico'])
            mutations=[lambda d:d['assets'][0].update(assetKey='bfasset1-'+'00'*32),
                       lambda d:d['assets'][0].update(nativeSizes=[True]),
                       lambda d:d['assets'][0]['sourceTiles'][0].update(rgbaSha256='ab'*32),
                       lambda d:d['assets'][0]['files'].pop(),
                       lambda d:d['assets'][0]['files'][0].update(file=['invalid']),
                       lambda d:d['assets'].append(copy.deepcopy(d['assets'][0]))]
            for mutate in mutations:
                altered=copy.deepcopy(result);mutate(altered)
                (root/'out/manifest.json').write_bytes(_json(altered))
                with self.assertRaises(ValueError):verify_asset_bundle(root/'out')

    def test_cli_export_and_verification_and_nonzero_errors(self):
        script=ROOT/'scripts/export-artwork-assets.py'
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);suite,benchmark=write_test_evidence(root,(16,))
            result=subprocess.run([sys.executable,str(script),'--confirm-public','export','--suite',str(suite),
                '--benchmark',str(benchmark),'--output',str(root/'out'),'--formats','png,ico'],
                cwd=ROOT,text=True,capture_output=True,timeout=20)
            self.assertEqual(result.returncode,0,result.stderr)
            verified=subprocess.run([sys.executable,str(script),'--confirm-public','verify','--bundle',str(root/'out')],
                cwd=ROOT,text=True,capture_output=True,timeout=20)
            self.assertEqual(verified.returncode,0,verified.stderr)
            self.assertTrue(json.loads(verified.stdout)['decodedPixelsVerified'])
            bad=subprocess.run([sys.executable,str(script),'verify','--bundle',str(root/'out')],
                cwd=ROOT,text=True,capture_output=True,timeout=20)
            self.assertNotEqual(bad.returncode,0)


if __name__ == '__main__':
    unittest.main()
