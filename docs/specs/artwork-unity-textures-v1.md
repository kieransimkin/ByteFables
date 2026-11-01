# Unity Texture2DArray consumer v1

Image workstreams BF-W7/BF-W9; public and presentation-only. This milestone adds
an optional Unity consumer of the frozen uncompressed KTX2 profile. It does not
change a generator, identity key, mip arithmetic, browser format or word output.
Implementation is separate from qualification: **the supplied C# and Unity GPU
code was not compiled/executed in the authoring environment**. Hosted C# gates
and the explicit licensed Unity/GPU gate must pass before it is called qualified.

## Observed prior baseline

ByteFables `73e82e03ba133faa561a928e8d862921bcf28890`, native workflow run
`41297971184`, finished successfully on 2026-11-01. All KTX2 Khronos
validation/extraction and browser GPU checks passed. Those observed results
apply to the preceding commit, not to this Unity implementation.

## Components

`integrations/unity/com.bytefables.textures` is a local UPM package targeting
Unity 6000.0 APIs. Separate core/runtime/editor assembly definitions keep Unity
references out of the pure C# parser. The package contains:

- Bounded strict JSON and exact-profile KTX2 readers; canonical descriptors and
  full 64-bit offsets, original file/mip/layer hashes, public gates, canonical
  source paths, stable sprite keys, immutable byte snapshots, payload budgets.
- `TextureArrayUpload` and runtime-owned `UploadedTextureBundle` with disposal;
  no implicit regeneration, conversion, straight-alpha multiplication or flip.
- `.bftextures` ScriptedImporter, stable bank subasset IDs, dependency tracking,
  serialized full identity/style bindings, no global `.ktx2` extension takeover.
- Explicit unlit premultiplied-array shader and synchronous editor qualification
  using the actual importer, CPU data, GPU data and rendered matte results.

The exact reader intentionally rejects otherwise-valid KTX2 files outside the
existing ByteFables contract, including different metadata, orientation, colour
transfer, compression, cube faces, mip counts, padding, or physical level order.
The JSON reader rejects duplicates, excessive depth/node/string budgets,
noninteger numbers, invalid UTF-8 and unpaired Unicode surrogates. It accepts the
integer-only texture schemas rather than purporting to implement every JSON use.

The local path adapter rejects links/reparse points in the path. As with the
existing exporters this is not a hostile concurrent-filesystem isolation layer.
The callback API reads only canonical local resource names. Trust an independent
manifest pin for authenticity-sensitive workflows; a user-supplied unsigned
manifest can be replaced together with all its matching images and hashes.

## Staging contract

`python scripts/stage-artwork-unity.py --confirm-public stage --bundle INPUT
--output NEW_DIRECTORY` verifies a complete original KTX2 bundle before copying.
It copies original `manifest.json` byte-for-byte as `transport.json`, the bound
source manifest and each bank. The final file is `artwork.bftextures`:

```json
{
  "schema": "bytefables.unity-texture-import.v1",
  "publicOnly": true,
  "manifestFile": "transport.json",
  "manifestSha256": "<full SHA-256 of the original transport manifest bytes>"
}
```

The placeholder above is explanatory, not a valid digest. Output refuses an
existing directory or a path nested inside the input. The descriptor is written
last, after saved-file checks. Failed copies retain `failure.json` and remove the
descriptor. `verify` checks saved metadata, geometry, mip/layer bytes and exact
inventory, except Unity-generated `.meta` files. It does not run Unity.
The metadata references for the original web viewer are structurally validated
but no viewer files are staged, loaded or executed by Unity.

## Runtime invariants

For each bank and mip, data is copied layer by layer into a full-chain RGBA32
Texture2DArray. Top-origin rows are reversed exactly once. `linear:true` disables
hardware sRGB decoding; `Apply(false, ...)` prevents Unity from substituting
mips. Premultiplied source-over uses `Blend One OneMinusSrcAlpha`; texture wrap is
Clamp and anisotropy zero. Point/Trilinear modes are explicit.

Source sizes 16/32/64/128, 1..256 layers per bank, 1..1024 sprites, 8 MiB JSON,
32 MiB per KTX2 container, default 64 MiB payload and hard 128 MiB payload are
bounded before upload. Budgets exclude duplicate CPU/GPU/staging allocations.
Runtime upload requires an adequate device. Editor import can create serialized
assets in an import worker without claiming GPU execution. CPU readability is
off by default. Imported subassets belong to Unity; runtime-created arrays belong
to the disposable owner. Calls into Unity and disposal occur on the main thread.

The original image convention is stored colour samples, not colour-managed
linear-light filtering. The exact shader test uses a linear render target and
disables sRGB writes. Real scene output transforms, post-processing, render
pipelines, standalone-player shader stripping and material integration require
application-level qualification. Use a serialized shader/material reference in
builds. The supplied shader is an always-on-top preview, not a lit world material.

## Acceptance and evidence

Hosted .NET tests compile the exact pure C# source with language version 7.3,
check the existing Python/JavaScript vector, every layer hash, manifest pinning,
immutability, malformed headers/JSON/paths, bounds, and row conversion. The
Windows/Linux job is independent of Unity and must not be reported as a Unity
engine pass. The native workflow additionally supplies real image-derived KTX2.

`python scripts/qualify-artwork-unity.py` requires an explicit executable or
`UNITY_EDITOR`, an exact Unity 6 editor version and a fresh output directory.
It creates a separate project, embeds the package without a third-party test
framework, stages the supplied bundle and an asymmetric synthetic corpus, then
calls `TextureQualification.RunFromCommandLine` synchronously. No nographics,
mock engine, silent skip, license activation or editor installation is attempted.

For every supplied mip/layer it checks readable CPU upload, GPU raw readback
from the imported nonreadable texture, and shader output on transparent/black/
white targets. Raw and single-sprite comparisons are exact. Three overlapping
sentinel cases (including reversed order and a cross-bank pair) allow at most
one byte per component of normalized-blend rounding difference. The wrapper
checks exact comparison counts, hashes, editor version, device, no skips and
success exit before publishing `report.json`. Missing output, timeout, null
renderer and insufficient GPU capability are failures; diagnostics survive.

The manual GitHub GPU workflow is limited to main and a configured `unity-gpu`
runner. A hosted prerequisite checks that the selected image artifact came from
a successful push to this repository's main native workflow. It never runs PR
code automatically on a licensed workstation. The user must configure the
runner/executable or run the same command locally; no unattended work is claimed.

## Remaining work

Record actual managed compilation and Unity GPU evidence, then qualify player
builds and a broader device/pipeline matrix. Fractional/trilinear appearance,
URP/HDRP integration, Unity graph batching/performance, compressed Basis transport,
streaming/LOD cache policy, accessibility and human recognisability remain open.
This is not a claim that the complete BF-W9 wave is finished.

## Primary API references

- https://docs.unity3d.com/6000.0/Documentation/ScriptReference/Texture2DArray.SetPixelData.html
- https://docs.unity3d.com/6000.0/Documentation/ScriptReference/Texture2DArray.GetPixelData.html
- https://docs.unity3d.com/6000.0/Documentation/ScriptReference/Texture2DArray.SetPixels.html
- https://docs.unity3d.com/6000.0/Documentation/ScriptReference/Rendering.AsyncGPUReadback.Request.html
- https://docs.unity3d.com/6000.0/Documentation/ScriptReference/AssetImporters.AssetImportContext.DependsOnSourceAsset.html
- https://docs.unity3d.com/6000.0/Documentation/Manual/upm-localpath.html
- https://unity.com/releases/editor/whats-new/6000.0.62f1

The complete installation, usage and qualification commands are in the package
README. Detailed local execution scope is recorded in the patch validation report.
