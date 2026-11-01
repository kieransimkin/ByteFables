# KTX2 transport of isolated transparent mip arrays, v1

Status: experimental, PUBLIC, presentation-only. This is the next BF-W9 transport
increment, not another renderer, a compression milestone, a signed identity proof,
or qualification of every KTX2 consumer. The existing raw alpha-array format,
source artwork, seed assignments and lossless PNGs are unchanged.

## Scope and commands

Input is a successfully verified `bytefables.alpha-texture-array-bundle.v1`.
Output is `bytefables.ktx2-alpha-bundle.v1`, with one uncompressed `.ktx2` file per
bank. Every layer at every mip level is retained byte for byte. No mip calculation,
resizing, straight/premultiplied conversion, colour transfer or GPU compression
occurs. The original alpha bundle's quantisation still exists; this transport is
lossless relative to those already-derived bytes, NOT relative to the original
straight-alpha PNGs.

```sh
python scripts/export-artwork-ktx2.py --confirm-public export \
  --bundle _work/artwork-alpha-textures --output _work/artwork-ktx2
python scripts/export-artwork-ktx2.py --confirm-public verify \
  --bundle _work/artwork-ktx2 --source-bundle _work/artwork-alpha-textures
python -m http.server 8765 --bind 127.0.0.1 --directory _work/artwork-ktx2
```

Open `http://127.0.0.1:8765/` in a WebGL2 browser. Rendering new source artwork is
not necessary to package an existing verified array bundle. Verification without
`--source-bundle` checks internal consistency and all original hashes; supplying
that argument additionally verifies the original package and compares raw bytes.
Checksums and unsigned manifests do not authenticate an identity or its owner.

## Explicit narrow KTX2 profile

Profile: `bytefables.ktx2-rgba8-array.v1`.

- KTX 2 identifier, little-endian header and level table.
- `VK_FORMAT_R8G8B8A8_UNORM` (37), `typeSize=1`, square 16/32/64/128px.
- `pixelDepth=0`, `faceCount=1`, `layerCount=1..256` (even a one-layer bank is
  explicitly an array). Every mip is present through 1x1.
- `supercompressionScheme=0`; no global supercompression data. No BasisLZ,
  UASTC, block-compressed formats, cube maps, Zstandard or zlib in this profile.
- Largest mip is index 0, but image payloads occur physically smallest-first.
  Images within each level are layer-major and tightly packed top-left RGBA8.
- DFD: Khronos basic descriptor version 2, RGBSDA model, 8-bit R/G/B/A samples,
  unspecified colour primaries, identity transfer, `ALPHA_PREMULTIPLIED=1`.
- Metadata: NUL-terminated `KTXorientation=rd`, versioned `KTXwriter`, and
  `org.bytefables.profile`; keys are sorted, with zero alignment padding.

The DFD identity transfer means consumers must use these as raw UNORM samples,
without an additional sRGB decode. The preceding mip profile intentionally works
in stored sample values. This is NOT a claim of scene-linear light, colour-managed
physically accurate filtering, or an automatic sRGB asset conversion. A future
colour-managed profile needs separate versioned generation and comparison rules.

Python and JavaScript decoders intentionally accept only this canonical profile.
Other valid KTX2 files are rejected, including other metadata layouts. This makes
all offsets, byte counts, descriptors and ordering checkable before payload
allocation or slicing. A canonical encoding is deterministic for fixed input
bytes and bank layout. The profile is not a general-purpose KTX2 reader.

## Manifest and provenance

`manifest.json` contains the transport schema/profile, public/presentation labels,
the original-manifest file checksum, per-bank geometry/file checksums, and an
inventory of the static viewer files. `source-manifest.json` is an exact copy of
the original array manifest, including original sprite keys, digests, source PNG
references, per-mip and per-layer hashes. Its old raw-file/viewer references are
provenance records, NOT additional files fetched by this transport.

The verifier parses every bank, checks every complete mip and individual layer
against those original hashes, and verifies the complete package file inventory.
With the source bundle it also compares each decoded level to the original raw
file. It rejects unknown files, missing files, failed bundles, changed viewer
files, unsafe paths, symbolic links/reparse points and output overwrite. A success
manifest is written last, after saved-file checks; partial failures get
`failure.json`. Consumers must not modify a package concurrently with validation.

The identity keys do not change because packaging changes. Repacking a source
bundle with a different bank size still retains the source keys, but the resulting
container files and transport checksums will naturally change.

## Browser integration and ownership

Load trusted `alpha-runtime.js`, then `ktx2-runtime.js` as external scripts. The
new `ByteFablesKtx2Textures` API supplies `loadBundle`, `decode`, `validateManifest`
and `lengthFor`, and shares `WebGLArray`, `lookup`, `makeGrid` and `runs` with the
existing alpha runtime. No shader, blending rule or second renderer is added.

```js
const api = globalThis.ByteFablesKtx2Textures;
const bundle = await api.loadBundle('/identities/ktx2/', {
  manifestSha256: independentlyTrustedTransportManifestHash,
  maxTextureBytes: 64 * 1024 * 1024,
});
const renderer = new api.WebGLArray(canvas, bundle, {filter: 'linear-mipmap-linear'});
const i = api.lookup(bundle.manifest, {digestHex: fullDigest, family: 'sigil'});
renderer.draw([{spriteIndex: i, x: 0, y: 0, width: 32, height: 32}]);
renderer.dispose();
bundle.dispose();
```

`loadBundle`'s `manifestSha256` option pins the TRANSPORT manifest. The returned
object is an ordinary accepted alpha-runtime bundle: `bundle.manifest` and
`bundle.manifestSha256` describe the ORIGINAL alpha manifest. Do not confuse these
two checksums when persisting configuration. The transport checks its own pin
before processing banks; it then checks the exact original manifest's hash.

The shared runtime adds `fromLevels(manifestBytes, bankLevelArrays, options)` for
transport adapters. It snapshots all caller-owned arrays before its first async
suspension, validates the original identity and all mip/layer hashes, checks
premultiplied samples, freezes metadata, and stores payloads privately. Callers
cannot bypass integrity checks by constructing an arbitrary renderer input.

Only same-origin HTTP(S) directories are allowed. Credentials, redirects, query
parameters and fragments are rejected. URLs for payload files must match canonical
bank paths. Reads are bounded even when a server omits Content-Length. No decoder
WASM, CDN, dynamic imports or CSP exceptions are required. The CSP retains
`script-src 'self'`; controlling the hosting directory is still a trust boundary.

The original bounds remain: at most 1,024 sprites and 128 MiB raw payload, with a
64 MiB default consumer budget. A single bank is limited to 32 MiB encoded bytes.
The count of banks, images, levels and all file sizes is validated. The texture
budget measures raw bytes, not peak process/GPU memory. Fetch buffers, independent
snapshots and GPU copies add overhead (approximately multiple payload copies).
This version downloads complete banks; HTTP range streaming is not implemented.

## Independent qualification

```sh
python scripts/qualify-artwork-ktx2.py --bundle _work/artwork-ktx2 \
  --ktx /path/to/ktx --report _work/artwork-ktx2-khronos.json
python tests/browser/artwork-ktx2-smoke.py --bundle _work/artwork-ktx2 \
  --source-bundle _work/artwork-alpha-textures \
  --report _work/artwork-ktx2-browser.json
```

The first command requires the actual Khronos executable. It runs `ktx validate`,
then `ktx extract --all --raw` on every bank. Every independently extracted image
must match the ORIGINAL per-layer mip checksum. Tool version, executable hash,
validation output and image counts are recorded. There is no mocked fallback or
successful skip. Warnings from the independent validator are preserved in the
report rather than hidden; nonzero exits fail qualification.

CI downloads Khronos KTX-Software 4.4.2 for Linux x86_64 and checks its published
SHA-256 (`ca635ed489d8bf54fac8d7687056c651193de0740830a7738cc034adc63e3027`)
before installing it. This is an explicit test baseline, not an assertion that
4.4.2 is the latest release. No Khronos binaries are bundled with ByteFables.

The second command loads the real HTTP preview under its unchanged CSP, renders
all levels on transparent, black and white backgrounds, and compares full GPU
readbacks against independent CPU sampling of the ORIGINAL raw-array package.
Texel-centre tests are exact. Only fractional interpolation/overlap tests retain
the preceding profile's explicit maximum two-channel-unit tolerance. Existing
raw-array GPU qualification still runs, including synthetic layer isolation.
Missing HTTP/GPU support fails this acceptance script.

## Tests, limitations and next milestone

```sh
python -m unittest discover -s tests/python -p test_artwork_ktx2.py -v
node --test tests/artwork-ktx2.test.mjs
```

Tests cover headers, DFD fields, metadata, all truncations of a small file,
64-bit overflows, wrong level ordering, mutations and rehashed substitutions,
source binding, deterministic byte transport, URI restrictions, budgets,
caller-buffer mutation, no overwrite and Python/JavaScript shared vectors.
Mocked HTTP and GPU-call contracts are not real-browser qualification.

Record actual execution results in the accompanying validation report. Local
unit success does not establish Khronos acceptance, Unity interoperability,
real-device performance or a fresh native renderer run. The next milestone is
Unity Texture2DArray consumption/qualification of this frozen uncompressed profile.
Basis compression, streaming, colour-managed generation, additional devices and
human recognition/accessibility studies remain separate work.

## Primary references used

- KTX 2.0 specification: https://registry.khronos.org/KTX/specs/2.0/ktxspec.v2.html
  (file structure, level order, DFD alpha flag, orientation and metadata).
- Khronos DFD construction: https://github.com/KhronosGroup/KTX-Software/blob/v4.4.2/external/dfdutils/createdfd.c
- Independent validation command: https://github.com/KhronosGroup/KTX-Software/blob/v4.4.2/tools/ktx/command_validate.cpp
- Independent raw extraction command: https://github.com/KhronosGroup/KTX-Software/blob/v4.4.2/tools/ktx/command_extract.cpp
- Pinned validator release: https://github.com/KhronosGroup/KTX-Software/releases/tag/v4.4.2
