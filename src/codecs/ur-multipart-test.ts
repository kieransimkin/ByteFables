/** Blockchain Commons UR v2/MUR transport, restricted to public `ur:bytes` TEST fixtures.
 * BCR-2020-005, BCR-2024-001, BCR-2020-012. This is not a wallet UR type.
 * No private-key processing, UR crypto-* registry, or guessed external type tags.
 * Test limit 4 KiB with bounded fountain receiver; the code is NOT audited.
 */
import { encodeDeterministicCbor, decodeDeterministicCbor } from '../framing/cbor.js';
import { encodeBytewords, decodeBytewords } from './bytewords.js';
import { sha256 } from '../identity/sha256.js';
import { crc32 } from '../utils/crc32.js';
import { concatBytes, writeU32 } from '../utils/binary.js';

const MAX_DATA = 4096;
const MAX_PARTS = 256;
const MAX_FRAMES = 1024;
const MASK64 = (1n << 64n) - 1n;
const UTF = new TextEncoder();
const UR_PREFIX = 'ur:bytes/';

function checkBytes(bytes: Uint8Array, label: string): void {
  if (!(bytes instanceof Uint8Array) || bytes.length < 1 || bytes.length > MAX_DATA) {
    throw new RangeError(`${label} must be 1..4096 PUBLIC test bytes`);
  }
}

function rotate(value: bigint, count: bigint): bigint {
  return ((value << count) | (value >> (64n - count))) & MASK64;
}

/** Non-cryptographic, exactly specified xoshiro256** generator, BCR-2024-001.
 * PRNG output is only used for robust fragment selection, NEVER for key material.
 */
export class UrTestXoshiro256 {
  private readonly state: bigint[];
  private constructor(state: bigint[]) { this.state = state; }
  static async fromSeed(bytes: Uint8Array): Promise<UrTestXoshiro256> {
    const digest = await sha256(bytes);
    const state: bigint[] = [];
    for (let i = 0; i < 4; i++) {
      let v = 0n;
      for (let j = 0; j < 8; j++) v = (v << 8n) | BigInt(digest[i * 8 + j]!);
      state.push(v);
    }
    return new UrTestXoshiro256(state);
  }
  static async fromString(input: string): Promise<UrTestXoshiro256> {
    return UrTestXoshiro256.fromSeed(UTF.encode(input));
  }
  next(): bigint {
    const s = this.state;
    const result = (rotate((s[1]! * 5n) & MASK64, 7n) * 9n) & MASK64;
    const t = (s[1]! << 17n) & MASK64;
    s[2] = s[2]! ^ s[0]!;
    s[3] = s[3]! ^ s[1]!;
    s[1] = s[1]! ^ s[2]!;
    s[0] = s[0]! ^ s[3]!;
    s[2] = s[2]! ^ t;
    s[3] = rotate(s[3]!, 45n);
    return result;
  }
  /** IEEE 754 conversion follows the reference's UInt64 -> Double / 2^64. */
  nextDouble(): number { return Number(this.next()) / 18446744073709551616; }
  nextIndex(length: number): number {
    if (!Number.isSafeInteger(length) || length < 1) throw new RangeError('Invalid shuffle length');
    return Math.min(length - 1, Math.floor(this.nextDouble() * length));
  }
}

class AliasChooser {
  private readonly probabilities: number[];
  private readonly aliases: number[];
  constructor(count: number) {
    if (!Number.isSafeInteger(count) || count < 1 || count > MAX_PARTS) throw new RangeError('Invalid fountain degree count');
    const weights = Array.from({ length: count }, (_, i) => 1 / (i + 1));
    const total = weights.reduce((s, n) => s + n, 0);
    const p = weights.map(w => w * count / total);
    const small: number[] = [], large: number[] = [];
    // The reference adds indices in reverse order and removes from the end.
    for (let i = count - 1; i >= 0; i--) (p[i]! < 1 ? small : large).push(i);
    const probability = new Array<number>(count).fill(1);
    const alias = new Array<number>(count).fill(0);
    while (small.length && large.length) {
      const a = small.pop()!, g = large.pop()!;
      probability[a] = p[a]!;
      alias[a] = g;
      p[g] = p[g]! + p[a]! - 1;
      (p[g]! < 1 ? small : large).push(g);
    }
    this.probabilities = probability;
    this.aliases = alias;
  }
  next(rng: UrTestXoshiro256): number {
    const i = Math.min(this.probabilities.length - 1,
      Math.floor(this.probabilities.length * rng.nextDouble()));
    return rng.nextDouble() < this.probabilities[i]! ? i : this.aliases[i]!;
  }
}

/** 0-based indices mixed by a standard UR fountain part. Pure frames are first. */
export async function chooseUrTestFragments(seqNum: number, seqLen: number,
  checksum: number): Promise<readonly number[]> {
  if (!Number.isSafeInteger(seqNum) || seqNum < 1 || seqNum > 0xffffffff ||
      !Number.isSafeInteger(seqLen) || seqLen < 1 || seqLen > MAX_PARTS ||
      !Number.isSafeInteger(checksum) || checksum < 0 || checksum > 0xffffffff) {
    throw new RangeError('Invalid UR fountain header');
  }
  if (seqNum <= seqLen) return [seqNum - 1];
  const rng = await UrTestXoshiro256.fromSeed(concatBytes(writeU32(seqNum), writeU32(checksum)));
  const degree = new AliasChooser(seqLen).next(rng) + 1;
  const remaining = Array.from({ length: seqLen }, (_, i) => i);
  const selected: number[] = [];
  while (selected.length < degree) selected.push(remaining.splice(rng.nextIndex(remaining.length), 1)[0]!);
  return selected.sort((a, b) => a - b);
}

export type UrTestPart = Readonly<{
  seqNum: number; seqLen: number; messageLen: number; checksum: number; data: Uint8Array;
}>;

export interface UrTestEncodeOptions {
  /** Maximum raw bytes in a fountain fragment, excluding CBOR and Bytewords overhead. */
  readonly fragmentBytes?: number;
  /** Number of EXTRA deterministic fountain mixes after first seqLen pure frames. */
  readonly extraMixedFrames?: number;
}
export interface UrTestSequence {
  readonly type: 'bytes';
  readonly testOnly: true;
  readonly sourceBytes: number;
  readonly encodedCborBytes: number;
  readonly fragmentCount: number;
  readonly extraMixedFrames: number;
  readonly frames: readonly string[];
}

export function parseUrTestPart(text: string): UrTestPart {
  if (typeof text !== 'string' || text.length > 6000 || !/^ur:bytes\/[1-9]\d{0,9}-[1-9]\d{0,3}\/[a-z]+$/.test(text)) {
    throw new TypeError('Expected canonical multipart ur:bytes TEST frame');
  }
  const match = /^ur:bytes\/(\d+)-(\d+)\/([a-z]+)$/.exec(text)!;
  const seq = Number(match[1]!), count = Number(match[2]!);
  if (seq > 0xffffffff || count < 2 || count > MAX_PARTS) throw new RangeError('Out-of-range multipart UR sequence');
  const cbor = decodeDeterministicCbor(decodeBytewords(match[3]!, 'minimal'));
  if (!Array.isArray(cbor) || cbor.length !== 5 ||
      cbor.slice(0, 4).some(v => typeof v !== 'number') || !(cbor[4] instanceof Uint8Array)) {
    throw new TypeError('Invalid UR fountain CBOR part');
  }
  const [seqNum, seqLen, messageLen, checksum, bytes] = cbor as [number, number, number, number, Uint8Array];
  if (seqNum !== seq || seqLen !== count || messageLen < 1 || messageLen > MAX_DATA + 8 ||
      bytes.length < 1 || bytes.length > MAX_DATA ||
      count !== Math.ceil(messageLen / bytes.length) ||
      bytes.length * count > MAX_DATA + MAX_PARTS ||
      encodeDeterministicCbor(cbor).length > 5000) {
    throw new TypeError('Conflicting or noncanonical UR fountain part');
  }
  return Object.freeze({ seqNum, seqLen, messageLen, checksum, data: bytes });
}

/** Test-only standard `ur:bytes` sequence. No custom ByteFables UR type is advertised. */
export async function encodeUrBytesMultipartTestOnly(
  publicBytes: Uint8Array, opts: UrTestEncodeOptions = {}
): Promise<UrTestSequence> {
  checkBytes(publicBytes, 'UR source');
  const encoded = encodeDeterministicCbor(publicBytes);
  const requested = opts.fragmentBytes ?? 80;
  const extra = opts.extraMixedFrames ?? 0;
  if (!Number.isSafeInteger(requested) || requested < 8 || requested > 512 ||
      !Number.isSafeInteger(extra) || extra < 0 || extra > 512) {
    throw new RangeError('Invalid UR fragment budget or redundancy');
  }
  if (encoded.length <= requested) {
    if (extra !== 0) throw new RangeError('A single-part UR does not carry extra fountain parts');
    return Object.freeze({ type: 'bytes' as const, testOnly: true as const,
      sourceBytes: publicBytes.length, encodedCborBytes: encoded.length, fragmentCount: 1,
      extraMixedFrames: 0, frames: Object.freeze([UR_PREFIX + encodeBytewords(encoded, 'minimal')]) });
  }
  const count = Math.ceil(encoded.length / requested);
  if (count > MAX_PARTS || count + extra > MAX_FRAMES) throw new RangeError('UR exceeds bounded fountain budget');
  const fragmentLen = Math.ceil(encoded.length / count);
  const fragments = Array.from({ length: count }, (_, i) => {
    const f = new Uint8Array(fragmentLen);
    f.set(encoded.slice(i * fragmentLen, (i + 1) * fragmentLen));
    return f;
  });
  const checksum = crc32(encoded);
  const frames: string[] = [];
  for (let seq = 1; seq <= count + extra; seq++) {
    const indices = await chooseUrTestFragments(seq, count, checksum);
    const mixed = new Uint8Array(fragmentLen);
    for (const i of indices) for (let j = 0; j < fragmentLen; j++) mixed[j] = mixed[j]! ^ fragments[i]![j]!;
    const payload = encodeDeterministicCbor([seq, count, encoded.length, checksum, mixed]);
    frames.push(`${UR_PREFIX}${seq}-${count}/${encodeBytewords(payload, 'minimal')}`);
  }
  return Object.freeze({ type: 'bytes' as const, testOnly: true as const,
    sourceBytes: publicBytes.length, encodedCborBytes: encoded.length,
    fragmentCount: count, extraMixedFrames: extra, frames: Object.freeze(frames) });
}

interface Row { mask: bigint; data: Uint8Array; }
const xorRows = (a: Uint8Array, b: Uint8Array): Uint8Array => {
  const result = new Uint8Array(a);
  for (let i = 0; i < result.length; i++) result[i] = result[i]! ^ b[i]!;
  return result;
};
function lowest(mask: bigint): number {
  if (!mask) throw new RangeError('Zero-pivot fountain row');
  let i = 0;
  while (!(mask & 1n)) { mask >>= 1n; i++; }
  return i;
}

/** Incremental, order-independent BCR-2024-001 fountain solver.
 * Linear Gaussian reduction (not a security/authentication scheme).
 */
export class UrBytesTestDecoder {
  private readonly seen = new Map<number, string>();
  private readonly rows = new Map<number, Row>();
  private header?: UrTestPart;
  private resultData?: Uint8Array;
  private single = false;

  get progress(): Readonly<{ receivedFrames: number; fragmentsSolved: number;
    requiredFragments: number; complete: boolean }> {
    return Object.freeze({ receivedFrames: this.seen.size,
      fragmentsSolved: this.rows.size,
      requiredFragments: this.header?.seqLen ?? (this.single ? 1 : 0),
      complete: !!this.resultData });
  }
  get result(): Uint8Array | null { return this.resultData ? new Uint8Array(this.resultData) : null; }

  async receive(text: string): Promise<boolean> {
    if (this.resultData) return false;
    if (typeof text !== 'string' || text.length > 6000) throw new TypeError('Invalid UR input length');
    if (/^ur:bytes\/[a-z]+$/.test(text)) {
      if (this.header || this.seen.size) throw new TypeError('Cannot mix single and multipart UR');
      const decoded = decodeDeterministicCbor(decodeBytewords(text.slice(UR_PREFIX.length), 'minimal'));
      if (!(decoded instanceof Uint8Array)) throw new TypeError('UR bytes must encode one CBOR byte string');
      checkBytes(decoded, 'Decoded test fixture');
      this.single = true;
      this.resultData = decoded;
      return true;
    }
    const part = parseUrTestPart(text);
    if (this.single) throw new TypeError('Cannot mix single and multipart UR');
    if (this.header) {
      if (part.seqLen !== this.header.seqLen || part.messageLen !== this.header.messageLen ||
          part.checksum !== this.header.checksum || part.data.length !== this.header.data.length) {
        throw new TypeError('Mixed or incompatible multipart UR session');
      }
    } else this.header = part;
    const old = this.seen.get(part.seqNum);
    if (old !== undefined) {
      if (old !== text) throw new TypeError('Conflicting duplicate UR fountain part');
      return false;
    }
    if (this.seen.size >= MAX_FRAMES) throw new RangeError('Too many UR frames');
    this.seen.set(part.seqNum, text);
    const indexes = await chooseUrTestFragments(part.seqNum, part.seqLen, part.checksum);
    let mask = indexes.reduce((acc, n) => acc | (1n << BigInt(n)), 0n);
    let data = new Uint8Array(part.data);
    for (const [pivot, existing] of [...this.rows].sort((a, b) => a[0] - b[0])) {
      if (mask & (1n << BigInt(pivot))) {
        mask ^= existing.mask;
        data = xorRows(data, existing.data);
      }
    }
    if (!mask) {
      if (data.some(v => v !== 0)) throw new TypeError('Inconsistent UR fountain constraints');
      return true;
    }
    const pivot = lowest(mask);
    for (const [key, previous] of this.rows) {
      if (previous.mask & (1n << BigInt(pivot))) this.rows.set(key,
        { mask: previous.mask ^ mask, data: xorRows(previous.data, data) });
    }
    this.rows.set(pivot, { mask, data });
    if (this.rows.size === part.seqLen) {
      const joined = new Uint8Array(part.seqLen * part.data.length);
      for (let i = 0; i < part.seqLen; i++) {
        const row = this.rows.get(i);
        if (!row || row.mask !== (1n << BigInt(i))) throw new TypeError('Fountain row reduction incomplete');
        joined.set(row.data, i * part.data.length);
      }
      if (joined.slice(part.messageLen).some(v => v !== 0)) throw new TypeError('UR padding is not zero');
      const source = joined.slice(0, part.messageLen);
      if (crc32(source) !== part.checksum) throw new TypeError('UR fountain message checksum mismatch');
      const decoded = decodeDeterministicCbor(source);
      if (!(decoded instanceof Uint8Array)) throw new TypeError('Multipart ur:bytes contains invalid CBOR');
      checkBytes(decoded, 'UR recovered fixture');
      this.resultData = decoded;
    }
    return true;
  }
}

export async function decodeUrBytesMultipartTestOnly(frames: readonly string[]): Promise<Uint8Array> {
  if (!Array.isArray(frames) || frames.length < 1 || frames.length > MAX_FRAMES) {
    throw new RangeError('Expected 1..1024 public UR frames');
  }
  const decoder = new UrBytesTestDecoder();
  for (const frame of frames) await decoder.receive(frame);
  if (!decoder.result) throw new RangeError('Incomplete multipart UR test sequence');
  return decoder.result;
}
