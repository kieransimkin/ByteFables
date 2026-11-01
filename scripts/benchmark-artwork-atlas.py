#!/usr/bin/env python3
"""Render PUBLIC synthetic artwork atlas suites using the real FrameRudiments host."""
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
    parser.add_argument('--synthetic-fixture', action='store_true', required=True,
                        help='Explicitly create/use a labelled silent PCM clock fixture; no music claims')
    parser.add_argument('--suite', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True, help='New output directory; never overwritten')
    parser.add_argument('--samples', type=int, default=3, help='1..5 timed frame seeks per page')
    args = parser.parse_args(argv)
    try:
        from tools.artwork_native_benchmark import run_benchmark
        report = run_benchmark(args.suite, args.output, confirm_public=args.confirm_public,
                               synthetic_fixture=args.synthetic_fixture, samples=args.samples)
    except (ValueError, OSError, ImportError, RuntimeError) as exc:
        parser.exit(2, f'Native artwork benchmark failed: {exc}\n')
    print(json.dumps({'output': str(args.output.resolve()), 'cases': len(report['cases']),
                      'nativeHostExecuted': report['nativeHostExecuted'], 'status': report['status']}, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
