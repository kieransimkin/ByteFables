#!/usr/bin/env python3
from pathlib import Path
import argparse,json,sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from tools.artwork_distinctiveness import analyse_distinctiveness

def main():
 p=argparse.ArgumentParser(description='Screen transparent ByteFables artwork for visual collisions')
 p.add_argument('--bundle',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
 p.add_argument('--sizes',default='16,32,64,128');p.add_argument('--preview-size',type=int,default=64);p.add_argument('--top-pairs',type=int,default=50)
 a=p.parse_args()
 try:r=analyse_distinctiveness(a.bundle,a.output,sizes=tuple(int(x) for x in a.sizes.split(',')),preview_size=a.preview_size,top_pairs=a.top_pairs)
 except Exception as exc:print(f'Distinctiveness benchmark failed: {exc}',file=sys.stderr);return 1
 print(json.dumps(r,indent=2));return 0
if __name__=='__main__':raise SystemExit(main())
