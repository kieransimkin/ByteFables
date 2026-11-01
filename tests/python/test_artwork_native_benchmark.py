"""Input security, real source-pixel QA and separately gated native compositor tests."""
from __future__ import annotations
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import wave

from PIL import Image
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'integrations' / 'framerudiments'))
from tools.artwork_native_benchmark import (
    BACKGROUND, SUITE_SCHEMA, BenchmarkError, load_suite, run_benchmark,
    create_fixture_clock, project_for_page, verify_composited_page,
)
from tools.artwork_atlas_readback import AtlasReadbackError, readback_artwork_atlas
from bytefables_framerudiments.artwork import ArtworkRenderer, BRIDGE


def encode(value):
    return (json.dumps(value, indent=2) + '\n').encode()


def fixture_plan(size=16, family='sigil', count=2):
    """Hand-authored contract fixture; production suites use the existing TS API."""
    step = size + 8
    width = count * step
    tiles = []
    for i in range(count):
        digest = hashlib.sha256(f'public-test-{i}'.encode()).hexdigest()
        rect = [i * step + 4, 4, i * step + 4 + size, 4 + size]
        tiles.append({'inputIndex':i, 'digestHex':digest, 'rect':rect,
                      'uv':[rect[0]/width, rect[1]/step, rect[2]/width, rect[3]/step],
                      'layer':{'id':f'atlas-0-{i}', 'type':'rudiment', 'renderer':'bytefables-artwork-v1',
                               'bounds':rect, 'motion':{'kind':'named','pattern':'circle'}, 'axes':[0],
                               'history_frames':1, 'style':{'bridge_version':BRIDGE,'digest_hex':digest,
                               'style':family,'palette':'neon','complexity':4}}})
    return {'version':'bytefables.artwork-atlas.v1','publicOnly':True,'guarantee':'presentation-only',
            'inputCount':count,'pages':[{'index':0,'width':width,'height':step,'tiles':tiles}]}


def write_suite(root, cases=(('sigil',16),), count=2):
    root.mkdir(parents=True,exist_ok=True)
    (root/'plans').mkdir(exist_ok=True)
    document={'schema':SUITE_SCHEMA,'publicOnly':True,'guarantee':'presentation-only',
              'corpus':{'id':'bytefables.public-benchmark-corpus.v1','seed':'test','count':count},'cases':[]}
    for family,size in cases:
        name=f'{family}-neon-{size}'
        payload=encode(fixture_plan(size,family,count))
        (root/'plans'/f'{name}.json').write_bytes(payload)
        document['cases'].append({'id':name,'plan':f'plans/{name}.json',
              'planSha256':hashlib.sha256(payload).hexdigest(),'family':family,'palette':'neon','sourceSize':size})
    (root/'suite.json').write_bytes(encode(document))
    return root/'suite.json'


def update_plan(root, mutate):
    suite=json.loads((root/'suite.json').read_text())
    path=root/suite['cases'][0]['plan']
    data=json.loads(path.read_text());mutate(data)
    payload=encode(data);path.write_bytes(payload)
    suite['cases'][0]['planSha256']=hashlib.sha256(payload).hexdigest()
    (root/'suite.json').write_bytes(encode(suite))


class InputBoundaries(unittest.TestCase):
    def test_valid_multiple_case_suite_and_exact_native_project(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); path=write_suite(root,(('sigil',16),('crystal',32)))
            suite=load_suite(path)
            self.assertEqual(len(suite.cases),2)
            project=project_for_page(suite.cases[0].plan['pages'][0],'ab'*32)
            self.assertEqual(project['clock']['status'],'synthetic')
            self.assertEqual(project['background'],{'colour':'#111827'})
            self.assertNotIn('post_effects',project)
            self.assertEqual(project['audio']['source']['sha256'],'ab'*32)

    def test_suite_rejects_changed_hash_traversal_and_duplicate_cases(self):
        for mutation in ('hash','path','duplicate','public','count','budget','extra'):
            with self.subTest(mutation=mutation),tempfile.TemporaryDirectory() as tmp:
                root=Path(tmp);path=write_suite(root);data=json.loads(path.read_text())
                if mutation=='hash':data['cases'][0]['planSha256']='00'*32
                elif mutation=='path':data['cases'][0]['plan']='../outside.json'
                elif mutation=='duplicate':data['cases']*=2
                elif mutation=='public':data['publicOnly']=False
                elif mutation=='count':data['corpus']['count']=True
                elif mutation=='budget':data['corpus']['count']=1000;data['cases']*=9
                else:data['command']='execute'
                path.write_bytes(encode(data))
                with self.assertRaises(BenchmarkError):load_suite(path)

    def test_no_unexpected_native_fields_or_motion_routes(self):
        mutations=[lambda p:p['pages'][0]['tiles'][0]['layer'].update(opacity=0),
                   lambda p:p['pages'][0]['tiles'][0]['layer'].update(motion={'kind':'recording','file':'unapproved'}),
                   lambda p:p['pages'][0]['tiles'][0]['layer'].update(axes=[False]),
                   lambda p:p['pages'][0]['tiles'][0]['layer'].update(history_frames=True),
                   lambda p:p['pages'][0]['tiles'][0]['layer']['style'].update(palette='mono'),
                   lambda p:p['pages'][0]['tiles'][0].update(uv=[0,0,1,1]),
                   lambda p:p['pages'][0].update(index=False)]
        for mutate in mutations:
            with tempfile.TemporaryDirectory() as tmp:
                root=Path(tmp);path=write_suite(root);update_plan(root,mutate)
                with self.assertRaises((BenchmarkError,AtlasReadbackError)):load_suite(path)

    def test_duplicate_json_and_nonfinite_values_are_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'suite.json'
            for raw in (b'{"schema":"x","schema":"y"}',b'{"bad":NaN}'):
                path.write_bytes(raw)
                with self.assertRaises(BenchmarkError):load_suite(path)

    def test_cases_must_have_same_ordered_corpus(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);path=write_suite(root,(('sigil',16),('crystal',16)))
            def mutate(p):
                tile=p['pages'][0]['tiles'][0];tile['digestHex']='ab'*32
                tile['layer']['style']['digest_hex']=tile['digestHex']
            update_plan(root,mutate)
            with self.assertRaisesRegex(BenchmarkError,'same ordered'):load_suite(path)

    @unittest.skipUnless(hasattr(os,'symlink'),'Symlinks unavailable')
    def test_symlink_plan_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);path=write_suite(root)
            original=root/'plans/sigil-neon-16.json';target=root/'saved.json'
            original.rename(target)
            try:original.symlink_to(target)
            except OSError:self.skipTest('OS disallows symlinks in this environment')
            with self.assertRaises(BenchmarkError):load_suite(path)

    def test_opt_in_missing_native_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);path=write_suite(root/'input');out=root/'out'
            with self.assertRaisesRegex(BenchmarkError,'consent'):run_benchmark(path,out)
            with patch('tools.artwork_native_benchmark._native_api',side_effect=BenchmarkError('host absent')):
                with self.assertRaisesRegex(BenchmarkError,'host absent'):
                    run_benchmark(path,out,confirm_public=True,synthetic_fixture=True)
            self.assertFalse(out.exists())
            out.mkdir();(out/'keep').write_text('keep')
            with self.assertRaisesRegex(BenchmarkError,'new directory'):
                run_benchmark(path,out,confirm_public=True,synthetic_fixture=True)
            self.assertEqual((out/'keep').read_text(),'keep')

    def test_failed_run_keeps_diagnostics_without_success_marker(self):
        # Failure-path injection only: this is NOT a substitute native render test.
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); path=write_suite(root/'input'); out=root/'failed'
            with patch('tools.artwork_native_benchmark._native_api',return_value=object()), \
                 patch('tools.artwork_native_benchmark._render_page',side_effect=BenchmarkError('injected failure')):
                with self.assertRaisesRegex(BenchmarkError,'injected failure'):
                    run_benchmark(path,out,confirm_public=True,synthetic_fixture=True)
            report=json.loads((out/'failure.json').read_text())
            self.assertEqual(report['status'],'failed')
            self.assertEqual(report['exception'],'BenchmarkError')
            self.assertFalse((out/'report.json').exists())
            self.assertFalse((out/'index.html').exists())
            with self.assertRaisesRegex(BenchmarkError,'new directory'):
                run_benchmark(path,out,confirm_public=True,synthetic_fixture=True)

    def test_explicit_synthetic_wav_is_real_pinned_pcm_and_not_overwritten(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'fixture.wav';sha=create_fixture_clock(path)
            self.assertEqual(sha,hashlib.sha256(path.read_bytes()).hexdigest())
            with wave.open(str(path),'rb') as wav:
                self.assertEqual((wav.getnchannels(),wav.getframerate(),wav.getnframes()),(1,48000,48000))
                self.assertEqual(wav.readframes(48000),b'\0\0'*48000)
            with self.assertRaises(FileExistsError):create_fixture_clock(path)


class SourcePixelChecks(unittest.TestCase):
    def test_all_nine_families_render_real_small_icons_reproducibly(self):
        families=('sigil','constellation','heraldry','topography','crystal','mandala','cellular','branching','orbital')
        for family in families:
            for size in (16,32,64,128):
                for palette in ('neon','pastel','mono'):
                    style={'bridge_version':BRIDGE,'digest_hex':'00'*32,'style':family,'palette':palette,'complexity':4}
                    with self.subTest(family=family,size=size,palette=palette):
                        renderer=ArtworkRenderer((size,size),style)
                        a=renderer.render(None);b=renderer.render(None)
                        self.assertEqual(a.mode,'RGBA');self.assertEqual(a.size,(size,size))
                        self.assertEqual(a.tobytes(),b.tobytes());a.close();b.close()

    def test_cellular_subpixel_cells_do_not_invert_rectangles(self):
        for size in (16,18,24,32,64):
            for complexity in range(1,9):
                style={'bridge_version':BRIDGE,'digest_hex':'00'*32,'style':'cellular','palette':'neon','complexity':complexity}
                with self.subTest(size=size,complexity=complexity):
                    image=ArtworkRenderer((size,size),style).render(None)
                    self.assertIsNotNone(image.getchannel('A').getbbox());image.close()

    def test_saved_composite_pixels_and_gutters_checked_separately_from_rgba_sources(self):
        plan=fixture_plan(32);page=plan['pages'][0]
        image=Image.new('RGBA',(page['width'],page['height']),BACKGROUND+(255,))
        for tile in page['tiles']:
            source=ArtworkRenderer((32,32),tile['layer']['style']).render(None)
            image.alpha_composite(source,dest=tuple(tile['rect'][:2]));source.close()
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);path=root/'atlas-page-000.png'
            image.convert('RGB').save(path)
            report=verify_composited_page(page,path,ArtworkRenderer)
            self.assertTrue(report['guttersMatch'])
            self.assertTrue(all(0<t['sourceAlphaCoverage']<1 for t in report['tiles']))
            check=readback_artwork_atlas(plan,root)
            self.assertEqual(check['sourcePixelsComparison'],'not-run')
            self.assertTrue(all(t['quality']['alphaCoverage']==1 for t in check['tiles']))
            with self.assertRaisesRegex(AtlasReadbackError,'Source-only'):
                readback_artwork_atlas(plan,root,compare_source=True)
            altered=image.copy();altered.putpixel((0,0),(255,255,255,255));altered.convert('RGB').save(path)
            with self.assertRaisesRegex(BenchmarkError,'gutters'):verify_composited_page(page,path,ArtworkRenderer)
            altered.close();altered=image.copy();altered.putpixel((5,5),(0,0,0,255));altered.convert('RGB').save(path)
            with self.assertRaisesRegex(BenchmarkError,'source mismatch'):verify_composited_page(page,path,ArtworkRenderer)
            altered.close()
        image.close()


class NativeHostIntegration(unittest.TestCase):
    def test_real_compositor_exports_readback_gallery_and_repeatability(self):
        if importlib.util.find_spec('framerudiments') is None:
            if os.environ.get('BYTEFABLES_REQUIRE_NATIVE')=='1':
                self.fail('Native host required by CI but not installed')
            self.skipTest('FrameRudiments native host not installed; no fallback render claim')
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            cases=tuple((f,s) for f in ('sigil','cellular','crystal') for s in (16,32,64,128))
            suite=write_suite(root/'suite',cases)
            first=run_benchmark(suite,root/'first',confirm_public=True,synthetic_fixture=True,samples=2)
            second=run_benchmark(suite,root/'second',confirm_public=True,synthetic_fixture=True,samples=1)
            self.assertTrue(first['nativeHostExecuted']);self.assertEqual(first['status'],'passed')
            self.assertEqual(len(first['cases']),12)
            for a,b in zip(first['cases'],second['cases']):
                self.assertEqual(a['pages'],b['pages'])
                self.assertEqual(a['compositedSourceComparison'],'passed')
                self.assertTrue(all(p['staticSeekPixelsMatch'] for p in a['nativePageMeasurements']))
            self.assertTrue((root/'first/index.html').is_file())
            self.assertFalse((root/'first/failure.json').exists())


if __name__=='__main__':
    unittest.main()
