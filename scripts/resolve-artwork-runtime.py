#!/usr/bin/env python3
"""Create or verify a lazy-runtime ByteFables bank cache."""
from pathlib import Path
import argparse, json, sys
ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT/'integrations/framerudiments')]
from tools.artwork_runtime_resolve import resolve_lossless_bundle, resolve_uastc_bundle, verify_runtime_bundle


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--confirm-public',action='store_true')
    sub=parser.add_subparsers(dest='command',required=True)
    lossless=sub.add_parser('lossless');lossless.add_argument('--bundle',type=Path,required=True);lossless.add_argument('--output',type=Path,required=True)
    uastc=sub.add_parser('uastc');uastc.add_argument('--bundle',type=Path,required=True);uastc.add_argument('--output',type=Path,required=True);uastc.add_argument('--ktx',type=Path,required=True)
    verify=sub.add_parser('verify');verify.add_argument('--bundle',type=Path,required=True)
    args=parser.parse_args()
    try:
        if args.command=='lossless': result=resolve_lossless_bundle(args.bundle,args.output,confirm_public=args.confirm_public)
        elif args.command=='uastc': result=resolve_uastc_bundle(args.bundle,args.output,ktx=args.ktx,confirm_public=args.confirm_public)
        else: result=verify_runtime_bundle(args.bundle)
        print(json.dumps(result,indent=2));return 0
    except Exception as exc:
        print(f'Runtime resolution failed: {exc}',file=sys.stderr);return 1
if __name__=='__main__':raise SystemExit(main())
