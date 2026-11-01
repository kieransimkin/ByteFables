# Lazy runtime resolution and Unity CPU/GPU residency v1

Status: experimental, PUBLIC, presentation-only. This milestone connects the
existing lossless/UASTC transports to a metadata-first Unity runtime. It does not
change artwork generation, public sprite keys, original source mips, or the
qualified lossless KTX2 transport.

## Resolved runtime cache

Schema: `bytefables.runtime-resolved-bundle.v1`
Profile: `bytefables.runtime-rgba8-resolved.v1`
Unity descriptor: `bytefables.unity-lazy-runtime.v1` (`runtime.bfresolved`).

The cache can be produced from either:

- a verified lossless `bytefables.ktx2-alpha-bundle.v1`; or
- a verified `bytefables.ktx2-uastc-bundle.v1`, transcoded by the exact pinned
  Khronos KTX 4.4.2 tool.

UASTC resolution uses the qualified UASTC decoded mip bytes. Those bytes are then
wrapped in the existing canonical uncompressed RGBA8 KTX2 bank profile. This is
**not lossless relative to the original alpha mip bytes**: the manifest records
`sourceArtifact.kind = uastc-zstd` and records separate resolved level/layer
hashes. The original full sprite key and `sourceRGBAsha256` remain unchanged.
No derived pixels are falsely published under the original alpha-bundle schema.

Lossless resolution is a metadata/repackaging step and should reproduce the same
bank pixel bytes. Both source modes produce the same runtime schema, allowing the
Unity lazy loader to consume one strict format.

Commands:

```sh
python scripts/resolve-artwork-runtime.py --confirm-public lossless \
  --bundle _work/artwork-ktx2 --output _work/runtime-lossless

python scripts/resolve-artwork-runtime.py --confirm-public uastc \
  --bundle _work/artwork-uastc --output _work/runtime-uastc \
  --ktx /absolute/path/to/ktx

python scripts/resolve-artwork-runtime.py verify --bundle _work/runtime-uastc
```

Outputs are create-only. Bank and descriptor checksums, complete mip hashes and
per-sprite resolved mip hashes are re-read after writing. Checksums establish
consistency, not identity authenticity.

## Metadata-first Unity open

`LazyTextureBundleDirectory.LoadDescriptor()` reads only:

1. `runtime.bfresolved`;
2. `manifest.json`.

It does **not** read a KTX2 bank during open or full-key identity lookup. The
manifest is strictly validated before any bank path is accepted. Bank paths are
canonical fixed `banks/bank-NNN.ktx2` names.

`LazyTextureBundleData.LoadBank(index)` then reads exactly the requested bank,
parses it through the existing strict `Ktx2ArrayData` parser, verifies full-level
hashes, and verifies every sprite layer/mip hash before returning the bank.

This separates metadata memory from decoded/parsed bank residency. The old
`TextureBundleData` eager loader remains unchanged for code that wants the full
bundle resident.

## CPU residency

`TextureCpuResidency` is an independent lease-pinned LRU over parsed banks.

- Budget range: 1 byte through 128 MiB.
- The unit of residency is one complete KTX2 bank.
- Concurrent requests for the same missing bank share one load task.
- Cancellation cancels that waiter, not another caller's shared bank read.
- A lease pins its bank; a pinned bank is never evicted.
- Budget shrink below pinned bytes fails before the budget is changed.
- Hits, loads, evictions, resident/peak bytes and in-flight loads are observable.
- `PrefetchAsync` performs CPU/disk work without creating Unity GPU objects.
- Disposal is idempotent; pinned banks remain valid until their final lease is
  released, while new acquisitions fail.

Disk I/O uses the existing bounded, reparse-point-rejecting local directory
adapter. `Task.Run` moves synchronous local bank parsing off the caller thread;
this is not a claim of OS-native async file cancellation once a read has begun.
The data is PUBLIC artwork, and GC-retired parser buffers are not treated as
secret-memory erasure.

## GPU residency

`LazyTextureArrayResidency` layers a separate main-thread GPU LRU on top of the
CPU cache.

- CPU and GPU budgets are independent. GPU accounting uses decoded RGBA payload bytes; driver allocation/alignment can consume more physical VRAM.
- A GPU miss obtains/validates a CPU bank first, then uploads it through the
  existing `TextureArrayUpload.Create` implementation.
- GPU work is restricted to the thread that constructed the residency manager.
- Full sprite keys resolve to a bank lease without changing bank/layer mapping.
- `PrefetchCpuAsync` can warm storage/CPU state in advance; `PrefetchGpu` uploads
  at most one requested bank per yielded frame.
- GPU leases pin arrays, and pinned VRAM cannot be evicted to satisfy another
  request.
- Filter mode is fixed at cache construction, preventing leases from silently
  fighting over one resident array's sampling state.

This is actual lazy CPU/disk and bounded GPU residency for the resolved RGBA8
runtime profile. It is not yet direct GPU block-compressed residency.

## Why resolved RGBA8 first

Khronos KTX can transcode UASTC to BC7, ETC2 and ASTC, but raw block-compressed
upload has additional platform/orientation rules. ByteFables' source convention
is top-left while Unity's CPU texture convention used by the qualified RGBA8 path
is bottom-left; flipping compressed blocks correctly is format-specific. V1
therefore resolves to the already-qualified RGBA8 KTX2 representation rather
than silently introducing a possibly inverted block-compressed path.

Direct BC7/ETC2/ASTC runtime selection is the next versioned gate and must include
orientation, alpha, mip and device readback qualification for each target.

## Acceptance

`Artwork lazy runtime resolution contracts`:

- runs Python resolver/failure tests;
- builds the explicit lossless synthetic KTX2 fixture;
- installs checksum-pinned Khronos KTX 4.4.2;
- resolves both lossless and real UASTC sources;
- compiles all `Runtime/Core/*.cs` with C# 7.3/.NET 8;
- runs a C# contract executable proving metadata open causes zero bank reads,
  full-key lookup causes zero reads, explicit bank loading is checked, concurrent
  requests coalesce, one-bank budgets evict LRU banks and pinned banks fail
  closed.

The existing Unity GPU workflows remain separate engine/device acceptance. A
hosted C# pass does not claim a Unity GPU pass.
