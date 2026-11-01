#!/usr/bin/env python3
"""Export or verify BC7/ASTC4x4/ETC2_RGBA8 raw block bundles from verified UASTC."""
from pathlib import Path
import argparse, json, sys
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'integrations/framerudiments')]
from tools.artwork_gpu_formats import export_gpu_bundle,verify_gpu_bundle

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--confirm-public',action='store_true');p.add_argument('--ktx',type=Path)
    sub=p.add_subparsers(dest='cmd',required=True)
    e=sub.add_parser('export');e.add_argument('--bundle',type=Path,required=True);e.add_argument('--output',type=Path,required=True)
    v=sub.add_parser('verify');v.add_argument('--bundle',type=Path,required=True);v.add_argument('--source-uastc',type=Path)
    a=p.parse_args()
    try:
        if a.cmd=='export':
            if a.ktx is None: raise ValueError('--ktx is required for export')
            out=export_gpu_bundle(a.bundle,a.output,ktx=a.ktx,confirm_public=a.confirm_public)
        else:
            out=verify_gpu_bundle(a.bundle,source_uastc=a.source_uastc,ktx=a.ktx)
        print(json.dumps(out,indent=2));return 0
    except Exception as exc:
        print(f'GPU block operation failed: {exc}',file=sys.stderr);return 1
if __name__=='__main__':raise SystemExit(main())
