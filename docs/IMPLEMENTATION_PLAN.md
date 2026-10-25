# ByteFables staged implementation plan

**Date:** 2026-10-25. This is a technical roadmap, not a claim that phases
have shipped. Plan items reference [DESIGN.md](DESIGN.md) and [SECURITY.md](../SECURITY.md).

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
safety gate; a successful encoder does not implicitly satisfy it.

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

## Stage 2 — reversible grammar engine **[13-bit proof of concept included]**

**Included prototype:** grammar compiler, two equal-capacity sentence templates,
13 bits per sentence, magic/version/size/CRC32 prototype format, exhaustive
8,192-codeword bijection test, corruption/truncation/size tests. It is not an
interoperable backup format.

**Next work:**
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

**Exit:** random byte arrays (including 128–512-bit fixtures) round-trip with
strict bit-accounting and no ambiguous parse across every allowed template.
Advertised sentence capacities match independent measurements.

**Follow-on:** Formosa-compatible theme adapter only after official test-vector
and wallet compatibility checks, not merely because both use 33-bit blocks.

## Stage 3 — interoperable standard encodings

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

The repository was confirmed empty before the initial patch. The patch is
created against an empty Git index, so `git apply --check` works after `git
init` or directly inside the empty checkout. Files are **not pushed** by
producing the patch. Do not claim GitHub Actions have passed until a commit is
pushed and the workflow reports success.
