# ByteFables public artwork atlas readback v1

**Status:** experimental image-output QA; **not** a renderer, recovery codec,
proof of identity, wallet backup or independent authentication. This milestone
adds independent **decoded-pixel inspection** on top of the v1 atlas planner,
PNG CRC checks and existing byte-level export receipts.

## Boundaries

- ByteFables TypeScript still owns **only** the `artwork-atlas.v1` layout and
  full public identity commitments. FrameRudiments owns every generated pixel,
  source renderer, compositor, effect, and PNG export.
- `tools/artwork_atlas_readback.py` uses **Pillow** independently to decode
  *saved PNG files*, including compressed IDAT bytes and all image filters;
  it does **not** rasterise glyphs or add effects. The already-frozen native
  `ArtworkRenderer` is used *only* when exact source-only comparison is requested.
- It validates PNG signature, bounded layout, every chunk CRC, expected
  dimensions and actual decompressed pixels. It rejects corrupted zlib data
  even when an attacker recomputes the PNG chunk CRCs.
- This proves that specific image files can be decoded, not that they are the
  intended identity artwork. Use `--compare-source` on **unmodified, transparent
  source-only** exports to compare each tile pixel-for-pixel against its native
  FrameRudiments registered generator. Composited backgrounds, antialiasing,
  scaling, masks and effects will appropriately fail this exact comparison;
  omit that flag for ordinary processed renders.
- You may provide `--expect-receipt` with a previous `createArtworkPngReceipt`
  JSON, binding the independent decoded image report to the exact exported PNG
  file digests. The receipt itself still is not an authenticity signature.

## Files and usage

Generate a public atlas plan in JS using
`createFrameRudimentsArtworkAtlas(records, options)` and save it as `plan.json`.
The **existing** FrameRudiments renderer must export one PNG per page, using
`atlas-page-000.png`, `atlas-page-001.png`, etc., into one directory. Filenames
are deliberately fixed and never obtained from untrusted plan JSON.

```sh
python scripts/verify-artwork-atlas.py --confirm-public \
  --plan plan.json --pages-dir exported-pages \
  --report exported-pages/readback.json
```

For source-only exports or comparison with the previous TypeScript receipt:

```sh
python scripts/verify-artwork-atlas.py --confirm-public \
  --plan plan.json --pages-dir exported-pages \
  --expect-receipt exported-pages/receipt.json \
  --compare-source --fail-on-blank \
  --report exported-pages/readback.json
```

Requirements: Python 3.11+ and `Pillow>=10,<13` (already declared by
`integrations/framerudiments/pyproject.toml`). `--compare-source` additionally
needs the in-tree FrameRudiments Python adapter or its installed equivalent.
The verifier never fetches models or contacts network services. A failed check
exits nonzero **without writing a new report**. Reports are atomically replaced
only after all pages and tiles validate.

To run the Python tests (also covered by the existing
`framerudiments-generator-contract` GitHub CI job):

```sh
python -m unittest discover -s tests/python -p 'test_artwork_atlas_readback.py' -v
```

Tests use real compressed PNGs, deliberately damaged CRCs, valid-CRC invalid
DEFLATE, two-page receipts, malformed plans, blank tiles, the existing native
source generator for all nine families and an actual TS-generated public plan
when `npm run build` has been run. No new runtime dependency is added to the
TypeScript foundation.

## Report format and metrics

Schema: `bytefables.artwork-atlas-readback.v1`.

- Per page: exact file SHA-256, dimensions, file length, SHA-256 of decoded
  RGBA bytes (not just the compressed file), and tile count.
- Per tile: original public record digest and native layer ID, decoded RGBA
  SHA-256, alpha coverage, 32px luminance-contrast standard deviation and
  blank/uniform warning. A 16/32/64/128px resized RGB pixel hash and
  **64-bit difference hash (dHash)** are stored for each resolution.
- Per resolution: number of *distinct-identity* comparisons, exact dHash
  collisions, distances within four bits, minimum Hamming distance and up to
  12 nearest pairs. Matching digest pairs are excluded from collision counts.
- Source comparison status and optional native Python renderer-source SHA-256,
  Pillow version, and whether the earlier TypeScript exact-file receipt matched.
- `planCanonicalJsonSha256` hashes the parsed JSON reserialised with Python's
  documented sorted-key/compact encoding. It is a report provenance hint,
  **not** a cross-language canonical JSON wire standard.

All such measurements are **diagnostic proxies**. dHash collisions do not prove
actual perceptual confusion, and dHash distance does not prove distinctiveness
or cryptographic security. Human blinded recognition tests, accessibility
reviews, renderer-version baselines and processed native FrameRudiments image
readback remain separate release gates.

## Limits and safety

Only `publicOnly: true`, `guarantee: presentation-only` v1 atlas plans and
`bytefables-artwork-v1` layers are accepted. Plan JSON <=4 MiB; 1..1,000
inputs and pages; image page coordinates <=7,680; decoded pixels/page
<=16,777,216; PNG file <=128 MiB; source image dimensions obey the plugin's
2,048-side / 1,048,576-pixel limits. All original source bytes, wallet secrets
and arbitrary paths in plan JSON are excluded. Reports contain only public
metadata and fingerprints. Resampling uses a fixed opaque viewing background
and Pillow LANCZOS; include the captured Pillow version when comparing runs.

This **does not yet** certify that a full FrameRudiments timeline/compositor,
FFmpeg video stream or colour-managed production export matches its source;
that requires a separately installed host-render acceptance test with exact
project, font and effect provenance. Identity art is never reversible binary
storage, no matter how good its PNGs look.
