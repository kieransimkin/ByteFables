# Android direct compressed-texture qualification v1

Status: real-device BF-W9 acceptance harness. This extends the desktop direct
block measurement to a **physical Android device** without changing artwork,
source mips, UASTC encoding or GPU-block manifests.

Profiles:

- `android-vulkan-astc4x4`: ARM64, IL2CPP, Linear, Built-in, Vulkan, ASTC 4x4.
- `android-gles3-etc2rgba8`: ARM64, IL2CPP, Linear, Built-in, OpenGLES3,
  ETC2 RGBA8.

No RGBA fallback is allowed. Unsupported format/API/array/readback capability is a
failed qualification, not a skip.

## Build and embedded evidence

Unity Android `StreamingAssets` may live inside the APK rather than as normal
filesystem files. The build entry point therefore copies the pinned GPU manifest,
**only the selected compressed representation**, the lossless reference transport,
source manifest and reference KTX2 banks into imported `.bytes` `TextAsset`s and
serializes those assets into the isolated qualification scene. Runtime callbacks
still use the same strict Core parsers and SHA-256 checks.

The build explicitly selects `NamedBuildTarget.Android`, IL2CPP, ARM64 and one
graphics API. The package ID is fixed to
`com.bytefables.compressedqualification`; the build is a non-development APK.

## Physical ADB execution

The host runner requires exactly one attached ADB device unless an explicit serial
is supplied. `ro.kernel.qemu`/`ro.boot.qemu` values identifying an emulator are
rejected. The serial is used only to address ADB commands and is deliberately not
written into the receipt.

The runner uninstalls any stale package, installs the fresh APK, clears logcat,
launches the package with Android's launcher intent, and waits for the player to
write `bytefables-compressed-android-result.json` under its persistent external
files directory. The result is pulled through ADB, checked against the serialized
run ID and source hashes, and the local APK hash is checked again after execution.
The package is removed afterward unless `--keep-installed` is explicitly used.

## Measurements

Every compressed sprite/mip is read back as RGBA32 and compared with both
possible source orientations. Up to 16 evenly distributed identities are also
rendered across every mip over transparent, black and white backgrounds through
the premultiplied array shader. The report records device model, Android/driver,
graphics API, format support, error metrics and orientation.

`productionQualified` is true only when the real device consistently resolves to
the already-qualified Unity bottom-up convention. Quality numbers are measurement
evidence, not universal perceptual thresholds.

The iOS Metal/ASTC profile remains preparation-only in this version because a
signed Xcode deployment/provisioning bridge is account/device specific and must
not be faked by Editor capability checks.
