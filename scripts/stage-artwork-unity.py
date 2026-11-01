#!/usr/bin/env python3
"""Verified, no-overwrite staging for ByteFables' optional Unity package."""
from pathlib import Path
import argparse
import json
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT/'integrations/framerudiments')]
from tools.artwork_unity_stage import stage_unity_bundle, verify_unity_stage

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--confirm-public', action='store_true')
    parser.add_argument('--max-payload-mib', type=int, default=64)
    commands = parser.add_subparsers(dest='command', required=True)
    export = commands.add_parser('stage'); export.add_argument('--bundle', type=Path, required=True); export.add_argument('--output', type=Path, required=True)
    verify = commands.add_parser('verify'); verify.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    try:
        if not args.confirm_public: raise ValueError('Explicit --confirm-public consent required')
        if not 1 <= args.max_payload_mib <= 128: raise ValueError('Budget must be 1..128 MiB')
        budget = args.max_payload_mib*1024*1024
        if args.command == 'stage':
            result = stage_unity_bundle(args.bundle, args.output, confirm_public=True, max_payload_bytes=budget)
        else: result = verify_unity_stage(args.output, max_payload_bytes=budget)
        print(json.dumps(result, indent=2)); return 0
    except (ValueError, OSError) as exc:
        print(f'Unity staging failed: {exc}', file=sys.stderr); return 1
if __name__ == '__main__': raise SystemExit(main())
