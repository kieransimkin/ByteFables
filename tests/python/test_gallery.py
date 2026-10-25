"""PUBLIC example gallery uses FrameRudiments sources, not another effects engine."""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]

class GalleryTests(unittest.TestCase):
    def test_example_gallery_has_pinned_receipts_and_approved_assets(self):
        with tempfile.TemporaryDirectory() as d:
            dest=Path(d)/'public-gallery'
            subprocess.check_call([sys.executable,str(ROOT/'scripts/generate-public-gallery.py'),
                '--output',str(dest)],cwd=ROOT,timeout=60,stdout=subprocess.DEVNULL)
            report=json.loads((dest/'evidence.json').read_text())
            self.assertEqual(report['schema'],'bytefables.public-gallery-evidence.v1')
            self.assertEqual(len(report['artwork']),16)
            self.assertGreaterEqual(len(report['qr']),2)
            for q in report['qr']:
                self.assertTrue(q['text'].startswith('BFQR1:'))
                self.assertTrue((dest/q['name']).is_file())
            with self.assertRaises(subprocess.CalledProcessError):
                subprocess.check_call([sys.executable,str(ROOT/'scripts/generate-public-gallery.py'),
                    '--output',str(dest)],cwd=ROOT,timeout=60,
                    stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
