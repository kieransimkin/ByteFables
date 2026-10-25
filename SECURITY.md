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
- BIP-39, SLIP-39 or Formosa compatibility.
- Threshold sharing, QR, SeedQR, Bytewords/UR, RS/BCH codes, PDF/metal templates.
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
