"""Advanced Unity IL2CPP/Linear + graph qualification contract tests.

Mocked process reports exercise the runner protocol only; they are never Unity or GPU evidence.
"""
from __future__ import annotations
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT/'integrations/framerudiments'), str(ROOT/'tests/helpers')]
from artwork_unity_fixture import make_fixture
from tools.artwork_native_benchmark import _json, _sha
from tools.artwork_unity_advanced import (
    prepare_advanced_project, run_advanced_qualification,
    check_advanced_build_report, check_advanced_player_report,
    PROFILES, SCHEMA, BUILD_SCHEMA, DEFAULT_GRAPH_COUNTS,
)


def build_result(plan):
    q = plan['request']
    result = {k:q[k] for k in ('runId','editorVersion','profile','manifestSha256','sentinelManifestSha256',
        'graphicsApi','scriptingBackend','colourSpace','renderPipeline','target')}
    result.update(schema=BUILD_SCHEMA,status='passed',elapsedMilliseconds=1,developmentBuild=False,
                  buildSucceeded=True,errors=0,totalSize=4,error=None)
    return result


def graph_result(plan, count):
    src=plan['source']; cols=math.ceil(count**0.5); rows=(count+cols-1)//cols
    mip=0; tile=src['nativeSize']
    while mip+1 < src['levelsPerSprite'] and (cols*tile>2048 or rows*tile>2048):
        mip+=1;tile=src['nativeSize']>>mip
    digest='a'*64
    return dict(instances=count,uniqueSprites=min(count,src['sprites']),banks=src['banks'],drawCalls=max(1,src['banks']),
                mip=mip,width=cols*tile,height=rows*tile,pixelsCompared=cols*tile*rows*tile,
                submitMicroseconds=1,readbackMicroseconds=1,totalMicroseconds=2,exactPixels=True,
                expectedSha256=digest,actualSha256=digest)


def player_result(plan):
    q=plan['request'];src=plan['source'];probe=plan['sentinel']
    comparisons=src['sprites']*src['levelsPerSprite']+probe['sprites']*probe['levelsPerSprite']
    result={k:q[k] for k in ('runId','editorVersion','profile','manifestSha256','sentinelManifestSha256',
        'graphicsApi','scriptingBackend','colourSpace','renderPipeline')}
    result.update(schema=SCHEMA,status='passed',elapsedMilliseconds=2,error=None,isEditor=False,
        runtimePlatform=q['runtimePlatform'],graphicsDevice='MOCK fixture, NOT GPU evidence',graphicsDeviceVersion='MOCK',
        operatingSystem='MOCK',playerExecuted=True,gpuExecuted=True,serializedAssetsExecuted=True,
        syntheticSentinelsExecuted=True,disposalExecuted=True,graphExecuted=True,skipped=0,banks=src['banks'],sprites=src['sprites'],
        cpuComparisons=comparisons,gpuComparisons=comparisons,shaderComparisons=comparisons*3,
        bindingComparisons=src['sprites']+probe['sprites'],overlapComparisons=3,overlapByteTolerance=1,
        graphResults=[graph_result(plan,n) for n in q['graphCounts']])
    return result


class FixtureBase(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name);self.source=make_fixture(self.root/'source');self.output=self.root/'out'
    def prepare(self,**kw):
        return prepare_advanced_project(self.source,self.output,confirm_public=True,**kw)


class Preparation(FixtureBase):
    def test_default_is_explicit_il2cpp_linear_built_in_with_1k_10k_graphs(self):
        p=self.prepare();q=p['request']
        self.assertEqual(q['profile'],'windows-d3d11-il2cpp-linear');self.assertEqual(q['scriptingBackend'],'IL2CPP')
        self.assertEqual(q['colourSpace'],'Linear');self.assertEqual(q['renderPipeline'],'BuiltIn')
        self.assertEqual(q['graphCounts'],[1000,10000]);self.assertFalse(p['playerExecuted']);self.assertFalse(p['graphExecuted'])
        self.assertFalse((self.output/'report.json').exists())
    def test_linux_profile_is_native_vulkan_il2cpp_linear(self):
        q=self.prepare(profile='linux-vulkan-il2cpp-linear')['request']
        self.assertEqual((q['target'],q['runtimePlatform'],q['graphicsApi']),('StandaloneLinux64','LinuxPlayer','Vulkan'))
        self.assertEqual((q['scriptingBackend'],q['colourSpace']),('IL2CPP','Linear'))
    def test_windows_d3d12_profile_is_explicit(self):
        q=self.prepare(profile='windows-d3d12-il2cpp-linear')['request']
        self.assertEqual((q['target'],q['runtimePlatform'],q['graphicsApi']),('StandaloneWindows64','WindowsPlayer','Direct3D12'))
        self.assertEqual(PROFILES['windows-d3d12-il2cpp-linear']['launch'],'-force-d3d12')
    def test_custom_graph_counts_are_bounded_unique_and_sorted(self):
        self.assertEqual(self.prepare(graph_counts=[1,256,10000])['request']['graphCounts'],[1,256,10000])
        for counts in ([],[0],[10001],[100,10],[10,10],[1,2,3,4],[True]):
            with self.subTest(counts=counts),self.assertRaises(ValueError):
                prepare_advanced_project(self.source,self.root/f'bad-{len(str(counts))}',confirm_public=True,graph_counts=counts)
    def test_invalid_profile_version_or_missing_consent_precede_writes(self):
        with self.assertRaises(ValueError):prepare_advanced_project(self.source,self.output)
        self.assertFalse(self.output.exists())
        for opts in ({'profile':'urp'},{'editor_version':'latest'},{'editor_version':None}):
            with self.assertRaises(ValueError):self.prepare(**opts)
        self.assertFalse(self.output.exists())
    def test_embeds_package_and_keeps_streaming_reference_bytes_identical(self):
        self.prepare();project=self.output/'project';pkg=project/'Packages/com.bytefables.textures'
        for f in ('Runtime/TextureAdvancedQualification.cs','Runtime/TextureGraphBenchmark.cs','Editor/TextureAdvancedBuild.cs','Shaders/PremultipliedArrayInstanced.shader'):
            self.assertTrue((pkg/f).is_file(),f)
        for name in ('ByteFablesFixture','ByteFablesSentinel'):
            a=project/'Assets'/name;b=project/'Assets/StreamingAssets'/name
            for path in a.rglob('*'):
                if path.is_file():self.assertEqual(path.read_bytes(),(b/path.relative_to(a)).read_bytes())
    def test_corrupt_source_never_publishes_plan_or_success(self):
        (self.source/'banks/bank-000.ktx2').write_bytes(b'corrupt')
        with self.assertRaises(ValueError):self.prepare()
        self.assertFalse((self.output/'plan.json').exists());self.assertFalse((self.output/'report.json').exists())
        self.assertTrue((self.output/'failure.json').exists())
    def test_cli_prepare_never_needs_unity(self):
        cmd=[sys.executable,str(ROOT/'scripts/qualify-artwork-unity-advanced.py'),'--confirm-public','--prepare-only',
             '--bundle',str(self.source),'--output',str(self.output),'--profile','linux-vulkan-il2cpp-linear']
        p=subprocess.run(cmd,capture_output=True,text=True);self.assertEqual(p.returncode,0,p.stderr)
        self.assertEqual(json.loads(p.stdout)['status'],'prepared')


class ReceiptValidation(FixtureBase):
    def setUp(self):super().setUp();self.plan=self.prepare(profile='linux-vulkan-il2cpp-linear')
    def test_complete_mock_reports_satisfy_only_report_validators(self):
        check_advanced_build_report(build_result(self.plan),self.plan['request'])
        check_advanced_player_report(player_result(self.plan),self.plan)
    def test_profile_backend_colour_and_pipeline_are_pinned(self):
        for key in ('profile','graphicsApi','scriptingBackend','colourSpace','renderPipeline','runId','manifestSha256','sentinelManifestSha256'):
            r=player_result(self.plan);r[key]='other'
            with self.subTest(key=key),self.assertRaises(ValueError):check_advanced_player_report(r,self.plan)
    def test_missing_execution_flags_or_skips_fail(self):
        for key in ('playerExecuted','gpuExecuted','serializedAssetsExecuted','syntheticSentinelsExecuted','disposalExecuted','graphExecuted'):
            r=player_result(self.plan);r[key]=False
            with self.subTest(key=key),self.assertRaises(ValueError):check_advanced_player_report(r,self.plan)
        r=player_result(self.plan);r['skipped']=1
        with self.assertRaises(ValueError):check_advanced_player_report(r,self.plan)
    def test_graph_geometry_hash_and_exactness_are_strict(self):
        mutations=[('exactPixels',False),('actualSha256','b'*64),('mip',4),('width',1),('pixelsCompared',1),('drawCalls',0),('totalMicroseconds',-1)]
        for key,value in mutations:
            r=player_result(self.plan);r['graphResults'][0][key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):check_advanced_player_report(r,self.plan)
    def test_graph_result_inventory_and_counts_are_strict(self):
        r=player_result(self.plan);r['graphResults'].pop()
        with self.assertRaises(ValueError):check_advanced_player_report(r,self.plan)
        r=player_result(self.plan);r['graphResults'][0]['instances']=999
        with self.assertRaises(ValueError):check_advanced_player_report(r,self.plan)
    def test_base_comparison_counts_remain_exact(self):
        for key in ('banks','sprites','cpuComparisons','gpuComparisons','shaderComparisons','bindingComparisons','overlapComparisons','overlapByteTolerance'):
            r=player_result(self.plan);r[key]=r[key]+1
            with self.subTest(key=key),self.assertRaises(ValueError):check_advanced_player_report(r,self.plan)
    def test_build_must_be_nondevelopment_success(self):
        for key,value in [('target','wrong'),('buildSucceeded',False),('developmentBuild',True),('errors',1),('totalSize',0)]:
            r=build_result(self.plan);r[key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):check_advanced_build_report(r,self.plan['request'])


class RunnerProtocol(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
        self.source=make_fixture(self.root/'source');self.output=self.root/'out';install=self.root/'install';install.mkdir()
        self.editor=install/'Unity';self.editor.touch()
    def fake_execution(self,command,env,log,timeout):
        log.touch();plan=json.loads((self.output/'plan.json').read_bytes())
        if 'BYTEFABLES_ADVANCED_REQUEST' in env:
            exe=Path(plan['request']['buildPath']);exe.parent.mkdir();exe.write_bytes(b'MOCK')
            (self.output/'build-result.json').write_bytes(_json(build_result(plan)))
        else:(self.output/'player-result.json').write_bytes(_json(player_result(plan)))
    def run_qual(self,**kw):
        return run_advanced_qualification(self.editor,self.source,self.output,confirm_public=True,
            profile='linux-vulkan-il2cpp-linear',**kw)
    def test_mock_protocol_binds_build_player_and_artifact(self):
        with patch('platform.system',return_value='Linux'),patch('tools.artwork_unity_advanced._execute',side_effect=self.fake_execution) as ex:
            receipt=self.run_qual()
        self.assertEqual(ex.call_count,2);self.assertEqual(receipt['status'],'passed');self.assertTrue(receipt['graphExecuted'])
        self.assertIn('ByteFables.Textures.Editor.TextureAdvancedBuild.RunFromCommandLine',ex.call_args_list[0].args[0])
        self.assertIn('-force-vulkan',ex.call_args_list[1].args[0]);self.assertNotIn('-nographics',ex.call_args_list[1].args[0])
        self.assertEqual(receipt['buildReportSha256'],_sha((self.output/'build-result.json').read_bytes()))
    def test_zero_exit_without_reports_is_not_pass(self):
        with patch('platform.system',return_value='Linux'),patch('tools.artwork_unity_advanced._execute'),self.assertRaises(ValueError):self.run_qual()
        self.assertTrue((self.output/'failure.json').exists());self.assertFalse((self.output/'report.json').exists())
    def test_changed_player_binary_after_execution_is_rejected(self):
        def changed(*args):
            self.fake_execution(*args)
            if 'BYTEFABLES_ADVANCED_REPORT' in args[1]:
                (self.output/'player/ByteFablesAdvanced.x86_64').write_bytes(b'changed')
        with patch('platform.system',return_value='Linux'),patch('tools.artwork_unity_advanced._execute',side_effect=changed),self.assertRaises(ValueError):self.run_qual()
        self.assertFalse((self.output/'report.json').exists())
    def test_wrong_host_missing_editor_and_invalid_timeouts_precede_output(self):
        with patch('platform.system',return_value='Windows'),self.assertRaises(ValueError):self.run_qual()
        with patch('platform.system',return_value='Linux'),self.assertRaises(ValueError):self.run_qual(build_timeout=True)
        self.editor.unlink()
        with patch('platform.system',return_value='Linux'),self.assertRaises(ValueError):self.run_qual()
        self.assertFalse(self.output.exists())


class SourceInvariants(unittest.TestCase):
    def test_advanced_build_explicitly_sets_il2cpp_linear_and_built_in(self):
        s=(ROOT/'integrations/unity/com.bytefables.textures/Editor/TextureAdvancedBuild.cs').read_text()
        for token in ('ScriptingImplementation.IL2CPP','ColorSpace.Linear','GetScriptingBackend','defaultRenderPipeline = null','BuildOptions.None','GraphicsDeviceType.Direct3D12'):
            self.assertIn(token,s)
        self.assertNotIn('ScriptingImplementation.Mono2x',s)
    def test_player_requires_compile_time_il2cpp_and_runtime_linear(self):
        s=(ROOT/'integrations/unity/com.bytefables.textures/Runtime/TextureAdvancedQualification.cs').read_text()
        for token in ('#if ENABLE_IL2CPP','report.scriptingBackend == "IL2CPP"','report.colourSpace == "Linear"','SystemInfo.supportsInstancing'):
            self.assertIn(token,s)
    def test_graph_shader_is_instanced_array_sampling_with_premultiplied_blend(self):
        s=(ROOT/'integrations/unity/com.bytefables.textures/Shaders/PremultipliedArrayInstanced.shader').read_text()
        for token in ('#pragma multi_compile_instancing','#pragma require 2darray','UNITY_DEFINE_INSTANCED_PROP(float4, _Rect)',
                      'UNITY_DEFINE_INSTANCED_PROP(float, _Layer)','UNITY_SAMPLE_TEX2DARRAY_LOD','Blend One OneMinusSrcAlpha'):
            self.assertIn(token,s)
    def test_graph_benchmark_has_bounded_exact_readback(self):
        s=(ROOT/'integrations/unity/com.bytefables.textures/Runtime/TextureGraphBenchmark.cs').read_text()
        for token in ('instanceCount <= 10000','MaxSide = 2048','enableInstancing = true','DrawMeshInstanced','ReadPixels','TextureHashes.Sha256','Graph instancing framebuffer differs'):
            self.assertIn(token,s)


if __name__=='__main__':unittest.main()
