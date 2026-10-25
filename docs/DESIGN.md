# ByteFables — Architecture and design specification

**Document:** `BF-DESIGN-001`
**Status:** working design; normative only for the explicitly identified
`foundation` and `experimental` prototype formats
**Date:** 2026-10-25
**Target:** reusable DanceFlow component, usable standalone by Node.js, web UI,
CLI, Python/WASM clients and ecosystem MCP adapters.
**Implementation roadmap:** [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md)

## 1. Vision

ByteFables is a deterministic representation toolkit for typed byte sequences.
Every node can possess a unique cryptographic **identity**, any public value can
be rendered into recognisable **art**, and selected binary values can be mapped
into **lossless** text or machine-readable formats. Later, ByteFables will
support reviewed, interoperable **secret archival** adapters.

A ByteFable is a representation of bytes, not an independent source of truth.
The original bytes and their provenance determine identity. Names, art and
backup envelopes are *views* with different guarantees.

### 1.1 Design goals

G1. Lossless formats MUST round-trip byte-for-byte, preserving length and leading
zeroes and rejecting unsupported versions, invalid padding and ambiguous input.

G2. Public identity art MUST be deterministic for a specific input, namespace,
object kind, derivation algorithm and renderer version.

G3. Generated phrases SHOULD be grammatically coherent, pronounceable and
varied. Any phrase advertised as a *lossless codec* MUST be unambiguously
reversible: style quality cannot weaken injectivity.

G4. Format IDs, dictionary order, grammar rules and renderer versions MUST be
stable. Published codebooks are immutable; an update creates a new version.

G5. Preserve existing ecosystem node IDs. ByteFables MUST be an optional view,
not an alternate consensus or identity algorithm.

G6. No secret value enters public avatar or name generation, logging, caching,
remote services or media pipelines by default. This is an API-design and threat
model goal, not a claim of secure memory on JavaScript hosts.

G7. Provide readable metadata, honest collision budgets, reproducible test
vectors, capability discovery and clear interoperability status.

### 1.2 Non-goals

- Replace Bitcoin/other blockchain consensus rules, keypair verification or
  address-format cryptographic validation.
- Treat a rendered icon or a shortened fingerprint as proof of ownership.
- Decode a cryptographic hash back into its preimage.
- Claim that mnemonic stories improve cryptographic security or add entropy.
- Invent a new cryptographic hash, key derivation, cipher, MAC or secret-sharing
  algorithm in the foundation release.
- Automatically “repair” unknown secret text without review and verification.

## 2. Terminology and security classes

**Payload**: exact byte string, of known length, before representation.

**Context**: canonical namespace, type/kind, network, version, and optional
content schema; context MAY be required to interpret a recovered payload.

**Identity**: full, canonical, verifiable object ID or a digest of canonical
public bytes. The SHA-256-derived ByteFables *identity digest* is used for
repeatable art and fingerprints; it is not a blockchain transaction signature.

**Alias**: pronounceable or visual mnemonic suitable for browsing and human
recognition; MAY intentionally encode only a fraction of the identity bits.

**Lossless**: decoder reconstructs every payload byte. If the encoding omits
context, the decoder MUST declare that it returns raw bytes only.

**Archival**: lossless format plus explicit framing, integrity, recovery, medium
and operational policy. Secret archival is a separate protected activity.

**Correction**: algorithmic recovery from damaged data. A checksum that detects
errors does not itself correct them. Threshold sharing recovers from missing
shares and is not the same as optical symbol correction.

### 2.1 Output classes

| Class | Payload reconstructible? | Publicly shareable? | Identity guarantee |
|---|---|---|---|
| Full public byte encoding | Yes | Yes, for public data | Exact only when fully compared |
| Wallet backup / secret archival | Yes | **No** | Requires correct secret, metadata, threat model |
| Short text fingerprint | No, normally | Public inputs only | Probabilistic; size documented |
| Procedural avatar | No | Public inputs only | Visual recognition aid only |
| Human-readable generated alias | Depends on its mode | Public aliases only | Not a unique ID without registration |
| Archival optical transport | Yes, with its full envelope | Depends on payload | ECC/symbol checksum ≠ authentication |

### 2.2 Sensitivity labels

The initial `ByteValue` API has `public` and `secret` labels; each value snapshots
its source bytes and exposes a defensive copy. Public renderers require a
`PublicByteValue` and reject a secret value at runtime. TypeScript narrows the
error surface; *the caller's classification remains a trust input*.

Current `ByteValue<'secret'>` is reserved and MUST NOT be taken to mean
“production-ready private key container”. The JS runtime does not guarantee
memory lock, zeroisation, enclave execution, or safe clipboard handling.

## 3. Architecture

```text
Canonical typed input (network/type/namespace/original bytes)
      |
      +--> [Public identity service]
      |        SHA-256 domain-separated digest
      |         +--> full canonical ID / short verification fingerprint
      |         +--> visual renderer registry (SVG, sprite, shader, art)
      |         +--> friendly identity naming (non-reversible allowed)
      |
      +--> [Lossless encoding service]
      |         +--> standard text codecs (hex, Base32, Bytewords ...)
      |         +--> grammar pack compiler / reversible story encoder
      |         +--> versioned self-describing archival envelope
      |
      +--> [Secret archival: FUTURE, separately gated]
                +--> BIP-39, SLIP-39, descriptors, SeedQR
                +--> verified ECC/UR fragments and print/engraving outputs

Cross-cutting: capability registry, golden vectors, security policy,
              schema/version registry, cryptographic boundaries, tests
```

### 3.1 Runtime and integration strategy

**Phase 0:** zero-runtime-dependency TypeScript package; ES2022/NodeNext;
WebCrypto SHA-256; strict TypeScript and native Node unit tests.

**Near-term:** CLI for public-byte workflows (no secret arguments), browser
demo, deterministic SVG downloads, package metadata and MCP discovery adapter.

**Long-term:** separately packaged Python bindings or language-neutral codecs,
WASM render kernels for demanding art generators, high-quality Canvas/WebGL
implementations, print/metal vector output. The binary specifications and
golden vectors are shared, not reimplemented by guesswork.

React/Next.js and WebGL consumers should use the canonical public identifier as
a stable cache key and include the rendering profile/version in cache keys.
Canvas/WebGL textures can be rendered lazily for graph nodes, with deterministic
fallback SVG while loading.

### 3.2 Plugin/capability registry contract (planned)

Each registered implementation SHALL advertise:

- `id`, `version`, `category` (`lossless`, `identity`, `archival`), `maturity`.
- `inputTypes`, `allowedSensitivity`, `reversible` boolean.
- `outputMediaTypes`, `maxInputBytes`, `maxOutputBytes`, `async`, `offlineSafe`.
- `integrityType`, `errorCorrectionType`, `capacityModel`, `determinism`.
- `specUri`, `specDigest`, `wordlistDigest`, golden-vector-set version.
- A renderer MAY advertise scale, palette, animation, and aesthetic parameters.

`CATALOGUE` in the initial patch is an intentionally simple static foundation.
Planned entries MUST NOT be returned as executable capabilities.

## 4. Data model and deterministic public identity

### 4.1 Canonical typed input

The source object consists of exact bytes and validated ASCII context:

```ts
interface CanonicalPublicValue {
  namespace: string; // stable, lowercase, ASCII, e.g. "danceflow"
  kind: string;      // e.g. "node-id", "public-key", "address"
  bytes: Uint8Array; // original binary data, not JS strings or hex text
}
```

Transport adapters MUST normalise *before* producing this object. No silent
Unicode normalisation, case-folding of opaque addresses, byte-order inversion,
hex-prefix stripping or interpretation of network addresses occurs in core.
Future contextual types should explicitly distinguish network, curve, key form,
HRP, derivation path, and descriptor/policy version.

### 4.2 Public identity SHA-256 v1 — implemented

Define `u32be(n)` as exactly four bytes, most significant byte first.
`UTF8(x)` is the UTF-8 byte sequence of the ASCII-validated context string.
The exact preimage is:

```text
UTF8("ByteFables:public-identity:v1\0")
|| u32be(len(namespace)) || UTF8(namespace)
|| u32be(len(kind))      || UTF8(kind)
|| u32be(len(payload))   || payload
```

`identityDigest = SHA-256(preimage)`. No salt or randomness is used. Each
field is length-prefixed, preventing concatenation ambiguities. This represents
**public identity derived from bytes**, not proof that those bytes contain
sufficient secret entropy.

`identityFingerprint = "bf1-" || lowercase_hex(first K digest bytes)` with
`K` between 12 and 32, default 12. Default fingerprint size is therefore 96
bits; birthday collisions remain possible around 2^48 random samples, much
lower with adversarial/favourable prefix searches. Never use the short form as
the lookup key for an authorisation decision.

A 5x5 mirrored pixel avatar uses:

```text
avatarSeed = SHA-256(UTF8("ByteFables:pixel-avatar:v1\0") || identityDigest)
```

The current renderer uses 15 mirrored on/off cells and a constrained colour
scheme. Many digest values lead to visually similar or identical images;
**visual entropy is far smaller than 256 bits**. Renderer version is fixed.

### 4.3 Future public-art families

Prioritise a style registry containing:

- Pixel identicons (5x5, 7x7, 9x9) and vector polygon symmetries.
- LifeHash, Randomart, Blockies, Jdenticon-style patterns (only with appropriate
  licensing, compatibility labels and pinned reference versions).
- Character assemblers: animals, robots, masks, mythic creatures and props.
- Procedural heraldry, sigils, landscapes, constellations, L-systems, mandalas,
  fractals, reaction-diffusion and layered material motifs.
- Motion/sound/haptic identity renderers: beat-derived motions or animated
  orbs as optional *perceptual views*, not bit-exact identities.
- Themed identity cards combining avatar, typed icon, short readable phrase,
  full identifier, QR for the PUBLIC identifier, and namespace metadata.

Colour, complexity, symmetry, animation and palette are **presentation options**
that cannot accidentally change identity derivation. If a renderer option changes
pixel output, it belongs in the style-versioned cache key.

### 4.4 Collision and user experience requirements

Short captions and icons can collide. The system retains and exposes the full
public identifier and uses collision-resolution or namespace-aware registry keys
where unique user-readable aliases are required. For identity comparisons,
show the full digest or use the network's own authenticated identity protocol.

Stress-test 100,000+ seeded public identifiers for rendering crashes, shape
clustering and unintentional bias; do not infer cryptographic collision
resistance from an avatar's appearance.

## 5. Lossless byte representations

The general lossless service takes `Uint8Array` and produces a versioned format.
All adapters MUST preserve leading zeroes and exact byte count, reject invalid
characters and noncanonical tail bits, and return typed error classifications.

### 5.1 Initial codecs — implemented

**Hex:** two lowercase hex digits per byte; no prefix, spaces or delimiter in
canonical form. Decoder accepts uppercase ASCII digits but rejects odd length,
whitespace and `0x` prefixes.

**RFC 4648 Base32:** 5 bits per symbol, uppercase alphabet
`ABCDEFGHIJKLMNOPQRSTUVWXYZ234567`, no `=` padding, and strict residual-bit
validation. Not Bech32 or Crockford Base32; use explicit codec IDs.

### 5.2 Standard-format adapters — planned

| Family | Compatible use | Required validation |
|---|---|---|
| BIP-39 | Standard 128–256-bit entropy mnemonic | Exact English wordlist; checksum; NFKD; 12/15/18/21/24 lengths; PBKDF2 tests |
| SLIP-39 | Grouped threshold secret backup | RS1024, group/member thresholds, passphrase and extension flags, full vectors |
| Bytewords | Human transcription of structured bytes | Exact 256-word codebook, CRC-32 and normal/minimal style |
| UR v2 | Typed CBOR payloads via QR optical transport | Type and CBOR registry, fragment ordering, fountain decoder |
| Bech32/Bech32m | Correct *specific* typed address/payload usage | HRP, witness version and distinct checksum rules |
| SeedQR | Existing wallet seed scanning formats | Real hardware-wallet interoperability, zero/padding semantics |
| Codex32 | Error-correcting seed/share strings | BCH error/correction guarantees and cryptographic review |
| Formosa | BIP-39-compatible themed mnemonic sentences | Exact theme, 33-bit grouping, checksum and wallet interoperability |

BIP-39's 24 words carry 256 entropy bits + 8 checksum bits; its seed derivation
produces 512 bits but the original mnemonic does not preserve arbitrary 512-bit
input. ByteFables MUST not silently substitute one concept for another.

Every adapter is responsible for explicit object and chain context. A raw
wallet seed may not capture multisignature policy, derivation paths, scripts or
other recovery metadata. That data must travel with an archival record.

## 6. Grammar-aware reversible sentences

### 6.1 Goals and definitions

A *grammar pack* defines multiple templates, dictionaries, slot bit widths,
static filler tokens and a deterministic decoder. A *semantic theme* can include
frequency/time, emotion, character, action, place, machines, and mythology.

Grammar creation is not free-form LLM completion at encoding time. An LLM MAY
suggest codebook words, but all emitted choices MUST come from a frozen,
validated and uniquely decodable vocabulary. Creative language is compiled into
a fixed code, not trusted to invent decodable information.

### 6.2 Capacity equation and grammar selection

For one grammar with independent slots of sizes `2^b1 ... 2^bn`:

```text
slot_bits = sum(bi)
```

If a pack has `2^s` templates, **all with identical slot capacity**, and the
decoder distinguishes templates unambiguously, their *template choice can carry*
`s` additional bits:

```text
bits_per_sentence = s + slot_bits
```

This is not free entropy. A selector bit comes from the input bitstream and
chooses one of the templates. A hash-based aesthetic chooser that does *not*
transmit its choice may provide variety but cannot be counted as extra payload
bits without a separately proven invertible mapping.

For non-power-of-two lists and conditional dictionaries, use a formally
specified enumerative/range coder or enforce equal-size branch sets. Arbitrary
modulo indexing is biased and often non-injective. Dynamic grammatical choices
must have a provable inverse and exact bit-count model.

### 6.3 Initial demo grammar — implemented

The built-in `bytefables-demo/v1` pack has two templates (1 selector bit):

```text
0: The [adjective:4] [animal:4] [adverb:4] rests.
1: At dawn the [adjective:4] [animal:4] [verb:4].
```

Each bracketed slot is a frozen, ordered **16-unique-word** dictionary (4
bits). This yields `1 + 4 + 4 + 4 = 13` bits per sentence. `The` and `At`
are mutually exclusive first tokens and make the structure decodable. Filler
words such as `dawn` and `rests` carry zero bits in this version.

A legal codeword yields `The silly snail sometimes rests.`. A full exhaustive
test checks that 8,192 distinct 13-bit codewords produce 8,192 distinct
sentences and that decoding reconstructs the exact codeword.

This proof does not establish naturalness of every combination, security,
error-correcting strength or compatibility with existing wallets.

### 6.4 `BYTEFABLES-STORY-PROTOTYPE-1` wire format — implemented

This is deliberately **not the future canonical archival format**. It exists
to test framing and reversible grammar structure with public sample bytes.

```text
text-file:
  line 1  = ASCII "BYTEFABLES-STORY-PROTOTYPE-1"
  lines 2...n = one grammar-generated sentence per line

binary envelope (before the 13-bit word mapping):
  4 bytes  ASCII BFBL
  1 byte   version = 0x01
  4 bytes  original byte length, unsigned big-endian
  N bytes  exact source payload
  4 bytes  IEEE CRC-32 (big-endian) of all preceding envelope bytes
```

Convert envelope bytes to MSB-first bits, split into 13-bit chunks and append
zero padding only to the final chunk. Decoder validates the text label,
marker/word/grammar, magic, format version, size (max 4,096 bytes), *exact*
expected sentence count, zero padding, and CRC-32. CRLF is accepted in place of
LF. It returns raw bytes, without pretending to reconstruct namespace/type.

Required bits for an `N`-byte payload:

```text
B = 8 * (13 + N)
S = ceil(B / 13) sentences
```

A 256-bit (32-byte) public payload therefore needs `360` envelope bits and
`28` sentences with this intentionally small dictionary. This is not a
competitive mnemonic density; it is a falsifiable demonstration of the design.

CRC-32 detects many accidental changes but an adversary can recompute it.
It is **not a MAC, digital signature, secure hash commitment or guarantee**.

### 6.5 Grammar compiler invariants

Compiler MUST reject:

- Invalid IDs/versions and unsupported lexicon representations.
- Any duplicate word within a data-bearing category, including case-folded
  duplicates when case-insensitive decoding is supported.
- Overlapping structural markers or productions that parse ambiguously.
- Non-power-of-two slot sizes in the simple block-indexing encoder.
- Templates with different capacities if they share a uniform selector.
- Grammar parts with noncanonical punctuation/spaces or undefined inflections.
- Context-dependent dictionaries that shrink below promised capacity.
- Codebooks with unbounded lengths or inappropriate memory costs.

Compiler SHOULD additionally report homophones, edit-distance near misses,
semantically odd combinations, script confusables and cross-language ambiguity.
Such warnings are usability aids, not substitutes for formal injectivity tests.

### 6.6 Future variable-capacity sentence scheduling

Add grammar options with different lengths/capacities and build a bounded,
versioned packet framing scheme. A dynamic programming scheduler can select a
sequence of grammar capacities to minimise weighted cost:

```text
cost = A * word_count + B * spoken_duration
     + C * ambiguity_score + D * layout_width
```

It must still encode the grammar choices unambiguously, account for headers,
length, version, checksum/ECC and final padding, and guarantee the inverse.
Prove that every admitted bitstring has exactly one decoding under a pack
version. Constrain search complexity and runtime, particularly for long keys.

Do not claim the entire phrase encodes 256 bits merely because a hash was used
to *seed* the choice: count every recoverable bit and collision in the actual
output space.

## 7. Future archival envelope and recovery pipeline

Secret and public archival require a more general format than the demo. Define
an interoperable, versioned envelope containing:

| Field | Requirement |
|---|---|
| Magic, schema version, format ID | Distinguish all editions and decoders |
| Object class and network | Prevent address/seed/public-key confusion |
| Original byte length | Preserve arbitrary binary including leading 0 |
| Payload | Raw bytes or standard-native structure, explicitly identified |
| Recovery metadata | HD path, wallet descriptor/policy, share IDs, derivation metadata when needed |
| Integrity | Strong accidental-error detection; cryptographic integrity only when authenticated appropriately |
| Correction parameters | Reed–Solomon/BCH/UR fragmentation parameters as applicable |
| Provenance | Reference implementation, codebook IDs/digests and specification version |

Unknown versions, unrecognised critical fields or incompatible network metadata
must cause a hard failure. The plaintext envelope itself does not encrypt
secrets. Encryption, passphrases, threshold shares, and paper/media security
must be explicitly scoped and user-visible.

### 7.1 Error models and recovery

Distinguish substitution, insertion, deletion, erasure, burst damage, faded
QR patches, swapped sheets, lost fragments, misread homophones, and malicious
replacement. CRC, SHA hashes, ECC, threshold sharing and authenticated
signatures provide different guarantees and MUST be described separately.

Automatic repair for secret backups is hazardous: valid-but-wrong recovery is
potentially worse than a detected failure. Present suggestions and demand
independent recovery confirmation before claiming a wallet is restored.

### 7.2 Medium adapters

- QR Code with explicit ECC level, dimensions and quiet-zone constraints.
- Data Matrix, Aztec and PDF417 where they improve durability or density.
- SeedQR for its specific seed format, not arbitrary binary substitution.
- Typed UR v2 fountain-fragmented QR for larger outputs.
- Printable archival sheets with human text, optical fallback and metadata.
- Vector stamping/laser engraving templates; metal plate min-line and wear
  tests; emboss/punch/perforation and tactile encodings for accessibility.

Every medium adapter needs round-trip *capture* tests using actual scans or
photographs, not just encoder/decoder round trips in memory.

## 8. Size and format matrix

The general pipeline accepts arbitrary data length, with explicit storage and
resource limits. Optimise codec presets and tests for frequently used lengths:

| Bits | Bytes | Example typed object |
|---:|---:|---|
| 128 | 16 | BIP-39 entropy, 12-word mnemonic input |
| 160 | 20 | Ethereum address, Bitcoin HASH160 |
| 192 | 24 | BIP-39 entropy, 18-word mnemonic input |
| 224 | 28 | BIP-39 entropy, 21-word mnemonic input |
| 256 | 32 | SHA-256, secp256k1 scalar, Ed25519 seed, many public IDs |
| 264 | 33 | Compressed secp256k1 public key |
| 384 | 48 | BLS12-381 public key in common Ethereum consensus convention |
| 512 | 64 | SHA-512, certain Ed25519 keypair byte forms or signatures |
| 520 | 65 | Uncompressed secp256k1 public key |
| 624 | 78 | Binary BIP-32 extended key payload |
| 768 | 96 | BLS12-381 signatures in common conventions |
| Variable | Variable | Descriptors, multisig, certificates, PQ key objects |

**Never identify a key type based on length alone.** A 32-byte hash is not a
Bitcoin private key, an Ethereum address, or a BIP-39 mnemonic simply because
it has a familiar size. BIP-39 derives seeds from entropy using its own
checksum/wordlist and KDF rules; the 512-bit seed is a different object.

Larger post-quantum objects demand chunking, efficient binary optical formats,
and bounded memory; sentence stories may be optional or impractically long.

## 9. Functional and non-functional requirements

### 9.1 Reliability

- Every reversible format: `decode(encode(bytes)) == bytes` on all supported
  byte lengths and randomized/property-tested cases.
- Each published grammar pack: exhaustive bijection test when feasible;
  compiler proof plus property tests otherwise.
- Each new renderer: pinned deterministic vectors across Node/browser/Python
  as appropriate; raster-output comparison tolerances explicitly recorded.
- Corrupted inputs: reject errors, never silently truncate, wrap, reorder or
  canonicalise unknown data.
- Stable identifier context: string and byte interpretation explicit.

### 9.2 Accessibility, design and performance

- SVGs remain legible at 16/32/64px, support dark/light backgrounds, and avoid
  relying on colour alone for identity verification.
- Print representations have human-readable fallback, sufficient contrast and
  QR sizing/quiet-zone guidance.
- Renderers should degrade gracefully to stable simple shapes in performance-
  constrained graph visualisers; heavy GPU artwork can be generated on demand.
- Public identity hashing is bounded (current maximum 1 MiB); prototype story
  payload is bounded to 4 KiB. Raise limits only with explicit use-case tests.
- Rendering must be deterministic and not use wall clock, unseeded RNG,
  locale-dependent ordering, installed fonts or platform-specific layout as an
  unrecorded input.

### 9.3 Compatibility and distribution

- ESM TypeScript/JavaScript first; no runtime dependencies for foundation.
- Build, type-check and run unit tests in Node 20/22 CI.
- Explicit package/version management, changelog and golden vectors before
  first public non-experimental package release.
- Stable REST/MCP/React adapters for DanceFlow once the core contracts settle.
- No silent system-wide installation, external model download, key export,
  destructive repository operation, or automatic deployment in library APIs.

## 10. Trust, verification and release policy

Initial public identity and experimental story are suitable for controlled
public-data demonstrations. **No production secret-handling declaration** until
independent review, standard conformance, complete recovery simulations,
network/descriptor metadata testing, memory/supply-chain controls, and a secure
user workflow have evidence.

Test categories, in order:

1. Strict canonical parsing and byte-exact round trips.
2. Negative/edge tests for zero length, leading zeroes, boundary sizes, invalid
   words, mixed encodings, noncanonical pad bits, and overlong input.
3. Exhaustive grammar decode uniqueness for small fixed packs.
4. Published cross-language golden vectors for stable output formats.
5. Mutation/property fuzzing of decoders and compiler (resource limits).
6. Statistical collision and visual-distinguishability studies (non-security).
7. Printed/scanned/engraved recovery under damage and user transcription.
8. Independent interoperability tests for BIP/SLIP/UR/QR and separate security
   audit before secret support.

## 11. Phasing and open decisions

See [the staged plan](IMPLEMENTATION_PLAN.md) for dependencies and exit gates.
Before the first interoperable archival release, settle:

- Future full binary envelope (CBOR/UR-first versus a compact independent
  canonical format); avoid creating a private standard unnecessarily.
- Exact network/type registry and namespace assignment rules.
- Grammar-pack portability: canonical JSON/CBOR, signed/hash-pinned dictionaries,
  multilingual display and speech-confusable policy.
- Efficient range/enumerative coding for arbitrary dictionary cardinalities.
- Default public identity format and acceptable visual collision rate for
  node-count targets (10^4 / 10^6 / 10^9).
- Whether standalone Python package, WASM interop or native TS-only API should
  own authoritative golden-vector generation.
- Security handling of deliberate secret-backup use cases and scope for
  independent review; not to be inferred from prototype success.

The initial deliverable is intentionally small enough that a future format
review can change the archival design without breaking published wallets.
