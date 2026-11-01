# Unity URP / HDRP qualification v1

Image workstream BF-W9. This milestone keeps the frozen ByteFables KTX2 and
Texture2DArray data contracts intact and varies only the **render pipeline**.
It is separate from the Built-in IL2CPP/Linear profiles so backend, colour-space
and SRP failures remain attributable.

## Profiles

The runner defines five native desktop profiles:

- `windows-d3d11-urp-il2cpp-linear`
- `windows-d3d12-urp-il2cpp-linear`
- `linux-vulkan-urp-il2cpp-linear`
- `windows-d3d12-hdrp-il2cpp-linear`
- `linux-vulkan-hdrp-il2cpp-linear`

All use Unity 6.0, IL2CPP and Linear colour space. The isolated project pins the
Unity 6000.0 render-pipeline package line to **16.0.6** rather than resolving a
floating latest package. URP uses `com.unity.render-pipelines.universal`; HDRP
uses `com.unity.render-pipelines.high-definition`. The build report must observe
that exact resolved package version.

The existing Built-in profiles are not changed. Missing package resolution,
IL2CPP, graphics API, array textures, instancing, async readback, shader support,
or a working SRP is a hard failure.

## What is tested

A successful player must rerun the existing exact raw Texture2DArray contract:
all supplied mip/layer bytes, serialized identity/style bindings,
premultiplied-alpha matte checks, orientation sentinels, cross-bank overlaps and
disposal. It also retains the deterministic 1,000/10,000 instance exact graph
workload from the preceding milestone.

SRP adds a separate camera path. Up to 16 evenly spaced real identity/style
entries plus all four synthetic orientation/alpha sentinels are rendered through
an actual `Camera.Render()` call. Every selected mip is checked on transparent,
black and white backgrounds. The expected pixels come directly from the verified
KTX2 payload; the camera output permits at most one byte per component for
normalised blend/target rounding. `Graphics.Blit` cannot satisfy this SRP-camera
gate.

After a camera render, the player requires both:

- the active `RenderPipelineAsset` full type recorded in the request; and
- the instantiated `RenderPipelineManager.currentPipeline` runtime type.

A URP request cannot pass with HDRP, Built-in or a null/fallback pipeline, and
vice versa.

## Pipeline creation

The editor builder uses installed package runtime types rather than copying a
pipeline template. URP creates a `UniversalRendererData` asset and a
`UniversalRenderPipelineAsset` referencing it. HDRP creates an
`HDRenderPipelineAsset` and asks the installed package to ensure its global
settings when that API is available. The pipeline asset is assigned to both
GraphicsSettings and the active QualitySettings override before the scene is
saved and the standalone player is built.

The ByteFables package itself does not declare URP/HDRP as a mandatory dependency.
The isolated qualification project's root `Packages/manifest.json` selects exactly
one SRP package. Ordinary consumers of the core ByteFables package therefore do
not acquire either pipeline accidentally.

## Shaders

URP and HDRP have separate unlit qualification shaders with explicit
`RenderPipeline` tags. Both sample the existing `Texture2DArray` with an explicit
mip and use premultiplied `Blend One OneMinusSrcAlpha`. These are qualification
materials, not general lit identity shaders or a claim of feature parity with
Shader Graph, post-processing, HDR output, cameras stacks or custom passes.

## Evidence

A final receipt is written only when the build and launched player reports agree
on the exact editor, profile, graphics API, IL2CPP, Linear colour space, pipeline,
package/version, pipeline asset/runtime types and source manifests. Every expected
comparison count and graph framebuffer checksum must match. Player artifacts are
hashed before and after execution.

Preparation mode and Python mock-process tests never count as Unity/GPU evidence.
The real SRP workflow is manual-only on an approved, licensed `unity-gpu`
self-hosted runner and only consumes a successful main-branch native KTX2 artifact.

## Remaining work

Passing these profiles qualifies only the recorded desktop API/device/editor/SRP
combination. Remaining BF-W9 work includes broader hardware/driver coverage,
macOS/Metal and mobile APIs, richer graph culling/LOD/painter-order workloads,
compressed KTX2/Basis transport, async streaming/residency, and accessibility /
unique-identity studies. No whole-wave completion is claimed.

## References

- Unity 6 Universal Render Pipeline manual: https://docs.unity3d.com/6000.0/Manual/com.unity.render-pipelines.universal.html
- Unity 6 High Definition Render Pipeline manual: https://docs.unity3d.com/6000.0/Manual/com.unity.render-pipelines.high-definition.html
- Unity render-pipeline asset selection: https://docs.unity3d.com/6000.0/ScriptReference/Rendering.GraphicsSettings-isScriptableRenderPipelineEnabled.html
- RenderPipelineManager lifecycle: https://docs.unity3d.com/6000.0/ScriptReference/Rendering.RenderPipelineManager-activeRenderPipelineCreated.html
