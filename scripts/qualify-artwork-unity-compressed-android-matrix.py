#!/usr/bin/env python3
"""Build and execute both Android compressed-texture profiles on one physical device."""
from pathlib import Path
import argparse,json,sys
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'integrations/framerudiments')]
from tools.artwork_unity_compressed_android_matrix import run_android_matrix

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--confirm-public',action='store_true');p.add_argument('--unity',type=Path,required=True);p.add_argument('--adb',type=Path,required=True)
    p.add_argument('--gpu-bundle',type=Path,required=True);p.add_argument('--reference-bundle',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--editor-version',default='6000.0.62f1');p.add_argument('--device-serial');p.add_argument('--build-timeout',type=int,default=5400);p.add_argument('--device-timeout',type=int,default=900);p.add_argument('--keep-installed',action='store_true')
    a=p.parse_args()
    try:
        result=run_android_matrix(a.unity,a.adb,a.gpu_bundle,a.reference_bundle,a.output,confirm_public=a.confirm_public,editor_version=a.editor_version,
            device_serial=a.device_serial,build_timeout=a.build_timeout,device_timeout=a.device_timeout,keep_installed=a.keep_installed)
        print(json.dumps(result,indent=2));return 0
    except Exception as exc:print(f'Android compressed matrix failed: {exc}',file=sys.stderr);return 1
if __name__=='__main__':raise SystemExit(main())
