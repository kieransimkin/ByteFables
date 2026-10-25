# Public QR recovery sheets via FrameRudiments

**Status:** experimental public-only card exporter. **No wallet-secret support.**
This adapter takes an existing ByteFables typed `PublicRecord`, uses the
`BFQR1` binary recovery codec to produce framed QR matrices, and returns a
versioned declarative `bytefables-public-card-v1` FrameRudiments layer for each
frame. It does not introduce a competing effects, animation or raster engine.

## Separation of responsibilities

- ByteFables owns full typed public digest, BFQR1 framing, CRC/SHA-256 checks,
  module grids, page order, explanatory text, and the immutable card manifest.
- FrameRudiments owns the actual registered PIL source generator, project-pinned
  font loading, pixels, effects pipeline, animation and final export.
- The optical region is *special*: never apply blur, glow, resampling, masks,
  overlays, colour changes, text or compositing effects to its cells or quiet
  zone. The plan marks every printed frame `excludedFromEffects: true` but
  an integration must enforce this policy. Caller-owned arbitrary effects
  can silently destroy scanner readability.
- Exported public PNG sheets can be independently scanned by OpenCV using
  `scripts/render-public-cards.py`; the script rejects a mismatched scan and
  writes SHA-256 receipts. This is **not** a substitute for validating real
  physical print media and actual camera/scanner combinations.

## Page design

Portrait page: 1024×1440 px recommended (minimum 640×960), RGBA on solid
white, with a black/white integer-pitch QR and at least a four-module quiet
zone. The page also includes `PUBLIC RECORD`, a frame/optional parity label,
full 256-bit `bfrec1-…` typed fingerprint, node namespace/kind and complete
public BFQR1 text in wrapped monospace as a transcription fallback.

A SHA-256-pinned TTF/OTF font in the FrameRudiments project is mandatory. The
reference CLI requires the caller to provide the font path **and** SHA-256,
refuses pre-populated output directories, and records the bytes of emitted PNGs.
The tool does not choose a system-dependent font implicitly. Fonts/text/layout
are bounded; undersized layouts fail rather than omitting transcription data.

## Commands

```sh
node bin/bytefables.mjs public-print-sheet --confirm-public \
  --public-hex 001122334455 --namespace danceflow --kind node-id \
  --fragment-bytes 48 > public-sheet.json

python scripts/render-public-cards.py --confirm-public \
  --input-json public-sheet.json --output output-public-pages \
  --font /absolute/pinned/font.ttf --font-sha256 FULL_SHA256
```

If the optional OpenCV scanner isn't available, one can explicitly set
`--allow-unscanned`, but the output must be labelled **NOT RECOVERY-QUALIFIED**.
No PDF/A, TIFF or laser-engraving interoperability is claimed by a 300dpi PNG
alone. Those require subsequent media-specific release tests.

## Failure tests

- Reject inconsistent type, raw/non-QR matrices, missing quiet zone, bad
  fingerprint, unsupported characters, non-pinned fonts, invalid sizes or
  untrusted extra style keys.
- Detect incomplete/mixed BFQR1 frames before declaring recovered bytes.
- Scanner-validate the **saved PNG**, not the in-memory array; exercise real
  physical copies before shipping permanent archive features.
- The full public identifier is a verification aid and does not by itself prove
  cryptographic ownership. No secret material may be printed by this module.
