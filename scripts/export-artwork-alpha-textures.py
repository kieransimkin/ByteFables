#!/usr/bin/env python3
"""Export or verify isolated premultiplied RGBA texture arrays for PUBLIC artwork."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.artwork_alpha_textures import export_alpha_textures, verify_alpha_textures


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--confirm-public', action='store_true', required=True)
    commands = parser.add_subparsers(dest='command', required=True)
    export = commands.add_parser('export')
    export.add_argument('--bundle', type=Path, required=True)
    export.add_argument('--output', type=Path, required=True)
    export.add_argument('--native-size', type=int, choices=(16,32,64,128), default=64)
    export.add_argument('--layers-per-bank', type=int, default=128)
    verify = commands.add_parser('verify')
    verify.add_argument('--bundle', type=Path, required=True)
    verify.add_argument('--source-bundle', type=Path)
    args = parser.parse_args()
    try:
        if args.command == 'export':
            doc = export_alpha_textures(args.bundle,args.output,confirm_public=args.confirm_public,
                                       native_size=args.native_size,layers_per_bank=args.layers_per_bank)
            result = {'status':doc['status'],'sprites':doc['spriteCount'],'banks':len(doc['banks']),
                      'levelsPerSprite':doc['levelCount'],'payloadBytes':doc['payloadBytes'],'output':str(args.output)}
        else:
            result = verify_alpha_textures(args.bundle,source_bundle=args.source_bundle)
        print(json.dumps(result,indent=2))
    except (ValueError,OSError,KeyError,TypeError) as exc:
        print(f'Alpha texture export/verify failed: {exc}',file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
