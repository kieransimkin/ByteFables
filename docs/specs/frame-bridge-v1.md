# ByteFables ↔ FrameRudiments renderer bridge v1

**Status:** experimental, public-only. ByteFables generates **declarative**
`framerudiments.project.v1` `type: "rudiment"` *layer fragments*. FrameRudiments
remains the **only runtime** for new visual generators, effects, composites,
quality processing, timeline, video and sprite outputs. The ByteFables core
retains only its legacy `renderPixelAvatar` image exporter;
new production graphics may NOT introduce another renderer pipeline.

## Producer

- `createFrameRudimentsIdentityLayer(publicRecord, {id,bounds,palette})` emits
  `renderer: bytefables-pixel-v1`. It supplies a 64-lowercase-hex SHA-256
  **public record digest** (covering every context field), never source bytes.
- `createFrameRudimentsMatrixLayer(publicMatrix, {id,bounds})` emits
  `renderer: bytefables-matrix-v1`. It supplies binary row-major modules,
  dimensions, format ID and quiet-zone modules. This is *not a barcode codec*.
- `createFrameRudimentsSceneLayer(publicScene, {id,bounds})` emits
  `renderer: bytefables-scene-v1`, a strictly validated primitive scene. Bridge
  v1 accepts rect/circle/line and absolute closed M/L/H/V/Z paths only.

All use `bridge_version: "bytefables.framerudiments.layer.v1"`; a breaking
change requires v2 and new renderer identifiers. Layer IDs are validated
lowercase names, and bounds are integer pixel rectangles relative to the
native project frame. A generated `motion: {kind: "named", pattern: "circle"}`
meets FrameRudiments' current RudimentLayer native-motion requirement; these
static generators do not use motion to invent content. Host effects are free
to bind real DanceRudiments motion to `layer:ID` and frame scopes.

## Consumer/installation

The independent optional Python package lives in
`integrations/framerudiments/bytefables_framerudiments`. Install into the **same
Python environment** as an existing, compatible FrameRudiments runtime:

```sh
python -m pip install ./integrations/framerudiments
```

Then explicitly register its trusted factories in the caller's local renderer
registry. A project JSON can only select registered names; it cannot execute
Python imports or arbitrary plugins. The host's source hashing captures factory
code identity, and ordinary FrameRudiments project assets must remain pinned.

```python
from framerudiments import Project, default_renderers, preflight, render
from bytefables_framerudiments import register_bytefables_renderers

registry = register_bytefables_renderers(default_renderers())
project = Project.load("project.json")
preflight(project, "preflight", renderers=registry)
render(project, "new-render", renderers=registry)
```

Copy emitted layer fragments into the project's `layers` array. The real
project must still define its own valid `audio`, `clock`, dimensions and
source provenance; ByteFables does not forge dummy audio or replace the native
FrameRudiments project owner. This integration requires tested host API support
as described in FrameRudiments' `docs/rudiment-renderers.md`.
An optional smoke test (`tests/python/test_optional_native_host.py`) executes
against the **real** Python registry when installed; the default CI contract
job exercises only the public plugin factories, not an actual encoded video.

For native effects, author directly in the existing FrameRudiments pipeline:

```json
{
  "post_effects": {
    "elements": {
      "layer:avatar-one": [
        {"id": "glow", "visual": {"glow": 4, "hue_shift": 20}}
      ]
    }
  }
}
```

Existing `effect_graph`, masks, visuals, Beat/DanceRudiments modulation,
Butterchurn and projectM remain native host features. **Do not reimplement**
these controls or stages in ByteFables. Reusable generators should be added as
FrameRudiments registered renderers or native effect-graph sources; improvements
with broad non-ByteFables applicability belong in FrameRudiments itself.

## Presentation vs recoverability

`bytefables-pixel-v1` is deliberately NOT reversible. Its visible output
contains far less than 256 bits and may collide. A matrix layer accepts already
encoded public bits, but *does not certify* scanner compatibility. Blurring,
warping, antialiasing, cropping, feedback, mask effects, lossy video or printed
media may corrupt it. Scanner readback must occur on the **final** artifact;
for restoration require complete envelope check plus type-aware comparison.

The FrameRudiments host has a 60-fps/audio-oriented project contract, which
is not a static image exporter API. Phase A deliberately provides project-layer
fragments and registered generators, **not** a promised standalone still-image
render command. A native still-frame export contract should be developed in
FrameRudiments, not copied into ByteFables.

## Conformance

Node tests cover typed input, deterministic digest and fragment generation.
Python tests exercise the registered factories using Pillow and synthetic public
fixtures. Actual FrameRudiments composition, effect graph, FFmpeg and GPU output
must be tested in an installed FrameRudiments host before claiming production
integration or cross-platform pixel identity. Pillow renders can vary across
pinned library versions; the native host pins version and provenance.


## Future invisible-watermark effect operations

Watermarks are **not** visual generators. The existing renderer factories are
insufficient to implement a robust hidden signal in the final delivered media.
The ByteFables core implements only `BFWM` v1 message framing and a research
planner. Image/audio/video/text *embed and detect* must be implemented as
reusable, explicitly registered **native FrameRudiments effects / controlled
text generators**, with per-medium clocks, encoder placement, FEC and blind
post-export verification. FrameRudiments' fixed effect graph node-kind list
currently needs an upstream extension API for these transforms. Never fake a
watermark by applying a filter to the existing avatar generator and asserting
that original bytes can be recovered from it.

See [the watermark contract and research gate](watermark-v1.md).
