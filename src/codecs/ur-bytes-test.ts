/** BCR-2020-005 single-part UR `bytes` TEST TYPE only. No multipart/fountain
 * encoding or UR type registry. The UR specification reserves `bytes` for
 * interoperability testing and forbids production application use.
 */
import { encodeDeterministicCbor, decodeDeterministicCbor } from '../framing/cbor.js';
import { encodeBytewords, decodeBytewords } from './bytewords.js';

export function encodeUrBytesTestOnly(publicTestBytes: Uint8Array): string {
  if (!(publicTestBytes instanceof Uint8Array) || publicTestBytes.length > 4096) {
    throw new RangeError('UR bytes TEST format accepts at most 4 KiB of public fixture bytes');
  }
  return 'ur:bytes/' + encodeBytewords(encodeDeterministicCbor(publicTestBytes), 'minimal');
}
export function decodeUrBytesTestOnly(text: string): Uint8Array {
  if (typeof text !== 'string' || text.length > 10000 || !/^ur:bytes\/[a-z]+$/i.test(text)) {
    throw new TypeError('Expected single-part ur:bytes/ test fixture');
  }
  const bytewords = text.slice('ur:bytes/'.length).toLowerCase();
  const result = decodeDeterministicCbor(decodeBytewords(bytewords, 'minimal'));
  if (!(result instanceof Uint8Array) || result.length > 4096) {
    throw new TypeError('UR bytes test must contain one canonical CBOR byte string');
  }
  return result;
}
