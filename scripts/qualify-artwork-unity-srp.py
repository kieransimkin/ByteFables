#!/usr/bin/env python3
"""Prepare or run URP/HDRP Unity standalone qualification in an isolated project."""
from pathlib import Path
import argparse, json, os, sys
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'integrations/framerudiments')]
from tools.artwork_unity_srp import prepare_srp_project, run_srp_qualification, PROFILES

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--confirm-public',action='store_true');p.add_argument('--prepare-only',action='store_true')
    p.add_argument('--bundle',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--unity',type=Path,default=os.environ.get('UNITY_EDITOR'))
    p.add_argument('--profile',choices=tuple(PROFILES),required=True)
    p.add_argument('--editor-version',default=os.environ.get('BYTEFABLES_UNITY_EDITOR_VERSION','6000.0.62f1'))
    p.add_argument('--graph-count',type=int,action='append',dest='graph_counts')
    p.add_argument('--build-timeout',type=int,default=3600);p.add_argument('--player-timeout',type=int,default=1200)
    a=p.parse_args()
    try:
        kw=dict(confirm_public=a.confirm_public,profile=a.profile,editor_version=a.editor_version,graph_counts=a.graph_counts)
        if a.prepare_only:r=prepare_srp_project(a.bundle,a.output,**kw)
        else:
            if a.unity is None:raise ValueError('--unity or UNITY_EDITOR must identify an installed Unity executable')
            r=run_srp_qualification(a.unity,a.bundle,a.output,build_timeout=a.build_timeout,player_timeout=a.player_timeout,**kw)
        print(json.dumps(r,indent=2));return 0
    except Exception as e:
        print(f'Unity SRP qualification failed: {e}',file=sys.stderr);return 1
if __name__=='__main__':raise SystemExit(main())
