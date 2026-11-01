from __future__ import annotations
import unittest
import numpy as np
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from tools.artwork_distinctiveness import _feature,_nearest,_percentiles,_dhash,MODES

class DistinctivenessMath(unittest.TestCase):
 def rgba(self,r,g,b,a=255):
  x=np.zeros((16,16,4),dtype=np.float32);x[:,:,:]=[r/255,g/255,b/255,a/255];return x
 def test_identical_features_are_zero_distance(self):
  a=self.rgba(255,0,0);self.assertEqual(float(np.mean(np.abs(_feature(a,'colour')-_feature(a,'colour')))),0.0)
 def test_modes_are_deterministic_bounded(self):
  a=self.rgba(30,200,70,128)
  for mode in MODES:
   f=_feature(a,mode);self.assertTrue(np.isfinite(f).all());self.assertGreaterEqual(float(f.min()),0);self.assertLessEqual(float(f.max()),1)
 def test_nearest_excludes_same_digest_for_primary_pairs(self):
  items=[{'digestHex':'a'},{'digestHex':'a'},{'digestHex':'b'}];features=[np.array([0.]),np.array([.01]),np.array([.2])]
  different,nearest=_nearest(features,items,False);self.assertTrue(nearest);self.assertTrue(all(p['a']!=p['b'] for p in different))
  same,_=_nearest(features,items,True);self.assertEqual(len(same),1)
 def test_percentiles_monotonic(self):
  p=_percentiles([.1,.2,.3,.4]);self.assertLessEqual(p['min'],p['p01']);self.assertLessEqual(p['p01'],p['p05']);self.assertLessEqual(p['p05'],p['median'])
 def test_dhash_changes_for_asymmetric_pattern(self):
  a=self.rgba(0,0,0);b=a.copy();b[:,8:,:3]=1.0;b[:,:,3]=1.0;self.assertNotEqual(_dhash(a),_dhash(b))

if __name__=='__main__':unittest.main()
