# ByteFables staged implementation plan

**Date:** 2026-10-25. This is a technical roadmap, not a claim that phases
have shipped. Plan items reference [DESIGN.md](DESIGN.md),
[SECURITY.md](../SECURITY.md), the
[format atlas](OUTPUT_FORMAT_ATLAS.md),
[rendering pipeline](OUTPUT_PIPELINE.md), and
[research survey](RESEARCH_SURVEY_2026-10.md).

## Stage map and dependency gates

| Stage | Product milestone | Prerequisite | Explicit acceptance gate |
|---|---|---|---|
| **0** | Bootstrap & architecture | Empty repository | Builds from clean checkout; typed boundaries; documented plan; CI/tests |
| **1** | Foundational public identities | Stage 0 | Namespace-separated SHA-256, stable fingerprints, one deterministic SVG |
| **2** | General grammar encoder | Stages 0–1 | Compiler rejects ambiguity; several full-size packs; binary round trips |
| **3** | Standard reversible codecs | Stage 0 | BIP-39, Bytewords/UR, Bech32 etc. matched against upstream vectors |
| **4** | Visual identity gallery | Stage 1 | Versioned renderers, stable sprites, theme controls, accessibility checks |
| **5** | Archival transport | Stage 3 | QR/SeedQR/UR, ECC, printable templates, damaged-media readback |
| **6** | DanceFlow integration | Stages 1, 2, 4 | MCP discovery, graph-node fallback sprites, public-type safeguards |
| **7** | Secret-backup qualification | Stages 3, 5 | Offline secure workflow, independent threat/security review, recovery evidence |
| **8** | Multi-runtime & ecosystem release | Stages 1–7 as needed | Golden vectors across runtimes; audited package/release flow |

Stages 2–4 may proceed in parallel after Stage 1. Stage 7 is an independent
safety gate; a successful encoder does not implicitly satisfy it. The
**comprehensive output programme** appended below extends this original stage
map into parallel workstreams BF-W1 through BF-W14 with explicit dependencies,
50 ranked engineering issues, and rendering/readback acceptance matrices.

## Stage 0 — repository foundation **[included in initial patch]**

**Work:**
- TypeScript ESM project with pinned TypeScript and lockfile; `npm ci` CI.
- Public/secret typed byte wrapper (defensive-copy semantics, validation),
  capability/maturity catalogue, strict hex/Base32 and binary utilities.
- Architecture, reference matrix, threat model, roadmap, tests, no-runtime-dep
  baseline and example.

**Exit:** clean build/test under Node >=20, no secretly downloaded models,
no runtime deps, no accidental public wallet-archive claims. Basic spec and
next-stage issues identified.

**Demonstrated here:** actual local TS build + tests; CI workflow provided but
remote GitHub Actions run cannot exist until code is committed/pushed.

## Stage 1 — deterministic public identity **[minimal version included]**

**Work:**
- Domain-separated, length-delimited SHA-256 identity for canonical public
  namespace, type and bytes.
- 96-bit default shortened verification fingerprint; configurable through
  full 256-bit digest; 5x5 mirrored SVG icon version 1.
- Golden vectors, multiple namespaces/kinds and public/secret rejection tests.

**Next:** full-fingerprint identity card, clear context display, cache/etag
strategy, vector icon fidelity tests, Node vs browser verification.

**Exit:** identical typed input yields identical binary digest and SVG; any
semantic context difference alters the digest; public/secret separation has
explicit runtime and type tests; UX doesn't rely on icon uniqueness.

## Stage 2 — reversible grammar engine **[implemented experimentally, review gates remain]**

**Included prototype:** grammar compiler, two equal-capacity sentence templates,
13 bits per sentence, magic/version/size/CRC32 prototype format, exhaustive
8,192-codeword bijection test, corruption/truncation/size tests. It is not an
interoperable backup format.

**Completed in the Stage 2 patch:** six 256-entry compound-lexeme theme packs,
  four prefix-coded 33–35-bit templates per pack, three explicitly marked
  24/32/40-bit scheduled templates per pack, versioned raw-byte framing,
  SHA-256-128 unkeyed integrity, strict canonical round trips, enumerative
  coding of unequal radices, conditional dictionaries and explicit verb
  agreement, bounded scheduling, warning-only lexical audit, immutable pack
  digest vectors, CLI and FrameRudiments text preview handoff.
  The legacy 13-bit wire format remains unchanged. See
  [story-v2.md](specs/story-v2.md).

**Next research/qualification work:**
- Expand lexical categories (adverb, adjective, noun, animal, verb, place,
  action, object, conjunction, temporal and technical categories).
- Curate multiple immutable **33-bit** themed templates and verify capacity;
  separate language quality from injectivity.
- Introduce dependent dictionary relationships with compile-time cardinality
  checks, agreement/inflection tables, stable punctuation and normalized parse.
- Add prefix-free template decoding where templates vary in length, entropy
  coding for non-power-of-two vocabularies, finite-state grammar parser.
- Use an explicit framed packet encoder and bounded dynamic-programming
  scheduler for variable sentence structures, optimising word count, spoken
  complexity and visual layout.
- Provide experimental themes: nature, music, technology, fantasy, science,
  gentle humour and traditional mnemonic stories.
- Add exhaustive or formal proofs of decode uniqueness, homophone/confusable
  audits, mutation fuzzing, cross-runtime golden vectors.

**Experimental exit achieved:** random byte arrays (including 128–512-bit fixtures) round-trip with
strict bit-accounting and no ambiguous parse across every allowed template.
Advertised sentence capacities match independent measurements.

**Follow-on:** Formosa-compatible theme adapter only after official test-vector
and wallet compatibility checks, not merely because both use 33-bit blocks.

**Remaining qualification:** independent linguistic/homophone reviews,
spoken transcription trials, formal proof documents beyond compiler invariants,
cross-language decoder vectors and long-lived archival/wallet suitability.
These are not implied by a passing Node test suite.

## Stage 3 — interoperable standard encodings **[public codec subset implemented; wallet qualification pending]**

**Implemented in this increment:** Base45, Base64/Base64url, checked
Crockford Base32, checked network-explicit Base58, Bech32/Bech32m with
SegWit validation, Multibase, Bytewords standard/URI/minimal, official BIP-39
public fixture entropy mapping, and reserved single-part UR `bytes` tests.
These have vectors and strict decoders but are **not** production wallet
recovery or private-key backup features. See
[the Stage 3 codec specification](specs/standard-codecs-v1.md).
The overall Stage 3 gate is still **open** for SLIP-39, typed/multipart UR,
wallet recovery tests, seed derivation/metadata and independent reviews.

**Priority A:**
1. RFC 4648 (foundation); broaden to checked Crockford Base32/Base45 where
   relevant and keep explicit alphabet/format IDs.
2. BIP-39 entropy <-> mnemonic (official wordlist + vectors; NFKD; checksum;
   optional seed derivation as a separately identified operation).
3. Blockchain Commons Bytewords normal/minimal, CRC and UR v2 type registry.

**Priority B:**
4. Bech32/Bech32m with HRP-aware strict address/payload semantics.
5. SLIP-39 (group and member shares) using reviewed reference implementation
   rather than fresh, unreviewed Shamir cryptography.
6. Formosa, codex32 and legacy RFC 1751 as distinctly labelled formats.

**Exit:** every adapter passes official vectors, rejects incorrect version,
unsupported type, inconsistent length and checksum failures; comparisons with
independent implementations are recorded in docs/test artifacts.

## Stage 4 — visual identity catalogue

**Work:**
- Stable renderer interface (`styleId`, `styleVersion`, `digest`, canonical
  options, output MIME, render bounds, deterministic cache key).
- Geometric variants (Jdenticon/Blockies-like, rotations, symmetry), LifeHash
  interoperability, character/creature sprite synthesis, heraldry, sigils,
  procedural landscapes, constellations and abstract patterns.
- Theme registry and customisable palettes/shapes with accessibility metrics.
- Gallery: one node across 20+ styles and a large-node visual collision study.
- `identity-card` output with icon, type glyph, full digest, safe short name,
  and public-only machine-readable identifier.

**Exit:** for a fixed public value and options, exports remain byte-identical
within pinned renderers; favicon and graph-node styles remain legible at 16px;
contrast/colour-vision tests and deterministic SSR/browser tests pass.

## Stage 5 — resilient archival transport

**Work:**
- QR Code with selectable ECC, Data Matrix/Aztec/PDF417 as separate adapters;
  enforce scanner-compatible quiet zones and capacity limits.
- SeedQR with actual wallet-compatible vector tests, not QR encoding alone.
- UR v2 CBOR typed fragments and bounded fountain reassembly; interrupted
  session resume and fragment de-duplication.
- Printable cards in vector formats, large-tile formats, laser/stamping layouts,
  paper and metal workflows. Human transcription fallback.
- Explicit checksums; appropriate Reed–Solomon/BCH error correction, erasures,
  and loss-model simulations. Prefer reviewed implementations.

**Exit:** optical readback from damaged/blurred/partially obscured real-world
samples within documented conditions; failure is detectable with no silent
incorrect payload; all recovered bytes + type metadata validated.

## Stage 6 — DanceFlow integration

**Work:**
- Integrate with DanceFlow's component discovery, MCP capability references and
  release preflight. ByteFables remains its **own** source repository.
- API for graph node default avatars, orb thumbnails, remembered colour/theme
  family, accessible placeholders and full node identity on inspection.
- Browser worker/WASM/raster cache only if perf evidence warrants it.
- Optional adapter for thought graphs, project workspaces and other nodes with
  separate network identifier namespaces. Never derive visual identities from
  private keys or untrusted arbitrary serialized objects.
- Public identity card endpoint, CLI (public values only), Next.js interactive
  gallery and export demos.

**Exit:** stable fallbacks for all node kinds, cache invalidation across
renderer versions, no new code paths logging secret data, and documented
integration tests on the intended host.

## Stage 7 — secret-backup safety qualification

**This is a gate, not an automatic feature release.**

**Work:**
- Threat-model key generation/import, in-memory lifecycle, CLI/UI channels,
  print spool, clipboard, browser storage, telemetry/network, and backup media.
- Design explicit opt-in offline workflow with irrecoverable-loss warnings.
- Use audited dependencies for BIP-39/SLIP-39/UR, review entropy/KDF rules and
  passphrase normalization; test actual wallet recoveries, including HD account
  metadata and multisig descriptors.
- Independent security review and fuzzing; no silent text correction.
- Document physical-media wear, multiple geographically separated copies,
  legal/regulatory and theft risks; don't invent a durability guarantee.

**Exit:** release checklist signed off on evidence of interoperability, key
protection and correct recovery; future secret feature must be separately
versioned and feature-gated.

## Stage 8 — cross-platform release and developer operations

**Work:**
- Publish JS/TS package when stability and API version review are complete;
  Python shim or native implementation only against shared golden vectors.
- CLI, MCP server/adapter, browser gallery, WASM renderer modules where useful.
- Signed build provenance, SBOM/dependency review, release jobs and changelog.
- Report collision statistics, theme recognisability and layout accessibility.

**Exit:** pinned releases, documented upgrade/migration path, reproduce builds,
plus independent recovery-tool readback for each advertised archival format.

## Cross-cutting engineering backlog

### Functional tests

- Property tests for all round-trip codecs, lengths 0–4096, arbitrary binary,
  all-zero/all-one, truncation, leading zeros and explicit padding.
- Exhaustive injectivity for small grammar packs and compiler negative tests.
- Hash vectors for public identity domains and aliases, including namespace
  collision defenses; future snapshot tests across Node/browser/Python.
- Immutable dictionary/grammar snapshots, hash-pinned reference packs.

### Adversarial tests

- Invalid lengths, output overflows, UTF-8 abnormalities, confusable glyphs,
  homophones, malicious grammars, deeply nested/large envelopes, invalid CRC.
- QR damage, packet deletion/reordering/duplication, erroneous share selection.
- Pen-testing of secret flows (later), no unexpected logs/cache/export.

### Product/UX tests

- Compare users' ability to recognise correct vs subtly altered visual hashes.
- Accessibility: screen reader names, colour-blind palettes, reduced motion.
- Print and engraving recovery measured on real media.
- Internationalisation must not change decoder semantics or unversioned codebooks.

## Suggested issue breakdown for first iteration

1. `core: canonical typed public value and SHA-256 identity vectors` — included.
2. `codecs: RFC4648 hex/base32 strict implementations` — included.
3. `grammar: compile 13-bit experimental templates and prove bijection` — included.
4. `art: deterministic mirrored SVG public identicon` — included.
5. `ci: lockfile-based Node 20/22 checks` — included, pending remote run.
6. `spec: define versioned archival envelope and CDDL` — next.
7. `grammar: 33-bit standard-compatible and varied templates` — next.
8. `catalogue: durable format and renderer registry` — next.
9. `interop: BIP-39 official vectors and typed import/export` — subsequent.
10. `graphics: node avatar gallery and metadata card` — subsequent.

## Status accounting

The original ByteFables bootstrap has since been committed, per the project
maintainer, and its `main` file tree was inspected on GitHub on 2026-10-25.
The 13-bit grammar remains explicitly experimental. Do not infer current CI,
release, package registry or secret-backup readiness from a source commit.
This extension only adds research/design/roadmap documents, not functioning
new output encoders or renderers.

---

# Comprehensive rendering and output programme (October 2026 extension)

**Intent:** broaden the original Stages 0–8 without changing any committed
prototype's wire format or treating a candidate as shipped. Read the
[research survey](RESEARCH_SURVEY_2026-10.md),
[output-format atlas](OUTPUT_FORMAT_ATLAS.md) and
[output pipeline](OUTPUT_PIPELINE.md) first. These documents enumerate the
candidate universe; this section assigns dependencies and release gates.

## Wave A implementation — core transport spine and FrameRudiments boundary

The first implementation batch consists of deterministic public CBOR records,
strict framing and a CDDL contract, immutable capability manifest and selection
API, public-only reference CLI, typed module/scene IR, and an optional native
FrameRudiments renderer plugin. **FrameRudiments is now the sole production
visual host** for subsequent generators and effects. ByteFables provides
validated native layer fragments; no separate animation, shader, frame loop,
image-processing or video encoder is to be built in ByteFables. The original
three-word and pixel-avatar output APIs remain stable compatibility adapters.

Native adapter generators include a public deterministic pixel identity,
pixel-perfect binary `ModuleMatrix`, and a bounded vector scene. They attach to
FrameRudiments' native per-element/post-frame `post_effects` and `effect_graph`.
They do not implement their own postprocessing or bypass the native project
asset/clock provenance. See [bridge](specs/frame-bridge-v1.md).

**Wave A acceptance gates:** byte-level CBOR fixtures, forbidden/ambiguous input
rejection, canonical public context, manifest snapshots, planner/dispatcher
negative tests, TypeScript and Python fragment vectors, plugin factory tests,
strict secret exclusion, and native contract documentation. Integration against
an installed FrameRudiments project plus real FFmpeg/effect-readback evidence is
a *separate native host acceptance gate*, not a claim conferred by unit tests.
Before announcing Wave B, validate the upstream FrameRudiments version and
publish an actual multi-layer preview and output receipt.

## Programme model and definition of done

Every new format follows:

```text
canonical public value (or future gated secret input)
    -> lossless codec or non-reversible identity derivation
    -> optional framing/checksum/ECC/secret-sharing [distinct]
    -> symbol / scene intermediate representation
    -> exporter file bytes / device transport
    -> independent decode or visual verification
    -> immutable versioned fixture + capability registry metadata
```

**Never conflate:** the ability of a PNG to preserve image pixels with the
ability of an identicon to preserve its source bytes; QR symbol ECC with
cryptographic authentication; multi-share secret recovery with repairing a
damaged plate; an NFC chip's readability with physical permanence; a PDF/A
archive's compliance with actual restorability decades later.

A candidate advances from `researched -> prototype -> implementation-tested ->
interop-qualified -> security-qualified (secrets only)` only after these gates:

1. **Specification:** pinned normative reference / originating research, status,
   compatible format identifiers, usable licence and independent implementation.
2. **Binary fidelity:** typed byte length, framing, canonicalisation, padding,
   deterministic decoding or explicit `identity-only`, adversarial parser limits.
3. **Failure model:** truncation, substitution, erasure, burst errors, duplicate
   fragments, interference, hardware failure and expected decoder behaviour.
4. **Rendering fidelity:** exported source plus independent readback from **the
   exported artifact**, not just the original in-memory symbol matrix.
5. **Security:** public/secret classification, sink allowlist, no unauthorised
   bytes in previews or metadata; secret releases pass original Stage 7.
6. **Product:** metadata in capability registry, CLI/gallery UX, docs, golden
   vectors, licensing and accessibility; traceable issue/maintainer ownership.

A display-only style can skip the recovery decoder but must still preserve
*stable seed/domain/style provenance*, list its effective visual distinctiveness
limitations and retain the canonical full public identifier.

## Ordered delivery waves

| Wave | Dependencies | User-visible deliverable | Evidence gate |
|---|---|---|---|
| **A. Core transport spine** | Existing Stage 0, Stage 1 | Immutable manifest + registry, canonical CBOR envelopes, typed `ModuleMatrix`/`VectorScene`, reference CLI and FrameRudiments generator bridge | Negative vectors, compatibility snapshots, no secret API |
| **B. Public identity and graphics** | A | 12+ stable avatar styles, SVG/PNG/WebP/ICO, cards, atlas and Next.js gallery | 16px/32px recognition, renderer consistency, 1k-node load |
| **C. Common recovery carriers** | A | Hex/Base32/Base45/Bytewords, QR + PDF/SVG/PNG public recovery sheets | Independent scanners/decoders, offline public demonstration |
| **D. Grammar and wallet compatibility** | A | 33-bit and variable story codecs; BIP-39/SeedQR/UR read/write of **public fixtures only** | Proof of unique parse, official vectors, no real key workflows |
| **E. Industrial and animated optics** | C | Data Matrix, Aztec, PDF417, Micro/rMQR, multi-frame UR and BBQr, printed label profiles | Real scanner/device tests for named formats |
| **F. Audio, NFC and accessibility** | A + selected C | TTS/SSML, BRF, alt text, MIDI/earcons, LED/haptics, sound modem, NFC NDEF | Independent device readback; microphone/camera opt-in |
| **G. Procedural 3D and game assets** | B | GLB/3MF reliefs, instanced WebGL scenes, Unity atlases/KTX2, shader identities | Cross-runtime determinism and performance evidence |
| **H. Archival resilience laboratory** | C + E | ECC benchmark, damaged-medium corpus, steel/laser/plotter, OPTAR and specialist codes research | Measured, documented restore success/failure distributions |
| **I. Independent secret archive** | C + D + H + original Stage 7 | Separately distributed reviewed offline recovery tool | Independent cryptography/security review and real wallet recovery |

Multiple waves can proceed in parallel after A. Wave I **does not ship** just
because C, D and H have code; Stage 7 review remains a hard stop. Scope changes
that affect a published binary format require a new version and migration note.

## Workstream specifications, milestones and acceptance gates

### BF-W1: Input, metadata, capacity and renderer registry (Wave A)

- Formal typed input: namespace, kind, public/secret sensitivity, algorithm,
  data length, network, endian/version and original record context.
- `ByteFables` canonical CBOR schema specified in CDDL; length-prefix and
  context domain separation; deterministic CBOR subset, no float ambiguity.
- Registry manifest carries unique `formatId`, semver/immutable `version`,
  standards status, reversible/identity-only flag, entropy/capacity, sensitivity
  policy, estimated density and expansion, supported MIME and carrier, decoder,
  resource limits, ECC characteristics, licences and reference vectors.
- Capability introspection, public-only format planning API, input-size router,
  no runtime invocation of `planned` entries.
- Plugin input/output intermediate types as defined in OUTPUT_PIPELINE.md.

**Exit:** registry can express every atlas class without adding `if/else` to
crypto core; all sample manifests validate against schemas and backward
compatibility tests; a consumer can distinguish `identity-only` from `lossless`.

### BF-W2: Canonical text, mnemonic, symbol and spoken codecs (Waves A, C, D, F)

- Strict Base64/url, Base45, Crockford Base32, Base58Check, Bech32/m,
  decimal/octal/binary, multibase, JSON/CBOR/ASCII-armor and Bytewords normal,
  URI and minimal representations.
- Full words/provenance/checksum for BIP-39 and Formosa as separate read/write
  adapters; SLIP-39 and codex32 only after secure reference implementations and
  official vectors. RFC1751, RFC2289 and network-specific mnemonic formats
  isolated in compatibility adapters.
- Structured output: numbered chunks, lines with CRC/check values, fixed-
  width handwriting grids, word prefix aids, phonetic alphabet, Braille byte
  units, Morse text, pronunciation/SSML and VTT/SRT captions.
- Freeze dictionaries with digests; never substitute a new wordlist in-place.

**Exit:** exact round trip with independent published vectors; useful spoken or
printed fallback for each enabled recovery format; no implicit BIP39 wallet
conversion or use of passphrases without gated wallet-specific semantics.

### BF-W3: Grammar compiler and linguistic laboratory (Wave D)

- Design 33-bit reference pack, independent sentence patterns (adverb/adjective/
  noun, action, dialogue, conditional, time, music, science, place, mythology).
- Prefix-decodable structural markers; finite-state grammar with agreement,
  number, tense and inflection; context-dependent lists of guaranteed capacity.
- Formally account for selector bits, filler words, checksum, packet length and
  padding; use enumerative coding for non-power-of-two vocabularies only when
  a proof of inverse is available.
- Variable-size grammar scheduler optimises readability/spoken duration,
  alliteration, syllable complexity and output width under exact bit capacity.
- Human study of homophones, proper nouns, script confusables and visual
  similarity; deterministic render and language tests at 128/160/192/224/256,
  512 and large arbitrary payload sizes.

**Exit:** no two legal bitstrings in a published codebook decode to the same
story; fixtures reproducible across versions; measured copy/recall performance.

### BF-W4: 2D symbol interoperability (Waves C and E)

- **P0:** QR Model 2 encoder/independent decoder tests, binary vs Base45 mode,
  four ECC grades, capacity planner, module-size and quiet-zone enforcement;
  SVG vector master with PNG/PDF/print/laser exports.
- **P1:** Data Matrix ECC200 and Aztec; PDF417; readback scanner plugin and
  physical print templates; Bytewords, typed UR and SeedQR interoperability.
- **P2:** Micro QR, rMQR, Han Xin, MaxiCode, Code128/39/93, DotCode and other
  industrial symbols, with scanner support gated per format.
- **Lab:** JAB multi-colour, Ultracode (draft status must be checked),
  Xerox DataGlyphs-inspired marks, HCCB, OPTAR dot archives, Bokode, infrared,
  fiducial-in-QR hybrids and geometry-constrained decorative codes.

**Exit:** per-format reference fixtures, 2 independent decoders where practical,
real-world readback and a clear unsupported-reader warning when applicable;
art overlays cannot invalidate quiet zones or checksum margins.

### BF-W5: Temporal and segmented optical formats (Wave E)

- Native multi-part UR v2 fountain encoder/reassembler, typed CBOR, strict
  fragment bounds, duplicate/reorder/drop tests and progress reporting.
- BBQr and independently defined sequential/structured append QR adapter,
  static contact sheet, GIF/APNG/animated SVG/MP4/WebM or display-led scanner
  stream **without treating compressed video frames as exact symbols**.
- Frame timing, exposure/motion blur, safe maximum payload and recovery after
  interrupted capture. Render a human fallback ID for every session.

**Exit:** independent reconstructing decoder from the **rendered animation**;
complete payload verified against full digest after loss/reorder within
published test conditions; deterministic timeline and bounded memory.

### BF-W6: Public avatar and graphic family catalogue (Waves B and G)

- Preserve current 5x5 pixel v1; add grid/symmetry, polygons, Voronoi,
  heraldry, knotwork, sigils, runes, framed crests, pixel art, mosaics, flags,
  type/colour motifs, OpenSSH-style random art and pin-compatible LifeHash.
- Sprite/character families: animals, robots, fantasy characters, masks,
  accessories and theme layers with frozen seed assignments and metadata.
- Natural/mathematical generators: L-system plants, crystals, terrain, river
  networks, constellations, kaleidoscope, reaction-diffusion, cellular automata,
  fractals, iterative attractors, audio-derived visual motifs and shader arts.
- Composite Object Identity Block-style cards with full canonical ID, kind,
  alias/phrase, public-only QR and accessibility description; manual sprite
  overrides leave the primary node identifier unchanged.

**Exit:** at least 20 stable catalogue profiles with deterministic Node/browser
vectors; 16/32/64/128/512px output checks; colour-vision and user-confusion
study; full-id disclosure on identity confirmation (not image-only trust).

### BF-W7: Image, vector, accessibility and document exporters (Waves B, C, F)

- **Bitmap:** PNG, WebP, AVIF, GIF, APNG, JPEG (identity-only or explicitly
  lossy), TIFF/PBM/PGM high-contrast archival, ICO, iconset, favicons.
- **Vector:** SVG (canonical), EPS/PostScript where justified, monochrome
  plotter paths, PDF vector and PDF/A (compliance validator), raster profiles,
  multi-resolution thumbnails and print-ready tiled posters.
- **Document:** A4/A5/Letter cards, fold-booklets, numbered recovery worksheets,
  bilingual *instructions* (not unversioned translations of binary wordlists),
  optical contact sheets, Braille BRF, alt text, captions, metadata manifests.
- **Web:** CSS background/data-URI, picture/srcset, favicon/OG-card,
  accessible React component, Canvas/WebGL texture and worker-supplied image.
- Exporters must expose colour profile, DPI and exact dimensions/bleed, margin,
  quiet zone, line widths and typography/frozen font metadata if used.

**Exit:** reconstruct source from published recovery documents/optical symbols;
print/raster output quality metrics, no secret record in EXIF/preview or file
name; PDF/A verification where claimed; low-resolution identity legibility.

### BF-W8: 3D, volumetric, tactile and manufacturing (Waves G and H)

- Generated 3D glyphs and characters, reliefs, extruded public QR matrix,
  voxels, height/normal/displacement/roughness maps, point clouds and
  procedural orbital objects for public node identity.
- Export GLB/glTF (primary runtime), OBJ/PLY/STL, 3MF (manufacturing profile),
  DXF, SVG laser paths, STEP only through measured CAD-compatible exporter,
  G-code only by controlled integration with reviewed slicer/firmware.
- Investigate embossing, punched paper/card, perforated mesh, milling,
  ceramic tiles, stitched textiles, engraved steel, etch, PCB copper, microfilm,
  infrared marker layering and other repeatable physical binary carriers.
- Pixel/geometry scale and orientation labels, relief depth constraints,
  real-world camera scanning and model-versioned CAD precision.

**Exit:** fabricated symbol independent scan/readback under recorded material,
finish, module pitch, illumination and decoder; 3D visual avatars validated as
identity-only unless a separate decoder is proven. No uncontrolled machine
instructions; never assume durable media ensures correct wallet restore.

### BF-W9: GPU, video, live scene and game engine deliverables (Wave G)

- Sprite strips, multi-resolution sprite atlases with packed UV JSON, animated
  sprite sheets, GL texture uploads, mipmapped KTX2/BasisU, Unity sprite prefabs,
  GLB/3MF scene data, interactive HTML demos and WebXR/AR presentations.
- WebGL2/WebGPU and Canvas2D compute/renderer fallback strategy; shader DSL,
  versioned RNG/noise/cellular models, stable layout and deterministic seeds.
- Media export: APNG/GIF/WebP animation, SVG animations, Lottie/Rive only if
  semantic conversion is compatible, WebM/MP4 loops and video thumbnails.
- Optimise the 1k–100k node graph case: thumbnail LOD, atlas batching,
  memory/latency cache metrics, colour accessibility, reduced-motion/static
  fallbacks; link optional performance sharing with FrameRudiments/PrismMoves.

**Exit:** no broken identity when spritesheet packing changes; 1k-node UI and
representative large graph scene benchmarks published; pinned ref seed yields
stable assets across Node/WebGL/Unity within advertised determinism tier.

### BF-W10: Audio, speech, signals and tactile channels (Wave F)

- Generate stable public musical signatures/earcons, MIDI note/beat patterns,
  PCM WAV/FLAC, audible identity cues, rhythm/call-and-response, TTS-readable
  names and offline SSML/VTT transcription metadata.
- A distinct modem/transport adapter for ggwave-style FSK sound exchange,
  optionally Morse LED/light patterns with explicit frame, checksum and FEC.
- NFC NDEF import/export and read-back compatibility on actual tags; hardware
  reader modes with separate permission and size profiles.
- Braille characters/uncontracted binary cells, embossed paper/BRF, semantic
  tactile markings and haptic feedback sequences for accessible recognition.

**Exit:** public binary recoverability only from transport modes with proven
decoder; real-device latency/loss tests and accessible alternatives. A tune,
TTS voice or vibration is not an arbitrary-byte backup unless formally encoded.

### BF-W11: Long-term durability, erasure, redundancy and offline archive (Wave H)

- Integrity checks: per-packet CRC, cryptographic digest commitment, object
  context and complete original length; correct intentional vs accidental
  corruption framing.
- Reed–Solomon/BCH/erasure/fountain schemes as independent tested components,
  with exact advertised correction limits; PAR2/RaptorQ-style redundancy for
  media sets only when interoperable.
- Media templates: monochrome paper/PDF-A; laser/metal/stamp; machine scanner
  targets; optical strips and microfilm; fabrication metadata and material
  test evidence. Printing and destructive tests use **public dummy data**.
- Measured failure/fidelity across copying, faxing, grayscale conversions,
  page/fragment omissions, blur, glare, scratching, oxidisation and ageing.
- Recovery kit: open specification, one-page decoder instructions, software
  and source snapshot, human transcription fallback, multiple geographical
  copies and periodic verified readback guidance.

**Exit:** documented test corpus contains both successes and failures;
independently recovered bytes plus type and metadata equal the original record.
Do not advertise unconditional correction or medium life span.

### BF-W12: Specialist experimental laboratory (Wave H and later)

- Multi-colour code density vs scanner/printing quality: JAB, Ultracode,
  photographic colour stripes and multi-spectral tags.
- Novel codes: fractal/fiducial patterns, data-bearing procedural artwork,
  polar/annular codes, conformal curved-surface codes, shadow-projection art,
  IR-visible/UV/fluorescence/micro-dot tags and lenticular/holographic designs.
- Experimental **lossless** storytelling: haiku/rhymes/poetry, structured
  dialogue, phonetic checksums, conditional grammar/weighted slot scheduling,
  multi-language frozen dictionaries, physical letter/tile/card puzzles.
- Emerging media: 5D laser glass, DNA storage, photographic and magnetic
  archival experiments, wearable displays, e-paper, haptics, acoustic and light
  data links, braided or woven relief artifacts.
- Explicitly distinguish source-backed results from new codec ideas;
  steganographic image/watermark-only private-key backups not recommended.

**Exit:** publish reproducible public fixture, sample artifact, complete
specification and independent decoder. Keep lab features unavailable to the
secret-backup release until reviewed and reproducible.

### BF-W13: Integration, packaging, discoverability and plugin ecosystem (Waves B–I)

- ByteFables manifest for DanceFlow discovery, MCP component description,
  media type router, CLI `inspect/list/render/encode/verify` commands for
  **public values only**, TypeScript/React/Next.js integration, Python bridge
  only against shared vectors.
- Expose public fallback avatar and optional gallery/card renderer to thought
  graphs, workspace orbs, profile cards, asset thumbnails, scene nodes and
  branded media across DanceFlow. The source node key is always canonical.
- Backend async/worker job status, batch streaming, deterministic caching,
  `rendererVersion+options+identityDigest` keys, no remote work for secret input.
- Documentation/demo matrix shows implemented vs experimental vs researched,
  warns of missing optional dependencies and required readback devices.

**Exit:** published package/registry only for independently validated formats;
MCP/CLI cannot cause an unreviewed decoder or secret backup flow to run. Report
actual performance and coverage instead of inventing it.

### BF-W14: Wallet-specific secret archival security gate (Wave I)

- Maintain a wholly separated offline companion, with import/export consent,
  no clipboard/telemetry/browser logs/remote printers, protected memory design
  for supported runtimes, backups not uploaded to remote art services.
- BIP-39/SLIP-39/seedQR/UR and any encrypted container must retain network,
  curve, account/derivation, descriptor or policy context as applicable.
- Independent reviewed cryptography, canonical format/cross-vendor restore
  tests, no unprompted key generation, no auto-correction without verified
  original authentication and explicit operator decision.
- Recovery drills on real compatible devices using test vectors and test funds;
  separate confidentiality protection from accidental-damage recovery.

**Exit:** Stage 7 release criteria independently signed off. Existing
TypeScript `ByteValue<'secret'>` labels are **not** a safety guarantee; no
production key backup recommendation before this gate.

## Issue-ready milestone backlog (ordered within areas)

Each item gets an issue link, maintainer, target wave, input fixtures, evidence
location and explicit done/blocked status. A P1 item can proceed in parallel
once prerequisites are satisfied; P2 is research or deployment dependent.

| ID | Priority | Work item / reviewable acceptance evidence | Prereq |
|---|---|---|---|
| BF-001 | P0 | Registry schema, capability manifest and typed format planner; negative maturity tests | Stage 0 |
| BF-002 | P0 | ByteFables CBOR/CDDL envelope and public canonical vectors | BF-001 |
| BF-003 | P0 | `ModuleMatrix` and `VectorScene` immutable intermediate artifacts | BF-001 |
| BF-004 | P0 | Public QR Model 2 adapter with ECC and 2 independent decoders | BF-003 |
| BF-005 | P0 | SVG and PNG exporters with exact-size/quiet-zone conformance | BF-003 |
| BF-006 | P0 | Bytewords normal/URI/minimal with reference vectors | BF-002 |
| BF-007 | P0 | 33-bit grammar theme and bijection/fuzz corpus | Existing Stage 2 |
| BF-008 | P0 | Public identity card with full ID and QR | BF-004, Stage 1 |
| BF-009 | P0 | 16/32/128px avatar profiles, favicon, batch caching | Stage 1 |
| BF-010 | P0 | GitHub Pages interactive gallery, actual format capability badges | BF-001, 008, 009 |
| BF-011 | P1 | PDF/public print sheets (A4/A5/Letter), scan/readback checks | BF-004, 005 |
| BF-012 | P1 | Base45, strict Base64, Crockford Base32 and Base58Check | BF-001 |
| BF-013 | P1 | BIP-39 official-vector compatibility (dummy inputs only) | BF-002 |
| BF-014 | P1 | SeedQR/CompactSeedQR interoperability using public test fixtures | BF-013, 004 |
| BF-015 | P1 | Typed UR v2 fountain encoder/decoder, bad/missing fragment tests | BF-002, 004 |
| BF-016 | P1 | Data Matrix ECC200 with scanner fixtures | BF-003 |
| BF-017 | P1 | Aztec and PDF417 adapters, independent readers | BF-003 |
| BF-018 | P1 | Art pack v1 (20+ renderer variants) incl. LifeHash compatible mode | BF-001, Stage 1 |
| BF-019 | P1 | Identity gallery 1k-node and 16px confusion/accessibility test | BF-018 |
| BF-020 | P1 | GPU spritesheet/atlas, metadata, texture cache eviction metrics | BF-018 |
| BF-021 | P1 | File bundle, manifest + recovery/readme and independent verification | BF-002, 005 |
| BF-022 | P1 | Story variable-capacity grammar scheduler + proof of unique parse | BF-007 |
| BF-023 | P1 | Language/homophone transcription pilot with fixed lexicons | BF-007 |
| BF-024 | P1 | Model interoperability for Formosa (draft-pinned) | BF-013, 007 |
| BF-025 | P1 | Multi-frame UR displays and BBQr benchmark fixture | BF-015 |
| BF-026 | P1 | Monochrome 3D engrave/DXF/3MF public optical symbol export | BF-004, 011 |
| BF-027 | P1 | GLB/GLTF node token + Unity atlas/scene adapter | BF-018, 020 |
| BF-028 | P1 | Node fallback API / DanceFlow MCP capability integration | BF-001, 018 |
| BF-029 | P1 | Large graph (10k+) profiling, WebGL/WebGPU progressive LOD | BF-020, 028 |
| BF-030 | P1 | CI protocol-fuzzing, scanned artifact corpus and licence ledger | BF-001 |
| BF-031 | P2 | Micro QR, rMQR and Han Xin scanner survey and prototype | BF-004 |
| BF-032 | P2 | DotCode/Code128/industrial print/DPM comparison | BF-016 |
| BF-033 | P2 | JAB coloured marks, Ultracode specification/status research | BF-016 |
| BF-034 | P2 | OPTAR / printable large-file erasure baseline (public data) | BF-021 |
| BF-035 | P2 | Metal/stamp/laser/calibration templates and destructive scan report | BF-026 |
| BF-036 | P2 | Animated SVG/APNG/WebM loss testing of optical frames | BF-025 |
| BF-037 | P2 | Public NFC NDEF reader/writer with real tag readback | BF-002 |
| BF-038 | P2 | ggwave-style public acoustic modem/WAV receiver experiment | BF-002 |
| BF-039 | P2 | SSML/VTT offline speech, earcons/MIDI and accessible names | BF-007, 018 |
| BF-040 | P2 | Braille BRF, raised relief and 8-dot byte-cell study | BF-011 |
| BF-041 | P2 | OpenSSH Randomart, geometric/voronoi/cellular avatar variants | BF-018 |
| BF-042 | P2 | Procedural landscape, heraldry, animal, mythology and music themes | BF-018 |
| BF-043 | P2 | Shader/particle/motion loops, KTX2 texture and WebXR preview | BF-027 |
| BF-044 | P2 | Microfilm, photographic archive, PCB/tile/textile research demos | BF-035 |
| BF-045 | P2 | HCCB/Bokode/IR/3D hidden tags reader viability experiment | BF-035 |
| BF-046 | P2 | Reversible poetry/dialogue/conditional story language experiment | BF-022 |
| BF-047 | P2 | Audio/LED/Morse/haptic public identity-and-transport study | BF-039 |
| BF-048 | P2 | SLIP-39, codex32 and encrypted wallet format feasibility review | BF-013, W14 |
| BF-049 | **BLOCKED** | Independent secret key archive and restore workflows | Stage 7, W14 |
| BF-050 | P1 | Source/digest manifest, SBOM, release verification and registry freshness | BF-001 |

**P0 = next release-fundable**, **P1 = primary roadmap**, **P2 = candidate/lab**,
**BLOCKED = no shipping regardless of completed upstream work until security
review**. Priorities are planning judgements, not reported project commitments.

## Public demonstration products to ship incrementally

1. **Identity Wall:** enter or select a *public* hash/node ID; compare 20+
   avatar themes, naming templates, snapshots, cards, orbiting 3D node and
   accessible high-contrast alternatives; exact seed and renderer version shown.
2. **Codec Workbench:** encode a dummy byte string into strict text, story,
   QR, Bytewords, CBOR and back; live bit-capacity/overhead and checksum budget;
   no network or sensitive material by default.
3. **Print/Scan Laboratory:** public test fixtures with SVG/PNG/PDF/3MF
   previews, export DPI and module pitch, deliberate damage toggle, independent
   decoder results and a reproducible failure corpus.
4. **Transport Lab:** chunked/animated optical streams, optional speaker and
   NFC adapters, real-world recovery graphs and device compatibility matrix.
5. **Node Identity Integration:** consistent fallback profile art in graph
   views, orbit workspace navigation and asset/media catalogues, with cache
   manifest and full public ID on inspection.
6. **Offline Recovery Companion (future):** separate release, no launch or
   import path unless all security and interoperability gates are complete.

## Output QA and measurement matrix

| Output family | Round trip | Interop | Rendering | Physical/device test | Visual recognition | Security |
|---|---|---|---|---|---|---|
| Exact text, mnemonic, story | Mandatory | Reference vectors | Layout/print readability | Human transcription | Optional | Secret gate for wallet use |
| QR/Data Matrix/Aztec/PDF417 | Mandatory | Independent reader | Quiet zone, capacity, contrast | Camera/print/engraving | No security inference | Secret gate |
| UR/BBQr/multi-part | Mandatory | Independent receiver | All frames & timing | Drop/reorder/glare | N/A | Secret gate |
| Identity avatar/card | **Not applicable** | Style-reference vectors | 16px to 4K, alt text | Browser/Unity if relevant | User confusion study | Public only |
| 3D/laser relief | Mandatory only if data-bearing | Independent 3D decoder | Module geometry | Real part scan | If identity art | Public initially |
| Audio/LED/NFC transport | Mandatory if data-bearing | Independent device | Timing/signal profile | Interference, power, range | If earcon | Public initially |
| Print/microfilm/metal archive | Mandatory | Independent offline restore | DPI/material limits | Repeated physical readback | N/A | Secret gate |

Make profiles fail *closed* if a format cannot fit the payload and metadata,
if a renderer would violate optical module geometry, if resource limits are
exceeded, or if a secret value is about to enter a public/art/cloud device sink.
A format without a decoder must be catalogued as **non-reversible**.

## Roadmap upkeep and definition of coverage

- Never implement a new visual style by modifying a frozen encoder/identity
  digest. Keep separate scene renderers and canonical `styleVersion`.
- For `OUTPUT_FORMAT_ATLAS.md`, track each line's **state** (`research`,
  `prototype`, `tested`, `interoperable`, `released`), format/version, an issue,
  code owner, actual licence and a golden vector, without suggesting every
  listed candidate is committed work.
- Record rejected candidates with a reason (reader availability, weak
  durability, licensing, security, low demand, overlap); maintain a separate
  "experimental gallery" so ambitious ideas remain discoverable.
- Refresh external draft statuses before releases; BIP-450, BIP-93 and
  Ultracode are drafts/under development as of this survey, not approved
  proof of wallet interoperability.
- One golden dummy byte payload (128, 256, 512, 4,096 and larger sizes) should
  be rendered through every supported *lossless* pipeline and decoded by a
  distinct code path; capture the full artifact checksums and failures.
- Publish a verified **coverage dashboard** with `implemented/compatible/
  experimentally demonstrated/researched`, scanner and device matrix,
  performance measurements, and security badges based only on actual reviews.


---

## Wave J / BF-W15 — robust invisible watermark research and media adapters

**New fourth operation category** (`watermark`), dependent on Wave A typed
public records and native FrameRudiments effect-graph extension. Its *purpose*
is a public identity reference embedded perceptually unobtrusively in another
carrier, statistically extractable after a bounded, measured set of edits. Do
not equate a watermarked carrier with original key recovery or authenticity.
The [full protocol and attack matrix](specs/watermark-v1.md) defines version 1.

**Wave A delivered in this patch:**
- Frozen `BFWM` watermark message v1 with 12/16/32-byte public-record SHA-256
  prefix, version, size, CRC32. Decoder and candidate binding check, vectors.
- `planPublicWatermark` for image/audio/video/text, including message-bit budgets,
  conservative media research eligibility and distortion test targets.
- Registry entries for all four as strictly **planned/non-executable**;
  `probabilistic-recovery` guarantee and second carrier input type introduced.
- Public-only CLI `watermark-plan`, negative tests, documentation and security
  limits. **No** watermark is currently embedded or detected in any medium.

**Next shared native FrameRudiments work (prerequisites):**
1. [P0] Add an explicitly registered, trusted, versioned effect plugin contract
   to FrameRudiments effect graph. Keep all media effects in its host, using
   existing render/effect clocks, reports, assets, CPU/GPU backends and
   provenance. Do not copy host rendering into ByteFables.
2. [P0] Specify exact insertion stages: image final raster before delivery
   encoding; video after visual effects, temporally spread; derived audio
   mix/export after canonical master (the master remains byte-identical);
   text only through generator-time constrained selection.
3. [P0] Add a stable extraction API, explicit signed/unsigned soft-binding
   schema and benchmark harness. Distinguish blind detection from comparison
   with supplied unmarked original.
4. [P0] Choose ECC/interleaver and synchronisation profile; count coding bits
   **after** `BFWM` envelope and CRC. Establish honest capacity estimates for
   96, 128, 256-bit identifiers and evaluate shorter external lookup handles.
5. [P0] Create a synthetic, nonsecret distortion corpus with controls and
   reproducible codec/resize/crop/rotation/removal parameters, plus metrics
   for bit error, false positive, failure, confidence, and visual/audio quality.

**Carrier implementations (separately qualification-gated):**
6. [P1/image] Multiscale perceptual residual/transform-domain image watermark,
   sync markers, spatial tile repetition and crop recovery; StegaStamp/modern
   reference comparison; independent PNG/JPEG/WebP output and scanner tests.
7. [P1/audio] Time/frequency spread-spectrum and/or reviewed learned audio
   watermark adapter; speech/music/silence subsets, MP3/AAC/Opus, resampling,
   channel conversion and time cropping. Respect FrameRudiments' **unchanged
   master** and publish a separately marked derived audio stream.
8. [P1/video] Temporal/spatial repetition with scene/clock-aware symbol
   alignment, frame drop, transcoding, FPS and partial-clip tests;
   VideoSeal/RivaGAN benchmark comparisons.
9. [P1/text] Generator-controlled probabilistic/syntactic watermarking on
   semantically interchangeable text. Quantify excerpt, rewriting and
   translation limitations. Refuse rewriting arbitrary fixed text, quotes,
   program code or signed documents. No fragile Unicode trick promoted as
   robust format.
10. [P1] Measurable embedding budget and `strength` quality profile per carrier,
    with opt-in and clear no-watermark fallbacks; preserve existing identity
    digests, grammars and image-only generators without byte changes.
11. [P1] C2PA manifest soft binding and optional signing/full original hash
    verification. Do not treat unkeyed CRC or a recovered 96-bit prefix as
    attribution, proof of ownership, or authenticated provenance.
12. [P1] Native FrameRudiments evidence/exports and independent detector at
    delivery boundary; build optional integration in ByteFables but do not
    duplicate the host effect graph or any generator.
13. [P2] Mixed-media redundancy, texture/3D watermark lab, optical physical
    photo/screen capture and neural resynthesis attack evaluations.
14. [P2] Cross-platform performance, GPU/model licence review, adversarial
    removal and watermark forgery assessment; explicit per-profile claims.

**Release gate:** for each independently supported carrier/profile, publish
unmarked controls, ≥1,000 representative nonsecret positive samples, error
rates and confidence intervals, blind decoder independent from embedder,
full final-export artifact readback, named bounded distortion profiles,
measured perceptual quality and false-positive thresholds. A clean "watermark
found" output alone is not enough. Successful detection never replaces
cryptographic signature/public-key verification, and **no secret payload**
shares this public renderer pipeline. All four adapters remain `planned`
until evidence qualifies the *specific* profile.


---

## Experimental Wave J — bit-conditioned generative identity art (started)

**Purpose:** compare small local prompt writers and tiny image generators
against a frozen, one-bit-to-one-opposing-feature semantic contract. See
[BF-EXPERIMENT-IMAGE-001](specs/hash-image-benchmark-v1.md) and
[compact model research](IMAGE_MODEL_RESEARCH.md). This operation remains
**public identity art**, never a lossless hash/key backup.

**Implemented foundational items:**
- Frozen MSB-first bit-feature choices, source length 1..512 PUBLIC bytes,
  32 global opposing visual attributes and 16 repeatable local feature types
  bound to separately numbered micro-motifs. The full manifest retains every bit.
- `visual-features` CLI; baseline prompts; six local research prompt styles;
  single-bit-flip dataset and deterministic identity/paired noise seed policies.
- Loopback-only OpenAI-compatible small-LLM prompt authoring with raw replies,
  exact feature IDs and lexical coverage diagnostics. No source hash to LLM.
- Local-only Diffusers cross-product with explicit GPU opt-in, checkpoint
  revision claims, PNG source receipts, elapsed time, optional peak GPU memory,
  tokenizer truncation indicators and source artifact hashes.
- Optional locally pinned CLIP pairwise caption scorer, blind observer import,
  paired-bit/low-cost image diagnostics, aggregate JSON/HTML report.
- Pinned raw image asset handoff to native FrameRudiments sprite/effect pipeline;
  no new ByteFables effects or visual compositor.

**Remaining evidence and implementation gates:**
1. Run *real* small LLM and image checkpoints on identified GPU hardware.
   The initial testing environment has no CUDA device or model weights.
2. Implement a native FrameRudiments prompt-conditioned source generator that
   reads approved and SHA-pinned image assets without launching model downloads.
3. Calibrate independent VQA scoring and human binary judgments on balanced
   one-bit-flip sets; establish per-feature confusion and confidence intervals.
4. Add big-image and 16/32px nearest-neighbour identity retrieval, perceptual
   distance/LPIPS/DINOv2 and validated alt-text accessibility.
5. Improve prompt compression/hierarchical groups, test attribute count
   4..256, tokenizer truncation, negative-prompt support and prompt weighting.
6. Optimise generator model/prompt writer Pareto frontier under operator GPU
   VRAM, time, cache/storage budgets; publish a controlled, nonsecret gallery.
7. Qualify model copyrights/licenses, pinned revisions, resource containment,
   standalone offline reproducibility and independent external replication.

**Exit:** no model ranking without actual inference; no "256-bit image" claim
without an independent error-controlled exact decoder; no usable private key
workflow in this module.


## BF-W15: Fractal seeding and tiny-image generation experiments (experimental)

**Source:** [BF-FRACTAL-001](specs/fractal-seeding-v1.md). This workstream is
linked to Wave B public identity renderers, the FrameRudiments host integration,
and the local tiny-LLM/image model benchmark. It is NOT part of secret archival.

**F15.1 — Complete:** Domain-separated public-record fractal seed and fixed
opposing feature axes; four bounded generator families registered into
FrameRudiments; TS/Python vector and fail-closed style validation.

**F15.2 — Complete:** CPU static-fractal gallery, original/single-bit-flip
counterfactuals, avalanche vs fixed-seed trials, PNG receipts, checksums, pixel
statistics and change metrics. 8 axes are explicitly manipulable, not 256
recoverable bits. Both nondegenerate and collapsed outputs remain in reports.

**F15.3 — Experimental code path:** Local SD/SDXL spectral-correlated-noise
latents with paired Gaussian controls; explicit beta/mix and checkpoint
validation. Requires actual model inference to make performance claims.

**F15.4 — Experimental code path:** SHA-verified FrameRudiments fractal source
image as local SD/SDXL image-to-image initial condition; adjustable strength.
Requires real local checkpoint acceptance and output quality studies.

**F15.5 — Next:** Score 1k+ public hashes and stratified bit flips across 16,
32, 64 and 128px icons; human-blinded feature recognition; artist-controlled
palette libraries; reject or mark degenerate seeds rather than cherry-picking.

**F15.6 — Next:** Evaluate bounded Julia family parameter search, Newton basins,
fractal flames, orbit traps, complex-polynomial symmetries, L-systems and
transformable IFS; cross-runtime determinism fixtures and optional GPU kernels.
The original GPL flam3 source must not be copied into this MIT package.

**F15.7 — Later:** ControlNet/IP-Adapter where checkpoint support and licensing
permit, deterministic fractal animations using native FrameRudiments clock,
per-pixel identity shader themes and shared DanceRudiments parameters. Content
provenance, source image verification and reduced-motion output are required.

**Exit:** statistically supported comparative table of distinctive identity
success rate, visual collisions, validated feature adherence, GPU/CPU costs and
failure rates across direct fractal, normal Gaussian diffusion, structured
fractal noise and fractal img2img. No ability to reconstruct original hash
from art is claimed.

## Compact public identity profiles: 24/32/64 bits (implemented)

- New SHA-256 parent identity prefix aliases for 3-, 4-, 8-byte human/display
  IDs, with strict format labels and immutable golden vectors. The unchanged
  public identity digest remains authoritative.
- Public-only registry adapters and CLI subcommand, optional shortening in
  `visual-features`, and short-size-aware feature budgets in the image benchmark.
- Semantic counterfactual flips remain distinguishable from original-input
  avalanche tests; do not extrapolate high-bit diffusion seeds to additional
  visual information capacity.
- Future benchmark work: population-level collision measurements, recognisability
  at icon sizes, independently scored model feature adherence and cross-family
  visual collision/ambiguity studies.

Normative details: [short-public-hashes-v1.md](specs/short-public-hashes-v1.md).

---

## October 25, 2026: public optical and artwork implementation checkpoint

This development batch implements the following **public-only** slices of
waves B/C/E/H while deliberately preserving Stage 7 secret qualification:

- **QR Model 2**: complete version 1–40 byte-mode matrix encoder, ECC L/M/Q/H,
  standard Reed–Solomon grouping, eight masks, capacity and input validation.
  Independent encoder comparison: 56 synthetic cases across representative
  versions, plus an external OpenCV reader of exported FrameRudiments PNGs.
- **BFQR1**: versioned public-only typed CBOR frames, strict Base64url header,
  CRC-32 and full SHA-256-derived session ID, deterministic ordered parts,
  strict out-of-order recovery and optional XOR one-erasure repair. NOT MUR/URv2.
- **FrameRudiments identity cards**: registered module-matrix layer fragments,
  protected optical profile guidance, checksum labels and public fingerprint
  context; no replacement rendering/effects pipeline.
- **Four native artwork generators**: reusable sigils, constellations, heraldry,
  topography with deterministic digest seeds, validated styles and tests.
- **CLI/registry**: public export, stdin scanner-text restore and artwork-layer
  creation; 37 checked capability entries. QR BFQR1 remains experimental.

**Remaining dependencies for a complete Stage 4/5 release:** independent
hardware-wallet interoperability, URv2 fountain encoder/decoder, actual print
and scanner matrix across printers, transformed/cropped/damaged-media tests,
G-code/metal media workflows, high-density 2D symbologies, Node/browser
cross-runtime integration, >20 artwork variants, accessible identity cards,
UI gallery, and installed native FrameRudiments compositor/effect-graph QA.

**Safety gate:** no wallet-seed/private-key encoding or secret archival approval
has been added by this milestone. Public sample images and short fingerprints
never authenticate ownership. The exact public typed bytes always remain
available separately for verification.


## Completed public optical recovery and procedural art batch (25 Oct 2026)

- Added restricted BCR-2024-001 `ur:bytes` multipart transport: deterministic
  fountain generation, bounded streaming Gaussian elimination receiver, official
  Xoshiro/fragment-selection vectors, and FrameRudiments QR layer handoff.
- Added an entirely separate **BFQR1** FrameRudiments printed public-record
  sheet adapter with mandatory pinned font, full fingerprint and exact manual
  text. PNG exporter validates the saved symbol with OpenCV. It is not a
  physical, PDF/A or private-key archival qualification.
- Increased procedural FrameRudiments identity generators from four to nine;
  maintained old style names/algorithms unchanged, with validation and
  deterministic output tests. New families: crystal, mandala, cellular,
  branching and orbital.
- Extended the public-only capability registry and user-facing CLI; preserved
  both previous BFQR1 and all legacy mnemonic/story wire formats.

**Still not shipped:** registered production UR application types, actual
wallet/hardware interoperability, sustained frame-loss device testing, PDF/A,
printing/engraving and damaged-media restoration, secret/wallet safety review,
large-sample visual distinctiveness and full native host release qualification.

**Next:** register/validate compatible UR types and test against independently
released decoders; provide explicit 300dpi/PDF/A manufacturing profiles and
separate hard-copy scan results; benchmark nine art styles at 16/32/64 px;
profile physical/optical error rates and extend archive ECC beyond XOR parity.

---

## Video effects research and implementation programme (25 Oct 2026)

The [video effects implementation roadmap](VIDEO_EFFECTS_IMPLEMENTATION_PLAN.md)
adds host-owned effect expansion milestones **VE0–VE9** and 25 engineering
issues **FX-001–FX-025**, with an explicit distinction between a demonstrated
FrameRudiments control, a composable preset, and a future shader/effect node.
The [143-effect research catalogue](../manifests/video-effects-v1.json) has
11 implementation families; 35 entries map to an existing host route (some
only as an explicitly labelled visual approximation), while the remainder
require FrameRudiments work or specialist research.

**VE0 implemented in this ByteFables patch:** frozen research catalogue,
validation, 16 deterministic public video-look recipes, scope/intensity
validation, public-only CLI and tests. **Nothing new renders inside
ByteFables.** FrameRudiments retains all source animation, post effects,
colour conversion, GPU, compositing, rendering and video encoding; the
optical QR protection rule remains hard. New effect algorithms await changes
in the FrameRudiments repository under its own graph roadmap. No GPU
performance or perceptual image-quality claim is made by this document.
