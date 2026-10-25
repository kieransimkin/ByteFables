"""Offline PUBLIC BFQR1 printable PNG export with independent post-export optical readback.

Requires Python Pillow, SHA-256-pinned caller font, and OpenCV for default
optical verification. All source pixels come from the FrameRudiments registered
PublicRecoveryCardRenderer; there is no competing effects or scene engine.
NEVER use with private seeds, passwords or other sensitive materials.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "integrations" / "framerudiments"))
from bytefables_framerudiments.public_cards import PublicRecoveryCardRenderer


def render_sheet(document, directory, font_path, font_sha256, *, scanned=True):
    if not isinstance(document, dict) or document.get("schema") != "bytefables.public-recovery-sheet.v1":
        raise ValueError("Expected public-only BFQR1 recovery sheet plan")
    pages = document.get("frames")
    if not isinstance(pages, list) or not 1 <= len(pages) <= 64 or document.get("count") != len(pages):
        raise ValueError("Invalid public sheet page count")
    font_path = Path(font_path).resolve(strict=True)
    if not isinstance(font_sha256, str) or len(font_sha256) != 64 or hashlib.sha256(font_path.read_bytes()).hexdigest() != font_sha256:
        raise ValueError("Font checksum mismatch")
    if scanned:
        try:
            import cv2
        except ImportError as e:
            raise RuntimeError("OpenCV required for independent printed-artifact scan") from e
    directory = Path(directory).resolve()
    if directory.exists() and any(directory.iterdir()):
        raise FileExistsError("Print output directory must be new or empty")
    directory.mkdir(parents=True, exist_ok=True)
    receipts = []
    for i, page in enumerate(pages):
        if type(page) is not dict or page.get("index") != i or not page.get("excludedFromEffects"):
            raise ValueError("Unsafe/unsorted public card page")
        layer = page.get("layer")
        if not isinstance(layer, dict) or layer.get("renderer") != "bytefables-public-card-v1":
            raise ValueError("Card must be the registered FrameRudiments renderer")
        bounds = layer.get("bounds")
        if (not isinstance(bounds, list) or len(bounds) != 4 or not all(type(n) is int for n in bounds)):
            raise ValueError("Invalid FrameRudiments page bounds")
        w, h = bounds[2] - bounds[0], bounds[3] - bounds[1]
        if layer.get("style", {}).get("manual_text") != page.get("text"):
            raise ValueError("QR/manual source mismatch")
        card = PublicRecoveryCardRenderer((w, h), layer["style"])
        card.prepare(SimpleNamespace(font_ref={"path":str(font_path), "sha256":font_sha256}))
        image = card.render(None)
        output = directory / f"public-card-{i+1:03d}.png"
        image.save(output, format="PNG", dpi=(300, 300), optimize=False)
        if scanned:
            scanned_image = cv2.imread(str(output))
            actual, _, _ = cv2.QRCodeDetector().detectAndDecode(scanned_image)
            if actual != page["text"]:
                output.unlink(missing_ok=True)
                raise ValueError("Exported PNG QR was not independently recovered as exact text")
        receipts.append({"filename":output.name,"sha256":hashlib.sha256(output.read_bytes()).hexdigest(),
                         "sourceFrameIndex":i,"frameTextSha256":hashlib.sha256(page["text"].encode('ascii')).hexdigest(),
                         "independentOpticalScan": "passed" if scanned else "NOT RUN"})
    manifest = {"schema":"bytefables.public-card-render-receipt.v1",
                "source":"PUBLIC-BFQR1-only", "renderer":"framerudiments:bytefables-public-card-v1",
                "fontSha256":font_sha256,"pages":receipts,
                "warning":"PUBLIC identifiers only. PNG readability does not prove printed-media recovery."}
    (directory/"receipt.json").write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
    return manifest


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--confirm-public",action="store_true",required=True)
    p.add_argument("--input-json",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True)
    p.add_argument("--font",type=Path,required=True)
    p.add_argument("--font-sha256",required=True)
    p.add_argument("--allow-unscanned",action="store_true",
                   help="Explicitly omit independent scan; these exports are NOT recovery-qualified")
    a=p.parse_args()
    if not a.confirm_public:
        p.error("PUBLIC test-only confirmation required")
    if a.input_json.stat().st_size>5000000:
        p.error("Public sheet plan is too large")
    data=json.loads(a.input_json.read_text(encoding='utf-8'))
    manifest=render_sheet(data,a.output,a.font,a.font_sha256,scanned=not a.allow_unscanned)
    print(json.dumps({"pages":len(manifest['pages']),"output":str(a.output)},indent=2))


if __name__=="__main__":
    main()
