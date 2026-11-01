# GPU-native block texture bundle v1

Status: experimental, PUBLIC, presentation-only. This BF-W9 increment derives
platform-native block payloads from the already-qualified UASTC transport. It
never changes artwork, sprite keys, source mip construction or the lossless RGBA8
reference.

## Formats

Schema: `bytefables.gpu-block-texture-bundle.v1`
Profile: `bytefables.gpu-blocks-4x4.v1`

The bundle contains three independently transcoded targets, all produced by the
pinned Khronos KTX 4.4.2 tool:

| id | Khronos target | Unity format | block |
|---|---|---|---|
| `bc7` | `bc7` | `TextureFormat.BC7` | 4x4 / 16 bytes |
| `astc4x4` | `astc` | `TextureFormat.ASTC_4x4` | 4x4 / 16 bytes |
| `etc2rgba8` | `etc-rgba` | `TextureFormat.ETC2_RGBA8` | 4x4 / 16 bytes |

Each file is one complete mip of one array bank, concatenated layer-major. Small
mips still occupy one complete 4x4 compression block per layer. All file lengths,
paths and SHA-256 values are deterministic and bounded. A `.bfgpu` descriptor pins
the manifest.

This format deliberately stores no implicit fallback. The RGBA8 resolved runtime
bundle remains the explicit fallback/reference surface.

## Runtime selection

`CompressedTextureFormatSelector` asks the actual Unity device whether each
`TextureFormat` is supported. Desktop-class players prefer BC7 then ASTC then
ETC2; mobile players prefer ASTC then ETC2 then BC7. Selection is still gated by
`SystemInfo.SupportsTextureFormat`, texture-array support and a non-null graphics
device. If no compressed format is available, `Select` throws unless the caller
explicitly requests a null result and then chooses the separate RGBA8 runtime.

Unity documents BC7 as a high-quality format for DX11-class hardware and notes
that unsupported BC7 assets may otherwise be decompressed at load time. The
ByteFables path therefore refuses unsupported formats before construction rather
than depending on that implicit conversion. Unity's raw `SetPixelData` API is
used because it is explicitly intended for compressed/preformatted data.

## Orientation boundary

KTX source images use top-left (`rd`) orientation. Raw block payloads are written
exactly as returned by the Khronos transcoder and are **not** manipulated by
ByteFables. Unlike RGBA8 rows, vertically flipping BC7/ASTC/ETC2 requires
format-specific manipulation inside blocks as well as block-row ordering.

Therefore direct block upload is not called production-qualified merely because
`Texture2DArray.SetPixelData` succeeds. A real-device qualification must render
asymmetric sentinel images through the selected graphics API and prove the
orientation/output against the resolved RGBA8 reference. No automatic flip or
silent RGBA fallback is performed.

## Residency

`CompressedTextureArrayResidency` is a lease-pinned LRU over one explicitly
selected block format. Its budget counts the exact compressed block bytes in the
bundle, not driver allocation overhead. Active leases cannot be evicted. Budget
shrink fails before violating pinned residency. The manager does not mix texture
formats inside one cache.

## Acceptance split

Hosted tests prove manifest/inventory bounds, deterministic Khronos extraction,
selector rules and source invariants. Real Unity GPU orientation/quality remains
a manual hardware gate. Quality of the underlying UASTC source is owned by the
real-artwork UASTC workflow; this bundle adds another block-compression stage, so
final framebuffer error must be measured on the target device rather than inferred
from UASTC's RGBA8 quality metrics.
