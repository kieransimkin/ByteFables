"""External optical reader integration for BCR-2024-001 public-only test frames."""
import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'integrations'/'framerudiments'))
from bytefables_framerudiments.renderers import MatrixRenderer

class UrOpticalTests(unittest.TestCase):
    def test_module_qr_pngs_scan_as_exact_multipart_ur_and_restore(self):
        try:
            import cv2
            import numpy as np
        except ImportError:
            self.skipTest('OpenCV optical scanner optional outside qualified CI')
        # TS generates the UR and QR (not the Python qrcode module).
        js='''import {createUrBytesQrTestDeck} from './dist/index.js';
const payload=Uint8Array.from({length:128},(_,i)=>(i*13+1)&255);
const deck=await createUrBytesQrTestDeck(payload,{id:'urpublic',bounds:[0,0,640,640],
fragmentBytes:20,extraMixedFrames:8,maxVersion:14,ecc:'M'});
console.log(JSON.stringify(deck));'''
        raw=subprocess.check_output(['node','--input-type=module','-e',js],cwd=ROOT,text=True,timeout=30)
        deck=json.loads(raw)
        self.assertEqual(deck['schema'],'bytefables.ur-bytes-qr-test.v1')
        decoded=[]
        for frame in deck['frames']:
            im=MatrixRenderer((640,640),frame['layer']['style']).render(None)
            arr=np.array(im.convert('RGB'))[:,:,::-1].copy()
            text,_,_=cv2.QRCodeDetector().detectAndDecode(arr)
            self.assertEqual(text,frame['text'])
            decoded.append(text)
        result=subprocess.run(['node',str(ROOT/'bin/bytefables.mjs'),
            'ur-test-recover','--confirm-public'],input=json.dumps(decoded[::-1]),
            cwd=ROOT,text=True,capture_output=True,timeout=30)
        self.assertEqual(result.returncode,0,result.stderr)
        payload=json.loads(result.stdout)
        self.assertEqual(payload['bytesHex'],bytes((i*13+1)&255 for i in range(128)).hex())
        self.assertTrue(payload['testOnly'])
