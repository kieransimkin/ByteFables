/** Multiformats Multibase: explicit single-character alphabet identification.
 * Implements the final common subset f, b, z, m and u. No CID interpretation.
 */
import { encodeHex, decodeHex } from './hex.js';
import { encodeBase32, decodeBase32 } from './base32.js';
import { encodeBase58, decodeBase58 } from './base58check.js';
import { encodeBase64, decodeBase64 } from './base64.js';
export type MultibasePrefix = 'f' | 'b' | 'z' | 'm' | 'u';

export function encodeMultibase(bytes: Uint8Array, prefix: MultibasePrefix = 'b'): string {
  if (!(bytes instanceof Uint8Array)) throw new TypeError('Multibase requires bytes');
  switch (prefix) {
    case 'f': return 'f' + encodeHex(bytes);
    case 'b': return 'b' + encodeBase32(bytes).toLowerCase();
    case 'z': return 'z' + encodeBase58(bytes);
    case 'm': return 'm' + encodeBase64(bytes).replace(/=+$/, '');
    case 'u': return 'u' + encodeBase64(bytes, true);
    default: throw new TypeError('Unsupported Multibase prefix');
  }
}

export function decodeMultibase(text: string): { prefix: MultibasePrefix; bytes: Uint8Array } {
  if (typeof text !== 'string' || text.length < 1 || text.length > 2100000) {
    throw new TypeError('Invalid Multibase text length');
  }
  const prefix = text[0] as MultibasePrefix, body = text.slice(1);
  let bytes: Uint8Array;
  switch (prefix) {
    case 'f': bytes = decodeHex(body); break;
    case 'b':
      if (!/^[a-z2-7]*$/.test(body)) throw new TypeError('Multibase b requires lowercase base32');
      bytes = decodeBase32(body.toUpperCase());
      break;
    case 'z': bytes = decodeBase58(body); break;
    case 'm':
      if (!/^[A-Za-z0-9+/]*$/.test(body) || body.length % 4 === 1) {
        throw new TypeError('Multibase m requires unpadded Base64');
      }
      bytes = decodeBase64(body + '='.repeat((4 - body.length % 4) % 4));
      break;
    case 'u': bytes = decodeBase64(body, true); break;
    default: throw new TypeError('Unsupported Multibase prefix');
  }
  if (encodeMultibase(bytes, prefix) !== text) throw new TypeError('Noncanonical Multibase encoding');
  return { prefix, bytes };
}
