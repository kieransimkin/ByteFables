"""Generate synthetic PUBLIC identity gallery using only registered FrameRudiments sources.

This is a demo/CI evidence aid, not an independent rendering engine or a
wallet backup. ByteFables supplies digest seeds/QR modules; the existing
FrameRudiments Pillow renderers generate the pixels.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "integrations" / "framerudiments"))
from PIL import Image
from bytefables_framerudiments.artwork import ArtworkRenderer
from bytefables_framerudiments.renderers import MatrixRenderer

FAMILIES = ("sigil", "constellation", "heraldry", "topography")


def cli(*args):
    return json.loads(subprocess.check_output(
        ["node", str(ROOT / "bin" / "bytefables.mjs"), *args],
        cwd=ROOT, text=True, timeout=45))


def write_png(path, image):
    image.save(path, format="PNG")
    return {"name": path.name, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}


def main():
    parser = argparse.ArgumentParser(description="FrameRudiments PUBLIC synthetic gallery")
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    output = args.output.resolve()
    if output.exists() and any(output.iterdir()):
        raise FileExistsError("Use an empty/new gallery directory")
    output.mkdir(parents=True, exist_ok=True)
    size = 128
    contact = Image.new("RGBA", (size * len(FAMILIES), size * 4), (13, 17, 28, 255))
    receipts = []
    for row in range(4):
        source = hashlib.sha256(f"ByteFables public gallery vector {row}".encode()).hexdigest()
        for col, family in enumerate(FAMILIES):
            data = cli("artwork-layer", "--confirm-public", "--public-hex", source,
                       "--namespace", "danceflow", "--kind", "node-id",
                       "--artwork", family, "--palette", "neon", "--complexity", "4")
            image = ArtworkRenderer((size, size), data["layer"]["style"]).render(None)
            contact.alpha_composite(image, (col * size, row * size))
            receipts.append({"row": row, "family": family, "fullFingerprint": data["fullFingerprint"],
                             "pixelSha256": hashlib.sha256(image.tobytes()).hexdigest()})
    sheet = output / "public-artwork-contact.png"
    sheet_receipt = write_png(sheet, contact)
    fixture = hashlib.sha256(b"ByteFables public QR gallery fixture").hexdigest()
    frames = cli("qr-public", "--confirm-public", "--public-hex", fixture,
                 "--namespace", "danceflow", "--kind", "node-id",
                 "--ecc", "Q", "--qr-mask", "0", "--fragment-bytes", "48",
                 "--include-layers", "--bounds", "0,0,480,480")
    qr_receipts = []
    for frame in frames["frames"]:
        img = MatrixRenderer((480, 480), frame["layer"]["style"]).render(None)
        p = output / f"qr-frame-{frame['index']:02}.png"
        qr_receipts.append({"index": frame["index"], "parity": frame["isParity"],
                            "text": frame["text"], **write_png(p, img)})
    manifest = {"schema": "bytefables.public-gallery-evidence.v1",
                "notice": "Synthetic public identity art and BFQR1 QR sheets, NOT wallet backups",
                "artwork": receipts, "sheet": sheet_receipt, "qr": qr_receipts}
    (output / "evidence.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {len(receipts)} public artwork tiles and {len(qr_receipts)} QR PNGs to {output}")


if __name__ == "__main__":
    main()
