"""Explicit synthetic orientation/alpha sentinel corpus; NEVER native-render evidence."""
from pathlib import Path
import argparse
import hashlib
import json
import sys
ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT/'integrations/framerudiments')]
from PIL import Image
from bytefables_framerudiments.alpha_mips import mip_chain, PROFILE as ALPHA_PROFILE
from bytefables_framerudiments.ktx2_arrays import encode_ktx2, PROFILE
from tools.artwork_alpha_textures import SAMPLING, key_for
from tools.artwork_ktx2_bundle import verify_ktx2_bundle
from tools.artwork_native_benchmark import _json, _sha
from tools.artwork_transparent_bundle import _new_output
from tools.artwork_asset_bundle import _no_links


def make_fixture(output: Path) -> Path:
    output = _new_output(output, ())
    payloads = []
    for i in range(4):
        pixels = bytearray()
        for y in range(16):
            for x in range(16):
                pixel = (255, 0, 0, 128) if i == 0 else (0, 0, 255, 128) if i == 1 else (
                    x*17, y*17, (x+y)*8, 255 if x % 3 else 0) if i == 2 else (
                    (x*13+y*7)%256, (y*17)%256, 80, (x*11+y*5)%256)
                pixels.extend(pixel)
        image = Image.frombytes('RGBA', (16,16), bytes(pixels))
        try: payloads.append((bytes(pixels), mip_chain(image)))
        finally: image.close()
    dummy = b'Explicit synthetic test fixture. No viewer and no native renderer.\n'
    viewer = lambda names: [{'file': n, 'byteLength': len(dummy), 'sha256': _sha(dummy)} for n in names]
    sprites = []
    for i, (raw, levels) in enumerate(payloads):
        digest = f'{i:064x}'
        sprite = {'digestHex': digest, 'family':'sigil', 'palette':'neon', 'complexity':4, 'nativeSize':16,
                  'bankIndex':i//2, 'layerIndex':i%2, 'sourceFile':f'assets/sigil-neon-c4/{digest}/16.png',
                  'sourceFileSha256':_sha(b'explicit synthetic png placeholder'+bytes([i])),
                  'sourceRGBAsha256':_sha(raw), 'levelSha256':[_sha(x) for x in levels]}
        sprite['spriteKey'] = key_for(sprite); sprites.append(sprite)
    banks = []; encoded = []
    for bank in range(2):
        levels = [b''.join(payloads[i][1][level] for i in range(bank*2,bank*2+2)) for level in range(5)]
        banks.append({'index':bank,'layerCount':2,'levels':[
            {'level': l,'size':16>>l,'file':f'levels/bank-{bank:03d}-mip-{l:02d}.rgba',
             'byteLength':len(raw),'sha256':_sha(raw)} for l,raw in enumerate(levels)]})
        encoded.append(encode_ktx2(16,2,levels))
    source = {'schema':'bytefables.alpha-texture-array-bundle.v1','profile':ALPHA_PROFILE,'status':'passed',
              'publicOnly':True,'guarantee':'presentation-only','nativeSize':16,'layersPerBank':2,'spriteCount':4,
              'levelCount':5,'payloadBytes':sum(len(p) for _,l in payloads for p in l),
              'sourceManifestSha256':_sha(b'explicit synthetic sentinel corpus, not native output'),
              'sampling':SAMPLING.copy(),'banks':banks,'sprites':sprites,
              'viewerFiles':viewer(('index.html','runtime.js','demo.js','demo.css'))}
    output.mkdir(parents=True); (output/'banks').mkdir()
    source_bytes = _json(source); (output/'source-manifest.json').write_bytes(source_bytes)
    wrappers = []
    for i,raw in enumerate(encoded):
        path = f'banks/bank-{i:03d}.ktx2'; (output/path).write_bytes(raw)
        wrappers.append({'index':i,'layerCount':2,'file':path,'byteLength':len(raw),'sha256':_sha(raw)})
    viewers = viewer(('index.html','alpha-runtime.js','ktx2-runtime.js','demo.js','demo.css'))
    for item in viewers: (output/item['file']).write_bytes(dummy)
    doc = {'schema':'bytefables.ktx2-alpha-bundle.v1','profile':PROFILE,'status':'passed','publicOnly':True,
           'guarantee':'presentation-only','sourceManifest':{'file':'source-manifest.json','byteLength':len(source_bytes),'sha256':_sha(source_bytes)},
           'banks':wrappers,'viewerFiles':viewers}
    (output/'manifest.json').write_bytes(_json(doc)); verify_ktx2_bundle(output)
    return output

if __name__ == '__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);args=p.parse_args()
    make_fixture(args.output)
    print(json.dumps({'status':'passed','synthetic':True,'nativeHostExecuted':False,'output':str(args.output)},indent=2))
