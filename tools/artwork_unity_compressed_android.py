"""Build, install and execute ByteFables compressed-texture qualification on Android.

This runner requires a physical ADB device. It does not persist the device serial
in evidence. The APK is IL2CPP/ARM64/Linear and uses the exact requested Vulkan
ASTC4x4 or GLES3 ETC2_RGBA8 path with no RGBA fallback.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess
import time

from tools.artwork_asset_bundle import _expect, _file, _no_links
from tools.artwork_native_benchmark import _json, _read_json
from tools.artwork_transparent_bundle import _new_output, _failure
from tools.artwork_unity_compressed_device import prepare_compressed_project, PROFILES
from tools.artwork_unity_player import _execute, _positive, _version
from tools.artwork_unity_qualification import PACKAGE

BUILD_SCHEMA='bytefables.unity-compressed-android-build.v1'
PLAYER_SCHEMA='bytefables.unity-compressed-android-qualification.v1'
RECEIPT_SCHEMA='bytefables.unity-compressed-android-receipt.v1'
PACKAGE_ID='com.bytefables.compressedqualification'
REMOTE_REPORT=f'/sdcard/Android/data/{PACKAGE_ID}/files/bytefables-compressed-android-result.json'
ANDROID_PROFILES=('android-vulkan-astc4x4','android-gles3-etc2rgba8')


def _sha_file(path:Path)->str:
    h=hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk)
    return h.hexdigest()


def _run(command:list[str],*,timeout:int=60,check:bool=True)->subprocess.CompletedProcess:
    result=subprocess.run(command,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,timeout=timeout,check=False)
    if check and result.returncode!=0:
        raise ValueError(f"Command failed ({result.returncode}): {' '.join(command[:5])}\n{(result.stderr or result.stdout)[-3000:]}")
    return result


def _adb(adb:Path,args:list[str],serial:str|None=None,*,timeout:int=60,check:bool=True)->subprocess.CompletedProcess:
    command=[str(adb)]
    if serial:command += ['-s',serial]
    command += args
    return _run(command,timeout=timeout,check=check)


def select_physical_device(adb:Path,serial:str|None=None)->str:
    adb=_no_links(adb);_expect(adb.is_file(),'Concrete adb executable required')
    result=_adb(adb,['devices','-l'],timeout=30)
    devices=[]
    for line in result.stdout.splitlines()[1:]:
        if '\tdevice' in line:devices.append(line.split('\t',1)[0].strip())
    if serial is None:
        _expect(len(devices)==1,'Exactly one attached ADB device is required when --device-serial is omitted')
        selected=devices[0]
    else:
        _expect(serial in devices,'Requested ADB device is not attached in device state');selected=serial
    qemu=_adb(adb,['shell','getprop','ro.kernel.qemu'],selected,timeout=15).stdout.strip()
    boot_qemu=_adb(adb,['shell','getprop','ro.boot.qemu'],selected,timeout=15).stdout.strip()
    _expect(qemu!='1' and boot_qemu!='1','Android emulator is not real-device qualification')
    return selected


def check_build_report(report:dict,request:dict)->None:
    _expect(isinstance(report,dict) and report.get('schema')==BUILD_SCHEMA and report.get('status')=='passed','No successful Android compressed build report')
    for key in ('runId','editorVersion','profile','target','graphicsApi','formatId','scriptingBackend','colourSpace','renderPipeline','gpuManifestSha256','referenceManifestSha256'):
        _expect(report.get(key)==request[key],f'Android build {key} mismatch')
    _expect(report.get('packageId')==PACKAGE_ID and 'ARM64' in str(report.get('architecture','')),'Android package/architecture mismatch')
    _expect(report.get('buildSucceeded') is True and report.get('developmentBuild') is False and type(report.get('errors')) is int and report['errors']==0,'Android build incomplete')
    _positive(report.get('totalSize'),'Android build size',1,2*1024*1024*1024);_positive(report.get('elapsedMilliseconds'),'Android build elapsed',0,24*60*60*1000)


def _finite(value,label):
    import math
    _expect(type(value) in (int,float) and not isinstance(value,bool) and math.isfinite(value),f'Invalid {label}')


def check_player_report(report:dict,plan:dict)->None:
    q=plan['request'];_expect(isinstance(report,dict) and report.get('schema')==PLAYER_SCHEMA and report.get('status')=='passed','No successful Android device report')
    for key in ('runId','editorVersion','profile','graphicsApi','formatId','gpuManifestSha256','referenceManifestSha256','sourceManifestSha256'):
        _expect(report.get(key)==q[key],f'Android player {key} mismatch')
    _expect(report.get('runtimePlatform')=='Android' and report.get('packageId')==PACKAGE_ID and report.get('isEditor') is False,'Wrong Android runtime/package')
    _expect(report.get('scriptingBackend')=='IL2CPP' and report.get('colourSpace')=='Linear' and report.get('renderPipeline')=='BuiltIn','Android player backend/colour/pipeline mismatch')
    for key in ('playerExecuted','gpuExecuted','formatSupported','arraySupported','readbackExecuted','shaderExecuted'):_expect(report.get(key) is True,f'Missing Android device evidence: {key}')
    _expect(type(report.get('skipped')) is int and report['skipped']==0,'Skipped Android checks cannot pass')
    _expect(report.get('readbackComparisons')==q['spriteCount']*q['levelCount'],'Android readback coverage mismatch')
    _expect(report.get('shaderComparisons')==min(16,q['spriteCount'])*q['levelCount']*3,'Android shader coverage mismatch')
    _expect(report.get('orientation') in ('bottom-up','top-left','mixed','ambiguous') and type(report.get('orientationComparisons')) is int and report['orientationComparisons']>=1,'Invalid Android orientation evidence')
    _expect(report.get('productionQualified') is (report.get('orientation')=='bottom-up'),'Android production flag must match established bottom-up orientation')
    for key in ('readbackMeanAbsoluteError','readbackPsnrDb','shaderMeanAbsoluteError','shaderPsnrDb','topLeftMeanAbsoluteError','bottomUpMeanAbsoluteError'):_finite(report.get(key),key)
    for key in ('graphicsDevice','graphicsDeviceVersion','operatingSystem','deviceModel'):_expect(isinstance(report.get(key),str) and report[key],f'Missing Android {key}')


def _write_logcat(adb:Path,serial:str,output:Path)->None:
    try:
        result=_adb(adb,['logcat','-d','-v','threadtime'],serial,timeout=30,check=False)
        text=(result.stdout or '')+(('\nSTDERR\n'+result.stderr) if result.stderr else '')
        output.write_text(text[-8*1024*1024:],encoding='utf-8',errors='replace')
    except Exception as exc:output.write_text(f'logcat collection failed: {exc}\n',encoding='utf-8')


def run_android_qualification(editor:Path,adb:Path,gpu_bundle:Path,reference_bundle:Path,output:Path,*,confirm_public:bool=False,
                              profile:str='android-vulkan-astc4x4',editor_version:str='6000.0.62f1',device_serial:str|None=None,
                              build_timeout:int=5400,device_timeout:int=900,keep_installed:bool=False)->dict:
    _expect(confirm_public is True,'Explicit --confirm-public consent required');_expect(profile in ANDROID_PROFILES,'Unsupported Android compressed profile');_version(editor_version)
    _positive(build_timeout,'Android build timeout',30,7200);_positive(device_timeout,'Android device timeout',30,1800)
    editor=_no_links(editor);adb=_no_links(adb);_expect(editor.is_file(),'Installed Unity executable required');_expect(adb.is_file(),'adb executable required')
    output=_new_output(output,(_no_links(gpu_bundle),_no_links(reference_bundle),PACKAGE,editor.parent,adb.parent))
    plan=prepare_compressed_project(gpu_bundle,reference_bundle,output,confirm_public=True,profile=profile,editor_version=editor_version)
    selected=None
    try:
        q=plan['request'];project=output/'project';env={k:v for k,v in os.environ.items() if not k.startswith(('BYTEFABLES_COMPRESSED_','BYTEFABLES_UNITY_'))}
        env['BYTEFABLES_COMPRESSED_REQUEST']=str(project/'compressed-device-request.json')
        command=[str(editor),'-batchmode','-projectPath',str(project),'-buildTarget','Android','-executeMethod','ByteFables.Textures.Editor.CompressedTextureAndroidBuild.RunFromCommandLine','-logFile',str(output/'unity-android-build.log'),'-quit']
        _execute(command,env,output/'android-build-launcher.log',build_timeout)
        build,build_sha=_read_json(_file(output,'build-result.json'),1024*1024);check_build_report(build,q)
        apk=_no_links(Path(q['buildPath']));_expect(apk.is_file(),'Android build reported success without APK');apk_sha=_sha_file(apk)
        selected=select_physical_device(adb,device_serial)
        _adb(adb,['uninstall',PACKAGE_ID],selected,timeout=60,check=False)
        _adb(adb,['install','-r','-g',str(apk)],selected,timeout=180)
        _adb(adb,['shell','rm','-f',REMOTE_REPORT],selected,timeout=30,check=False)
        _adb(adb,['logcat','-c'],selected,timeout=30,check=False)
        launch=_adb(adb,['shell','monkey','-p',PACKAGE_ID,'-c','android.intent.category.LAUNCHER','1'],selected,timeout=60)
        _expect('Events injected: 1' in launch.stdout or 'Monkey finished' in launch.stdout or launch.returncode==0,'Could not launch Android qualification app')
        local_report=output/'player-result.json';deadline=time.monotonic()+device_timeout
        while time.monotonic()<deadline:
            pulled=_adb(adb,['pull',REMOTE_REPORT,str(local_report)],selected,timeout=30,check=False)
            if pulled.returncode==0 and local_report.is_file():break
            time.sleep(2)
        _expect(local_report.is_file(),'Android qualification report was not produced before timeout')
        player,player_sha=_read_json(_file(output,'player-result.json'),2*1024*1024);check_player_report(player,plan)
        _expect(_sha_file(apk)==apk_sha,'Android APK changed during qualification')
        receipt={'schema':RECEIPT_SCHEMA,'status':'passed','runId':q['runId'],'profile':profile,'formatId':q['formatId'],
                 'productionQualified':player['productionQualified'],'orientation':player['orientation'],'apkSha256':apk_sha,
                 'buildReportSha256':build_sha,'playerReportSha256':player_sha,'deviceExecuted':True,'physicalDeviceRequired':True,
                 'result':player,'warning':'Evidence is bound to this APK/device/API. Device serial is intentionally not persisted.'}
        with (output/'report.json').open('xb') as f:f.write(_json(receipt))
        return receipt
    except Exception as exc:
        (output/'report.json').unlink(missing_ok=True);_failure(output,exc);raise
    finally:
        if selected:
            _write_logcat(adb,selected,output/'android-logcat.log')
            if not keep_installed:_adb(adb,['uninstall',PACKAGE_ID],selected,timeout=60,check=False)
