# Native artwork render benchmark v1

**Milestone:** BF-W6 / BF-W7 / BF-W9, native image-output evidence. Word-based
codecs are unchanged. This implements benchmark orchestration and a bounded
offline image gallery, not a replacement renderer or wallet-backup feature.

## What runs

1. `scripts/prepare-artwork-benchmark.mjs` uses the existing `ByteValue`,
   `PublicRecord` and `createFrameRudimentsArtworkAtlas` APIs. The public fixture
   corpus is SHA-256 of domain `ByteFables:artwork-benchmark-corpus:v1\0`, the
   ASCII seed label, NUL and the decimal input index. Its namespace is
   `bytefables-benchmark`, kind `fixture-id`, network `synthetic`.
2. The planner writes hash-pinned native atlas JSON files and `suite.json`.
   Identical public seed/count/options produce identical plans. All cases must
   use the same ordered, distinct identity corpus. No raw secret inputs exist.
3. `scripts/benchmark-artwork-atlas.py` **requires the actual FrameRudiments
   installation**. It creates a real `Project`, a native `RendererRegistry`
   containing the existing `bytefables-artwork-v1` factory, and a `Compositor`.
   `Compositor.frame()` owns all source rendering and composition. There is no
   fake host, Pillow-based production compositor or fallback rendering mode.
4. The native compositor's RGB frames are saved as PNG. Existing independent
   readback checks saved file CRCs, zlib/pixels, dimensions, RGBA pixel hashes,
   per-tile analysis, 16/32/64/128 viewing scales and dHash comparisons.
5. A separate source-on-matte comparison checks every saved tile against the
   registered source generator over the fixed `#111827` background. It also
   verifies **all gutters and unused cells**, and records source alpha coverage
   separately from opaque output coverage. The old transparent `--compare-source`
   mode is deliberately not misused on opaque compositor output.
6. Frame 0 is rendered cold, then frames 1/0 are sampled repeatedly. All pixels
   must stay identical because this suite uses static sources and no effects.
   Project setup, cold rendering, warm frame samples, PNG encoding and readback
   have separate timings. Results are machine-dependent, not an FPS guarantee.
7. The runner saves `readback.json`, native project JSON and PNGs per case,
   `report.json`, and an offline `index.html` gallery. HTML has no scripts,
   external resources or model inference. Page links open original image pixels.

Each **native source size** is rendered independently; 16px results are not
merely downsampled 128px images. Readback's resampled viewing-scale statistics
remain separately labelled. Perceptual dHash matches are diagnostic; they are
not cryptographic collisions, measured human confusion, or proof of ownership.
The reference shares the source artwork algorithm, so it checks composition and
export consistency, not independently proved visual meaning.

## Explicit synthetic clock fixture

FrameRudiments requires pinned audio/clock provenance even for a sampled frame.
This benchmark is deliberately **not a general still-image export API**. It
requires `--synthetic-fixture` to generate a genuine one-second, mono, 48kHz,
16-bit silent PCM WAV. Every native page project pins that file's SHA-256 and
labels the clock `synthetic` with a benchmark-only authority. No production song,
measured tempo, font, external media or fictitious music analysis is substituted.

Native frame postprocessing is disabled for exact source-on-matte verification;
there are no captions, motion effects, quality filters, masks or effect graphs.
Those need a separate acceptance profile. The runner verifies host inputs before
and after rendering, records host Python source-tree and generator-file hashes,
and records Python, platform, FrameRudiments, DanceRudiments and Pillow versions.
These are reproducibility metadata, not signed provenance/authentication.

## Run on Windows / PowerShell

From ByteFables, after `npm ci` and `npm run build`:

```powershell
node scripts/prepare-artwork-benchmark.mjs --confirm-public --output _work/artwork-suite

uv run --python 3.11 --with "Pillow==12.3.0" --with "numpy>=1.26" --with "framerudiments @ git+https://github.com/kieransimkin/FrameRudiments.git@de0b4bb37e3b0b827f3367dac40eae4fe9faa0d7" --with-editable ./integrations/framerudiments python scripts/benchmark-artwork-atlas.py --confirm-public --synthetic-fixture --suite _work/artwork-suite/suite.json --output _work/artwork-benchmark

Start-Process .\_work\artwork-benchmark\index.html
```

The `uv` command installs the explicitly named local runtime/dependencies; the
benchmark itself performs no downloads or network requests. Git must be installed
for the pinned host source URL. An already prepared native Python environment can
run the same `python scripts/benchmark-artwork-atlas.py ...` command directly.
For Bash, use the same commands and open `_work/artwork-benchmark/index.html`.
Both suite and output paths must be **new directories** on each invocation.

Default: 32 synthetic identities, nine families, neon palette, four native sizes:
36 cases / 1,152 native tiles. To compare all palettes, pass
`--palettes neon,pastel,mono` to the planner. A bounded 1,000-node case is:

```sh
node scripts/prepare-artwork-benchmark.mjs --confirm-public --count 1000 --families sigil --sizes 32 --output _work/artwork-1000
```

Inputs are bounded to 1,000 identities/case, 108 cases, 8,192 total source tiles,
16 million viewing-scale pair comparisons and 268,435,456 aggregate page pixels.
The existing readback's per-page/PNG limits still apply. More styles/counts must
be split across runs, not used to evade the budgets. Timing samples are 1..5.
No performance threshold, colour-vision qualification or human-recognition
score is invented by these measurements.

## Failure handling and input restrictions

All plans are checked before native host loading or output creation: no path
traversal, symlinked plan files/directories, duplicate IDs, substituted corpus,
changed plan hashes, non-finite JSON, unknown fields or arbitrary motion/effect
configuration. The benchmark accepts only the existing static artwork-atlas
contract. Previously existing output directories are refused, even if empty.

A failed run leaves diagnostic `failure.json` and possibly partial PNGs; it
never publishes `report.json` as a successful run. The final success marker is
written after all readback/comparison and gallery work. The native integration
CI job installs the pinned real host and sets `BYTEFABLES_REQUIRE_NATIVE=1`:
missing host means failure, not an accepted skipped render test. Full repository
`npm run check` remains a separate gate.

## Small-cell renderer regression repair

The previously accepted cellular 16px / complexity-4 configuration crashed:
its cell pitch was below one pixel, producing reversed rectangle endpoints.
Subpixel cells now sample their centres with a single point. The old rectangle
path is unchanged when pitch is at least one pixel, preserving its pixels.
At 32px the same repair also covers the high-complexity subpixel case.
This repairs previously undefined/error output, not a re-versioning of existing
successful seed mappings. Runtime/generator source hashes identify the fix.

Tests render all nine families and three palettes at 16/32/64/128, exercise the
cellular complexity range, check real PNGs and source-on-matte readback, reject
altered gutters/tiles, and exercise a real native compositor when installed.
The existing transparent source readback and V1 TS APIs remain unchanged.

## Roadmap accounting

Implemented here: native benchmark orchestration, real PNG persistence/readback,
exact source-on-matte/layout validation, per-resolution diagnostics, repeatability
and timing measurements, offline gallery, mandatory native integration workflow.

Still separate: actual CI execution results, larger-corpus results on target
hardware, measured human recognition and colour accessibility, effect-enabled
acceptance, WebP/ICO/KTX2 exports, mipmaps, a production native still-export API,
and GPU/Unity resource-lifetime/performance validation. Image identity remains
presentation-only and never substitutes for the full public identifier.

References: the pinned FrameRudiments `docs/rudiment-renderers.md`,
`src/framerudiments/project.py` and `src/framerudiments/compositor.py`;
ByteFables `docs/specs/frame-bridge-v1.md`; Pillow's `Image.open`, `load`, and
`alpha_composite` contracts at https://pillow.readthedocs.io/en/stable/reference/Image.html.
