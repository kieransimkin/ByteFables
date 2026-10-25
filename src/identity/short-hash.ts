/** NIST-style left truncation of a SHA-256 public identity digest.
 *
 * The 256-bit parent identity is computed by identityDigest: SHA-256 over a
 * domain-separated, length-delimited namespace, kind and entire byte value.
 * Output length is deliberately NOT part of the digest preimage: shorter
 * profiles are nested prefixes of the same parent digest, never fresh entropy.
 */
import { assertPublicValue, type PublicByteValue } from '../value.js';
import { encodeHex } from '../codecs/hex.js';
import { identityDigest } from './identity.js';

export const SHORT_HASH_LENGTHS = Object.freeze([3, 4, 8] as const);
export type ShortHashBytes = (typeof SHORT_HASH_LENGTHS)[number];
export const SHORT_HASH_SCHEME = 'bytefables.sha256-left-truncated-public-identity.v1' as const;

export interface ShortPublicHash {
  readonly scheme: typeof SHORT_HASH_SCHEME;
  readonly hashFunction: 'SHA-256';
  readonly selection: 'leftmost-bytes';
  readonly namespace: string;
  readonly kind: string;
  readonly sourceByteLength: number;
  /** Informational 256-bit canonical parent, NOT an authentication signature. */
  readonly parentDigestHex: string;
  readonly bytes: ShortHashBytes;
  readonly bits: 24 | 32 | 64;
  readonly hex: string;
  readonly label: string;
  readonly guarantee: 'display-only';
}

function checkSize(bytes: number): asserts bytes is ShortHashBytes {
  if (bytes !== 3 && bytes !== 4 && bytes !== 8) {
    throw new RangeError('Short public hashes must have 3, 4 or 8 bytes');
  }
}

/** Truncate an ALREADY computed SHA-256 digest, by whole leftmost bytes.
 * For a uniform input digest the projection to 24/32/64 bits is exactly
 * uniform. No modulo operations, folding or unpredictable selections.
 */
export function truncateSha256Digest(digest: Uint8Array, bytes: ShortHashBytes): Uint8Array {
  checkSize(bytes);
  if (!(digest instanceof Uint8Array) || digest.length !== 32) {
    throw new TypeError('An exact 32-byte SHA-256 digest is required');
  }
  return new Uint8Array(digest.slice(0, bytes));
}

/** Derive a short PUBLIC display alias from a LONGER public byte value.
 * This discards information; never use its result as a node primary key,
 * signature, authenticator, cryptographic commitment or secret.
 */
export async function deriveShortPublicHash(
  source: PublicByteValue, bytes: ShortHashBytes
): Promise<ShortPublicHash> {
  assertPublicValue(source);
  checkSize(bytes);
  if (source.byteLength <= bytes) {
    throw new RangeError('Source must be strictly longer than selected short-hash size');
  }
  const full = await identityDigest(source);
  const hex = encodeHex(truncateSha256Digest(full, bytes));
  const bits = (bytes * 8) as 24 | 32 | 64;
  return Object.freeze({ scheme: SHORT_HASH_SCHEME, hashFunction: 'SHA-256',
    selection: 'leftmost-bytes', namespace: source.namespace, kind: source.kind,
    sourceByteLength: source.byteLength, parentDigestHex: encodeHex(full),
    bytes, bits, hex, label: `bf${bits}-${hex}`, guarantee: 'display-only' });
}

/** One parent digest, three nested display aliases. */
export async function deriveShortPublicHashes(source: PublicByteValue): Promise<readonly ShortPublicHash[]> {
  assertPublicValue(source);
  if (source.byteLength <= 8) {
    throw new RangeError('Source must be longer than 8 bytes for the three short-hash profiles');
  }
  const full = await identityDigest(source);
  const parentDigestHex = encodeHex(full);
  return Object.freeze(SHORT_HASH_LENGTHS.map(bytes => {
    const bits = (bytes * 8) as 24 | 32 | 64;
    const hex = encodeHex(truncateSha256Digest(full, bytes));
    return Object.freeze({ scheme: SHORT_HASH_SCHEME, hashFunction: 'SHA-256' as const,
      selection: 'leftmost-bytes' as const, namespace: source.namespace, kind: source.kind,
      sourceByteLength: source.byteLength, parentDigestHex, bytes, bits,
      hex, label: `bf${bits}-${hex}`, guarantee: 'display-only' as const });
  }));
}
