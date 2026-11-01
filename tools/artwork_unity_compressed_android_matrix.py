"""Run both ByteFables Android compressed-texture profiles on one physical device.

The device serial is used only in-process and is never persisted.  Each profile
retains its own existing qualification receipt; this module adds a combined
same-device matrix receipt and continues to the second profile if the first fails
so partial hardware evidence is not discarded.
"""
from __future__ import annotations

import json
from pathlib import Path

from tools.artwork_asset_bundle import _expect, _no_links
from tools.artwork_native_benchmark import _json
from tools.artwork_transparent_bundle import _new_output, _failure
from tools.artwork_unity_compressed_android import (
    ANDROID_PROFILES, run_android_qualification, select_physical_device,
)

SCHEMA = 'bytefables.unity-compressed-android-matrix.v1'
PROFILES = tuple(ANDROID_PROFILES)


def _profile_summary(profile: str, receipt: dict) -> dict:
    result=receipt['result']
    return {
        'profile':profile,'status':'passed','graphicsApi':result['graphicsApi'],'formatId':result['formatId'],
        'orientation':result['orientation'],'productionQualified':bool(result['productionQualified']),
        'readbackMeanAbsoluteError':result['readbackMeanAbsoluteError'],'readbackPsnrDb':result['readbackPsnrDb'],
        'shaderMeanAbsoluteError':result['shaderMeanAbsoluteError'],'shaderPsnrDb':result['shaderPsnrDb'],
        'graphicsDevice':result['graphicsDevice'],'graphicsDeviceVersion':result['graphicsDeviceVersion'],
        'operatingSystem':result['operatingSystem'],'deviceModel':result['deviceModel'],
        'apkSha256':receipt['apkSha256'],'playerReportSha256':receipt['playerReportSha256'],
    }


def validate_matrix_report(report: dict) -> dict:
    _expect(isinstance(report,dict) and report.get('schema')==SCHEMA,'Invalid Android matrix report')
    _expect(report.get('status') in ('passed','failed'),'Invalid Android matrix status')
    _expect(report.get('samePhysicalDevice') is True and report.get('deviceSerialPersisted') is False,'Android matrix privacy/device binding mismatch')
    records=report.get('profiles');_expect(isinstance(records,list) and len(records)==len(PROFILES),'Android matrix profile inventory mismatch')
    _expect([x.get('profile') for x in records]==list(PROFILES),'Android matrix profile order mismatch')
    passed=[x for x in records if x.get('status')=='passed']
    _expect(report.get('completedProfiles')==len(passed),'Android matrix completed count mismatch')
    _expect(report.get('allProfilesExecuted') is (len(passed)==len(PROFILES)),'Android matrix execution flag mismatch')
    if passed:
        identity={(x.get('deviceModel'),x.get('operatingSystem'),x.get('graphicsDevice')) for x in passed}
        _expect(len(identity)==1,'Android matrix receipts do not describe the same physical device class/GPU')
    qualified=sum(1 for x in passed if x.get('productionQualified') is True)
    _expect(report.get('productionQualifiedProfiles')==qualified,'Android matrix qualification count mismatch')
    _expect(report.get('allProfilesProductionQualified') is (qualified==len(PROFILES)),'Android matrix production flag mismatch')
    if report['status']=='passed':_expect(report['allProfilesExecuted'] is True,'Passed Android matrix must execute both profiles')
    return report


def run_android_matrix(editor: Path, adb: Path, gpu_bundle: Path, reference_bundle: Path, output: Path, *,
                       confirm_public: bool=False, editor_version: str='6000.0.62f1', device_serial: str|None=None,
                       build_timeout: int=5400, device_timeout: int=900, keep_installed: bool=False) -> dict:
    _expect(confirm_public is True,'Explicit --confirm-public consent required')
    editor=_no_links(editor);adb=_no_links(adb);gpu=_no_links(gpu_bundle);reference=_no_links(reference_bundle)
    output=_new_output(Path(output),(gpu,reference,editor.parent,adb.parent));output.mkdir(parents=True)
    selected=None;records=[];errors=[]
    try:
        selected=select_physical_device(adb,device_serial)
        for profile in PROFILES:
            profile_output=output/profile
            try:
                receipt=run_android_qualification(editor,adb,gpu,reference,profile_output,confirm_public=True,
                    profile=profile,editor_version=editor_version,device_serial=selected,
                    build_timeout=build_timeout,device_timeout=device_timeout,keep_installed=keep_installed)
                records.append(_profile_summary(profile,receipt))
            except Exception as exc:
                records.append({'profile':profile,'status':'failed','errorType':type(exc).__name__,'message':str(exc)[:2000]})
                errors.append(profile)
        passed=[x for x in records if x['status']=='passed'];qualified=sum(1 for x in passed if x.get('productionQualified') is True)
        report={'schema':SCHEMA,'status':'failed' if errors else 'passed','samePhysicalDevice':True,'deviceSerialPersisted':False,
                'profileOrder':list(PROFILES),'profiles':records,'completedProfiles':len(passed),'allProfilesExecuted':len(passed)==len(PROFILES),
                'productionQualifiedProfiles':qualified,'allProfilesProductionQualified':qualified==len(PROFILES),
                'warning':'Same-device execution matrix. No device serial is persisted; quality/orientation claims apply only to the recorded APK/API/GPU evidence.'}
        validate_matrix_report(report)
        (output/'matrix-result.json').write_bytes(_json(report))
        if errors:
            _failure(output,ValueError('Android matrix failed profiles: '+', '.join(errors)))
            raise ValueError('Android matrix failed profiles: '+', '.join(errors))
        (output/'report.json').write_bytes(_json(report));return report
    except Exception:
        # Profile subdirectories retain their individual receipts/failures.
        raise
