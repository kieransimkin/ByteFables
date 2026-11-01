"""Artwork v2 candidate contracts. Machine screening is not human recognition evidence."""
from __future__ import annotations
import hashlib,json,tempfile,unittest
from pathlib import Path
import numpy as np

ROOT=Path(__file__).resolve().parents[2]
import sys
sys.path[:0]=[str(ROOT),str(ROOT/'integrations/framerudiments')]
from bytefables_framerudiments.artwork import ArtworkRenderer,BRIDGE
from bytefables_framerudiments.artwork_remediation import RemediationArtworkRenderer
from bytefables_framerudiments.artwork_remediation_v2 import RemediationArtworkRendererV2,PROFILE as REMEDIATION_V2
from bytefables_framerudiments.artwork_v2 import ArtworkRendererV2Candidate,PROFILE,TARGET_FAMILIES
from tools.artwork_v2_promotion import run_promotion,_digests,_style,_rgba
from tools.artwork_distinctiveness import MODES,_feature,_nearest,_percentiles

class Renderer(unittest.TestCase):
    def test_target_v2_is_deterministic_and_untouched_family_is_exact_v1(self):
        digest='12'*32
        for family in sorted(TARGET_FAMILIES):
            style={'bridge_version':BRIDGE,'digest_hex':digest,'style':family,'palette':'mono','complexity':4}
            a=ArtworkRendererV2Candidate((32,32),style).render(0);b=ArtworkRendererV2Candidate((32,32),style).render(0);base=ArtworkRenderer((32,32),style).render(0)
            try:self.assertEqual(a.tobytes(),b.tobytes());self.assertNotEqual(a.tobytes(),base.tobytes())
            finally:a.close();b.close();base.close()
        style={'bridge_version':BRIDGE,'digest_hex':digest,'style':'sigil','palette':'neon','complexity':5}
        a=ArtworkRendererV2Candidate((64,64),style).render(0);b=ArtworkRenderer((64,64),style).render(0)
        try:self.assertEqual(a.tobytes(),b.tobytes())
        finally:a.close();b.close()

    def test_heraldry_v2_fixes_candidate_v1_16px_p05_collapse(self):
        digests=_digests(64);items=[{'digestHex':d} for d in digests]
        old=[_rgba(RemediationArtworkRenderer((16,16),_style(d,'heraldry'))) for d in digests]
        new=[_rgba(RemediationArtworkRendererV2((16,16),_style(d,'heraldry'))) for d in digests]
        for mode in MODES:
            _,on=_nearest([_feature(x,mode) for x in old],items,False);_,nn=_nearest([_feature(x,mode) for x in new],items,False)
            oldp=_percentiles(on)['p05'];newp=_percentiles(nn)['p05']
            self.assertGreater(newp,0.0);self.assertGreaterEqual(newp,oldp)

    def test_small_promotion_run_is_versioned_and_never_auto_changes_v1(self):
        with tempfile.TemporaryDirectory() as t:
            out=Path(t)/'out';r=run_promotion(out,identities=32,sizes=(16,32),preview_size=32)
            self.assertEqual(r['candidateProfile'],PROFILE);self.assertTrue(r['unchangedFamilies']['byteExact']);self.assertEqual(len(r['families']),3)
            self.assertTrue((out/'PROMOTION.md').is_file())

    def test_golden_vectors(self):
        vectors=json.loads((ROOT/'tests/vectors/artwork-v2-candidate-v1.json').read_text())
        self.assertEqual(vectors['profile'],PROFILE);self.assertEqual(vectors['remediationProfile'],REMEDIATION_V2)
        for case in vectors['cases']:
            style={k:case[k] for k in ('bridge_version','digest_hex','style','palette','complexity')}
            image=ArtworkRendererV2Candidate((case['size'],case['size']),style).render(0)
            try:
                raw=image.tobytes();self.assertEqual(hashlib.sha256(raw).hexdigest(),case['rgbaSha256']);self.assertEqual(sum(1 for a in raw[3::4] if a),case['nonzeroAlphaPixels'])
            finally:image.close()

    def test_invalid_promotion_count_fails_before_output(self):
        with tempfile.TemporaryDirectory() as t:
            out=Path(t)/'out'
            with self.assertRaises(ValueError):run_promotion(out,identities=31)
            self.assertFalse(out.exists())

if __name__=='__main__':unittest.main()
