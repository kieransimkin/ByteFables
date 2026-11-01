# Image output milestone ledger

This ledger tracks the image-focused implementation of the original
[implementation plan](IMPLEMENTATION_PLAN.md), chiefly BF-W6, BF-W7 and BF-W9.
It does not reopen word-based output work or mark an entire programme wave done.

## Baseline checked: ac677f7701b23e3b604cfb8a1f7e69a3fa9c09e1

GitHub run 41277844420 on 2026-11-01 completed native source comparisons,
36 render cases, PNG/WebP/ICO export and independent saved-file validation.
The run exported 144 identity/style groups and verified 1,296 image files.
Its browser step failed because a Playwright string predicate invoked eval
under the gallery's strict CSP. The general Tests workflow 41277844421 passed.
These are observed results for that baseline, not a claim that the next patch's
workflow has run.

- Gallery and atlas plans: implemented.
- PNG CRC and pixel readback: implemented.
- Native compositor benchmark: executed successfully at the baseline in CI.
- PNG/WebP/ICO asset bundle export: executed successfully at the baseline in CI.
- Browser gallery: implemented; baseline smoke-test CSP failure addressed here.
- **Runtime texture atlases v1 (this patch):** deterministic lossless packing,
  gutters, top/bottom-origin UVs, page and source verification, Canvas/WebGL2
  consumers and a bounded 1,000-instance display/readback test. See the
  [runtime contract](specs/artwork-runtime-textures-v1.md).

## Next acceptance work

First confirm the updated HTTP gallery and WebGL readback steps pass on GitHub.
Then add independently qualified transparent native-source exports and isolated
mip levels/KTX2 (not page-wide mipmaps), followed by Unity consumption tests.
Larger unique-identity and accessibility studies remain separate from repeated
sprite display throughput. Existing formats and hashes are not silently changed.

## Transparent source-sprite milestone -- based on 1d5497b

Observed baseline: native image-output run **41279164273** completed successfully
on 2026-11-01, including HTTP gallery, PNG/WebP readback and the 1,000-instance
Canvas/WebGL texture check. This closes the preceding runtime/browser acceptance
check for that committed baseline; it does not claim a run of this new patch.

This increment adds the separate `bytefables.transparent-artwork-bundle.v1`:
source RGBA PNG/WebP/native ICO, exact original native-matte comparison,
post-save file/alpha verification, a static multi-background preview, and a
separate real-native black/white qualification command. See
[transparent source contract](specs/artwork-transparent-sprites-v1.md).
The old opaque exports, runtime manifest and generator versions are unchanged.

New local execution and remote acceptance results belong in the accompanying
validation report; new native two-matte and HTTP browser gates must pass in CI.
The next image work is isolated alpha-aware mip levels / versioned transparent
texture consumption, then KTX2 and Unity qualification. No page-wide mipmap
claim, speech/word work, identity authenticity or entire-wave completion is added.
