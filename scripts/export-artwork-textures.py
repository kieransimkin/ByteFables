#!/usr/bin/env python3
"""Export/verify PUBLIC runtime texture atlases from verified native asset bundles."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools.artwork_texture_bundle import export_texture_bundle, verify_texture_bundle


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--confirm-public', action='store_true', required=True)
    commands = parser.add_subparsers(dest='command', required=True)
    export = commands.add_parser('export')
    export.add_argument('--bundle', type=Path, required=True)
    export.add_argument('--output', type=Path, required=True)
    export.add_argument('--native-size', type=int, choices=(16, 32, 64, 128), default=64)
    export.add_argument('--page-size', type=int, default=1024)
    export.add_argument('--padding', type=int, default=2)
    verify = commands.add_parser('verify')
    verify.add_argument('--bundle', type=Path, required=True)
    verify.add_argument('--source-bundle', type=Path)
    args = parser.parse_args()
    try:
        if args.command == 'export':
            manifest = export_texture_bundle(args.bundle, args.output, confirm_public=args.confirm_public,
                                             native_size=args.native_size, page_size=args.page_size, padding=args.padding)
            result = {'status': 'passed', 'sprites': manifest['spriteCount'], 'pages': len(manifest['pages']),
                      'output': str(args.output)}
        else:
            result = verify_texture_bundle(args.bundle, source_bundle=args.source_bundle)
        print(json.dumps(result, indent=2))
        return 0
    except (ValueError, OSError) as exc:
        print(f'Texture bundle failed: {exc}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
