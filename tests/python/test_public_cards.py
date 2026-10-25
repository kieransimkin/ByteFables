"""Native FrameRudiments PUBLIC printed cards: true PNG optical readback."""
import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from PIL import ImageFont

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'integrations'/'framerudiments'))
from bytefables_framerudiments.public_cards import PublicRecoveryCardRenderer
from bytefables_framerudiments.renderers import register_bytefables_renderers


class PublicCards(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.font_path=ImageFont.truetype('DejaVuSansMono.ttf',14).path
        cls.font_sha=hashlib.sha256(Path(cls.font_path).read_bytes()).hexdigest()

    @staticmethod
    def sample():
        result=subprocess.check_output(['node',str(ROOT/'bin/bytefables.mjs'),'public-print-sheet',
            '--confirm-public','--public-hex','aa'*96,'--namespace','danceflow',
            '--kind','node-id','--fragment-bytes','52'],cwd=ROOT,text=True,timeout=20)
        return json.loads(result)

    def test_registered_native_card_has_pinned_font_and_fails_closed(self):
        sheet=self.sample()
        page=sheet['frames'][0]
        style=page['layer']['style']
        renderer=PublicRecoveryCardRenderer((1024,1440),style)
        with self.assertRaisesRegex(ValueError,'prepare'):
            renderer.render(None)
        with self.assertRaisesRegex(ValueError,'pinned'):
            renderer.prepare(SimpleNamespace(font_ref=None))
        renderer.prepare(SimpleNamespace(font_ref={'path':str(self.font_path),'sha256':self.font_sha}))
        a=renderer.render(None)
        b=renderer.render(None)
        self.assertEqual(a.tobytes(),b.tobytes())
        self.assertEqual(a.mode,'RGBA')
        self.assertEqual(a.size,(1024,1440))
        for bad in ({**style,'command':'rm -rf /'},
                    {**style,'quiet_zone':1},
                    {**style,'fingerprint':'fake'},
                    {**style,'manual_text':'<svg onload=alert(1)>'}):
            with self.assertRaises(ValueError):
                PublicRecoveryCardRenderer((1024,1440),bad)
        # Native registry exposes the new generator without dynamic imports from project JSON.
        class Registry:
            def __init__(self):self.registry={}
            def register(self,name,constructor):self.registry[name]=constructor
        registry=Registry()
        register_bytefables_renderers(registry)
        self.assertIs(registry.registry['bytefables-public-card-v1'],PublicRecoveryCardRenderer)

    def test_print_pngs_independently_decode_exact_frame_text(self):
        import importlib.util
        if importlib.util.find_spec('cv2') is None:
            self.skipTest('OpenCV optical decoder optional outside qualified CI')
        from importlib.machinery import SourceFileLoader
        # Hyphenated script loaded through spec, no shell invocation.
        import importlib.util
        filename=ROOT/'scripts'/'render-public-cards.py'
        spec=importlib.util.spec_from_file_location('public_card_export',filename)
        if spec is None:
            module=SourceFileLoader('public_card_export',str(filename)).load_module()
        else:
            module=importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
        sheet=self.sample()
        with tempfile.TemporaryDirectory() as directory:
            output=Path(directory)/'cards'
            manifest=module.render_sheet(sheet,output,self.font_path,self.font_sha)
            self.assertEqual(len(manifest['pages']),len(sheet['frames']))
            self.assertTrue(all(p['independentOpticalScan']=='passed' for p in manifest['pages']))
            self.assertEqual(manifest['source'],'PUBLIC-BFQR1-only')
            self.assertTrue((output/'receipt.json').exists())
            with self.assertRaises(FileExistsError):
                module.render_sheet(sheet,output,self.font_path,self.font_sha)
            with self.assertRaises(ValueError):
                module.render_sheet(sheet,Path(directory)/'another',self.font_path,'0'*64)
