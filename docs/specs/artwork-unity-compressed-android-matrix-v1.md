# Unity Android compressed same-device matrix v1

Status: real-device qualification orchestration. This extends the existing
single-profile Android compressed-texture runner; it does not alter texture
formats, shaders or qualification arithmetic.

Schema: `bytefables.unity-compressed-android-matrix.v1`.

## Profiles and order

One physical ADB device is selected once. The matrix then executes, in order:

1. `android-vulkan-astc4x4`;
2. `android-gles3-etc2rgba8`.

Each profile retains its own independent IL2CPP/ARM64/Linear APK build, install,
GPU readback, shader/matte checks, orientation classification and receipt. The
existing single-profile runner remains the authority for those checks.

The selected ADB serial is passed between sub-runs only in process memory and is
**never written into the matrix report or artifacts**. The combined report checks
that successful sub-runs describe the same device model, OS and graphics device.
Those public device-class fields are evidence, not a unique-device identifier.

## Completion versus production qualification

`status: passed` means both profiles executed to complete valid device receipts on
the selected physical device. It does **not** imply that both direct compressed
paths are production-qualified.

`productionQualifiedProfiles` and `allProfilesProductionQualified` are separate.
As with the individual runner, a profile is production-qualified only when the
measured compressed orientation matches the established bottom-up Unity contract.
A completed top-left/mixed/ambiguous measurement remains useful evidence but does
not become a fake production pass.

If one profile fails (unsupported API/format, build failure, missing report, etc.),
the matrix still attempts the second profile. `matrix-result.json` is written with
the partial evidence, then the command fails and `failure.json` is emitted. This
avoids losing a valid second-profile measurement because the first profile failed.

## Workflow provenance

The manual workflow accepts only a successful main-branch real GPU-block packaging
run and finds the matching successful native-reference run for the same commit.
It runs only on a self-hosted `unity-android-device` runner and uploads the whole
matrix directory, including each sub-run's build/player receipts and logs.

This matrix does not qualify iOS, emulators, a device farm, thermal stability or
performance over time. Those are separate future device gates.
