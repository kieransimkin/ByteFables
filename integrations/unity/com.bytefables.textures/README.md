# ByteFables verified Unity texture arrays

Optional Unity 6 package for the **existing, public-only ByteFables KTX2 v1
profile**. It imports image bytes; it does not generate artwork, recover secret
material, or authenticate identities. General-purpose KTX2, Basis/ASTC/BCn,
cubemaps, sRGB conversion and automatic mip generation are intentionally absent.

## Install and import

In Unity's Package Manager, select **Add package from disk** and choose this
folder's `package.json`. The package targets Unity 6000.0 APIs. The qualification
runner defaults to the explicitly identified 6000.0.62f1 baseline, not a claim
that this is the latest editor or that other versions have been tested.

From the ByteFables checkout, stage a completed KTX2 bundle into a **new** folder
under your Unity project's Assets directory:

```powershell
python scripts/stage-artwork-unity.py --confirm-public stage --bundle _work/artwork-ktx2 --output "C:/Projects/MyUnityProject/Assets/ByteFablesIds"
```

The Python tooling requires Pillow, as do the preceding image milestones.
The staging command verifies the complete input bundle and copies only
`transport.json`, `source-manifest.json`, the KTX2 banks and the last-written
`artwork.bftextures` descriptor. No HTML, JavaScript or web-viewer files are
copied or executed. Existing output directories are never overwritten.

Unity imports `artwork.bftextures` as a `TextureBundleAsset` with named
`Texture2DArray` subassets. It registers the original transport, source manifest
and bank files as dependencies. It does **not** claim the `.ktx2` extension or
interfere with another KTX importer. Leave the bank files beside the descriptor.
The importer defaults to dropping its CPU-readable texture copies after upload.

The Inspector shows the full digest, style, bank and layer for each entry. Use a
**full sprite key**, not a shortened digest or a transient layer number, to select
an identity/style. Stable keys and original identity digests are preserved.

```csharp
using ByteFables.Textures;
using UnityEngine;

// Keep these references on your component or a saved material so the shader
// and imported subassets are included in your build.
public sealed class PublicIdentityView : MonoBehaviour
{
    public TextureBundleAsset bundle;
    public Renderer target;
    public Shader arrayShader; // Assign Shaders/PremultipliedArray.shader.
    public string fullSpriteKey;
    private Material created, previous;
    void Start()
    {
        var sprite = bundle.Find(fullSpriteKey);
        created = new Material(arrayShader);
        created.SetTexture("_Array", bundle.GetBank(sprite.BankIndex));
        created.SetFloat("_Layer", sprite.LayerIndex);
        created.SetFloat("_Mip", -1); // Automatic; an integer selects one exact mip.
        previous = target.sharedMaterial;
        target.sharedMaterial = created;
    }
    void OnDestroy()
    {
        if (target != null && target.sharedMaterial == created)
            target.sharedMaterial = previous;
        if (created != null) Destroy(created);
    }
}
```

The shader is an unlit, always-on-top preview shader, not a general lit material,
SpriteRenderer adapter, URP/HDRP integration, or graph batching solution.

## Runtime loading and ownership

`TextureBundleData.Load(manifestBytes, boundedFileReader, expectedManifestSha256)`
validates immutable snapshots of the metadata and banks. The reader callback
receives only fixed relative paths and an exact maximum byte count. It is a
trusted I/O boundary: implement bounded reads rather than fetching arbitrary
URLs or allocating unknown response sizes. No network transport is supplied.

`TextureBundleDirectory.LoadDescriptor(path)` is the local-file adapter. It
rejects symlinks/reparse points and changed/truncated files; it is not a sandbox
against hostile concurrent filesystem rewrites. Keep export/import directories
under the application's control.

Construct `UploadedTextureBundle` on Unity's main thread to upload runtime-owned
arrays. Dispose it on the main thread when no longer used. Do not dispose the
subassets of an imported `TextureBundleAsset`; Unity owns those. Each parser
bank owns its byte snapshot and returns copies, never an editable view of accepted
bytes. Array payloads default to 64 MiB, with an explicit maximum of 128 MiB.
JSON is capped at 8 MiB and a bank at 32 MiB. These are input/payload limits,
**not total RAM or VRAM limits**: parser snapshots, upload buffers, driver copies
and temporary qualification targets require additional memory.

## Pixel convention

Source banks are top-left, premultiplied RGBA8 with isolated existing mips. The
uploader reverses rows exactly once into Unity's bottom-left CPU convention,
uses `TextureFormat.RGBA32` with `linear: true` (no sRGB decode), and calls
`Apply(updateMipmaps: false, ...)`. It never lets Unity rebuild the mip chain.
Normal Unity UVs therefore need no additional vertical flip.

Blend state is `One, OneMinusSrcAlpha`. A straight-alpha material would multiply
alpha again and darken edges. Stored sample values are preserved: this does not
make the source artwork or its filtering physically linear-light. Shader
qualification uses an explicit linear RGBA8 render target with sRGB writes
disabled. Ordinary scene post-processing and linear/sRGB output transforms can
change displayed values; qualify your real rendering pipeline separately.

## Qualification (not an automatic green check)

Run on a machine with an installed, activated editor and a working graphics
backend. The runner creates a fresh isolated project and embeds this package.
It does not install Unity, activate licenses, or use `-nographics`.

```powershell
python scripts/qualify-artwork-unity.py --confirm-public --unity "C:/Program Files/Unity/Hub/Editor/6000.0.62f1/Editor/Unity.exe" --editor-version 6000.0.62f1 --bundle _work/artwork-ktx2 --output _work/unity-qualification
```

`--editor-version` must match the actual editor; the report records its version,
graphics API and device. A different installed Unity 6 version can be selected
explicitly, but acceptance applies only to the recorded environment.

The synchronous editor qualification tests the actual ScriptedImporter and
serialized identity bindings, readable CPU upload and GPU readback of **every
mip and layer**, shader orientation on transparent/black/white targets, and
ordered overlapping sprites, including a cross-bank overlap. A separate
synthetic corpus contains asymmetric rows and partial alpha; it is explicitly
not native-render evidence. Raw mip, CPU and single-sprite matte comparisons
are exact. Normalized overlapping blend output permits at most one byte of
rounding difference per component. Fractional/trilinear image-quality studies
and broad device/pipeline coverage remain open.

A missing shader/device/readback capability, editor error, timeout, wrong
coverage count or absent report fails. `report.json` is written by the Python
wrapper only after validating the actual editor's report. CPU-only staging,
.NET parser tests, and a zero process exit by themselves cannot produce a pass.
The GPU check is an `-executeMethod` test with its own assertions; it does not
depend on a particular NUnit/Test Framework package version.

On GitHub, `Artwork Unity CSharp contracts` runs the actual managed parser on
hosted Windows/Linux runners. The native image-output workflow also compiles
that parser and feeds it real generated KTX2 assets. Neither job runs Unity.
`Artwork Unity real GPU qualification` is **manual-only** on a configured
`unity-gpu` self-hosted runner. Set repository variable `UNITY_EDITOR` to its
executable path, and select a successful main-branch native benchmark run ID.
A hosted prerequisite rejects PR/fork/failed artifacts before the workstation
job is eligible. No self-hosted job is triggered automatically by a PR.

See the repository's `docs/specs/artwork-unity-textures-v1.md` and the accompanying
validation report for the distinction between tests run here and pending C#/GPU
gates. Checksums prove consistency with the chosen manifest, not its authenticity.
