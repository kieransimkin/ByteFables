# ByteFables experimental multipart `ur:bytes` transport (test fixtures only)

**Status:** implemented research/test adapter. **Not qualified for storing or transferring secrets.**
**Normative references:** [BCR-2020-005 Uniform Resources](https://github.com/BlockchainCommons/Research/blob/master/papers/bcr-2020-005-ur.md), [BCR-2024-001 multipart UR](https://github.com/BlockchainCommons/Research/blob/master/papers/bcr-2024-001-multipart-ur.md), [BCR-2020-012 Bytewords](https://github.com/BlockchainCommons/Research/blob/master/papers/bcr-2020-012-bytewords.md), [RFC 8949 CBOR](https://www.rfc-editor.org/rfc/rfc8949.html).

## Scope and type policy

This implementation uses **only** `ur:bytes`, the standard UR **test-only** type.
It does not produce `ur:crypto-*` wallet objects, register a ByteFables UR type,
implement SSKR/SLIP-39 or provide wallet interoperability. Source bytes and all
metadata must be intentionally **PUBLIC**. It is distinct from the existing
ByteFables BFQR1 *production-candidate public* typed record envelope.

A small external UR decoder should be able to interpret each emitted UR fragment,
but full external-implementation compatibility and physical device readback are
still unqualified. Reference consensus-vector checks do **not** establish a
complete independently audited implementation.

## Wire format and fountain selection

- Encode input as a deterministic CBOR **byte string** (public test data only).
- If it fits a fragment, preserve the existing `ur:bytes/<minimal-bytewords>`
  single-part syntax exactly. No multipart wrapper for one fragment.
- Otherwise split the CBOR message into `seqLen` equal-length padded fragments.
  The fragment size is `ceil(messageLen / ceil(messageLen / maxFragmentLen))`.
- Emit `ur:bytes/<seqNum>-<seqLen>/<minimal-bytewords>` where the encoded
  payload is the CBOR array `[seqNum, seqLen, messageLen, crc32, mixedBytes]`.
- The first `seqLen` frames are unmodified in-order fragments. Extra frames
  select and XOR a pseudo-random fragment subset using the BCR-2024-001
  `SHA256(u32be(seqNum) || u32be(crc32))` seed, Xoshiro256**, the Walker-Vose
  alias harmonic-degree sampler, and Fisher–Yates selection.
- The receiver accepts out-of-order/duplicate frames, rejects incompatible
  sessions, solves fragment equations over GF(2), checks canonical padding,
  CRC-32 and CBOR type, and returns an exact copy of the PUBLIC bytes.
- The full session is capped at 4,096 source bytes, 256 source fragments, and
  1,024 received frames. Encoded frames themselves are bounded.

The PRNG is **not cryptographically secure** and must not be used for seeds or
keys. CRC-32 is an accidental-error check, **not authentication**. The fountain
is resilient to *erasures* given enough independent fragments, not to deliberate
attack or arbitrary distortion of the QR image. Source-format `ur:bytes`
version and case policy are deliberately canonical/strict.

## Verified and still unverified

**Verified:** the original official `"Wolf"` Xoshiro modulo-100 values and
Fisher–Yates 10-item shuffle; the BCR-2024-001 50-frame fragment-chooser test
vector; pure/mixed round trips from 16 through 4096 bytes; fixed golden
Bytewords frames; tamper/metadata/canonicalisation rejection; actual matrix
output rendered by the FrameRudiments `bytefables-matrix-v1` renderer and
optically scanned with OpenCV.

**Not yet verified:** broad device compatibility, low-light scanning, exotic
cameras, QR animation timing, all publicly registered UR application types,
secret-handling, live wallet restore, or every malformed-input attack.

## API and CLI

```ts
const session = await encodeUrBytesMultipartTestOnly(publicFixtureBytes, {
  fragmentBytes: 20, extraMixedFrames: 8
});
const decoder = new UrBytesTestDecoder();
for (const frame of shuffledReceivedFrames) await decoder.receive(frame);
const recovered = decoder.result; // Uint8Array|null
const deck = await createUrBytesQrTestDeck(publicFixtureBytes, {
  fragmentBytes: 20, extraMixedFrames: 8,
  ecc: 'M', maxVersion: 14, id: 'public-ur-test', bounds: [0,0,640,640]
});
// deck.frames[].layer is a declarative FrameRudiments matrix renderer layer.
```

```sh
node bin/bytefables.mjs ur-test-encode --confirm-public --public-hex 00112233 \
  --fragment-bytes 16 --mixed-frames 6
# ur-test-recover --confirm-public consumes the JSON frames array on stdin.
```

Use `tests/vectors/ur-multipart-v1.json` for frozen test bytes/frames, and
`tests/python/test_ur_optical.py` for the OpenCV scanner pipeline. A fountain
receiver's rank is not a mathematical guarantee of optical or cryptographic
safety. Never treat the images as identity proof, encryption or backups.
