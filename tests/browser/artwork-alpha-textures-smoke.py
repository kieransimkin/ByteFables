#!/usr/bin/env python3
"""Required real WebGL2 texture-array readback under the shipped strict CSP.

Tests all saved mips, two mattes and transparent output, painter-order overlap,
fractional trilinear LOD, and red/blue array-layer isolation. Missing GPU/HTTP
support is a failure, not a successful skip. No browser policy bypass.
"""
from __future__ import annotations
import argparse
import base64
from contextlib import contextmanager
import functools
import hashlib
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import sys
import tempfile
import threading
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from tools.artwork_alpha_textures import verify_alpha_textures

DRAW = r'''async ({manifestHash, instances, width, height, background, filter}) => {
 const api=globalThis.ByteFablesAlphaTextures,bundle=await api.loadBundle('./',{manifestSha256:manifestHash});
 const canvas=document.createElement('canvas');canvas.width=width;canvas.height=height;
 let renderer;
 try{renderer=new api.WebGLArray(canvas,bundle,{filter});const stats=renderer.draw(instances,{background});
 const pixels=renderer.readPixels(),parts=[];
 for(let i=0;i<pixels.length;i+=8192)parts.push(String.fromCharCode(...pixels.subarray(i,i+8192)));
 return {...stats,rgbaBase64:btoa(parts.join('')),gpuVersion:renderer.gl.getParameter(renderer.gl.VERSION)};
 }finally{renderer?.dispose();bundle.dispose();canvas.width=1;canvas.height=1;}
}'''


@contextmanager
def server(root):
    class Quiet(SimpleHTTPRequestHandler):
        def do_GET(self):
            if self.path == '/favicon.ico':self.send_response(204);self.end_headers()
            else:super().do_GET()
        def log_message(self,*args):pass
    http=ThreadingHTTPServer(('127.0.0.1',0),functools.partial(Quiet,directory=str(root)))
    thread=threading.Thread(target=http.serve_forever,daemon=True);thread.start()
    try:yield f'http://127.0.0.1:{http.server_port}/'
    finally:http.shutdown();http.server_close();thread.join(timeout=5)


def payloads(root, manifest):
    return [[np.frombuffer((root/r['file']).read_bytes(),dtype=np.uint8).reshape(bank['layerCount'],r['size'],r['size'],4)
             for r in bank['levels']] for bank in manifest['banks']]


def sample(sprite, levels, size, lod, filter):
    # Independent CPU sampling from saved raw levels; never the JS shader or GL.
    def level_pixels(level):
        image=levels[sprite['bankIndex']][level][sprite['layerIndex']].astype(np.float64)
        n=image.shape[0];uv=(np.arange(size)+0.5)*n/size
        if filter=='nearest':
            index=np.clip(np.floor(uv).astype(int),0,n-1)
            return image[index[:,None],index[None,:]]
        position=uv-0.5;lo=np.floor(position).astype(int);mix=position-lo;hi=lo+1
        lo=np.clip(lo,0,n-1);hi=np.clip(hi,0,n-1)
        top=image[lo[:,None],lo[None,:]]*(1-mix[None,:,None])+image[lo[:,None],hi[None,:]]*mix[None,:,None]
        bottom=image[hi[:,None],lo[None,:]]*(1-mix[None,:,None])+image[hi[:,None],hi[None,:]]*mix[None,:,None]
        return top*(1-mix[:,None,None])+bottom*mix[:,None,None]
    if filter=='nearest':return level_pixels(int(np.floor(lod+0.5)))
    lower=int(np.floor(lod));upper=min(lower+1,len(levels[0])-1);weight=lod-lower
    return level_pixels(lower)*(1-weight)+level_pixels(upper)*weight


def expected(manifest, levels, scene):
    width,height=scene['width'],scene['height'];bg=np.array(scene['background'],dtype=np.float64)
    bg[:3]*=bg[3]/255
    result=np.empty((height,width,4),dtype=np.uint8);result[:]=np.floor(bg+0.5).astype(np.uint8)
    cache={}
    for item in scene['instances']:
        assert item['width']==item['height']
        key=(item['spriteIndex'],item['width'],item['lod'],scene['filter'])
        if key not in cache:cache[key]=sample(manifest['sprites'][key[0]],levels,key[1],key[2],key[3])
        source=cache[key]*item.get('opacity',1);x,y=item['x'],item['y'];size=item['width']
        dest=result[y:y+size,x:x+size].astype(np.float64)
        result[y:y+size,x:x+size]=np.clip(np.floor(source+dest*(1-source[:,:,3:4]/255)+0.5),0,255).astype(np.uint8)
    return result.tobytes()


def grid_scene(manifest, level, background, *, filter='nearest', display=None, lod=None):
    size=display or manifest['nativeSize']>>level;count=max(1000,manifest['spriteCount']);columns=40
    return {'width':columns*size,'height':((count+columns-1)//columns)*size,'background':list(background),'filter':filter,
      'instances':[{'spriteIndex':i%manifest['spriteCount'],'x':i%columns*size,'y':i//columns*size,
                    'width':size,'height':size,'lod':level if lod is None else lod} for i in range(count)]}


def exercise(page,root,manifest,pin,*,synthetic=False):
    levels=payloads(root,manifest);scenes=[]
    for level in range(manifest['levelCount']):
        for bg in ((0,0,0,0),(0,0,0,255),(255,255,255,255)):
            scenes.append((f'level-{level}-matte-{bg[0]}-alpha-{bg[3]}',grid_scene(manifest,level,bg),0))
    # These use fractional interpolation/blending; GL precision permits a small
    # fixed tolerance. It is NEVER applied to exact texel-centre tests above.
    scenes.append(('trilinear-half-lod',grid_scene(manifest,0,(255,255,255,255),
                   filter='linear-mipmap-linear',display=11,lod=0.5),2))
    size=manifest['nativeSize'];last=manifest['spriteCount']-1
    scenes.append(('overlap-bank-order',{'width':size,'height':size,'background':[65,127,191,255],
      'filter':'nearest','instances':[{'spriteIndex':i,'x':0,'y':0,'width':size,'height':size,
                                     'lod':1,'opacity':opacity} for i,opacity in [(0,1),(last,0.5),(1,0.75)]]},2))
    if synthetic:
        # Adjacent solid red/blue layers must never blend with one another.
        scenes.append(('trilinear-array-layer-isolation',{
            'width':18,'height':9,'background':[0,0,0,0],'filter':'linear-mipmap-linear',
            'instances':[{'spriteIndex':i,'x':i*9,'y':0,'width':9,'height':9,'lod':2.5} for i in (0,1)]},0))
    evidence=[]
    for name,scene,tolerance in scenes:
        target=expected(manifest,levels,scene)
        actual=page.evaluate(DRAW,{'manifestHash':pin,**scene})
        raw=base64.b64decode(actual.pop('rgbaBase64'),validate=True)
        assert len(raw)==len(target),f'Pixel length mismatch: {name}'
        max_error=0
        for offset in range(0,len(raw),1048576):
            a=np.frombuffer(raw[offset:offset+1048576],dtype=np.uint8).astype(np.int16)
            b=np.frombuffer(target[offset:offset+1048576],dtype=np.uint8).astype(np.int16)
            max_error=max(max_error,int(np.abs(a-b).max(initial=0)))
        assert max_error<=tolerance,f'{name}: channel difference {max_error} > fixed allowed {tolerance}'
        evidence.append({'case':name,'maxChannelError':max_error,'allowedChannelError':tolerance,
                         'expectedPMsha256':hashlib.sha256(target).hexdigest(),
                         'actualPMsha256':hashlib.sha256(raw).hexdigest(),**actual})
    return evidence


def smoke(bundle, executable=None):
    from playwright.sync_api import sync_playwright, expect
    root=Path(bundle).resolve(strict=True);verified=verify_alpha_textures(root)
    manifest=json.loads((root/'manifest.json').read_text());errors=[]
    with sync_playwright() as driver:
        options={'headless':True,'args':['--use-angle=swiftshader','--enable-unsafe-swiftshader']}
        if executable:options['executable_path']=executable
        browser=driver.chromium.launch(**options)
        try:
            with server(root) as origin:
                page=browser.new_page();page.on('pageerror',lambda error:errors.append(str(error)))
                def route(req):
                    if req.request.url.startswith(origin):req.continue_()
                    else:errors.append('Unexpected external request');req.abort()
                page.route('**/*',route);page.goto(origin)
                expect(page.locator('#status')).to_contain_text('1000 instances',timeout=30000)
                csp=page.locator('meta[http-equiv="Content-Security-Policy"]').get_attribute('content')
                assert "script-src 'self'" in csp and 'unsafe-eval' not in csp and 'unsafe-inline' not in csp
                checks=exercise(page,root,manifest,verified['manifestSha256']);page.close()
            with tempfile.TemporaryDirectory() as tmp:
                # Explicit synthetic GPU conformance fixture, not native provenance.
                fixture=json.loads((ROOT/'tests/vectors/artwork-alpha-textures-v1.json').read_text());target=Path(tmp)
                for name,data in fixture['files'].items():
                    p=target/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(base64.b64decode(data))
                text=json.dumps(fixture['manifest'],indent=2)+'\n';(target/'manifest.json').write_text(text)
                (target/'runtime.js').write_bytes((ROOT/'integrations/web/artwork-alpha-textures/runtime.js').read_bytes())
                (target/'index.html').write_text('''<!doctype html><meta http-equiv="Content-Security-Policy" content="default-src 'none'; script-src 'self'; connect-src 'self'; base-uri 'none'"><script src="runtime.js"></script><p>Explicit synthetic GPU conformance vector</p>''')
                with server(target) as origin:
                    page=browser.new_page();page.on('pageerror',lambda error:errors.append(str(error)))
                    page.route('**/*',lambda req:req.continue_() if req.request.url.startswith(origin) else req.abort())
                    page.goto(origin);control=exercise(page,target,fixture['manifest'],hashlib.sha256(text.encode()).hexdigest(),synthetic=True)
                    page.close()
            assert not errors,errors
            return {'status':'passed','browser':browser.version,'httpLoaderAndUIExercised':True,'gpuExercised':True,
                    'manifestSha256':verified['manifestSha256'],'spriteCount':manifest['spriteCount'],
                    'realBundleChecks':checks,'explicitSyntheticChecks':control,
                    'warning':'Exact PM texel-centre checks; fixed <=2-channel-unit tolerance only for interpolation/overlap.'}
        finally:browser.close()


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--bundle',required=True,type=Path)
    parser.add_argument('--executable');parser.add_argument('--report',type=Path);args=parser.parse_args()
    try:result=smoke(args.bundle,args.executable)
    except Exception as exc:result={'status':'failed','exception':type(exc).__name__,'message':str(exc)[:2000]}
    text=json.dumps(result,indent=2)+'\n'
    if args.report:
        args.report.parent.mkdir(parents=True,exist_ok=True)
        with args.report.open('x',encoding='utf-8') as f:f.write(text)
    print(text,end='');raise SystemExit(0 if result['status']=='passed' else 1)
