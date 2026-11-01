# Unity IL2CPP / Linear + instanced graph qualification v1

Image workstream BF-W9. This is a **separate** qualification profile layered on
top of the frozen KTX2/Texture2DArray pipeline. It does not change artwork,
identity keys, source mips, KTX2 bytes, or the existing Mono/Gamma standalone
contract.

## Scope

Two native-host profiles are defined:

- `windows-d3d11-il2cpp-linear`: Windows x64, Direct3D11, IL2CPP, Linear,
  Built-in render pipeline.
- `windows-d3d12-il2cpp-linear`: Windows x64, Direct3D12, IL2CPP, Linear,
  Built-in render pipeline.
- `linux-vulkan-il2cpp-linear`: Linux x64, Vulkan, IL2CPP, Linear, Built-in
  render pipeline.

The runner creates a fresh isolated project, imports the existing verified KTX2
bundle, saves the actual `Texture2DArray` subassets into a scene, builds a
non-development IL2CPP player, launches it on the same OS, and rejects any
backend/API/colour/pipeline fallback. The existing exact per-layer/mip CPU/GPU,
orientation, matte and source-over checks are rerun in the built player.

This milestone intentionally keeps the Built-in render pipeline. URP and HDRP are
separate next gates so a scripting-backend/colour-space regression is not mixed
with SRP setup or shader compatibility.

## Large graph workload

The same built player also runs deterministic **1,000** and **10,000** instance
texture-array workloads by default. The workload cycles through the complete
public identity/style inventory, batches by texture bank, caps each instanced
draw at 1,023 instances, and selects an existing mip so the exact framebuffer
stays within 2,048 x 2,048 pixels.

Every node occupies an integer pixel rectangle exactly the size of the selected
mip. There is no interpolation, overlap or layout ambiguity in this acceptance
image. A CPU reference buffer is assembled directly from the original validated
KTX2 layer bytes. The GPU framebuffer must match every byte and the report binds
both SHA-256 hashes.

This is a batching/correctness workload, **not FPS evidence**. It reports CPU
submission, forced readback, total qualification time, draw calls, framebuffer
size, selected mip and unique source sprites. Those timings include different
work on different machines and must not be advertised as a cross-device
performance score.

## Resource bounds

- 1..10,000 instances per workload; one to three strictly increasing workloads.
- Render target maximum 2,048 on either axis.
- Instanced batch maximum 1,023, matching Unity's bounded instanced API path.
- Existing KTX2 parser and texture payload limits remain unchanged.
- Existing player artifact inventory remains capped at 20,000 files / 2 GiB.

No missing IL2CPP toolchain, graphics API, instancing support, array-texture
support, GPU readback or shader support can become a successful skip.

## Commands

Preparation without Unity:

```powershell
python scripts/qualify-artwork-unity-advanced.py --confirm-public --prepare-only `
  --bundle _work/artwork-ktx2 --output _work/unity-advanced-prepared `
  --profile windows-d3d11-il2cpp-linear
```

Real Windows qualification:

```powershell
python scripts/qualify-artwork-unity-advanced.py --confirm-public `
  --bundle _work/artwork-ktx2 --output _work/unity-advanced `
  --profile windows-d3d11-il2cpp-linear `
  --unity 'C:\Program Files\Unity\Hub\Editor\6000.0.62f1\Editor\Unity.exe'
```

Linux uses `linux-vulkan-il2cpp-linear` and a native Linux editor. The installed
editor must include the relevant desktop IL2CPP build support. The runner does
not install Unity or handle licenses.

## Evidence

A success receipt is published only after:

1. build report pins IL2CPP, Linear, Built-in and the requested graphics API;
2. a non-development player exists and its complete artifact inventory is hashed;
3. the launched player independently reports compile-time IL2CPP and active Linear;
4. all existing exact texture/matte/orientation checks pass;
5. every configured graph framebuffer matches its CPU reference byte-for-byte;
6. the player artifact inventory is unchanged after execution.

Mock Python process tests exercise protocol failure handling only and are never
engine/GPU evidence. The real GPU workflow is manual-only on a configured,
licensed `unity-gpu` runner and accepts artifacts only from a successful
main-branch native benchmark.

## Next gates

After successful runs across the D3D11, D3D12 and Vulkan profiles:

1. add URP qualification with its own pipeline asset and shader path;
2. add HDRP qualification separately;
3. expand graph rendering beyond a correctness grid into culling/LOD/painter
   ordering and measured CPU/GPU/memory evidence;
4. broaden desktop APIs/devices, then compressed KTX2 and streaming/residency.

Unity documents texture arrays as supported on modern D3D, Vulkan-class/OpenGL,
Metal, GLES3 and WebGL2-class APIs, but each ByteFables qualification result is
bound only to the exact recorded host, API, editor version and build profile.
