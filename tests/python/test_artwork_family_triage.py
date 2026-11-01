from __future__ import annotations
import json,tempfile,unittest
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from tools.artwork_family_triage import triage,SCHEMA

def fixture(path:Path):
    modes={}
    for mode in ('colour','greyscale','protan','deutan','tritan'):
        modes[mode]={'nearestDifferentDigestDistribution':{'min':.1,'p01':.2,'p05':.4,'median':.8},
                     'withinFamilyDistribution':{
                       'strong':{'min':.1,'p01':.22,'p05':.44,'median':.82},
                       'weak':{'min':.01,'p01':.04 if mode=='greyscale' else .1,'p05':.08 if mode=='greyscale' else .2,'median':.2}}}
    doc={'schema':'bytefables.artwork-distinctiveness.v1','status':'passed','manifestSha256':'a'*64,'assetCount':18,'uniqueDigests':3,
         'results':[{'size':16,'modes':modes},{'size':64,'modes':modes}]}
    path.write_text(json.dumps(doc))

class Triage(unittest.TestCase):
    def setUp(self):self.t=tempfile.TemporaryDirectory();self.addCleanup(self.t.cleanup);self.root=Path(self.t.name);self.report=self.root/'report.json';fixture(self.report)
    def test_ranks_relative_weak_family_first_and_writes_all_outputs(self):
        out=self.root/'out';r=triage(self.report,out);self.assertEqual(r['schema'],SCHEMA);self.assertEqual(r['families'][0]['family'],'weak')
        self.assertEqual(r['families'][0]['worstCase']['mode'],'greyscale');self.assertTrue((out/'family-ranking.csv').is_file());self.assertTrue((out/'REMEDIATION.md').is_file())
    def test_recommendations_surface_small_icon_and_non_colour_cues(self):
        r=triage(self.report,self.root/'out');text=' '.join(r['families'][0]['recommendations']).lower();self.assertIn('silhouette',text);self.assertIn('luminance',text)
    def test_existing_output_and_wrong_schema_fail(self):
        out=self.root/'out';out.mkdir()
        with self.assertRaises(ValueError):triage(self.report,out)
        bad=self.root/'bad.json';bad.write_text(json.dumps({'schema':'wrong','status':'passed'}))
        with self.assertRaises(ValueError):triage(bad,self.root/'out2')
    def test_no_absolute_pass_threshold_is_emitted(self):
        r=triage(self.report,self.root/'out');self.assertIn('relative',r['rankingMethod'].lower());self.assertNotIn('passedThreshold',r)

if __name__=='__main__':unittest.main()
