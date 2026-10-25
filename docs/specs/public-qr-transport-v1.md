# BFQR1 — public records in QR Model 2 symbols

**Status:** experimental ByteFables wire protocol, 25 October 2026. Not a wallet
backup or a Blockchain Commons UR/SeedQR format. Codebook and wire layout are
versioned; changes require a new `BFQR2` identifier.

## Separation of responsibilities

- `encodeQrModel2(publicBytes)` produces an ISO/IEC 18004 QR Code Model 2
  **byte-mode** binary module matrix. Versions 1–40, levels L/M/Q/H, 8 masks,
  Reed–Solomon ECC block partitioning, format/version BCH fields, four-module
  quiet zone, exact capacity checks and deterministic mask selection. The
  mathematical encoder runs without any renderer or npm runtime dependency.
- `encodePublicQrSession(publicRecord)` wraps ByteFables' **typed public CBOR
  envelope** in ASCII QR frames. `decodePublicQrSession` reassembles and
  verifies typed bytes, lengths, CRC-32, SHA-256 prefix, inner SHA-256 integrity
  and canonical CBOR framing. It accepts reordering, exact duplicates and up to
  **one missing data frame** when the optional XOR-parity frame is available.
- FrameRudiments' registered `bytefables-matrix-v1` factory owns all optical
  rasterisation. `createPublicQrCard` emits native layers plus captions; these
  are project fragments rather than a separate ByteFables pixel renderer.
- External readers independently scan the **exported PNG** and submit decoded
  frame strings for reassembly. In development CI we compare 56 cases with an
  independent Python QR encoder, and exercise OpenCV readback of saved PNGs.

## Public byte-mode QR

`encodeQrModel2(bytes, { ecc, minVersion, maxVersion, mask })` chooses the
smallest version within bounds fitting the byte-mode payload. It uses the
standard 4-bit byte-mode indicator, 8-bit character count for versions 1–9,
16-bit count for versions 10–40, terminator, byte alignment and 0xEC/0x11 pad
codewords. It then creates QR Reed–Solomon parity blocks, interleaves all
codewords, lays down finder/alignment/timing/version/format patterns and
applies one of eight masks. `mask: undefined` selects the lowest scoring mask.

The matrix does not itself decode from scanned images; optical detection,
error correction and camera imaging belong to independent scanner libraries.
For archival use, never interpret *module ECC* as an integrity or
cryptographic signature guarantee. Full original bytes remain authoritative.

## BFQR1 text packet

Each QR contains an ASCII string `BFQR1:` followed by **unpadded RFC 4648
Base64url** encoding of the following binary record:

| Offset | Size | Meaning |
| --- | ---: | --- |
| 0 | 4 | `BFQ1` ASCII magic |
| 4 | 1 | flags: `0` data, `1` parity |
| 5 | 16 | first 16 bytes of SHA-256 of complete CBOR |
| 21 | 4 | complete CBOR length, uint32 big endian |
| 25 | 2 | nominal chunk size, uint16 big endian |
| 27 | 2 | number of data chunks, uint16 big endian |
| 29 | 2 | zero-based chunk index; parity index = data chunk count |
| 31 | 4 | IEEE CRC-32 of complete canonical CBOR, big endian |
| 35 | 4 | IEEE CRC-32 of packet bytes `[0..34] || [39..end]` |
| 39 | N | fixed-sized chunk bytes (final data chunk zero-padded) |

*Canonical constraints:* all frames in a session must match the same ID,
length, chunk size, count and full CRC. Unknown flag values, oversized frames,
noncanonical Base64url, invalid frame CRCs, conflicting duplicates, too many
fragments, wrong final padding or a bad full commitment are rejected. The
recovered CBOR MUST pass ByteFables public-record validation. Decoders are
bounded to 256 KiB and at most 1,024 original data chunks, plus one parity
chunk. The framing adds no cryptographic secrecy or message authentication.

The optional parity frame is **XOR of all zero-padded data chunks**, so one
missing data fragment can be reconstructed exactly, but two missing fragments
cannot. This is an intentionally simple, separately versioned public-profile
redundancy scheme: **not rateless fountain coding**, not Reed–Solomon at the
session level, and not Blockchain Commons MUR. The QR symbol itself carries
standard Reed–Solomon codewords.

## Optically qualified pilot

The default is ECC Q, QR max version 12, mask 0, with enough bytes per part to
fit the configured QR profile. Fixed mask 0 is a valid QR mask used for the
independent scanner test fixtures; different masks may be selected explicitly.
QR input is **PUBLIC** only. No private keys, entropy, recovery phrases,
credentials or undisclosed personal information may enter this pipeline.

- Preserve a four-module white quiet zone.
- Render at **integer pixels per module**, without interpolation or resizing.
- No glyph/logo insertions, post effects, anti-aliasing, gradients, colour
  grading, blur, distortion or animation applied to the optical symbol itself.
- Place decorative artwork and caption text **outside** the protected QR bounds.
- Verify each **final exported image** using a genuinely separate QR reader.
- For multi-page sheets, scan every page (or enough pages plus the parity page),
  then recover and compare the complete typed record independently.
- Mark export profiles as tested only for the documented scanner, DPI, module
  pitch and channel. OpenCV acceptance on particular synthetic samples is not
  printer calibration, damage tolerance or hardware wallet interoperability.

## Public-only CLI

```sh
npm ci --ignore-scripts
npm run build
node bin/bytefables.mjs qr-public --confirm-public \
  --public-hex 000102ff --namespace danceflow --kind node-id \
  --ecc Q --max-version 12 --fragment-bytes 48 \
  > public-frames.json

node bin/bytefables.mjs qr-public --confirm-public \
  --public-hex 000102ff --namespace danceflow --kind node-id \
  --fragment-bytes 48 --include-layers > framerudiments-layers.json

cat public-frames.json | node bin/bytefables.mjs qr-recover --confirm-public
```

`qr-recover` reads a JSON array of frame texts or the JSON `frames` field from
stdin. These are *public data* commands; shells/terminal scrollback may record
the complete input and output. The `qr-public --include-layers` output includes
existing `bytefables-matrix-v1` layer fragments to pass into a FrameRudiments
project with registered renderer factories. The host's final encoded/project
output must still pass independent readback.

## Forward compatibility

- Standards-compatible UR v2 single/multipart and fountain coding require
  their own CBOR types and fragment chooser, reference test vectors, and
  actual hardware/software interoperability; BFQR1 MUST NOT be mislabeled UR.
- Full QR byte-mode decoding with RS error correction is delegated to
  independent mature scanners; ByteFables' current proof is *encoding* plus
  typed-data reassembly, not a homegrown QR scanner.
- PDFs/steel/photographic storage and printer density require later
  fabrication-specific approval and retained scan/readback evidence.
