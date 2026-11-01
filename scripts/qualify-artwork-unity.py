#!/usr/bin/env python3
from pathlib import Path
import argparse
import json
import os
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT),str(ROOT/'integrations/framerudiments')]
from tools.artwork_unity_qualification import run_qualification

def main():
    p=argparse.ArgumentParser(description='Run real Unity import, GPU mip readback and alpha/orientation qualification')
    p.add_argument('--confirm-public',action='store_true');p.add_argument('--unity',type=Path,default=os.environ.get('UNITY_EDITOR'))
    p.add_argument('--bundle',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--editor-version',default=os.environ.get('BYTEFABLES_UNITY_EDITOR_VERSION','6000.0.62f1'));p.add_argument('--timeout',type=int,default=1200)
    a=p.parse_args()
    try:
        if a.unity is None: raise ValueError('--unity or UNITY_EDITOR must identify an installed Unity executable')
        print(json.dumps(run_qualification(a.unity,a.bundle,a.output,confirm_public=a.confirm_public,
                         editor_version=a.editor_version,timeout_seconds=a.timeout),indent=2));return 0
    except Exception as e:
        print(f'Unity qualification failed: {e}',file=sys.stderr);return 1
if __name__=='__main__': raise SystemExit(main())
