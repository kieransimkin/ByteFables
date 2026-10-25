/**
 * Small, strict RFC 8949 core-deterministic CBOR subset.
 * Supported: unsigned integers <= 2^32-1, UTF-8 text, byte strings,
 * fixed arrays and maps whose unsigned integer keys are 0..23.
 * No floats, tags, indefinite lengths, negative integers or simple values.
 * This is intentionally NOT a general-purpose CBOR decoder.
 */
import { concatBytes } from '../utils/binary.js';
import { MAX_VALUE_BYTES } from '../value.js';

export type CborValue = number | string | Uint8Array |
  readonly CborValue[] | ReadonlyMap<number, CborValue>;

export const MAX_CBOR_BYTES = MAX_VALUE_BYTES + 2048;
const MAX_DEPTH = 8;
const MAX_TEXT_BYTES = 1024;
const MAX_COLLECTION_SIZE = 32;
const encoder = new TextEncoder();
const decoder = new TextDecoder('utf-8', { fatal: true });

function uintHeader(major: number, count: number): Uint8Array {
  if (!Number.isSafeInteger(count) || count < 0 || count > 0xffffffff) {
    throw new RangeError('CBOR length or integer exceeds 32 bits');
  }
  const lead = major << 5;
  if (count < 24) return Uint8Array.of(lead | count);
  if (count <= 0xff) return Uint8Array.of(lead | 24, count);
  if (count <= 0xffff) return Uint8Array.of(lead | 25, count >>> 8, count & 255);
  return Uint8Array.of(lead | 26, count >>> 24, (count >>> 16) & 255,
    (count >>> 8) & 255, count & 255);
}

function encode(value: CborValue, depth: number): Uint8Array {
  if (depth > MAX_DEPTH) throw new RangeError('CBOR nesting too deep');
  if (typeof value === 'number') return uintHeader(0, value);
  if (typeof value === 'string') {
    const bytes = encoder.encode(value);
    // TextEncoder silently substitutes U+FFFD for unpaired surrogates; reject.
    if (bytes.length > MAX_TEXT_BYTES || decoder.decode(bytes) !== value) {
      throw new TypeError('Invalid or oversized UTF-8 string');
    }
    return concatBytes(uintHeader(3, bytes.length), bytes);
  }
  if (value instanceof Uint8Array) {
    if (value.length > MAX_VALUE_BYTES) throw new RangeError('CBOR byte string too large');
    return concatBytes(uintHeader(2, value.length), value);
  }
  if (Array.isArray(value)) {
    if (value.length > MAX_COLLECTION_SIZE) throw new RangeError('CBOR array too large');
    return concatBytes(uintHeader(4, value.length), ...value.map(v => encode(v, depth + 1)));
  }
  if (value instanceof Map) {
    if (value.size > 24) throw new RangeError('CBOR map too large');
    const keys = [...value.keys()].sort((a, b) => a - b);
    if (keys.some(k => !Number.isInteger(k) || k < 0 || k > 23)) {
      throw new TypeError('CBOR map keys must be unsigned integers from 0 to 23');
    }
    const result: Uint8Array[] = [uintHeader(5, keys.length)];
    for (const key of keys) {
      result.push(uintHeader(0, key), encode(value.get(key)!, depth + 1));
    }
    return concatBytes(...result);
  }
  throw new TypeError('Unsupported CBOR data type');
}

export function encodeDeterministicCbor(value: CborValue): Uint8Array {
  const output = encode(value, 0);
  if (output.length > MAX_CBOR_BYTES) throw new RangeError('CBOR document too large');
  return output;
}

class CborReader {
  private position = 0;
  constructor(private readonly bytes: Uint8Array) {}

  get done(): boolean { return this.position === this.bytes.length; }

  private readByte(): number {
    if (this.position >= this.bytes.length) throw new RangeError('Truncated CBOR document');
    return this.bytes[this.position++]!;
  }

  private readUnsigned(ai: number): number {
    if (ai < 24) return ai;
    if (ai === 24) {
      const v = this.readByte();
      if (v < 24) throw new TypeError('Non-preferred CBOR unsigned integer');
      return v;
    }
    if (ai === 25) {
      const v = this.readByte() * 256 + this.readByte();
      if (v <= 0xff) throw new TypeError('Non-preferred CBOR unsigned integer');
      return v;
    }
    if (ai === 26) {
      const v = this.readByte() * 0x1000000 + this.readByte() * 65536 +
        this.readByte() * 256 + this.readByte();
      if (v <= 0xffff) throw new TypeError('Non-preferred CBOR unsigned integer');
      return v;
    }
    throw new TypeError('Unsupported CBOR length, integer width or indefinite form');
  }

  private take(size: number): Uint8Array {
    if (size < 0 || size > this.bytes.length - this.position) {
      throw new RangeError('Truncated CBOR payload');
    }
    const result = new Uint8Array(this.bytes.subarray(this.position, this.position + size));
    this.position += size;
    return result;
  }

  parse(depth = 0): CborValue {
    if (depth > MAX_DEPTH) throw new RangeError('CBOR nesting too deep');
    const header = this.readByte();
    const major = header >>> 5;
    // Reject unsupported types BEFORE processing arguments/allocations.
    if (![0, 2, 3, 4, 5].includes(major)) throw new TypeError('Unsupported CBOR major type');
    const n = this.readUnsigned(header & 31);
    if (major === 0) return n;
    if (major === 2) {
      if (n > MAX_VALUE_BYTES) throw new RangeError('CBOR byte string too large');
      return this.take(n);
    }
    if (major === 3) {
      if (n > MAX_TEXT_BYTES) throw new RangeError('CBOR text too large');
      return decoder.decode(this.take(n));
    }
    if (major === 4) {
      if (n > MAX_COLLECTION_SIZE) throw new RangeError('CBOR array too large');
      const output: CborValue[] = [];
      for (let i = 0; i < n; i++) output.push(this.parse(depth + 1));
      return output;
    }
    if (n > 24) throw new RangeError('CBOR map too large');
    const output = new Map<number, CborValue>();
    let previous = -1;
    for (let i = 0; i < n; i++) {
      const key = this.parse(depth + 1);
      if (typeof key !== 'number' || key <= previous || key > 23) {
        throw new TypeError('CBOR map keys must be strictly increasing unsigned small integers');
      }
      previous = key;
      output.set(key, this.parse(depth + 1));
    }
    return output;
  }
}

/** Strict canonical read: exact 1 item, no trailing bytes, only core preferred encodings. */
export function decodeDeterministicCbor(bytes: Uint8Array): CborValue {
  if (!(bytes instanceof Uint8Array) || bytes.length > MAX_CBOR_BYTES) {
    throw new TypeError('Expected bounded CBOR bytes');
  }
  const reader = new CborReader(bytes);
  const result = reader.parse();
  if (!reader.done) throw new TypeError('Trailing CBOR data');
  // Reject any encoding not reproduced byte-for-byte by the deterministic writer.
  const canonical = encodeDeterministicCbor(result);
  if (canonical.length !== bytes.length || canonical.some((b, i) => b !== bytes[i])) {
    throw new TypeError('Non-canonical CBOR document');
  }
  return result;
}
