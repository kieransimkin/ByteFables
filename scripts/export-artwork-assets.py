#!/usr/bin/env python3
"""Export lossless PUBLIC image assets from a completed native artwork benchmark."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--confirm-public', action='store_true', required=True)
    sub = parser.add_subparsers(dest='command', required=True)
    export = sub.add_parser('export', help='Read native evidence and create a new asset bundle')
    export.add_argument('--suite', type=Path, required=True)
    export.add_argument('--benchmark', type=Path, required=True)
    export.add_argument('--output', type=Path, required=True)
    export.add_argument('--formats', default='png,webp,ico', help='png required; optional webp,ico')
    verify = sub.add_parser('verify', help='Re-read all saved assets and verify decoded pixels')
    verify.add_argument('--bundle', type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        from tools.artwork_asset_bundle import export_asset_bundle, verify_asset_bundle
        if args.command == 'export':
            manifest = export_asset_bundle(args.suite, args.benchmark, args.output,
                confirm_public=args.confirm_public, formats=args.formats.split(','))
            result = {'status': manifest['status'], 'assets': manifest['assetCount'],
                      'formats': manifest['formats'], 'output': str(args.output.absolute())}
        else:
            result = verify_asset_bundle(args.bundle)
    except (ValueError, OSError, ImportError, RuntimeError, TypeError) as exc:
        parser.exit(2, f'Artwork asset bundle failed: {exc}\n')
    print(json.dumps(result, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
