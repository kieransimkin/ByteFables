/** QR Code Model 2, byte mode, versions 1-40, four ISO error-correction levels.
 * Produces a public, unstyled ModuleMatrix for FrameRudiments to rasterise.
 * No secret inputs, images, fonts, compression, ECI, Kanji, structured append,
 * arbitrary text encoding or scanning are provided by this module.
 *
 * QR tables implement the published ISO/IEC 18004 Model 2 block parameters.
 */
import { ModuleMatrix } from '../ir/module-matrix.js';

export type QrEcc = 'L' | 'M' | 'Q' | 'H';
export interface QrOptions {
  readonly ecc?: QrEcc;
  readonly minVersion?: number;
  readonly maxVersion?: number;
  readonly mask?: number;
}
export interface QrResult {
  readonly schema: 'bytefables.qr-model2-byte.v1';
  readonly version: number;
  readonly ecc: QrEcc;
  readonly mask: number;
  readonly dataBytes: number;
  readonly dataCapacityBytes: number;
  readonly matrix: ModuleMatrix;
}

const LEVELS: readonly QrEcc[] = ['L', 'M', 'Q', 'H'];
const TABLE: Readonly<Record<QrEcc, readonly [readonly number[], readonly number[]]>> = {
  L: [
    [7,10,15,20,26,18,20,24,30,18,20,24,26,30,22,24,28,30,28,28,28,28,30,30,26,28,30,30,30,30,30,30,30,30,30,30,30,30,30,30],
    [1,1,1,1,1,2,2,2,2,4,4,4,4,4,6,6,6,6,7,8,8,9,9,10,12,12,12,13,14,15,16,17,18,19,19,20,21,22,24,25]
  ],
  M: [
    [10,16,26,18,24,16,18,22,22,26,30,22,22,24,24,28,28,26,26,26,26,28,28,28,28,28,28,28,28,28,28,28,28,28,28,28,28,28,28,28],
    [1,1,1,2,2,4,4,4,5,5,5,8,9,9,10,10,11,13,14,16,17,17,18,20,21,23,25,26,28,29,31,33,35,37,38,40,43,45,47,49]
  ],
  Q: [
    [13,22,18,26,18,24,18,22,20,24,28,26,24,20,30,24,28,28,26,30,28,30,30,30,30,28,30,30,30,30,30,30,30,30,30,30,30,30,30,30],
    [1,1,2,2,4,4,6,6,8,8,8,10,12,16,12,17,16,18,21,20,23,23,25,27,29,34,34,35,38,40,43,45,48,51,53,56,59,62,65,68]
  ],
  H: [
    [17,28,22,16,22,28,26,26,24,28,24,28,22,24,24,30,28,28,26,28,30,24,30,30,30,30,30,30,30,30,30,30,30,30,30,30,30,30,30,30],
    [1,1,2,4,4,4,5,6,8,8,11,11,16,16,18,16,19,21,25,25,25,34,30,32,35,37,40,42,45,48,51,54,57,60,63,66,70,74,77,81]
  ]
};

function rawDataModules(ver: number): number {
  let n = (16 * ver + 128) * ver + 64;
  if (ver >= 2) {
    const align = Math.floor(ver / 7) + 2;
    n -= (25 * align - 10) * align - 55;
    if (ver >= 7) n -= 36;
  }
  return n;
}
function capacityCodewords(ver: number, ecc: QrEcc): number {
  return Math.floor(rawDataModules(ver) / 8) - TABLE[ecc][0][ver - 1]! * TABLE[ecc][1][ver - 1]!;
}
/** Exact maximum source byte count of QR byte mode for a chosen version/ECC. */
export function qrByteCapacity(version: number, ecc: QrEcc = 'M'): number {
  if (!Number.isSafeInteger(version) || version < 1 || version > 40 || !LEVELS.includes(ecc)) {
    throw new RangeError('Invalid QR version or error-correction level');
  }
  const countBits = version <= 9 ? 8 : 16;
  return Math.min((1 << countBits) - 1, Math.floor((capacityCodewords(version, ecc) * 8 - 4 - countBits) / 8));
}

function gfMultiply(a: number, b: number): number {
  let z = 0;
  for (let i = 7; i >= 0; i--) {
    z = (z << 1) ^ (((z >>> 7) & 1) * 0x11d);
    z ^= ((b >>> i) & 1) * a;
  }
  return z;
}
function reedSolomonDivisor(degree: number): Uint8Array {
  const divisor = new Uint8Array(degree);
  divisor[degree - 1] = 1;
  let root = 1;
  for (let i = 0; i < degree; i++) {
    for (let j = 0; j < degree; j++) {
      divisor[j] = gfMultiply(divisor[j]!, root);
      if (j + 1 < degree) divisor[j] = divisor[j]! ^ divisor[j + 1]!;
    }
    root = gfMultiply(root, 0x02);
  }
  return divisor;
}
function reedSolomonRemainder(data: Uint8Array, divisor: Uint8Array): Uint8Array {
  const remainder = new Uint8Array(divisor.length);
  for (const byte of data) {
    const factor = byte ^ remainder[0]!;
    remainder.copyWithin(0, 1);
    remainder[remainder.length - 1] = 0;
    for (let j = 0; j < remainder.length; j++) remainder[j] = remainder[j]! ^ gfMultiply(divisor[j]!, factor);
  }
  return remainder;
}
function addBits(output: number[], value: number, length: number): void {
  if (!Number.isSafeInteger(value) || value < 0 || value >= 2 ** length) throw new RangeError('Invalid QR bit field');
  for (let i = length - 1; i >= 0; i--) output.push((value >>> i) & 1);
}
function makeDataCodewords(data: Uint8Array, version: number, ecc: QrEcc): Uint8Array {
  const capacity = capacityCodewords(version, ecc);
  const bits: number[] = [];
  addBits(bits, 4, 4); // byte mode
  addBits(bits, data.length, version <= 9 ? 8 : 16);
  for (const byte of data) addBits(bits, byte, 8);
  const total = capacity * 8;
  if (bits.length > total) throw new RangeError('QR capacity exceeded');
  addBits(bits, 0, Math.min(4, total - bits.length));
  while (bits.length % 8 !== 0) bits.push(0);
  const bytes = Uint8Array.from(Array.from({ length: bits.length / 8 }, (_, i) =>
    bits.slice(i * 8, (i + 1) * 8).reduce((n, b) => n * 2 + b, 0)));
  const out = new Uint8Array(capacity);
  out.set(bytes);
  for (let i = bytes.length; i < capacity; i++) out[i] = i % 2 === bytes.length % 2 ? 0xec : 0x11;
  return out;
}
function addEccAndInterleave(data: Uint8Array, version: number, level: QrEcc): Uint8Array {
  const numBlocks = TABLE[level][1][version - 1]!;
  const ecc = TABLE[level][0][version - 1]!;
  const raw = Math.floor(rawDataModules(version) / 8);
  const shortCount = numBlocks - raw % numBlocks;
  const shortDataSize = Math.floor(raw / numBlocks) - ecc;
  const divisor = reedSolomonDivisor(ecc);
  const blocks: { data: Uint8Array; parity: Uint8Array }[] = [];
  let offset = 0;
  for (let j = 0; j < numBlocks; j++) {
    const length = shortDataSize + (j >= shortCount ? 1 : 0);
    const chunk = data.slice(offset, offset + length);
    blocks.push({ data: chunk, parity: reedSolomonRemainder(chunk, divisor) });
    offset += length;
  }
  if (offset !== data.length) throw new Error('QR interleaving length mismatch');
  const result = new Uint8Array(raw);
  let k = 0;
  for (let i = 0; i <= shortDataSize; i++) {
    for (const block of blocks) if (i < block.data.length) result[k++] = block.data[i]!;
  }
  for (let i = 0; i < ecc; i++) for (const block of blocks) result[k++] = block.parity[i]!;
  if (k !== raw) throw new Error('QR codeword count mismatch');
  return result;
}

function alignmentPositions(version: number, size: number): number[] {
  if (version === 1) return [];
  const n = Math.floor(version / 7) + 2;
  const step = version === 32 ? 26 : Math.ceil((size - 13) / (n - 1) / 2) * 2;
  const result = [6];
  for (let i = n - 2; i >= 0; i--) result.push(size - 7 - i * step);
  return result;
}
const ECL_FORMAT: Record<QrEcc, number> = { L: 1, M: 0, Q: 3, H: 2 };
function formatBits(ecc: QrEcc, mask: number): number {
  const data = (ECL_FORMAT[ecc] << 3) | mask;
  let rem = data;
  for (let i = 0; i < 10; i++) rem = (rem << 1) ^ ((rem >>> 9) * 0x537);
  return ((data << 10) | rem) ^ 0x5412;
}
function maskAt(id: number, x: number, y: number): boolean {
  switch (id) {
    case 0: return (x + y) % 2 === 0;
    case 1: return y % 2 === 0;
    case 2: return x % 3 === 0;
    case 3: return (x + y) % 3 === 0;
    case 4: return (Math.floor(x / 3) + Math.floor(y / 2)) % 2 === 0;
    case 5: return (x * y) % 2 + (x * y) % 3 === 0;
    case 6: return ((x * y) % 2 + (x * y) % 3) % 2 === 0;
    case 7: return ((x + y) % 2 + (x * y) % 3) % 2 === 0;
    default: throw new RangeError('Invalid QR mask');
  }
}
function penaltyScore(mods: Uint8Array, size: number): number {
  const at = (x: number, y: number) => mods[y * size + x]!;
  let score = 0;
  for (let vertical = 0; vertical < 2; vertical++) {
    for (let line = 0; line < size; line++) {
      let run = 1;
      for (let j = 1; j < size; j++) {
        const a = vertical ? at(line, j) : at(j, line);
        const b = vertical ? at(line, j - 1) : at(j - 1, line);
        if (a === b) run++;
        else { if (run >= 5) score += 3 + run - 5; run = 1; }
      }
      if (run >= 5) score += 3 + run - 5;
      // Finder-like 1:1:3:1:1 with >=4 light modules on either side.
      for (let j = 0; j + 7 <= size; j++) {
        const lineAt = (t: number) => vertical ? at(line, t) : at(t, line);
        const pat = [1, 0, 1, 1, 1, 0, 1];
        if (pat.every((b, k) => lineAt(j + k) === b) &&
          ((j >= 4 && [1, 2, 3, 4].every(k => lineAt(j - k) === 0)) ||
           (j + 11 <= size && [7, 8, 9, 10].every(k => lineAt(j + k) === 0)))) score += 40;
      }
    }
  }
  for (let y = 0; y < size - 1; y++) for (let x = 0; x < size - 1; x++) {
    const k = at(x, y);
    if (k === at(x + 1, y) && k === at(x, y + 1) && k === at(x + 1, y + 1)) score += 3;
  }
  let black = 0;
  for (const bit of mods) black += bit;
  score += Math.floor(Math.abs(black * 20 - size * size * 10) / (size * size)) * 10;
  return score;
}

/** Create an ISO Model 2 symbol using byte-mode encoding and a 4-module quiet zone. */
export function encodeQrModel2(publicBytes: Uint8Array, options: QrOptions = {}): QrResult {
  if (!(publicBytes instanceof Uint8Array) || publicBytes.length > 2953) {
    throw new TypeError('QR byte input must be a bounded public Uint8Array');
  }
  const ecc = options.ecc ?? 'M';
  const min = options.minVersion ?? 1;
  const max = options.maxVersion ?? 40;
  if (!LEVELS.includes(ecc) || !Number.isSafeInteger(min) || !Number.isSafeInteger(max) ||
      min < 1 || max > 40 || min > max ||
      (options.mask !== undefined && (!Number.isSafeInteger(options.mask) || options.mask < 0 || options.mask > 7))) {
    throw new RangeError('Invalid QR ECC, version bounds or mask');
  }
  let version = min;
  while (version <= max && publicBytes.length > qrByteCapacity(version, ecc)) version++;
  if (version > max) throw new RangeError(`QR byte input too large for ECC ${ecc} through version ${max}`);
  const size = version * 4 + 17;
  const codewords = addEccAndInterleave(makeDataCodewords(publicBytes, version, ecc), version, ecc);
  const base = new Uint8Array(size * size);
  const isFunction = new Uint8Array(size * size);
  const set = (x: number, y: number, dark: boolean) => {
    if (x < 0 || y < 0 || x >= size || y >= size) return;
    const pos = y * size + x;
    base[pos] = dark ? 1 : 0; isFunction[pos] = 1;
  };
  // Timing patterns first; finder/separators override their crossing points.
  for (let i = 0; i < size; i++) { set(6, i, i % 2 === 0); set(i, 6, i % 2 === 0); }
  const finder = (cx: number, cy: number) => {
    for (let dy = -4; dy <= 4; dy++) for (let dx = -4; dx <= 4; dx++) {
      const d = Math.max(Math.abs(dx), Math.abs(dy));
      set(cx + dx, cy + dy, d !== 2 && d !== 4);
    }
  };
  finder(3, 3); finder(size - 4, 3); finder(3, size - 4);
  const align = alignmentPositions(version, size);
  for (let i = 0; i < align.length; i++) for (let j = 0; j < align.length; j++) {
    if ((i === 0 && j === 0) || (i === 0 && j === align.length - 1) ||
        (i === align.length - 1 && j === 0)) continue;
    const ax = align[i]!, ay = align[j]!;
    for (let y = -2; y <= 2; y++) for (let x = -2; x <= 2; x++) {
      set(ax + x, ay + y, Math.max(Math.abs(x), Math.abs(y)) !== 1);
    }
  }
  // Reserve fixed format/version locations before laying down payload bits.
  for (let i = 0; i <= 8; i++) { if (i !== 6) { set(8, i, false); set(i, 8, false); } }
  for (let i = 0; i < 8; i++) { set(size - 1 - i, 8, false); set(8, size - 1 - i, false); }
  set(8, size - 8, true);
  if (version >= 7) {
    const v = version;
    let rem = v;
    for (let i = 0; i < 12; i++) rem = (rem << 1) ^ (((rem >>> 11) & 1) * 0x1f25);
    const bits = (v << 12) | rem;
    for (let i = 0; i < 18; i++) {
      const bit = ((bits >>> i) & 1) !== 0;
      const a = size - 11 + i % 3;
      const b = Math.floor(i / 3);
      set(a, b, bit); set(b, a, bit);
    }
  }
  let bitPos = 0;
  for (let right = size - 1; right >= 1; right -= 2) {
    if (right === 6) right = 5;
    for (let vert = 0; vert < size; vert++) {
      const y = ((right + 1) & 2) === 0 ? size - 1 - vert : vert;
      for (let j = 0; j < 2; j++) {
        const x = right - j, pos = y * size + x;
        if (isFunction[pos]) continue;
        base[pos] = bitPos < codewords.length * 8 ?
          ((codewords[bitPos >>> 3]! >>> (7 - (bitPos & 7))) & 1) : 0;
        bitPos++;
      }
    }
  }
  if (bitPos !== rawDataModules(version)) throw new Error('QR function/data bit count invariant broken');
  const drawFormat = (target: Uint8Array, mask: number): void => {
    const bits = formatBits(ecc, mask);
    const b = (i: number) => (bits >>> i) & 1;
    for (let i = 0; i <= 5; i++) target[i * size + 8] = b(i);
    target[7 * size + 8] = b(6); target[8 * size + 8] = b(7);
    target[8 * size + 7] = b(8);
    for (let i = 9; i < 15; i++) target[8 * size + 14 - i] = b(i);
    for (let i = 0; i < 8; i++) target[8 * size + size - 1 - i] = b(i);
    for (let i = 8; i < 15; i++) target[(size - 15 + i) * size + 8] = b(i);
    target[(size - 8) * size + 8] = 1;
  };
  const choose = (mask: number): Uint8Array => {
    const modules = new Uint8Array(base);
    for (let y = 0; y < size; y++) for (let x = 0; x < size; x++) {
      const k = y * size + x;
      if (!isFunction[k] && maskAt(mask, x, y)) modules[k] = modules[k]! ^ 1;
    }
    drawFormat(modules, mask);
    return modules;
  };
  let bestMask = options.mask ?? 0;
  let best = choose(bestMask);
  if (options.mask === undefined) {
    let score = penaltyScore(best, size);
    for (let mask = 1; mask < 8; mask++) {
      const trial = choose(mask), next = penaltyScore(trial, size);
      if (next < score) { bestMask = mask; best = trial; score = next; }
    }
  }
  return Object.freeze({ schema: 'bytefables.qr-model2-byte.v1' as const, version, ecc,
    mask: bestMask, dataBytes: publicBytes.length, dataCapacityBytes: qrByteCapacity(version, ecc),
    matrix: new ModuleMatrix({ formatId: 'symbol/qr-model2', width: size, height: size,
      quietZone: 4, modules: best }) });
}
