# Transparent GPU texture arrays and isolated mip levels v1

Image workstreams BF-W7 / BF-W9. PUBLIC presentation only. This is a separate
format from the already qualified opaque atlas; no old seed, renderer, source
image or blending contract is changed. This milestone implements mip packaging
and a texture consumer, not a new artwork generator.

## Inputs and outputs

Input: a verified `bytefables.transparent-artwork-bundle.v1` containing PNGs for
**every** identity/style at the requested native size (16, 32, 64 or 128).
Missing native sizes are an error. The source package must pass all its existing
file, alpha and native-matte recomposition checks before export. The exporter
never subtracts a matte or estimates alpha from a flattened image.

Output: `bytefables.alpha-texture-array-bundle.v1`, profile
`bytefables.premultiplied-area-mips.v1`. It contains `manifest.json`, bounded raw
`levels/bank-NNN-mip-LL.rgba` files, and the self-contained HTTP preview. Raw files
are **not PNG, KTX2, Basis or compressed GPU textures**. They are layer-major,
then top-left row-major premultiplied RGBA8, without padding, headers or metadata.

Each sprite occupies one full array layer. Each bank contains at most the chosen
`layersPerBank` (1..256, default 128). All levels from native size to 1x1 are
explicit. WebGL uses `TEXTURE_2D_ARRAY`, not a whole-page atlas mip chain; array
layers are not blended with neighbouring layers when sampling. No GPU mip
builder is called, so host-specific mip generation cannot alter saved levels.

```sh
python scripts/export-artwork-alpha-textures.py --confirm-public export \
  --bundle _work/artwork-transparent --output _work/artwork-alpha-textures \
  --native-size 64 --layers-per-bank 128
python scripts/export-artwork-alpha-textures.py --confirm-public verify \
  --bundle _work/artwork-alpha-textures --source-bundle _work/artwork-transparent
python -m http.server 8765 --bind 127.0.0.1 --directory _work/artwork-alpha-textures
```

Open `http://127.0.0.1:8765/`. GPU use requires WebGL2; missing support is reported
as an error, not a silent switch to the old opaque runtime. Packaging a completed
source bundle does not require the full native host or another render run.

## Alpha, colour and numerical contract

Original lossless source PNGs remain **straight/unassociated RGBA**. GPU levels
are a derived, quantised **premultiplied** representation, including level zero.
Hidden RGB under alpha zero becomes zero. Fractional-alpha source RGB can lose
precision when premultiplied to eight bits. The original source digest is kept;
do not call GPU levels an exact lossless backup of the source PNG.

For each output pixel covering N original pixels:

```
A   = floor((sum(sourceAlpha) + floor(N/2)) / N)
RGB = floor((sum(sourceColour * sourceAlpha) + floor(255*N/2)) / (255*N))
```

Every level uses the original unrounded sums. The implementation aggregates
integer 2x2 sums, but does NOT average the already rounded previous level. Tests
compare it against an independent direct-area summation. Each RGBA channel is
0..255; RGB is never greater than alpha; all-zero alpha implies zero RGB.

This v1 calculation is in **stored sample space**. It is not sRGB-to-linear
filtering, colour management, high-dynamic-range processing or a claim of
physically correct light integration. Keeping that distinction explicit avoids
silently changing the existing native artwork's stored-sample convention.
No alpha-test coverage preservation is promised: distant thin features can
legitimately disappear after quantisation. Mip levels are filtered derivatives,
not separately rendered 16/32/64/128px native artwork.

## Ordering, keys and verification

Sprites sort by family, palette, complexity, full public digest. Bank/layer
placement follows that order. `spriteKey` is `bfalpha1-` plus SHA-256 of the
following exact object, pretty-printed with two-space indentation and a final
newline, in the shown property order:

```
profile, digestHex, family, palette, complexity, nativeSize, sourceRGBAsha256
```

Changing bank capacity does not change the key or sprite's mip bytes. Changing
native size, source pixels or profile does. The synthetic cross-language fixture
freezes Python/JavaScript key and upload layouts without claiming native output.

Each raw level has length and SHA-256, and every sprite separately records each
layer slice's SHA-256, source PNG path/hash and source RGBA hash. Verification
checks bounds, all file and slice hashes, PM pixel invariants, viewer inventory,
no unexpected files, and optional complete mip recomputation against source PNGs.
The exporter performs source recomputation before writing the success manifest.

Checksums and these manifests are unsigned. An attacker can replace both a
manifest and its payload; self-consistency is **not authentication**. Pin the
manifest checksum from an independent trusted channel when integrity matters.
The image itself never proves identity ownership or recovers arbitrary bytes.

## Browser usage and sampling

Load the trusted external `runtime.js` from the embedding application. It exposes
`globalThis.ByteFablesAlphaTextures` and does not import manifest-selected code:

```js
const api = globalThis.ByteFablesAlphaTextures;
const bundle = await api.loadBundle('/identities-alpha/', {
  manifestSha256: independentlyTrustedManifestHash,
  maxTextureBytes: 64 * 1024 * 1024,
});
const spriteIndex = api.lookup(bundle.manifest, {
  digestHex: fullPublicDigest, family: 'sigil', palette: 'neon', complexity: 4,
});
const display = new api.WebGLArray(canvas, bundle, {filter: 'linear-mipmap-linear'});
display.draw([{spriteIndex, x: 0, y: 0, width: 24, height: 24}], {
  background: [0, 0, 0, 0], // straight byte clear colour, explicitly premultiplied
});
display.dispose();
bundle.dispose();
```

The consumer owns its canvas/context exclusively. It uploads verified raw
`Uint8Array` bytes, not DOM images. This avoids browser PNG premultiplication or
unpremultiplication changing fractional-alpha samples during upload. Same-origin
HTTP(S), bounded streaming reads, no redirects/credentials, optional manifest
pinning and per-file/per-layer hashes are enforced before GPU upload. Payload
arrays remain private; caller-supplied bundle objects cannot bypass verification.

The context is `alpha:true, premultipliedAlpha:true, antialias:false`. Upload
premultiplication is disabled because input bytes are already premultiplied.
Blend factors for colour AND alpha are `(ONE, ONE_MINUS_SRC_ALPHA)`, with additive
blend equations. `opacity`, if provided, multiplies all four premultiplied channels.
Native top-left pixel origin is preserved with unflipped raw upload and shader UVs.

Two explicit filters: `nearest` (nearest pixel and nearest supplied mip) and
`linear-mipmap-linear` (bilinear pixels and trilinear mips). Instances can set a
finite `lod` in 0..lastLevel; otherwise choose
`clamp(log2(nativeSize / max(width,height)), 0, lastLevel)`. This is an explicit
2D LOD rule, not arbitrary perspective/anisotropic 3D sampling. Clamp-to-edge
prevents edge wrapping. Separate array layers prevent neighbour contamination.
Contiguous bank runs are batched with instanced quads without reordering sprites;
reordering by bank would incorrectly change overlapping transparent output.

`readPixels()` returns top-left **premultiplied** bytes, not Canvas2D's
unassociated RGBA. Call immediately after draw in the same task for reliable
readback. Context loss makes the consumer permanently fail closed; dispose it
and construct a new consumer after restoration. Dispose both GPU consumer and
CPU bundle when done. No hidden continuous render loop or telemetry exists.

The page shows 100/1,000/10,000 displayed instances and reports actual distinct
identity/style count separately. Repeated instances are not a unique-identity
recognition study. Reported timing is CPU submission, not GPU completion or FPS.

## Resource and file boundaries

Maximum 1,024 sprites, 128 MiB total raw levels, 256 layers/bank. The browser
uses a 64 MiB raw payload default and permits an explicit maximum of 128 MiB.
CPU arrays, fetch copies, GPU texture copies and driver allocations add overhead;
this is not a total-process-memory guarantee. Device texture-size and array-layer
limits are checked before allocating textures. Canvases are limited to 8,192 per
axis and 16,777,216 pixels; at most 10,000 instances per draw. Workloads exceeding
these bounds fail, including too-large combinations in the demo selectors.

The exporter requires explicit public confirmation, rejects symlink/reparse
paths, refuses existing output directories and ancestor/descendant overlap with
source, and writes manifest last. Failure leaves `failure.json`, never a success
marker. Paths and dimensions are generated and strictly checked. Windows is
supported by the Python/Node interfaces; no shell-specific generation command is
required. Reports should be written OUTSIDE the verified bundle inventory.

## Tests and acceptance gates

```sh
python -m unittest discover -s tests/python -p test_artwork_alpha_textures.py -v
node --test tests/artwork-alpha-textures.test.mjs
python tests/browser/artwork-alpha-textures-smoke.py \
  --bundle _work/artwork-alpha-textures --report _work/artwork-alpha-textures-browser.json
```

The browser gate requires the real HTTP loader/UI under `script-src 'self'`
without unsafe-eval/inline, WebGL2 and all complete mip levels on transparent,
black and white outputs. Each scene displays at least 1,000 instances and covers
all sprites. Texel-centre/solid-layer comparisons require exact PM bytes. Only
fractional trilinear and overlapping opacity scenes use a predeclared maximum
2/255 per-channel tolerance, recorded with actual and expected hashes; no
perceptual approximation replaces the exact checks. Synthetic red/blue layers
add an exact no-cross-layer-interpolation control. Missing browser/GPU support
fails this CI step; CPU/mocked-GL tests are not labelled GPU qualification.

Local execution scope and failures are recorded in the release validation report.
The preceding transparent-source native CI success does not establish success of
this new GPU mip path. KTX2/BasisU, Unity, linear-light profiles, alpha-test coverage,
additional browsers/devices and human accessibility studies remain subsequent work.

## Primary references

- Khronos WebGL2 specification (texture arrays, sized RGBA8 storage, instancing):
  https://registry.khronos.org/webgl/specs/latest/2.0/
- OpenGL ES texture storage reference:
  https://registry.khronos.org/OpenGL-Refpages/es3.0/html/glTexStorage3D.xhtml
- OpenGL ES blend factors reference:
  https://registry.khronos.org/OpenGL-Refpages/es3.0/html/glBlendFunc.xhtml

The explicit arithmetic and canonical package/key format above are ByteFables
contracts, not claims imposed by the Khronos format specifications.
