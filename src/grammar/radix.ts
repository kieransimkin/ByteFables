/** Exact enumerative/mixed-radix coding. No floating-point capacity estimates. */
export function radixCapacityBits(radices: readonly number[]): number {
  if (!Array.isArray(radices) || !radices.length || radices.length > 32 ||
      radices.some(r => !Number.isSafeInteger(r) || r < 2 || r > 65536)) {
    throw new TypeError('Require 1–32 integer radices between 2 and 65536');
  }
  let product = 1n;
  for (const radix of radices) product *= BigInt(radix);
  return product.toString(2).length - 1;
}

export function bitsToBigint(bits: readonly number[]): bigint {
  if (!Array.isArray(bits) || bits.length > 512) throw new RangeError('Invalid bitstream size');
  let value = 0n;
  for (const bit of bits) {
    if (bit !== 0 && bit !== 1) throw new TypeError('Expected only zeroes and ones');
    value = value * 2n + BigInt(bit);
  }
  return value;
}

export function bigintToBits(value: bigint, count: number): number[] {
  if (typeof value !== 'bigint' || !Number.isSafeInteger(count) || count < 0 || count > 512 ||
      value < 0n || value >= (1n << BigInt(count))) {
    throw new RangeError('Number outside bit capacity');
  }
  return Array.from({ length: count }, (_, i) =>
    Number((value >> BigInt(count - 1 - i)) & 1n));
}

/** Encode exactly floor(log2(product(radices))) bits, discarding no original bit. */
export function encodeRadixBits(bits: readonly number[], radices: readonly number[]): number[] {
  const capacity = radixCapacityBits(radices);
  if (bits.length !== capacity) throw new RangeError('Radix bit count does not match capacity');
  let value = bitsToBigint(bits);
  const digits = Array<number>(radices.length);
  for (let i = radices.length - 1; i >= 0; i--) {
    const radix = BigInt(radices[i]!);
    digits[i] = Number(value % radix);
    value /= radix;
  }
  if (value !== 0n) throw new RangeError('Radix overflow');
  return digits;
}

/** Reject unused mixed-radix combinations rather than silently folding them. */
export function decodeRadixBits(digits: readonly number[], radices: readonly number[]): number[] {
  const capacity = radixCapacityBits(radices);
  if (!Array.isArray(digits) || digits.length !== radices.length) {
    throw new RangeError('Wrong radix digit count');
  }
  let value = 0n;
  for (let i = 0; i < digits.length; i++) {
    const digit = digits[i]!;
    const radix = radices[i]!;
    if (!Number.isSafeInteger(digit) || digit < 0 || digit >= radix) {
      throw new RangeError('Digit outside allowed radix');
    }
    value = value * BigInt(radix) + BigInt(digit);
  }
  return bigintToBits(value, capacity); // Rejects all unused, noncanonical tuples.
}
