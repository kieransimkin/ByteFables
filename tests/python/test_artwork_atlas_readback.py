"""Real decoded-pixel QA for public artwork, including adversarial PNG fixtures."""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from tools.artwork_atlas_readback import (
    ATLAS_VERSION, BRIDGE_VERSION, AtlasReadbackError,
    validate_atlas_plan, readback_artwork_atlas, load_atlas_plan, verify_export_receipt
)


def sample_plan(digests: tuple[str, ...] = ("01" * 32, "02" * 32),
                *, artwork: str = "sigil", palette: str = "neon"):
    width = 160
    height = 80
    tiles = []
    for index, digest in enumerate(digests):
        x = index * 80 + 8
        rect = [x, 8, x + 64, 72]
        tiles.append({
            "inputIndex": index, "digestHex": digest,
            "rect": rect, "uv": [rect[0] / width, rect[1] / height,
                                    rect[2] / width, rect[3] / height],
            "layer": {
                "id": f"atlas-0-{index}", "type": "rudiment",
                "renderer": "bytefables-artwork-v1", "bounds": rect,
                "motion": {"kind": "named", "pattern": "circle"},
                "axes": [0], "history_frames": 1,
                "style": {"bridge_version": BRIDGE_VERSION, "digest_hex": digest,
                          "style": artwork, "palette": palette, "complexity": 4},
            }
        })
    return {"version": ATLAS_VERSION, "publicOnly": True,
            "guarantee": "presentation-only", "inputCount": len(tiles),
            "pages": [{"index": 0, "width": width, "height": height, "tiles": tiles}]}


def make_png(path: Path, *, mutate: bool = False):
    image = Image.new("RGBA", (160, 80), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw.rectangle((12, 12, 65, 63), fill=(232, 50, 80, 255))
    draw.ellipse((90, 16, 145, 66), fill=(30, 200, 210, 255))
    if mutate:
        draw.point((29, 29), fill=(19, 19, 19, 255))
    image.save(path, format="PNG")


class ArtworkAtlasReadback(unittest.TestCase):
    def test_real_png_pixels_hashes_scales_and_similarity_are_reproducible(self):
        plan = sample_plan()
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            path = directory / "atlas-page-000.png"
            make_png(path)
            report = readback_artwork_atlas(plan, directory)
            self.assertEqual(report["schema"], "bytefables.artwork-atlas-readback.v1")
            self.assertEqual(report["sourcePixelsComparison"], "not-run")
            self.assertEqual(report["inputCount"], 2)
            self.assertEqual(len(report["tiles"]), 2)
            self.assertEqual(report, readback_artwork_atlas(plan, directory))
            self.assertEqual(len(report["pages"][0]["fileSha256"]), 64)
            self.assertEqual(len(report["pages"][0]["decodedRGBAsha256"]), 64)
            self.assertEqual(report["similarity"]["16"]["distinctIdentityPairs"], 1)
            self.assertGreater(report["tiles"][0]["quality"]["alphaCoverage"], 0.1)
            self.assertFalse(report["tiles"][0]["quality"]["blankOrUniform"])
            sha_before = report["tiles"][0]["quality"]["decodedRGBAsha256"]
            make_png(path, mutate=True)
            changed = readback_artwork_atlas(plan, directory)
            self.assertNotEqual(sha_before, changed["tiles"][0]["quality"]["decodedRGBAsha256"])

    def test_rejects_real_png_corruption_and_invalid_deflate_with_valid_crc(self):
        plan = sample_plan()
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            path = directory / "atlas-page-000.png"
            make_png(path)
            png = bytearray(path.read_bytes())
            self.assertEqual(readback_artwork_atlas(plan, directory)["inputCount"], 2)
            png[44] ^= 1
            path.write_bytes(png)
            with self.assertRaisesRegex(AtlasReadbackError, "CRC|decompression"):
                readback_artwork_atlas(plan, directory)
            # A re-checksummed PNG may still have an invalid DEFLATE stream.
            make_png(path)
            png = bytearray(path.read_bytes())
            import zlib
            pos = 8
            while pos < len(png):
                length = int.from_bytes(png[pos:pos + 4], "big")
                kind = bytes(png[pos + 4:pos + 8])
                end = pos + 12 + length
                if kind == b"IDAT":
                    png[pos + 8] = 0  # Invalid zlib CMF byte.
                    png[end - 4:end] = zlib.crc32(png[pos + 4:end - 4]).to_bytes(4, "big")
                    break
                pos = end
            path.write_bytes(png)
            with self.assertRaisesRegex(AtlasReadbackError, "decompression|pixel"):
                readback_artwork_atlas(plan, directory)

    def test_plan_bounds_and_public_only_gate(self):
        plan = sample_plan()
        validate_atlas_plan(plan)
        for broken in (
            {**plan, "publicOnly": False},
            {**plan, "inputCount": 3},
            {**plan, "pages": [dict(plan["pages"][0], index=1)]},
            {**plan, "pages": [dict(plan["pages"][0], width=1)]},
        ):
            with self.assertRaises(AtlasReadbackError):
                validate_atlas_plan(broken)
        duplicated = json.loads(json.dumps(plan))
        duplicated["pages"][0]["tiles"][1]["inputIndex"] = 0
        with self.assertRaisesRegex(AtlasReadbackError, "Duplicate"):
            validate_atlas_plan(duplicated)
        wrong_digest = json.loads(json.dumps(plan))
        wrong_digest["pages"][0]["tiles"][0]["layer"]["style"]["digest_hex"] = "aa" * 32
        with self.assertRaisesRegex(AtlasReadbackError, "digest mismatch"):
            validate_atlas_plan(wrong_digest)
        overlapping = json.loads(json.dumps(plan))
        overlapping["pages"][0]["tiles"][1]["rect"] = [8, 8, 72, 72]
        with self.assertRaisesRegex(AtlasReadbackError, "Overlapping"):
            validate_atlas_plan(overlapping)

    def test_blank_tile_and_missing_page_failure(self):
        plan = sample_plan()
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            with self.assertRaises(AtlasReadbackError):
                readback_artwork_atlas(plan, directory)
            Image.new("RGBA", (160, 80), (0, 0, 0, 0)).save(directory / "atlas-page-000.png")
            report = readback_artwork_atlas(plan, directory)
            self.assertTrue(all(t["quality"]["blankOrUniform"] for t in report["tiles"]))
            with self.assertRaisesRegex(AtlasReadbackError, "Blank/uniform"):
                readback_artwork_atlas(plan, directory, fail_on_blank=True)

    def test_cli_stores_report_only_on_success(self):
        plan = sample_plan()
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            plan_file = directory / "plan.json"
            plan_file.write_text(json.dumps(plan), encoding="utf-8")
            out = directory / "report.json"
            command = [sys.executable, str(ROOT / "scripts" / "verify-artwork-atlas.py"),
                       "--confirm-public", "--plan", str(plan_file),
                       "--pages-dir", str(directory), "--report", str(out)]
            proc = subprocess.run(command, text=True, capture_output=True, timeout=30)
            self.assertNotEqual(proc.returncode, 0)
            self.assertFalse(out.exists())
            make_png(directory / "atlas-page-000.png")
            proc = subprocess.run(command, text=True, capture_output=True, timeout=30)
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertEqual(json.loads(out.read_text())["inputCount"], 2)
            self.assertEqual(load_atlas_plan(plan_file), plan)

    def test_export_receipt_binding_and_multiple_pages(self):
        plan = sample_plan()
        extra = sample_plan(("03" * 32, "04" * 32))
        extra_page = extra["pages"][0]
        extra_page["index"] = 1
        for tile in extra_page["tiles"]:
            tile["inputIndex"] += 2
            tile["layer"]["id"] = tile["layer"]["id"].replace("atlas-0-", "atlas-1-")
        plan["pages"].append(extra_page)
        plan["inputCount"] = 4
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            for page_index in range(2):
                make_png(directory / f"atlas-page-{page_index:03d}.png")
            report = readback_artwork_atlas(plan, directory)
            self.assertEqual(len(report["pages"]), 2)
            expected = {
                "version": "bytefables.artwork-export-receipt.v1",
                "atlasVersion": ATLAS_VERSION, "publicOnly": True,
                "guarantee": "presentation-only", "inputCount": 4,
                "pages": [{"pageIndex": pg["pageIndex"], "width": pg["width"],
                           "height": pg["height"], "byteLength": pg["fileBytes"],
                           "sha256Hex": pg["fileSha256"], "tileCount": pg["tileCount"]}
                          for pg in report["pages"]],
            }
            verified = readback_artwork_atlas(plan, directory, expected_receipt=expected)
            self.assertEqual(verified["exportReceiptComparison"], "passed")
            expected["pages"].reverse()
            verify_export_receipt(expected, plan, report["pages"])
            expected["pages"][0]["sha256Hex"] = "00" * 32
            with self.assertRaisesRegex(AtlasReadbackError, "receipt"):
                readback_artwork_atlas(plan, directory, expected_receipt=expected)
            (directory / "atlas-page-001.png").unlink()
            with self.assertRaises(AtlasReadbackError):
                readback_artwork_atlas(plan, directory)

    def test_typescript_atlas_plan_roundtrips_through_native_image_plugin(self):
        if not (ROOT / "dist" / "index.js").exists():
            self.skipTest("TypeScript dist/ not built (npm run build)")
        sys.path.insert(0, str(ROOT / "integrations" / "framerudiments"))
        try:
            from bytefables_framerudiments.artwork import ArtworkRenderer
        except ImportError:
            self.skipTest("Native FrameRudiments generator not installed")
        js = """import { ByteValue, PublicRecord, createFrameRudimentsArtworkAtlas } from './dist/index.js';
const records = [1,2].map(n=>new PublicRecord(ByteValue.public(Uint8Array.of(n),{
  namespace:'danceflow',kind:'node-id'})));
console.log(JSON.stringify(await createFrameRudimentsArtworkAtlas(records,{
  tileSize:64,padding:8,columns:2,rowsPerPage:1,
  artwork:'sigil',palette:'neon',complexity:4})));
"""
        child = subprocess.run(["node", "--input-type=module", "-e", js], cwd=ROOT,
                               capture_output=True, text=True, timeout=30)
        self.assertEqual(child.returncode, 0, child.stderr)
        plan = json.loads(child.stdout)
        validate_atlas_plan(plan)
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            page = Image.new("RGBA", (plan["pages"][0]["width"], plan["pages"][0]["height"]),
                             (0, 0, 0, 0))
            for tile in plan["pages"][0]["tiles"]:
                rect = tile["rect"]
                source = ArtworkRenderer((rect[2] - rect[0], rect[3] - rect[1]),
                                         tile["layer"]["style"]).render(None)
                page.paste(source, tuple(rect[:2]))
            page.save(directory / "atlas-page-000.png", format="PNG")
            checked = readback_artwork_atlas(plan, directory, compare_source=True)
            self.assertEqual(checked["sourcePixelsComparison"], "passed")
            self.assertEqual(checked["tiles"][0]["digestHex"],
                             plan["pages"][0]["tiles"][0]["digestHex"])

    def test_native_source_generator_pixels_survive_png_roundtrip(self):
        sys.path.insert(0, str(ROOT / "integrations" / "framerudiments"))
        try:
            from bytefables_framerudiments.artwork import ArtworkRenderer
        except ImportError:
            self.skipTest("FrameRudiments artwork plugin not installed in test environment")
        # A real native renderer generates the source pixels; the checker opens
        # the PNG independently and compares decoded pixels against that source.
        for family in ("sigil", "constellation", "heraldry", "topography", "crystal",
                       "mandala", "cellular", "branching", "orbital"):
            with self.subTest(family=family), tempfile.TemporaryDirectory() as tmp:
                directory = Path(tmp)
                plan = sample_plan(artwork=family)
                page = Image.new("RGBA", (160, 80), (0, 0, 0, 0))
                for tile in plan["pages"][0]["tiles"]:
                    source = ArtworkRenderer((64, 64), tile["layer"]["style"]).render(None)
                    page.paste(source, tuple(tile["rect"][:2]))
                page.save(directory / "atlas-page-000.png", format="PNG")
                receipt = readback_artwork_atlas(plan, directory, compare_source=True,
                                                 fail_on_blank=True)
                self.assertEqual(receipt["sourcePixelsComparison"], "passed")
                self.assertTrue(all(t["sourcePixelsMatch"] for t in receipt["tiles"]))
                altered = Image.open(directory / "atlas-page-000.png").convert("RGBA")
                altered.putpixel((32, 32), (0, 0, 0, 255))
                altered.save(directory / "atlas-page-000.png")
                with self.assertRaisesRegex(AtlasReadbackError, "pixel mismatch"):
                    readback_artwork_atlas(plan, directory, compare_source=True)


if __name__ == "__main__":
    unittest.main()
