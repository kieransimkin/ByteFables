/** Crockford Base32, with optional mod-37 check symbol; not RFC 4648 Base32. */
const ALPHABET = '0123456789ABCDEFGHJKMNPQRSTVWXYZ';
const CHECK = ALPHABET + '*~$=U';
const norm = (c: string): string => {
  const x = c.toUpperCase();
  if (x === 'O') return '0';
  if (x === 'I' || x === 'L') return '1';
  return x;
};

/** Left-to-right base-32 accumulator; the optional check symbol uses mod 37. */
function checked(s: string): number {
  let modulus = 0;
  for (const c of s) {
    const digit = ALPHABET.indexOf(norm(c));
    if (digit < 0) throw new TypeError('Invalid Crockford Base32 character');
    modulus = (modulus * 32 + digit) % 37;
  }
  return modulus;
}

export function encodeCrockford32(bytes: Uint8Array, check = false): string {
  if (!(bytes instanceof Uint8Array)) throw new TypeError('Expected bytes');
  let out = '', carry = 0, count = 0;
  for (const b of bytes) {
    carry = (carry << 8) | b;
    count += 8;
    while (count >= 5) {
      count -= 5;
      out += ALPHABET[(carry >>> count) & 31]!;
      carry &= (1 << count) - 1;
    }
  }
  if (count) out += ALPHABET[(carry << (5 - count)) & 31]!;
  return check ? out + CHECK[checked(out)]! : out;
}

export function decodeCrockford32(encoded: string, check = false): Uint8Array {
  if (typeof encoded !== 'string' || encoded.length > 1700000 || !/^[A-Za-z0-9*~$=\-]*$/.test(encoded)) {
    throw new TypeError('Invalid Crockford Base32 input');
  }
  const compact = encoded.replace(/-/g, '').toUpperCase();
  if (check && compact.length < 1) throw new TypeError('Missing Crockford check symbol');
  const body = check ? compact.slice(0, -1) : compact;
  if (check && CHECK[checked(body)] !== norm(compact.at(-1)!)) {
    throw new TypeError('Crockford check-symbol mismatch');
  }
  let carry = 0, count = 0;
  const result: number[] = [];
  for (const char of body) {
    const digit = ALPHABET.indexOf(norm(char));
    if (digit < 0) throw new TypeError('Invalid Crockford Base32 character');
    carry = (carry << 5) | digit;
    count += 5;
    if (count >= 8) {
      count -= 8;
      result.push((carry >>> count) & 255);
      carry &= (1 << count) - 1;
    }
  }
  if (count >= 5 || carry !== 0 || encodeCrockford32(Uint8Array.from(result)) !== [...body].map(norm).join('')) {
    throw new TypeError('Noncanonical Crockford Base32 padding');
  }
  return Uint8Array.from(result);
}
