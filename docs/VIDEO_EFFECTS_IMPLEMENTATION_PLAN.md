# Video effects programme — ByteFables consumes FrameRudiments

**Checkpoint:** 2026-10-25. **Scope:** effects catalogue, reusable host effects,
public hash-based styling, rendered public identity video and ordinary creative
media. **Sources:** [methodology](research/video-effects-methods-2026-10.md),
[manifest](../manifests/video-effects-v1.json),
[public look contract](specs/public-video-looks-v1.md),
[FrameRudiments unified roadmap](https://github.com/kieransimkin/FrameRudiments/blob/main/docs/unified-effects-transitions-rendering-roadmap.md).

## Governing rule

**FrameRudiments implements every effect, generator, compositing operation and
export**. ByteFables publishes public, deterministic identity-derived effect
**configuration and catalogue metadata** only. Where FrameRudiments already
provides a usable control, publish a tested preset instead of implementing an
extra shader or filter. For missing effects, contribute changes to FrameRudiments'
own repository under its effect-graph roadmap. Experimental neural inference is
a hash-pinned source/analysis job and must not bypass the native host for final
media composition.

## Priority waves and exit gates

| Wave | Main deliverables | Evidence gate |
| --- | --- | --- |
| **VE0 — catalogue + public recipes (this increment)** | Research 143 candidates, 16 FrameRudiments `post_effects` presets, `video-look` CLI and manifest validator | Frozen naming/order, validation, deterministic stage output, explicit research statuses |
| **VE1 — effect descriptor/unification** | Native per-effect descriptors (ports, colour/alpha, bounds, time, range, units, animation, controls), source-to-graph adapter | Existing effects and no-op legacy render pixel regression; invalid modes fail |
| **VE2 — advanced grades and light** | OCIO-approved colour pipeline, shaper/3D LUT, scene-linear HDR/SDR tone map, multi-scale bloom, flare/streaks | Reference colour patches + transparent/HDR tests, no incorrect label on simple glow |
| **VE3 — masking, layer style, blend** | W3C blend family, alpha/SDF outlines/shadow/bevel, improved chroma key/garbage matte/despill | Strict premult-alpha golden tests and host graph fork/mask tests |
| **VE4 — transitions** | Luma/clock/pixel/zoom/warp/mask-based transitions, optional GL Transitions adapter | Exact at 0/1 endpoints, alpha correct, deterministic seed and arbitrary source dimensions |
| **VE5 — native motion and temporal graph** | Explicit time/frame ports, sequential feedback/checkpoint contract, temporal colour glitch, slit scan and history | Random seek and chunk-resume equality where supported; declared state otherwise |
| **VE6 — GPU parity, optimisation** | Typed GPU passes, pass fusion, intermediate texture reuse, bounded shaders, staged CPU fallback | Record actual CPU/GPU diff, VRAM peaks, deterministic fallbacks and failure modes |
| **VE7 — tracking and analysis** | Optional optical flow, stabilization/scene cuts, depth and segmentation based masks | Independent flow/device tests, occlusion and low-confidence paths, pinned source clips |
| **VE8 — style-bits + identity tests** | Hash-to-typed effect axes, visual similarity/classifier study at 16/32/64px, cross-artist style families, provenance | Blinded discrimination, nearest-neighbour/false-match stats, reference seed equality |
| **VE9 — authoring and release** | FrameRudiments visual effect browser, param introspection, graphs/presets/UX, profile export via DanceFlow MCP | Pin renderer/manifest/third-party licences and audit complete release artifacts |

### Engineering issues (preferred pull request order)

**P0 — Contracts and proofs**

1. `FX-001` Read `VisualStyle`/`POST_RANGES`/quality params from FrameRudiments
   metadata rather than relying on copied field lists; keep an explicit
   version/compatibility range.
2. `FX-002` Add a FrameRudiments effect-capability discovery API with stable
   namespaced IDs, input/output texture ports, masks and control metadata.
3. `FX-003` Require separate optical-protected and decorative layers; validate
   no `post_effects.frame` stage can inadvertently recolour barcode regions.
4. `FX-004` Add per-stage readback and before/after synthetic fixtures (RGBA
   with transparent borders; 16/32/128/1024 pixels; portrait and landscape).
5. `FX-005` Native host reproducibility: renderer release, Pillow/FFmpeg,
   shader/asset hash, CPU/GPU backend, exact time and graph parameters.

**P1 — Largest leverage with manageable cost**

6. `FX-006` W3C blend/Porter-Duff parity cases and linear/encoded colour choice.
7. `FX-007` Scene-linear multisize bloom/glow, highlights and flare controls.
8. `FX-008` 1D/shaper/3D `.cube` LUT and explicit OCIO colour transform stages.
9. `FX-009` Matte morphology, SDF-based outline/shadow/bevel that works on
   isolatable source-alpha and child graph branches.
10. `FX-010` Luma/pixel-dissolve/clock-wipe transitions with actual
    FrameRudiments `transition` graph nodes, not duplicate ByteFables code.
11. `FX-011` FrameRudiments unit tests for each supported `effect_graph_controls`
    parameter via native DanceRudiments source-time snapshots.
12. `FX-012` Pixel-centre/coordinate sampling, bounds-growth, transparent
    resampling and 16px legibility reference cases.

**P2 — Temporal and analysis-assisted work**

13. `FX-013` Frame history, mutable-feedback state policy, deterministic
    checkpoint/replay and chunk/seek semantics.
14. `FX-014` Optical flow as cached external provenance data, frame
    interpolation and motion-compensated blur with confidence masks.
15. `FX-015` Per-frame stabilization transform path with feature tracking,
    RANSAC, smoothing, crop/safe-border rules and scene-cut detection.
16. `FX-016` Controlled rolling shutter, slit scan, datamosh-style motion
    simulation, VHS head-switching and tape jitter profiles.
17. `FX-017` GPU compute/pass-fusion benchmark at 128/512/1080p with known
    graph branch fan-out; resource/quality budgets and CPU reference.
18. `FX-018` Evaluate GL Transitions shader pack and optional sandboxed OFX
    plugin route. Never execute arbitrary shader text from ByteFables JSON.
19. `FX-019` Native FrameRudiments generator assets: fractal flames,
    reaction-diffusion, caustics, procedural lens dirt, orbital animations.

**P3 — System integration / experimental**

20. `FX-020` Design browser/desktop effect UI using the host's typed descriptor
    database, including sliders for every animatable property.
21. `FX-021` Bind public-hash feature-axis pairs to native effect parameter
    variants with explicit cost, fallback and unsupported-feature reporting.
22. `FX-022` Benchmark visual identity confusion vs cost and effect stacking;
    compare 3/4/8/32-byte hash styles and original public identities.
23. `FX-023` Make identity cards optically recoverable regardless of decoration;
    decode *exported* public QR under chosen scanner and physical damage model.
24. `FX-024` Cross-carrier watermark R&D remains a separate opt-in host module
    (embedding/extraction is not a synonym for ordinary video filters).
25. `FX-025` Review shader/3rd-party licences, supported hardware and
    vulnerability/sandbox permissions before shipping GPU/OFX hooks.

## Definition of done for one effect

Each effect or preset must have a reviewed ID, source of truth, parameter
schema, colour/alpha/space/time contract, deterministic seed policy, explicit
inputs and outputs, resource bound, working code, CPU or GPU acceptance fixture,
restoration/legacy compatibility tests and a sample in the native effects
gallery. A named effect in the ByteFables research manifest **does not count**
as delivered until the native FrameRudiments implementation and tests exist.

## Host composition and QR safety example

```json
{
  "post_effects": {
    "elements": {
      "layer:public-avatar": [
        {"id":"bytefables-video-look-v1", "visual":{"glow":5,"contrast":1.2}}
      ]
    }
  }
}
```

The canonical QR/coded-symbol `layer:public-recovery-qr` remains isolated and
untouched in this example. **Do not** instead put those post-effects under
`post_effects.frame`: a frame-wide pass may corrupt the symbol. A full
recovery-card production profile must guarantee masks, layer isolation and
post-export scanner verification.

The video look API permits `post_effects.frame` **only** with explicitly
selected `purpose: 'public-video'`. The safe default affects only
`layer:bytefables-identity`; use `target: 'layer:public-avatar'` when making optical recovery cards.
There is no secure private-key import/export workflow in this programme.
