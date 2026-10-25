/** Explicit public-fixture text decoding. Raw-byte codecs do not recover
 * network, algorithm, namespace, key type or other contextual metadata.
 */
import { getFormatManifest } from './manifest.js';
import { decodeHex } from '../codecs/hex.js';
import { decodeBase32 } from '../codecs/base32.js';
import { decodeBase45 } from '../codecs/base45.js';
import { decodeBase64 } from '../codecs/base64.js';
import { decodeCrockford32 } from '../codecs/crockford32.js';
import { decodeBytewords } from '../codecs/bytewords.js';
import { decodeBip39PublicMnemonic } from '../codecs/bip39.js';
import { decodeUrBytesTestOnly } from '../codecs/ur-bytes-test.js';
import { decodeMultibase } from '../codecs/multibase.js';

const DECODERS: Readonly<Record<string, (text: string) => Uint8Array | Promise<Uint8Array>>> = {
  'codec/hex': decodeHex,
  'codec/rfc4648-base32-nopad': decodeBase32,
  'codec/base45': decodeBase45,
  'codec/base64-padded': decodeBase64,
  'codec/base64url-nopad': text => decodeBase64(text, true),
  'codec/crockford32-check': text => decodeCrockford32(text, true),
  'codec/bytewords': decodeBytewords,
  'codec/bytewords-uri': text => decodeBytewords(text, 'uri'),
  'codec/bytewords-minimal': text => decodeBytewords(text, 'minimal'),
  'codec/bip39-public-fixture': decodeBip39PublicMnemonic,
  'codec/ur-bytes-test-only': decodeUrBytesTestOnly,
  'codec/multibase-base32': text => decodeMultibase(text).bytes,
  'codec/multibase-base64url': text => decodeMultibase(text).bytes
};

export async function decodePublicTextFormat(
  formatId: string, text: string,
  options: { readonly allowExperimental?: boolean } = {}
): Promise<Uint8Array> {
  const manifest = getFormatManifest(formatId);
  if (!manifest || manifest.input !== 'public-record' || manifest.guarantee !== 'reversible-raw' ||
      manifest.maturity === 'planned' || !Object.hasOwn(DECODERS, formatId)) {
    throw new TypeError('No implemented public raw-byte decoder for requested format');
  }
  if (manifest.maturity === 'experimental' && options.allowExperimental !== true) {
    throw new TypeError('Experimental decoding requires opt-in');
  }
  if (typeof text !== 'string' || new TextEncoder().encode(text).length > manifest.maxOutputBytes) {
    throw new RangeError('Public text exceeds format output limit');
  }
  if (formatId === 'codec/multibase-base32' && !text.startsWith('b') ||
      formatId === 'codec/multibase-base64url' && !text.startsWith('u')) {
    throw new TypeError('Multibase encoding does not match the requested alphabet');
  }
  const bytes = await DECODERS[formatId]!(text);
  if (bytes.length < manifest.minInputBytes || bytes.length > manifest.maxInputBytes) {
    throw new RangeError('Decoded byte length not permitted for this format');
  }
  return new Uint8Array(bytes);
}
