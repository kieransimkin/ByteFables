#!/usr/bin/env python3
"""Required same-origin HTTP streaming/residency smoke test for lossless KTX2 banks."""
from __future__ import annotations
import argparse, contextlib, http.server, json, shutil, socketserver, tempfile, threading
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]

@contextlib.contextmanager
def server(root: Path):
    class Handler(http.server.SimpleHTTPRequestHandler):
        def __init__(self,*a,**kw):super().__init__(*a,directory=str(root),**kw)
        def log_message(self,*a):pass
        def end_headers(self):
            self.send_header('Cache-Control','no-store');super().end_headers()
    class TCP(socketserver.ThreadingTCPServer):allow_reuse_address=True
    httpd=TCP(('127.0.0.1',0),Handler);thread=threading.Thread(target=httpd.serve_forever,daemon=True);thread.start()
    try:yield f'http://127.0.0.1:{httpd.server_address[1]}/'
    finally:httpd.shutdown();httpd.server_close();thread.join(timeout=5)

HTML='''<!doctype html><meta charset="utf-8"><meta http-equiv="Content-Security-Policy" content="default-src 'none'; script-src 'self'; connect-src 'self'"><title>ByteFables streaming smoke</title><pre id="status">starting</pre><script src="alpha-runtime.js"></script><script src="ktx2-runtime.js"></script><script src="streaming-runtime.js"></script><script src="smoke.js"></script>'''
JS='''(async()=>{const out=document.querySelector('#status');try{const source=await (await fetch('/bundle/source-manifest.json')).json();const one=source.banks[0].levels.reduce((n,r)=>n+r.byteLength,0);const bundle=await ByteFablesStreaming.openKtx2('/bundle/',{budgetBytes:one});
const a=await bundle.acquireBank(0);a.release();const b=await bundle.acquireBank(1);b.release();const b2=await bundle.acquireBank(1);b2.release();
const first=source.sprites[0];const s=await bundle.acquireSprite({digestHex:first.digestHex,family:first.family,palette:first.palette,complexity:first.complexity});s.release();const stats=bundle.stats();bundle.dispose();out.dataset.status='passed';out.textContent=JSON.stringify(stats);}catch(e){out.dataset.status='failed';out.textContent=String(e?.stack||e);}})();'''

def smoke(bundle: Path, executable: str|None=None)->dict:
    from playwright.sync_api import sync_playwright
    bundle=bundle.resolve(strict=True)
    with tempfile.TemporaryDirectory(prefix='bytefables-streaming-http-') as td:
        site=Path(td);shutil.copytree(bundle,site/'bundle')
        shutil.copy2(ROOT/'integrations/web/artwork-alpha-textures/runtime.js',site/'alpha-runtime.js')
        shutil.copy2(ROOT/'integrations/web/artwork-ktx2/ktx2-runtime.js',site/'ktx2-runtime.js')
        shutil.copy2(ROOT/'integrations/web/artwork-streaming/runtime.js',site/'streaming-runtime.js')
        (site/'index.html').write_text(HTML,encoding='utf-8');(site/'smoke.js').write_text(JS,encoding='utf-8')
        errors=[]
        with sync_playwright() as p:
            options={'headless':True};
            if executable:options['executable_path']=executable
            browser=p.chromium.launch(**options)
            try:
                with server(site) as origin:
                    page=browser.new_page();page.on('pageerror',lambda e:errors.append(str(e)))
                    page.goto(origin,wait_until='load');page.locator('#status[data-status]').wait_for(timeout=30000)
                    status=page.locator('#status').get_attribute('data-status');text=page.locator('#status').text_content()
                    if status!='passed':raise RuntimeError(text)
                    stats=json.loads(text);assert stats['loads']==3 and stats['evictions']==2 and stats['residentBanks']==1 and stats['hits']==1,stats
                    csp=page.locator('meta[http-equiv="Content-Security-Policy"]').get_attribute('content')
                    assert "script-src 'self'" in csp and 'unsafe-inline' not in csp and 'unsafe-eval' not in csp
                    assert not errors,errors
                    return {'status':'passed','httpStreamingExercised':True,'browser':browser.version,'stats':stats}
            finally:browser.close()

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--bundle',required=True,type=Path);p.add_argument('--executable');p.add_argument('--report',type=Path);a=p.parse_args()
    if a.report and a.report.exists():p.error('Report already exists')
    try:r=smoke(a.bundle,a.executable)
    except Exception as e:r={'status':'failed','exception':type(e).__name__,'message':str(e)[:4000]}
    text=json.dumps(r,indent=2)+'\n';print(text,end='')
    if a.report:
        a.report.parent.mkdir(parents=True,exist_ok=True);a.report.write_text(text,encoding='utf-8')
    raise SystemExit(0 if r['status']=='passed' else 1)
