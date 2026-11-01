#!/usr/bin/env python3
"""Required HTTP/CSP/WebGL2 KTX2 readback against the original raw mip arrays.

All native texel-centre comparisons are exact. Fractional LOD/overlap uses only
an explicit <=2-channel-unit tolerance, matching the existing alpha qualification.
Missing browser/GPU support is a failing acceptance gate, never a successful skip.
"""
from __future__ import annotations
import argparse
import base64
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import numpy as np
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from tools.artwork_ktx2_bundle import verify_ktx2_bundle
spec=importlib.util.spec_from_file_location('alpha_smoke_reference',ROOT/'tests/browser/artwork-alpha-textures-smoke.py')
reference=importlib.util.module_from_spec(spec);spec.loader.exec_module(reference)
# Existing independently calculated CPU expectations stay unchanged. Only loading
# the transported bytes differs from the preceding real-GPU qualification.
DRAW=reference.DRAW.replace('globalThis.ByteFablesAlphaTextures','globalThis.ByteFablesKtx2Textures')


def smoke(bundle: Path, source_bundle: Path, executable: str | None=None) -> dict:
    from playwright.sync_api import sync_playwright,expect
    root=Path(bundle).resolve(strict=True);source_root=Path(source_bundle).resolve(strict=True)
    verified=verify_ktx2_bundle(root,source_bundle=source_root)
    source=json.loads((source_root/'manifest.json').read_text(encoding='utf-8'))
    levels=reference.payloads(source_root,source);scenes=[];errors=[]
    for level in range(source['levelCount']):
        for background in ((0,0,0,0),(0,0,0,255),(255,255,255,255)):
            scenes.append((f'level-{level}-background-{background}',reference.grid_scene(source,level,background),0))
    scenes.append(('fractional-lod',reference.grid_scene(source,0,(255,255,255,255),filter='linear-mipmap-linear',display=11,lod=0.5),2))
    size=source['nativeSize'];last=source['spriteCount']-1
    scenes.append(('overlap-bank-order',{'width':size,'height':size,'background':[65,127,191,255],
      'filter':'nearest','instances':[{'spriteIndex':i,'x':0,'y':0,'width':size,'height':size,'lod':1,'opacity':opacity}
                                    for i,opacity in [(0,1),(last,0.5),(min(1,last),0.75)]]},2))
    checks=[]
    with sync_playwright() as driver:
        options={'headless':True,'args':['--use-angle=swiftshader','--enable-unsafe-swiftshader']}
        if executable:options['executable_path']=executable
        browser=driver.chromium.launch(**options)
        try:
            with reference.server(root) as origin:
                page=browser.new_page();page.on('pageerror',lambda error:errors.append(str(error)))
                def route(request):
                    if request.request.url.startswith(origin):request.continue_()
                    else:errors.append('Unexpected external request');request.abort()
                page.route('**/*',route);page.goto(origin)
                expect(page.locator('#status')).to_contain_text('1000 instances',timeout=30000)
                csp=page.locator('meta[http-equiv="Content-Security-Policy"]').get_attribute('content')
                assert "script-src 'self'" in csp and 'unsafe-eval' not in csp and 'unsafe-inline' not in csp
                for name,scene,tolerance in scenes:
                    expected=reference.expected(source,levels,scene)
                    result=page.evaluate(DRAW,{'manifestHash':verified['manifestSha256'],**scene})
                    actual=base64.b64decode(result.pop('rgbaBase64'),validate=True)
                    assert len(actual)==len(expected),f'{name}: wrong pixel count'
                    maximum=0
                    for offset in range(0,len(actual),1048576):
                        a=np.frombuffer(actual[offset:offset+1048576],dtype=np.uint8).astype(np.int16)
                        b=np.frombuffer(expected[offset:offset+1048576],dtype=np.uint8).astype(np.int16)
                        maximum=max(maximum,int(np.abs(a-b).max(initial=0)))
                    assert maximum<=tolerance,f'{name}: maximum error {maximum} > {tolerance}'
                    checks.append({'case':name,'maxChannelError':maximum,'allowedChannelError':tolerance,
                        'actualPMsha256':hashlib.sha256(actual).hexdigest(),'expectedPMsha256':hashlib.sha256(expected).hexdigest(),**result})
                page.close()
            assert not errors,errors
            return {'status':'passed','httpLoaderAndUIExercised':True,'gpuExercised':True,'browser':browser.version,
                    'manifestSha256':verified['manifestSha256'],'spriteCount':source['spriteCount'],'checks':checks}
        finally:browser.close()


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--bundle',required=True,type=Path)
    parser.add_argument('--source-bundle',required=True,type=Path);parser.add_argument('--executable');parser.add_argument('--report',type=Path)
    args=parser.parse_args()
    if args.report and args.report.exists():parser.error('Report already exists')
    try:result=smoke(args.bundle,args.source_bundle,args.executable)
    except Exception as exc:result={'status':'failed','exception':type(exc).__name__,'message':str(exc)[:4000]}
    text=json.dumps(result,indent=2)+'\n'
    if args.report:
        args.report.parent.mkdir(parents=True,exist_ok=True)
        with args.report.open('x',encoding='utf-8') as f:f.write(text)
    print(text,end='');raise SystemExit(0 if result['status']=='passed' else 1)
