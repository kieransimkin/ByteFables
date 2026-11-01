#!/usr/bin/env python3
"""Real-tool UASTC protocol smoke for synthetic fixtures; deliberately not a quality gate."""
from __future__ import annotations
from pathlib import Path
import argparse, json, tempfile, sys
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'integrations/framerudiments')]
from tools.artwork_ktx2_bundle import verify_ktx2_bundle
from tools.artwork_ktx2_basis import ktx_version,encode_command,_run,_validate_ktx,_extract_rgba8
from tools.artwork_asset_bundle import _file,_bytes,_no_links
from tools.artwork_native_benchmark import _read_json,_sha

def probe(bundle:Path,ktx:Path)->dict:
    root=_no_links(bundle);exe=_no_links(ktx);ktx_version(exe);verified=verify_ktx2_bundle(root)
    transport,_=_read_json(_file(root,'manifest.json'),16*1024*1024)
    source,_=_read_json(_file(root,'source-manifest.json'),16*1024*1024)
    bank=transport['banks'][0];src=_file(root,bank['file'])
    with tempfile.TemporaryDirectory(prefix='bytefables-uastc-probe-') as td:
        a=Path(td)/'a.ktx2';b=Path(td)/'b.ktx2'
        _run(encode_command(exe,src,a),timeout=300);_run(encode_command(exe,src,b),timeout=300)
        _validate_ktx(exe,a);_validate_ktx(exe,b)
        ra=_bytes(a,32*1024*1024);rb=_bytes(b,32*1024*1024)
        if ra!=rb: raise ValueError('Pinned UASTC protocol probe was not deterministic')
        levels=_extract_rgba8(exe,a,source['nativeSize'],bank['layerCount'])
        if len(levels)!=source['levelCount']: raise ValueError('UASTC protocol probe mip count mismatch')
        return {'status':'protocol-passed','qualityGateExecuted':False,'manifestSha256':verified['manifestSha256'],
                'bank':bank['index'],'layers':bank['layerCount'],'levels':len(levels),'encodedBytes':len(ra),
                'encodedSha256':_sha(ra),'toolVersion':'4.4.2',
                'warning':'Synthetic orientation fixture proves tool/codec protocol only; real-artwork workflow owns quality acceptance.'}

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--bundle',type=Path,required=True);p.add_argument('--ktx',type=Path,required=True);p.add_argument('--report',type=Path)
    a=p.parse_args()
    try:r=probe(a.bundle,a.ktx)
    except Exception as exc:
        print(f'UASTC protocol probe failed: {exc}',file=sys.stderr);return 1
    text=json.dumps(r,indent=2)+'\n';print(text,end='')
    if a.report:
        if a.report.exists():raise ValueError('Report already exists')
        a.report.parent.mkdir(parents=True,exist_ok=True);a.report.write_text(text,encoding='utf-8')
    return 0
if __name__=='__main__':raise SystemExit(main())
