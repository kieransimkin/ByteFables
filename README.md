# ByteFables

**Deterministic representations for unique bytes.**

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
- `planned`: BIP-39, Bytewords/UR, QR/SeedQR, SLIP-39, advanced grammars, ECC,
  archival templates, and more avatar renderers. These are NOT implemented.

Neither generated text nor a visual icon proves ownership, authorisation,
non-repudiation or exact identity. Use original public keys/full hashes and
cryptographic verification for those decisions.

See [the design](docs/DESIGN.md), [the staged roadmap](docs/IMPLEMENTATION_PLAN.md),
[output-format atlas](docs/OUTPUT_FORMAT_ATLAS.md),
[composable rendering/export pipeline](docs/OUTPUT_PIPELINE.md),
[October 2026 research survey](docs/RESEARCH_SURVEY_2026-10.md),
[security policy](SECURITY.md), and [reference catalogue](docs/REFERENCES.md).

The expanded roadmap now covers lossless text, key standards, QR/industrial
barcodes, animation, public 2D/3D avatars, WebGL/Unity sprites, print/metal,
audio/LED/NFC, accessibility and speculative storage media. **Those formats are
planned/researched, not implemented** by the first TypeScript foundation.

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

The current package has `"private": true` to prevent accidental publishing of
an experimental format. Published packages and their codebooks will require
versioned stability and independent test vectors first.

## Example

```ts
import {
  ByteValue, identityFingerprint, renderPixelAvatar,
  encodeBase32, decodeBase32,
  encodeExperimentalStory, decodeExperimentalStory
} from 'bytefables';

// Public node ID, never an undisclosed secret.
const node = ByteValue.public(Uint8Array.of(0, 1, 2, 255), {
  namespace: 'danceflow',
  kind: 'node-id'
});

const fingerprint = await identityFingerprint(node); // bf1-... (96 bits)
const svg = await renderPixelAvatar(node, { size: 128 });
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
  identity/                public fingerprints and SVG avatar renderer
  grammar/                 compiling grammar packs, sentence and story demo
  utils/                   strict binary helpers and CRC32
  catalogue.ts             explicit maturity and safety inventory
  index.ts                 public TypeScript interface
docs/
  DESIGN.md                normative direction and architecture
  IMPLEMENTATION_PLAN.md  milestones, dependencies, exit criteria
  REFERENCES.md           standards and source references
SECURITY.md                threat model and security support policy
tests/                    native Node test runner
examples/                 public-input-only sample
.github/workflows/ci.yml  build/typecheck/tests, Node 20 and 22
```

## Contribution rules

Keep wire encodings deterministic and strictly versioned, preserve zero bytes,
compile-time validate all grammar codebooks, and add golden vectors and
round-trip tests for every new codec. No secret-processing adapter should be
advertised before its threat model, test-vector conformance, offline workflow,
and review requirements have been met. See the staged plan.
