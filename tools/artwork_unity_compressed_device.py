"""Prepare and run real-device Unity qualification for ByteFables GPU block arrays.

Desktop profiles build and launch an isolated IL2CPP/Linear player. Mobile
profiles are preparation/capability contracts only in v1: they intentionally do
not pretend an Android/iOS device was deployed or executed.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import platform
import secrets
import shutil

from tools.artwork_asset_bundle import _expect, _file, _no_links, MAX_REPORT_BYTES
from tools.artwork_native_benchmark import _json, _read_json, _sha
from tools.artwork_transparent_bundle import _new_output, _failure
from tools.artwork_gpu_formats import verify_gpu_bundle
from tools.artwork_ktx2_bundle import verify_ktx2_bundle
from tools.artwork_unity_stage import stage_unity_bundle
from tools.artwork_unity_qualification import PACKAGE
from tools.artwork_unity_player import _execute, artifact_inventory, _positive, _version

SCHEMA='bytefables.unity-compressed-device-qualification.v1'
BUILD_SCHEMA='bytefables.unity-compressed-device-build.v1'
REQUEST_SCHEMA='bytefables.unity-compressed-device-request.v1'
PLAN_SCHEMA='bytefables.unity-compressed-device-plan.v1'
RECEIPT_SCHEMA='bytefables.unity-compressed-device-receipt.v1'

PROFILES={
 'windows-d3d11-bc7':dict(host='Windows',target='StandaloneWindows64',runtime='WindowsPlayer',graphics='Direct3D11',format='bc7',cli='StandaloneWindows64',launch='-force-d3d11',build='ByteFablesCompressed.exe',automated=True),
 'windows-d3d12-bc7':dict(host='Windows',target='StandaloneWindows64',runtime='WindowsPlayer',graphics='Direct3D12',format='bc7',cli='StandaloneWindows64',launch='-force-d3d12',build='ByteFablesCompressed.exe',automated=True),
 'linux-vulkan-bc7':dict(host='Linux',target='StandaloneLinux64',runtime='LinuxPlayer',graphics='Vulkan',format='bc7',cli='StandaloneLinux64',launch='-force-vulkan',build='ByteFablesCompressed.x86_64',automated=True),
 'macos-metal-astc4x4':dict(host='Darwin',target='StandaloneOSX',runtime='OSXPlayer',graphics='Metal',format='astc4x4',cli='StandaloneOSX',launch='-force-metal',build='ByteFablesCompressed.app',automated=True),
 'android-vulkan-astc4x4':dict(host=None,target='Android',runtime='Android',graphics='Vulkan',format='astc4x4',cli='Android',launch=None,build='ByteFablesCompressed.apk',automated=False),
 'android-gles3-etc2rgba8':dict(host=None,target='Android',runtime='Android',graphics='OpenGLES3',format='etc2rgba8',cli='Android',launch=None,build='ByteFablesCompressed.apk',automated=False),
 'ios-metal-astc4x4':dict(host=None,target='iOS',runtime='IPhonePlayer',graphics='Metal',format='astc4x4',cli='iOS',launch=None,build='ByteFablesCompressed-iOS',automated=False),
}


def _copy_tree_verified(source:Path,dest:Path)->None:
    source=_no_links(source);_expect(source.is_dir(),'GPU block source directory required')
    for path in source.rglob('*'):_no_links(path)
    shutil.copytree(source,dest)


def _source_binding(gpu:Path,reference:Path)->tuple[dict,dict,str,str]:
    gpu_result=verify_gpu_bundle(gpu);ref_result=verify_ktx2_bundle(reference)
    gpu_doc,gpu_sha=_read_json(_file(gpu,'manifest.json'),MAX_REPORT_BYTES)
    transport,transport_sha=_read_json(_file(reference,'manifest.json'),MAX_REPORT_BYTES)
    source,source_sha=_read_json(_file(reference,'source-manifest.json'),MAX_REPORT_BYTES)
    _expect(gpu_sha==gpu_result['manifestSha256'] and transport_sha==ref_result['manifestSha256'],'Source changed during qualification preparation')
    _expect(gpu_doc['sourceManifest']['sha256']==source_sha==transport['sourceManifest']['sha256'],'GPU blocks and lossless reference use different source manifests')
    _expect(gpu_doc['nativeSize']==source['nativeSize'] and gpu_doc['spriteCount']==source['spriteCount'] and gpu_doc['levelCount']==source['levelCount'],'GPU/reference geometry mismatch')
    return gpu_doc,source,gpu_sha,transport_sha


def prepare_compressed_project(gpu_bundle:Path,reference_bundle:Path,output:Path,*,confirm_public:bool=False,
                               profile:str='windows-d3d12-bc7',editor_version:str='6000.0.62f1')->dict:
    _expect(confirm_public is True,'Explicit --confirm-public consent required')
    _expect(profile in PROFILES,'Unsupported compressed-device profile');_version(editor_version)
    gpu=_no_links(gpu_bundle);reference=_no_links(reference_bundle);output=_new_output(output,(gpu,reference,PACKAGE));output.mkdir(parents=True)
    try:
        gpu_doc,source,gpu_sha,reference_sha=_source_binding(gpu,reference);p=PROFILES[profile]
        _expect(any(f['id']==p['format'] for f in gpu_doc['formats']),'Requested compressed format absent from bundle')
        project=output/'project'
        for name in ('Assets','Packages','ProjectSettings'):(project/name).mkdir(parents=True)
        for path in PACKAGE.rglob('*'):_no_links(path)
        shutil.copytree(PACKAGE,project/'Packages/com.bytefables.textures')
        (project/'Packages/manifest.json').write_bytes(_json({'dependencies':{}}))
        (project/'ProjectSettings/ProjectVersion.txt').write_text(f'm_EditorVersion: {editor_version}\n',encoding='utf-8')
        streaming=project/'Assets/StreamingAssets';streaming.mkdir()
        _copy_tree_verified(gpu,streaming/'ByteFablesGpuBlocks')
        reference_stage=stage_unity_bundle(reference,streaming/'ByteFablesReference',confirm_public=True)
        run_id=secrets.token_hex(16);build_root=output/'player';build_path=build_root/p['build']
        if p['target']=='StandaloneOSX':launch_path=build_path/'Contents/MacOS/ByteFablesCompressed'
        else:launch_path=build_path
        request={'schema':REQUEST_SCHEMA,'runId':run_id,'editorVersion':editor_version,'profile':profile,
                 'target':p['target'],'runtimePlatform':p['runtime'],'graphicsApi':p['graphics'],'formatId':p['format'],
                 'scriptingBackend':'IL2CPP','colourSpace':'Linear','renderPipeline':'BuiltIn',
                 'gpuManifestSha256':gpu_sha,'referenceManifestSha256':reference_stage['manifestSha256'],
                 'sourceManifestSha256':gpu_doc['sourceManifest']['sha256'],'nativeSize':gpu_doc['nativeSize'],
                 'spriteCount':gpu_doc['spriteCount'],'levelCount':gpu_doc['levelCount'],
                 'buildPath':str(build_path),'launchPath':str(launch_path),'buildReportPath':str(output/'build-result.json'),
                 'automatedDesktop':bool(p['automated'])}
        (project/'compressed-device-request.json').write_bytes(_json(request))
        plan={'schema':PLAN_SCHEMA,'status':'prepared','deviceExecuted':False,'gpuExecuted':False,'profile':profile,
              'mobileDeviceBridgeRequired':not p['automated'],'request':request,
              'source':{'gpuBlocks':gpu_sha,'reference':reference_sha,'sprites':source['spriteCount'],'nativeSize':source['nativeSize']}}
        (output/'plan.json').write_bytes(_json(plan));return plan
    except Exception as exc:
        _failure(output,exc);raise


def _finite(value,label):
    import math
    _expect(type(value) in (int,float) and not isinstance(value,bool) and math.isfinite(value),f'Invalid {label}')


def check_build_report(report:dict,request:dict)->None:
    _expect(isinstance(report,dict) and report.get('schema')==BUILD_SCHEMA and report.get('status')=='passed','No successful compressed-device build report')
    for key in ('runId','editorVersion','profile','target','graphicsApi','formatId','scriptingBackend','colourSpace','renderPipeline','gpuManifestSha256','referenceManifestSha256'):
        _expect(report.get(key)==request[key],f'Compressed build {key} mismatch')
    _expect(report.get('buildSucceeded') is True and report.get('developmentBuild') is False and type(report.get('errors')) is int and report['errors']==0,'Compressed-device build incomplete')
    _positive(report.get('totalSize'),'Build size',1,2*1024*1024*1024);_positive(report.get('elapsedMilliseconds'),'Build elapsed',0,24*60*60*1000)


def check_player_report(report:dict,plan:dict)->None:
    q=plan['request'];_expect(isinstance(report,dict) and report.get('schema')==SCHEMA and report.get('status')=='passed','No completed compressed-device measurement')
    for key in ('runId','editorVersion','profile','graphicsApi','formatId','scriptingBackend','colourSpace','renderPipeline','gpuManifestSha256','referenceManifestSha256','sourceManifestSha256'):
        _expect(report.get(key)==q[key],f'Compressed player {key} mismatch')
    for key in ('playerExecuted','gpuExecuted','formatSupported','arraySupported','readbackExecuted','shaderExecuted'):_expect(report.get(key) is True,f'Missing compressed device evidence: {key}')
    _expect(report.get('runtimePlatform')==q['runtimePlatform'] and report.get('isEditor') is False,'Editor/wrong-platform result is not device evidence')
    _expect(type(report.get('skipped')) is int and report['skipped']==0,'Skipped compressed-device checks cannot pass')
    expected_readbacks=q['spriteCount']*q['levelCount'];expected_shader=min(16,q['spriteCount'])*q['levelCount']*3
    _expect(report.get('readbackComparisons')==expected_readbacks and report.get('shaderComparisons')==expected_shader,'Compressed-device coverage count mismatch')
    _expect(report.get('orientation') in ('bottom-up','top-left','mixed','ambiguous'),'Invalid orientation classification')
    _expect(type(report.get('orientationComparisons')) is int and report['orientationComparisons']>=1,'No asymmetric orientation evidence')
    for key in ('readbackMeanAbsoluteError','readbackPsnrDb','shaderMeanAbsoluteError','shaderPsnrDb','topLeftMeanAbsoluteError','bottomUpMeanAbsoluteError'):_finite(report.get(key),key)
    for key in ('graphicsDevice','graphicsDeviceVersion','operatingSystem'):_expect(isinstance(report.get(key),str) and report[key],f'Missing {key}')
    _expect(report.get('productionQualified') is (report.get('orientation')=='bottom-up'),'Production qualification flag must be tied only to established bottom-up orientation in v1')


def run_compressed_qualification(editor:Path,gpu_bundle:Path,reference_bundle:Path,output:Path,*,confirm_public:bool=False,
                                 profile:str='windows-d3d12-bc7',editor_version:str='6000.0.62f1',
                                 build_timeout:int=3600,player_timeout:int=900)->dict:
    _expect(confirm_public is True,'Explicit --confirm-public consent required');_expect(profile in PROFILES,'Unsupported compressed-device profile')
    p=PROFILES[profile];_expect(p['automated'] is True,'Mobile v1 profiles are preparation/capability contracts only; a device deployment bridge is still required')
    _expect(platform.system()==p['host'],'Compressed build-and-run profile must match current OS');_version(editor_version)
    _positive(build_timeout,'Build timeout',30,7200);_positive(player_timeout,'Player timeout',30,1800)
    editor=_no_links(editor);_expect(editor.is_file(),'Installed Unity executable required; no successful skip')
    output=_new_output(output,(_no_links(gpu_bundle),_no_links(reference_bundle),PACKAGE,editor.parent))
    plan=prepare_compressed_project(gpu_bundle,reference_bundle,output,confirm_public=True,profile=profile,editor_version=editor_version)
    try:
        q=plan['request'];project=output/'project';env={k:v for k,v in os.environ.items() if not k.startswith(('BYTEFABLES_COMPRESSED_','BYTEFABLES_UNITY_'))}
        env['BYTEFABLES_COMPRESSED_REQUEST']=str(project/'compressed-device-request.json')
        command=[str(editor),'-batchmode','-projectPath',str(project),'-buildTarget',p['cli'],'-standaloneBuildSubtarget','Player',
                 '-executeMethod','ByteFables.Textures.Editor.CompressedTextureDeviceBuild.RunFromCommandLine','-logFile',str(output/'unity-build.log'),'-quit']
        _execute(command,env,output/'build-launcher.log',build_timeout)
        build,build_sha=_read_json(_file(output,'build-result.json'),1024*1024);check_build_report(build,q)
        launch=_no_links(Path(q['launchPath']));_expect(launch.is_file(),'Compressed-device build has no launch executable')
        inventory=artifact_inventory(output/'player');(output/'player-inventory.json').write_bytes(_json(inventory))
        env.pop('BYTEFABLES_COMPRESSED_REQUEST');env['BYTEFABLES_COMPRESSED_RUN_ID']=q['runId'];env['BYTEFABLES_COMPRESSED_REPORT']=str(output/'player-result.json')
        args=[str(launch),'-batchmode']
        if p['launch']:args.append(p['launch'])
        args+=['-logFile',str(output/'unity-player.log')]
        _execute(args,env,output/'player-launcher.log',player_timeout)
        player,player_sha=_read_json(_file(output,'player-result.json'),2*1024*1024);check_player_report(player,plan)
        _expect(artifact_inventory(output/'player')==inventory,'Compressed-device player changed during execution')
        receipt={'schema':RECEIPT_SCHEMA,'status':'passed','runId':q['runId'],'profile':profile,'formatId':q['formatId'],
                 'productionQualified':player['productionQualified'],'orientation':player['orientation'],
                 'buildReportSha256':build_sha,'playerReportSha256':player_sha,'playerArtifactSha256':inventory['sha256'],
                 'result':player,'warning':'Real-device measurement for this exact build/GPU/API. Quality metrics are measurements, not universal perceptual thresholds.'}
        with (output/'report.json').open('xb') as f:f.write(_json(receipt))
        return receipt
    except Exception as exc:
        (output/'report.json').unlink(missing_ok=True);_failure(output,exc);raise
