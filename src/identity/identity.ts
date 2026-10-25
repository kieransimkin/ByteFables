import { assertPublicValue, type PublicByteValue } from '../value.js';
import { concatBytes, writeU32 } from '../utils/binary.js';
import { encodeHex } from '../codecs/hex.js';
import { sha256 } from './sha256.js';

const TEXT = new TextEncoder();
const DOMAIN = TEXT.encode('ByteFables:public-identity:v1\0');

/** Domain-separated, length-prefixed public identity; unambiguous across type/namespace/data. */
export async function identityDigest(value: PublicByteValue): Promise<Uint8Array> {
  assertPublicValue(value);
  const namespace = TEXT.encode(value.namespace);
  const kind = TEXT.encode(value.kind);
  const bytes = value.toBytes();
  return sha256(concatBytes(DOMAIN, writeU32(namespace.length), namespace,
    writeU32(kind.length), kind, writeU32(bytes.length), bytes));
}

/** Human verification aid, NOT a substitute for an authenticated full identifier. */
export async function identityFingerprint(value: PublicByteValue, bytes = 12): Promise<string> {
  if (!Number.isInteger(bytes) || bytes < 12 || bytes > 32) {
    throw new RangeError('Fingerprint length must be 12–32 bytes');
  }
  return `bf1-${encodeHex((await identityDigest(value)).slice(0, bytes))}`;
}
