# Standards and research references

These are upstream specifications, not a list of implemented ByteFables
capabilities. Before releasing adapters, pin source revision and compare the
actual interoperability test vectors from the official project.

| Topic | Primary reference | Planned work |
|---|---|---|
| Bitcoin entropy mnemonic | [BIP-39](https://github.com/bitcoin/bips/blob/master/bip-0039.mediawiki) | Strict entropy sizes, checksums, NFKD, reference vectors, seeds |
| Hierarchical wallets | [BIP-32](https://github.com/bitcoin/bips/blob/master/bip-0032.mediawiki) | Chain codes, derivation paths, key type context |
| Wallet script reconstruction | [BIP-380 descriptor terminology](https://github.com/bitcoin/bips/blob/master/bip-0380.mediawiki) | Preserve wallet metadata independently of mnemonic |
| Mnemonic threshold sharing | [SLIP-39](https://github.com/satoshilabs/slips/blob/master/slip-0039.md) | Shares, RS1024, complete interoperable recovery |
| Sentence-structured wallet encoding | [Formosa / BIP-450](https://github.com/bitcoin/bips/blob/master/bip-0450.mediawiki) | Evaluate grammar/33-bit sentence compatibility; status must be rechecked |
| Raw byte-word encoding | [Blockchain Commons Bytewords](https://github.com/BlockchainCommons/Research/blob/master/papers/bcr-2020-012-bytewords.md) | Lexicon, CRC-32, normal/minimal styles |
| Offline optical transport | [UR v2](https://github.com/BlockchainCommons/Research/blob/master/papers/bcr-2020-005-ur.md) | CBOR typed envelopes, fountain QR fragments |
| URI/QR binary alphabet | [RFC 9285 Base45](https://www.rfc-editor.org/rfc/rfc9285.html) | Efficient QR alphanumeric input |
| Base encodings | [RFC 4648](https://www.rfc-editor.org/rfc/rfc4648.html) | Implemented hex and strict unpadded Base32; test vectors |
| Human checksum encoding | [Bech32 / BIP-173](https://github.com/bitcoin/bips/blob/master/bip-0173.mediawiki), [Bech32m / BIP-350](https://github.com/bitcoin/bips/blob/master/bip-0350.mediawiki) | Explicit typed address/profile codecs |
| Error-correcting seed shares | [codex32 / BIP-93](https://github.com/bitcoin/bips/blob/master/bip-0093.mediawiki) | Assess independent validation and usability |
| SeedQR | [SeedSigner](https://github.com/SeedSigner/seedsigner) | Optical entropy or index forms, explicit import/export |
| Visual hash fingerprint | [LifeHash](https://developer.blockchaincommons.com/lifehash/) | Version-pinned renderer and reference vectors |
| Identity layout | [Object Identity Block](https://developer.blockchaincommons.com/oib/) | Avatar + type glyph + short/full digest + label |
| Avatar styles | [DiceBear](https://www.dicebear.com/), [Jdenticon](https://jdenticon.com/) | Deterministic styles with clear licences |
| Public-key random art | [OpenSSH Randomart](https://man.openbsd.org/ssh-keygen.1) | Contextual human recognition of public identities |
| Baseline naming | [Angry Purple Tiger](https://github.com/helium/angry-purple-tiger) and [Sometimes Silly Snail](https://github.com/kieransimkin/sometimes-silly-snail) | Legacy importer and collision study, not cryptographic identifiers |

## Key-size fixtures

Use byte lengths of 16, 20, 24, 28, 32, 33, 48, 64, 65, 78, 96, plus 0, 1,
non-aligned boundaries, and larger post-quantum samples. These are byte lengths,
**not** claims that a public key, seed, secret and signature of the same size
are interchangeable.

## Document status

Reviewed for architectural planning on 2026-10-25. Each adapter requires its
own current upstream status and conformance assessment at implementation time.

## Expanded output and rendering research (2026-10-25)

The [evidence survey](RESEARCH_SURVEY_2026-10.md) groups primary references by
text/mnemonics, QR/industrial optical symbols, paper/metal/3D archiving,
visual identity art, sound/NFC/tactile channels and GPU/media outputs. The
[format atlas](OUTPUT_FORMAT_ATLAS.md) is the exhaustive *candidate taxonomy*,
not a list of supported code. The [pipeline](OUTPUT_PIPELINE.md) defines how
logical encodings, protection, symbols, renderers and carriers compose. The
[updated implementation plan](IMPLEMENTATION_PLAN.md) maps each area to
milestones and acceptance evidence.

Additional especially actionable primary references:

- [ISO/IEC 18004:2024](https://webstore.iec.ch/en/publication/99495) QR and
  [ISO/IEC 16022:2024](https://www.iso.org/standard/80926.html) Data Matrix.
- [ISO/IEC 24778](https://www.iso.org/standard/82441.html) Aztec,
  [ISO/IEC 23941](https://www.iso.org/standard/77404.html) rMQR,
  [ISO/IEC 23634](https://webstore.iec.ch/en/publication/75648) JAB Code.
- [RFC 9285](https://www.rfc-editor.org/rfc/rfc9285.html) Base45 for QR,
  [RFC 6330](https://www.rfc-editor.org/rfc/rfc6330.html) RaptorQ fountain FEC.
- [Blockchain Commons LifeHash](https://github.com/BlockchainCommons/LifeHash),
  [NFC Forum NDEF](https://nfc-forum.org/build/specifications/data-exchange-format-ndef-technical-specification/),
  [ggwave](https://github.com/ggerganov/ggwave).
- [glTF registry](https://registry.khronos.org/glTF/),
  [KTX registry](https://registry.khronos.org/KTX/),
  [3MF](https://3mf.io/spec/),
  [PDF/A](https://pdfa.org/resource/iso-19005-pdfa/).
- [LayerCode optical 3D](https://www.cs.columbia.edu/cg/layercode/index.html),
  [MIT InfraredTags](https://hcie.csail.mit.edu/research/infraredtags/infraredtags.html),
  [OPTAR paper optical archive](https://paperbackup.github.io/).

New/draft/proprietary specifications must be checked again for current status
and licensed access at implementation time. No raw-key import features are
implemented merely because a specification is cited.

## Native rendering ownership

- [FrameRudiments](https://github.com/kieransimkin/FrameRudiments) — the
  canonical DanceFlow rendering engine; its [native Rudiment renderer registry](https://github.com/kieransimkin/FrameRudiments/blob/main/docs/rudiment-renderers.md),
  [scoped effects](https://github.com/kieransimkin/FrameRudiments/blob/main/docs/scoped-post-effects.md)
  and [effect DAG](https://github.com/kieransimkin/FrameRudiments/blob/main/docs/effect-graph-design.md)
  are reusable instead of starting new graphics/effects engines in ByteFables.


## Robust watermark and provenance references

- [C2PA 2.5 — hard/soft bindings](https://spec.c2pa.org/specifications/specifications/2.5/specs/ContentCredentials.html): signed provenance, exact hash binding and invisible watermark/fingerprint soft lookup are distinct.
- [StegaStamp](https://github.com/tancik/StegaStamp): neural watermark for photographed physical images; published capacity/model limitations apply.
- [AudioSeal](https://github.com/facebookresearch/audioseal): localised audio watermark research, detector and limited optional message encoding; 16-bit public payload is NOT a generic 96/256-bit codec.
- [VideoSeal](https://github.com/facebookresearch/videoseal) and [OmniSealBench](https://github.com/facebookresearch/omnisealbench): video watermarking and cross-media evaluation.
- [Google SynthID](https://deepmind.google/models/synthid/) and [SynthID Text documentation](https://ai.google.dev/responsible/docs/safeguards/synthid): media/text marks; rewriting/translation degrades text-detection confidence.
- [FrameRudiments effects pipeline](https://github.com/kieransimkin/FrameRudiments/blob/main/docs/effect-graph-design.md): native home for reusable media transforms and benchmark evidence.

[ByteFables watermark v1 protocol](specs/watermark-v1.md) keeps message framing
independent from the carrier/effect; the four public-watermark capabilities are
catalogued as planned, with no production robustness or undetectability claim.

## Stage 2 local references

- [Story V2 wire specification](specs/story-v2.md): immutable public-only grammar
  and scheduled profiles, byte framing, radix mathematics and parser limits.
- [Story V2 vectors](../tests/vectors/story-v2.json): six theme pack digests
  and canonical sample stories for both independent formats.
- These ByteFables codecs are **original formats**, not implementations of
  [BIP-450/Formosa](https://github.com/bitcoin/bips/blob/master/bip-0450.mediawiki).

## Stage 3 public codec references (implemented subset)

The implementation, conformance examples, canonical BIP-39 English wordlist
revision and incomplete wallet-safety gates are now described in
[standard-codecs-v1.md](specs/standard-codecs-v1.md). Additional primary
sources: [RFC 9285](https://www.rfc-editor.org/rfc/rfc9285.html),
[Crockford Base32](https://www.crockford.com/base32),
[BIP-173](https://github.com/bitcoin/bips/blob/master/bip-0173.mediawiki),
[BIP-350](https://github.com/bitcoin/bips/blob/master/bip-0350.mediawiki),
[Multibase](https://github.com/multiformats/multibase), and
[UR single-part rules](https://github.com/BlockchainCommons/Research/blob/master/papers/bcr-2020-005-ur.md).
