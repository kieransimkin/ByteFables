# Video-effects implementation atlas — ByteFables / FrameRudiments

**Research date:** 2026-10-25. **Authority:** FrameRudiments owns every
pixel/video effect. **Scope:** public hash-based identity art, music visualisers,
and general-purpose compositing. This is a *technical research and engineering
inventory*, not a claim that each listed effect has shipped.

A machine-readable list of **143 separately named candidates**, including
**35 already supported by a specific FrameRudiments route** (sometimes only a
*stylised approximation*), lives in
[`../../manifests/video-effects-v1.json`](../../manifests/video-effects-v1.json).
The independent source host currently offers `visual`, `post_effects`,
`effect_graph`, `effect_graph_controls`, deterministic Rudiment renderers,
materials/emitters, and the optional Butterchurn/projectM effect chain.
These are several different APIs, not 143 new shader programs.

## 1. The basic implementation model

Video effects operate on one or more **typed surfaces** rather than just an
unannotated `uint8` RGB image:

- Frame `I(x,y,t)` with colour space, transfer function, alpha association,
  pixel aspect ratio, orientation, output dimensions and exact rational clock.
- Optional `A(x,y,t)` masks; `Z(x,y,t)` linear camera depth; normals `N`;
  velocity `V`; light/highlight masks; roughness; binary segment maps;
  calibrated music/beat sources; and **bounded** frame history.
- Deterministic parameter snapshot `P(t)` (including any hash-selected choices),
  versioned effect identity, state/checkpoints, and input hashes.

An image-processing node is conceptually
`O(t) = f(I_1(t), ..., I_n(t), P(t), history, context)`. Implementation
mechanisms are **point operations** (each pixel independent), **neighbourhood
filters** (convolution/local morphology), **resampling/warps** (sample source at
new coordinates), **multi-input compositing**, **temporal sampling**, **procedural
simulation**, or **analysis-assisted** effects (flow, tracking, segmentation).

These mechanisms determine CPU/GPU cost, buffer/texture requirements,
modulation eligibility, deterministic seeking, alpha correctness and whether
external evidence or models are needed.

### Computational taxonomy

| Primitive | Representative complexity | Likely backend | Examples |
| --- | --- | --- | --- |
| Per-pixel scalar/colour transform | `O(W H)` | CPU SIMD / GPU fragment | Exposure, gamma, channel mixer, tone curve |
| Texture coordinate transform | `O(W H)` + samples | GPU fragment / CPU bilinear | Fisheye, swirl, chromatic aberration |
| Small convolution | `O(W H K²)` naive | Separable/filter GPU | Blur, sharpening, edge |
| Separable convolution | `O(W H K)` | GPU two-pass / CPU vector | Gaussian, directional streak |
| Image pyramid | `O(W H)` per level | GPU mip / CPU multi-res | Bloom, local exposure, optical flow |
| Two-image blend | `O(W H)` | GPU fragment | Crossfade, screen, multiply, matte |
| Variable-radius neighbourhood | Cost scales with samples/radius | GPU compute | Bokeh, edge-preserving smoothing |
| Frame history | `O(W H N_frames)` naive | Cached temporal graph | Trails, echoes, shutters, slit-scan |
| Flow/tracking/segmentation | Algorithm/model dependent | CPU+GPU optional | Stabilise, morph, key/inpaint |
| Iterative simulation | Grid size × iterations | CPU/GPU compute | Reaction-diffusion, fire, fluids |

The complexity estimates describe typical implementations, not measured
FrameRudiments performance. Benchmark actual sizes, dependencies, and hardware.

## 2. Colour, light and grading

**Exposure.** Decode the input transfer function to scene-linear colour;
`C' = C × 2^EV`. Clamp/roll highlights only at a declared display/encoding
boundary. In contrast, an arbitrary RGB brightness multiplier is not a physical
exposure operation.

**Lift/gamma/gain, curves, contrast.** A pixel transform may use a constant
black offset, a midtone power law and a gain; per-channel monotone spline
curves allow shadow/highlight targeting. Preserve source neutral and avoid NaNs,
negative-value domain errors and hard clipping. FrameRudiments already offers
basic `visual.contrast`, `visual.gamma`, brightness/hue/saturation but **not a
verified OCIO scene-linear grading engine**.

**White balance / channel mixer / secondary selection.** Linear RGB can be
transformed by a chromatic-adaptation matrix or 3×3 channel mixer. Secondary
corrections need an independently inspectable hue/chroma/luminance matte.
Colour-space transforms MUST declare input and output primaries, transfer
functions and reference luminance rather than applying sRGB math to HDR.

**3D LUT.** Apply an input shaper if required; index a cube mapping `(R,G,B)`
into output colours using trilinear or tetrahedral interpolation. `.cube`
profiles are not substitutes for the full colour-management chain. The
[OpenColorIO LUT guide](https://opencolorio.readthedocs.io/en/stable/guides/using_ocio/using_ocio.html)
documents supported formats, shapers and caveats. Candidate production
backend: reviewed `OpenColorIO`, optional and version-pinned.

**HDR.** Work in appropriately sized floating-point linear buffers; apply a
specified tone/gamut mapping stage for target SDR/PQ/HLG output. Separate
artistic looks from colour-space conversion. See
[libplacebo's tone-mapping options](https://github.com/haasn/libplacebo/blob/master/docs/options.md).

## 3. Blur, sharpening and stylisation

**Gaussian blur.** Standard 2D Gaussian blur uses
`I'(x,y)=Σ I(x+i,y+j) Gσ(i,j)` with normalized weights.
Because the kernel is separable, use horizontal then vertical 1D passes.
Do this on premultiplied RGBA when blurring transparent shapes, with explicit
border policy and expanded effect bounds.

**Unsharp masking.** `I' = I + k (I - Gσ(I))`. Protect alpha and clip to the
working range. Edge-aware sharpening may use a threshold to avoid amplifying
noise. FrameRudiments already exposes `visual.sharpen`.

**Bilateral/guided filters** mix spatial proximity with colour similarity,
reducing smoothing across large edges. These are more expensive than simple
Gaussian filters, especially at large radii. Do not treat a tiny blur as a
fully edge-preserving denoiser.

**Pixelation** downsamples then upsamples using nearest-neighbour; **posterise**
quantizes values; **ordered dithering** compares pixels against an immutable
threshold matrix; **error-diffusion** propagates quantization residuals in a
specified scan order. For bit-for-bit reproducibility, keep explicit colour
space and dither seed. FrameRudiments already has the first three.

**Halftone/ASCII/edge/emboss** derive one or more luminance/alpha features and
rasterize shaped dots, glyphs, boundary contours or gradient-relief shadows.
For small hash avatars, test at 16/32 px; details can collapse into a nearly
uniform icon.

## 4. Camera and cinematic effects

**Bloom/glow.** Extract a highlight mask with threshold plus optional soft
knee; blur several downsampled copies; composite back into the unblurred
scene. This is why high-quality bloom naturally uses a mip/pyramid.
FrameRudiments `visual.glow` is an existing diffuse alpha-colour halo, not a
verified multiresolution HDR bloom filter. Blender's
[Glare Node](https://docs.blender.org/manual/en/4.4/compositing/types/filter/glare.html)
distinguishes bloom, ghosts, streaks and fog glow.

**Lens flares, ghosting, streaks.** Detect suitable highlight points, create
offset ghost copies from a lens-geometry model or convolution along a given
axis, then composite additively. Should support separate halo, anamorphic
streak and shaped aperture controls. Artistic approximations must not claim
photographic lens calibration.

**Chromatic aberration** resamples wavelength/channel slices at slightly
different UV coordinates, often radially varying. Distinguish simple RGB
shift (native) from per-colour displacement based on spectral selection and
matte edges (partly present in the FrameRudiments graph).

**Vignette** multiplies with a smooth ellipse/radial attenuation. **Lens
distortion** uses inverse mapping (e.g. calibrated radial coefficients), not
forward warping that leaves holes. **Heat haze** varies UV with coherent noise,
requiring bounded displacement and a deterministic source-time phase.

**Depth-of-field** computes a circle-of-confusion radius from depth/focus and
then gathers blur samples while treating occlusion and semi-transparency. It
requires a real depth/depth-like input, not simply blurring background pixels.

## 5. Compositing, mattes and keying

Use the W3C [Compositing and Blending specification](https://www.w3.org/TR/compositing-1/)
for exact formulae. For source-over in premultiplied colour:

```text
out.a   = src.a + dst.a * (1 - src.a)
out.rgb = src.rgb + dst.rgb * (1 - src.a)
```

For a multiply-style blend, unassociate RGB where alpha is nonzero, compute
`B(cb, cs)`, and then compose using the documented blend/composite semantics;
**do not** just multiply premultiplied RGB values. W3C defines multiply,
screen, overlay, soft-light, difference, hue, saturation and other modes.

**Chroma key** starts with a distance-to-key-colour mask, then applies
softness, spill suppression, edge despiking, clean foreground alpha, and garbage
mattes. Reference:
[Blender keying nodes](https://docs.staging.blender.org/manual/en/latest/compositing/types/keying/index.html).
The FrameRudiments graph already implements basic keying, luma/alpha mattes
and independently modulated displacement. Film-grade hair detail/roto remains
a separate milestone.

**Layer styles** such as outline, shadow, glow, bevel and emboss should derive
from the original or selected-stage alpha, not only RGB. Keep expanded padding,
source/derived masks and independent effect-graph branches. Transforms/effects
applied to one layer must not damage adjacent QR recovery symbols.

## 6. Geometry and displacement

An inverse sample warp can be represented as:

```text
out(x, y) = sample(src, x + dx(x,y,t), y + dy(x,y,t))
```

Different effects simply create different displacement functions:

- Ripple / sine / wave: periodic phase, amplitude, wavelength and origin.
- Swirl / twirl: radius-dependent angle around centre.
- Pinch / bulge: monotonic radius reparameterisation.
- Kaleidoscope: fold an angular sector then mirror/rotate.
- Lens distortion: radial polynomials with calibrated centre and crop/edge rule.
- Mesh / perspective warp: piecewise interpolation of image coordinates.
- Pixel sort: segment image by deterministic mask, sort according to bounded
  key; costly for animated high-resolution clips, and not a single fragment pass.

Use premultiplied sampling and preserve alpha; displacement maps are **data
inputs** with coordinate-space/type metadata. Overshoot requires transparent,
clamp/mirror or wrap border policy. Force texture/VRAM limits and ROI growth.

## 7. Time, motion, tracking and feedback

There are four distinct notions of temporal processing:

1. **True subframe composition**: evaluate the scene at `t + Δt` several times
   across a shutter interval, then integrate. FrameRudiments already offers
   8 temporal samples for supported sources.
2. **Motion-vector blur**: integrate samples displaced along available
   per-pixel velocity; a moving-object approximation, not new observed frames.
3. **History echoes**: composite a bounded ledger of *previously observed*
   frames with opacity/radius/position falloff. FrameRudiments has an optional
   encoded-frame shutter, separate from its directional streak approximation.
4. **Motion-interpolated synthetic frames**: estimate optical flow from
   source frame pairs, warp with occlusion/confidence and blend. This is
   analysis and can invent detail; it is NOT the same as subframe rendering.

OpenCV provides sparse Lucas–Kanade point tracking and dense Farnebäck flow
in its [Optical Flow guide](https://docs.opencv.org/4.x/d4/dee/tutorial_optical_flow.html).
FFmpeg `minterpolate` supports duplicate, simple blend and motion-compensated
interpolation modes: [filter reference](https://ffmpeg.org/ffmpeg-filters.html).

**Stabilisation:** detect/track features, fit a robust affine/projective camera
transform via RANSAC, smooth transform path, warp source and crop/extend
boundaries. Scene cuts and parallax need special handling. It's best built as an
optional analysis service feeding *saved pinned motion* to FrameRudiments.

**Feedback** intentionally maintains prior-frame state, e.g.
`F(t) = mix(I(t), warp(F(t-1)), decay)`; this is not random-access safe without
replaying prefix frames or checkpointing. FrameRudiments' chunk resume already
has a deterministic prefix replay strategy for its visualiser effects; all new
temporal nodes must honour its exact source clock and retained state contract.

## 8. Transitions

Most transitions combine two frames with a spatially varying reveal weight
`m(x,y,p)` and may resample or blur either input:

```text
out(x,y,p) = lerp_premult(A(x,y), B(x,y), m(x,y,p))
```

- Dissolve: constant `m = p`.
- Wipe: `m = smoothstep(q(x,y), q(x,y)+feather, p)` for projection `q`.
- Radial/clock: analogous distance/angle threshold.
- Luma/dissolve-map: use a third opacity/luminance texture as `q`.
- Pixel dissolve: assign every cell a frozen pseudorandom rank; reveal by `p`.
- Push/zoom/spin: progress-controlled inverse transforms with two inputs.
- Optical morph: warp each source using estimated motion toward its target,
  blend with confidence to limit stretch/occlusion artifacts.

FrameRudiments currently has dissolve, four directions of wipe, and radial
reveals. [GL Transitions](https://gl-transitions.com/) exposes a common GLSL
`transition(uv)` contract and a substantial transition collection, with
cross-language translations. Treat external shader sources as licensed,
untrusted optional code; import only through approved, pinned adapters.

## 9. Analog, digital and compression aesthetics

- Grain: seed a spatial noise field and vary coherently across frames. Static
  grain and independent per-frame noise have different visual results.
- Gate weave: bounded low-frequency translation/rotation of frame content.
- Film scratches/dust: persistent texture/sprites with finite lifetimes.
- VHS: low chroma bandwidth, scanline time-base jitter, head switching noise,
  luma/chroma offsets; a single RGB shift is only a stylised proxy.
- CRT: line structure, RGB phosphor/mask pattern, glow, optional curvature.
- Glitch: deterministic row/region offsets, channel swaps, block substitutions.
- Datamosh: use motion-compensated prediction residual/MV ideas *as visual
  simulation* unless deliberately editing an actual coded bitstream.
- Codec artefacts: block quantisation, ringing, banding/blur. Do not pretend a
  cosmetic pixel filter faithfully models H.264/AV1 quantisation.

FrameRudiments already has many of these **styled** treatments in
`visual.post_effects`. A library of curated combinations will be more useful
than copying small variants as independent GPU kernels.

## 10. Procedural, depth, and optional AI

**Procedural:** seeded fractal flames/Julia, reaction-diffusion, sprite emitters,
height-field lighting, particle motion, fire and fluid simulation. Control
simulation timestep, noise source, seed and checkpoint. Native FrameRudiments
already contains particle, fire/ice, and spatial views; ByteFables adds public
hash-conditioned source parameters, not a parallel renderer.

**Depth-aware:** depth fog, bokeh, SSAO-like local obscurance and relighting need
valid source depth/normals. If only a luminance image exists, reject
"physically correct depth" claims and label approximations accurately.

**AI-assisted:** segmentation, relighting, style transfer, frame
interpolation, super-resolution and inpainting are optional source/analysis
operations. Models must be pinned, sandboxed, offline by default, and their
outputs independently validated. OpenCV also provides classical
[Telea / Navier–Stokes inpainting](https://docs.opencv.org/5.0/main_modules/photo_inpaint.html)
without a neural model.

## 11. Host integration and dependency decisions

| Integration | Recommendation | Failure mode / status |
| --- | --- | --- |
| FrameRudiments `visual` / `post_effects` | **Immediate** presets; no new engine | Keys and bounds from its `VisualStyle` / `POST_RANGES` |
| FrameRudiments `effect_graph` | **Immediate** for currently supported graph nodes | Unknown graph nodes must fail, not silently bypass |
| `OpenColorIO` | Future opt-in colour-correct node | Needs space/transfer/LUT provenance, high precision |
| GL Transitions | Future approved shader adapter | Licensing, shader security, transition endpoint tests |
| OpenFX | Future sandboxed plugin host | Typed clips, temporal access, ownership and threading; not just `dlopen` |
| FFmpeg | Keep for encoding/export, optional validated filters | Filters may change sampling/alpha/timebase, protect manifests |
| libplacebo | Future video scaler/HDR shader backend | Context/render API, GPU availability, reproducibility differences |
| OpenCV | Optional offline analysis | Flow confidence, masking, crop, stabilization metadata |
| Butterchurn/projectM | Already optional FrameRudiments chain | Stateful, GPU environment dependent, no symbol-safe claims |
| DanceRudiments / DanceNotion | Single canonical parameter/time driver | No new BPM clocks in ByteFables |
| Blender | Optional 3D/material bake/import | Pin external render and all assets; no implicit scripts |

OpenFX publishes explicit
[clip, parameter, rendering and temporal-access contracts](https://openfx.readthedocs.io/en/main/Reference/).
Directly loading unknown OFX plugins into a secret-capable process is not
acceptable; keep trust boundaries and worker sandboxing.

## 12. ByteFables hash-driven style selection

The `public-video-look.v1` recipe catalogue intentionally reuses **16**
pre-existing host VisualStyle controls/presets, selected from a separate
SHA-256 domain based on the *full typed PUBLIC record*. It returns a
`post_effects` fragment; it does **not** render pixels or run an external host.

- Exactly **4 bits** of a domain-separated seed choose one of 16 presets.
- An independent seed portion sets native deterministic grain phase; it does
  not imply additional recoverable visual information.
- Intensity is bounded and interpolated toward the neutral VisualStyle defaults.
- `frame` and validated `layer:ID` scopes use existing host effect targets.
- `purpose: 'optical-recovery'` **hard rejects** artistic effects on QR/code
  pixels; metadata, captions and separate regions may still be styled through
  approved production layouts.
- Values are a best-effort visual presentation. Do not treat perceptual
  differences as authentication or reversible encoding.

Future hash-driven controls should be exposed as a `featureAxis` registry with
explicit contradictory pairs, confidence and perceptual distinctiveness
metrics. In the initial release only exact preset selection and reproducible
parameter recipes are executable.

## 13. Test/QA contract and protection for recovery formats

**For every implemented effect** maintain:

- alpha/reference: opaque, transparent, antialiased, straight/premultiplied
  zero-alpha contamination; SDR/HDR and checkerboard transparency;
- spatial: 16/32 px, 128/1024 px, portrait/wide, crop and padding;
- temporal: first frame, seek to arbitrary N, repeat window, variable BPM,
  chunk resume and checkpoint; cross-time/clock validation;
- resource: CPU and optional GPU timing, allocations, cache hits and peak VRAM;
- identity: same source + same version yields equal deterministic settings;
  toggling selected bits changes expected feature paths, not cryptographic IDs;
- colour: explicit transformations/round-trip/visual comparison with
  independently known reference colour patches;
- optical: **rendered/scanned QR symbol is separated from artistic effects**;
  if any artistic effect touches the machine-readable region, recovery status
  resets to unqualified until independent scanner readback.

For exported video evaluate signal and timing with FFmpeg/ffprobe, plus optional
VMAF, PSNR, SSIM and optical checks. These metrics are not direct measures of
visual-semantic fidelity. Also assess visually with blinded human or independent
review; avoid cherry-picked frames or altered baselines.

## 14. Primary reference links

1. [FrameRudiments unified effects roadmap](https://github.com/kieransimkin/FrameRudiments/blob/main/docs/unified-effects-transitions-rendering-roadmap.md)
2. [FrameRudiments post effects](https://github.com/kieransimkin/FrameRudiments/blob/main/docs/scoped-post-effects.md)
3. [FrameRudiments quality / time](https://github.com/kieransimkin/FrameRudiments/blob/main/docs/quality-effects.md)
4. [W3C Compositing and Blending](https://www.w3.org/TR/compositing-1/)
5. [OpenColorIO](https://opencolorio.readthedocs.io/en/stable/guides/using_ocio/using_ocio.html)
6. [OpenFX 1.5.1](https://openfx.readthedocs.io/en/main/Reference/)
7. [FFmpeg Filters](https://ffmpeg.org/ffmpeg-filters.html)
8. [OpenCV Optical Flow](https://docs.opencv.org/4.x/d4/dee/tutorial_optical_flow.html)
9. [Blender Glare](https://docs.blender.org/manual/en/4.4/compositing/types/filter/glare.html)
10. [Blender Keying](https://docs.staging.blender.org/manual/en/latest/compositing/types/keying/index.html)
11. [GL Transitions](https://gl-transitions.com/)
12. [libplacebo](https://libplacebo.org/custom-shaders/)
13. [WebGPU compute blur examples](https://webkit.org/demos/webgpu/)

**Legal/integration note:** public online examples and shader catalogues are
research references, NOT automatically vendored code or safe-to-execute
plugins. Verify licences, provenance, precise specifications and CI
compatibility before copying or hosting implementations.
