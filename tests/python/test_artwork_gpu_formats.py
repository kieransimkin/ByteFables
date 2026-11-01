"""GPU-block packaging contracts. Mock transcodes are NOT compression evidence."""
from __future__ import annotations
import json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[2]
import sys
sys.path[:0]=[str(ROOT),str(ROOT/'integrations/framerudiments'),str(ROOT/'tests/helpers')]
from artwork_unity_fixture import make_fixture
from tools.artwork_native_benchmark import _json,_sha
from tools.artwork_gpu_formats import export_gpu_bundle,verify_gpu_bundle,level_bytes,TARGETS


def fake_extract(_exe,_compressed,target,size,layers):
    levels=[]
    seed={'bc7':17,'astc':41,'etc-rgba':73}[target['ktxTarget']]
    for level in range(size.bit_length()):
        per=level_bytes(size>>level,1,target)
        levels.append(b''.join(bytes((seed+level*5+layer*11+i)%256 for i in range(per)) for layer in range(layers)))
    return tuple(levels)

class GpuBlocks(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
  lossless=make_fixture(self.root/'lossless')
  source=(lossless/'source-manifest.json').read_bytes();source_doc=json.loads(source)
  self.uastc=self.root/'uastc';(self.uastc/'banks').mkdir(parents=True)
  banks=[]
  for b in range(2):
   raw=b'UASTC-MOCK-'+bytes([b]);path=f'banks/bank-{b:03d}.uastc.ktx2';(self.uastc/path).write_bytes(raw)
   banks.append({'index':b,'layerCount':2,'sourceFile':f'banks/bank-{b:03d}.ktx2','sourceByteLength':3148,
                 'sourceSha256':'a'*64,'file':path,'byteLength':len(raw),'sha256':_sha(raw),
                 'compressionRatio':.5,'decodedLevels':[],'metrics':{}})
  manifest={'schema':'bytefables.ktx2-uastc-bundle.v1','profile':'bytefables.ktx2-uastc-zstd.v1','status':'passed',
            'publicOnly':True,'guarantee':'presentation-only','tool':{'name':'Khronos KTX-Software','version':'4.4.2'},
            'encoder':{},'qualityPolicy':{},'sourceTransport':{'file':'source-transport.json','byteLength':1,'sha256':'b'*64},
            'sourceManifest':{'file':'source-manifest.json','byteLength':len(source),'sha256':_sha(source)},'banks':banks,'totals':{}}
  (self.uastc/'source-manifest.json').write_bytes(source);(self.uastc/'source-transport.json').write_bytes(b'x')
  (self.uastc/'manifest.json').write_bytes(_json(manifest));self.manifest_sha=_sha((self.uastc/'manifest.json').read_bytes())
  self.ktx=self.root/'ktx';self.ktx.touch();self.source_doc=source_doc
 def mocks(self):
  return (patch('tools.artwork_gpu_formats.ktx_version',return_value='4.4.2'),
          patch('tools.artwork_gpu_formats.validate_uastc_manifest',side_effect=lambda x:x),
          patch('tools.artwork_gpu_formats.verify_uastc_bundle',return_value={'manifestSha256':self.manifest_sha}),
          patch('tools.artwork_gpu_formats._extract_target',side_effect=fake_extract))
 def run_export(self,out):
  a,b,c,d=self.mocks()
  with a,b,c,d:return export_gpu_bundle(self.uastc,out,ktx=self.ktx,confirm_public=True)
 def test_export_verify_all_three_targets_and_geometry(self):
  out=self.root/'gpu';doc=self.run_export(out)
  self.assertEqual([x['id'] for x in doc['formats']],list(TARGETS));self.assertTrue((out/'gpu.bfgpu').is_file())
  a,b,c,d=self.mocks()
  with a,b,c,d:result=verify_gpu_bundle(out,source_uastc=self.uastc,ktx=self.ktx)
  self.assertTrue(result['sourceRecomputed']);self.assertEqual(result['sprites'],4)
  for fmt in doc['formats']:
   for bank in fmt['banks']:
    for rec in bank['levels']:self.assertEqual(rec['byteLength'],level_bytes(rec['size'],bank['layerCount'],TARGETS[fmt['id']]))
 def test_tampered_block_fails(self):
  out=self.root/'gpu';self.run_export(out);p=next((out/'formats/bc7').glob('*.bin'));p.write_bytes(p.read_bytes()+b'x')
  with self.assertRaises(ValueError):verify_gpu_bundle(out)
 def test_existing_output_and_consent_fail_closed(self):
  out=self.root/'gpu';a,b,c,d=self.mocks()
  with a,b,c,d,self.assertRaises(ValueError):export_gpu_bundle(self.uastc,out,ktx=self.ktx)
  self.run_export(out)
  a,b,c,d=self.mocks()
  with a,b,c,d,self.assertRaises(ValueError):export_gpu_bundle(self.uastc,out,ktx=self.ktx,confirm_public=True)
 def test_all_targets_are_4x4_16_byte_blocks(self):
  for target in TARGETS.values():self.assertEqual((target['blockWidth'],target['blockHeight'],target['blockBytes']),(4,4,16))

class UnitySource(unittest.TestCase):
 def test_selector_has_explicit_support_checks_and_no_silent_rgba_fallback(self):
  s=(ROOT/'integrations/unity/com.bytefables.textures/Runtime/CompressedTextureArrayUpload.cs').read_text()
  for token in ('SystemInfo.SupportsTextureFormat','TextureFormat.BC7','TextureFormat.ASTC_4x4','TextureFormat.ETC2_RGBA8','allowNoCompressedFormat','Use Point or Trilinear filtering'):
   self.assertIn(token,s)
  self.assertIn('explicit RGBA8 resolved fallback',s)
 def test_upload_uses_raw_pixel_data_and_preserves_mips(self):
  s=(ROOT/'integrations/unity/com.bytefables.textures/Runtime/CompressedTextureArrayUpload.cs').read_text()
  for token in ('SetPixelData<byte>','updateMipmaps:false','No block flipping is attempted'):
   self.assertIn(token,s)
 def test_residency_is_one_format_lease_pinned_lru(self):
  s=(ROOT/'integrations/unity/com.bytefables.textures/Runtime/CompressedTextureArrayResidency.cs').read_text()
  for token in ('Compressed GPU budget is pinned by active leases','EvictOne','AcquireSprite','FormatId','TextureArrayUpload.Destroy','ManagedThreadId','creating Unity thread'):
   self.assertIn(token,s)
 def test_core_parser_pins_exact_khronos_target_names(self):
  s=(ROOT/'integrations/unity/com.bytefables.textures/Runtime/Core/GpuBlockTextureBundleData.cs').read_text()
  for token in ('ktxTarget=="bc7"','ktxTarget=="astc"','ktxTarget=="etc-rgba"'):
   self.assertIn(token,s)

if __name__=='__main__':unittest.main()
