"""Candidate family experiments are screening only; they never change production artwork."""
from __future__ import annotations
import json,sys,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT),str(ROOT/'integrations/framerudiments')]
from bytefables_framerudiments.artwork import ArtworkRenderer,BRIDGE
from bytefables_framerudiments.artwork_remediation import RemediationArtworkRenderer,SUPPORTED_FAMILIES,PROFILE
from tools.artwork_family_experiments import run_experiments,_select_families,SCHEMA

STYLE={'bridge_version':BRIDGE,'digest_hex':'12'*32,'style':'mandala','palette':'mono','complexity':4}

class Renderer(unittest.TestCase):
 def test_target_candidate_is_deterministic_nonblank_and_different(self):
  for family in sorted(SUPPORTED_FAMILIES):
   style={**STYLE,'style':family};a=RemediationArtworkRenderer((32,32),style).render(0);b=RemediationArtworkRenderer((32,32),style).render(0);base=ArtworkRenderer((32,32),style).render(0)
   try:
    self.assertEqual(a.tobytes(),b.tobytes());self.assertNotEqual(a.tobytes(),base.tobytes());self.assertGreater(max(a.getchannel('A').getdata()),0)
   finally:a.close();b.close();base.close()
 def test_nontarget_family_delegates_exactly(self):
  style={**STYLE,'style':'sigil'};a=RemediationArtworkRenderer((32,32),style).render(0);b=ArtworkRenderer((32,32),style).render(0)
  try:self.assertEqual(a.tobytes(),b.tobytes())
  finally:a.close();b.close()

class Experiment(unittest.TestCase):
 def test_report_is_bounded_and_never_claims_promotion(self):
  with tempfile.TemporaryDirectory() as t:
   out=Path(t)/'out';r=run_experiments(out,families=['mandala'],identities=16,sizes=(16,32),preview_size=32)
   self.assertEqual(r['schema'],SCHEMA);self.assertEqual(r['candidateProfile'],PROFILE);self.assertEqual(len(r['families']),1)
   s=r['families'][0]['summary'];self.assertIn('promising',s);self.assertTrue((out/'REVIEW.md').is_file());self.assertTrue((out/'mandala-preview.png').is_file())
 def test_triage_order_selects_supported_families_only(self):
  with tempfile.TemporaryDirectory() as t:
   p=Path(t)/'triage.json';p.write_text(json.dumps({'schema':'bytefables.artwork-family-triage.v1','status':'passed','families':[{'family':'mandala'},{'family':'sigil'},{'family':'heraldry'}]}))
   self.assertEqual(_select_families(None,p),['mandala','heraldry'])
 def test_invalid_counts_and_families_fail_before_output(self):
  with tempfile.TemporaryDirectory() as t:
   root=Path(t)
   for kwargs in ({'identities':15},{'identities':257},{'families':['sigil']},{'sizes':(15,)}):
    with self.subTest(kwargs=kwargs),self.assertRaises(ValueError):run_experiments(root/f"x-{len(str(kwargs))}",**kwargs)

if __name__=='__main__':unittest.main()
