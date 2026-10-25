# BF-ID-SHORT-001 — Compact deterministic public hash profiles

**Status:** implemented, public-only display aliases; scheme
`bytefables.sha256-left-truncated-public-identity.v1`.

## Why this algorithm

Use **SHA-256 with leftmost-digest truncation** as specified in FIPS 180-4
§7 and described in NIST SP 800-107 Rev. 1 §5.1. NIST has announced plans to
withdraw SP 800-107 Rev. 1 once its additional guidance has moved to other
publications; FIPS 180-4's truncation mechanism remains a direct reference. Never
implement custom XOR folding, modulo reduction, arbitrary bit sampling or
variable random positions. Every byte of the input is hashed before any bits
are discarded. SHA-256 is already supplied by ByteFables' WebCrypto-compatible
`identityDigest`; the short function deliberately does NOT hash it a second time.

NIST SP 800-107 Rev. 1 §5.1 describes selecting the leftmost `lambda` bits and
notes the resulting collision resistance of roughly `lambda / 2` bits.
https://nvlpubs.nist.gov/nistpubs/FIPS/NIST.FIPS.180-4.pdf
https://csrc.nist.gov/pubs/sp/800/107/r1/final

For a PUBLIC typed input `(namespace, kind, bytes)`:

1. Compute `parentDigest = identityDigest(ByteValue.public(bytes, {namespace, kind}))`.
2. This uses the **unchanged** ByteFables public identity v1 construction:
   `SHA256(UTF8("ByteFables:public-identity:v1\\0") || u32be(ns.length) || ns ||
   u32be(kind.length) || kind || u32be(bytes.length) || bytes)`.
3. Compute `short_n = parentDigest[0:n]` for `n=3,4,8`, with no modulo or
   further transformation. Bytes are ordered left to right, most significant
   first. It has exactly `8*n` binary positions.
4. For display, use `bf24-<6 hex>`, `bf32-<8 hex>` and
   `bf64-<16 hex>`; these labels encode both algorithm version (implicitly v1)
   and length. Full provenance also includes the scheme ID, original typed
   context, original length and complete 32-byte parent digest.

A source **must be strictly longer than** the chosen short form. This prevents
accidentally suggesting that expanding a 3-byte input to an 8-byte display
hash adds actual identity entropy. Directly supplied 3/4/8-byte public values
are accepted by the visual feature and rendering system as-is.

### Distribution, mathematical claim and limits

If `H` is *exactly uniform* on `{0,1}^256`, its leftmost `n` bits are *exactly*
uniform: for every `n`-bit value, exactly `2^(256-n)` input strings share that
prefix. Taking a byte-aligned prefix introduces **zero additional bias**.
This is a mathematical statement about uniform *digest outputs*. SHA-256 is
modelled as pseudorandom in cryptographic applications, but no fixed hash
function guarantees perfectly balanced outputs under *every possible input
distribution*. In particular, fixed or highly concentrated inputs cannot be
made perfectly uniform by a deterministic operation. No shortening algorithm
preserves the full entropy or injectivity of the input.

The SHA-256 computation gives *computational whole-input sensitivity*, unlike
selecting the first three bytes of an arbitrary, possibly structured source.
An existing properly uniform digest could also be truncated directly; the
extra ByteFables domain-separated SHA-256 binds namespace and kind, produces
reproducible cross-runtime aliases and ensures changes in later source bytes
normally change the alias. The 3/4/8-byte aliases are deliberately nested
prefixes **of this ByteFables identity digest**; they're NOT raw leading bytes
of any blockchain's original transaction or key digest.

| Size | Bits | Distinct outputs | Birthday collision work | Approx. 50% collision population |
|---|---:|---:|---:|---:|
| 3 bytes | 24 | 16,777,216 | ~2^12 evaluations | ~4,823 |
| 4 bytes | 32 | 4,294,967,296 | ~2^16 evaluations | ~77,163 |
| 8 bytes | 64 | 18,446,744,073,709,551,616 | ~2^32 evaluations | ~5.06 billion |

None of these profiles supports authentication, direct signature lookup, unique
registry keys, tamper prevention or wallet/private-key operations. Primary node
keys MUST remain full original canonical node IDs. If display alias collisions
matter, detect them in the registry and show more bits or a secondary qualifier.
Do not reuse old `identityFingerprint(value, 12..32)` as a short hash: it retains
its existing 96-bit minimum for human *verification*, distinct from 24/32/64-
bit *display aliases*. The term "hash" here means a shortened hash digest, not
an irreversible representation of every source bit.

### Semantic prompt and fractal integration

A 3-byte derived alias yields 24 feature choices; 4 yields 32, 8 yields 64.
The same ByteFables `makeVisualBitPlan` maps those bytes MSB-first to opposing
semantic features. Use `visual-features --derive-short-bytes N` when you have a
long public hash, or feed an existing short hash directly. A 64-bit pseudorandom
visual seed derived by hashing a 24-bit alias has **at most 24 bits of source
information**, regardless of how many digits the seed output displays.

`hash_image_bench prepare --short-hash-bytes N` stores the parent digest and the
original input but makes the benchmark *on the shortened bytes*. Its paired
bit-flips operate on these **derived alias bytes**, so synthetic flip cases
are NOT generally outputs of the parent-hash derivation for a corresponding
long input. To measure original-hash avalanche, use a separate experiment that
flips a source input bit *before* shortening and compare the resulting short
hashes. Keep these two experiments distinct.

On newer fractal worktrees, the `render-fractals` command consumes these saved
cases as ordinary 3/4/8-byte public inputs and delegates effects and production
rendering to FrameRudiments. No separate fractal or animation renderer is added
by this identity shortening feature.

### Golden vectors and implementation scope

The independent fixture at `tests/vectors/short-public-hashes-v1.json` pins a
32-byte ascending test input, typed context, complete digest and all three
prefix outputs. Node tests independently calculate the original digest via
`node:crypto`; browser compatibility follows the pre-existing WebCrypto
`identityDigest` contract. No secret inputs, runtime dependencies, random
salt, external APIs or auto-downloaded models are introduced.

For a future **independent** derivation tree (non-nested values), use a separately
versioned, domain-separated KDF such as RFC 5869 HKDF with well-defined
context and output length. Do not silently change v1 to HKDF: this is a
format migration, not an improvement in exact uniformity. HKDF is a *key
derivation* standard, not an upgrade to 24-bit collision resistance.

### Empirical distribution diagnostic

Run `npm run profile:short-hashes` or `node scripts/profile-short-hashes.mjs
10000` on locally generated synthetic public values. The script calculates the
actual number of repeated aliases, expected random-output colliding-pair counts
and maximum binary-bit frequency deviation. It makes **no** claim that the
observed statistics prove perfect uniformity of SHA-256 or guarantee security
for malicious input populations.
