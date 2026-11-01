"""Qualify advanced standalone Unity profiles in an isolated project.

This keeps the existing Mono/Gamma player contract frozen and adds a separate
IL2CPP/Linear profile plus a deterministic 1k/10k texture-array graph workload.
Preparation, build execution and GPU evidence are separate states; no missing
Unity/graphics capability is converted into a pass.
"""
from __future__ import annotations

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

SCHEMA = 'bytefables.unity-advanced-player-qualification.v1'
BUILD_SCHEMA = 'bytefables.unity-advanced-player-build.v1'
REQUEST_SCHEMA = 'bytefables.unity-advanced-player-request.v1'
PLAN_SCHEMA = 'bytefables.unity-advanced-player-plan.v1'
RECEIPT_SCHEMA = 'bytefables.unity-advanced-player-receipt.v1'
MAX_BUILD_BYTES = 2 * 1024 * 1024 * 1024
DEFAULT_GRAPH_COUNTS = (1000, 10000)

PROFILES = {
    'windows-d3d11-il2cpp-linear': {
        'host': 'Windows', 'target': 'StandaloneWindows64', 'runtime': 'WindowsPlayer',
        'graphics': 'Direct3D11', 'launch': '-force-d3d11', 'exe': 'ByteFablesAdvanced.exe',
        'cli': 'win64', 'scriptingBackend': 'IL2CPP', 'colourSpace': 'Linear', 'renderPipeline': 'BuiltIn',
    },
    'windows-d3d12-il2cpp-linear': {
        'host': 'Windows', 'target': 'StandaloneWindows64', 'runtime': 'WindowsPlayer',
        'graphics': 'Direct3D12', 'launch': '-force-d3d12', 'exe': 'ByteFablesAdvanced.exe',
        'cli': 'win64', 'scriptingBackend': 'IL2CPP', 'colourSpace': 'Linear', 'renderPipeline': 'BuiltIn',
    },
    'linux-vulkan-il2cpp-linear': {
        'host': 'Linux', 'target': 'StandaloneLinux64', 'runtime': 'LinuxPlayer',
        'graphics': 'Vulkan', 'launch': '-force-vulkan', 'exe': 'ByteFablesAdvanced.x86_64',
        'cli': 'linux64', 'scriptingBackend': 'IL2CPP', 'colourSpace': 'Linear', 'renderPipeline': 'BuiltIn',
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


def prepare_advanced_project(bundle: Path, output: Path, *, confirm_public: bool = False,
                             profile: str = 'windows-d3d11-il2cpp-linear',
                             editor_version: str = '6000.0.62f1', graph_counts=None) -> dict:
    """Prepare inputs only. No Unity process is started and no qualification pass is claimed."""
    _expect(confirm_public is True, 'Explicit --confirm-public consent required')
    _expect(profile in PROFILES, 'Unsupported advanced Unity profile')
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
        (project / 'Packages/manifest.json').write_bytes(_json({'dependencies': {}}))
        (project / 'ProjectSettings/ProjectVersion.txt').write_text(
            f'm_EditorVersion: {editor_version}\n', encoding='utf-8')

        actual = stage_unity_bundle(source, project / 'Assets/ByteFablesFixture', confirm_public=True)
        # Explicit synthetic orientation/alpha probes; not additional real identities.
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

        p = PROFILES[profile]
        request = {
            'schema': REQUEST_SCHEMA,
            'runId': secrets.token_hex(16),
            'editorVersion': editor_version,
            'profile': profile,
            'target': p['target'],
            'runtimePlatform': p['runtime'],
            'graphicsApi': p['graphics'],
            'scriptingBackend': p['scriptingBackend'],
            'colourSpace': p['colourSpace'],
            'renderPipeline': p['renderPipeline'],
            'manifestSha256': actual['manifestSha256'],
            'sentinelManifestSha256': sentinel['manifestSha256'],
            'graphCounts': list(counts),
            'buildPath': str(output / 'player' / p['exe']),
            'buildReportPath': str(output / 'build-result.json'),
        }
        (project / 'advanced-player-request.json').write_bytes(_json(request))
        plan = {
            'schema': PLAN_SCHEMA,
            'status': 'prepared',
            'playerExecuted': False,
            'gpuExecuted': False,
            'graphExecuted': False,
            'targetProfile': profile,
            'request': request,
            'source': actual,
            'sentinel': sentinel,
        }
        (output / 'plan.json').write_bytes(_json(plan))
        return plan
    except Exception as exc:
        _failure(output, exc)
        raise


def _base_report(report: dict, schema: str, request: dict) -> None:
    _expect(isinstance(report, dict) and report.get('schema') == schema and report.get('status') == 'passed',
            'No successful completed advanced Unity report')
    for key in ('runId', 'editorVersion', 'profile', 'manifestSha256', 'sentinelManifestSha256',
                'graphicsApi', 'scriptingBackend', 'colourSpace', 'renderPipeline'):
        _expect(report.get(key) == request[key], f'Advanced Unity report {key} mismatch')
    _positive(report.get('elapsedMilliseconds'), 'Elapsed milliseconds', 0, 24 * 60 * 60 * 1000)
    _expect(not report.get('error'), 'Successful report must not carry an error')


def check_advanced_build_report(report: dict, request: dict) -> None:
    _base_report(report, BUILD_SCHEMA, request)
    _expect(report.get('target') == request['target'] and report.get('buildSucceeded') is True,
            'Wrong or incomplete advanced Unity player build')
    _expect(report.get('developmentBuild') is False and type(report.get('errors')) is int and report['errors'] == 0,
            'Expected a non-development advanced build with no errors')
    _positive(report.get('totalSize'), 'Build size', 1, MAX_BUILD_BYTES)


def check_advanced_player_report(report: dict, plan: dict) -> None:
    request = plan['request']
    _base_report(report, SCHEMA, request)
    for name in ('playerExecuted', 'gpuExecuted', 'serializedAssetsExecuted', 'syntheticSentinelsExecuted',
                 'disposalExecuted', 'graphExecuted'):
        _expect(report.get(name) is True, f'Advanced player did not execute {name}')
    _expect(report.get('isEditor') is False and report.get('runtimePlatform') == request['runtimePlatform'],
            'An editor result is not advanced standalone-player evidence')
    _expect(type(report.get('skipped')) is int and report['skipped'] == 0, 'Skipped advanced checks cannot pass')
    for key in ('graphicsDevice', 'graphicsDeviceVersion', 'operatingSystem'):
        _expect(isinstance(report.get(key), str) and 0 < len(report[key]) <= 512, f'Missing {key}')

    source = plan['source']; sentinel = plan['sentinel']
    comparisons = source['sprites'] * source['levelsPerSprite'] + sentinel['sprites'] * sentinel['levelsPerSprite']
    counts = {
        'banks': source['banks'], 'sprites': source['sprites'],
        'cpuComparisons': comparisons, 'gpuComparisons': comparisons,
        'shaderComparisons': comparisons * 3, 'bindingComparisons': source['sprites'] + sentinel['sprites'],
        'overlapComparisons': 3, 'overlapByteTolerance': 1,
    }
    for key, count in counts.items():
        _expect(type(report.get(key)) is int and report[key] == count, f'Incomplete or changed {key}')

    graphs = report.get('graphResults')
    expected_counts = request['graphCounts']
    _expect(isinstance(graphs, list) and len(graphs) == len(expected_counts), 'Graph result inventory mismatch')
    for item, expected_instances in zip(graphs, expected_counts):
        _expect(isinstance(item, dict), 'Graph result must be an object')
        _expect(item.get('instances') == expected_instances and type(item.get('instances')) is int,
                'Graph instance count mismatch')
        _expect(item.get('uniqueSprites') == min(expected_instances, source['sprites']), 'Graph unique-sprite count mismatch')
        _expect(item.get('banks') == source['banks'], 'Graph bank count mismatch')
        _expect(item.get('exactPixels') is True, 'Graph framebuffer did not match source mips exactly')
        for key in ('expectedSha256', 'actualSha256'):
            value = item.get(key)
            _expect(isinstance(value, str) and re.fullmatch(r'[a-f0-9]{64}', value), f'Invalid graph {key}')
        _expect(item['expectedSha256'] == item['actualSha256'], 'Graph output hash mismatch')
        for key, low, high in (
            ('drawCalls', 1, expected_instances), ('mip', 0, source['levelsPerSprite'] - 1),
            ('width', 1, 2048), ('height', 1, 2048), ('pixelsCompared', 1, 2048 * 2048),
            ('submitMicroseconds', 0, 60 * 60 * 1_000_000),
            ('readbackMicroseconds', 0, 60 * 60 * 1_000_000),
            ('totalMicroseconds', 0, 60 * 60 * 1_000_000),
        ):
            _positive(item.get(key), f'Graph {key}', low, high)
        columns = __import__('math').ceil(expected_instances ** 0.5)
        rows = (expected_instances + columns - 1) // columns
        expected_mip = 0
        tile = source['nativeSize']
        while expected_mip + 1 < source['levelsPerSprite'] and (columns * tile > 2048 or rows * tile > 2048):
            expected_mip += 1; tile = source['nativeSize'] >> expected_mip
        _expect(item['mip'] == expected_mip and item['width'] == columns * tile and item['height'] == rows * tile,
                'Graph mip/framebuffer geometry mismatch')
        _expect(item['pixelsCompared'] == item['width'] * item['height'], 'Graph compared-pixel geometry mismatch')


def run_advanced_qualification(editor: Path, bundle: Path, output: Path, *, confirm_public: bool = False,
                               profile: str = 'windows-d3d11-il2cpp-linear',
                               editor_version: str = '6000.0.62f1', graph_counts=None,
                               build_timeout: int = 3600, player_timeout: int = 900) -> dict:
    _expect(confirm_public is True, 'Explicit --confirm-public consent required')
    _expect(profile in PROFILES, 'Unsupported advanced Unity profile')
    _expect(platform.system() == PROFILES[profile]['host'], 'Advanced build-and-run profile must match the current OS')
    _version(editor_version)
    _positive(build_timeout, 'Build timeout', 30, 7200)
    _positive(player_timeout, 'Player timeout', 30, 1800)
    editor = _no_links(editor)
    _expect(editor.is_file(), 'Installed Unity executable required; no successful skip')
    output = _new_output(output, (_no_links(bundle), PACKAGE, editor.parent))
    plan = prepare_advanced_project(bundle, output, confirm_public=True, profile=profile,
                                    editor_version=editor_version, graph_counts=graph_counts)
    try:
        request = plan['request']; project = output / 'project'; p = PROFILES[profile]
        env = {key: value for key, value in os.environ.items()
               if not key.startswith(('BYTEFABLES_ADVANCED_', 'BYTEFABLES_PLAYER_', 'BYTEFABLES_UNITY_'))}
        env['BYTEFABLES_ADVANCED_REQUEST'] = str(project / 'advanced-player-request.json')
        command = [str(editor), '-batchmode', '-projectPath', str(project), '-buildTarget', p['cli'],
                   '-standaloneBuildSubtarget', 'Player',
                   '-executeMethod', 'ByteFables.Textures.Editor.TextureAdvancedBuild.RunFromCommandLine',
                   '-logFile', str(output / 'unity-build.log'), '-quit']
        _execute(command, env, output / 'build-launcher.log', build_timeout)
        build, build_sha = _read_json(_file(output, 'build-result.json'), 1024 * 1024)
        check_advanced_build_report(build, request)
        executable = _no_links(Path(request['buildPath']))
        _expect(executable.is_file(), 'Advanced build reported success without a player executable')
        inventory = artifact_inventory(output / 'player')
        (output / 'player-inventory.json').write_bytes(_json(inventory))

        env.pop('BYTEFABLES_ADVANCED_REQUEST')
        env['BYTEFABLES_ADVANCED_RUN_ID'] = request['runId']
        env['BYTEFABLES_ADVANCED_REPORT'] = str(output / 'player-result.json')
        _execute([str(executable), '-batchmode', p['launch'], '-logFile', str(output / 'unity-player.log')],
                 env, output / 'player-launcher.log', player_timeout)
        report, player_sha = _read_json(_file(output, 'player-result.json'), 2 * 1024 * 1024)
        check_advanced_player_report(report, plan)
        _expect(artifact_inventory(output / 'player') == inventory, 'Built advanced player changed during qualification')
        receipt = {
            'schema': RECEIPT_SCHEMA, 'status': 'passed', 'runId': request['runId'],
            'manifestSha256': request['manifestSha256'], 'targetProfile': profile,
            'buildReportSha256': build_sha, 'playerReportSha256': player_sha,
            'playerArtifactSha256': inventory['sha256'], 'playerExecuted': True,
            'gpuExecuted': True, 'graphExecuted': True, 'result': report,
            'warning': 'Unsigned execution evidence for this exact IL2CPP/Linear build/device; not universal compatibility or FPS evidence.',
        }
        with (output / 'report.json').open('xb') as stream:
            stream.write(_json(receipt))
        return receipt
    except Exception as exc:
        (output / 'report.json').unlink(missing_ok=True)
        _failure(output, exc)
        raise
