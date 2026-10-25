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
