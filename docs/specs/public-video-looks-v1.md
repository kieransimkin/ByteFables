# ByteFables public video looks → FrameRudiments, v1

**Schema:** `bytefables.public-video-look.v1` (declarative recipe).
**Security:** public-only decorative display. No private keys, seed material or
unpublished credentials. No cryptographic identity proof and no embedded hash
recovery guarantee.
**Host:** FrameRudiments `post_effects` through its existing `VisualStyle`.
ByteFables does not implement post effects, shader loops, media decode, or
rasterisation.

## Wire/API contract

```ts
const record = new PublicRecord(ByteValue.public(bytes, {
  namespace: 'danceflow', kind: 'node-id'
}));
const look = await planPublicVideoLook(record, {
  look: 'auto', intensity: 0.8, target: 'layer:agent-face',
  purpose: 'public-art'
});
// look.post_effects.elements['layer:agent-face'] is a FrameRudiments stage array.
// The caller merges it with other stages without overwriting neighbouring scopes.
```

The default target is `layer:bytefables-identity`; explicit `target: 'frame'`
is accepted **only** with `purpose: 'public-video'`. Every other target is a
strictly validated `layer:<id>`. FrameRudiments owns the pipeline ordering, layers, masks,
modulators, compositing, alpha, clocks, rendering and final export. Do not
merge two `post_effects` objects using replacement semantics; append their
stages under the same target with unique IDs instead.

## Deterministic selection

1. Compute the existing context-complete `publicRecordDigest`, SHA-256 of the
   canonical typed PUBLIC record.
2. Compute
   `SHA256(UTF8("ByteFables:framerudiments:video-look:v1\\0") || digest)`.
3. The **high four bits** of seed byte zero select one of the **frozen sixteen**
   look recipes. The next two bytes select a reproducible `grain_seed` where
   the preset uses grain. An explicit `look` overrides the selection.
4. Interpolate each authored numeric parameter from FrameRudiments' documented
   neutral value to the selected preset using bounded `intensity` in `[0,1]`.
   Integral fields use a fixed round-to-nearest rule.
5. Emit only a declarative `post_effects.frame` or `post_effects.elements`.
   No I/O, animation loop, GPU, model, processing or file generation occurs.

The public digest remains the authoritative identity. The 4-bit style choice
cannot represent or uniquely distinguish a 256-bit hash; the image is not a
reversible hash codec. All 16 presets are designed as **artistic presets of
existing effects**, not independent physically accurate simulation models.

## Available looks

| ID | Main existing knobs |
| --- | --- |
| `subtle-film` | colour + fine grain + vignette |
| `noir` | saturation/contrast + grain |
| `cool-grade` | hue/contrast/saturation |
| `warm-grade` | hue/contrast/saturation |
| `neon-bloom` | FrameRudiments diffuse-alpha `glow`, not HDR bloom |
| `crt-soft` | lines/channel-shift/vignette |
| `crt-heavy` | stronger line/colour/noise modulation |
| `vhs-inspired` | seeded digital row glitches, scanlines and colour shift; no tape transport model |
| `retro-pixel` | pixel size, posterisation, ordered dither |
| `print-halftone` | dot screen, contrast, edge extraction |
| `solar-poster` | posterisation and solarisation |
| `bright-soft` | brightness, blur, diffuse glow |
| `crisp-etched` | sharpen, contrast, alpha-edge accent |
| `dream-glow` | glow/blur/saturation |
| `scanline-ghost` | scanline/grain/vignette |
| `minimal-matte` | restrained saturation and low-contrast grade |

## Optical and archival exclusion

`purpose: 'optical-recovery'` always throws, even when `intensity = 0`.
Frame-wide styling requires `purpose: 'public-video'`; the ordinary
`public-art` path is restricted to a named decorative layer. These
non-reversible effects must not run on QR modules, Data Matrix symbols,
colour-calibration bars or exact proof images. Put artwork in separately
composited layers, protect the QR stencil with a no-effects route, render through
the optically qualified host path, and independently scan the actual exported
artifact. Scanning success is media-/scanner-profile-dependent, not permanent.

Never use artistic avatar glyphs, style IDs, human visual resemblance or
rendering output hashes for cryptographic authorisation or wallet recovery.

## Test obligations

- Pinned deterministic vectors for public typed input, look selection and
  granular scope. Binary/JS versions do not change an existing version's
  selection ordering or neutral values; new looks require a new version.
- Reject secret objects, invalid intensity/target/purpose/IDs, NaN/Infinity.
- Validate every emitted `visual.*` field against installed FrameRudiments
  contract at actual integration time, and report an explicit capability miss.
- Keep `post_effects` output separate from QR/symbol recoverability.
- Compare native CPU reference and, when implemented, GPU output by declared
  tolerance/colour space, not assumed identical numerical pixels.

Research and planned host work:
[video effect atlas](../research/video-effects-methods-2026-10.md),
[implementation plan](../VIDEO_EFFECTS_IMPLEMENTATION_PLAN.md).
