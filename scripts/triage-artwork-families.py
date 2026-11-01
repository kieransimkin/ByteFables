#!/usr/bin/env python3
"""Turn a ByteFables distinctiveness report into a ranked family remediation queue."""
from pathlib import Path
import argparse, json, sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from tools.artwork_family_triage import triage

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--report',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args()
    try: result=triage(a.report,a.output);print(json.dumps(result,indent=2));return 0
    except Exception as exc: print(f'Family triage failed: {exc}',file=sys.stderr);return 1
if __name__=='__main__':raise SystemExit(main())
