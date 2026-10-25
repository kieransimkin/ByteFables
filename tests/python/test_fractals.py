"""Fractal generator contracts: genuine local CPU pixels, NOT AI model benchmarks."""
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'integrations'/'framerudiments'))

from bytefables_framerudiments.fractals import FractalRenderer,BRIDGE_VERSION,FAMILIES
from tools.hash_image_bench.fractal import render_fractal_study
from tools.hash_image_bench.experiment import prepare, render_local_models, descriptor, audit_prompt


SEED=hashlib.sha256(b'public fixture seed').hexdigest()
STYLE={'bridge_version':BRIDGE_VERSION,'family':'julia','palette':'neon',
       'seed_hex':SEED,'feature_bits':'10010101','quality':'draft'}


class GeneratorTests(unittest.TestCase):
    def test_families_deterministic_bounded_and_nonblank(self):
        for family in FAMILIES:
            style={**STYLE,'family':family}
            a=FractalRenderer((64,64),style).render(None)
            b=FractalRenderer((64,64),style).render(None)
            self.assertEqual(a.size,(64,64))
            self.assertEqual(a.mode,'RGBA')
            self.assertEqual(a.tobytes(),b.tobytes(),family)
            self.assertGreater(len(set(a.tobytes())),5,family)
            # Nothing is recoverable by hashing the RGBA; the output is art.
            self.assertNotEqual(hashlib.sha256(a.tobytes()).hexdigest(),SEED)

    def test_rejects_untrusted_executable_and_oversized_style(self):
        invalid=[{**STYLE,'seed_hex':'00'*31},
                 {**STYLE,'seed_hex':'AB'*32},
                 {**STYLE,'feature_bits':'0'*7},
                 {**STYLE,'quality':'production-secret'},
                 {**STYLE,'family':'../commands'},
                 {**STYLE,'palette':'unknown'},
                 {**STYLE,'extra':'exec'},
                 {**STYLE,'bridge_version':'other'}]
        for spec in invalid:
            with self.assertRaises(ValueError):FractalRenderer((64,64),spec)
        with self.assertRaises(ValueError):FractalRenderer((800,800),STYLE)
        with self.assertRaises(ValueError):FractalRenderer((8,8),STYLE)

    def test_public_typescript_fixture_produces_real_pixels(self):
        fixture=json.loads((ROOT/'tests'/'vectors'/'fractal-v1.json').read_text())
        layer=fixture['layer']
        self.assertEqual(layer['renderer'],'bytefables-fractal-v1')
        a=FractalRenderer((128,128),layer['style']).render(None)
        b=FractalRenderer((128,128),layer['style']).render(None)
        self.assertEqual(a.tobytes(),b.tobytes())

    def test_fractal_prompt_style_preserves_every_explicit_binary_choice(self):
        feature={'featureId':'shape','scope':'main subject','property':'silhouette',
                 'selected':'spiky','opposite':'smooth'}
        prompt=descriptor([feature],strategy='fractal')
        self.assertIn('self-similar',prompt)
        self.assertEqual(audit_prompt(prompt,[feature])['literalCoverage'],1.0)
        self.assertEqual(audit_prompt(prompt,[feature])['oppositePhrasePresent'],[])

    def test_axis_isolation_and_avalanche_are_distinct_experiments(self):
        base=STYLE
        altered={**STYLE,'feature_bits':'00010101'}
        a=FractalRenderer((48,48),base).render(None).tobytes()
        b=FractalRenderer((48,48),altered).render(None).tobytes()
        self.assertNotEqual(a,b)
        changed_seed={**STYLE,'seed_hex':hashlib.sha256(bytes.fromhex(SEED)).hexdigest()}
        c=FractalRenderer((48,48),changed_seed).render(None).tobytes()
        self.assertNotEqual(a,c)

    def test_counterfactual_fractal_runner_separates_seed_and_feature_axes(self):
        with tempfile.TemporaryDirectory() as directory:
            source='000102030405060708090a0b0c0d0e0f'
            prepare(source,directory,budgets=(8,),strategies=('direct',),paired_bits=(0,31))
            report=render_fractal_study(directory,families=('julia',),size=48,max_images=6)
            self.assertEqual(report['images'],6)
            self.assertEqual(len(report['receipts'][0]['recipe']['rendererSourceSha256']),64)
            self.assertIn('pillow',report['receipts'][0]['runtimeVersions'])
            self.assertEqual(len(report['pairComparisons']),4)
            isolated={r['flippedBit']:r for r in report['pairComparisons'] if r['seedMode']=='axis-isolated'}
            avalanche={r['flippedBit']:r for r in report['pairComparisons'] if r['seedMode']=='avalanche'}
            self.assertEqual(isolated[31]['channelChangeFraction'],0)
            self.assertGreater(isolated[0]['channelChangeFraction'],0)
            self.assertGreater(avalanche[31]['channelChangeFraction'],0)
            self.assertTrue((Path(directory)/'fractal'/'gallery.html').is_file())
            again=render_fractal_study(directory,families=('julia',),size=48,max_images=6)
            self.assertEqual([x['imageSha256'] for x in again['receipts']],
                             [x['imageSha256'] for x in report['receipts']])
            with self.assertRaises(ValueError):render_fractal_study(directory,max_images=1)

    def test_img2img_controlled_model_jobs_and_tamper_detection(self):
        with tempfile.TemporaryDirectory() as directory:
            prepare('00010203', directory, budgets=(8,), strategies=('direct',), paired_bits=(0,))
            models=Path(directory)/'models.json'
            models.write_text(json.dumps({'models':[{'id':'test','family':'stable-diffusion',
                'localPath':'/not/present','steps':5,'guidance':2.0,'width':256,'height':256}]}))
            with self.assertRaisesRegex(ValueError,'render-fractals'):
                render_local_models(directory,models,execute=False,max_jobs=2,repetitions=1,
                                    conditioning_policy='fractal-img2img')
            render_fractal_study(directory,families=('julia',),modes=('avalanche',),size=48,max_images=2)
            dry=render_local_models(directory,models,execute=False,max_jobs=2,repetitions=1,
                conditioning_policy='fractal-img2img',fractal_family='julia',img2img_strength=.5)
            normal=render_local_models(directory,models,execute=False,max_jobs=2,repetitions=1)
            self.assertNotEqual(dry['jobs'][0]['jobId'],normal['jobs'][0]['jobId'])
            with self.assertRaisesRegex(ValueError,'Separate'):
                render_local_models(directory,models,execute=False,max_jobs=2,repetitions=1,
                    conditioning_policy='fractal-img2img',latent_policy='fractal-spectral')
            receipts=list((Path(directory)/'fractal'/'renders').glob('*.json'))
            to_damage=json.loads(receipts[0].read_text())
            img=Path(directory)/to_damage['imageFile']
            img.write_bytes(b'corrupted')
            with self.assertRaisesRegex(ValueError,'tampered'):
                render_local_models(directory,models,execute=False,max_jobs=2,repetitions=1,
                                    conditioning_policy='fractal-img2img')

    def test_fractal_spectral_model_job_dry_run_requires_no_model_or_gpu(self):
        with tempfile.TemporaryDirectory() as directory:
            prepare('00010203',directory,budgets=(4,),strategies=('direct',))
            models=Path(directory)/'models.json'
            models.write_text(json.dumps({'models':[{'id':'test','family':'stable-diffusion',
                'localPath':'/not/present','steps':5,'guidance':2.0,'width':256,'height':256}]}))
            regular=render_local_models(directory,models,execute=False,max_jobs=1,repetitions=1)
            fractal=render_local_models(directory,models,execute=False,max_jobs=1,repetitions=1,
                latent_policy='fractal-spectral',fractal_beta=1.2,fractal_mix=.25)
            self.assertNotEqual(regular['jobs'][0]['jobId'],fractal['jobs'][0]['jobId'])
            with self.assertRaises(ValueError):
                render_local_models(directory,models,execute=False,latent_policy='fractal-spectral',fractal_mix=0)


class OptionalTorchLatents(unittest.TestCase):
    def test_fractal_noise_statistics_on_cpu(self):
        try:
            import torch
        except ImportError:
            self.skipTest('PyTorch is optional')
        from tools.hash_image_bench.fractal_latents import spectral_fractal_latents
        a=spectral_fractal_latents(77,(1,4,32,32),beta=1.5,mix=.35)
        b=spectral_fractal_latents(77,(1,4,32,32),beta=1.5,mix=.35)
        self.assertTrue(torch.equal(a,b))
        self.assertTrue(torch.isfinite(a).all())
        self.assertAlmostEqual(float(a.std(dim=(-2,-1)).mean()),1.0,places=3)
        white=spectral_fractal_latents(77,(1,4,32,32),mix=0)
        self.assertFalse(torch.equal(a,white))
        def neighbor(img):
            return float((img[:,:,:,:-1]*img[:,:,:,1:]).mean())
        self.assertGreater(neighbor(a),neighbor(white))
        with self.assertRaises(ValueError):spectral_fractal_latents(0,(1,4,32,32),mix=1)
        with self.assertRaises(ValueError):spectral_fractal_latents(0,(1,4,32,32),beta=-1)


if __name__=='__main__':unittest.main()
