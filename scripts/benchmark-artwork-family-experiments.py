#!/usr/bin/env python3
"""Run versioned A/B remediation candidates without changing production artwork."""
from pathlib import Path
import argparse,json,sys
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'integrations/framerudiments')]
from tools.artwork_family_experiments import run_experiments

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);p.add_argument('--triage',type=Path)
    p.add_argument('--families',help='comma-separated supported families');p.add_argument('--identities',type=int,default=128)
    p.add_argument('--sizes',default='16,32,64,128');p.add_argument('--preview-size',type=int,default=32);a=p.parse_args()
    try:
        families=[x for x in (a.families or '').split(',') if x] or None
        result=run_experiments(a.output,families=families,triage_path=a.triage,identities=a.identities,
                               sizes=tuple(int(x) for x in a.sizes.split(',')),preview_size=a.preview_size)
        print(json.dumps(result,indent=2));return 0
    except Exception as exc:print(f'Family experiment failed: {exc}',file=sys.stderr);return 1
if __name__=='__main__':raise SystemExit(main())
