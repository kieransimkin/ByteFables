#!/usr/bin/env python3
"""Export/verify source-alpha sprites; optionally qualify on two REAL native mattes."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.artwork_transparent_bundle import (
    export_transparent_bundle, verify_transparent_bundle, qualify_native_mattes,
)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--confirm-public', action='store_true', required=True)
    sub = parser.add_subparsers(dest='command', required=True)
    export = sub.add_parser('export')
    export.add_argument('--suite', type=Path, required=True)
    export.add_argument('--benchmark', type=Path, required=True)
    export.add_argument('--output', type=Path, required=True)
    export.add_argument('--formats', default='png,webp,ico')
    verify = sub.add_parser('verify')
    verify.add_argument('--bundle', type=Path, required=True)
    qualify = sub.add_parser('qualify')
    for key in ('suite', 'benchmark', 'bundle', 'output'):
        qualify.add_argument('--' + key, type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == 'export':
            result = export_transparent_bundle(args.suite, args.benchmark, args.output,
                confirm_public=args.confirm_public, formats=args.formats.split(','))
            summary = {'status': 'passed', 'assets': result['assetCount'], 'alpha': result['alpha'],
                       'output': str(args.output), 'nativeHostRerunByExporter': False}
        elif args.command == 'verify':
            summary = verify_transparent_bundle(args.bundle)
        else:
            result = qualify_native_mattes(args.suite, args.benchmark, args.bundle, args.output,
                                          confirm_public=args.confirm_public)
            summary = {'status': result['status'], 'nativeHostExecuted': True,
                       'tilesPerMatte': result['tilesPerMatte'], 'pages': len(result['pages'])}
        print(json.dumps(summary, indent=2))
        return 0
    except Exception as exc:
        print(json.dumps({'status': 'failed', 'exception': type(exc).__name__, 'message': str(exc)[:1000]}),
              file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
