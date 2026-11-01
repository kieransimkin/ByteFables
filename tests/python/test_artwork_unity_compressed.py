"""Compressed-device runner/report contracts. Mock reports are not Unity/GPU evidence."""
from __future__ import annotations
import json, tempfile, unittest
from pathlib import Path
from unittest.mock import patch
import sys
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from tools.artwork_unity_compressed_device import (prepare_compressed_project,check_build_report,check_player_report,PROFILES,SCHEMA,BUILD_SCHEMA)

GPU_DOC={'formats':[{'id':'bc7'},{'id':'astc4x4'},{'id':'etc2rgba8'}],'sourceManifest':{'sha256':'c'*64},'nativeSize':16,'spriteCount':4,'levelCount':5}
SOURCE={'nativeSize':16,'spriteCount':4,'levelCount':5}

def fake_binding(gpu,ref):return GPU_DOC,SOURCE,'a'*64,'b'*64

def fake_stage(source,dest,**kw):dest.mkdir(parents=True);(dest/'artwork.bftextures').write_text('{}');return {'manifestSha256':'d'*64}

def build_result(plan):
 q=plan['request'];r={k:q[k] for k in ('runId','editorVersion','profile','target','graphicsApi','formatId','scriptingBackend','colourSpace','renderPipeline','gpuManifestSha256','referenceManifestSha256')}
 r.update(schema=BUILD_SCHEMA,status='passed',buildSucceeded=True,developmentBuild=False,errors=0,totalSize=123,elapsedMilliseconds=1,error=None);return r

def player_result(plan,orientation='bottom-up'):
 q=plan['request'];r={k:q[k] for k in ('runId','editorVersion','profile','graphicsApi','formatId','scriptingBackend','colourSpace','renderPipeline','gpuManifestSha256','referenceManifestSha256','sourceManifestSha256')}
 r.update(schema=SCHEMA,status='passed',runtimePlatform=q['runtimePlatform'],isEditor=False,playerExecuted=True,gpuExecuted=True,formatSupported=True,arraySupported=True,readbackExecuted=True,shaderExecuted=True,skipped=0,
          graphicsDevice='MOCK not evidence',graphicsDeviceVersion='MOCK',operatingSystem='MOCK',readbackComparisons=q['spriteCount']*q['levelCount'],shaderComparisons=min(16,q['spriteCount'])*q['levelCount']*3,
          orientationComparisons=2,orientation=orientation,productionQualified=orientation=='bottom-up',readbackMeanAbsoluteError=1.0,readbackPsnrDb=40.0,shaderMeanAbsoluteError=1.5,shaderPsnrDb=38.0,topLeftMeanAbsoluteError=20.0,bottomUpMeanAbsoluteError=1.0,readbackMaxAbsoluteError=5,shaderMaxAbsoluteError=7,elapsedMilliseconds=1,error=None)
 return r

class Preparation(unittest.TestCase):
 def setUp(self):
  self.t=tempfile.TemporaryDirectory();self.addCleanup(self.t.cleanup);self.root=Path(self.t.name);self.gpu=self.root/'gpu';self.ref=self.root/'ref';self.gpu.mkdir();self.ref.mkdir();(self.gpu/'x').write_text('x')
 def prep(self,profile='windows-d3d12-bc7'):
  with patch('tools.artwork_unity_compressed_device._source_binding',side_effect=fake_binding),patch('tools.artwork_unity_compressed_device.stage_unity_bundle',side_effect=fake_stage):
   return prepare_compressed_project(self.gpu,self.ref,self.root/'out',confirm_public=True,profile=profile)
 def test_desktop_profiles_are_explicit(self):
  p=self.prep();q=p['request'];self.assertEqual((q['formatId'],q['graphicsApi'],q['scriptingBackend'],q['colourSpace']),('bc7','Direct3D12','IL2CPP','Linear'));self.assertTrue(q['automatedDesktop'])
 def test_mobile_profiles_prepare_but_require_device_bridge(self):
  p=self.prep('android-vulkan-astc4x4');self.assertTrue(p['mobileDeviceBridgeRequired']);self.assertFalse(p['request']['automatedDesktop']);self.assertEqual(p['request']['formatId'],'astc4x4')
 def test_profile_matrix_has_desktop_and_mobile_api_contracts(self):
  self.assertEqual(PROFILES['macos-metal-astc4x4']['graphics'],'Metal');self.assertEqual(PROFILES['android-gles3-etc2rgba8']['format'],'etc2rgba8');self.assertEqual(PROFILES['ios-metal-astc4x4']['runtime'],'IPhonePlayer')
 def test_missing_consent_and_unknown_profile_fail(self):
  with self.assertRaises(ValueError):prepare_compressed_project(self.gpu,self.ref,self.root/'out')
  with self.assertRaises(ValueError):prepare_compressed_project(self.gpu,self.ref,self.root/'out2',confirm_public=True,profile='nope')

class Reports(unittest.TestCase):
 def setUp(self):
  self.t=tempfile.TemporaryDirectory();self.addCleanup(self.t.cleanup);self.root=Path(self.t.name);gpu=self.root/'gpu';ref=self.root/'ref';gpu.mkdir();ref.mkdir();(gpu/'x').write_text('x')
  with patch('tools.artwork_unity_compressed_device._source_binding',side_effect=fake_binding),patch('tools.artwork_unity_compressed_device.stage_unity_bundle',side_effect=fake_stage):self.plan=prepare_compressed_project(gpu,ref,self.root/'out',confirm_public=True,profile='linux-vulkan-bc7')
 def test_complete_mock_reports_validate_protocol_only(self):check_build_report(build_result(self.plan),self.plan['request']);check_player_report(player_result(self.plan),self.plan)
 def test_orientation_can_be_measured_without_false_production_qualification(self):check_player_report(player_result(self.plan,'top-left'),self.plan);r=player_result(self.plan,'top-left');self.assertFalse(r['productionQualified'])
 def test_production_flag_must_track_bottom_up_orientation(self):
  r=player_result(self.plan,'top-left');r['productionQualified']=True
  with self.assertRaises(ValueError):check_player_report(r,self.plan)
 def test_execution_capability_and_counts_fail_closed(self):
  for key in ('playerExecuted','gpuExecuted','formatSupported','arraySupported','readbackExecuted','shaderExecuted'):
   r=player_result(self.plan);r[key]=False
   with self.subTest(key=key),self.assertRaises(ValueError):check_player_report(r,self.plan)
  r=player_result(self.plan);r['readbackComparisons']-=1
  with self.assertRaises(ValueError):check_player_report(r,self.plan)

class SourceContracts(unittest.TestCase):
 def test_runtime_uses_actual_support_readback_and_no_rgba_fallback(self):
  s=(ROOT/'integrations/unity/com.bytefables.textures/Runtime/CompressedTextureDeviceQualification.cs').read_text()
  for token in ('CompressedTextureFormatSelector.IsSupported','AsyncGPUReadback.Request','TextureFormat.RGBA32','productionQualified = report.orientation == "bottom-up"','CompressedTextureArrayResidency'):
   self.assertIn(token,s)
 def test_build_is_il2cpp_linear_and_supports_metal_d3d_vulkan(self):
  s=(ROOT/'integrations/unity/com.bytefables.textures/Editor/CompressedTextureDeviceBuild.cs').read_text()
  for token in ('ScriptingImplementation.IL2CPP','ColorSpace.Linear','GraphicsDeviceType.Direct3D11','GraphicsDeviceType.Direct3D12','GraphicsDeviceType.Vulkan','GraphicsDeviceType.Metal','BuildTarget.StandaloneOSX'):
   self.assertIn(token,s)

if __name__=='__main__':unittest.main()
