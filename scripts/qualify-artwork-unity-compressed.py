#!/usr/bin/env python3
"""Prepare or run ByteFables direct compressed-texture device qualification."""
from pathlib import Path
import argparse,json,os,sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from tools.artwork_unity_compressed_device import prepare_compressed_project,run_compressed_qualification,PROFILES

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--confirm-public',action='store_true');p.add_argument('--prepare-only',action='store_true')
 p.add_argument('--gpu-bundle',type=Path,required=True);p.add_argument('--reference-bundle',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
 p.add_argument('--profile',choices=tuple(PROFILES),required=True);p.add_argument('--unity',type=Path,default=os.environ.get('UNITY_EDITOR'))
 p.add_argument('--editor-version',default=os.environ.get('BYTEFABLES_UNITY_EDITOR_VERSION','6000.0.62f1'));p.add_argument('--build-timeout',type=int,default=3600);p.add_argument('--player-timeout',type=int,default=900)
 a=p.parse_args()
 try:
  opts=dict(confirm_public=a.confirm_public,profile=a.profile,editor_version=a.editor_version)
  if a.prepare_only:r=prepare_compressed_project(a.gpu_bundle,a.reference_bundle,a.output,**opts)
  else:
   if a.unity is None:raise ValueError('--unity or UNITY_EDITOR must identify an installed Unity executable')
   r=run_compressed_qualification(a.unity,a.gpu_bundle,a.reference_bundle,a.output,build_timeout=a.build_timeout,player_timeout=a.player_timeout,**opts)
  print(json.dumps(r,indent=2));return 0
 except Exception as exc:print(f'Compressed-device qualification failed: {exc}',file=sys.stderr);return 1
if __name__=='__main__':raise SystemExit(main())
