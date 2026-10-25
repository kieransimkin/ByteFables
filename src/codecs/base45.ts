/** RFC 9285 Base45: binary -> QR-alphanumeric-compatible text. No checksum. */
const ALPHABET = '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ $%*+-./:';
const INDEX = new Map([...ALPHABET].map((character, index) => [character, index]));

export function encodeBase45(bytes: Uint8Array): string {
  if (!(bytes instanceof Uint8Array)) throw new TypeError('Base45 requires bytes');
  let encoded = '';
  for (let i = 0; i < bytes.length; i += 2) {
    const paired = i + 1 < bytes.length;
    const number = paired ? bytes[i]! * 256 + bytes[i + 1]! : bytes[i]!;
    encoded += ALPHABET[number % 45]! + ALPHABET[Math.floor(number / 45) % 45]!;
    if (paired) encoded += ALPHABET[Math.floor(number / 2025)]!;
  }
  return encoded;
}

export function decodeBase45(encoded: string): Uint8Array {
  if (typeof encoded !== 'string' || encoded.length % 3 === 1 || encoded.length > 1572864) {
    throw new TypeError('Invalid Base45 length');
  }
  const result: number[] = [];
  for (let i = 0; i < encoded.length;) {
    const paired = i + 3 <= encoded.length;
    const digits = paired ? 3 : 2;
    let n = 0, factor = 1;
    for (let j = 0; j < digits; j++) {
      const value = INDEX.get(encoded[i + j]!);
      if (value === undefined) throw new TypeError('Invalid Base45 character');
      n += value * factor;
      factor *= 45;
    }
    if (n > (paired ? 65535 : 255)) throw new TypeError('Noncanonical Base45 value');
    if (paired) result.push(n >>> 8, n & 255);
    else result.push(n);
    i += digits;
  }
  return Uint8Array.from(result);
}
