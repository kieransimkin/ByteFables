# Runtime texture atlases v1

Image-output workstreams: BF-W7 and BF-W9. Experimental, PUBLIC and
presentation-only. This is a packaging/runtime-consumer milestone, not a new
artwork renderer, authenticity mechanism, reversible encoding or wallet format.

## Input and output

Input is a completed `bytefables.artwork-asset-bundle.v1` directory from the
existing native-image pipeline. The exporter verifies its entire file inventory
and decoded frames before packaging. PNGs at the requested native size must
already exist for **every** identity/style; missing sizes are errors. There is
no implicit resize, colour transform, palette change, or alpha reconstruction.
The source artwork retains the native compositor's opaque dark matte. Empty
texture cells are transparent RGBA zeroes.

```sh
python scripts/export-artwork-textures.py --confirm-public export \
  --bundle _work/artwork-assets --output _work/artwork-textures \
  --native-size 64 --page-size 1024 --padding 2
python scripts/export-artwork-textures.py --confirm-public verify \
  --bundle _work/artwork-textures --source-bundle _work/artwork-assets
python -m http.server 8765 --bind 127.0.0.1 --directory _work/artwork-textures
```

Open `http://127.0.0.1:8765/`. The viewer requires HTTP(S), not `file://`.
The export refuses an existing output directory, symlink/reparse paths, missing
public confirmation and outputs nested inside the source bundle. It writes a
success manifest only after saved-page and complete-package validation. Failed
exports retain `failure.json` and cannot be reused or verified as successful.

Runtime layout and PNG packaging live in the optional FrameRudiments integration;
ByteFables coordinates validation and identity metadata. The web consumers only
place pre-rendered textures. They do not evaluate a procedural artwork generator,
effect graph, animation clock, native renderer or model in the browser.

## Geometry and identity contract

`schema: bytefables.artwork-texture-bundle.v1`

`profile: bytefables.texture-layout.v1`

One bundle selects one native size: 16, 32, 64 or 128 pixels. Page extents are
square powers of two from 64 through 4096. Padding is 1..16 pixels; default 2.
Pitch is `nativeSize + 2 * padding`; cells are packed row-major. Whole pages
remain square, including the final page. There is no rotation or trimming.

Sprites sort by `(family, palette, complexity, full public digest)`, independent
of source array order. `spriteKey` is domain/version-labelled SHA-256 over the
identity/style/native-size/decoded-pixel tuple, encoded as the exact pretty JSON
used by `tools.artwork_native_benchmark._json`. The fixed key order is profile,
digestHex, family, palette, complexity, nativeSize, rgbaSha256. The geometry
fixture freezes this cross-Python/JavaScript contract. Changing packing settings
does not change these keys. Neither a file checksum nor a key authenticates an
identity: a malicious party can replace an unsigned manifest and its images.

Each sprite has `pageIndex`, `rect: [left, top, right, bottom]` with exclusive
right/bottom bounds, the full identity digest and style fields, the source PNG
path/checksum and its decoded RGBA checksum. Pixels in the rectangle are exact
copies of the native source. Gutters duplicate the nearest edge/corner pixel.
PNG readback checks all interiors, all gutters and every unused pixel, including
otherwise invisible RGB under zero alpha.

For a page extent `N`, the two **edge-coordinate** UV conventions are:

- `uvTopLeft = [left/N, top/N, right/N, bottom/N]`.
- `uvBottomLeft = [left/N, 1-bottom/N, right/N, 1-top/N]`.

The browser shader uses top-left UVs, top-left destination coordinates and an
unflipped upload. Native-size fragment centres then sample texel centres. Do not
apply a second vertical flip. The bottom-left values are metadata for external
consumers; no Unity importer qualification is claimed in this milestone.

## Sampling and bounds

Use clamp-to-edge wrapping and nearest or linear filtering. **No mipmaps are
created or permitted in this profile.** A conventional whole-page mip chain can
mix neighbouring sprites. Gutter replication is not a claim of arbitrary
minification quality, anisotropic filtering safety or mip-level isolation.
Separate already-rendered native-size bundles provide the available resolutions.

Export bounds: 1..8192 sprites, at most 128 pages, at most 64 million allocated
page pixels and 512 MiB output bytes. Encoded page bounds also scale with the
pixel count, avoiding large unknown PNG payloads. PNGs must be static RGBA with
no metadata. The consumer defaults to a **64 MiB decoded-texture budget** and
accepts an explicit limit up to 256 MiB. This is a raw-pixel budget, not a promise
about total browser/GPU memory: bitmaps, decode scratch space and GPU copies add
overhead. Individual canvases are bounded to 8192 on either axis and 16 million
pixels. Workloads are limited to 10,000 instances.

## Browser integration

Load the shipped `runtime.js` as a normal external script. It exposes
`globalThis.ByteFablesTextures`; there is no CDN, framework or package dependency.

```js
const api = globalThis.ByteFablesTextures;
const bundle = await api.loadBundle('/public-identities/', {
  // Pin this to an independently trusted value when integrity matters.
  manifestSha256: expectedManifestSha256,
  maxTextureBytes: 64 * 1024 * 1024,
});
const spriteIndex = api.lookup(bundle.manifest, {
  digestHex: fullPublicDigest, family: 'sigil', palette: 'neon', complexity: 4,
});
const display = new api.WebGLAtlas(canvas, bundle, {filter: 'nearest'});
display.draw([{spriteIndex, x: 0, y: 0, width: 64, height: 64}]);
// When the owning UI is removed:
display.dispose();
bundle.dispose();
```

`CanvasAtlas` has the same constructor/draw/dispose contract. Choose a separate
canvas when switching context types. WebGL2 batches contiguous page runs with
instanced quads, preserving painter order even for overlapping sprites. It does
not silently fall back after a GL failure. Context loss makes draws fail closed;
create a new consumer after restoration. The caller owns the bundle and disposes
its decoded bitmaps independently of each renderer's GPU resources.

The loader allows only same-origin HTTP(S) directories, refuses redirects and
credentials, bounds reads, validates layout and source paths, checks optional
manifest pins, checks sprite identity/pixel keys and every PNG file SHA-256, then
independently verifies the decoded page RGBA SHA-256 with browser Canvas. It does
not execute manifest-supplied code. Production CSP stays `script-src 'self'`,
without unsafe-eval/unsafe-inline. Serving untrusted manifest directories is not a
substitute for trusted deployment: a party controlling the directory can also
replace its HTML/JavaScript unless those are pinned by the embedding application.

## Demo and measurement

`index.html` displays 100, 1,000 or 10,000 instances, subject to pixel budgets.
It reports **both** instance count and unique identity/style count. Repetition of
144 source sprites into 1,000 instances is a display workload, not a 1,000-unique-
identity discrimination study. An inspection control exposes the full digest,
style, sprite key and source rectangle. The page redraws on explicit input only.
There are no continuous animation loops or telemetry.

`submitMilliseconds` measures CPU draw submission, including buffer upload for
WebGL. It excludes proof of GPU completion; do not label it FPS, GPU latency or
cross-device performance. Full pixel readback belongs to the tests, not this
submission timing metric.

## Tests and remaining gates

```sh
node --test tests/artwork-texture-runtime.test.mjs
python -m unittest discover -s tests/python -p test_artwork_texture_bundle.py -v
python tests/browser/artwork-textures-smoke.py --bundle _work/artwork-textures \
  --report _work/artwork-textures-browser.json
```

The default browser test requires BOTH Canvas2D and WebGL2, loads the actual HTTP
viewer under its CSP, and compares all pixels of a 1,000-instance frame with an
independent Pillow copy of the original texture tiles. SHA-256 covers complete
RGBA buffers; no perceptual tolerance or approximate match is substituted.

A separate `--offline-contract` mode exercises saved PNG bytes and trusted local
runtime code in a blank browser page, without any HTTP request. Its report
explicitly says the HTTP loader/UI were not exercised. `--backend canvas2d` is an
explicit narrower contract test, not an automatic successful GPU skip. CI uses
the default full test. Missing browser/GL support is a failure there.

The prior gallery smoke test's string-predicate polling invoked eval under
Playwright 1.57 and conflicted with the gallery CSP. It now uses locator
assertions and `HTMLImageElement.decode()` on the actual image under test, rather
than waiting for off-screen lazy images or weakening CSP.

Open gates: successful full HTTP/WebGL CI execution for this patch, additional
real browser/device coverage, driver-specific colour/sampling checks,
transparent native compositor export, per-sprite mipmaps/KTX2, Unity import,
and measured human recognisability. Passing packed-pixel tests is not evidence
that icons are visually unique or accessible to every viewer.

## Primary API references

- WebGL 2 specification: https://registry.khronos.org/webgl/specs/latest/2.0/
- Texture sampling parameters: https://developer.mozilla.org/en-US/docs/Web/API/WebGLRenderingContext/texParameter
- Playwright locator evaluation/assertions: https://playwright.dev/python/docs/api/class-locator

Reviewed for this implementation on 2026-11-01. The current WebGL editor draft
is work in progress; the runtime only uses established WebGL2 core operations.
