"""Runner/staging/report tests. Mock process reports are NOT Unity or GPU evidence."""
from __future__ import annotations
import copy
import json
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
from tools.artwork_unity_stage import verify_unity_stage
from tools.artwork_unity_player import (prepare_player_project, run_player_qualification, check_player_report,
    check_build_report, artifact_inventory, _execute, TARGETS, SCHEMA)


def build_result(plan):
    q = plan['request']
    result = {k: q[k] for k in ('runId','editorVersion','manifestSha256','sentinelManifestSha256',
        'graphicsApi','scriptingBackend','colourSpace','renderPipeline','target')}
    result.update(schema='bytefables.unity-player-build.v1', status='passed', elapsedMilliseconds=1,
        developmentBuild=False, buildSucceeded=True, errors=0, totalSize=4, error=None)
    return result


def player_result(plan):
    result = build_result(plan)
    result.pop('target');result.pop('developmentBuild');result.pop('buildSucceeded');result.pop('errors');result.pop('totalSize')
    source = plan['source']; probe = plan['sentinel']
    n = source['sprites']*source['levelsPerSprite'] + probe['sprites']*probe['levelsPerSprite']
    result.update(schema=SCHEMA, playerExecuted=True, gpuExecuted=True, serializedAssetsExecuted=True,
        syntheticSentinelsExecuted=True, disposalExecuted=True, isEditor=False, skipped=0,
        runtimePlatform=plan['request']['runtimePlatform'], graphicsDevice='MOCK fixture, NOT GPU evidence',
        graphicsDeviceVersion='MOCK', operatingSystem='MOCK', sprites=source['sprites'], banks=source['banks'],
        cpuComparisons=n, gpuComparisons=n, shaderComparisons=n*3, bindingComparisons=source['sprites']+probe['sprites'],
        overlapComparisons=3, overlapByteTolerance=1)
    return result


class FixtureBase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name);self.source = make_fixture(self.root/'source');self.output=self.root/'out'
    def prepare(self, **kw):
        return prepare_player_project(self.source,self.output,confirm_public=True,**kw)


class PreparedProject(FixtureBase):
    def test_prepare_does_not_claim_execution(self):
        plan=self.prepare();self.assertEqual(plan['status'],'prepared');self.assertFalse(plan['playerExecuted'])
        self.assertFalse(plan['gpuExecuted']);self.assertFalse((self.output/'report.json').exists())
        self.assertFalse((self.output/'player').exists())
    def test_both_serialized_sources_and_streaming_sources_are_identical(self):
        plan=self.prepare()
        for name in ('ByteFablesFixture','ByteFablesSentinel'):
            a=self.output/'project/Assets'/name;b=self.output/'project/Assets/StreamingAssets'/name
            self.assertEqual(verify_unity_stage(a),verify_unity_stage(b))
            for path in a.rglob('*'):
                if path.is_file():self.assertEqual(path.read_bytes(),(b/path.relative_to(a)).read_bytes())
        self.assertEqual(plan['source']['sprites'],4)
    def test_embedded_package_and_serialized_reference_entry_points_exist(self):
        self.prepare();p=self.output/'project/Packages/com.bytefables.textures'
        for file in ['Runtime/TexturePlayerReadback.cs','Runtime/TexturePlayerQualification.cs','Editor/TexturePlayerBuild.cs']:
            self.assertTrue((p/file).is_file());self.assertTrue((p/(file+'.meta')).is_file())
        self.assertEqual(json.loads((p.parent/'manifest.json').read_text()),{'dependencies':{}})
    def test_consent_precedes_all_writes(self):
        with self.assertRaises(ValueError):prepare_player_project(self.source,self.output)
        self.assertFalse(self.output.exists())
    def test_invalid_target_and_version_do_not_write(self):
        for options in [{'target':'mac-metal'},{'editor_version':'latest'},{'editor_version':None}]:
            with self.assertRaises(ValueError):self.prepare(**options)
        self.assertFalse(self.output.exists())
    def test_existing_output_is_not_modified(self):
        self.prepare();before=(self.output/'plan.json').read_bytes()
        with self.assertRaises(ValueError):self.prepare()
        self.assertEqual((self.output/'plan.json').read_bytes(),before)
    def test_output_cannot_contain_or_be_contained_in_source(self):
        for out in [self.source/'nested',self.source.parent]:
            with self.assertRaises(ValueError):prepare_player_project(self.source,out,confirm_public=True)
    def test_corrupted_source_does_not_publish_plan_or_success(self):
        (self.source/'banks/bank-000.ktx2').write_bytes(b'corrupt')
        with self.assertRaises(ValueError):self.prepare()
        self.assertFalse((self.output/'plan.json').exists());self.assertFalse((self.output/'report.json').exists())
        self.assertTrue((self.output/'failure.json').exists())
    def test_run_ids_are_fresh_but_source_pins_are_stable(self):
        a=self.prepare();b=prepare_player_project(self.source,self.root/'second',confirm_public=True)
        self.assertNotEqual(a['request']['runId'],b['request']['runId'])
        self.assertEqual(a['request']['manifestSha256'],b['request']['manifestSha256'])
    def test_linux_profile_is_explicit(self):
        q=self.prepare(target='linux-vulkan')['request']
        self.assertEqual(q['graphicsApi'],'Vulkan');self.assertEqual(q['target'],'StandaloneLinux64')
        self.assertEqual(q['scriptingBackend'],'Mono');self.assertEqual(q['colourSpace'],'Gamma')
    def test_il2cpp_linear_profiles_are_explicit_and_do_not_change_transport(self):
        q=self.prepare(target='linux-vulkan-il2cpp-linear')['request']
        self.assertEqual(q['target'],'StandaloneLinux64');self.assertEqual(q['graphicsApi'],'Vulkan')
        self.assertEqual(q['scriptingBackend'],'IL2CPP');self.assertEqual(q['colourSpace'],'Linear')
        self.assertEqual(q['renderPipeline'],'BuiltIn')
        self.assertEqual(q['manifestSha256'],verify_unity_stage(self.output/'project/Assets/ByteFablesFixture')['manifestSha256'])
    def test_cli_prepare_and_missing_unity_failures_are_distinct(self):
        cli=[sys.executable,str(ROOT/'scripts/qualify-artwork-unity-player.py'),'--confirm-public',
            '--bundle',str(self.source),'--output',str(self.output),'--target','linux-vulkan']
        p=subprocess.run(cli+['--prepare-only'],capture_output=True,text=True)
        self.assertEqual(p.returncode,0,p.stderr);self.assertEqual(json.loads(p.stdout)['status'],'prepared')
        env=dict(os.environ);env.pop('UNITY_EDITOR',None)
        p=subprocess.run(cli,capture_output=True,text=True,env=env)
        self.assertNotEqual(p.returncode,0)


class ReceiptGate(FixtureBase):
    def setUp(self):
        super().setUp();self.plan=self.prepare()
    def test_complete_mock_reports_satisfy_only_the_report_validator(self):
        check_build_report(build_result(self.plan),self.plan['request']);check_player_report(player_result(self.plan),self.plan)
    def test_stale_version_pins_or_nonce_are_rejected(self):
        for key in ['runId','editorVersion','manifestSha256','sentinelManifestSha256','graphicsApi','scriptingBackend','colourSpace','renderPipeline']:
            r=player_result(self.plan);r[key]='other'
            with self.subTest(key=key),self.assertRaises(ValueError):check_player_report(r,self.plan)
    def test_missing_gpu_and_editor_reports_fail_closed(self):
        for key in ['playerExecuted','gpuExecuted','serializedAssetsExecuted','syntheticSentinelsExecuted','disposalExecuted']:
            r=player_result(self.plan);r[key]=False
            with self.subTest(key=key),self.assertRaises(ValueError):check_player_report(r,self.plan)
        for key,value in [('isEditor',True),('skipped',1),('runtimePlatform','WindowsEditor'),('error','failed')]:
            r=player_result(self.plan);r[key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):check_player_report(r,self.plan)
    def test_counts_must_be_exact_integers_not_bool_or_float(self):
        for key in ['cpuComparisons','gpuComparisons','shaderComparisons','bindingComparisons','overlapComparisons','overlapByteTolerance','sprites','banks','skipped']:
            for value in [True,1.0,-1]:
                r=player_result(self.plan);r[key]=value
                with self.subTest(key=key,value=value),self.assertRaises(ValueError):check_player_report(r,self.plan)
    def test_partial_build_or_development_mode_is_rejected(self):
        for key,value in [('target','wrong'),('buildSucceeded',False),('developmentBuild',True),('errors',True),('errors',1),('totalSize',0)]:
            r=build_result(self.plan);r[key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):check_build_report(r,self.plan['request'])
    def test_bad_device_and_time_evidence_is_rejected(self):
        for key,value in [('graphicsDevice',''),('graphicsDeviceVersion',None),('operatingSystem',3),('elapsedMilliseconds',True)]:
            r=player_result(self.plan);r[key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):check_player_report(r,self.plan)

class ProcessAndArtifactBoundaries(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name);self.source=make_fixture(self.root/'source');self.output=self.root/'out'
        install=self.root/'install';install.mkdir();self.editor=install/'Unity';self.editor.touch()
    def run_qual(self,**kw):
        return run_player_qualification(self.editor,self.source,self.output,confirm_public=True,target='linux-vulkan',**kw)
    def fake_execution(self,command,env,log,timeout):
        log.touch();plan=json.loads((self.output/'plan.json').read_bytes())
        if 'BYTEFABLES_PLAYER_REQUEST' in env:
            executable=Path(plan['request']['buildPath']);executable.parent.mkdir();executable.write_bytes(b'MOCK')
            (self.output/'build-result.json').write_bytes(_json(build_result(plan)))
        else:
            (self.output/'player-result.json').write_bytes(_json(player_result(plan)))
    def test_mock_process_protocol_is_bound_to_both_reports_and_artifact(self):
        with patch('platform.system',return_value='Linux'),patch('tools.artwork_unity_player._execute',side_effect=self.fake_execution) as execute:
            result=self.run_qual()
        self.assertEqual(execute.call_count,2);self.assertEqual(result['status'],'passed')
        self.assertEqual(result['buildReportSha256'],_sha((self.output/'build-result.json').read_bytes()))
        self.assertEqual(result['playerReportSha256'],_sha((self.output/'player-result.json').read_bytes()))
        self.assertIn('linux64',execute.call_args_list[0].args[0]);self.assertIn('-standaloneBuildSubtarget',execute.call_args_list[0].args[0]);self.assertNotIn('-nographics',execute.call_args_list[0].args[0]);self.assertNotIn('-quit',execute.call_args_list[1].args[0])
    def test_zero_exit_without_reports_never_passes(self):
        with patch('platform.system',return_value='Linux'),patch('tools.artwork_unity_player._execute'),self.assertRaises(ValueError):self.run_qual()
        self.assertFalse((self.output/'report.json').exists());self.assertTrue((self.output/'failure.json').exists())
    def test_substituted_executable_detected_after_run(self):
        def changed(*args):
            self.fake_execution(*args)
            if 'BYTEFABLES_PLAYER_REPORT' in args[1]:
                (self.output/'player/ByteFablesPlayer.x86_64').write_bytes(b'changed')
        with patch('platform.system',return_value='Linux'),patch('tools.artwork_unity_player._execute',side_effect=changed),self.assertRaises(ValueError):self.run_qual()
        self.assertFalse((self.output/'report.json').exists())
    def test_stale_player_report_leaves_only_failure(self):
        def stale(*args):
            self.fake_execution(*args)
            p=self.output/'player-result.json'
            if p.exists():
                r=json.loads(p.read_bytes());r['runId']='0'*32;p.write_bytes(_json(r))
        with patch('platform.system',return_value='Linux'),patch('tools.artwork_unity_player._execute',side_effect=stale),self.assertRaises(ValueError):self.run_qual()
        self.assertFalse((self.output/'report.json').exists());self.assertTrue((self.output/'failure.json').exists())
    def test_missing_editor_wrong_host_and_timeout_reject_before_writes(self):
        with patch('platform.system',return_value='Darwin'),self.assertRaises(ValueError):self.run_qual()
        with patch('platform.system',return_value='Linux'),self.assertRaises(ValueError):self.run_qual(build_timeout=True)
        self.editor.unlink()
        with patch('platform.system',return_value='Linux'),self.assertRaises(ValueError):self.run_qual()
        self.assertFalse(self.output.exists())
    def test_inventory_hashes_all_build_files(self):
        root=self.root/'player';root.mkdir();(root/'a').write_bytes(b'one');(root/'b').write_bytes(b'two')
        a=artifact_inventory(root);(root/'b').write_bytes(b'TWO');b=artifact_inventory(root)
        self.assertEqual(a['byteLength'],6);self.assertEqual(len(a['files']),2);self.assertNotEqual(a['sha256'],b['sha256'])
    def test_inventory_rejects_links_and_empty_build(self):
        root=self.root/'player';root.mkdir()
        with self.assertRaises(ValueError):artifact_inventory(root)
        try:(root/'link').symlink_to(self.editor)
        except OSError as e:self.skipTest(str(e))
        with self.assertRaises(ValueError):artifact_inventory(root)
    def test_inventory_enforces_total_byte_budget(self):
        root=self.root/'player';root.mkdir();(root/'a').write_bytes(b'too large')
        with patch('tools.artwork_unity_player.MAX_BUILD_BYTES',1),self.assertRaises(ValueError):artifact_inventory(root)
    def test_real_subprocess_exit_errors_are_not_passes(self):
        with self.assertRaises(ValueError):_execute([sys.executable,'-c','raise SystemExit(4)'],dict(os.environ),self.root/'exit.log',5)
    def test_real_subprocess_timeout_terminates_launcher(self):
        with self.assertRaises(subprocess.TimeoutExpired):_execute([sys.executable,'-c','import time; time.sleep(60)'],dict(os.environ),self.root/'timeout.log',0.1)
    def test_process_does_not_overwrite_log(self):
        log=self.root/'exists.log';log.write_bytes(b'keep')
        with self.assertRaises(FileExistsError):_execute([sys.executable,'-c','pass'],dict(os.environ),log,1)
        self.assertEqual(log.read_bytes(),b'keep')


class PlayerSourceInvariants(unittest.TestCase):
    """Static packaging checks only: explicitly not C# compilation or engine execution."""
    def test_runtime_has_no_editor_dependencies_and_keeps_serialized_assets(self):
        p=ROOT/'integrations/unity/com.bytefables.textures/Runtime'
        for name in ('TexturePlayerQualification.cs','TexturePlayerReadback.cs'):
            self.assertNotIn('using UnityEditor',(p/name).read_text())
        s=(p/'TexturePlayerQualification.cs').read_text()
        self.assertIn('[SerializeField] private TextureBundleAsset actual, sentinel;',s)
        self.assertIn('!Application.isEditor',s);self.assertIn('FileMode.CreateNew',s)
    def test_build_preserves_profile_and_non_development_player(self):
        s=(ROOT/'integrations/unity/com.bytefables.textures/Editor/TexturePlayerBuild.cs').read_text()
        for token in ['StandaloneBuildSubtarget.Player','BuildOptions.None','ScriptingImplementation.Mono2x',
            'ScriptingImplementation.IL2CPP','ColorSpace.Gamma','ColorSpace.Linear',
            'SetUseDefaultGraphicsAPIs(target, false)','GetScriptingBackend']:
            self.assertIn(token,s)
        runtime=(ROOT/'integrations/unity/com.bytefables.textures/Runtime/TexturePlayerQualification.cs').read_text()
        self.assertIn('expectedScriptingBackend',runtime);self.assertIn('expectedColourSpace',runtime)
    def test_probe_yields_for_deferred_gpu_resource_release(self):
        s=(ROOT/'integrations/unity/com.bytefables.textures/Runtime/TexturePlayerReadback.cs').read_text()
        self.assertIn('yield return null;',s);self.assertIn('finally { TextureArrayUpload.Destroy(cpu); }',s)
        self.assertNotIn('AssetDatabase',s)

if __name__=='__main__':unittest.main()
