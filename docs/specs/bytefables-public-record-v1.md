# BF-PUBLIC CBOR record, v1

**Status:** ByteFables internal, public-only foundation. **Not wallet-safe.**

This file and [`public-record-v1.cddl`](public-record-v1.cddl) specify an exact
canonical serialisation of typed **public** values. The decoder rejects unknown
CBOR items rather than interpreting them as authority or unknown network data.
The format is not UR, BIP-39, COSE or a wallet keystore.

## Canonical structure

The CBOR root is a map with *integer keys 0..5 in ascending order*:

- `0`: text `BF-PUBLIC`; `1`: unsigned integer `1` (wire version).
- `2`: nested context map `{0: namespace, 1: kind, 2: algorithm, 3: network,
  4: byteOrder, 5: schemaVersion}` with integer keys in ascending order.
- `3`: unsigned integer, original byte count (0..1,048,576).
- `4`: byte string, original bytes (exactly member `3` in length).
- `5`: exactly 32-byte SHA-256 commitment calculated below.

Namespace, kind and algorithm must match `[a-z][a-z0-9._:/-]{0,127}`;
network uses the same syntax or the empty string. Byte order is one of
`na`, `big`, `little`. Schema version is an integer from `1` through `65535`.
An invalid or unrecognised interpretation is rejected by a *type-specific*
consumer; `opaque` is the neutral algorithm name. String encoding is UTF-8,
ASCII restricted by the defined regular expression. No Unicode normalization
or byte reinterpretation occurs in the encoder.

The domain-separated commitment is:

```
SHA256(UTF8("ByteFables:public-cbor-envelope:v1\\0") ||
       deterministicCBOR(root_without_member_5))
```

The shown `\\0` denotes a literal zero byte following `v1`, not two
characters backslash and zero. CDDL is descriptive: it cannot express the
computed-length or hash relationship; both are enforced by the decoder.

Only unsigned integers up to `2^32−1`, byte strings, UTF-8 text, fixed arrays
and small integer-keyed maps are admitted by the present CBOR profile. All
integer/length headers use the shortest encoding. Negative integers, floats,
CBOR tags, indefinite encodings, null, booleans, duplicate/out-of-order map
keys and trailing data are rejected. Max nesting is 8; arrays have at most
32 items; map keys are restricted to 0..23. Text is limited to 1,024 bytes
per field. Whole serialized size is bounded to input limit + 2,048 bytes.

The decoder re-encodes and compares the exact wire bytes to enforce this profile.
A record is *accidentally tamper-evident*, not authenticated: an attacker able
to modify public data can recompute its unkeyed SHA-256 digest. The `bfrec1-`
fingerprint is a human recognition aid; do not use it for authorisation.

## Versioning and interoperability

Publish a new version for any changes to map semantics, field constraints,
byte order defaults or hash domain. Never reinterpret a v1 record in place.
ByteFables identityDigest (legacy `bf1-` fingerprint) intentionally hashes a
different, smaller context and is NOT interchangeable with this record digest.

Golden examples in `tests/vectors/public-cbor-v1.json` MUST remain immutable.
The `encodePublicRecord` and `decodePublicRecord` API round-trips the payload
bytes *and* declared context, with no fallback parser.

This public-only container is not approved for private seeds, secret key
material, confidential documents or production wallet reconstruction.
