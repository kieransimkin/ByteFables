"""CPU-only validations for prompt and experiment contracts; no simulated image-model rankings."""
import hashlib
import http.server
import json
import subprocess
import sys
import types
from unittest.mock import patch
import tempfile
import threading
import unittest
from pathlib import Path

from tools.hash_image_bench.experiment import (
    VERSION, _require_loopback, audit_prompt, bitplan, descriptor, make_pair_hex,
    prepare, local_llm_prompt, load, report_experiment, assess_judgments,
    render_local_models, export_framerudiments_assets, validate_model_file
)

ROOT=Path(__file__).resolve().parents[2]
SOURCE=hashlib.sha256(b'ByteFables random public vector').hexdigest()

class BenchTests(unittest.TestCase):
    def test_bitplan_consistent_with_typescript_contract(self):
        p=bitplan(SOURCE)
        self.assertEqual(p['bitCount'],256)
        self.assertEqual(len(p['choices']),256)
        self.assertEqual(len({c['featureId'] for c in p['choices']}),256)
        self.assertEqual(p['choices'][0]['bit'],int(SOURCE[0],16)>=8)
        self.assertEqual(p['choices'][0]['scope'],'main subject')
        self.assertEqual(p['choices'][255]['scope'],'motif 014')
        self.assertEqual(p['schema'],'bytefables.visual-bits.v1')

    def test_all_bits_flip_independently(self):
        p=bitplan(SOURCE)
        for i in (0,1,7,8,31,32,64,127,255):
            flipped=bitplan(make_pair_hex(SOURCE,i))
            changed=[j for j,(a,b) in enumerate(zip(p['choices'],flipped['choices'])) if a['bit']!=b['bit']]
            self.assertEqual(changed,[i]);self.assertEqual(flipped['bitCount'],256)
            self.assertNotEqual(flipped['identityDigestHex'],p['identityDigestHex'])

    def test_prepare_controls_and_counterfactuals(self):
        with tempfile.TemporaryDirectory() as d:
            exp=prepare(SOURCE,d,budgets=(8,16,32),strategies=('direct','structured'),paired_bits=(0,31))
            self.assertEqual(exp['schema'],VERSION)
            self.assertEqual(len(exp['cases']),3)
            self.assertEqual(len(exp['candidates']),18)
            original=next(c for c in exp['candidates'] if c['caseId']=='original' and c['bitBudget']==8 and c['strategy']=='direct')
            flip_hi=next(c for c in exp['candidates'] if c['caseId']=='flip-0031' and c['bitBudget']==8 and c['strategy']=='direct')
            self.assertEqual(original['prompt'],flip_hi['prompt'], 'Unprompted high bit cannot be recovered from the prompt')
            flip_lo=next(c for c in exp['candidates'] if c['caseId']=='flip-0000' and c['bitBudget']==8 and c['strategy']=='direct')
            self.assertNotEqual(original['prompt'],flip_lo['prompt'])
            self.assertEqual(original['audit']['literalCoverage'],1.0)
            self.assertEqual(len(exp['cases'][0]['features']),256)
            self.assertTrue((Path(d)/'experiment.json').exists())
            with self.assertRaises(FileExistsError): prepare(SOURCE,d)

    def test_prompt_coverage_and_contradiction_are_only_lexical(self):
        c=[{'selected':'spiky','opposite':'smooth','featureId':'shape'}]
        self.assertEqual(audit_prompt('spiky',c)['literalCoverage'],1)
        self.assertEqual(audit_prompt('smooth',c)['literalCoverage'],0)
        self.assertEqual(audit_prompt('smooth',c)['oppositePhrasePresent'],['shape'])

    def test_no_remote_endpoint(self):
        for host in ('https://127.0.0.1:1234/v1/chat/completions',
                     'http://api.openai.com:80/v1/chat/completions',
                     'http://127.0.0.1:1234/other',
                     'http://127.0.0.1:1234/v1/chat/completions?q=1'):
            with self.assertRaises(ValueError):_require_loopback(host)
        _require_loopback('http://127.0.0.1:1234/v1/chat/completions')

    def test_local_llm_receives_decisions_not_hash(self):
        captures=[]
        class Handler(http.server.BaseHTTPRequestHandler):
            def do_POST(self):
                length=int(self.headers.get('Content-Length','0'))
                payload=json.loads(self.rfile.read(length))
                captures.append(payload)
                content=json.loads(payload['messages'][1]['content'])
                text='An illuminated sculpture: '+'; '.join(d['required'] for d in content['choices'])
                raw=json.dumps({'prompt':text, 'negative_prompt':''}).encode()
                output=json.dumps({'choices':[{'message':{'content':raw.decode()}}]}).encode()
                self.send_response(200);self.send_header('Content-Type','application/json')
                self.send_header('Content-Length',str(len(output)));self.end_headers();self.wfile.write(output)
            def log_message(self,*args):pass
        server=http.server.HTTPServer(('127.0.0.1',0),Handler)
        runner=threading.Thread(target=server.serve_forever,daemon=True);runner.start()
        try:
            features=bitplan(SOURCE)['choices'][:4]
            output=local_llm_prompt(features,endpoint=f'http://127.0.0.1:{server.server_port}/v1/chat/completions',
                                    model='mock-local',strategy='structured',seed=2)
            self.assertTrue(output['parseableJson'])
            self.assertEqual(audit_prompt(output['prompt'],features)['literalCoverage'],1.0)
            self.assertNotIn(SOURCE,json.dumps(captures))
            self.assertEqual(captures[0]['model'],'mock-local')
        finally:server.shutdown();server.server_close()

    def test_model_paths_are_explicit_and_dry_run_has_no_gpu_or_models(self):
        with tempfile.TemporaryDirectory() as d:
            prepare(SOURCE,d,budgets=(4,),strategies=('direct',))
            cfg={'models':[{'id':'tiny','localPath':'/not/a/real/model','steps':15,'width':256,'height':256,
                            'guidance':4.0,'device':'cuda','dtype':'float16','negativePrompt':False}]}
            filename=Path(d)/'models.json';filename.write_text(json.dumps(cfg))
            self.assertEqual(len(validate_model_file(filename,require_files=False)),1)
            dry=render_local_models(d,filename,execute=False,max_jobs=4,repetitions=2)
            self.assertEqual(dry['status'],'dry-run');self.assertEqual(dry['jobCount'],2)
            with self.assertRaises(ValueError):validate_model_file(filename,require_files=True)
            with self.assertRaises(ValueError):render_local_models(d,filename,execute=False,max_jobs=1)
            result=report_experiment(d)
            self.assertEqual(result['renderAttempts'],0)
            self.assertIsNone(result['imageConditions'] or None)

    def test_blind_scoring_accepts_only_selected_bits_and_completed_jobs(self):
        with tempfile.TemporaryDirectory() as d:
            exp=prepare(SOURCE,d,budgets=(8,),strategies=('direct',))
            c=exp['candidates'][0]
            r={'jobId':'aa','status':'completed','candidateId':c['candidateId'],
               'imageModel':'fixture','writerId':'deterministic-baseline','strategy':'direct','bitBudget':8,
               'caseId':'original'}
            graded=assess_judgments(exp,[r],[{'jobId':'aa','answers':{'0':c['features'][0]['bit'],'1':1-c['features'][1]['bit']}}])
            self.assertEqual(graded['correct'],1);self.assertEqual(graded['assessed'],2)
            with self.assertRaises(ValueError):assess_judgments(exp,[r],[{'jobId':'aa','answers':{'255':0}}])

    def test_local_inference_orchestration_with_explicitly_fake_test_pipeline(self):
        # Strictly a unit stub, NEVER a model-quality result or released image benchmark.
        with tempfile.TemporaryDirectory() as d:
            run_path=Path(d)/'run'
            prepare(SOURCE,run_path,budgets=(4,),strategies=('direct',))
            modeldir=Path(d)/'weights'
            modeldir.mkdir()
            (modeldir/'model_index.json').write_text('\"fixture\"')
            cfg={'models':[{'id':'unit-test-model','localPath':str(modeldir),'steps':2,'width':256,'height':256,
                            'guidance':1.0,'device':'cpu','dtype':'float32','negativePrompt':False}]}
            config=Path(d)/'models.json';config.write_text(json.dumps(cfg))
            # Fake torch/diffusers modules exercise orchestration and receipt handling only.
            class Generator:
                def __init__(self,device):self.device=device
                def manual_seed(self,seed):self.seed=seed;return self
            class FakeImage:
                def save(self,path,format=None):Path(path).write_bytes(b'TEST-FIXTURE-NOT-A-REAL-PNG')
            class FakePipeline:
                @classmethod
                def from_pretrained(cls,*args,**kwargs):return cls()
                def to(self,device):return self
                def __call__(self,**kwargs):return types.SimpleNamespace(images=[FakeImage()])
            torch_fake=types.SimpleNamespace(float32='float32',float16='float16',bfloat16='bfloat16',
                Generator=Generator,__version__='mocked-unit-test',cuda=types.SimpleNamespace(is_available=lambda:False))
            diffusers_fake=types.SimpleNamespace(DiffusionPipeline=FakePipeline)
            with patch.dict(sys.modules,{'torch':torch_fake,'diffusers':diffusers_fake}), \
                 patch('tools.hash_image_bench.experiment.compute_image_diagnostics',
                       return_value={'lumaMean':0.25,'saturationMean':0.2,'edgeMean':0.1}):
                result=render_local_models(run_path,config,execute=True,max_jobs=1,repetitions=1,allow_cpu=True)
            self.assertEqual(result['jobs'][0]['status'],'completed')
            receipt=load(run_path/'renders'/f"{result['jobs'][0]['jobId']}.json")
            self.assertIn('imageSha256',receipt)
            assets=export_framerudiments_assets(run_path)
            self.assertEqual(len(assets['assets']),1)
            self.assertEqual(assets['assets'][0]['layerFragment']['type'],'sprite')
            self.assertEqual(assets['assets'][0]['effectsTarget'],
                             'layer:bytefables-'+receipt['jobId'])
            report=report_experiment(run_path)
            self.assertEqual(report['completedImages'],1)
            self.assertEqual(report['imageConditions'][0]['imageModel'],'unit-test-model')

    def test_generated_art_is_handed_to_native_host_without_reprocessing(self):
        with tempfile.TemporaryDirectory() as d:
            prepare(SOURCE,d,budgets=(4,),strategies=('direct',))
            handoff=export_framerudiments_assets(d)
            self.assertEqual(handoff['renderEngine'],'framerudiments')
            self.assertEqual(handoff['assets'],[])
            self.assertTrue((Path(d)/'framerudiments-assets.json').exists())

if __name__=='__main__':unittest.main()
