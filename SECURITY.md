# ByteFables security policy and boundaries

**Status:** pre-release experimental foundation (2026-10-25).
**Scope:** this repository presently makes no claim of suitability for storing,
transporting, encrypting, importing or recovering a cryptocurrency private key.

## Threat model

ByteFables has two independent security domains:

1. **Public identity** uses public identifiers (public keys, hashes, network
   addresses, node IDs) to derive aliases, visual fingerprints, and fallback
   sprites. Inputs are public; outputs can be published and cached. A picture
   must never substitute for cryptographic proof of identity.
2. **Secret archival** will eventually represent secret material for offline
   recording and recovery. This is not yet implemented as a supported
   application. It will need restricted environments, vetted format adapters,
   verification, storage rules, anti-exfiltration testing, and external review.

A `ByteValue<'secret'>` is refused at runtime and at compile-time by the current
public identity and experimental grammar APIs. This is an accident-prevention
interface, **not a security boundary**: callers control how they label input;
TypeScript can be bypassed; JavaScript memory cannot guarantee zeroisation.
Any raw bytes passed to generic hex/Base32 functions remain the caller's
responsibility. Never use these demonstration functions to handle live funds.

## Expected attacks or failures

| Threat | Initial design decision | Remaining limit |
|---|---|---|
| Input ambiguity / same bytes of different types | Namespace/type/length are included in domain-separated SHA-256 | Callers must assign truthful, stable types |
| Hash fingerprint collision | Use 12–32 digest bytes, default 12, always retain original full identifier | Short identifiers can collide; cannot authenticate |
| Accidental secret-to-avatar flow | Only typed public inputs accepted, with runtime guard | Incorrect labelling and memory compromise still possible |
| Forged mnemonic text | CRC-32 detects most random mistakes | CRC is unkeyed and can be forged; no authentication |
| Lost/truncated data | Length-checked, byte-exact decoder with padding checks | No damage repair in the prototype |
| Untrusted codebooks | Strict grammar compile, unique marker/roles/words and equal capacities | No homophone/language-quality audit yet |
| Long or malicious inputs | 1 MiB core limit; 4 KiB story limit; 512 char sentence cap | Future decoders require their own resource ceilings |
| Supply-chain changes | No runtime dependencies; pinned TypeScript; CI | Registries and CI runner still require review |
| Changing dictionaries | Prototype lexicon indices documented and tested | Future pack formats need immutable signed releases |
| QR scan or altered share | Not implemented yet | No error correction/threshold recovery currently |

## What is not implemented

- Private-key import/export, encryption, passphrase/seed derivation.
- Production BIP-39 wallet backup/import, SLIP-39 or Formosa compatibility.
- Threshold sharing, QR, SeedQR, UR multipart/fountain, RS/BCH codes, PDF/metal templates.
- BIP-39 mnemonic-to-seed derivation, wallet account restoration or private mnemonic processing.
- Wallet descriptor or address derivation.
- Secure memory, secure deletion or offline-only operational enforcement.
- Automated repair of erroneous key material.

`encodeExperimentalStory` uses SHA-256 **nowhere** for authentication; it uses
IEEE CRC-32 only as a detectable, accidental-error checksum. An adversary can
modify the bytes and recompute CRC. It has no cryptographic tamper resistance.

## Security requirements before secret support

1. Independent threat model for all secret-handling entry points.
2. A reviewed, interoperable target specification and published reference
   test vectors for each supported format.
3. Offline-only by default, no analytics, no telemetry, no silent clipboard,
   logs, history, screenshots or network transmissions.
4. Enforce secret/public provenance throughout API, CLI, UI, exports and caches.
5. Verify every recovery path restores the intended key and related wallet
   metadata, not only a 32-byte array.
6. Strong checksumming and explicit context/version checks; never silently
   autocorrect key material into a different valid backup.
7. Independent cryptography/security review and parser fuzzing before a
   production or wallet-safe claim.

## Reporting

Use GitHub private vulnerability reporting if enabled for this repository.
Otherwise contact the maintainers privately before disclosing exploitable
secret-handling issues in public. The initial prototype does not warrant a
security-bounty or cryptographic assurance claim.

## FrameRudiments bridge boundary (experimental, public-only)

FrameRudiments is the only intended production renderer for ByteFables imagery.
A native project may log renderer configuration, source code hashes, content and
media traces; therefore it MUST NEVER receive sensitive source records. Only
already-public 256-bit record digests or explicitly public matrix/vector input
may cross into a renderer. The TypeScript public label is a defensive API hint,
not a proof that caller-supplied data is safe to publish. Do not use render
service endpoints to generate private-key, wallet-seed or password material.

`bytefables-matrix-v1` converts already encoded *public* module bits to host
layers; it adds NO check code, QR standard compatibility, ECC or authentication.
Native visual effects, resampling, lossy video, user compositing and physical
printing can destroy machine readability. Independent readback from final
output is required before calling a symbol a recoverable archive.

The FrameRudiments Python adapter is trusted code, not an importable project
script. Install explicitly into a vetted FrameRudiments environment; its
factories validate bounded, versioned public-only style data and never accept
network, filesystem, arbitrary Python or executable SVG specifications.

## Invisible/robust watermark capability (Wave A planning only)

**No concealed signal is currently written.** `encodePublicWatermarkMessage`
creates a typed public record's SHA-256 prefix plus a CRC-32 accidental-error
check; it does not produce a steganographic image/sound/video/text mark.
`planPublicWatermark` is a descriptive planning API with **no embedder or
extractor**. These are public-only operations, not encryption, forensic proof,
DRM, confidentiality, digital signatures or a way to secure private keys.

Invisible ≠ statistically undetectable. A motivated party can potentially
locate, counterfeit, remove or disrupt a hidden mark, including by cropping,
resampling, paraphrasing or re-generating media. Text watermarking is especially
sensitive to edits, translation, and the number of unconstrained token choices.
CRC-32 can be replaced; 96-bit prefixes can collide with enough trials;
confidence in a detector requires false-positive testing on *unmarked* data.

Only opt-in, owned/licensed output should be modified. Avoid secret payloads,
recipient-specific covert tracking, unreleased private correspondence and any
undisclosed outbound watermarking service. Production adapters require blind
extraction from final encoded media, independently reviewed algorithms and
measured distortion/false-negative/false-positive limits. Exact optical codes
and signed/hash-committed files must not be damaged in order to add a watermark.
See [the public watermark protocol](docs/specs/watermark-v1.md).

## Stage 2 public mnemonic stories — experimental only

Two new versioned text formats reconstruct PUBLIC bytes with unkeyed truncated
SHA-256 checksums. Their word choices and template markers are NOT a security
mechanism, ownership proof, seed-derivation algorithm or entropy generator.
The decoder preserves the byte sequence, but does not preserve the original
context/namespace and is not compatible with BIP-39 or BIP-450/Formosa.

The 33–35-bit prefix grammar and the 24/32/40-bit scheduled format are
distinct wire formats; the scheduled template ID never counts toward data
capacity. Parser limits, strict canonical re-encoding, codebook digest vectors,
UTF-8/whitespace rejection and public-only runtime gates are in place. A malicious
actor can always manufacture a new story with its own valid SHA-256 checksum.
No third-party language or security qualification is claimed.

FrameRudiments previews display a bounded subset of sentences and are not
recoverable copies of the full public story. Effects and language transformations
may destroy recoverability; the renderer must not claim an archival guarantee.

## Experimental LLM -> image hash identity profiler (public only)

The `visual-features` API and `tools.hash_image_bench` process only explicitly
confirmed PUBLIC byte values. A hash-derived image cannot act as a private-key
backup, proof of signature ownership, or cryptographic authenticity check.
The raw public hex is visible in CLI arguments and manifests; keep secret
identifiers out of this tool. The local prompt writer receives only selected
semantic decisions, not the original hash. Its endpoint accepts only an explicit
HTTP loopback address; hosted generation and remote model downloads are not
provided. Native Diffusers model weights and tokenizers should be pinned,
audited and executed in an operator-controlled sandbox with resource limits.
FrameRudiments owns all production rendering and effects; ByteFables holds
raw source render receipts strictly as benchmark evidence. Auto-evaluation
with CLIP is a fallible proxy, not proof of recoverable hash bits.


## Fractal identity and small-model benchmarking (experimental)

The new public fractal generator accepts only a context-derived 256-bit digest
and eight validated, explicit public feature bits. Its output is **not** a
reversible encoding, secret backup, watermark, authentication mark, or
cryptographic uniqueness proof. Different public inputs can produce the same
or similar visible pattern. An image model's inferred fidelity is never an
identity check. Runtime classification of caller-supplied public data is still
not a reliable secret-memory boundary.

The optional spectral latent-noise experiment changes the model's Gaussian
prior and has no security or quality guarantee. The optional img2img experiment
reads only checksum-verified locally produced public fractal images and fails
if source files are missing or changed. Model checkpoints must exist locally;
no implicit downloads, remote prompt endpoints, arbitrary scripts or model
licence promises are included. Keep the result gallery and full hex values
PUBLIC; never supply wallet seeds, key material or private records.

## Short public hash aliases (v1)

Optional 3/4/8-byte public display aliases follow SHA-256 left truncation. They
are not cryptographically unique or authenticators. A visual seed derived from
24 or 32 source bits has at most that many bits of possible variation, even
if SHA-256 produces a 256-bit visual-seed digest. Never use a shortened public
alias in place of an original node ID, address, full digest, signature or MAC;
collisions are expected at scales described in `docs/specs/short-public-hashes-v1.md`.
Only publicly classified inputs are admitted, and misclassification by callers
remains a security boundary that TypeScript alone cannot enforce.

## Stage 3 public standards codec qualification (experimental where noted)

Common public binary text codecs are implemented with strict canonical decoders,
no global model downloads and official published reference vectors. BIP-39 now
exists **only for publicly disclosed dummy entropy**; its `wallet/bip39`
manifest entry deliberately remains `planned`, while
`codec/bip39-public-fixture` requires experimental opt-in. Its 2048-word list is
SHA-256 pinned and matched byte-for-byte against the Bitcoin BIPs Git object.
The decoder cannot determine whether its input is a live wallet seed phrase, so
the caller must keep secrets out: never paste a mnemonic into the public CLI,
Python or frontend flows. The raw CLI text and process argument lists may be
logged, and browser pages may preserve input history.

`ur:bytes` is a one-part test type reserved for implementation validation, not
an interoperable wallet UR export. True multipart/typed UR and hardened wallet
recovery remain unimplemented. Base58Check requires explicit version bytes and
Bech32 witness functions enforce witness-version and checksum pairing. A
correctly checksummed address can still be unauthorised, wrong-network, burned,
or unrelated to the user's private keys. The standalone binary codecs do **not**
preserve network, provenance, key type, account policy or authentication.
See [Stage 3 standards profile](docs/specs/standard-codecs-v1.md).
