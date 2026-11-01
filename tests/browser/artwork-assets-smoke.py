#!/usr/bin/env python3
"""Browser smoke test of a saved asset bundle, using loopback HTTP only.

Requires Playwright and Chromium. Does not render native artwork; the supplied
bundle must already exist. Tests image decoding, filters and native dimensions.
"""
from __future__ import annotations
import argparse
import functools
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import threading


def smoke(bundle: Path, executable: str | None = None, screenshot: Path | None = None):
    from playwright.sync_api import sync_playwright
    root = Path(bundle).resolve(strict=True)
    manifest = json.loads((root / 'manifest.json').read_text())
    assert manifest['status'] == 'passed' and manifest['assets'], 'Expected completed asset bundle'

    class Quiet(SimpleHTTPRequestHandler):
        def do_GET(self):
            if self.path == '/favicon.ico':
                self.send_response(204); self.end_headers()
            else:
                super().do_GET()

        def log_message(self, *_args):
            pass

    server = ThreadingHTTPServer(('127.0.0.1', 0), functools.partial(Quiet, directory=str(root)))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    origin = f'http://127.0.0.1:{server.server_port}'
    try:
        with sync_playwright() as driver:
            options = {'headless': True}
            if executable:
                options['executable_path'] = executable
            browser = driver.chromium.launch(**options)
            try:
                page = browser.new_page(viewport={'width': 1280, 'height': 900})
                errors, external = [], []
                page.on('pageerror', lambda e: errors.append(str(e)))
                page.on('console', lambda m: errors.append(m.text) if m.type == 'error' else None)
                def route(request):
                    if not request.request.url.startswith(origin + '/'):
                        external.append(request.request.url)
                        request.abort()
                    else:
                        request.continue_()
                page.route('**/*', route)
                page.goto(origin + '/index.html')
                page.wait_for_function("document.getElementById('status').textContent.includes('matching')")
                assert page.locator('article').count() > 0, 'No asset cards'
                page.locator('#query').fill('not-a-public-digest')
                assert page.locator('article').count() == 0, 'Search does not filter'
                first = manifest['assets'][0]
                size = min(first['nativeSizes'])
                page.locator('#query').fill(first['digestHex'])
                page.locator('#family').select_option(first['family'])
                page.locator('#palette').select_option(first['palette'])
                page.locator('#size').select_option(str(size))
                page.wait_for_function("Array.from(document.querySelectorAll('article img')).every(x => x.complete && x.naturalWidth)")
                assert page.locator('article').count() >= 1
                actual = page.locator('article img').first.evaluate('(x)=>[x.width,x.height,x.naturalWidth,x.naturalHeight]')
                assert actual == [size]*4, f'Native dimensions changed: {actual}'
                decoded = 0
                for item in first['files']:
                    if item['format'] not in ('png', 'webp') or item['frames'][0]['size'] != size:
                        continue
                    pixel_sha = page.evaluate('''async (url) => {
                        const image = new Image(); image.src = url; await image.decode();
                        const c = document.createElement('canvas'); c.width = image.width; c.height = image.height;
                        const ctx = c.getContext('2d', {willReadFrequently:true}); ctx.drawImage(image, 0, 0);
                        const data = ctx.getImageData(0, 0, c.width, c.height).data;
                        const hash = await crypto.subtle.digest('SHA-256', data);
                        return Array.from(new Uint8Array(hash), x=>x.toString(16).padStart(2,'0')).join('');
                    }''', origin + '/' + item['file'])
                    assert pixel_sha == item['frames'][0]['rgbaSha256'], 'Browser pixels differ from exported asset'
                    decoded += 1
                page.locator('#query').fill('')
                page.locator('#family').select_option('')
                page.locator('#palette').select_option('')
                if screenshot:
                    page.screenshot(path=str(screenshot), full_page=True)
                assert not errors, errors
                assert not external, external
                return {'status': 'passed', 'browser': browser.version, 'transport': 'loopback HTTP',
                        'filterAndNativeSizeChecks': True, 'independentBrowserPixelDecodes': decoded,
                        'externalRequests': len(external), 'consoleErrors': len(errors)}
            finally:
                browser.close()
    finally:
        server.shutdown(); server.server_close(); thread.join(timeout=5)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bundle', type=Path, required=True)
    parser.add_argument('--executable', help='Optional installed Chromium executable')
    parser.add_argument('--screenshot', type=Path)
    args = parser.parse_args()
    print(json.dumps(smoke(args.bundle, args.executable, args.screenshot), indent=2))
