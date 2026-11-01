"""Qualify URP/HDRP standalone Unity profiles in a fresh isolated project.

This profile consumes the frozen ByteFables KTX2 Texture2DArray transport.  It
adds a real Scriptable Render Pipeline camera pass on top of the existing exact
raw texture, alpha, orientation and instancing checks.  Missing packages,
backends, pipeline activation or GPU evidence fail closed; no capability becomes
an automatic successful skip.
"""
from __future__ import annotations

import math
import os
from pathlib import Path
import platform
import re
import secrets
import shutil

from tools.artwork_asset_bundle import _expect, _file, _no_links
from tools.artwork_native_benchmark import _json, _read_json, _sha
from tools.artwork_transparent_bundle import _new_output, _failure
from tools.artwork_unity_stage import stage_unity_bundle, verify_unity_stage
from tools.artwork_unity_qualification import PACKAGE, ROOT
from tools.artwork_unity_player import artifact_inventory, _execute, _positive, _version

SCHEMA = 'bytefables.unity-srp-player-qualification.v1'
BUILD_SCHEMA = 'bytefables.unity-srp-player-build.v1'
REQUEST_SCHEMA = 'bytefables.unity-srp-player-request.v1'
PLAN_SCHEMA = 'bytefables.unity-srp-player-plan.v1'
RECEIPT_SCHEMA = 'bytefables.unity-srp-player-receipt.v1'
SRP_VERSION = '16.0.6'
DEFAULT_GRAPH_COUNTS = (1000, 10000)
MAX_BUILD_BYTES = 2 * 1024 * 1024 * 1024

PROFILES = {
    'windows-d3d11-urp-il2cpp-linear': {
        'host': 'Windows', 'target': 'StandaloneWindows64', 'runtime': 'WindowsPlayer',
        'graphics': 'Direct3D11', 'launch': '-force-d3d11', 'exe': 'ByteFablesSrp.exe', 'cli': 'win64',
        'renderPipeline': 'URP', 'packageName': 'com.unity.render-pipelines.universal', 'packageVersion': SRP_VERSION,
        'assetType': 'UnityEngine.Rendering.Universal.UniversalRenderPipelineAsset',
        'runtimeType': 'UnityEngine.Rendering.Universal.UniversalRenderPipeline',
    },
    'windows-d3d12-urp-il2cpp-linear': {
        'host': 'Windows', 'target': 'StandaloneWindows64', 'runtime': 'WindowsPlayer',
        'graphics': 'Direct3D12', 'launch': '-force-d3d12', 'exe': 'ByteFablesSrp.exe', 'cli': 'win64',
        'renderPipeline': 'URP', 'packageName': 'com.unity.render-pipelines.universal', 'packageVersion': SRP_VERSION,
        'assetType': 'UnityEngine.Rendering.Universal.UniversalRenderPipelineAsset',
        'runtimeType': 'UnityEngine.Rendering.Universal.UniversalRenderPipeline',
    },
    'linux-vulkan-urp-il2cpp-linear': {
        'host': 'Linux', 'target': 'StandaloneLinux64', 'runtime': 'LinuxPlayer',
        'graphics': 'Vulkan', 'launch': '-force-vulkan', 'exe': 'ByteFablesSrp.x86_64', 'cli': 'linux64',
        'renderPipeline': 'URP', 'packageName': 'com.unity.render-pipelines.universal', 'packageVersion': SRP_VERSION,
        'assetType': 'UnityEngine.Rendering.Universal.UniversalRenderPipelineAsset',
        'runtimeType': 'UnityEngine.Rendering.Universal.UniversalRenderPipeline',
    },
    'windows-d3d12-hdrp-il2cpp-linear': {
        'host': 'Windows', 'target': 'StandaloneWindows64', 'runtime': 'WindowsPlayer',
        'graphics': 'Direct3D12', 'launch': '-force-d3d12', 'exe': 'ByteFablesSrp.exe', 'cli': 'win64',
        'renderPipeline': 'HDRP', 'packageName': 'com.unity.render-pipelines.high-definition', 'packageVersion': SRP_VERSION,
        'assetType': 'UnityEngine.Rendering.HighDefinition.HDRenderPipelineAsset',
        'runtimeType': 'UnityEngine.Rendering.HighDefinition.HDRenderPipeline',
    },
    'linux-vulkan-hdrp-il2cpp-linear': {
        'host': 'Linux', 'target': 'StandaloneLinux64', 'runtime': 'LinuxPlayer',
        'graphics': 'Vulkan', 'launch': '-force-vulkan', 'exe': 'ByteFablesSrp.x86_64', 'cli': 'linux64',
        'renderPipeline': 'HDRP', 'packageName': 'com.unity.render-pipelines.high-definition', 'packageVersion': SRP_VERSION,
        'assetType': 'UnityEngine.Rendering.HighDefinition.HDRenderPipelineAsset',
        'runtimeType': 'UnityEngine.Rendering.HighDefinition.HDRenderPipeline',
    },
}


def _graph_counts(values) -> tuple[int, ...]:
    if values is None:
        return DEFAULT_GRAPH_COUNTS
    _expect(isinstance(values, (list, tuple)) and 1 <= len(values) <= 3, 'One to three graph counts required')
    result = tuple(values)
    _expect(all(type(v) is int and 1 <= v <= 10000 for v in result), 'Graph counts must be integers in 1..10000')
    _expect(tuple(sorted(set(result))) == result, 'Graph counts must be unique and strictly increasing')
    return result


def _pipeline_sample_count(source: dict, sentinel: dict) -> int:
    # Up to 16 real identities plus every synthetic sentinel, across every mip
    # and transparent/black/white mattes.
    return (min(16, source['sprites']) * source['levelsPerSprite'] +
            sentinel['sprites'] * sentinel['levelsPerSprite']) * 3


def prepare_srp_project(bundle: Path, output: Path, *, confirm_public: bool = False,
                        profile: str = 'windows-d3d12-urp-il2cpp-linear',
                        editor_version: str = '6000.0.62f1', graph_counts=None) -> dict:
    """Prepare inputs only.  No Unity process starts and no pass is claimed."""
    _expect(confirm_public is True, 'Explicit --confirm-public consent required')
    _expect(profile in PROFILES, 'Unsupported Unity SRP profile')
    _version(editor_version)
    counts = _graph_counts(graph_counts)
    source = _no_links(bundle)
    output = _new_output(output, (source, PACKAGE))
    output.mkdir(parents=True)
    try:
        project = output / 'project'
        for name in ('Assets', 'Packages', 'ProjectSettings'):
            (project / name).mkdir(parents=True)
        for path in PACKAGE.rglob('*'):
            _no_links(path)
        shutil.copytree(PACKAGE, project / 'Packages/com.bytefables.textures')
        p = PROFILES[profile]
        # Unity 6000.0's URP/HDRP documentation is the 16.x package line.  Pin
        # an exact tested package instead of asking Package Manager for latest.
        (project / 'Packages/manifest.json').write_bytes(_json({'dependencies': {
            p['packageName']: p['packageVersion'],
        }}))
        (project / 'ProjectSettings/ProjectVersion.txt').write_text(
            f'm_EditorVersion: {editor_version}\n', encoding='utf-8')

        actual = stage_unity_bundle(source, project / 'Assets/ByteFablesFixture', confirm_public=True)
        import sys
        sys.path.insert(0, str(ROOT / 'tests/helpers'))
        try:
            from artwork_unity_fixture import make_fixture
            sentinel_source = make_fixture(output / 'synthetic-source')
        finally:
            sys.path.pop(0)
        sentinel = stage_unity_bundle(sentinel_source, project / 'Assets/ByteFablesSentinel', confirm_public=True)
        streaming = project / 'Assets/StreamingAssets'
        streaming.mkdir()
        for name in ('ByteFablesFixture', 'ByteFablesSentinel'):
            shutil.copytree(project / 'Assets' / name, streaming / name)
            verify_unity_stage(streaming / name)

        request = {
            'schema': REQUEST_SCHEMA, 'runId': secrets.token_hex(16), 'editorVersion': editor_version,
            'profile': profile, 'target': p['target'], 'runtimePlatform': p['runtime'],
            'graphicsApi': p['graphics'], 'scriptingBackend': 'IL2CPP', 'colourSpace': 'Linear',
            'renderPipeline': p['renderPipeline'], 'srpPackageName': p['packageName'],
            'srpPackageVersion': p['packageVersion'], 'pipelineAssetType': p['assetType'],
            'pipelineRuntimeType': p['runtimeType'], 'manifestSha256': actual['manifestSha256'],
            'sentinelManifestSha256': sentinel['manifestSha256'], 'graphCounts': list(counts),
            'pipelineComparisons': _pipeline_sample_count(actual, sentinel),
            'buildPath': str(output / 'player' / p['exe']),
            'buildReportPath': str(output / 'build-result.json'),
        }
        (project / 'srp-player-request.json').write_bytes(_json(request))
        plan = {
            'schema': PLAN_SCHEMA, 'status': 'prepared', 'playerExecuted': False,
            'gpuExecuted': False, 'pipelineExecuted': False, 'graphExecuted': False,
            'targetProfile': profile, 'request': request, 'source': actual, 'sentinel': sentinel,
        }
        (output / 'plan.json').write_bytes(_json(plan))
        return plan
    except Exception as exc:
        _failure(output, exc)
        raise


def _base_report(report: dict, schema: str, request: dict) -> None:
    _expect(isinstance(report, dict) and report.get('schema') == schema and report.get('status') == 'passed',
            'No successful completed Unity SRP report')
    for key in ('runId', 'editorVersion', 'profile', 'manifestSha256', 'sentinelManifestSha256',
                'graphicsApi', 'scriptingBackend', 'colourSpace', 'renderPipeline',
                'srpPackageName', 'srpPackageVersion', 'pipelineAssetType'):
        _expect(report.get(key) == request[key], f'Unity SRP report {key} mismatch')
    _positive(report.get('elapsedMilliseconds'), 'Elapsed milliseconds', 0, 24 * 60 * 60 * 1000)
    _expect(not report.get('error'), 'Successful SRP report must not carry an error')


def check_srp_build_report(report: dict, request: dict) -> None:
    _base_report(report, BUILD_SCHEMA, request)
    _expect(report.get('target') == request['target'] and report.get('buildSucceeded') is True,
            'Wrong or incomplete Unity SRP player build')
    _expect(report.get('developmentBuild') is False and type(report.get('errors')) is int and report['errors'] == 0,
            'Expected a non-development SRP build with no errors')
    _positive(report.get('totalSize'), 'Build size', 1, MAX_BUILD_BYTES)


def check_srp_player_report(report: dict, plan: dict) -> None:
    request = plan['request']
    _base_report(report, SCHEMA, request)
    _expect(report.get('pipelineRuntimeType') == request['pipelineRuntimeType'], 'Wrong active SRP runtime type')
    for name in ('playerExecuted', 'gpuExecuted', 'serializedAssetsExecuted', 'syntheticSentinelsExecuted',
                 'disposalExecuted', 'pipelineExecuted', 'graphExecuted'):
        _expect(report.get(name) is True, f'SRP player did not execute {name}')
    _expect(report.get('isEditor') is False and report.get('runtimePlatform') == request['runtimePlatform'],
            'An editor result is not SRP standalone-player evidence')
    _expect(type(report.get('skipped')) is int and report['skipped'] == 0, 'Skipped SRP checks cannot pass')
    for key in ('graphicsDevice', 'graphicsDeviceVersion', 'operatingSystem'):
        _expect(isinstance(report.get(key), str) and 0 < len(report[key]) <= 512, f'Missing {key}')

    source, sentinel = plan['source'], plan['sentinel']
    comparisons = source['sprites'] * source['levelsPerSprite'] + sentinel['sprites'] * sentinel['levelsPerSprite']
    exact = {
        'banks': source['banks'], 'sprites': source['sprites'],
        'cpuComparisons': comparisons, 'gpuComparisons': comparisons,
        'shaderComparisons': comparisons * 3, 'bindingComparisons': source['sprites'] + sentinel['sprites'],
        'overlapComparisons': 3, 'overlapByteTolerance': 1,
        'pipelineComparisons': request['pipelineComparisons'], 'pipelineByteTolerance': 1,
    }
    for key, value in exact.items():
        _expect(type(report.get(key)) is int and report[key] == value, f'Incomplete or changed {key}')

    graphs = report.get('graphResults')
    _expect(isinstance(graphs, list) and len(graphs) == len(request['graphCounts']), 'SRP graph result inventory mismatch')
    for item, instances in zip(graphs, request['graphCounts']):
        _expect(isinstance(item, dict) and type(item.get('instances')) is int and item['instances'] == instances,
                'SRP graph instance count mismatch')
        _expect(item.get('uniqueSprites') == min(instances, source['sprites']) and item.get('banks') == source['banks'],
                'SRP graph source inventory mismatch')
        _expect(item.get('exactPixels') is True, 'SRP graph framebuffer was not exact')
        for key in ('expectedSha256', 'actualSha256'):
            _expect(isinstance(item.get(key), str) and re.fullmatch(r'[a-f0-9]{64}', item[key]), f'Invalid graph {key}')
        _expect(item['expectedSha256'] == item['actualSha256'], 'SRP graph output hash mismatch')
        for key, lo, hi in (
            ('drawCalls', 1, instances), ('mip', 0, source['levelsPerSprite'] - 1),
            ('width', 1, 2048), ('height', 1, 2048), ('pixelsCompared', 1, 2048*2048),
            ('submitMicroseconds', 0, 60*60*1_000_000), ('readbackMicroseconds', 0, 60*60*1_000_000),
            ('totalMicroseconds', 0, 60*60*1_000_000),
        ):
            _positive(item.get(key), f'SRP graph {key}', lo, hi)
        columns = math.ceil(instances ** 0.5); rows = (instances + columns - 1) // columns
        mip = 0; tile = source['nativeSize']
        while mip + 1 < source['levelsPerSprite'] and (columns*tile > 2048 or rows*tile > 2048):
            mip += 1; tile = source['nativeSize'] >> mip
        _expect(item['mip'] == mip and item['width'] == columns*tile and item['height'] == rows*tile,
                'SRP graph mip/framebuffer geometry mismatch')
        _expect(item['pixelsCompared'] == item['width'] * item['height'], 'SRP graph compared-pixel geometry mismatch')


def run_srp_qualification(editor: Path, bundle: Path, output: Path, *, confirm_public: bool = False,
                          profile: str = 'windows-d3d12-urp-il2cpp-linear',
                          editor_version: str = '6000.0.62f1', graph_counts=None,
                          build_timeout: int = 3600, player_timeout: int = 1200) -> dict:
    _expect(confirm_public is True, 'Explicit --confirm-public consent required')
    _expect(profile in PROFILES, 'Unsupported Unity SRP profile')
    p = PROFILES[profile]
    _expect(platform.system() == p['host'], 'SRP build-and-run profile must match current OS')
    _version(editor_version); _positive(build_timeout, 'Build timeout', 30, 7200); _positive(player_timeout, 'Player timeout', 30, 2400)
    editor = _no_links(editor); _expect(editor.is_file(), 'Installed Unity executable required; no successful skip')
    output = _new_output(output, (_no_links(bundle), PACKAGE, editor.parent))
    plan = prepare_srp_project(bundle, output, confirm_public=True, profile=profile,
                               editor_version=editor_version, graph_counts=graph_counts)
    try:
        request = plan['request']; project = output / 'project'
        env = {k:v for k,v in os.environ.items() if not k.startswith(('BYTEFABLES_SRP_', 'BYTEFABLES_PLAYER_', 'BYTEFABLES_UNITY_'))}
        env['BYTEFABLES_SRP_REQUEST'] = str(project / 'srp-player-request.json')
        command = [str(editor), '-batchmode', '-projectPath', str(project), '-buildTarget', p['cli'],
                   '-standaloneBuildSubtarget', 'Player',
                   '-executeMethod', 'ByteFables.Textures.Editor.TextureSrpBuild.RunFromCommandLine',
                   '-logFile', str(output / 'unity-build.log'), '-quit']
        _execute(command, env, output / 'build-launcher.log', build_timeout)
        build, build_sha = _read_json(_file(output, 'build-result.json'), 1024*1024)
        check_srp_build_report(build, request)
        executable = _no_links(Path(request['buildPath'])); _expect(executable.is_file(), 'SRP build reported success without executable')
        inventory = artifact_inventory(output / 'player'); (output / 'player-inventory.json').write_bytes(_json(inventory))
        env.pop('BYTEFABLES_SRP_REQUEST'); env['BYTEFABLES_SRP_RUN_ID'] = request['runId']; env['BYTEFABLES_SRP_REPORT'] = str(output / 'player-result.json')
        _execute([str(executable), '-batchmode', p['launch'], '-logFile', str(output / 'unity-player.log')],
                 env, output / 'player-launcher.log', player_timeout)
        report, player_sha = _read_json(_file(output, 'player-result.json'), 2*1024*1024)
        check_srp_player_report(report, plan)
        _expect(artifact_inventory(output / 'player') == inventory, 'Built SRP player changed during qualification')
        receipt = {
            'schema': RECEIPT_SCHEMA, 'status': 'passed', 'runId': request['runId'],
            'manifestSha256': request['manifestSha256'], 'targetProfile': profile,
            'buildReportSha256': build_sha, 'playerReportSha256': player_sha,
            'playerArtifactSha256': inventory['sha256'], 'playerExecuted': True, 'gpuExecuted': True,
            'pipelineExecuted': True, 'graphExecuted': True, 'result': report,
            'warning': 'Unsigned evidence for this exact SRP package/editor/build/device; not universal compatibility or FPS evidence.',
        }
        with (output / 'report.json').open('xb') as stream: stream.write(_json(receipt))
        return receipt
    except Exception as exc:
        (output / 'report.json').unlink(missing_ok=True); _failure(output, exc); raise
