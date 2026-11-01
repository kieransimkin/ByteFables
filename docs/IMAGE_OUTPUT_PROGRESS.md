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

## Transparent GPU arrays and isolated mip levels -- based on 9bc9cb7

Observed baseline: native image-output run **41281039108** completed successfully
on 2026-11-01. All transparent-source export, black/white native qualification,
HTTP preview and previous opaque Canvas/WebGL checks passed. These observations
refer to the merged baseline, not this new patch's workflow.

This increment adds `bytefables.alpha-texture-array-bundle.v1`: explicit
premultiplied RGBA8, independent per-sprite area-filtered levels through 1x1,
raw level readback/source recomputation, and a separately versioned WebGL2
texture-array consumer. Opaque formats and lossless source PNGs are unchanged.
The browser qualification requires complete level readback, painter-order
blending, fractional LOD and synthetic red/blue layer-isolation tests. See
[the mip/array contract](specs/artwork-alpha-textures-v1.md).

Next: qualify this new browser/GPU path in CI and additional real devices, then
KTX2 transport and Unity consumption. Neither KTX2/Basis encoding nor Unity,
linear-light filtering, cutout alpha coverage preservation or an entire BF-W9
wave is claimed complete. Human recognisability/accessibility studies remain
separate from repeated-instance display throughput.

## Lossless KTX2 array transport -- based on 56d6c5c

Observed baseline: native image-output run **41282545299** completed successfully
on 2026-11-01, including the required alpha-array WebGL2 levels, blending and
layer-isolation readback. This closes the prior alpha runtime's CI gate for that
committed baseline; it does not claim acceptance of this increment.

This increment adds `bytefables.ktx2-alpha-bundle.v1`: canonical uncompressed
RGBA8 KTX2 arrays with every original mip byte preserved, strict Python/JavaScript
parsers, source-manifest and layer-hash binding, a transport adapter into the
existing alpha renderer, an independent Khronos validation/raw-extraction gate,
and a real HTTP/WebGL2 readback gate. See
[the KTX2 contract](specs/artwork-ktx2-transport-v1.md).

The raw mip profile, existing image formats, generators and identity keys remain
unchanged. New independent-tool/browser acceptance must be recorded separately
from local unit results. Next is Unity consumption and qualification of this
frozen uncompressed profile. Basis compression, streaming, colour-managed
filtering and the rest of BF-W9 are not marked complete.

## Unity Texture2DArray consumer -- based on 73e82e0

Observed baseline: native image-output run **41297971184** completed successfully
on 2026-11-01, including independent Khronos validation/all-image extraction and
the real KTX2 HTTP/WebGL2 readback. The preceding KTX2 acceptance gate is closed
for that committed baseline, not for any new Unity code.

This increment adds the optional Unity 6 package, strict immutable C# readers,
verified `.bftextures` staging, Texture2DArray upload with explicit row orientation
and preserved mip bytes, serialized identity lookup, premultiplied preview shader,
managed cross-platform conformance tests, and actual Unity importer/GPU acceptance
harness. See [the Unity contract](specs/artwork-unity-textures-v1.md).

Local Python staging and existing artwork regression tests were executed. **C#
compilation and Unity execution were unavailable locally and remain acceptance
gates**. Hosted .NET jobs do not qualify the Unity runtime. The GPU workflow is
manual-only on a configured licensed workstation; it cannot report a skipped
renderer as passed. No generator, public identity key, existing texture format,
word output, compressed transport or entire programme wave is changed/completed.

Next: run and record managed/Unity GPU acceptance, then player-build and render-
pipeline/device qualification before expanding Unity graph batching or compressed
transport. The current pipeline's native/browser evidence is preserved separately.
