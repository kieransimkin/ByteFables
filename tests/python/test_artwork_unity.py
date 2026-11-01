"""Runnable Python staging/orchestration tests. These do NOT compile or run C#/Unity."""
from __future__ import annotations
import copy
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT),str(ROOT/'integrations/framerudiments'),str(ROOT/'tests/helpers')]
from artwork_unity_fixture import make_fixture
from tools.artwork_unity_stage import stage_unity_bundle, verify_unity_stage, DESCRIPTOR
from tools.artwork_unity_qualification import check_report, run_qualification
from tools.artwork_asset_bundle import AssetBundleError
from tools.artwork_native_benchmark import _json, _sha
from bytefables_framerudiments.ktx2_arrays import decode_ktx2, DFD, KVD


class Staging(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.source=make_fixture(self.root/'source');self.output=self.root/'staged'
    def stage(self): return stage_unity_bundle(self.source,self.output,confirm_public=True)
    def test_roundtrip_exact_bytes_identity_and_no_web_executables(self):
        result=self.stage();self.assertEqual(result['sprites'],4);self.assertFalse(result['unityExecuted'])
        self.assertEqual((self.output/'transport.json').read_bytes(),(self.source/'manifest.json').read_bytes())
        for p in (self.output/'banks').glob('*.ktx2'): self.assertEqual(p.read_bytes(),(self.source/'banks'/p.name).read_bytes())
        self.assertEqual({p.name for p in self.output.iterdir()},{DESCRIPTOR,'transport.json','source-manifest.json','banks'})
        self.assertEqual(verify_unity_stage(self.output),result)
    def test_explicit_public_consent_before_writes(self):
        with self.assertRaises(ValueError): stage_unity_bundle(self.source,self.output)
        self.assertFalse(self.output.exists())
    def test_never_overwrites_existing_output(self):
        self.stage();before=(self.output/DESCRIPTOR).read_bytes()
        with self.assertRaises(ValueError): self.stage()
        self.assertEqual(before,(self.output/DESCRIPTOR).read_bytes())
    def test_output_cannot_nest_in_source(self):
        with self.assertRaises(ValueError): stage_unity_bundle(self.source,self.source/'nested',confirm_public=True)
        self.assertFalse((self.source/'nested').exists())
    def test_bad_source_rejected_before_output(self):
        (self.source/'banks/bank-000.ktx2').write_bytes(b'bad')
        with self.assertRaises(ValueError): self.stage()
        self.assertFalse(self.output.exists())
    def test_budget_checked_before_output(self):
        with self.assertRaises(ValueError): stage_unity_bundle(self.source,self.output,confirm_public=True,max_payload_bytes=1)
        self.assertFalse(self.output.exists())
    def test_staged_transport_pin_changes_fail(self):
        self.stage();p=self.output/'transport.json';p.write_bytes(p.read_bytes()+b' ')
        with self.assertRaises(ValueError): verify_unity_stage(self.output)
    def test_rehashed_bank_still_must_match_source_mips(self):
        self.stage();p=self.output/'banks/bank-000.ktx2';raw=bytearray(p.read_bytes());raw[-4]^=1;p.write_bytes(raw)
        transport=json.loads((self.output/'transport.json').read_bytes());transport['banks'][0]['sha256']=_sha(bytes(raw));transport_bytes=_json(transport)
        (self.output/'transport.json').write_bytes(transport_bytes)
        descriptor=json.loads((self.output/DESCRIPTOR).read_bytes());descriptor['manifestSha256']=_sha(transport_bytes);(self.output/DESCRIPTOR).write_bytes(_json(descriptor))
        with self.assertRaises(ValueError):verify_unity_stage(self.output)
    def test_unknown_staging_files_fail_but_unity_meta_allowed(self):
        self.stage();(self.output/'transport.json.meta').write_text('fileFormatVersion: 2\n')
        verify_unity_stage(self.output)
        (self.output/'extra.txt').write_text('unexpected')
        with self.assertRaises(ValueError):verify_unity_stage(self.output)
    def test_symlinks_rejected(self):
        self.stage();p=self.output/'banks/bank-000.ktx2';p.unlink()
        try:p.symlink_to(self.source/'banks/bank-000.ktx2')
        except OSError as e:self.skipTest(str(e))
        with self.assertRaises(ValueError):verify_unity_stage(self.output)
    def test_copy_failure_leaves_no_import_descriptor(self):
        from tools.artwork_unity_stage import _Writer
        original=_Writer.write
        def fail(writer,name,raw):
            if name.startswith('banks/'):raise OSError('injected write failure')
            return original(writer,name,raw)
        with patch.object(_Writer,'write',fail),self.assertRaises(OSError):self.stage()
        self.assertFalse((self.output/DESCRIPTOR).exists());self.assertTrue((self.output/'failure.json').exists())
    def test_cli_stage_verify_and_error_exit(self):
        cli=[sys.executable,str(ROOT/'scripts/stage-artwork-unity.py')]
        for suffix in [['--confirm-public','stage','--bundle',str(self.source),'--output',str(self.output)],['--confirm-public','verify','--output',str(self.output)]]:
            p=subprocess.run(cli+suffix,capture_output=True,text=True);self.assertEqual(p.returncode,0,p.stderr);self.assertFalse(json.loads(p.stdout)['unityExecuted'])
        p=subprocess.run(cli+['verify','--output',str(self.output)],capture_output=True,text=True);self.assertNotEqual(p.returncode,0)
    def test_sentinel_has_asymmetric_rows_and_fractional_alpha(self):
        bank=decode_ktx2((self.source/'banks/bank-001.ktx2').read_bytes());raw=bank.levels[0][:16*16*4]
        self.assertNotEqual(raw[:64],raw[-64:]);self.assertIn(0,raw[3::4]);self.assertIn(255,raw[3::4])
        second=bank.levels[0][16*16*4:];self.assertTrue(any(0<a<255 for a in second[3::4]))


class QualificationGate(unittest.TestCase):
    def report(self):
        return {'schema':'bytefables.unity-qualification.v1','status':'passed','unityExecuted':True,'gpuExecuted':True,
                'syntheticSentinelsExecuted':True,'skipped':0,'editorVersion':'6000.0.62f1','manifestSha256':'a'*64,
                'sprites':4,'banks':2,'graphicsApi':'Vulkan','graphicsDevice':'test report fixture',
                'cpuComparisons':40,'gpuComparisons':40,'shaderComparisons':120,'overlapComparisons':3,
                'overlapByteTolerance':1,'elapsedMilliseconds':1}
    def check(self,r):check_report(r,'a'*64,'6000.0.62f1',4,2,5)
    def test_complete_report_contract(self):self.check(self.report())
    def test_partial_skipped_headless_and_wrong_hash_reports_fail(self):
        for key,value in [('status','failed'),('gpuExecuted',False),('unityExecuted',False),('syntheticSentinelsExecuted',False),('skipped',1),
                          ('graphicsApi','Null'),('editorVersion','different'),('manifestSha256','b'*64),('gpuComparisons',39),('shaderComparisons',119),('overlapByteTolerance',2)]:
            with self.subTest(key=key),self.assertRaises(ValueError):r=self.report();r[key]=value;self.check(r)
    def test_missing_editor_fails_without_success_artifact(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t)
            with self.assertRaises(ValueError):run_qualification(root/'no-editor',root/'no-source',root/'output',confirm_public=True)
            self.assertFalse((root/'output').exists())
    def test_process_exit_zero_without_unity_evidence_is_not_a_pass(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);source=make_fixture(root/'source');fake=root/'editor';fake.write_bytes(b'not an executable')
            with patch('subprocess.run',return_value=subprocess.CompletedProcess([],0)),self.assertRaises((ValueError,OSError)):
                run_qualification(fake,source,root/'output',confirm_public=True)
            self.assertFalse((root/'output/report.json').exists());self.assertTrue((root/'output/failure.json').exists())
    def test_wrong_editor_version_rejected(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);fake=root/'editor';fake.touch()
            with self.assertRaises(ValueError):run_qualification(fake,root/'source',root/'output',confirm_public=True,editor_version='latest')


class PackageSourceContract(unittest.TestCase):
    """Packaging/static invariants only; these are not C# compilation or GPU tests."""
    def test_descriptor_constants_match_existing_python_codec(self):
        import base64
        s=(ROOT/'integrations/unity/com.bytefables.textures/Runtime/Core/Ktx2ArrayData.cs').read_text()
        encoded=re.findall(r'FromBase64String\("([A-Za-z0-9+/=]+)"\)',s)
        self.assertEqual([base64.b64decode(x) for x in encoded],[DFD,KVD])
    def test_linked_dotnet_sources_are_real_core_files(self):
        import xml.etree.ElementTree as ET
        p=ROOT/'tests/dotnet/ByteFables.TextureContracts/ByteFables.TextureContracts.csproj'
        links=[x.attrib['Include'] for x in ET.parse(p).iter('Compile')]
        core_dir=(p.parent/Path(links[1]).parent).resolve()
        paths={x.name for x in core_dir.glob('*.cs')}
        required={'Checks.cs','StrictJson.cs','Ktx2ArrayData.cs','TextureBundleData.cs','TextureBundleDirectory.cs'}
        self.assertTrue(required.issubset(paths))
        self.assertIn('../../../integrations/unity/com.bytefables.textures/Runtime/Core/*.cs',links)
    def test_upload_and_shader_contract_is_explicit(self):
        p=ROOT/'integrations/unity/com.bytefables.textures'
        upload=(p/'Runtime/TextureArrayUpload.cs').read_text();shader=(p/'Shaders/PremultipliedArray.shader').read_text()
        self.assertIn('bottomUp: true',upload);self.assertIn('updateMipmaps: false',upload)
        self.assertIn('Blend One OneMinusSrcAlpha',shader);self.assertNotIn('Blend SrcAlpha',shader)
        self.assertNotIn('UnityEngine',(p/'Runtime/Core/Ktx2ArrayData.cs').read_text())
    def test_package_metadata_and_assembly_boundaries(self):
        p=ROOT/'integrations/unity/com.bytefables.textures';doc=json.loads((p/'package.json').read_text())
        self.assertEqual(doc['unity'],'6000.0');self.assertEqual(doc['name'],'com.bytefables.textures')
        core=json.loads((p/'Runtime/Core/ByteFables.Textures.Core.asmdef').read_text());self.assertTrue(core['noEngineReferences'])
        editor=json.loads((p/'Editor/ByteFables.Textures.Editor.asmdef').read_text());self.assertEqual(editor['includePlatforms'],['Editor'])

if __name__=='__main__':unittest.main()
