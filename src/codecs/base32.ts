/** RFC 4648 Base32 without padding. Output uppercase; decoder rejects noncanonical padding bits. */
const ALPHABET = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ234567';
const REVERSE = new Map(Array.from(ALPHABET, (ch, i) => [ch, i]));

export function encodeBase32(bytes: Uint8Array): string {
  if (!(bytes instanceof Uint8Array)) throw new TypeError('Expected Uint8Array');
  let buffer = 0, bits = 0, output = '';
  for (const byte of bytes) {
    buffer = (buffer << 8) | byte;
    bits += 8;
    while (bits >= 5) {
      bits -= 5;
      output += ALPHABET[(buffer >>> bits) & 31]!;
    }
    buffer &= (1 << bits) - 1;
  }
  if (bits) output += ALPHABET[(buffer << (5 - bits)) & 31]!;
  return output;
}

export function decodeBase32(text: string): Uint8Array {
  if (typeof text !== 'string' || !/^[A-Z2-7]*$/.test(text) ||
      ![0, 2, 4, 5, 7].includes(text.length % 8)) {
    throw new TypeError('Invalid unpadded RFC 4648 Base32 string');
  }
  let buffer = 0, bits = 0;
  const output: number[] = [];
  for (const char of text) {
    const value = REVERSE.get(char);
    if (value === undefined) throw new TypeError('Invalid Base32 symbol');
    buffer = (buffer << 5) | value;
    bits += 5;
    if (bits >= 8) {
      bits -= 8;
      output.push((buffer >>> bits) & 255);
      buffer &= (1 << bits) - 1;
    }
  }
  if (buffer !== 0) throw new TypeError('Noncanonical Base32 padding bits');
  return Uint8Array.from(output);
}
