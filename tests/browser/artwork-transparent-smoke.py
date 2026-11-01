#!/usr/bin/env python3
"""Real browser compositing of transparent native sprites on black and white.

HTTP mode checks the static preview under its CSP. --offline-contract checks
only decoded saved-image compositing in a blank page, never HTTP/UI behaviour.
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
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from tools.artwork_transparent_bundle import verify_transparent_bundle
from bytefables_framerudiments.image_assets import _frames
from bytefables_framerudiments.transparent_assets import composite_rgb

DRAW = r'''async ({data, format, size, matte}) => {
  const bytes = Uint8Array.from(atob(data), c => c.charCodeAt(0));
  const bitmap = await createImageBitmap(new Blob([bytes], {type:'image/'+format}),
    {colorSpaceConversion:'none', imageOrientation:'none', premultiplyAlpha:'none'});
  try {
    if(bitmap.width !== size || bitmap.height !== size) throw Error('Image dimensions differ');
    const canvas=document.createElement('canvas');canvas.width=size;canvas.height=size;
    const ctx=canvas.getContext('2d', {willReadFrequently:true});
    ctx.fillStyle=`rgb(${matte.join(',')})`;ctx.fillRect(0,0,size,size);
    ctx.drawImage(bitmap,0,0);
    const pixels=ctx.getImageData(0,0,size,size).data, parts=[];
    for(let i=0;i<pixels.length;i+=8192)parts.push(String.fromCharCode(...pixels.subarray(i,i+8192)));
    return btoa(parts.join(''));
  } finally {bitmap.close();}
}'''


def smoke(directory, executable=None, offline=False):
    from playwright.sync_api import sync_playwright, expect
    root=Path(directory).resolve(strict=True)
    verified=verify_transparent_bundle(root)
    document=json.loads((root/'manifest.json').read_text())
    # First identity for every family/palette/size; no claim of testing all IDs.
    selected={}
    for asset in document['assets']:
        for file in asset['files']:
            if file['format'] not in ('png','webp'): continue
            size=file['frames'][0]['size']
            selected.setdefault((asset['family'],asset['palette'],size,file['format']),file)
    server=thread=None
    if not offline:
        class Quiet(SimpleHTTPRequestHandler):
            def log_message(self,*args): pass
        server=ThreadingHTTPServer(('127.0.0.1',0),functools.partial(Quiet,directory=str(root)))
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    try:
        with sync_playwright() as driver:
            opts={'headless':True}
            if executable:opts['executable_path']=executable
            browser=driver.chromium.launch(**opts)
            try:
                page=browser.new_page();errors=[]
                page.on('pageerror',lambda error:errors.append(str(error)))
                if not offline:
                    origin=f'http://127.0.0.1:{server.server_port}/'
                    def route(req):
                        if not req.request.url.startswith(origin):
                            errors.append('Unexpected external request');req.abort()
                        else:req.continue_()
                    page.route('**/*',route);page.goto(origin+'index.html')
                    expect(page.locator('h1')).to_have_text('Transparent source sprites')
                    expect(page.locator('article')).to_have_count(document['assetCount'])
                    assert 'script-src' not in page.locator('meta[http-equiv="Content-Security-Policy"]').get_attribute('content')
                    assert page.locator('script').count()==0
                    # Explicit decoding; no eval-based polling or CSP bypass.
                    page.locator('article img').first.evaluate('(img) => img.decode()')
                hashes=[]
                for key,file in selected.items():
                    data=(root/file['file']).read_bytes();size=key[2]
                    raw=_frames(data,file['format'])[size]
                    with Image.frombytes('RGBA',(size,size),raw) as source:
                        for matte in ((0,0,0),(255,255,255)):
                            actual=base64.b64decode(page.evaluate(DRAW,{'data':base64.b64encode(data).decode('ascii'),
                                'format':file['format'],'size':size,'matte':matte}),validate=True)
                            with composite_rgb(source,matte) as expected,expected.convert('RGBA') as rgba:
                                assert actual==rgba.tobytes(),f'Browser alpha composite mismatch: {key} {matte}'
                            hashes.append(hashlib.sha256(actual).hexdigest())
                assert not errors,errors
                return {'status':'passed','browser':browser.version,'mode':'offline contract' if offline else 'HTTP preview and Canvas',
                        'httpPreviewExercised':not offline,'manifestSha256':verified['manifestSha256'],
                        'sampledNativeVariants':len(selected),'compositeChecks':len(hashes),
                        'allPixelComparisonsExact':True,
                        'warning':'Native generator fixtures have binary alpha; this does not qualify arbitrary fractional-alpha browser rounding.'}
            finally:browser.close()
    finally:
        if server:server.shutdown();server.server_close();thread.join(timeout=5)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--bundle',type=Path,required=True);p.add_argument('--executable')
    p.add_argument('--offline-contract',action='store_true');p.add_argument('--report',type=Path)
    a=p.parse_args()
    try: result=smoke(a.bundle,a.executable,a.offline_contract)
    except Exception as exc: result={'status':'failed','exception':type(exc).__name__,'message':str(exc)[:1500]}
    text=json.dumps(result,indent=2)+'\n'
    if a.report:
        with a.report.open('x',encoding='utf-8') as stream:stream.write(text)
    print(text,end='');raise SystemExit(0 if result['status']=='passed' else 1)
