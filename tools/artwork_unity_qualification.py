"""Run the actual Unity editor in an isolated project; missing editor/GPU is failure."""
from __future__ import annotations
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
from tools.artwork_asset_bundle import _expect, _no_links, _file
from tools.artwork_native_benchmark import _json, _read_json
from tools.artwork_transparent_bundle import _new_output, _failure
from tools.artwork_unity_stage import stage_unity_bundle

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT/'integrations/unity/com.bytefables.textures'


def check_report(report: dict, expected_sha: str, version: str, sprites: int, banks: int, levels: int) -> None:
    _expect(isinstance(report,dict) and report.get('schema') == 'bytefables.unity-qualification.v1' and
            report.get('status') == 'passed' and report.get('unityExecuted') is True and
            report.get('gpuExecuted') is True and report.get('syntheticSentinelsExecuted') is True and
            type(report.get('skipped')) is int and report['skipped'] == 0, 'Unity qualification did not execute all gates')
    _expect(report.get('editorVersion') == version and report.get('manifestSha256') == expected_sha and
            report.get('sprites') == sprites and report.get('banks') == banks, 'Unity report input/environment mismatch')
    _expect(report.get('graphicsApi') not in (None,'','Null') and isinstance(report.get('graphicsDevice'),str) and
            bool(report['graphicsDevice']), 'No graphics device reported')
    comparisons = sprites*levels + 4*5
    _expect(report.get('cpuComparisons') == comparisons and report.get('gpuComparisons') == comparisons and
            report.get('shaderComparisons') == comparisons*3 and report.get('overlapComparisons') == 3 and
            report.get('overlapByteTolerance') == 1 and type(report.get('elapsedMilliseconds')) is int and
            report['elapsedMilliseconds'] >= 0, 'Incomplete or changed Unity readback coverage')


def run_qualification(editor: Path, bundle: Path, output: Path, *, confirm_public: bool = False,
                      editor_version: str = '6000.0.62f1', timeout_seconds: int = 1200) -> dict:
    _expect(confirm_public is True, 'Explicit --confirm-public consent required')
    editor = _no_links(editor)
    _expect(editor.is_file(), 'Unity executable is required; no skipped success')
    _expect(re.fullmatch(r'6000\.\d+\.\d+[fp]\d+', editor_version) is not None, 'Explicit Unity 6 editor version required')
    _expect(type(timeout_seconds) is int and 30 <= timeout_seconds <= 3600, 'Timeout outside 30..3600 seconds')
    source = _no_links(bundle); output = _new_output(output,(source,PACKAGE))
    output.mkdir(parents=True)
    try:
        project = output/'project'; (project/'Assets').mkdir(parents=True)
        (project/'Packages').mkdir(); (project/'ProjectSettings').mkdir()
        for path in PACKAGE.rglob('*'): _no_links(path)
        shutil.copytree(PACKAGE,project/'Packages/com.bytefables.textures')
        # Embedded package: no extra Unity packages or test-framework version guesses.
        (project/'Packages/manifest.json').write_bytes(_json({'dependencies':{}}))
        (project/'ProjectSettings/ProjectVersion.txt').write_text(f'm_EditorVersion: {editor_version}\n',encoding='utf-8')
        stage = stage_unity_bundle(source,project/'Assets/ByteFablesFixture',confirm_public=True)
        sys.path.insert(0,str(ROOT/'tests/helpers'))
        from artwork_unity_fixture import make_fixture
        fixture = make_fixture(output/'synthetic-source')
        stage_unity_bundle(fixture,project/'Assets/ByteFablesSentinel',confirm_public=True)
        raw_report = output/'unity-result.json'; log = output/'unity-editor.log'
        env = dict(os.environ, BYTEFABLES_UNITY_REPORT=str(raw_report),
                   BYTEFABLES_UNITY_DESCRIPTOR='Assets/ByteFablesFixture/artwork.bftextures',
                   BYTEFABLES_UNITY_SENTINEL='Assets/ByteFablesSentinel/artwork.bftextures',
                   BYTEFABLES_UNITY_EDITOR_VERSION=editor_version)
        command = [str(editor), '-batchmode', '-projectPath', str(project), '-executeMethod',
                   'ByteFables.Textures.Editor.TextureQualification.RunFromCommandLine', '-logFile', str(log), '-quit']
        # Synchronous executeMethod; deliberately no -nographics or fallback renderer.
        with (output/'launcher.log').open('wb') as transcript:
            result = subprocess.run(command, env=env, stdout=transcript, stderr=subprocess.STDOUT,
                                    timeout=timeout_seconds, check=False)
        _expect(result.returncode == 0, f'Unity exited with code {result.returncode}; see unity-editor.log')
        report, _ = _read_json(_file(output,'unity-result.json'),1024*1024)
        check_report(report,stage['manifestSha256'],editor_version,stage['sprites'],stage['banks'],stage['levelsPerSprite'])
        (output/'report.json').write_bytes(_json(report)); return report
    except Exception as exc:
        _failure(output,exc); raise
