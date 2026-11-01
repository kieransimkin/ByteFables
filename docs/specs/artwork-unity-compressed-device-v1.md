# Unity compressed-texture real-device qualification v1

Status: experimental device evidence. This BF-W9 gate measures direct BC7,
ASTC 4x4 and ETC2 RGBA8 `Texture2DArray` uploads on an actual Unity graphics
backend. It does not change the compressed block bundle, artwork, identity keys,
or the lossless RGBA reference.

## Desktop execution profiles

The automated build-and-run harness defines four native-host profiles:

- `windows-d3d11-bc7`
- `windows-d3d12-bc7`
- `linux-vulkan-bc7`
- `macos-metal-astc4x4`

Every build is non-development, IL2CPP, Linear colour and Built-in rendering. The
requested graphics API and compressed format are fixed explicitly; missing format
support, array textures, GPU readback, graphics device or build module is a hard
failure. No RGBA fallback is silently enabled.

Unity documents `SystemInfo.SupportsTextureFormat` as the runtime support query
for script-created texture formats. `AsyncGPUReadback.Request` can request a
different destination texture format, so the qualifier asks the GPU for RGBA32
readback from the compressed array and compares that output with the verified
lossless ByteFables reference.

## Orientation and quality evidence

KTX source images are top-left. ByteFables' qualified RGBA Unity path explicitly
reverses rows before upload, but v1 GPU block payloads are currently uploaded
without format-specific BC7/ASTC/ETC2 flipping.

For every identity and every mip the player records RGBA32 GPU-readback error
against both top-left and established Unity bottom-up references. Strongly
asymmetric mip-0 identities vote on orientation. The result is one of
`bottom-up`, `top-left`, `mixed` or `ambiguous`.

`productionQualified` is true only when every asymmetric vote resolves to the
established `bottom-up` convention. A completed run may therefore be useful
measurement evidence while still reporting `productionQualified: false`.

The player also renders up to 16 evenly distributed identities at every mip on
transparent, black and white backgrounds through the normal premultiplied-array
shader. It records mean/maximum channel error and PSNR. v1 deliberately records
quality without inventing a universal perceptual pass threshold.

## Mobile profiles

The same request format defines preparation-only capability contracts for:

- `android-vulkan-astc4x4`
- `android-gles3-etc2rgba8`
- `ios-metal-astc4x4`

`--prepare-only` can generate their isolated projects and pinned requests, but v1
does not claim Android/iOS deployment or execution. ADB/device-farm and signed
Xcode deployment are separate future gates. This prevents a desktop build or an
Editor capability query from being misrepresented as mobile-device evidence.

## Manual GPU workflow

`Artwork Unity compressed real-device qualification` accepts the run ID of a
successful main-branch real GPU-block packaging workflow. A hosted prerequisite
locates the matching successful native benchmark for the same commit. The GPU
artifact provides raw compressed blocks; the native artifact provides the
independently verified lossless KTX2 reference. Only then can the selected
self-hosted `unity-gpu` workstation build and execute the player.

The final receipt is bound to the exact Unity version, platform, graphics API,
format, GPU/device strings, player inventory, build report and player report.
Checksums establish consistency, not authenticity or universal compatibility.
