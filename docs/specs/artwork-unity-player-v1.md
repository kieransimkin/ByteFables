# Standalone Unity player qualification v1

Image workstream BF-W9. This extends the Unity importer with **built-player**
acceptance; it does not change the frozen KTX2, alpha-array, image or identity
formats. It is not a new renderer, generator or performance/recognisability study.

## Why a player is a separate gate

The hosted managed-reader tests compile only Unity-independent C#. An editor GPU
run does not prove that texture subassets, shader dependencies and serialized
identity bindings survive a player build. This gate creates a fresh project,
imports pinned artwork through the real importer, saves references in a scene,
builds a non-development player, and tests those built assets in another process.
The existing editor qualifier is unchanged and remains a separate requirement.

## Profiles and prerequisites

- `windows-d3d11`: native Windows x64 build/run, Direct3D11.
- `linux-vulkan`: native Linux x64 build/run, Vulkan; requires a working graphics
  session/driver as well as Unity desktop build support.

Both use an exact installed Unity 6 version (default `6000.0.62f1`, inherited from
previous qualification), Built-in rendering, Gamma colour space and Mono. The
package is not declared qualified until an actual engine run passes. No automatic
editor/license installation, license transfer, graphics fallback or download of
executables occurs. Configure the local Unity installation separately. A software
Vulkan implementation can satisfy readback; reported device strings distinguish
it. Passing is not evidence of physical-GPU performance.

The runner is native-host-only: Windows cannot qualify a Linux executable by
merely building it, nor vice versa. IL2CPP, URP/HDRP, Linear colour space, Metal,
D3D12, WebGL players and mobile remain outside this profile.

## Commands

From the repository root, using the existing Python/Pillow integration environment:

```powershell
python scripts/qualify-artwork-unity-player.py --confirm-public `
  --bundle _work/artwork-ktx2 --output _work/unity-player-new `
  --target windows-d3d11 --unity 'C:\Program Files\Unity\Hub\Editor\6000.0.62f1\Editor\Unity.exe' `
  --editor-version 6000.0.62f1
```

```sh
python scripts/qualify-artwork-unity-player.py --confirm-public \
  --bundle _work/artwork-ktx2 --output _work/unity-player-linux-new \
  --target linux-vulkan --unity /absolute/path/to/Unity --editor-version 6000.0.62f1
```

`UNITY_EDITOR` and `BYTEFABLES_UNITY_EDITOR_VERSION` provide optional defaults.
Use the exact version actually installed, not `latest`. Defaults allow 1,800
seconds for a build and 600 seconds for player execution. `--build-timeout` and
`--player-timeout` allow bounded overrides; a timeout fails and terminates the
owned process tree. On Windows tree termination uses `taskkill /T /F`, with a
launcher kill fallback. On POSIX it kills the newly created process group.

Preparation is independently useful and does not need Unity:

```sh
python scripts/qualify-artwork-unity-player.py --confirm-public --prepare-only \
  --bundle _work/artwork-ktx2 --output _work/unity-player-prepared \
  --target windows-d3d11 --editor-version 6000.0.62f1
```

This writes `plan.json` with `status: prepared`, `playerExecuted: false` and
`gpuExecuted: false`. It does not publish `report.json`. A later full run uses a
**new output directory**; prepared or failed outputs are never silently resumed.

## Data and execution path

The verified source KTX2 bundle and a separate four-sprite synthetic orientation/
alpha fixture are staged under `Assets`. The project embeds the local Unity
package and has no additional package dependencies. The same pinned descriptors
and KTX2 bytes are also copied into `StreamingAssets` as the player's reference
pixels. The fixture is explicitly synthetic, not an additional real-identity
sample or a discrimination study.

`TexturePlayerBuild` is an editor-only executeMethod. It checks the native host,
exact version, installed build module, fresh output paths and active target. The
runner supplies Unity's `win64`/`linux64` command-line target names and explicitly
chooses the Player subtarget, not a dedicated server. It disables automatic
API choice and fixes the backend. The saved scene references both imported
`TextureBundleAsset` objects and the actual shader asset, making shader stripping
and lost serialized references testable instead of relying only on `Shader.Find`.

The player independently requires `Application.isEditor == false`, matching
platform/version/backend, Built-in/Gamma/Mono, texture arrays and GPU readback.
It loads and validates the bundled reference KTX2s, checks both manifest pins,
then compares built texture subassets with them. It does not substitute newly
uploaded runtime arrays for the built arrays being tested. A separate runtime
upload is used for the CPU contract and overlap/disposal checks.

For every original and synthetic layer and mip:

1. Exact CPU upload readback of the supplied bytes, with explicit bottom-up rows.
2. Exact GPU readback of the **built imported** array subasset.
3. Exact shader output on transparent, opaque black and opaque white backgrounds.

All full sprite keys and identity/style/bank/layer bindings are checked. Three
ordered overlaps cover forward/reversed order and crossing banks. Only these
normalised framebuffer blend checks use the pre-existing one-byte rounding
allowance; raw mip and matte checks are not weakened. The probe yields one frame
per layer so deferred Unity destruction can release temporary readback surfaces.
The runtime owner is disposed twice and must reject subsequent access.

Let `N` be the source sprite count and `L` its levels per sprite. The synthetic
fixture is four sprites at five levels. Required CPU and GPU comparison counts
are each `N*L + 20`; shader comparisons are three times this; binding comparisons
are `N + 4`. Missing, floating-point, boolean or wrong counts fail validation.
Timing describes the qualification workload including readback and frame yields,
not throughput, FPS or a device benchmark.

## Evidence and limits

Every project gets a fresh run identifier embedded in its built scene. The player
must also receive that identifier from the launcher environment. Reusing a prior
executable/report cannot satisfy a new request. Exact manifest pins, Unity version,
target, backend, pipeline and colour space are checked in separate build and
player reports. A zero exit code, missing report, nonzero exit despite a successful
report, editor-only report, Null device or skipped check cannot pass.

A successful directory contains:

- `plan.json`, build/player raw JSON, build/player logs and launcher transcripts.
- `player-inventory.json`: SHA-256 and size of every built file, bounded to 20,000
  files and 2 GiB, checked both before and after execution.
- `report.json`: final receipt binding the two raw reports and whole-player
  inventory. This file is written only after all gates pass.

Failure retains diagnostics plus `failure.json`, never a final success receipt.
Reports use create-new writes; inputs, existing outputs, linked/reparse paths and
output/source nesting are rejected. Stage bytes are reverified after copying.
The supplied local package and Unity installation are trusted executables, not a
sandbox for arbitrary code. Checksums and run IDs are consistency/provenance
checks, not signatures or proof against a malicious host that forges all evidence.

## CI and local tests

The existing hosted Windows/Linux contracts workflow additionally runs the new
Python staging/receipt/process tests. Those tests include **mock** build/player
reports and real short subprocess timeout/error checks; they never represent
Unity execution. Source-invariant tests inspect packaging, not compilation.

`artwork-unity-player.yml` is manual-only on main. Its hosted gate permits artifacts
only from successful same-repository, push-to-main native benchmark runs. It then
uses a labelled `unity-gpu` Windows/Linux runner and the
`unity-player-qualification` environment (configure approval protection). Set
`UNITY_EDITOR` as an environment/repository variable and install the requested
Unity version and build module. No PR code is run on the workstation. Reports and
logs are uploaded; player binaries and license files are not uploaded.

```sh
python -m unittest discover -s tests/python -p test_artwork_unity_player.py -v
```

A manual job is not a successful acceptance test until it actually executes. A
single passed profile qualifies only that build/device/API, not all Unity targets.

## Primary API references

- Unity 6 editor CLI, including build target names and Player subtarget:
  https://docs.unity3d.com/6000.0/Documentation/Manual/EditorCommandLineArguments.html
- BuildPlayer/BuildPlayerOptions:
  https://docs.unity3d.com/6000.0/Documentation/ScriptReference/BuildPipeline.BuildPlayer.html
- Desktop build modules:
  https://docs.unity3d.com/6000.0/Documentation/ScriptReference/BuildPipeline.IsBuildTargetSupported.html
- Explicit scripting backend:
  https://docs.unity3d.com/6000.0/Documentation/ScriptReference/PlayerSettings.SetScriptingBackend.html
- Explicit graphics API:
  https://docs.unity3d.com/6000.0/Documentation/ScriptReference/PlayerSettings.SetGraphicsAPIs.html

The frozen transport's primaries/filtering/alpha semantics remain unchanged. This
milestone neither regenerates mips nor claims a colour-managed rendering pipeline.
