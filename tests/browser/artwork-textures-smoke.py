#!/usr/bin/env python3
"""Real Canvas/WebGL pixel readback; default mode also checks the HTTP loader/UI.

--offline-contract runs trusted local runtime code against saved PNG bytes in a
blank page. It does NOT claim HTTP loader, navigation or gallery integration.
No browser policies or production CSP directives are disabled in either mode.
"""
from __future__ import annotations
import argparse
import base64
import functools
import hashlib
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import sys
import threading
from PIL import Image

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from tools.artwork_texture_bundle import verify_texture_bundle

DRAW = r'''async ({manifest, pngs, manifestHash, offline, backends}) => {
    const api=globalThis.ByteFablesTextures;
    let bundle;
    if(offline){
      api.validateManifest(manifest);
      const images=[];
      for(const text of pngs){const bytes=Uint8Array.from(atob(text),c=>c.charCodeAt(0));
        images.push(await createImageBitmap(new Blob([bytes],{type:'image/png'}),
          {premultiplyAlpha:'none',colorSpaceConversion:'none',imageOrientation:'none'}));}
      bundle={manifest,images,disposed:false,dispose(){images.forEach(i=>i.close());this.disposed=true;}};
    }else bundle=await api.loadBundle('./',{manifestSha256:manifestHash});
    try{
      const grid=api.makeGrid(bundle.manifest,1000,40,bundle.manifest.nativeSize),results=[];
      for(const backend of backends){
        const canvas=document.createElement('canvas');canvas.width=grid.width;canvas.height=grid.height;
        const consumer=backend==='canvas2d'?new api.CanvasAtlas(canvas,bundle):new api.WebGLAtlas(canvas,bundle);
        try{
          const stats=consumer.draw(grid.instances);let pixels;
          if(backend==='canvas2d')pixels=canvas.getContext('2d').getImageData(0,0,grid.width,grid.height).data;
          else{
            const gl=consumer.gl,raw=new Uint8Array(grid.width*grid.height*4);pixels=new Uint8Array(raw.length);
            gl.readPixels(0,0,grid.width,grid.height,gl.RGBA,gl.UNSIGNED_BYTE,raw);
            if(gl.getError()!==gl.NO_ERROR)throw new Error('GPU pixel readback error');
            const stride=grid.width*4;
            for(let y=0;y<grid.height;y++)pixels.set(raw.subarray((grid.height-1-y)*stride,(grid.height-y)*stride),y*stride);
          }
          // FNV-style checks are not used: transport contract compares full SHA-256.
          // HTTP mode uses Web Crypto; offline mode returns raw bytes to Python,
          // because a blank page is not necessarily a secure Web Crypto context.
          if(offline){results.push({...stats,rgbaBase64:btoa((()=>{const parts=[];for(let i=0;i<pixels.length;i+=8192)
             parts.push(String.fromCharCode(...pixels.subarray(i,i+8192)));return parts.join('');})())});}
          else{const hash=await crypto.subtle.digest('SHA-256',pixels);results.push({...stats,
             rgbaSha256:Array.from(new Uint8Array(hash),b=>b.toString(16).padStart(2,'0')).join('')});}
        }finally{consumer.dispose();canvas.width=1;canvas.height=1;}
      }
      return results;
    }finally{bundle.dispose();}
}'''


def expected_pixels(root, manifest):
    size=manifest['nativeSize'];width=40*size;height=25*size
    images=[]
    try:
        for page in manifest['pages']:
            with Image.open(root/page['file']) as image:images.append(image.convert('RGBA'))
        with Image.new('RGBA',(width,height)) as frame:
            for i in range(1000):
                sprite=manifest['sprites'][i%manifest['spriteCount']]
                with images[sprite['pageIndex']].crop(tuple(sprite['rect'])) as tile:
                    frame.paste(tile,((i%40)*size,(i//40)*size))
            return hashlib.sha256(frame.tobytes()).hexdigest()
    finally:
        for image in images:image.close()


def smoke(directory: Path, executable=None, offline=False, backend='both') -> dict:
    from playwright.sync_api import sync_playwright, expect
    root=Path(directory).resolve(strict=True)
    verified=verify_texture_bundle(root)
    manifest=json.loads((root/'manifest.json').read_text())
    expected=expected_pixels(root,manifest)
    server=None;thread=None
    if not offline:
        class Quiet(SimpleHTTPRequestHandler):
            def do_GET(self):
                if self.path=='/favicon.ico':self.send_response(204);self.end_headers()
                else:super().do_GET()
            def log_message(self,*args):pass
        server=ThreadingHTTPServer(('127.0.0.1',0),functools.partial(Quiet,directory=str(root)))
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    try:
        with sync_playwright() as driver:
            options={'headless':True,'args':['--use-angle=swiftshader','--enable-unsafe-swiftshader']}
            if executable:options['executable_path']=executable
            browser=driver.chromium.launch(**options)
            try:
                page=browser.new_page();errors=[]
                page.on('pageerror',lambda error:errors.append(str(error)))
                if offline:
                    # Contract test of local code, no request to a blocked URL.
                    page.evaluate((ROOT/'integrations/web/artwork-textures/runtime.js').read_text())
                else:
                    origin=f'http://127.0.0.1:{server.server_port}'
                    def route(request):
                        if not request.request.url.startswith(origin+'/'):
                            errors.append('External request: '+request.request.url);request.abort()
                        else:request.continue_()
                    page.route('**/*',route)
                    page.goto(origin+'/index.html')
                    expect(page.locator('#status')).to_contain_text('Ready:',timeout=30000)
                    assert 'unsafe-eval' not in page.locator('meta[http-equiv="Content-Security-Policy"]').get_attribute('content')
                result=page.evaluate(DRAW,{'manifest':manifest,'manifestHash':verified['manifestSha256'],'offline':offline,
                    'backends':['canvas2d','webgl2'] if backend=='both' else [backend],
                    'pngs':[base64.b64encode((root/p['file']).read_bytes()).decode('ascii') for p in manifest['pages']] if offline else []})
                for item in result:
                    if offline:item['rgbaSha256']=hashlib.sha256(base64.b64decode(item.pop('rgbaBase64'),validate=True)).hexdigest()
                    assert item['rgbaSha256']==expected, f"{item['backend']} rendered pixels mismatch"
                assert not errors,errors
                return {'status':'passed','browser':browser.version,'mode':'offline pixel contract' if offline else 'HTTP loader and UI',
                        'httpLoaderExercised':not offline,'gpuExercised':backend in ('both','webgl2'),'instances':1000,'uniqueIdentityStyles':manifest['spriteCount'],
                        'expectedRGBAsha256':expected,'backends':result,'warning':'Submission timing is not GPU completion time or frame rate.'}
            finally:browser.close()
    finally:
        if server:server.shutdown();server.server_close();thread.join(timeout=5)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--bundle',type=Path,required=True)
    p.add_argument('--executable');p.add_argument('--offline-contract',action='store_true');p.add_argument('--report',type=Path)
    p.add_argument('--backend',choices=('both','canvas2d','webgl2'),default='both')
    a=p.parse_args()
    try:
        result=smoke(a.bundle,a.executable,a.offline_contract,a.backend)
    except Exception as exc:
        result={'status':'failed','exception':type(exc).__name__,'message':str(exc)[:2000],
                'mode':'offline pixel contract' if a.offline_contract else 'HTTP loader and UI'}
    text=json.dumps(result,indent=2)+'\n'
    if a.report:
        a.report.parent.mkdir(parents=True,exist_ok=True)
        with a.report.open('x',encoding='utf-8') as file:file.write(text)
    print(text,end='')
    raise SystemExit(0 if result['status']=='passed' else 1)
