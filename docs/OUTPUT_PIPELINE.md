# ByteFables pluggable output and rendering architecture

**Document:** BF-PIPE-001 • working design proposal • 2026-10-25
**Scope:** all current and foreseeable output forms, with explicit contracts for any future adapter.
**Normative baseline:** [DESIGN.md](DESIGN.md), [SECURITY.md](../SECURITY.md). **Research inventory:** [OUTPUT_FORMAT_ATLAS.md](OUTPUT_FORMAT_ATLAS.md).

## 1. Conceptual model

A single flat `render(format)` function will lead to security and interoperability problems. Separate **transformation**, **protection**, **symbols**, **presentation**, **export**, and **readback**. Avoid funneling secrets through a generic public renderer.

```text
PUBLIC INPUT: typed bytes + canonical identity
  +-> identity digest (domain separated) -> representation seed
  |     +-> named alias / short check words
  |     +-> geometric/character/procedural avatar
  |     +-> spatial, animated, musical, tactile identity view
  +-> reversible public-only encoders -> integrity/framing -> symbol -> export
                   (QR, words, matrix, audio, files, print, NFC)

FUTURE PROTECTED INPUT: secret + wallet metadata (separate package/process)
  +-> offline policy and consent -> reviewed typed encoder
  +-> independent backup framing + integrity + checked loss model
  +-> qualified secret-specific carrier(s) -> independent re-import/restore
  X--/ never routes to default sprites, cached public identifiers, graph panels,
       media capture, third-party HTTP services, analytics, normal print APIs
```

A “pipeline” is a **typed, directed acyclic graph (DAG)**; every edge declares data sensitivity and whether it is exact bytes, encoded text, symbol matrix, raster pixels, vertex geometry or time series. Arbitrary untyped concatenations are not allowed. Export profile = named, immutable renderer chain and its configuration.

### 1.1 Distinct guarantees

- `reversible-exact`: re-import returns identical bytes **and** the claimed type/context if it was explicitly included.
- `reversible-raw`: re-import returns exact raw bytes only; external context may be needed.
- `public-identity`: deterministic alias/avatar with documented expected collision and no recovery guarantee.
- `machine-readable`: decoder accepts exported artifact under a stated optical/acoustic/device profile, not necessarily byte-equivalent across media transformations.
- `archival`: a reversible scheme plus long-term spec availability, backup metadata, redundant routes and demonstrated recovery testing; separate from storing the file itself.
- `authenticated`: only when an independent signature/MAC/AEAD validation establishes authenticity; CRC and error correction cannot.

A lossless container like PNG does NOT make a PNG *picture of a hash* a lossless hash codec.

## 2. Registry metadata and extension API

Use a capability registry with namespaced format IDs and semver-like immutable versioning. Three base capability protocols:

```ts
interface BinaryCodec {
  id: string; version: string; standard?: string;
  encode(payload: Uint8Array, context: Record<string, unknown>): EncodedObject;
  decode(encoded: EncodedObject): { bytes: Uint8Array; context?: unknown };
  vectors: string; // pinned, content-addressed test set
}
interface IdentityRenderer {
  id: string; version: string;
  render(publicDigest: Uint8Array, params: CanonicalRenderOptions): Scene;
}
interface Exporter {
  id: string; version: string;
  export(sceneOrSymbols: SceneOrSymbols, target: OutputProfile): Uint8Array;
  mediaType: string;
}
```

These contracts are **illustrative**, not source code that exists in the current API. Separate `ProtectedEncoder` from public `BinaryCodec` with an actual runtime boundary: secret handling cannot be obtained simply by setting `handlesSecrets: true` in a metadata object.

Required registry fields:

| Field group | Mandatory fields |
|---|---|
| Identity and provenance | ID, author, version, source URL/revision, licence, upstream status, format spec digest |
| Classification | category, reversible kind, what exactly decodes, dependency codecs, trusted input types, secret eligibility |
| Capacity | min/max input bytes, usable bits, expansion bounds, per-symbol maximum, ECC/framing overhead, memory/output limits |
| Determinism | domain separator, seed derivation, codebook/font/asset hash, stable colour model, renderer version, canonical option order |
| Output | MIME/extension, pixel/geometry/time/physical dimensions, colour space, media profiles, optional presentation overrides |
| Verification | matching decoder, official vectors, round-trip tests, scan/readback hardware profiles, error outcomes, known false-accept hazards |
| Runtime | Node/browser/worker/WASM/native support, CPU/GPU requirements, async jobs, offline status, native dependencies |
| Security | public-only vs gated secret, retention/logging policy, privacy notes, side-channel/clipboard/print risk, untrusted decoder caps |
| Accessibility | alt-text algorithm, tactile support, high contrast, reduced motion, locale rules, pronunciation/confusable score |
| Maturity | planned/experimental/compatible/qualified/deprecated; clear separation from current code `CATALOGUE` |

Maturity must be evidence-based. A general-purpose media exporter can be `compatible` while its *cryptographic backup combination* remains `experimental`.

### 2.1 Registry design examples

```json
{
  "id": "symbol/qr-model2",
  "version": "1.0.0",
  "category": "symbol",
  "reversible": "through-decoder",
  "input": "typed-octet-record",
  "outputMediaTypes": ["image/svg+xml", "image/png"],
  "secretEligibility": "gated-not-supported",
  "standards": ["ISO/IEC 18004:2024"],
  "vectorRef": "test-vectors/qr-model2-v1.json",
  "printProfiles": ["mono-high-contrast-v1"]
}
```

**Do not infer that an entry shown here is implemented.** A machine-readable roadmap catalogue may share the format schema but must never be registered as a runnable encoder until compiled implementation and conformance evidence exist.

## 3. Canonical data and framed records

The existing `ByteValue` and SHA-256 domain-separated identity remain stable. A new independently specified `BF-ARCHIVE-v1` envelope should be designed, *not* implemented as a premature wallet-safe format:

```text
magic / protocol version / application and object-type ID
network / object schema version / payload length / exact payload
integrity profile ID + digest or CRC
optional signed manifest reference / component grouping / chunking descriptor
optional ECC, share policy and associated immutable profile metadata
```

Choose deterministic CBOR under RFC 8949 and define CDDL per RFC 8610 for a machine-readable interpretation. Spell out sort/order, permitted tags, string normalization, unknown field behaviour, payload limits and decoding failures; verify canonical re-encoding to prevent ambiguous bytes. For archival, store a plain-text explanatory recovery manifest with the format, necessary decoder source/revision, test vector and verification procedure. No self-described envelope is sufficient if all available software becomes unavailable.

A checksum detects accidents. An SHA-256 digest can verify recovered data if the correct digest is independently known, but an attacker able to alter the record can recalculate an unkeyed digest. For authenticity, use an explicit signer/recipient trust model and reviewed cryptographic signature/MAC/AEAD. Do not conflate redundancy and threshold secrecy.

### 3.1 Deterministic derivation profiles

`identityDigest` = fixed v1 public digest from `DESIGN.md`; derive any aesthetic seed as `SHA-256(domain || canonical_style_id || canonical_style_options || identityDigest)` with length-prefixing and a version. The aesthetic output can include user overrides but those overrides live **outside** the canonical ID and are not used as an authentication key.

Rendering goals:

- `strict`: byte-identical SVG/model output in pinned runtime with fixed coordinate transforms/quantization/fonts; cross-runtime golden vectors.
- `semantic`: same visual features (palette/topology/silhouette) but renderer-dependent raster pixels; acceptable for rich GPU animation, versioned as such.
- `preview`: artistic variation or live interaction; explicitly not a stable verifying fingerprint.

For fixed style and options, include all font, palette, shader and model versions in the cache key. Never try to derive encryption keys from a visual seed/PRNG.

## 4. Engine decomposition

| Subsystem | Responsibilities | Deliverables |
|---|---|---|
| `types` | Public/secret labels, length limits, contextual object types | TypeScript discriminated values + runtimes checks |
| `codecs` | Byte/text/mnemonic conversion, strict decoding | Bytes + bytecount, checksum evidence |
| `grammar` | Compile and freeze slots/templates, proof of injectivity, bit accounting | Story codec with immutable pack digest |
| `framing` | Versioned deterministic CBOR + schema | Envelope + standalone manifest |
| `integrity` | CRC, SHA, signature adapters (later), proofs | Explicit separate classifications |
| `fec` | RS, BCH, erasure and fountain wrappers | Configured recovery budgets, no false repair claims |
| `symbols` | QR family, Data Matrix, Aztec, paper grids, audio framing | Abstract `ModuleMatrix` or `SymbolFrames` |
| `scene` | Canonical 2D vector graph, 3D scene, timeline, sound/tactile sequence | Renderer-independent scene representations |
| `render2d` | SVG/Canvas/Skia/rasterisation, QR quiet zone | SVG/PNG/WebP etc. |
| `render3d` | Mesh, voxel, material, laser relief/surface projection | GLB/STL/3MF/DXF |
| `render-time` | SVG/CSS/Lottie/video/audio/MIDI/haptics | Repeatable timeline exports |
| `layout` | Paper templates, booklet/plate planning, font embedding | PDF/A, SVG/print and CAD layouts |
| `exporters` | Target-file serialization, media-specific metadata | MIME, file bytes, manifest |
| `readback` | Optical, acoustic, file and physical tests; evidence | Decoded bytes / confidence & failure reason |
| `gallery` | Public demo, style selection, capability badges, export preview | React/Next.js app and CLI |
| `danceflow-adapter` | MCP/discovery, graph fallback, sprite registry | Namespaced provider methods |
| `secret-archive` | Reviewed offline companion behind independent gates | **NOT IMPLEMENTED** in public package |

### 4.1 Intermediate outputs

Use typed intermediate structures to avoid format explosion:

- `ModuleMatrix` (rows/cols, monochrome or indexed colour, quiet-zone/layout instruction, signed module scale, barcode format/version) -> SVG/PNG/PDF/DXF/stamp/3D relief.
- `VectorScene` (paths, fill/stroke, typography, metadata, fixed viewport) -> SVG/PNG/PDF/tiles/spritesheets.
- `SpatialScene` (mesh/voxel/instancing/materials) -> GLB, OBJ, STL, 3MF, WebGL render, engraved relief.
- `TemporalScene` (frames/events/timing/palettes) -> animated SVG, GIF/APNG/WebM/MP4, Lottie where compatible, MIDI/video/audio scenes.
- `AcousticPacketStream` (modem protocol, carriers, FEC, pacing) -> WAV/FLAC/speaker; independent receiver path.
- `TactileSequence` (Braille cell, haptic motor events, raised geometry) -> BRF/embossed page/device pattern.
- `LayoutDocument` (paper size, bleed/margins, page indexes, ink/material profile) -> PDF/PDF-A and print/plot commands.

Save exact binary record or recovery string *independently* of these transcodings, so users can compare them even if an exporter changes appearance.

## 5. Media conversion and output profile

Example **public** request:

```ts
const result = await bytefables.generate({
  value: ByteValue.public(idBytes, { namespace: 'danceflow', kind: 'node' }),
  view: { family: 'avatar', style: 'sigil-mandala', version: 1 },
  output: { mediaType: 'image/svg+xml', width: 128, height: 128,
            mode: 'high-contrast', alpha: true },
  verification: { includeFullCanonicalId: true }
});
```

This is a **future API proposal**, not functioning v0.1 code.

Families of output profiles:

- `node-16`, `node-32`, `avatar-128`, `avatar-512`, `identity-card`, `orb-webgl`, `atlas-256xN`, `unity-sprite`, `desktop-favicon`.
- `qr-display-public`, `qr-print-300dpi`, `datamatrix-dpm`, `aztec-mobile`, `microqr-label`, `pdf417-ticket`, `ur-animation-public`.
- `paper-a4-archive`, `paper-a5-wallet`, `metal-engrave-monochrome`, `laser-dxf`, `embossed-braille`, `label-dpm`.
- `scene-webgl`, `scene-glb`, `scene-usdz`, `scene-3mf`, `texture-ktx2`, `texture-atlas`.
- `tts-description`, `earcon`, `audio-modem-public`, `morse-led-public`, `nfc-public`, `tactile-id`.

Profiles carry explicit `quality`, `dpi`, `modulePitch`, `contrast`, `colourSpace`, `dpiUnits`, `quietZone`, `pageSize`, `printerOffset`, `codecVersion`, `fontDigest` and limits where relevant.

For binary-bearing symbols, **fidelity outranks style**. If the requested layout conflicts with symbol semantics, reject rather than silently reducing ECC, shrinking modules below scanner qualification, or cropping the barcode. For an ordinary avatar, style can vary as long as its identity provenance stays attached.

## 6. Delivery, transport and physical recovery

### 6.1 Universal artifact bundle

`*.bfbl.zip` (name provisional) can contain:

```text
manifest.json                  human-readable type and list of files
original-record.cbor          exact record for public exports (never default for secrets)
representations/label.txt     canonical lossless text
representations/qr.svg        QR export
representations/avatar.svg    public identity art (never secret-derived)
recovery/RECOVER.md           decoder version, import commands, bit lengths
verification/sha256.txt      independent expected digest
verification/vectors.json    known-good test vectors (non-secret fixtures)
```

For actual secret backups, a different protected bundle must be designed. Secret bytes must not be put in manifests, thumbnails, preview HTML, browser URLs, filenames, EXIF, analytics logs or ZIP unencrypted. ZIP itself offers neither strong encryption nor a security boundary.

### 6.2 Live transports

- Animated QRs: type, total parts/session or fountain parameters, fragment checksum, bounded number of bytes/frames, user resume and progress.
- Acoustic: audible/near-ultrasound modulation, explicit consent to mic/speaker; packet IDs, checksum, FEC, retries; never assume inaudible to other devices.
- NFC: NFC Forum NDEF on compatible tags, size check, typed record, read-only/lock setting if available; tag duplication/read exposure threat model. Public first.
- Web/API: exact bytes/CBOR or JSON envelope, REST/MCP only public by default; HTTP caching must include version and scope.
- Print/fabrication: provide dry-run paper/plate preview, true module size, calibration target and readback instructions. No secret-to-cloud print workflow.

## 7. Testing and conformance program

**Protocol tests**
- Round-trip exact bytes, length 0/1/16/20/24/28/32/33/48/64/65/78/96/128/256 and >1 KiB; leading zeros; invalid encodings, duplicate phrases, unknown codebooks, whitespace, adjacent bits.
- Cross-validate against at least one external reference implementation for every interoperable format; compare known upstream vectors, not one self-consistent encoder/decoder.
- Golden stability snapshots for every published algorithm/style/profile: independent input -> expected canonical data -> encoded text/matrix/scene -> artifact SHA or semantic manifest.

**Recovery tests**
- Scanner matrices: camera/lens/lighting, glare, barrel distortion, blur, perspective, mirrored/reversed code, dirty/corroded marking, scale, substrate and ink/laser profiles.
- Simulate 1/2/4/8/16 missing pages or optical frames, 5%/10%/20% random symbol errors and burst damage. Record *actual* failure rates; don't promise unconditional ECC success.
- Scanner-side decode after each PDF/PNG/SVG/DXF/metal/3MF rendering, not just source QR matrix equality; independent checksum then exact payload comparison.
- For story/text, round-trip with deliberate homophones, confusables, insertion, truncation, reordering, duplicated lines and punctuation corruption.
- Validate no silent “correction” to another plausible secret; ambiguous recovery yields explicit candidates and requires independent verification.

**Visual-recognition tests**
- Profile at 16, 24, 32, 64, 128 px and 4K; WCAG-minded contrast, greyscale, colour-vision simulations, reduced-motion fallbacks.
- Test perceptual confusion between near-looking avatars on random 100k-node gallery, accessibility reader output and textual fallback.
- Deliberately show participants *different full identifiers* with superficially similar avatars and measure incorrect confirmations. Human recognition is secondary to cryptographic proof.

**Resource/security tests**
- Cap memory, output size, recursion, polynomial work, grammar codebook size, frame count and decompression ratio; use worker isolation for untrusted image/QR/CBOR decoders.
- Browser: no network by default for local generation, CSP, permission prompts, no telemetry/clipboard, no secret persistence in service workers or cache storage.
- Native: test temporary files, print spool, crash dumps, traces, sandbox escapes; isolate optional multimedia parsers.
- Licence/SBOM audit for every third-party renderer and asset; do not redistribute fonts/wordlists without compatibility/licence review.

## 8. Quantitative engineering targets (initial hypotheses, not measured claims)

- Public placeholder avatars: lazy generation, bounded cache and object-batch API; target P95 within `<= 5 ms` for simple 5x5 SVG on a representative target machine, to be benchmarked and revised.
- Browser gallery: at least 1,000 simultaneous virtualised previews without unnecessary per-frame allocations; select texture atlases for dense WebGL graph views after profiling.
- SVG/PNG rendering: stable 16–1,024px outputs, no external font/network dependency for baseline styles.
- QR exported to print profile: camera readback from at least two independent decoders and physical prints under documented conditions.
- Wallet interoperability: *100% official vectors and independent restore evidence*, not an estimate. No secret support until security gate.

## 9. Extension acceptance protocol

Any new format proposal must provide:

1. Evidence link and clearly stated standard vs research vs invention status.
2. Purpose: full-value recovery, identity recognition, live transport, physical archive or display.
3. Exact input size constraints and expansion/capacity formula.
4. Type/context and version semantics; a lossless decoder or explicit statement that none exists.
5. Fidelity/error model, checksum/FEC policy and readable fallback.
6. Threat model (especially if it could carry secret data).
7. Reference/open-source implementation and licence compatibility.
8. Test fixtures incl. malformed/corrupted samples and non-secret demo artifacts.
9. Staged implementation owner, dependency and quantitative release gate.

Non-interoperable experiments never silently claim to be established standards. Future output types can be registered without revising the core cryptographic identity contract.
