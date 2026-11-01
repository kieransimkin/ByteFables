#!/usr/bin/env python3
"""Run the opt-in artwork-generator v2 candidate promotion gate."""
from pathlib import Path
import argparse,json,sys
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'integrations/framerudiments')]
from tools.artwork_v2_promotion import run_promotion

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',required=True,type=Path);p.add_argument('--identities',type=int,default=256)
    p.add_argument('--sizes',default='16,32,64,128');p.add_argument('--preview-size',type=int,default=32);a=p.parse_args()
    try:
        result=run_promotion(a.output,identities=a.identities,sizes=tuple(int(x) for x in a.sizes.split(',')),preview_size=a.preview_size)
        print(json.dumps(result,indent=2));return 0
    except Exception as exc:print(f'Artwork v2 promotion failed: {exc}',file=sys.stderr);return 1
if __name__=='__main__':raise SystemExit(main())
