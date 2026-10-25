/** Big-endian integer and bit helpers used by all ByteFables wire formats. */
export function writeU32(value: number): Uint8Array {
  if (!Number.isSafeInteger(value) || value < 0 || value > 0xffffffff) {
    throw new RangeError('Expected unsigned 32-bit integer');
  }
  return Uint8Array.of(value >>> 24, (value >>> 16) & 255, (value >>> 8) & 255, value & 255);
}

export function readU32(bytes: Uint8Array, offset = 0): number {
  if (!Number.isSafeInteger(offset) || offset < 0 || offset + 4 > bytes.length) {
    throw new RangeError('Missing unsigned 32-bit integer');
  }
  return (((bytes[offset]! * 0x1000000) + (bytes[offset + 1]! << 16)) +
    (bytes[offset + 2]! << 8) + bytes[offset + 3]!) >>> 0;
}

export function concatBytes(...arrays: readonly Uint8Array[]): Uint8Array {
  const size = arrays.reduce((sum, a) => sum + a.length, 0);
  const result = new Uint8Array(size);
  let offset = 0;
  for (const array of arrays) { result.set(array, offset); offset += array.length; }
  return result;
}

export function bytesToBits(bytes: Uint8Array): number[] {
  const bits: number[] = [];
  for (const b of bytes) for (let shift = 7; shift >= 0; shift--) bits.push((b >>> shift) & 1);
  return bits;
}

export function bitsToBytes(bits: readonly number[]): Uint8Array {
  if (bits.length % 8) throw new RangeError('Bitstream length must be a multiple of 8');
  const bytes = new Uint8Array(bits.length / 8);
  for (let i = 0; i < bits.length; i++) {
    if (bits[i] !== 0 && bits[i] !== 1) throw new TypeError('Expected bits');
    bytes[i >>> 3] = bytes[i >>> 3]! | (bits[i]! << (7 - (i & 7)));
  }
  return bytes;
}

export function bitsToInt(bits: readonly number[]): number {
  if (bits.length > 24) throw new RangeError('Bit integer too wide');
  return bits.reduce((a, b) => { if (b !== 0 && b !== 1) throw new TypeError('Expected bits'); return a * 2 + b; }, 0);
}

export function intToBits(value: number, count: number): number[] {
  if (!Number.isInteger(count) || count < 0 || count > 24 ||
      !Number.isSafeInteger(value) || value < 0 || value >= 2 ** count) {
    throw new RangeError('Integer cannot fit in the specified bit width');
  }
  return Array.from({ length: count }, (_, i) => (value >>> (count - i - 1)) & 1);
}
