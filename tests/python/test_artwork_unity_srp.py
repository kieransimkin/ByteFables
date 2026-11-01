"""URP/HDRP runner/report tests. Mock reports are NOT Unity/GPU evidence."""
from __future__ import annotations
import json, os, math, subprocess, sys, tempfile, unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT),str(ROOT/'integrations/framerudiments'),str(ROOT/'tests/helpers')]
from artwork_unity_fixture import make_fixture
from tools.artwork_native_benchmark import _json,_sha
from tools.artwork_unity_srp import (prepare_srp_project,run_srp_qualification,check_srp_build_report,
    check_srp_player_report,PROFILES,SCHEMA,BUILD_SCHEMA,SRP_VERSION)

def build_result(plan):
    q=plan['request'];r={k:q[k] for k in ('runId','editorVersion','profile','manifestSha256','sentinelManifestSha256','graphicsApi','scriptingBackend','colourSpace','renderPipeline','srpPackageName','srpPackageVersion','pipelineAssetType','target')}
    r.update(schema=BUILD_SCHEMA,status='passed',elapsedMilliseconds=1,developmentBuild=False,buildSucceeded=True,errors=0,totalSize=4,error=None);return r

def graph_result(source,n):
    cols=math.ceil(n**.5);rows=(n+cols-1)//cols;mip=0;tile=source['nativeSize']
    while mip+1<source['levelsPerSprite'] and (cols*tile>2048 or rows*tile>2048):mip+=1;tile=source['nativeSize']>>mip
    h='a'*64
    return dict(instances=n,uniqueSprites=min(n,source['sprites']),banks=source['banks'],drawCalls=max(1,math.ceil(n/1023)),mip=mip,width=cols*tile,height=rows*tile,pixelsCompared=cols*tile*rows*tile,submitMicroseconds=1,readbackMicroseconds=1,totalMicroseconds=2,exactPixels=True,expectedSha256=h,actualSha256=h)

def player_result(plan):
    q=plan['request'];s=plan['source'];p=plan['sentinel'];n=s['sprites']*s['levelsPerSprite']+p['sprites']*p['levelsPerSprite']
    r={k:q[k] for k in ('runId','editorVersion','profile','manifestSha256','sentinelManifestSha256','graphicsApi','scriptingBackend','colourSpace','renderPipeline','srpPackageName','srpPackageVersion','pipelineAssetType')}
    r.update(schema=SCHEMA,status='passed',elapsedMilliseconds=1,error=None,pipelineRuntimeType=q['pipelineRuntimeType'],playerExecuted=True,gpuExecuted=True,serializedAssetsExecuted=True,syntheticSentinelsExecuted=True,disposalExecuted=True,pipelineExecuted=True,graphExecuted=True,isEditor=False,runtimePlatform=q['runtimePlatform'],graphicsDevice='MOCK, NOT GPU evidence',graphicsDeviceVersion='MOCK',operatingSystem='MOCK',banks=s['banks'],sprites=s['sprites'],cpuComparisons=n,gpuComparisons=n,shaderComparisons=n*3,bindingComparisons=s['sprites']+p['sprites'],overlapComparisons=3,overlapByteTolerance=1,pipelineComparisons=q['pipelineComparisons'],pipelineByteTolerance=1,skipped=0,graphResults=[graph_result(s,x) for x in q['graphCounts']]);return r

class Base(unittest.TestCase):
    def setUp(self):self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name);self.source=make_fixture(self.root/'source');self.output=self.root/'out'
    def prep(self,**kw):return prepare_srp_project(self.source,self.output,confirm_public=True,**kw)

class Preparation(Base):
    def test_default_urp_profile_is_pinned(self):
        q=self.prep()['request'];self.assertEqual(q['profile'],'windows-d3d12-urp-il2cpp-linear');self.assertEqual(q['renderPipeline'],'URP');self.assertEqual(q['srpPackageVersion'],SRP_VERSION);self.assertEqual(q['graphCounts'],[1000,10000]);self.assertEqual(q['scriptingBackend'],'IL2CPP');self.assertEqual(q['colourSpace'],'Linear')
    def test_hdrp_profile_is_separate_and_pinned(self):
        q=self.prep(profile='linux-vulkan-hdrp-il2cpp-linear')['request'];self.assertEqual(q['renderPipeline'],'HDRP');self.assertEqual(q['graphicsApi'],'Vulkan');self.assertEqual(q['srpPackageName'],'com.unity.render-pipelines.high-definition');self.assertIn('HDRenderPipelineAsset',q['pipelineAssetType'])
    def test_urp_manifest_contains_only_exact_pipeline_dependency(self):
        self.prep();m=json.loads((self.output/'project/Packages/manifest.json').read_text());self.assertEqual(m,{'dependencies':{'com.unity.render-pipelines.universal':SRP_VERSION}})
    def test_hdrp_manifest_contains_only_exact_pipeline_dependency(self):
        self.prep(profile='windows-d3d12-hdrp-il2cpp-linear');m=json.loads((self.output/'project/Packages/manifest.json').read_text());self.assertEqual(m,{'dependencies':{'com.unity.render-pipelines.high-definition':SRP_VERSION}})
    def test_all_profiles_are_il2cpp_linear_and_native(self):
        self.assertEqual(len(PROFILES),5)
        for name,p in PROFILES.items():
            with self.subTest(name=name):self.assertIn(p['host'],('Windows','Linux'));self.assertIn(p['renderPipeline'],('URP','HDRP'));self.assertEqual(p['packageVersion'],SRP_VERSION)
    def test_invalid_profile_counts_version_and_consent_precede_writes(self):
        with self.assertRaises(ValueError):prepare_srp_project(self.source,self.output)
        for kw in ({'profile':'builtin'},{'editor_version':'latest'},{'graph_counts':[]},{'graph_counts':[10,1]},{'graph_counts':[10001]}):
            with self.subTest(kw=kw),self.assertRaises(ValueError):self.prep(**kw)
        self.assertFalse(self.output.exists())
    def test_pipeline_comparison_count_is_bounded_and_deterministic(self):
        p=self.prep();q=p['request'];self.assertEqual(q['pipelineComparisons'],(min(16,p['source']['sprites'])*p['source']['levelsPerSprite']+p['sentinel']['sprites']*p['sentinel']['levelsPerSprite'])*3)
    def test_preparation_claims_no_execution(self):
        p=self.prep();self.assertEqual(p['status'],'prepared');self.assertFalse(p['playerExecuted']);self.assertFalse(p['pipelineExecuted']);self.assertFalse(p['graphExecuted']);self.assertFalse((self.output/'report.json').exists())
    def test_cli_prepare_needs_no_unity(self):
        cmd=[sys.executable,str(ROOT/'scripts/qualify-artwork-unity-srp.py'),'--confirm-public','--prepare-only','--bundle',str(self.source),'--output',str(self.output),'--profile','linux-vulkan-urp-il2cpp-linear'];r=subprocess.run(cmd,capture_output=True,text=True);self.assertEqual(r.returncode,0,r.stderr);self.assertEqual(json.loads(r.stdout)['status'],'prepared')

class Reports(Base):
    def setUp(self):super().setUp();self.plan=self.prep(profile='linux-vulkan-hdrp-il2cpp-linear')
    def test_complete_mock_reports_validate_only_protocol(self):check_srp_build_report(build_result(self.plan),self.plan['request']);check_srp_player_report(player_result(self.plan),self.plan)
    def test_pipeline_and_package_pins_are_strict(self):
        for key in ('profile','renderPipeline','srpPackageName','srpPackageVersion','pipelineAssetType','graphicsApi','scriptingBackend','colourSpace'):
            r=player_result(self.plan);r[key]='other'
            with self.subTest(key=key),self.assertRaises(ValueError):check_srp_player_report(r,self.plan)
    def test_runtime_pipeline_type_is_strict(self):
        r=player_result(self.plan);r['pipelineRuntimeType']='Wrong'
        with self.assertRaises(ValueError):check_srp_player_report(r,self.plan)
    def test_execution_flags_and_skips_fail_closed(self):
        for key in ('playerExecuted','gpuExecuted','serializedAssetsExecuted','syntheticSentinelsExecuted','disposalExecuted','pipelineExecuted','graphExecuted'):
            r=player_result(self.plan);r[key]=False
            with self.subTest(key=key),self.assertRaises(ValueError):check_srp_player_report(r,self.plan)
        r=player_result(self.plan);r['skipped']=1
        with self.assertRaises(ValueError):check_srp_player_report(r,self.plan)
    def test_pipeline_comparison_coverage_is_exact(self):
        for v in (0,self.plan['request']['pipelineComparisons']-1,self.plan['request']['pipelineComparisons']+1,True):
            r=player_result(self.plan);r['pipelineComparisons']=v
            with self.subTest(v=v),self.assertRaises(ValueError):check_srp_player_report(r,self.plan)
    def test_graph_hash_geometry_and_inventory_are_strict(self):
        for key,value in [('exactPixels',False),('actualSha256','b'*64),('width',1),('mip',6),('drawCalls',0)]:
            r=player_result(self.plan);r['graphResults'][0][key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):check_srp_player_report(r,self.plan)
    def test_build_must_match_package_pipeline_and_nondevelopment(self):
        for key,value in [('srpPackageVersion','wrong'),('pipelineAssetType','wrong'),('buildSucceeded',False),('developmentBuild',True),('errors',1),('totalSize',0)]:
            r=build_result(self.plan);r[key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):check_srp_build_report(r,self.plan['request'])

class Runner(unittest.TestCase):
    def setUp(self):self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name);self.source=make_fixture(self.root/'source');self.output=self.root/'out';d=self.root/'install';d.mkdir();self.editor=d/'Unity';self.editor.touch()
    def fake(self,command,env,log,timeout):
        log.touch();plan=json.loads((self.output/'plan.json').read_bytes())
        if 'BYTEFABLES_SRP_REQUEST' in env:
            exe=Path(plan['request']['buildPath']);exe.parent.mkdir();exe.write_bytes(b'MOCK');(self.output/'build-result.json').write_bytes(_json(build_result(plan)))
        else:(self.output/'player-result.json').write_bytes(_json(player_result(plan)))
    def run(self,**kw):return run_srp_qualification(self.editor,self.source,self.output,confirm_public=True,profile='linux-vulkan-urp-il2cpp-linear',**kw)
    def test_mock_protocol_binds_build_player_and_artifact(self):
        with patch('platform.system',return_value='Linux'),patch('tools.artwork_unity_srp._execute',side_effect=self.fake) as ex:r=self.run()
        self.assertEqual(ex.call_count,2);self.assertEqual(r['status'],'passed');self.assertTrue(r['pipelineExecuted']);self.assertTrue(r['graphExecuted']);self.assertIn('TextureSrpBuild.RunFromCommandLine',ex.call_args_list[0].args[0]);self.assertIn('-force-vulkan',ex.call_args_list[1].args[0])
    def test_wrong_host_and_missing_editor_fail_before_output(self):
        with patch('platform.system',return_value='Windows'),self.assertRaises(ValueError):self.run()
        self.editor.unlink()
        with patch('platform.system',return_value='Linux'),self.assertRaises(ValueError):self.run()
        self.assertFalse(self.output.exists())
    def test_zero_exit_without_reports_never_passes(self):
        with patch('platform.system',return_value='Linux'),patch('tools.artwork_unity_srp._execute'),self.assertRaises(ValueError):self.run()
        self.assertTrue((self.output/'failure.json').exists());self.assertFalse((self.output/'report.json').exists())

class SourceInvariants(unittest.TestCase):
    def test_build_creates_real_srp_assets_and_checks_package_version(self):
        s=(ROOT/'integrations/unity/com.bytefables.textures/Editor/TextureSrpBuild.cs').read_text()
        for t in ('UniversalRenderPipelineAsset','HDRenderPipelineAsset','PackageInfo.FindForAssetPath','package.version==request.srpPackageVersion','GraphicsSettings.defaultRenderPipeline=pipeline','ScriptingImplementation.IL2CPP','ColorSpace.Linear'):self.assertIn(t,s)
    def test_runtime_requires_real_active_pipeline_and_camera_probe(self):
        s=(ROOT/'integrations/unity/com.bytefables.textures/Runtime/TextureSrpQualification.cs').read_text()
        for t in ('GraphicsSettings.currentRenderPipeline','GraphicsSettings.isScriptableRenderPipelineEnabled','RenderPipelineManager.currentPipeline','TextureSrpCameraProbe.Qualify','report.pipelineRuntimeType==expectedRuntimeType'):self.assertIn(t,s)
    def test_camera_probe_uses_camera_render_not_graphics_blit(self):
        s=(ROOT/'integrations/unity/com.bytefables.textures/Runtime/TextureSrpCameraProbe.cs').read_text();self.assertIn('camera.Render()',s);self.assertNotIn('Graphics.Blit',s);self.assertIn('pipelineComparisons++',s)
    def test_pipeline_shaders_are_separate_and_premultiplied(self):
        u=(ROOT/'integrations/unity/com.bytefables.textures/Shaders/PremultipliedArrayURP.shader').read_text();h=(ROOT/'integrations/unity/com.bytefables.textures/Shaders/PremultipliedArrayHDRP.shader').read_text()
        self.assertIn('"UniversalPipeline"',u);self.assertIn('"HDRenderPipeline"',h)
        for s in (u,h):self.assertIn('Blend One OneMinusSrcAlpha',s);self.assertIn('#pragma require 2darray',s);self.assertIn('UNITY_SAMPLE_TEX2DARRAY_LOD',s)

if __name__=='__main__':unittest.main()
