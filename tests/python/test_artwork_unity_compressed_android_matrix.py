"""Same-device Android compressed matrix contracts; mocks are not device evidence."""
from __future__ import annotations
import json, tempfile, unittest
from pathlib import Path
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[2]
import sys
sys.path[:0]=[str(ROOT),str(ROOT/'integrations/framerudiments')]
from tools.artwork_unity_compressed_android_matrix import run_android_matrix,validate_matrix_report,PROFILES,SCHEMA

SERIAL='do-not-persist-this-serial'


def receipt(profile,qualified=True,model='MockPhone',gpu='MockGPU'):
    vulkan=profile.startswith('android-vulkan')
    return {'status':'passed','apkSha256':'a'*64,'playerReportSha256':'b'*64,
            'result':{'graphicsApi':'Vulkan' if vulkan else 'OpenGLES3','formatId':'astc4x4' if vulkan else 'etc2rgba8',
                      'orientation':'bottom-up' if qualified else 'top-left','productionQualified':qualified,
                      'readbackMeanAbsoluteError':1.0,'readbackPsnrDb':45.0,'shaderMeanAbsoluteError':2.0,'shaderPsnrDb':42.0,
                      'graphicsDevice':gpu,'graphicsDeviceVersion':'mock-v1','operatingSystem':'Android 16','deviceModel':model}}


class Matrix(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
        install=self.root/'install';tools=self.root/'tools';install.mkdir();tools.mkdir();self.editor=install/'Unity';self.adb=tools/'adb';self.editor.touch();self.adb.touch();self.gpu=self.root/'gpu';self.ref=self.root/'ref';self.gpu.mkdir();self.ref.mkdir();self.out=self.root/'out'

    def test_both_profiles_run_in_order_on_same_selected_serial_without_persisting_it(self):
        with patch('tools.artwork_unity_compressed_android_matrix.select_physical_device',return_value=SERIAL) as select,\
             patch('tools.artwork_unity_compressed_android_matrix.run_android_qualification',side_effect=[receipt(PROFILES[0]),receipt(PROFILES[1])]) as run:
            result=run_android_matrix(self.editor,self.adb,self.gpu,self.ref,self.out,confirm_public=True)
        self.assertEqual(result['schema'],SCHEMA);self.assertEqual(result['status'],'passed');self.assertTrue(result['allProfilesExecuted']);self.assertTrue(result['allProfilesProductionQualified'])
        self.assertEqual([x['profile'] for x in result['profiles']],list(PROFILES));self.assertEqual(run.call_count,2);select.assert_called_once()
        for call,profile in zip(run.call_args_list,PROFILES):
            self.assertEqual(call.kwargs['profile'],profile);self.assertEqual(call.kwargs['device_serial'],SERIAL)
        self.assertNotIn(SERIAL,json.dumps(result));self.assertFalse(result['deviceSerialPersisted'])

    def test_measurement_can_complete_when_one_orientation_is_not_production_qualified(self):
        with patch('tools.artwork_unity_compressed_android_matrix.select_physical_device',return_value=SERIAL),\
             patch('tools.artwork_unity_compressed_android_matrix.run_android_qualification',side_effect=[receipt(PROFILES[0],False),receipt(PROFILES[1],True)]):
            result=run_android_matrix(self.editor,self.adb,self.gpu,self.ref,self.out,confirm_public=True)
        self.assertEqual(result['status'],'passed');self.assertEqual(result['productionQualifiedProfiles'],1);self.assertFalse(result['allProfilesProductionQualified'])

    def test_one_profile_failure_still_attempts_second_and_keeps_matrix_evidence(self):
        with patch('tools.artwork_unity_compressed_android_matrix.select_physical_device',return_value=SERIAL),\
             patch('tools.artwork_unity_compressed_android_matrix.run_android_qualification',side_effect=[ValueError('unsupported'),receipt(PROFILES[1])]) as run:
            with self.assertRaises(ValueError):run_android_matrix(self.editor,self.adb,self.gpu,self.ref,self.out,confirm_public=True)
        self.assertEqual(run.call_count,2);doc=json.loads((self.out/'matrix-result.json').read_text());self.assertEqual(doc['status'],'failed');self.assertEqual(doc['completedProfiles'],1);self.assertTrue((self.out/'failure.json').is_file())

    def test_validation_rejects_receipts_that_do_not_describe_same_device(self):
        report={'schema':SCHEMA,'status':'passed','samePhysicalDevice':True,'deviceSerialPersisted':False,'profileOrder':list(PROFILES),
                'profiles':[{'profile':PROFILES[0],'status':'passed','productionQualified':True,'deviceModel':'A','operatingSystem':'Android','graphicsDevice':'GPU'},
                            {'profile':PROFILES[1],'status':'passed','productionQualified':True,'deviceModel':'B','operatingSystem':'Android','graphicsDevice':'GPU'}],
                'completedProfiles':2,'allProfilesExecuted':True,'productionQualifiedProfiles':2,'allProfilesProductionQualified':True}
        with self.assertRaises(ValueError):validate_matrix_report(report)

    def test_consent_and_existing_output_fail_before_device_selection(self):
        with patch('tools.artwork_unity_compressed_android_matrix.select_physical_device') as select:
            with self.assertRaises(ValueError):run_android_matrix(self.editor,self.adb,self.gpu,self.ref,self.out)
            select.assert_not_called();self.assertFalse(self.out.exists())
        self.out.mkdir()
        with patch('tools.artwork_unity_compressed_android_matrix.select_physical_device') as select:
            with self.assertRaises(ValueError):run_android_matrix(self.editor,self.adb,self.gpu,self.ref,self.out,confirm_public=True)
            select.assert_not_called()

if __name__=='__main__':unittest.main()
