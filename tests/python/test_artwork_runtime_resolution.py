"""Resolved runtime cache and lazy Unity source contracts. Fake KTX is not codec-quality evidence."""
from __future__ import annotations
import json, os, stat, sys, tempfile, unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT),str(ROOT/'integrations/framerudiments'),str(ROOT/'tests/helpers')]
from artwork_unity_fixture import make_fixture
from tools.artwork_ktx2_basis import export_uastc_bundle, _validate_ktx
from tools.artwork_runtime_resolve import (resolve_lossless_bundle,resolve_uastc_bundle,verify_runtime_bundle,
    SCHEMA,PROFILE,DESCRIPTOR_SCHEMA)

FAKE='''#!/usr/bin/env python3
import os,struct,sys
args=sys.argv[1:]
if args==['--version']:
 print('ktx version: 4.4.2');raise SystemExit(0)
if args[0]=='validate':
 if os.environ.get('FAKE_EXTRA_WARNING')=='1': print('warning-9999: unexpected warning')
 else:
  print('warning-7010: Custom key in Key/Value Data.')
  print('Custom key "org.bytefables.profile" found in Key/Value Data.')
 raise SystemExit(0)
if args[0]=='encode':
 src=args[-2];dst=args[-1];os.makedirs(os.path.dirname(dst),exist_ok=True);open(dst,'wb').write(open(src,'rb').read());raise SystemExit(0)
if args[0]=='extract':
 src=args[-2];out=args[-1];b=open(src,'rb').read();os.makedirs(out,exist_ok=True)
 width=struct.unpack_from('<I',b,20)[0];layers=struct.unpack_from('<I',b,32)[0];levels=struct.unpack_from('<I',b,40)[0]
 for level in range(levels):
  at,n,_=struct.unpack_from('<QQQ',b,80+level*24);side=width>>level;per=side*side*4;raw=b[at:at+n]
  for layer in range(layers): open(os.path.join(out,f'output_level{level}_layer{layer}.raw'),'wb').write(raw[layer*per:(layer+1)*per])
 raise SystemExit(0)
raise SystemExit(3)
'''

class Base(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
  self.lossless=make_fixture(self.root/'lossless');self.ktx=self.root/'ktx';self.ktx.write_text(FAKE);self.ktx.chmod(self.ktx.stat().st_mode|stat.S_IXUSR)

class Resolution(Base):
 def test_lossless_resolution_preserves_keys_but_has_new_manifest(self):
  out=self.root/'runtime';doc=resolve_lossless_bundle(self.lossless,out,confirm_public=True);result=verify_runtime_bundle(out)
  self.assertEqual((doc['schema'],doc['profile']),(SCHEMA,PROFILE));self.assertEqual(doc['sourceArtifact']['kind'],'lossless-ktx2')
  self.assertEqual(result['sprites'],4);self.assertTrue((out/'runtime.bfresolved').is_file())
  descriptor=json.loads((out/'runtime.bfresolved').read_text());self.assertEqual(descriptor['schema'],DESCRIPTOR_SCHEMA)
  source=json.loads((self.lossless/'source-manifest.json').read_text())
  self.assertEqual([s['spriteKey'] for s in doc['sprites']],[s['spriteKey'] for s in source['sprites']])
 def test_uastc_resolution_uses_qualified_decoded_bytes_and_preserves_keys(self):
  compressed=self.root/'compressed';export_uastc_bundle(self.lossless,compressed,ktx=self.ktx,confirm_public=True,verify_determinism=False)
  out=self.root/'runtime';doc=resolve_uastc_bundle(compressed,out,ktx=self.ktx,confirm_public=True);result=verify_runtime_bundle(out)
  self.assertEqual(doc['sourceArtifact']['kind'],'uastc-zstd');self.assertEqual(result['sourceKind'],'uastc-zstd')
  source=json.loads((self.lossless/'source-manifest.json').read_text());self.assertEqual([s['spriteKey'] for s in doc['sprites']],[s['spriteKey'] for s in source['sprites']])
 def test_tampered_bank_or_descriptor_is_rejected(self):
  out=self.root/'runtime';resolve_lossless_bundle(self.lossless,out,confirm_public=True)
  p=out/'banks/bank-000.ktx2';p.write_bytes(p.read_bytes()+b'x')
  with self.assertRaises(ValueError):verify_runtime_bundle(out)
 def test_consent_and_existing_outputs_fail_closed(self):
  out=self.root/'runtime'
  with self.assertRaises(ValueError):resolve_lossless_bundle(self.lossless,out)
  self.assertFalse(out.exists());resolve_lossless_bundle(self.lossless,out,confirm_public=True)
  with self.assertRaises(ValueError):resolve_lossless_bundle(self.lossless,out,confirm_public=True)

class KtxValidationWarning(Base):
 def test_only_known_custom_profile_warning_is_allowed(self):
  bank=self.lossless/'banks/bank-000.ktx2';_validate_ktx(self.ktx,bank)
  old=os.environ.get('FAKE_EXTRA_WARNING');os.environ['FAKE_EXTRA_WARNING']='1'
  try:
   with self.assertRaises(ValueError):_validate_ktx(self.ktx,bank)
  finally:
   if old is None:os.environ.pop('FAKE_EXTRA_WARNING',None)
   else:os.environ['FAKE_EXTRA_WARNING']=old

class UnityLazySource(unittest.TestCase):
 def test_core_metadata_open_and_cpu_cache_are_bank_lazy(self):
  data=(ROOT/'integrations/unity/com.bytefables.textures/Runtime/Core/LazyTextureBundleData.cs').read_text()
  cache=(ROOT/'integrations/unity/com.bytefables.textures/Runtime/Core/TextureCpuResidency.cs').read_text()
  self.assertIn('KTX2 bank bytes are not read until LoadBank is called',data)
  self.assertIn('public Ktx2ArrayData LoadBank',data);self.assertIn('Task.Run(()=>source.LoadBank(bankIndex))',cache)
  self.assertIn('Dictionary<int,Task<Ktx2ArrayData>> loading',cache);self.assertIn('CPU residency budget is pinned by active leases',cache)
  self.assertIn('WaitWithCancellation',cache);self.assertIn('PrefetchAsync',cache)
 def test_gpu_cache_separates_cpu_and_vram_budgets(self):
  source=(ROOT/'integrations/unity/com.bytefables.textures/Runtime/LazyTextureArrayResidency.cs').read_text()
  for token in ('TextureCpuResidency','gpuBudget','AcquireBank','AcquireSprite','PrefetchCpuAsync','PrefetchGpu','SetBudgets','ManagedThreadId','TextureArrayUpload.Create'):
   self.assertIn(token,source)
  self.assertNotIn('UnityWebRequest',source);self.assertNotIn('HttpClient',source)

if __name__=='__main__':unittest.main()
