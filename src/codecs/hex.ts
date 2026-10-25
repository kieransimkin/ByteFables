const HEX_PATTERN = /^(?:[0-9a-fA-F]{2})*$/;

/** Canonical output: lowercase, no prefix or separators. */
export function encodeHex(bytes: Uint8Array): string {
  if (!(bytes instanceof Uint8Array)) throw new TypeError('Expected Uint8Array');
  return Array.from(bytes, b => b.toString(16).padStart(2, '0')).join('');
}

/** Accept ASCII case variants but reject whitespace, odd nibbles and prefixes. */
export function decodeHex(text: string): Uint8Array {
  if (typeof text !== 'string' || !HEX_PATTERN.test(text)) {
    throw new TypeError('Invalid hexadecimal byte string');
  }
  const out = new Uint8Array(text.length / 2);
  for (let i = 0; i < out.length; i++) out[i] = parseInt(text.slice(i * 2, i * 2 + 2), 16);
  return out;
}
