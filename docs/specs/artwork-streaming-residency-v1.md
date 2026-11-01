# Texture streaming and residency v1

Status: experimental, PUBLIC, presentation-only. This milestone introduces
bounded bank residency. It does not regenerate artwork or mips, alter sprite
keys, or make compressed UASTC a mandatory runtime format.

## Unit of residency

Runtime identifier: `bytefables.streaming-residency.v1`.

The cache unit is one complete texture-array bank. All layers and all existing
mips in that bank move together. This preserves the established bank/layer
identity mapping and avoids creating partial texture arrays with ambiguous
indices.

A lease pins a bank. Unpinned banks participate in least-recently-used eviction.
The cache may not evict a pinned bank merely to satisfy a new request; an
otherwise unsatisfiable request fails with an explicit budget error.

## Browser HTTP streaming

`integrations/web/artwork-streaming/runtime.js` consumes the existing lossless
KTX2 transport and the existing strict KTX2 decoder. It does not contain a
procedural renderer, PNG decoder, Basis decoder, or mip generator.

`openKtx2()`:

1. requires a same-origin HTTP(S) directory;
2. reads bounded transport/source manifests and optionally verifies a separately
   supplied transport-manifest SHA-256;
3. fetches KTX2 banks only when first acquired or prefetched;
4. verifies the encoded file checksum before decoding;
5. verifies every decoded full-level and per-sprite mip checksum;
6. stores private byte copies in a bounded residency cache;
7. zeroes those decoded arrays when evicted or disposed.

Concurrent requests for the same nonresident bank share one load. Each caller
receives its own lease. Aborting one waiter does not cancel or corrupt a shared
load for other callers and does not leave the aborted caller pinned.

The default browser budget is the smaller of 16 MiB and the source payload. An
explicit budget may be 1 byte through 128 MiB, although real banks must each fit
entirely. This is a **decoded payload budget**, not total JavaScript/GPU memory.
Fetch buffers, manifests, decoder snapshots, browser internals and GPU uploads
consume additional memory.

## Unity GPU residency

`TextureArrayResidency` operates on an already validated `TextureBundleData`
snapshot. The core parser currently retains the verified KTX2 bank bytes in CPU
memory; this milestone bounds **GPU Texture2DArray residency**, not total CPU
bundle memory and not network traffic.

On Unity's main thread, `AcquireBank` uploads a bank through the existing
`TextureArrayUpload.Create` path, preserving all verified mip levels. Point or
trilinear filtering is selected once when the residency cache is created so two
leases cannot silently fight over one resident texture's filter state. `AcquireSprite`
resolves a full stable sprite key and leases its containing bank. Cooperative
`Prefetch` performs at most one bank acquisition per yielded frame. `SetBudget`
performs immediate LRU eviction when possible. Disposal releases unpinned arrays
immediately and defers a pinned bank until its final lease is released.

No network stack, UASTC decoder, asynchronous Unity worker-thread upload, or
asset-addressing framework is introduced here. Those are separate future gates.

## Cache semantics

- duplicate concurrent browser loads are coalesced;
- LRU order changes on load, hit and lease release;
- pinned entries are never chosen as eviction victims;
- shrinking below pinned residency fails and leaves the previous budget intact;
- success statistics distinguish loads, hits, evictions, resident bytes, peak
  resident bytes, resident banks and in-flight loads;
- disposal is idempotent and new acquisitions fail afterward.

Prefetch is a hint, not a permanent pin. A prefetched bank can be immediately
selected as the next LRU victim if the budget requires it.

## Acceptance

Node contract tests cover LRU behavior, load de-duplication, pinned-budget
failure, cancellation, prefetch, shrink and integrity failure before decode.
The browser smoke test serves a real verified lossless KTX2 bundle over loopback
HTTP under strict CSP and proves that a one-bank budget forces bank eviction while
subsequent accesses hit resident data.

Unity source-contract tests verify that GPU residency uses only existing verified
`Ktx2ArrayData` and `TextureArrayUpload`, has no network/Basis dependency, and
retains lease-aware destruction. Real Unity memory/device qualification remains a
separate GPU-host acceptance step.

Checksums and cache policy provide consistency and resource control, not identity
authentication.
