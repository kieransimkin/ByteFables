/** BIP-173 Bech32 and BIP-350 Bech32m. The generic format encodes five-bit words;
 * the byte adapter rejects non-zero or excessive padding. Segwit profiles
 * validate witness rules and use the mandatory version-dependent checksum.
 */
export type Bech32Variant = 'bech32' | 'bech32m';
const ALPHABET = 'qpzry9x8gf2tvdw0s3jn54khce6mua7l';
const GEN = [0x3b6a57b2, 0x26508e6d, 0x1ea119fa, 0x3d4233dd, 0x2a1462b3];
const CONST: Readonly<Record<Bech32Variant, number>> = { bech32: 1, bech32m: 0x2bc830a3 };

function polymod(values: readonly number[]): number {
  let chk = 1;
  for (const value of values) {
    const top = chk >>> 25;
    chk = (((chk & 0x1ffffff) << 5) ^ value) >>> 0;
    for (let j = 0; j < GEN.length; j++) if ((top >>> j) & 1) chk = (chk ^ GEN[j]!) >>> 0;
  }
  return chk >>> 0;
}

function expand(hrp: string): number[] {
  return [...hrp].map(c => c.charCodeAt(0) >>> 5).concat([0], [...hrp].map(c => c.charCodeAt(0) & 31));
}

/** Convert MSB-first digits between base 2^from and base 2^to. */
export function convertBits(values: Uint8Array, from: number, to: number, pad: boolean): Uint8Array {
  if (!(values instanceof Uint8Array) || !Number.isInteger(from) || !Number.isInteger(to) ||
      from < 1 || from > 8 || to < 1 || to > 8) throw new TypeError('Invalid bit conversion');
  const maxv = (1 << to) - 1, maxAccum = (1 << (from + to - 1)) - 1;
  let accumulator = 0, count = 0;
  const result: number[] = [];
  for (const value of values) {
    if (value >= (1 << from)) throw new TypeError('Input digit exceeds bit width');
    accumulator = ((accumulator << from) | value) & maxAccum;
    count += from;
    while (count >= to) {
      count -= to;
      result.push((accumulator >>> count) & maxv);
    }
  }
  if (pad && count) result.push((accumulator << (to - count)) & maxv);
  else if (!pad && (count >= from || ((accumulator << (to - count)) & maxv) !== 0)) {
    throw new TypeError('Invalid nonzero or excessive bit padding');
  }
  return Uint8Array.from(result);
}

export function encodeBech32(hrp: string, words: Uint8Array, variant: Bech32Variant): string {
  if (!Object.hasOwn(CONST, variant) || typeof hrp !== 'string' || !/^[\x21-\x7e]{1,83}$/.test(hrp) ||
      !(words instanceof Uint8Array) || words.some(x => x > 31)) {
    throw new TypeError('Invalid Bech32 HRP, variant or 5-bit words');
  }
  const h = hrp.toLowerCase();
  const values = expand(h).concat([...words], [0, 0, 0, 0, 0, 0]);
  const value = polymod(values) ^ CONST[variant];
  const check = Array.from({ length: 6 }, (_, i) => (value >>> (5 * (5 - i))) & 31);
  const text = h + '1' + [...words, ...check].map(x => ALPHABET[x]!).join('');
  if (text.length > 90) throw new RangeError('Bech32 maximum is 90 characters');
  return text;
}

export function decodeBech32(text: string): { hrp: string; words: Uint8Array; variant: Bech32Variant } {
  if (typeof text !== 'string' || text.length < 8 || text.length > 90 ||
      text.toLowerCase() !== text && text.toUpperCase() !== text) throw new TypeError('Invalid Bech32 case or length');
  if (!/^[\x21-\x7e]+$/.test(text)) throw new TypeError('Invalid Bech32 ASCII');
  const input = text.toLowerCase();
  const separator = input.lastIndexOf('1');
  if (separator < 1 || separator > 83 || separator + 7 > input.length) throw new TypeError('Invalid Bech32 separator');
  const hrp = input.slice(0, separator), data = input.slice(separator + 1);
  const numbers: number[] = [];
  for (const c of data) {
    const n = ALPHABET.indexOf(c);
    if (n < 0) throw new TypeError('Invalid Bech32 alphabet');
    numbers.push(n);
  }
  const check = polymod(expand(hrp).concat(numbers));
  const variant = check === CONST.bech32 ? 'bech32' : check === CONST.bech32m ? 'bech32m' : null;
  if (!variant) throw new TypeError('Bech32 checksum mismatch');
  return { hrp, words: Uint8Array.from(numbers.slice(0, -6)), variant };
}

/** Explicit HRP and checksum selection required: Bech32 is not a universal wallet address codec. */
export function encodeBech32Bytes(hrp: string, bytes: Uint8Array, variant: Bech32Variant): string {
  return encodeBech32(hrp, convertBits(bytes, 8, 5, true), variant);
}
export function decodeBech32Bytes(text: string): { hrp: string; bytes: Uint8Array; variant: Bech32Variant } {
  const parsed = decodeBech32(text);
  return { hrp: parsed.hrp, bytes: convertBits(parsed.words, 5, 8, false), variant: parsed.variant };
}

export function encodeSegwitAddress(hrp: 'bc' | 'tb' | 'bcrt', version: number, program: Uint8Array): string {
  if (!['bc', 'tb', 'bcrt'].includes(hrp) || !Number.isInteger(version) || version < 0 || version > 16 ||
      !(program instanceof Uint8Array) || program.length < 2 || program.length > 40 ||
      (version === 0 && program.length !== 20 && program.length !== 32)) {
    throw new TypeError('Invalid witness program, version or network');
  }
  return encodeBech32(hrp, Uint8Array.of(version, ...convertBits(program, 8, 5, true)), version === 0 ? 'bech32' : 'bech32m');
}
export function decodeSegwitAddress(text: string): { hrp: 'bc' | 'tb' | 'bcrt'; version: number; program: Uint8Array } {
  const { hrp, words, variant } = decodeBech32(text);
  if (hrp !== 'bc' && hrp !== 'tb' && hrp !== 'bcrt') throw new TypeError('Unsupported witness network');
  const version = words[0];
  if (version === undefined || version > 16 || variant !== (version === 0 ? 'bech32' : 'bech32m')) {
    throw new TypeError('Witness version/checksum mismatch');
  }
  const program = convertBits(words.slice(1), 5, 8, false);
  if (program.length < 2 || program.length > 40 || version === 0 && program.length !== 20 && program.length !== 32) {
    throw new TypeError('Invalid witness program length');
  }
  return { hrp, version, program };
}
