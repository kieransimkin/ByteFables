#!/usr/bin/env python3
"""Independently decode exported PUBLIC FrameRudiments artwork atlases.

The plan is JSON from createFrameRudimentsArtworkAtlas(). PNG filenames must be
atlas-page-000.png, atlas-page-001.png, ... under the supplied directory.
No image rendering happens here; only post-export readback and QA metrics.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.artwork_atlas_readback import (  # noqa: E402
    AtlasReadbackError, load_atlas_plan, load_expected_receipt, readback_artwork_atlas
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--confirm-public", action="store_true", required=True,
                        help="Explicitly confirm the plan contains PUBLIC identities only")
    parser.add_argument("--plan", type=Path, required=True,
                        help="JSON output of createFrameRudimentsArtworkAtlas()")
    parser.add_argument("--pages-dir", type=Path, required=True,
                        help="Directory of atlas-page-000.png, atlas-page-001.png, ...")
    parser.add_argument("--report", type=Path, required=True,
                        help="Output JSON receipt; written atomically only on successful validation")
    parser.add_argument("--expect-receipt", type=Path,
                        help="Optional TS createArtworkPngReceipt() JSON; verify exact exported file SHA-256")
    parser.add_argument("--compare-source", action="store_true",
                        help="Require pixel-exact match with native artwork generator; SOURCE-ONLY PNGs")
    parser.add_argument("--fail-on-blank", action="store_true",
                        help="Reject completely blank or nearly uniform tiles")
    args = parser.parse_args(argv)
    try:
        plan = load_atlas_plan(args.plan)
        expected = load_expected_receipt(args.expect_receipt) if args.expect_receipt else None
        receipt = readback_artwork_atlas(plan, args.pages_dir,
                                        compare_source=args.compare_source,
                                        fail_on_blank=args.fail_on_blank,
                                        expected_receipt=expected)
        output = args.report.resolve()
        output.parent.mkdir(parents=True, exist_ok=True)
        # Avoid accidentally overwriting one of the input image files or the plan.
        if output == args.plan.resolve() or output.suffix.lower() != ".json":
            raise AtlasReadbackError("Report must be a different .json file")
        payload = (json.dumps(receipt, indent=2, ensure_ascii=True, allow_nan=False) + "\n").encode("utf-8")
        fd, tmp = tempfile.mkstemp(prefix=".artwork-readback-", suffix=".tmp", dir=output.parent)
        try:
            with os.fdopen(fd, "wb") as handle:
                handle.write(payload)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(tmp, output)
        finally:
            Path(tmp).unlink(missing_ok=True)
    except (AtlasReadbackError, OSError, ImportError) as exc:
        parser.exit(2, f"Artwork readback failed: {exc}\n")
    print(json.dumps({"report": str(output), "pages": len(receipt["pages"]),
                      "tiles": receipt["inputCount"],
                      "sourcePixelsComparison": receipt["sourcePixelsComparison"],
                      "exportReceiptComparison": receipt["exportReceiptComparison"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
