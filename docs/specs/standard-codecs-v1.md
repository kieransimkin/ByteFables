# ByteFables Stage 3 — Public reversible standards codecs

**Status:** Source implementation and CI vectors, 2026-10-25. NOT a qualified
cryptocurrency wallet recovery application. This document describes ByteFables
adapters, not new encodings or independent crypto inventions.

## 1. Scope and guarantees

The library supports exact raw-byte round trips, including leading zeroes,
for the standards listed below. Only a separately defined typed CBOR record
preserves namespace, network, purpose and application metadata. Interoperable
text encodings do not themselves authenticate bytes, establish key ownership or
restore a wallet policy. FrameRudiments owns ALL finished rendering; these
codecs produce text/binary *source material* only.

| Format/API | Status | Payload | Integrity | Bounds and restrictions |
|---|---|---|---|---|
| `encodeBase64` / `decodeBase64` | Implemented | raw bytes | none | RFC 4648 padded Base64 |
| URL-safe `encodeBase64(x,true)` | Implemented | raw bytes | none | unpadded canonical Base64url |
| `encodeBase45` / `decodeBase45` | Implemented | raw bytes | none | RFC 9285, QR-compatible character set |
| `encodeCrockford32(x,true)` | Implemented | raw bytes | optional mod-37 check | Ambiguous O/I/L accepted on decode; noncanonical trailing bits rejected |
| `encodeBase58` / `decodeBase58` | Implemented | raw bytes | none | 256-byte resource ceiling; preserves initial 00 |
| `encodeBase58Check(x,version)` | Implemented | version + raw bytes | double SHA-256 prefix (4 bytes) | **explicit** 1–4 byte version; verify network; bounded payload |
| `encodeBech32` / `decodeBech32` | Implemented | 5-bit words | 30-bit checksum | BIP-173 and BIP-350 variant distinguished; max 90 characters |
| `encodeSegwitAddress` / `decodeSegwitAddress` | Implemented | version + witness program | BIP-173/BIP-350 | `bc`, `tb`, `bcrt` only; witness 0 -> Bech32, >=1 -> Bech32m |
| `encodeBytewords(...,style)` | Implemented | raw bytes | IEEE CRC-32 in network order | BCR-2020-012 canonical full, hyphen/URI, minimal forms |
| `encodeMultibase` / `decodeMultibase` | Implemented | raw bytes | none | canonical `f`, `b`, `z`, `m`, `u` prefixes |
| `encodeBip39PublicEntropy` | **public fixtures only** | 128,160,192,224,256 bits | ENT/32 bits of SHA-256 | Official English 2048-word index; no wallet import/KDF |
| `encodeUrBytesTestOnly` | **test-only** | CBOR byte string | Bytewords CRC-32 | BCR-2020-005 `ur:bytes` reserved for testing; no multipart/type registry |

The generic `executePublicFormat` registry exposes only fixed-configuration
formats that can encode any supported public byte value. Base58Check requires
explicit version bytes, and Bech32/SegWit requires an HRP, witness version or
checksum variant; their APIs are deliberately separate, rather than guessing a
network or silently making up an address. Unknown formats never execute.

## 2. Standard-specific boundaries

### BIP-39 public-fixture mode

The *exact* wordlist is copied from the canonical Bitcoin BIPs repository at
`bitcoin/bips:bip-0039/english.txt`, Git blob
`942040ed50f7205cafc465496229128ba4f78e75`. The checked-in text has
SHA-256 `2f5eed53a4727b4bf8880d8f3f199efc90e58503646d9ff8eff3a2ed3b24dbda`.
`node scripts/check-bip39-wordlist.mjs` ensures the reference text and compiled
TypeScript dictionary are identical. Dictionary changes require a new
version/compatibility review.

The encoder accepts only `ByteValue<'public'>` and exact BIP-39 entropy sizes.
The decoder accepts full, canonical lowercase English words separated by single
spaces and verifies the checksum, returning raw bytes. The **separate**
PBKDF2-HMAC-SHA512 mnemonic-to-seed procedure is not exposed or tested as a
production secret-handling workflow. Never supply an actual private key or
wallet mnemonic to the CLI, Node, browser or Python adapters; CLI arguments and
output may be logged. BIP-39 mnemonic interoperability does not automatically
restore BIP-32 paths, multisig policy, descriptors, passphrases or spending
permissions.

The experimental registry format ID is `codec/bip39-public-fixture`, requiring
`allowExperimental:true`. `wallet/bip39` remains **planned**, not executable.

### Bytewords versus UR

Full/URI/minimal Bytewords append a CRC32 of *the raw body*, then map every
body/checksum byte to the canonical 256-word table. Bytewords does not add
schema metadata and the CRC32 is forgeable. A UR transports a deterministic
CBOR object with a type registry. `ur:bytes` has been reserved by the UR
specification for testing/validation, and ByteFables only implements that
single-part, test-only case. It is **not** a production `ur:crypto-seed`,
Gordian Envelope, SSKR, fountain decoder or multipart QR workflow.

### Bech32, Base58Check and Multibase

Base58Check prefix bytes and Bech32 human-readable prefixes/witness versions
are part of the meaning. A successful checksum does not prove a chain/network,
valid account, authorization or balance. The typed `decodeBase58CheckForVersion`
helper compares a caller-specified prefix; caller must still validate the
payload with the *actual* chain rules. `Multibase` tags an alphabet, not a
cryptographic content hash or CID. `Base45` optimises text for the QR
alphanumeric mode but does not create a QR matrix or Reed–Solomon code.

## 3. Test evidence and independent vectors

`tests/interop-codecs.test.mjs` exercises known official vectors from:

- RFC 9285 `"AB" -> "BB8"`, `"Hello!!" -> "%69 VD92EX0"`.
- RFC 4648 standard Base64 `"f" .. "foobar"`.
- BIP-173 `A12UEL5L`, BIP-350 `A1LQFN3A`, published valid and invalid
  v0/v1 SegWit addresses with independent expected witness programs.
- BCR-2020-012 full/URI/minimal canonical sample and its CRC-32.
- Published BIP-39 English vectors for zero, all-one, patterned and selected
  entropy strings. The official 2048-word file is byte-for-byte pinned.
- Deterministic reference vectors for `ur:bytes` test-mode and Multibase.
- Random round-trip property tests at zero, odd, common and larger lengths;
  intentional corruptions, wrong checksums/versions, padding and parse limits.

`tests/interop-cli.test.mjs` verifies manifest/API/CLI interoperability,
confirmation gate and mandatory experimental opt-in. The repository's native
Python tests continue covering public Framerudiments and model benchmark
contracts. Our local Python test suite uses `PYTHONPATH` for the adapter when
installing build dependencies from the network is unavailable.

## 4. Sample use

```ts
import {
  ByteValue, PublicRecord, executePublicFormat, decodePublicTextFormat,
  encodeBip39PublicEntropy, decodeBip39PublicMnemonic,
  encodeSegwitAddress, decodeSegwitAddress
} from 'bytefables';

const source = ByteValue.public(Uint8Array.of(0, 1, 2, 255), {
  namespace: 'danceflow', kind: 'node-id'
});
const record = new PublicRecord(source);
const text = await executePublicFormat('codec/bytewords-minimal', record);
const raw = await decodePublicTextFormat(text.formatId, text.data as string);
// Raw bytes only; exact source namespace/kind are not recovered by Bytewords.

// PUBLIC DUMMY entropy only; not a wallet API.
const publicFixture = ByteValue.public(new Uint8Array(16), {
  namespace: 'test', kind: 'entropy-fixture'
});
const words = await encodeBip39PublicEntropy(publicFixture);
const publicBytes = await decodeBip39PublicMnemonic(words);

const address = encodeSegwitAddress('bc', 0, new Uint8Array(20));
const parsed = decodeSegwitAddress(address);
```

For public demonstrations:

```bash
node bin/bytefables.mjs encode-public --confirm-public \
  --namespace danceflow --kind node-id --public-hex 000102ff \
  --format codec/bytewords-minimal
node bin/bytefables.mjs decode-public-text --confirm-public \
  --format codec/base45 --text BB8
```

## 5. Outstanding Stage 3 and downstream work

- Reviewed, independently interoperable **SLIP-39** group/member sharing, not
  an ad-hoc Shamir implementation; threshold recovery is not media ECC.
- Full **UR v2** dCBOR tag registry, multipart/fountain transport, fragment
  rejection/partial loss and real wallet hardware interop.
- Secret-qualified **BIP-39**: offline-only threat model, mnemonic-to-seed
  tests, actual wallet restoration, passphrases/paths/descriptor policy.
- **Formosa**, codex32, Electrum/Monero network-specific formats and WIF
  adapters, each independently versioned and tested.
- QR, SeedQR, PDF and metal readback using FrameRudiments plus independent
  real-device scanner verification (Stage 5); don't call the codecs archival
  media merely because their text can be printed.
- External security review, property-based fuzzing, cross-language conformance,
  licensing and dependency audit before production key handling.

## References

- [RFC 4648](https://www.rfc-editor.org/rfc/rfc4648.html)
- [RFC 9285](https://www.rfc-editor.org/rfc/rfc9285.html)
- [Crockford Base32](https://www.crockford.com/base32)
- [BIP-39](https://github.com/bitcoin/bips/blob/master/bip-0039.mediawiki)
- [BIP-173](https://github.com/bitcoin/bips/blob/master/bip-0173.mediawiki)
- [BIP-350](https://github.com/bitcoin/bips/blob/master/bip-0350.mediawiki)
- [Bytewords (BCR-2020-012)](https://github.com/BlockchainCommons/Research/blob/master/papers/bcr-2020-012-bytewords.md)
- [UR (BCR-2020-005)](https://github.com/BlockchainCommons/Research/blob/master/papers/bcr-2020-005-ur.md)
- [Multibase specification](https://github.com/multiformats/multibase)
- [Bitcoin Base58Check](https://developer.bitcoin.org/reference/transactions.html)
