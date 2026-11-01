# Transparent native-source sprites v1

Image milestone after runtime texture atlases, based on ByteFables
`1d5497b5c2ae9af8359216c12fb329b59ae1d4d6`. Implements the transparent-source
acceptance work in [the image ledger](../IMAGE_OUTPUT_PROGRESS.md). Word-based
outputs, artwork generator seeds and the opaque texture v1 contract are unchanged.

## What is exported

This is a new **public-only, presentation-only** bundle with schema
`bytefables.transparent-artwork-bundle.v1` and profile
`bytefables.transparent-artwork-source.v1`. It saves the existing registered
`ArtworkRenderer`'s raw, straight/unassociated RGBA, **before** the compositor
adds a matte. It does not remove a background colour, estimate alpha, resize an
image, introduce another artwork algorithm, or recover raw identity bytes.
An opaque foreground pixel that happens to have the old background colour stays
opaque. Invisible RGB samples at alpha zero are preserved in file-codec checks.

PNG/WebP images are exported at the separately supplied native 16/32/64/128 sizes.
ICO uses those separate native PNG entries, never a resized largest image. PNG
metadata is stripped, WebP is lossless with `exact=True`, and every saved file is
reopened and decoded. A dependency upgrade is not promised byte-identical compressed
output; receipts bind exact files and decoded RGBA separately.

The source helper lives in the existing FrameRudiments integration package and
calls its unchanged artwork factory. FrameRudiments remains the rendering host.
No effects, clocks, shaders, compositor replacement, or animation pipeline is added.

## Evidence levels -- do not conflate them

1. **Export:** validates the completed original native benchmark, its suite,
   source plans, project settings, readback receipts and saved page pixels. The
   installed artwork Python file must have exactly the SHA-256 recorded in that
   benchmark. The exporter invokes that factory, checks repeated source pixels,
   and recomposites the source over the exact original `(17,24,39)` matte. The
   result must match the actual native atlas crop byte for byte. Export manifest
   explicitly reports `nativeHostRerunByExporter: false` and
   `additionalNativeMattes: "not-run"`.
2. **Verify:** reopens every output PNG/WebP/ICO, including all ICO entries,
   checks their exact RGBA, alpha statistics, declared original-matte RGB checksum,
   file digests, inventories and viewer bytes. This is consistency against an
   unsigned manifest, not independent proof of the claimed source.
3. **Qualify:** separately loads the real FrameRudiments `Project` and `Compositor`,
   re-renders every page on **black and white**, saves and decodes those native
   pages, and compares every pixel (including unused cells) to the saved source
   PNGs alpha-composited over each matte. Supersampling remains explicitly disabled.
   This command fails without the real host. It also rechecks the original native
   pages and exact identity/size/index coverage. The external
   `qualification.json` binds the bundle manifest and benchmark/suite hashes;
   it does not modify or retroactively relabel the export manifest.

The native and source-reference comparisons share the artwork algorithm. They
qualify source/export/compositing transport, not independent algorithm correctness,
cryptographic identity, visual uniqueness, authorization or recoverability.

## Commands

Run from the repository, with a **completed, successful** native benchmark and
its matching suite. Existing opaque asset/texture outputs need not be removed.
Use a new output directory for every export/qualification run.

```sh
python scripts/export-artwork-transparent.py --confirm-public export \
  --suite _work/artwork-suite/suite.json \
  --benchmark _work/artwork-benchmark \
  --output _work/artwork-transparent

python scripts/export-artwork-transparent.py --confirm-public verify \
  --bundle _work/artwork-transparent

python scripts/export-artwork-transparent.py --confirm-public qualify \
  --suite _work/artwork-suite/suite.json \
  --benchmark _work/artwork-benchmark \
  --bundle _work/artwork-transparent \
  --output _work/artwork-transparent-qualified
```

Export needs the existing plugin/Pillow and matching benchmark provenance, but
not a new native compositor execution. Qualification needs the installed native
host and its existing dependencies. A generator file hash mismatch fails rather
than quietly accepting newly rendered art; rerun the benchmark in the same source
checkout/environment. Raw file hashing intentionally also detects line-ending
changes when moving evidence between environments.

To omit WebP explicitly on a system without that codec, use `--formats png,ico`.
PNG is required and there is no silent lossy fallback. No dependencies or model
weights are downloaded by these commands.

## Manifest and layout

Each family/palette/complexity/full-public-digest group contains `nativeSizes`,
`files` with per-frame RGBA checksums, and `sources` with:

- Native size, original case/page/input indices and original matte RGB checksum.
- Raw RGBA checksum, separate alpha checksum, counts of alpha=0, alpha=255 and
  intermediate alpha pixels. Counts are integer sample counts, not a visual score.

Paths stay `assets/FAMILY-PALETTE-cN/DIGEST/SIZE.png`, `.webp`, and `icon.ico`.
A static `index.html` displays the **same transparent PNG** on checkerboard, black
and white CSS backgrounds with native-size download links. There is no JavaScript,
network service, external font or telemetry. The page CSP disables scripts and
external resources; an inline CSS block is explicitly allowed for the self-contained
preview. Existing gallery/runtime CSPs are not changed.

This transparent schema is deliberately **not accepted** by the opaque v1 texture
packer/runtime. It avoids an implicit alpha-blending contract change. Transparent
texture transport, premultiplication during filtering, isolated mip chains, KTX2,
Unity and fractional-alpha cross-browser GPU rounding remain subsequent gates.

## Bounds and failure behaviour

Export and qualification require explicit public confirmation. Strict suite and
manifest field validation rejects wrong profile, secret-labelled plans, repeated
identities/sizes/files, inconsistent alpha statistics, changed source hashes,
extra native layer fields, missing image entries and relative path escapes.
Symlink/reparse-point paths are rejected. Outputs cannot overwrite or nest inside
input evidence. At most 1,024 identity/style groups and 33,554,432 source pixels
are permitted, on top of existing benchmark/file/chunk/byte limits. Allocation is
bounded by the supplied native sizes and total source-pixel count.

`manifest.json` or `qualification.json` is written only after its gate succeeds.
Failures in an already-created output directory preserve `failure.json` and
partial files for diagnostics, without a success marker. Verification refuses
failed bundles. Neither a self-consistent manifest nor CRC/SHA-256 proves authorship.

## Test gates

`test_artwork_transparent_bundle.py` checks all nine families, three palettes and
four sizes; exact alpha-aware file-codec roundtrips; fractional alpha, invisible
RGB and foreground matching the old matte; provenance, altered native/file pixels,
missing/duplicate inventory, path restrictions, output reuse, workload limits,
CLI failures, qualification coverage and failure diagnostics. Unit fixture receipts
are marked test-only in their environment; they are not native-run evidence.

The new native test uses a real generated suite and actual compositor when the
host exists. `BYTEFABLES_REQUIRE_NATIVE=1` makes unavailable/broken native support a
failure in CI. No test double is used to satisfy that gate. Tests of failure paths
may use explicitly labelled mocks and never publish their output as evidence.

`tests/browser/artwork-transparent-smoke.py` checks the static HTTP preview and
real Chromium Canvas compositing of PNG/WebP samples on black/white. It tests one
identity per available family/palette/size/codec, not every identity. Saved native
source fixtures currently have binary alpha, so exact browser comparisons are
not a qualification of arbitrary partial-alpha rounding. `--offline-contract`
explicitly tests only saved image compositing in a blank page, not HTTP/UI/CSP.

## References

- W3C PNG specification, alpha representation:
  https://www.w3.org/TR/png/#6AlphaRepresentation -- straight/unassociated samples.
- Pillow image API: https://pillow.readthedocs.io/en/stable/reference/Image.html --
  RGBA alpha-composite reference used in transport QA.
- Pillow WebP options:
  https://pillow.readthedocs.io/en/stable/handbook/image-file-formats.html#webp --
  lossless and exact invisible-RGB preservation.

The reference composites deliberately match the current host's stored-sample
Pillow convention. This is **not** a claim of linear-light or ICC-managed blending.
