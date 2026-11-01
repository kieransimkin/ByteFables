"""UASTC transport protocol tests. Fake codec execution is NOT Basis quality evidence."""
from __future__ import annotations
import json, os, stat, sys, tempfile, unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT),str(ROOT/'integrations/framerudiments'),str(ROOT/'tests/helpers')]
from artwork_unity_fixture import make_fixture
from tools.artwork_ktx2_basis import (export_uastc_bundle,verify_uastc_bundle,validate_manifest,
    encode_command,ktx_version,QUALITY_POLICY,_quality,SCHEMA,PROFILE,KTX_VERSION)

FAKE='''#!/usr/bin/env python3
import os,shutil,struct,sys
args=sys.argv[1:]
if args==['--version']:
 print('ktx version: '+os.environ.get('FAKE_KTX_VERSION','4.4.2'));raise SystemExit(0)
cmd=args[0]
if cmd=='validate': raise SystemExit(0)
if cmd=='encode':
 src=args[-2];dst=args[-1];data=open(src,'rb').read()
 if os.environ.get('FAKE_NONDETERMINISTIC')=='1': data+=bytes([os.getpid()&255])
 os.makedirs(os.path.dirname(dst),exist_ok=True);open(dst,'wb').write(data);raise SystemExit(0)
if cmd=='extract':
 src=args[-2];out=args[-1];b=open(src,'rb').read();os.makedirs(out,exist_ok=True)
 width=struct.unpack_from('<I',b,20)[0];layers=struct.unpack_from('<I',b,32)[0];levels=struct.unpack_from('<I',b,40)[0]
 corrupt=os.environ.get('FAKE_CORRUPT')=='1'
 for level in range(levels):
  at,n,_=struct.unpack_from('<QQQ',b,80+level*24);side=width>>level;per=side*side*4;raw=b[at:at+n]
  for layer in range(layers):
   p=bytearray(raw[layer*per:(layer+1)*per])
   if corrupt and level==0 and layer==0:
    for i in range(min(256,len(p))): p[i]=255-p[i]
   open(os.path.join(out,f'output_level{level}_layer{layer}.raw'),'wb').write(p)
 raise SystemExit(0)
print('unsupported fake command',file=sys.stderr);raise SystemExit(3)
'''

class Base(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
  self.source=make_fixture(self.root/'source');self.out=self.root/'compressed';self.ktx=self.root/'ktx'
  self.ktx.write_text(FAKE);self.ktx.chmod(self.ktx.stat().st_mode|stat.S_IXUSR)

class ExportVerify(Base):
 def test_export_and_source_backed_verify(self):
  doc=export_uastc_bundle(self.source,self.out,ktx=self.ktx,confirm_public=True,verify_determinism=False)
  self.assertEqual((doc['schema'],doc['profile']),(SCHEMA,PROFILE));self.assertEqual(doc['tool']['version'],KTX_VERSION)
  self.assertEqual(len(doc['banks']),2);self.assertEqual(doc['totals']['metrics']['meanAbsoluteError'],0)
  self.assertEqual(doc['totals']['metrics']['psnrDb'],999.0)
  a=verify_uastc_bundle(self.out,ktx=self.ktx);self.assertFalse(a['sourceCompared'])
  b=verify_uastc_bundle(self.out,ktx=self.ktx,source_bundle=self.source);self.assertTrue(b['sourceCompared'])
 def test_manifest_and_inventory_tamper_fail(self):
  export_uastc_bundle(self.source,self.out,ktx=self.ktx,confirm_public=True,verify_determinism=False)
  m=json.loads((self.out/'manifest.json').read_text());m['encoder']['threads']=2;(self.out/'manifest.json').write_text(json.dumps(m))
  with self.assertRaises(ValueError):verify_uastc_bundle(self.out,ktx=self.ktx)
 def test_bank_tamper_fails_checksum(self):
  export_uastc_bundle(self.source,self.out,ktx=self.ktx,confirm_public=True,verify_determinism=False)
  p=self.out/'banks/bank-000.uastc.ktx2';p.write_bytes(p.read_bytes()+b'x')
  with self.assertRaises(ValueError):verify_uastc_bundle(self.out,ktx=self.ktx)
 def test_corrupt_transcode_fails_quality_or_decoded_hash(self):
  export_uastc_bundle(self.source,self.out,ktx=self.ktx,confirm_public=True,verify_determinism=False)
  old=os.environ.get('FAKE_CORRUPT');os.environ['FAKE_CORRUPT']='1'
  try:
   with self.assertRaises(ValueError):verify_uastc_bundle(self.out,ktx=self.ktx,source_bundle=self.source)
  finally:
   if old is None:os.environ.pop('FAKE_CORRUPT',None)
   else:os.environ['FAKE_CORRUPT']=old
 def test_consent_and_existing_output_fail_before_reuse(self):
  with self.assertRaises(ValueError):export_uastc_bundle(self.source,self.out,ktx=self.ktx)
  self.assertFalse(self.out.exists())
  export_uastc_bundle(self.source,self.out,ktx=self.ktx,confirm_public=True,verify_determinism=False)
  with self.assertRaises(ValueError):export_uastc_bundle(self.source,self.out,ktx=self.ktx,confirm_public=True)

class ToolProtocol(Base):
 def test_version_is_exact(self):
  self.assertEqual(ktx_version(self.ktx),KTX_VERSION)
  env=os.environ.copy();old=os.environ.get('FAKE_KTX_VERSION');os.environ['FAKE_KTX_VERSION']='4.4.0'
  try:
   with self.assertRaises(ValueError):ktx_version(self.ktx)
  finally:
   if old is None:os.environ.pop('FAKE_KTX_VERSION',None)
   else:os.environ['FAKE_KTX_VERSION']=old
 def test_command_pins_deterministic_uastc_rdo_and_zstd(self):
  c=encode_command(self.ktx,Path('in.ktx2'),Path('out.ktx2'));s=' '.join(c)
  for token in ['--codec uastc','--uastc-quality 4','--uastc-rdo','--uastc-rdo-l 0.5','--uastc-rdo-m','--threads 1','--zstd 18']:
   self.assertIn(token,s)
 def test_determinism_check_rejects_changing_encoder(self):
  old=os.environ.get('FAKE_NONDETERMINISTIC');os.environ['FAKE_NONDETERMINISTIC']='1'
  try:
   with self.assertRaises(ValueError):export_uastc_bundle(self.source,self.out,ktx=self.ktx,confirm_public=True)
  finally:
   if old is None:os.environ.pop('FAKE_NONDETERMINISTIC',None)
   else:os.environ['FAKE_NONDETERMINISTIC']=old
 def test_quality_policy_rejects_each_boundary(self):
  good={'sampleBytes':100,'pixelCount':25,'meanAbsoluteError':1.0,'maxAbsoluteError':5,'psnrDb':45.0,
   'alphaMeanAbsoluteError':1.0,'alphaMaxAbsoluteError':4,'alphaPsnrDb':45.0,'premultipliedViolations':0,
   'premultipliedViolationFraction':0.0,'maxPremultipliedOvershoot':0}
  _quality(good)
  cases=[('psnrDb',29.9),('meanAbsoluteError',8.1),('maxAbsoluteError',97),('alphaPsnrDb',33.9),
         ('alphaMeanAbsoluteError',6.1),('maxPremultipliedOvershoot',33),('premultipliedViolationFraction',.11)]
  for key,value in cases:
   bad=good.copy();bad[key]=value
   with self.subTest(key=key),self.assertRaises(ValueError):_quality(bad)

if __name__=='__main__':unittest.main()
