/** RFC 4648 canonical padded Base64 and unpadded Base64url; browser/Node portable. */
const CLASSIC = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/';
const URL = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_';

export function encodeBase64(bytes: Uint8Array, urlSafe = false): string {
  if (!(bytes instanceof Uint8Array)) throw new TypeError('Expected bytes');
  const alphabet = urlSafe ? URL : CLASSIC;
  let out = '';
  for (let i = 0; i < bytes.length; i += 3) {
    const a = bytes[i]!, b = bytes[i + 1] ?? 0, c = bytes[i + 2] ?? 0;
    const triple = (a << 16) | (b << 8) | c;
    out += alphabet[(triple >>> 18) & 63]! + alphabet[(triple >>> 12) & 63]!;
    if (i + 1 < bytes.length) out += alphabet[(triple >>> 6) & 63]!;
    else if (!urlSafe) out += '=';
    if (i + 2 < bytes.length) out += alphabet[triple & 63]!;
    else if (!urlSafe) out += '=';
  }
  return out;
}

export function decodeBase64(encoded: string, urlSafe = false): Uint8Array {
  if (typeof encoded !== 'string' || encoded.length > 1398104) throw new TypeError('Invalid Base64 input');
  const rule = urlSafe ? /^[A-Za-z0-9_-]*$/ : /^(?:[A-Za-z0-9+/]{4})*(?:[A-Za-z0-9+/]{2}==|[A-Za-z0-9+/]{3}=)?$/;
  if (!rule.test(encoded) || (urlSafe && encoded.length % 4 === 1)) {
    throw new TypeError('Invalid Base64 alphabet, padding or length');
  }
  const input = urlSafe ? encoded : encoded.replace(/=+$/, '');
  const alphabet = urlSafe ? URL : CLASSIC;
  let buffer = 0, bits = 0;
  const bytes: number[] = [];
  for (const char of input) {
    const digit = alphabet.indexOf(char);
    if (digit < 0) throw new TypeError('Invalid Base64 character');
    buffer = (buffer << 6) | digit;
    bits += 6;
    if (bits >= 8) {
      bits -= 8;
      bytes.push((buffer >>> bits) & 255);
      buffer &= (1 << bits) - 1;
    }
  }
  if (bits >= 6 || buffer !== 0 || encodeBase64(Uint8Array.from(bytes), urlSafe) !== encoded) {
    throw new TypeError('Noncanonical Base64 tail bits');
  }
  return Uint8Array.from(bytes);
}
