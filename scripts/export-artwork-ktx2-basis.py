#!/usr/bin/env python3
"""Export or verify deterministic PUBLIC UASTC+Zstd KTX2 transport."""
from pathlib import Path
import argparse, json, shutil, sys
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'integrations/framerudiments')]
from tools.artwork_ktx2_basis import export_uastc_bundle, verify_uastc_bundle


def main()->int:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--confirm-public',action='store_true')
    p.add_argument('--ktx',type=Path,default=shutil.which('ktx'))
    sub=p.add_subparsers(dest='command',required=True)
    e=sub.add_parser('export');e.add_argument('--bundle',type=Path,required=True);e.add_argument('--output',type=Path,required=True)
    e.add_argument('--no-determinism-check',action='store_true')
    v=sub.add_parser('verify');v.add_argument('--bundle',type=Path,required=True);v.add_argument('--source-bundle',type=Path)
    args=p.parse_args()
    try:
        if args.ktx is None: raise ValueError('--ktx or PATH must identify Khronos KTX 4.4.2')
        if args.command=='export':
            result=export_uastc_bundle(args.bundle,args.output,ktx=args.ktx,confirm_public=args.confirm_public,
                verify_determinism=not args.no_determinism_check)
        else:
            if not args.confirm_public: raise ValueError('Explicit --confirm-public required')
            result=verify_uastc_bundle(args.bundle,ktx=args.ktx,source_bundle=args.source_bundle)
        print(json.dumps(result,indent=2));return 0
    except Exception as exc:
        print(f'UASTC KTX2 operation failed: {exc}',file=sys.stderr);return 1
if __name__=='__main__': raise SystemExit(main())
