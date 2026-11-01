#!/usr/bin/env python3
"""Prepare, or build and qualify, a desktop player; never touches an existing Unity project."""
from pathlib import Path
import argparse
import json
import os
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'integrations/framerudiments')]
from tools.artwork_unity_player import prepare_player_project, run_player_qualification, TARGETS


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--confirm-public', action='store_true')
    parser.add_argument('--prepare-only', action='store_true', help='Write project inputs; does NOT qualify a build or GPU')
    parser.add_argument('--bundle', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--unity', type=Path, default=os.environ.get('UNITY_EDITOR'))
    parser.add_argument('--target', choices=tuple(TARGETS), required=True)
    parser.add_argument('--editor-version', default=os.environ.get('BYTEFABLES_UNITY_EDITOR_VERSION', '6000.0.62f1'))
    parser.add_argument('--build-timeout', type=int, default=1800)
    parser.add_argument('--player-timeout', type=int, default=600)
    args = parser.parse_args()
    try:
        options = dict(confirm_public=args.confirm_public, target=args.target, editor_version=args.editor_version)
        if args.prepare_only:
            result = prepare_player_project(args.bundle, args.output, **options)
        else:
            if args.unity is None:
                raise ValueError('--unity or UNITY_EDITOR must identify an installed Unity executable')
            result = run_player_qualification(args.unity, args.bundle, args.output,
                build_timeout=args.build_timeout, player_timeout=args.player_timeout, **options)
        print(json.dumps(result, indent=2))
        return 0
    except Exception as exc:
        print(f'Unity player qualification failed: {exc}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
