# ByteFables

**Deterministic representations for unique bytes, rendered through FrameRudiments.**

ByteFables is a planned DanceFlow ecosystem tool for reversible, human-readable
binary encodings, deterministic public identity visuals, and eventually
independently tested archival recovery formats. The first implementation is a
**TypeScript foundation** and proof of concept, not a wallet-backup product.

## Status and safety

- `foundation`: byte-exact hex and RFC 4648 unpadded Base32; domain-separated
  SHA-256 public identity digests, 96-bit minimum abbreviated fingerprints, and
  deterministic SVG pixel avatars.
- `experimental`: an exactly reversible but intentionally inefficient **13-bit
  sentence codec** using a typed grammar pack and CRC-32 for accidental errors.
  It refuses ByteFables values marked secret. It is **not BIP-39**, is not
  wallet interoperable, and is not recommended for private key archival.
- `foundation Wave A`: canonical public CBOR records, validated format registry,
  binary matrix and vector scene IR, a public CLI, and a declarative integration
  with the existing FrameRudiments renderer/effect pipeline.
- `experimental Stage 2`: six immutable thematic vocabularies, exact
  **33–35-bit** prefix-coded sentences, a separate **24/32/40-bit**
  DP-scheduled story profile, conditional grammar, explicit verb-agreement
  dictionaries, mixed-radix coding, and unkeyed SHA-256-128 integrity.
  These are **public raw-byte** codecs only, not wallet backups or BIP-450.
- `Stage 3 public standard codecs`: RFC 9285 Base45, RFC 4648 Base64/Base64url,
  Crockford Base32+check, Base58Check with mandatory version, Bech32/Bech32m,
  Multibase, and full/URI/minimal Bytewords with CRC-32. Experimental PUBLIC
  BIP-39 English entropy fixtures and `ur:bytes` single-part testing only;
  **no production wallet mnemonic or key recovery API**.
- `planned`: SLIP-39, real wallet-qualified BIP-39/SeedQR, registered multipart
  UR/fountain workflows, QR symbol generation/ECC and archival templates.

Neither generated text nor a visual icon proves ownership, authorisation,
non-repudiation or exact identity. Use original public keys/full hashes and
cryptographic verification for those decisions.

See [the design](docs/DESIGN.md), [the staged roadmap](docs/IMPLEMENTATION_PLAN.md),
[the public CBOR specification](docs/specs/bytefables-public-record-v1.md),
[FrameRudiments integration](docs/specs/frame-bridge-v1.md),
[reversible story v2 specification](docs/specs/story-v2.md),
[Stage 3 interoperable public codecs](docs/specs/standard-codecs-v1.md),
[output-format atlas](docs/OUTPUT_FORMAT_ATLAS.md),
[composable rendering/export pipeline](docs/OUTPUT_PIPELINE.md),
[October 2026 research survey](docs/RESEARCH_SURVEY_2026-10.md),
[security policy](SECURITY.md), and [reference catalogue](docs/REFERENCES.md).

The expanded roadmap now covers lossless text, key standards, QR/industrial
barcodes, animation, public 2D/3D avatars, WebGL/Unity sprites, print/metal,
audio/LED/NFC, accessibility and speculative storage media. **Those formats are
planned/researched, not implemented** by the first TypeScript foundation.

## Stage 3 — standards interoperability (public-only)

The canonical codec registry now exposes reversible Base45, Base64,
Base64url, checked Crockford Base32, Multibase and Bytewords normal/URI/minimal.
Base58Check and Bech32(m)/SegWit are provided as separate typed APIs because
network/address context must be explicit. The frozen official BIP-39 English
wordlist supports **PUBLIC TEST entropy only**, gated as experimental in the
format manifest. One single-part `ur:bytes` fixture codec is also test-only;
UR multiplexing and registered UR types have not shipped.

```sh
npm run check
node bin/bytefables.mjs encode-public --confirm-public \
  --public-hex 000102ff --namespace danceflow --kind node-id \
  --format codec/bytewords-minimal
node bin/bytefables.mjs decode-public-text --confirm-public \
  --format codec/base45 --text BB8
```

Read the [Stage 3 specification](docs/specs/standard-codecs-v1.md) before using
any of these. **Never input a real wallet mnemonic, private key, seed, or
passphrase.** A checksum detects some corruption but is never authorization.

## Stage 2 — structured sentence encodings (public-only)

There are now **two independently versioned, experimental** story encodings:

- `BYTEFABLES-STORY-V2`: four grammar variants carrying 33/34/35/35 bits
  per sentence (four 256-entry lexical choices plus actual prefix data bits).
- `BYTEFABLES-SCHEDULED-STORY-1`: explicitly marked 24/32/40-bit variants,
  selected using a bounded, deterministic DP schedule. Grammar selection is
  visible overhead, **not free data capacity**.

Six themed packs (`nature`, `technology`, `music`, `fantasy`, `science`,
`humour`) encode/decode exact arbitrary PUBLIC bytes up to 4,096 bytes. Both
formats use a different framed envelope and unkeyed SHA-256 integrity check;
no secret inputs, encrypted-wallet import, BIP-39 or BIP-450 interoperability.
They preserve raw bytes but not original node namespace/type metadata.

```js
const publicNode = ByteValue.public(Uint8Array.of(0, 1, 2, 255), {
  namespace: 'danceflow', kind: 'node-id'
});
const story = await encodeStoryV2(publicNode, 'nature');
const restored = await decodeStoryV2(story); // restored.bytes equals original bytes
const other = await encodeScheduledStory(publicNode, 'music');
const preview = await createFrameRudimentsStoryPreview(publicNode, 'music', {
  box: [0, 0, 640, 120], fontSize: 18, maxSentences: 2
});
// preview.identities is a fragment for FrameRudiments project.identity;
// caller must provide a SHA-256-pinned project font. Preview is NOT reversible.
```

CLI for **public identifiers only**:

```sh
node bin/bytefables.mjs story-encode --confirm-public --public-hex 000102ff \
  --namespace danceflow --kind node-id --theme nature --profile prefix --stats
node bin/bytefables.mjs story-preview --confirm-public --public-hex 000102ff \
  --namespace danceflow --kind node-id --max-sentences 2
node scripts/story-vectors.mjs --check
```

ByteFables owns the reversible language codec, while **FrameRudiments remains
sole owner of text rasterisation, styled captions, compositor and effects**.
The optional preview helper never attempts to draw pixels or produce a rival
renderer. Complete stories must be saved separately from truncated previews.

## Wave A extension: robust watermark operation (planning only)

ByteFables now also models a **fourth operation family, watermarking**: applying
an optional, human-imperceptible *public* hash reference to a separate carrier.
Image, audio, video and generator-controlled text targets have distinct planned
embedding and extraction profiles. This is **not** a working invisible watermark
engine: none of the four embedder/detector adapters has shipped, and no
robustness, undetectability, recovery rate or authenticity is claimed.

The shipped Wave A API can create and decode an exact `BFWM` message (version,
96/128/256-bit prefix of a typed public record digest, IEEE CRC-32). The
message is not itself a watermark, and the checksum is not authentication.
It can also produce conservative carrier feasibility *research plans*, with
expected bit budget, distortion test classes and a public-only host binding:

```ts
const message = await encodePublicWatermarkMessage(record, 12);
const restoredMessage = decodePublicWatermarkMessage(message);
const candidateMatches = await matchesPublicWatermarkMessage(message, record);
const candidate = await planPublicWatermark(record, {
  kind: 'image', mimeType: 'image/jpeg', width: 1920, height: 1080
});
// candidate.status === 'planning-only'; embedderAvailable === false
```

Or use the metadata-only CLI:

```sh
bytefables watermark-plan --confirm-public --public-hex 000102ff \
  --namespace danceflow --kind node-id --carrier image \
  --mime-type image/jpeg --width 1920 --height 1080
```

The public record must already exist in the code sample above. No private
keys, secrets or wallet backups may enter the shared renderer. Actual embedder
and extractor effects are to be developed in **FrameRudiments**, reusing its
native effect graph and video/audio timebase; ByteFables owns only typed message
framing and capability planning. For threat assumptions, carrier-specific
limits and independent testing see [watermark protocol and staged tests](docs/specs/watermark-v1.md).

## Experimental hash-to-image model profiler

Each **PUBLIC** hash bit maps to a fixed binary visual feature choice: e.g.
spiky/smooth, dark/bright, muted/saturated. A compact local LLM receives the
selected choices **without the raw hash** and writes image prompts. Compare
small prompt writers against locally installed tiny image diffusion models,
controlled noise seeds, counterfactual single-bit flips, feature budgets,
prompt coverage and independently measured visual attribute agreement.

- `bytefables visual-features ...` emits the complete frozen bit-feature ledger
  and a baseline prompt for public bytes.
- `python -m tools.hash_image_bench prepare ...` saves baseline candidates and
  paired bit-flip experiments.
- `write-prompts` calls only an explicitly supplied loopback OpenAI-compatible
  LLM server and persists raw replies and prompts.
- `render` uses existing local Diffusers checkpoint directories (no auto-
  downloads) and requires explicit `--execute` for inference; missing weights
  or GPU are reported, not simulated.
- `score-clip` is an **optional proxy**, `report` supports imported independent
  blinded binary evaluations, and `host-assets` writes checksum-pinned
  FrameRudiments sprite layer fragments without a competing render engine.

All output is **identity-only, NOT reversible binary art or a wallet backup**.
See [experimental specification](docs/specs/hash-image-benchmark-v1.md),
[compact-model research](docs/IMAGE_MODEL_RESEARCH.md) and
[example local checkpoint configs](experiments/tiny-image-models.example.json).


## Experimental fractal seeding (PUBLIC hashes only)

ByteFables now prepares versioned hash-derived fractal parameters and registers
`bytefables-fractal-v1` into **FrameRudiments'** existing source/effects pipeline.
Four CPU experimental generators (Julia, Burning Ship, IFS fern, fractal fBm)
use eight named opposing binary features; all remaining public hash bytes
influence the deterministic avalanche seed, but **no image is reversible**.

A new `render-fractals` benchmark command compares original/one-bit-flip sources
under two seeding policies: `avalanche` (new hash = new seed) and `axis-isolated`
(fixed source seed to measure just the first eight feature controls). PNG receipts,
independent checksums, per-family diagnostics, pairwise differences and an
offline gallery are produced. It runs locally on CPU without downloading model weights.

The optional local image-model runner also supports SD/SDXL-only experimental
`--latent-policy fractal-spectral` (correlated initial noise) and
`--conditioning-policy fractal-img2img` (a checksum-verified source fractal
image). **Both require independent GPU/quality experiments; neither has been
validated to improve outputs**. They must not be conflated with reversible key
storage, credential creation, watermarking, or image identity authentication.

See [fractal-seeding contract, research, instructions and experimental controls](docs/specs/fractal-seeding-v1.md).

## Compact public identities — 3, 4 and 8 bytes

The standardised **leftmost SHA-256 truncation** method is used for compact,
version-labelled *display aliases*. ByteFables first hashes the entire typed
PUBLIC value with its unchanged domain-separated identity SHA-256, then takes
3/4/8 bytes. These aliases are 24/32/64 bits respectively; shorter forms are
prefixes of longer ones. The original full public identity remains authoritative.

```sh
npm run build
node bin/bytefables.mjs short-hashes --confirm-public --public-hex 000102030405060708090a0b0c0d0e0f101112131415161718191a1b1c1d1e1f --namespace danceflow --kind node-id
node bin/bytefables.mjs visual-features --confirm-public --public-hex 000102030405060708090a0b0c0d0e0f101112131415161718191a1b1c1d1e1f --namespace danceflow --kind node-id --derive-short-bytes 3 --prompt-bits 24
python -m tools.hash_image_bench prepare --confirm-public --public-hex 000102030405060708090a0b0c0d0e0f101112131415161718191a1b1c1d1e1f --short-hash-bytes 8 --output _work/short-image-64
```

Directly supplied 3-, 4- and 8-byte PUBLIC hashes also work in the existing
semantic feature planner and image/fractal benchmark paths. The default prompt
budgets adapt to 24/32/64 bits. No short alias is collision-proof or a suitable
cryptographic verifier, and expanding it into a 64-bit noise seed does not
restore information lost by shortening. See
[the normative format specification](docs/specs/short-public-hashes-v1.md).

## Next optical and avatar batch — public-only

A `ur:bytes` **test-only**, standards-reference-aligned multipart/fountain
transport is available, including a bounded streaming decoder, harmonic
fragment selection and QR matrix handoff into FrameRudiments. The `bytes` UR
type is reserved for interoperability testing, **not production wallet use**.
For real typed public records, the separately versioned `BFQR1` transport
remains the native experimental choice.

The registered FrameRudiments artwork generator now supports **nine**
procedural families: sigil, constellation, heraldry, topography, crystal,
mandala, cellular automata, branching, and orbital. They are not recoverable
hash encodings or cryptographic authentication.

The `public-print-sheet` CLI produces a declarative BFQR1 page plan; the
FrameRudiments `bytefables-public-card-v1` generator renders each page with a
SHA-256-pinned font, 4-module white QR quiet zone, full public fingerprint and
complete manual fallback text. `scripts/render-public-cards.py` exports 300dpi
PNG pages and independently scans each saved PNG when OpenCV is available.
**No private keys, private wallet backups, PDF/A or physical durability are
qualified by this experimental feature.**

See [multipart UR test profile](docs/specs/ur-multipart-public-test-v1.md),
[printable public cards](docs/specs/public-recovery-cards-v1.md), and
[identity art catalogue](docs/specs/public-identity-art-v1.md).

## Public video effects and hash-selected looks (FrameRudiments only)

The new [video-effect research atlas](docs/research/video-effects-methods-2026-10.md)
tracks **143** named techniques across 11 categories, with explicit
implemented-vs-research maturity. The accompanying
[effect implementation plan](docs/VIDEO_EFFECTS_IMPLEMENTATION_PLAN.md)
prioritises additions to the **FrameRudiments host** instead of copying any
compositor or shader into ByteFables. The validated
[`video-effects-v1` inventory](manifests/video-effects-v1.json) is discovery
metadata, not 143 executable shaders.

ByteFables can select one of **16 public-only, deterministic VisualStyle recipes**
from a typed public-record digest and emit native `post_effects` fragments:

```sh
node bin/bytefables.mjs video-effects --family transitions --json
node bin/bytefables.mjs video-look --confirm-public \
  --public-hex 000102ff --namespace danceflow --kind node-id \
  --look neon-bloom --intensity 0.8 --target layer:public-avatar
```

Integrators merge the returned stage array into an already validated
FrameRudiments project. `--target frame` is for ordinary decoration **only**;
apply effects to `layer:public-avatar` instead of entire frames when QR or
other machine-readable recovery areas are present. See the
[versioned API contract](docs/specs/public-video-looks-v1.md) for exact
selection, security boundaries, and limits. A style is not a reversible
identity or proof of ownership. Actual new rendering algorithms belong in
FrameRudiments, not this tool.

## Large English lexicons and high-capacity public stories (experimental)

The 27 October 2026 research import adds **16,396 aligned nouns**, **10,569
adjectives** and **3,554 unique past-tense transitive verbs** in separately
pinned US and UK written-English dictionaries. Region-specific spelling maps
to the same conceptual index; the full source lists are kept under
`src/grammar/wordlists/large-v1/`, with independently checked SHA-256 digests.

The new **BYTEFABLES-LARGE-STORY-V1** format carries 68 actual source bits per
sentence (66 mixed-radix lexical bits, plus two template-selector bits), with
SHA-256-128 accidental integrity and strict bit-exact public-data decoding. It
does **not** replace the earlier story packs or create a private-key backup.
See [large lexicon and binary grammar specification](docs/specs/large-story-lexicons-v1.md).

```sh
node bin/bytefables.mjs story-large-lexicons
node bin/bytefables.mjs story-large-encode --confirm-public \
  --public-hex 00010203 --namespace danceflow --kind node-id --locale en-GB --raw > story.txt
node bin/bytefables.mjs story-large-decode --confirm-public --story-file story.txt
```

## Development

Requires Node.js >=20 and TypeScript 5.8.3. There are no runtime dependencies.

```sh
npm ci --ignore-scripts
npm run check
node examples/demo.mjs
```

To test using an existing TypeScript installation without installing dependencies:

```sh
tsc -p tsconfig.json
node --test tests/*.test.mjs
```

FrameRudiments is ByteFables' **only production graphics and effects engine**.
The historical `renderPixelAvatar` API remains for backward compatibility, and
new scene/matrix formats produce validated data for the native host. New reusable generators are registered
into FrameRudiments' existing renderer registry; post-processing, visualisers,
shader effects, time sampling and export live in FrameRudiments, not ByteFables.

An optional native FrameRudiments adapter is available under
`integrations/framerudiments/`, with a public-only fragment generator:

```sh
npm run build
node bin/bytefables.mjs framerudiments-layer --confirm-public \
  --public-hex 000102ff --namespace danceflow --kind node-id \
  --id avatar-one --bounds 0,0,128,128 --palette neon
```

See the [bridge instructions](docs/specs/frame-bridge-v1.md) to register the
Python factories with the FrameRudiments host. The bridge has synthetic tests;
full installed-host FFmpeg/effect acceptance is a subsequent integration gate.
It does not render wallet secrets or provide a production image export API.

The Python generator contract can be checked separately with:

```sh
python -m unittest discover -s tests/python -v
```

The current package has `"private": true` to prevent accidental publishing of
an experimental format. Published packages and their codebooks will require
versioned stability and independent test vectors first.

## Example

```ts
import {
  ByteValue, PublicRecord, identityFingerprint,
  createFrameRudimentsIdentityLayer, encodeBase32, decodeBase32,
  encodeExperimentalStory, decodeExperimentalStory
} from 'bytefables';

// Public node ID, never an undisclosed secret.
const node = ByteValue.public(Uint8Array.of(0, 1, 2, 255), {
  namespace: 'danceflow',
  kind: 'node-id'
});

const fingerprint = await identityFingerprint(node); // bf1-... (96 bits)
const frameLayer = await createFrameRudimentsIdentityLayer(
  new PublicRecord(node), { id: 'node-identity', bounds: [0, 0, 128, 128] }
); // Add to a FrameRudiments project with registered factories.
const text = encodeBase32(node.toBytes());
const recovered = decodeBase32(text);

// Experimental proof of reversible grammatical structures only.
const story = encodeExperimentalStory(node);
const roundTripped = decodeExperimentalStory(story);
```

## Why ByteFables?

Instead of representing an object by only a hexadecimal digest, ByteFables
plans multiple interchangeable views: a recoverable printed backup, a
pronounceable story, a geometric fingerprint, a character avatar, or a compact
human verification block. These serve **different purposes** and must not be
confused with each other.

The project draws inspiration from Helium's Angry Purple Tiger, the related
Sometimes Silly Snail fork, BIP-39, Formosa's themed sentences, Blockchain
Commons LifeHash/Bytewords/UR, and optical error-correcting codes. Compatibility
with those systems will always be called out individually; inspiration does not
imply format compatibility.

## Repository map

```text
src/
  value.ts                 typed byte container, public/secret boundary
  codecs/                  basic lossless text representations
  identity/                public fingerprints and legacy-compatible SVG avatar
  engine/framerudiments.ts  typed public-only native renderer layer instructions
  framing/                 deterministic public CBOR envelopes
  registry/                versioned capability metadata and planner
  ir/                      binary module matrices and public vector scene data
  grammar/                 compiling grammar packs, sentence and story demo
  utils/                   strict binary helpers and CRC32
  catalogue.ts             explicit maturity and safety inventory
  index.ts                 public TypeScript interface
docs/
  DESIGN.md                normative direction and architecture
  IMPLEMENTATION_PLAN.md  milestones, dependencies, exit criteria
  REFERENCES.md           standards and source references
SECURITY.md                threat model and security support policy
integrations/framerudiments/  optional FrameRudiments Python renderer factories
manifests/                immutable checked format catalogue snapshot
tests/                    native Node and Python generator tests
examples/                 public-input-only sample
.github/workflows/ci.yml  build/typecheck/tests, Node 20 and 22
```

## Contribution rules

Keep wire encodings deterministic and strictly versioned, preserve zero bytes,
compile-time validate all grammar codebooks, and add golden vectors and
round-trip tests for every new codec. No secret-processing adapter should be
advertised before its threat model, test-vector conformance, offline workflow,
and review requirements have been met. See the staged plan.

## Public QR recovery transport and native identity artwork (next implementation batch)

A **PUBLIC-only** QR Model 2 generator (including public registry adapter) now supports versions 1–40, ECC
L/M/Q/H, deterministic masking, Reed–Solomon blocks, and the immutable
`ModuleMatrix` bridge to FrameRudiments' `bytefables-matrix-v1` factory.
ByteFables BFQR1 wraps its own checksummed, typed public-record CBOR in
printable sequence frames. Data frames may arrive in any order and optional
single XOR parity recovers **one missing data frame**. This is **not** URv2,
SeedQR, a secure backup, or proof of identity. See the complete
[public QR transport spec](docs/specs/public-qr-transport-v1.md).

```sh
npm run build
node bin/bytefables.mjs qr-public --confirm-public \
  --public-hex 0001020304050607 --namespace danceflow --kind node-id \
  --ecc Q --max-version 12 --fragment-bytes 48 > public-qr-frames.json

# Generate native FrameRudiments module layers (project must register the adapter).
node bin/bytefables.mjs qr-public --confirm-public \
  --public-hex 0001020304050607 --namespace danceflow --kind node-id \
  --include-layers > public-qr-layers.json

# Public QR session restoration from scanner text, not from PNG pixels.
node bin/bytefables.mjs qr-recover --confirm-public < public-qr-frames.json
```

The new **FrameRudiments identity-art source** adds four styles: `sigil`,
`constellation`, `heraldry`, and `topography`. The new generators share the
existing native renderer/effects pipeline and accept only a SHA-256-derived
public identity digest plus validated palette/complexity choices. Read the
[identity-art contract](docs/specs/public-identity-art-v1.md).

```sh
node bin/bytefables.mjs artwork-layer --confirm-public \
  --public-hex 000102ff --namespace danceflow --kind node-id \
  --artwork sigil --palette neon --complexity 4
```

Verification includes 56 independent QR-encoder grid comparisons spanning
versions 1–40 and four ECC levels, plus saved-PNG readback with OpenCV for a
specific sample rendered by the native FrameRudiments adapter. This does **not**
certify physical media durability, all scanner/device combinations or any
private-key backup. These are distinct release gates.

### Experimental large-story v2 (new wire format)

The new `BYTEFABLES-LARGE-STORY-V2` uses the immutable large US/UK dictionaries but includes eight canonical sentence structures and a computed written a/an determiner. It carries 69 source bits per sentence: 3 selector bits and 66 mixed-radix payload bits. See [the independent v2 specification](docs/specs/large-story-lexicons-v2.md). Story V1 remains byte-for-byte unchanged. The format is strictly public-data-only, not a wallet/secret backup or phonetic mnemonic.
