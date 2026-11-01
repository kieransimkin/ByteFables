"""Build and execute a real desktop Unity player in a fresh, isolated project.

Preparation, building and GPU qualification are separate states. Only a checked
build AND a completed player run publish report.json. No Unity license handling,
network fetching, shell command construction or successful GPU skips are used.
"""
from __future__ import annotations

import hashlib
import os
from pathlib import Path
import platform
import re
import secrets
import shutil
import signal
import subprocess
import sys

from tools.artwork_asset_bundle import _expect, _file, _no_links
from tools.artwork_native_benchmark import _json, _read_json, _sha
from tools.artwork_transparent_bundle import _new_output, _failure
from tools.artwork_unity_stage import stage_unity_bundle, verify_unity_stage
from tools.artwork_unity_qualification import PACKAGE, ROOT

SCHEMA = 'bytefables.unity-player-qualification.v1'
TARGETS = {
    'windows-d3d11': ('Windows', 'StandaloneWindows64', 'WindowsPlayer', 'Direct3D11', '-force-d3d11', 'ByteFablesPlayer.exe', 'win64', 'Mono', 'Gamma'),
    'linux-vulkan': ('Linux', 'StandaloneLinux64', 'LinuxPlayer', 'Vulkan', '-force-vulkan', 'ByteFablesPlayer.x86_64', 'linux64', 'Mono', 'Gamma'),
    'windows-d3d11-il2cpp-linear': ('Windows', 'StandaloneWindows64', 'WindowsPlayer', 'Direct3D11', '-force-d3d11', 'ByteFablesPlayer.exe', 'win64', 'IL2CPP', 'Linear'),
    'linux-vulkan-il2cpp-linear': ('Linux', 'StandaloneLinux64', 'LinuxPlayer', 'Vulkan', '-force-vulkan', 'ByteFablesPlayer.x86_64', 'linux64', 'IL2CPP', 'Linear'),
}
MAX_BUILD_BYTES = 2 * 1024 * 1024 * 1024


def _version(value: str) -> None:
    _expect(isinstance(value, str) and re.fullmatch(r'6000\.\d+\.\d+[fp]\d+', value) is not None,
            'An exact Unity 6 editor version is required')


def _positive(value: object, label: str, low: int, high: int) -> None:
    _expect(type(value) is int and low <= value <= high, f'{label} outside {low}..{high}')


def prepare_player_project(bundle: Path, output: Path, *, confirm_public: bool = False,
                           target: str = 'windows-d3d11', editor_version: str = '6000.0.62f1') -> dict:
    """Prepare only: no editor or player process is started and no pass is claimed."""
    _expect(confirm_public is True, 'Explicit --confirm-public consent required')
    _expect(target in TARGETS, 'Unsupported player target')
    _version(editor_version)
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
        # This is an explicit synthetic orientation/alpha fixture, not another public identity corpus.
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
        entry = TARGETS[target]
        request = {
            'schema': 'bytefables.unity-player-request.v1', 'runId': secrets.token_hex(16),
            'editorVersion': editor_version, 'target': entry[1], 'runtimePlatform': entry[2],
            'graphicsApi': entry[3], 'scriptingBackend': entry[7], 'colourSpace': entry[8],
            'renderPipeline': 'BuiltIn', 'manifestSha256': actual['manifestSha256'],
            'sentinelManifestSha256': sentinel['manifestSha256'],
            'buildPath': str(output / 'player' / entry[5]),
            'buildReportPath': str(output / 'build-result.json'),
        }
        (project / 'player-request.json').write_bytes(_json(request))
        plan = {'schema': 'bytefables.unity-player-plan.v1', 'status': 'prepared',
                'playerExecuted': False, 'gpuExecuted': False, 'targetProfile': target,
                'request': request, 'source': actual, 'sentinel': sentinel}
        (output / 'plan.json').write_bytes(_json(plan))
        return plan
    except Exception as exc:
        _failure(output, exc)
        raise


def _base_report(report: dict, schema: str, request: dict) -> None:
    _expect(isinstance(report, dict) and report.get('schema') == schema and report.get('status') == 'passed',
            'No successful completed Unity report')
    for key in ('runId', 'editorVersion', 'manifestSha256', 'sentinelManifestSha256', 'graphicsApi',
                'scriptingBackend', 'colourSpace', 'renderPipeline'):
        _expect(report.get(key) == request[key], f'Unity report {key} mismatch')
    _positive(report.get('elapsedMilliseconds'), 'Elapsed milliseconds', 0, 24 * 60 * 60 * 1000)
    _expect(not report.get('error'), 'Successful report must not carry an error')


def check_build_report(report: dict, request: dict) -> None:
    _base_report(report, 'bytefables.unity-player-build.v1', request)
    _expect(report.get('target') == request['target'] and report.get('buildSucceeded') is True,
            'Wrong or incomplete Unity player build')
    _expect(report.get('developmentBuild') is False and type(report.get('errors')) is int and report['errors'] == 0,
            'Expected a non-development build with no build errors')
    _positive(report.get('totalSize'), 'Build size', 1, MAX_BUILD_BYTES)


def check_player_report(report: dict, plan: dict) -> None:
    request = plan['request']
    _base_report(report, SCHEMA, request)
    for name in ('playerExecuted', 'gpuExecuted', 'serializedAssetsExecuted', 'syntheticSentinelsExecuted', 'disposalExecuted'):
        _expect(report.get(name) is True, f'Player did not execute {name}')
    _expect(report.get('isEditor') is False and report.get('runtimePlatform') == request['runtimePlatform'],
            'An editor result is not standalone-player evidence')
    _expect(type(report.get('skipped')) is int and report['skipped'] == 0, 'Skipped player checks cannot pass')
    for key in ('graphicsDevice', 'graphicsDeviceVersion', 'operatingSystem'):
        _expect(isinstance(report.get(key), str) and 0 < len(report[key]) <= 512, f'Missing {key}')
    source = plan['source']; sentinel = plan['sentinel']
    comparisons = source['sprites'] * source['levelsPerSprite'] + sentinel['sprites'] * sentinel['levelsPerSprite']
    counts = {'banks': source['banks'], 'sprites': source['sprites'],
              'cpuComparisons': comparisons, 'gpuComparisons': comparisons,
              'shaderComparisons': comparisons * 3, 'bindingComparisons': source['sprites'] + sentinel['sprites'],
              'overlapComparisons': 3, 'overlapByteTolerance': 1}
    for key, count in counts.items():
        _expect(type(report.get(key)) is int and report[key] == count, f'Incomplete or changed {key}')


def artifact_inventory(root: Path) -> dict:
    """Hash the entire built player, not just its launcher executable."""
    root = _no_links(root)
    _expect(root.is_dir(), 'Missing standalone-player output')
    files = []; total = 0
    for path in sorted(root.rglob('*')):
        _no_links(path)
        if path.is_dir():
            continue
        _expect(path.is_file(), 'Non-regular build artifact')
        _expect(len(files) < 20000, 'Too many player artifacts')
        size = path.stat().st_size
        total += size
        _expect(total <= MAX_BUILD_BYTES, 'Player artifacts exceed 2 GiB budget')
        digest = hashlib.sha256(); observed = 0
        with path.open('rb') as stream:
            for block in iter(lambda: stream.read(1024 * 1024), b''):
                observed += len(block)
                _expect(observed <= size, 'Build artifact grew while hashing')
                digest.update(block)
        _expect(observed == size, 'Build artifact changed while hashing')
        files.append({'path': path.relative_to(root).as_posix(), 'byteLength': size, 'sha256': digest.hexdigest()})
    _expect(bool(files) and total > 0, 'Empty player artifact directory')
    return {'sha256': _sha(_json(files)), 'byteLength': total, 'files': files}


def _execute(command: list[str], env: dict, log: Path, timeout: int) -> None:
    """Own only the launched process group; terminate its tree on timeout."""
    kwargs = {'start_new_session': True} if os.name != 'nt' else {'creationflags': subprocess.CREATE_NEW_PROCESS_GROUP}
    with log.open('xb') as stream:
        process = subprocess.Popen(command, env=env, stdout=stream, stderr=subprocess.STDOUT, **kwargs)
        try:
            code = process.wait(timeout=timeout)
        except BaseException:
            if os.name == 'nt':
                try:
                    subprocess.run(['taskkill', '/PID', str(process.pid), '/T', '/F'],
                                   stdout=stream, stderr=subprocess.STDOUT, check=False, timeout=15)
                finally:
                    if process.poll() is None:
                        process.kill()
            else:
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
            process.wait(timeout=15)
            raise
    _expect(code == 0, f'Process exited with code {code}; see {log.name}')


def run_player_qualification(editor: Path, bundle: Path, output: Path, *, confirm_public: bool = False,
                             target: str = 'windows-d3d11', editor_version: str = '6000.0.62f1',
                             build_timeout: int = 1800, player_timeout: int = 600) -> dict:
    _expect(confirm_public is True, 'Explicit --confirm-public consent required')
    _expect(target in TARGETS, 'Unsupported player target')
    _expect(platform.system() == TARGETS[target][0], 'Build-and-run target must match the current OS')
    _version(editor_version)
    _positive(build_timeout, 'Build timeout', 30, 3600)
    _positive(player_timeout, 'Player timeout', 30, 1800)
    editor = _no_links(editor)
    _expect(editor.is_file(), 'Installed Unity executable required; no successful skip')
    # Do not allow outputs to consume or overwrite the installed editor.
    output = _new_output(output, (_no_links(bundle), PACKAGE, editor.parent))
    plan = prepare_player_project(bundle, output, confirm_public=True, target=target, editor_version=editor_version)
    try:
        request = plan['request']; project = output / 'project'
        env = {key: value for key, value in os.environ.items()
               if not key.startswith(('BYTEFABLES_PLAYER_', 'BYTEFABLES_UNITY_'))}
        env['BYTEFABLES_PLAYER_REQUEST'] = str(project / 'player-request.json')
        command = [str(editor), '-batchmode', '-projectPath', str(project), '-buildTarget', TARGETS[target][6],
                   '-standaloneBuildSubtarget', 'Player',
                   '-executeMethod', 'ByteFables.Textures.Editor.TexturePlayerBuild.RunFromCommandLine',
                   '-logFile', str(output / 'unity-build.log'), '-quit']
        _execute(command, env, output / 'build-launcher.log', build_timeout)
        build, build_sha = _read_json(_file(output, 'build-result.json'), 1024 * 1024)
        check_build_report(build, request)
        executable = _no_links(Path(request['buildPath']))
        _expect(executable.is_file(), 'Build reported success without a player executable')
        inventory = artifact_inventory(output / 'player')
        (output / 'player-inventory.json').write_bytes(_json(inventory))
        env.pop('BYTEFABLES_PLAYER_REQUEST')
        env['BYTEFABLES_PLAYER_RUN_ID'] = request['runId']
        env['BYTEFABLES_PLAYER_REPORT'] = str(output / 'player-result.json')
        # No -quit: the component exits only after all comparisons and report flush.
        # No -nographics: a Null device is a failure, not a headless pass.
        _execute([str(executable), '-batchmode', TARGETS[target][4],
                  '-logFile', str(output / 'unity-player.log')], env, output / 'player-launcher.log', player_timeout)
        report, player_sha = _read_json(_file(output, 'player-result.json'), 1024 * 1024)
        check_player_report(report, plan)
        _expect(artifact_inventory(output / 'player') == inventory, 'Built player changed during qualification')
        receipt = {'schema': 'bytefables.unity-player-receipt.v1', 'status': 'passed',
                   'runId': request['runId'], 'manifestSha256': request['manifestSha256'],
                   'targetProfile': target, 'buildReportSha256': build_sha,
                   'playerReportSha256': player_sha, 'playerArtifactSha256': inventory['sha256'],
                   'playerExecuted': True, 'gpuExecuted': True, 'result': report,
                   'warning': 'Unsigned execution evidence for this build/device, not authenticity or universal compatibility.'}
        with (output / 'report.json').open('xb') as stream:
            stream.write(_json(receipt))
        return receipt
    except Exception as exc:
        (output / 'report.json').unlink(missing_ok=True)
        _failure(output, exc)
        raise
