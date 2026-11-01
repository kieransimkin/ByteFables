# Native image asset bundles v1

**Milestone:** BF-W7 bitmap/web exports, building on BF-W6 native image evidence.
**Status:** experimental, public display assets only. Source drawing, compositing
and image effects remain owned by FrameRudiments. Word-based formats and existing
TypeScript wire formats are unchanged.

This increment adds lossless PNG/WebP tiles, multi-size ICO files, a local
filterable image gallery, a bounded manifest verifier, and a correction for the
native benchmark's inherited supersampling. It does not add a second renderer.

## Native benchmark prerequisite and CI repair

The native job for ByteFables `046cca409aa50902c74d7b3902185f52adc6c52c`
failed its exact source comparison. The separate general test workflow passed.
The pinned FrameRudiments host's `Compositor.frame(apply_quality=False)` skips
final antialiasing, **not** spatial or temporal supersampling. Its default
`OutputQuality` still selects four spatial samples per axis and eight temporal
samples. Comparing those rendered pixels with a native-resolution reference was
therefore the wrong benchmark configuration.

`project_for_page()` now explicitly emits `render_quality: {enabled: false}`.
Before creating the compositor, the runner requires effective `vector_scale`
and `time_samples` to be one. The reference comparison is not loosened, and no
mismatch tolerance, alternative renderer or skipped required native test is
introduced. Existing successful source-generator pixel mappings are untouched.
This acceptance profile deliberately measures **unfiltered native-resolution**
images, not the host's default quality-enhanced output.

Rerun the benchmark into a **new** directory after applying the patch. Failed or
older differently configured reports must not be relabelled as successful.
A real native CI rerun is required to confirm the end-to-end repair.

## Export pipeline

```text
hash-pinned TS suite and plans
    -> real FrameRudiments native benchmark + saved PNG readback
    -> verify report / clock / project / plan / page bindings
    -> crop each already-rendered native tile, without resampling
    -> host-integration PNG / lossless WebP / ICO encoders
    -> decode encoded bytes and compare every RGBA sample
    -> save each file, reopen it and compare bytes and decoded samples
    -> manifest.json + local gallery (success marker written last)
```

The native benchmark has already compared source-generator pixels composited on
`#111827` and verified gutters/unused cells. The exporter validates that evidence
and actual saved page hashes. It does **not** rerun FrameRudiments or independently
prove that an unsigned report came from the claimed host. A fabricated report
plus corresponding fabricated files can be internally consistent; trust the
producer and its source/CI separately.

The pixel-only image helpers live in the existing optional integration package:
`integrations/framerudiments/bytefables_framerudiments/image_assets.py`.
`tools/artwork_asset_bundle.py` orchestrates evidence checking and packaging;
`scripts/export-artwork-assets.py` exposes the CLI. There is no inference,
network request, scene renderer, clock, shader, animation or effect stack in
this exporter.

## Supported assets

| Output | v1 contract |
| --- | --- |
| PNG | One file per supplied native size; RGBA samples; level-6 lossless compression |
| WebP | One file per supplied native size; lossless with `exact=True`; decode must match all RGBA samples |
| ICO | PNG entries for the supplied 16/32/64/128 sizes; each entry is checked against its own native source |
| Gallery | Local HTML/CSS/classic JS; PNG previews; links to available formats; digest/family/palette/size filters |

PNG is required. WebP and ICO are optional. Missing WebP codec support fails
before output creation; explicitly select `--formats png,ico` rather than
silently substituting another format. A suite may contain a subset of the four
sizes. The exporter never invents a missing size, rescales a larger image, or
uses Pillow's automatic ICO downsampling in place of a supplied native image.
ICO directory bounds, distinct sizes, offsets and embedded PNG dimensions are
checked before decoding; every entry is decoded and compared afterwards.

The current native compositor returns **opaque, background-matted** pixels.
These bundles retain that matte, including in WebP and ICO. They do not recover
transparent source pixels from opaque PNGs. Images retain untagged RGB sample
values; EXIF/XMP/ICC/text metadata is not copied into encoded outputs. This is
not colour-management equivalence between displays or export environments.

## Use

Use the native benchmark instructions in [artwork-native-benchmark-v1.md](artwork-native-benchmark-v1.md)
to create a fresh suite and a successful benchmark. In the same prepared Python
environment, run from the repository root:

```powershell
python scripts/export-artwork-assets.py --confirm-public export --suite _work/artwork-suite/suite.json --benchmark _work/artwork-benchmark --output _work/artwork-assets --formats png,webp,ico
if ($LASTEXITCODE -ne 0) { throw "Image asset export failed." }

python scripts/export-artwork-assets.py --confirm-public verify --bundle _work/artwork-assets
if ($LASTEXITCODE -ne 0) { throw "Saved image verification failed." }

Start-Process .\_work\artwork-assets\index.html
```

For an isolated exporter environment (no native-host reinstall is needed for
this packaging step):

```powershell
uv run --python 3.11 --with "Pillow==12.3.0" --with-editable ./integrations/framerudiments python scripts/export-artwork-assets.py --confirm-public export --suite _work/artwork-suite/suite.json --benchmark _work/artwork-benchmark --output _work/artwork-assets
```

The explicit `uv` setup may install dependencies; the exporter itself never
downloads anything. Git and native host dependencies are needed for the earlier
benchmark, not for re-verifying an existing bundle. Use ordinary local paths;
symlinks, Windows junctions and other reparse-point paths are rejected.

The gallery uses no JSON fetch, ES modules, CDN, external fonts or network APIs.
It is designed for opening locally where browser policy permits. Managed
browsers may prohibit `file://`; it can also be served on loopback:

```powershell
python -m http.server 8765 --bind 127.0.0.1 --directory _work/artwork-assets
```

Open `http://127.0.0.1:8765/index.html`. This server exposes that directory to the
local machine only. The gallery renders at most 48 cards at once and shows the
selected native size without creating a fallback resolution. Full digests stay
visible; matching images are not identity authentication. There is no runtime
requirement for Playwright or Node to browse an already-exported bundle.

## Manifest and identity bindings

`manifest.json` has schema `bytefables.artwork-asset-bundle.v1`, `publicOnly: true`
and `guarantee: presentation-only`. It binds exact suite/report SHA-256 values,
page checksums, source crop rectangles, full public-record digests, style family,
palette, complexity and native sizes. Every image entry includes its byte length,
file SHA-256, and decoded RGBA SHA-256 for each frame. Viewer files have file
checksums too. Python/Pillow/libwebp versions and encoding options are recorded.

`assetKey` is `bfasset1-` plus SHA-256 of the repository's canonical JSON
serialization of this object:

```text
profile, family, palette, complexity, digestHex,
frames: [{size, rgbaSha256}, ...] in ascending native-size order
```

It identifies a pixel/style/version combination, not a promise of identical
encoded file bytes across different encoder builds. File digests identify exact
encoded bytes; the original full public-record identifier remains authoritative.
No namespace, public-key ownership or private material is inferred from a tile.

Files are stored under
`assets/<family>-<palette>-c<complexity>/<full-digest>/<size>.<format>`;
each style/digest group may additionally contain `icon.ico`. The standalone
verifier checks the exact required image inventory, duplicate IDs/paths, cache
key, checksums, source-frame relationships and all decoded frames. Its printed
`manifestSha256` is the actual manifest-file hash. Unreferenced extra files are
not treated as verified assets.

These are **unsigned consistency receipts**, not signed build provenance,
cryptographic ownership, source authentication, byte recovery, wallet backups
or measured human-recognition evidence.

## Limits and failures

The native suite limits still apply: at most 1,000 identities/case, 108 cases and
8,192 total source tiles, with the existing page/pixel/comparison budgets. Asset
bundles allow at most 512 MiB of written output, 24,576 written files, 2 MiB per
encoded image, and 16 MiB per manifest/report input. The combined output budget
includes the viewer and manifest; a workload near a limit may need splitting.

All source references must be canonical relative paths. URL/traversal paths,
symlinks/reparse points, changed hashes, duplicate JSON fields, substituted
plans, failure markers, unexpected project quality, missing formats, animation,
malformed containers and pixel mismatches fail closed. Output must be a new
directory outside either input evidence tree, even if an existing directory is
empty. The tool does not overwrite or repair earlier output in place.

On failure after output creation, partial files and `failure.json` remain for
inspection, but `manifest.json` is removed/not published. File checks are not a
hostile concurrent-filesystem sandbox: run against stable local files you own,
not directories being changed by another process while verification is running.

## Tests and qualification gates

- Python: real PNG/WebP/ICO encoding/decoding, hidden RGB under zero alpha,
  metadata removal, native ICO entries, bounded malformed ICO rejection,
  deterministic asset manifests, filesystem/evidence/manifest tampering,
  consent, failure handling and CLI exit codes. OpenCV provides an additional
  independent PNG/WebP pixel-decoder test where installed.
- Node: gallery DOM contract, filters, pagination, native-size selection,
  bounded visible cards, path allowlisting and safe text. The small DOM harness
  is **not** a browser visual-rendering test.
- Browser: `tests/browser/artwork-assets-smoke.py` serves a completed bundle
  on loopback and uses Chromium to check actual images, filters, native sizes,
  absence of external requests/errors and PNG/WebP pixel hashes via Canvas.
- Native CI: the existing required-host workflow now exports and re-verifies
  the bundle after native rendering, then runs the browser smoke test. Failure
  is not converted to success or a placeholder native render.

Codec tests construct clearly labelled **test evidence**, not native-render
proof. Only a successful real native run qualifies the host integration. The
current development environment passed codec, DOM and available regression tests,
but lacks the full native host/compiled TS distribution; its managed browser
blocked navigation. Native CI, full project checks and the served-page browser
test remain explicit release gates, not completed claims in this specification.

## Next image work

This closes the initial PNG/WebP/ICO bundle implementation in BF-W7. Separate
follow-on work remains for transparent native output, texture extrusion/mipmaps,
KTX2, GPU/Unity importers, more graphic families, effect-enabled export profiles,
real target-device performance, accessibility and human-recognition studies.
Do not substitute synthetic test pixels or a passing codec test for those gates.

## References

- Pillow ICO `sizes` / `append_images` and WebP `lossless` / `exact` parameters:
  https://pillow.readthedocs.io/en/stable/handbook/image-file-formats.html
- Pinned host: `kieransimkin/FrameRudiments` commit
  `de0b4bb37e3b0b827f3367dac40eae4fe9faa0d7`, files
  `src/framerudiments/output_quality.py`, `compositor.py`, `rudiment_renderers.py`.
- Observed failing native run: ByteFables Actions run `41276575058`, job
  `124759845415`, on source revision `046cca409aa50902c74d7b3902185f52adc6c52c`.
- [Programme roadmap](../IMPLEMENTATION_PLAN.md),
  [native benchmark](artwork-native-benchmark-v1.md), and
  [saved PNG readback](artwork-atlas-readback-v1.md).
