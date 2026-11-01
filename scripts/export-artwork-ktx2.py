#!/usr/bin/env python3
"""Export and verify lossless KTX2 transport of PUBLIC alpha mip arrays."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.artwork_ktx2_bundle import export_ktx2_bundle, verify_ktx2_bundle


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--confirm-public', action='store_true', required=True)
    commands = parser.add_subparsers(dest='command', required=True)
    export = commands.add_parser('export')
    export.add_argument('--bundle', type=Path, required=True)
    export.add_argument('--output', type=Path, required=True)
    verify = commands.add_parser('verify')
    verify.add_argument('--bundle', type=Path, required=True)
    verify.add_argument('--source-bundle', type=Path)
    args = parser.parse_args()
    try:
        if args.command == 'export':
            export_ktx2_bundle(args.bundle, args.output, confirm_public=args.confirm_public)
            result = verify_ktx2_bundle(args.output, source_bundle=args.bundle)
            result['output'] = str(args.output)
        else:
            result = verify_ktx2_bundle(args.bundle, source_bundle=args.source_bundle)
        print(json.dumps(result, indent=2))
    except (ValueError, OSError, KeyError, TypeError) as exc:
        print(f'KTX2 export/verify failed: {exc}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
