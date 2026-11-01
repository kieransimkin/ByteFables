"""Android compressed-device protocol/source contracts; mocks are not device evidence."""
from __future__ import annotations
import tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import sys
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from tools.artwork_unity_compressed_android import (select_physical_device,check_build_report,check_player_report,PACKAGE_ID,REMOTE_REPORT,BUILD_SCHEMA,PLAYER_SCHEMA)

class FakePlan:
 @staticmethod
 def make(profile='android-vulkan-astc4x4'):
  vulkan=profile.startswith('android-vulkan');return {'request':{'runId':'a'*32,'editorVersion':'6000.0.62f1','profile':profile,'target':'Android','runtimePlatform':'Android','graphicsApi':'Vulkan' if vulkan else 'OpenGLES3','formatId':'astc4x4' if vulkan else 'etc2rgba8','scriptingBackend':'IL2CPP','colourSpace':'Linear','renderPipeline':'BuiltIn','gpuManifestSha256':'b'*64,'referenceManifestSha256':'c'*64,'sourceManifestSha256':'d'*64,'spriteCount':4,'levelCount':5}}

def build(plan):
 q=plan['request'];r={k:q[k] for k in ('runId','editorVersion','profile','target','graphicsApi','formatId','scriptingBackend','colourSpace','renderPipeline','gpuManifestSha256','referenceManifestSha256')};r.update(schema=BUILD_SCHEMA,status='passed',packageId=PACKAGE_ID,architecture='ARM64',buildSucceeded=True,developmentBuild=False,errors=0,totalSize=123,elapsedMilliseconds=1);return r

def player(plan,orientation='bottom-up'):
 q=plan['request'];r={k:q[k] for k in ('runId','editorVersion','profile','graphicsApi','formatId','gpuManifestSha256','referenceManifestSha256','sourceManifestSha256')};r.update(schema=PLAYER_SCHEMA,status='passed',runtimePlatform='Android',packageId=PACKAGE_ID,isEditor=False,scriptingBackend='IL2CPP',colourSpace='Linear',renderPipeline='BuiltIn',playerExecuted=True,gpuExecuted=True,formatSupported=True,arraySupported=True,readbackExecuted=True,shaderExecuted=True,skipped=0,readbackComparisons=20,shaderComparisons=60,orientationComparisons=2,orientation=orientation,productionQualified=orientation=='bottom-up',readbackMeanAbsoluteError=1.0,readbackPsnrDb=40.0,shaderMeanAbsoluteError=1.2,shaderPsnrDb=39.0,topLeftMeanAbsoluteError=20.0,bottomUpMeanAbsoluteError=1.0,graphicsDevice='GPU',graphicsDeviceVersion='driver',operatingSystem='Android',deviceModel='physical phone');return r

class Reports(unittest.TestCase):
 def test_complete_android_reports_validate(self):
  p=FakePlan.make();check_build_report(build(p),p['request']);check_player_report(player(p),p)
 def test_orientation_does_not_false_promote(self):
  p=FakePlan.make('android-gles3-etc2rgba8');check_player_report(player(p,'top-left'),p);self.assertFalse(player(p,'top-left')['productionQualified'])
 def test_counts_capabilities_and_package_fail_closed(self):
  p=FakePlan.make()
  for key in ('playerExecuted','gpuExecuted','formatSupported','arraySupported','readbackExecuted','shaderExecuted'):
   r=player(p);r[key]=False
   with self.subTest(key=key),self.assertRaises(ValueError):check_player_report(r,p)
  r=player(p);r['packageId']='other'
  with self.assertRaises(ValueError):check_player_report(r,p)

class AdbSelection(unittest.TestCase):
 def test_exactly_one_physical_device_and_serial_not_in_remote_path(self):
  self.assertNotIn('serial',REMOTE_REPORT.lower());self.assertIn(PACKAGE_ID,REMOTE_REPORT)
  fake=type('R',(),{'stdout':'List of devices attached\nABC\tdevice product:x model:phone\n','stderr':'','returncode':0})
  props=[fake,type('R',(),{'stdout':'\n','stderr':'','returncode':0}),type('R',(),{'stdout':'\n','stderr':'','returncode':0})]
  with tempfile.TemporaryDirectory() as t:
   adb=Path(t)/'adb';adb.touch()
   with patch('tools.artwork_unity_compressed_android._adb',side_effect=props):self.assertEqual(select_physical_device(adb),'ABC')
 def test_emulator_rejected(self):
  devices=type('R',(),{'stdout':'List of devices attached\nemu\tdevice model:sdk\n','stderr':'','returncode':0})
  qemu=type('R',(),{'stdout':'1\n','stderr':'','returncode':0})
  with tempfile.TemporaryDirectory() as t:
   adb=Path(t)/'adb';adb.touch()
   with patch('tools.artwork_unity_compressed_android._adb',side_effect=[devices,qemu,qemu]),self.assertRaises(ValueError):select_physical_device(adb)

class SourceContracts(unittest.TestCase):
 def test_android_build_pins_il2cpp_arm64_graphics_and_imported_bytes(self):
  s=(ROOT/'integrations/unity/com.bytefables.textures/Editor/CompressedTextureAndroidBuild.cs').read_text()
  for token in ('NamedBuildTarget.Android','ScriptingImplementation.IL2CPP','AndroidArchitecture.ARM64','SetGraphicsAPIs(BuildTarget.Android','GraphicsDeviceType.Vulkan','GraphicsDeviceType.OpenGLES3','PackageId','TextAsset','gpu-manifest.bytes'):
   self.assertIn(token,s)
 def test_runtime_uses_physical_player_path_and_persistent_adb_report(self):
  s=(ROOT/'integrations/unity/com.bytefables.textures/Runtime/CompressedTextureAndroidQualification.cs').read_text()
  for token in ('RuntimePlatform.Android','Application.persistentDataPath','CompressedTextureFormatSelector.IsSupported','AsyncGPUReadback.Request','productionQualified=report.orientation=="bottom-up"'):
   self.assertIn(token,s)
  self.assertNotIn('deviceUniqueIdentifier',s)

if __name__=='__main__':unittest.main()
