"""Independent QR encoder and exported PNG reader tests, public fixtures only.

qrcode (Python) is a separate encoder; OpenCV is a separate optical scanner.
These test *specific* target conditions, not all QR scanner/devices/damage types.
"""
import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
try:
    import qrcode
    from qrcode import util, constants
except ImportError:
    qrcode = None
try:
    import cv2
    import numpy as np
    from PIL import Image
    from bytefables_framerudiments.renderers import MatrixRenderer
except ImportError:
    cv2 = None

class QrIndependentTests(unittest.TestCase):
    def test_iso_reference_grids_all_versions_ecc(self):
        if qrcode is None:
            self.skipTest('Optional independent Python qrcode encoder is not installed')
        cases = json.loads(subprocess.check_output(
            ['node', str(ROOT / 'scripts/qr-reference-cases.mjs')],
            cwd=ROOT, text=True, timeout=60))
        self.assertEqual(len(cases), 56)
        levels = dict(L=constants.ERROR_CORRECT_L, M=constants.ERROR_CORRECT_M,
                      Q=constants.ERROR_CORRECT_Q, H=constants.ERROR_CORRECT_H)
        for item in cases:
            with self.subTest(version=item['version'], ecc=item['ecc']):
                reference = qrcode.QRCode(version=item['version'],
                    error_correction=levels[item['ecc']], border=0, box_size=1, mask_pattern=0)
                reference.add_data(util.QRData(bytes.fromhex(item['byteHex']), mode=util.MODE_8BIT_BYTE),
                                   optimize=0)
                reference.make(fit=False)
                expected = bytes(int(v) for row in reference.modules for v in row)
                self.assertEqual(bytes.fromhex(item['modules']), expected)
                self.assertEqual(len(reference.modules), item['width'])

    def test_native_renderer_png_independent_opencv_decode(self):
        if cv2 is None:
            self.skipTest('Optional independent OpenCV and FrameRudiments adapter are not installed')
        from tempfile import TemporaryDirectory
        command = ['node', str(ROOT/'bin/bytefables.mjs'), 'qr-public', '--confirm-public',
                   '--public-hex', '000102030405060708090a0b0c0d0e0f',
                   '--namespace', 'danceflow', '--kind', 'node-id',
                   '--fragment-bytes', '48', '--ecc', 'Q', '--qr-mask', '0',
                   '--max-version', '12', '--include-layers', '--bounds', '0,0,480,480']
        card = json.loads(subprocess.check_output(command, cwd=ROOT, text=True, timeout=40))
        self.assertEqual(card['schema'], 'bytefables.public-qr-card.v1')
        with TemporaryDirectory() as d:
            for item in card['frames']:
                with self.subTest(index=item['index']):
                    self.assertEqual(item['layer']['renderer'], 'bytefables-matrix-v1')
                    qr = MatrixRenderer((480, 480), item['layer']['style']).render(None)
                    filename = str(Path(d) / f"frame-{item['index']}.png")
                    qr.save(filename,format='PNG')
                    exported = cv2.imread(filename, cv2.IMREAD_COLOR)
                    text, points, _ = cv2.QRCodeDetector().detectAndDecode(exported)
                    self.assertIsNotNone(points)
                    self.assertEqual(text, item['text'])

if __name__ == '__main__':
    unittest.main()
