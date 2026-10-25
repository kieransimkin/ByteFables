/** ByteFables PUBLIC multipart QR transport v1.
 *
 * Intentionally NOT Blockchain Commons UR v2/MUR, which requires different
 * CBOR type registration and fountain-fragment selection. Each frame contains
 * printable Base64url of a versioned binary packet; frames are independent,
 * sequenced and checksummed. An optional XOR parity frame repairs ONE missing
 * frame, not multiple erasures and not malicious modification.
 */
import { PublicRecord, encodePublicRecord, decodePublicRecord } from '../framing/public-record.js';
import { encodeBase64, decodeBase64 } from '../codecs/base64.js';
import { crc32 } from '../utils/crc32.js';
import { readU32, writeU32, concatBytes } from '../utils/binary.js';
import { sha256 } from '../identity/sha256.js';
import { encodeHex } from '../codecs/hex.js';
import { encodeQrModel2, qrByteCapacity, type QrEcc, type QrResult } from './qr.js';

const HEADER = 39;
const PREFIX = 'BFQR1:';
const MAGIC = Uint8Array.of(66, 70, 81, 49); // BFQ1
const MAX_RECORD_BYTES = 262144;
const MAX_PARTS = 1024;

function readU16(data: Uint8Array, i: number): number { return data[i]! * 256 + data[i + 1]!; }
function writeU16(n: number): Uint8Array {
  if (!Number.isSafeInteger(n) || n < 0 || n > 65535) throw new RangeError('Expected u16');
  return Uint8Array.of(n >>> 8, n & 255);
}
const base64Length = (n: number): number => Math.ceil(n * 8 / 6);

export interface PublicQrPlanOptions {
  readonly ecc?: QrEcc;
  readonly maxVersion?: number;
  readonly fragmentBytes?: number;
  readonly parity?: boolean;
  /** Fixed QR mask for repeatable optical qualification; default 0 (ISO-valid). */
  readonly qrMask?: number;
}
export interface PublicQrFrame {
  readonly schema: 'bytefables.public-qr-frame.v1';
  readonly index: number;
  readonly count: number;
  readonly parity: boolean;
  readonly text: string;
  readonly qr: QrResult;
}
export interface PublicQrSession {
  readonly schema: 'bytefables.public-qr-session.v1';
  readonly sourceByteLength: number;
  readonly sessionId: string;
  readonly fragmentBytes: number;
  readonly dataFrames: number;
  readonly parityFrames: number;
  readonly qrErrorCorrection: QrEcc;
  readonly qrMaxVersion: number;
  readonly frames: readonly PublicQrFrame[];
}

function packet(sha: Uint8Array, whole: Uint8Array, fragment: Uint8Array,
  chunkBytes: number, count: number, index: number, parity: boolean): string {
  const part = new Uint8Array(HEADER + chunkBytes);
  part.set(MAGIC); part[4] = parity ? 1 : 0;
  part.set(sha.slice(0, 16), 5);
  part.set(writeU32(whole.length), 21);
  part.set(writeU16(chunkBytes), 25);
  part.set(writeU16(count), 27);
  part.set(writeU16(index), 29);
  part.set(writeU32(crc32(whole)), 31);
  part.set(fragment, HEADER);
  const code = crc32(concatBytes(part.slice(0, 35), part.slice(HEADER)));
  part.set(writeU32(code), 35);
  return PREFIX + encodeBase64(part, true);
}

/** ByteFables PUBLIC framed QR transport. Not compatible with UR v2/SeedQR. */
export async function encodePublicQrSession(
  record: PublicRecord, options: PublicQrPlanOptions = {}
): Promise<PublicQrSession> {
  if (!(record instanceof PublicRecord)) throw new TypeError('PublicRecord required');
  const whole = await encodePublicRecord(record);
  if (whole.length > MAX_RECORD_BYTES) throw new RangeError('Public QR record exceeds 256 KiB');
  const ecc = options.ecc ?? 'Q';
  const qrMask = options.qrMask ?? 0;
  if (!Number.isSafeInteger(qrMask) || qrMask < 0 || qrMask > 7) throw new RangeError('Invalid QR mask');
  const maxVersion = options.maxVersion ?? 12;
  if (!Number.isSafeInteger(maxVersion) || maxVersion < 1 || maxVersion > 40) {
    throw new RangeError('Invalid QR maximum version');
  }
  const capacity = qrByteCapacity(maxVersion, ecc);
  // All parts carry the same fixed-sized payload; decoding never guesses final padding.
  const maximumChunk = Math.min(1024, Math.floor((capacity - PREFIX.length) * 3 / 4) - HEADER - 1);
  if (maximumChunk < 1) throw new RangeError('QR version too small for typed-frame metadata');
  const chunkBytes = options.fragmentBytes ?? maximumChunk;
  if (!Number.isSafeInteger(chunkBytes) || chunkBytes < 1 || chunkBytes > maximumChunk) {
    throw new RangeError('Invalid QR frame fragment length for selected ECC/version');
  }
  const count = Math.ceil(whole.length / chunkBytes);
  if (count < 1 || count > MAX_PARTS) throw new RangeError('Too many QR frames');
  const sha = await sha256(whole);
  const useParity = options.parity ?? true;
  if (typeof useParity !== 'boolean') throw new TypeError('Invalid parity option');
  const frames: PublicQrFrame[] = [];
  const parity = new Uint8Array(chunkBytes);
  for (let i = 0; i < count + (useParity && count > 1 ? 1 : 0); i++) {
    const isParity = i === count;
    let fragment: Uint8Array;
    if (isParity) fragment = parity;
    else {
      fragment = new Uint8Array(chunkBytes);
      fragment.set(whole.slice(i * chunkBytes, (i + 1) * chunkBytes));
      for (let j = 0; j < chunkBytes; j++) parity[j] = parity[j]! ^ fragment[j]!;
    }
    const text = packet(sha, whole, fragment, chunkBytes, count, i, isParity);
    const qr = encodeQrModel2(new TextEncoder().encode(text), { ecc, maxVersion, mask: qrMask });
    frames.push(Object.freeze({ schema: 'bytefables.public-qr-frame.v1' as const,
      index: i, count, parity: isParity, text, qr }));
  }
  return Object.freeze({ schema: 'bytefables.public-qr-session.v1' as const,
    sourceByteLength: whole.length, sessionId: encodeHex(sha.slice(0, 16)),
    fragmentBytes: chunkBytes, dataFrames: count, parityFrames: useParity && count > 1 ? 1 : 0,
    qrErrorCorrection: ecc, qrMaxVersion: maxVersion,
    frames: Object.freeze(frames) });
}

type Parsed = { readonly id: string; readonly length: number; readonly chunkBytes: number;
  readonly count: number; readonly index: number; readonly crc: number; readonly parity: boolean;
  readonly bytes: Uint8Array; };
function parseFrame(text: string): Parsed {
  if (typeof text !== 'string' || !text.startsWith(PREFIX) || text.length > 5000) {
    throw new TypeError('Invalid BFQR1 frame');
  }
  const data = decodeBase64(text.slice(PREFIX.length), true);
  if (data.length < HEADER + 1 || MAGIC.some((b, i) => data[i] !== b) || (data[4] !== 0 && data[4] !== 1)) {
    throw new TypeError('Invalid BFQR1 packet header');
  }
  const parity = data[4] === 1;
  const id = encodeHex(data.slice(5, 21));
  const length = readU32(data, 21);
  const chunkBytes = readU16(data, 25);
  const count = readU16(data, 27);
  const index = readU16(data, 29);
  const crc = readU32(data, 31);
  const frameCrc = readU32(data, 35);
  if (length < 1 || length > MAX_RECORD_BYTES || chunkBytes < 1 || chunkBytes > 1024 ||
      count < 1 || count > MAX_PARTS || count !== Math.ceil(length / chunkBytes) ||
      (parity && index !== count) || (!parity && index >= count) ||
      (parity && count === 1) || data.length !== HEADER + chunkBytes ||
      crc32(concatBytes(data.slice(0, 35), data.slice(HEADER))) !== frameCrc) {
    throw new TypeError('Malformed or corrupted BFQR1 frame');
  }
  return { id, length, chunkBytes, count, index, crc, parity, bytes: data.slice(HEADER) };
}

/** Returns the original *typed* PUBLIC record, or rejects incomplete/mixed/tampered sessions. */
export async function decodePublicQrSession(textFrames: readonly string[]): Promise<PublicRecord> {
  if (!Array.isArray(textFrames) || textFrames.length === 0 || textFrames.length > MAX_PARTS + 1) {
    throw new RangeError('BFQR1 requires 1..1025 frames');
  }
  const fragments = new Map<number, Uint8Array>();
  let common: Parsed | undefined;
  for (const text of textFrames) {
    const frame = parseFrame(text);
    if (common === undefined) common = frame;
    else if (frame.id !== common.id || frame.length !== common.length || frame.count !== common.count ||
        frame.chunkBytes !== common.chunkBytes || frame.crc !== common.crc) {
      throw new TypeError('Frames belong to different or incompatible BFQR1 sessions');
    }
    const old = fragments.get(frame.index);
    if (old !== undefined && (old.length !== frame.bytes.length || old.some((b, i) => b !== frame.bytes[i]))) {
      throw new TypeError('Conflicting duplicate BFQR1 fragment');
    }
    fragments.set(frame.index, frame.bytes);
  }
  const session = common!;
  const missing: number[] = [];
  for (let i = 0; i < session.count; i++) if (!fragments.has(i)) missing.push(i);
  if (missing.length > 1 || (missing.length === 1 && !fragments.has(session.count))) {
    throw new RangeError('QR session incomplete: missing more fragments than available parity can restore');
  }
  if (missing.length === 1) {
    const reconstructed = new Uint8Array(fragments.get(session.count)!);
    for (let i = 0; i < session.count; i++) {
      const part = fragments.get(i);
      if (!part) continue;
      for (let j = 0; j < part.length; j++) reconstructed[j] = reconstructed[j]! ^ part[j]!;
    }
    fragments.set(missing[0]!, reconstructed);
  }
  // When present, even an unnecessary parity frame is checked for internal
  // consistency. A contradictory checksum-valid parity frame must not be ignored.
  if (fragments.has(session.count)) {
    const parity = new Uint8Array(session.chunkBytes);
    for (let i = 0; i < session.count; i++) {
      const part = fragments.get(i)!;
      for (let j = 0; j < parity.length; j++) parity[j] = parity[j]! ^ part[j]!;
    }
    if (parity.some((v, i) => v !== fragments.get(session.count)![i])) {
      throw new TypeError('BFQR1 parity contradiction');
    }
  }
  const assembled = new Uint8Array(session.count * session.chunkBytes);
  for (let i = 0; i < session.count; i++) assembled.set(fragments.get(i)!, i * session.chunkBytes);
  // Strict padding canonicalisation prevents accepting ambiguous alternative sessions.
  if (assembled.slice(session.length).some(v => v !== 0)) throw new TypeError('Nonzero BFQR1 final padding');
  const complete = assembled.slice(0, session.length);
  if (crc32(complete) !== session.crc) throw new TypeError('BFQR1 full checksum mismatch');
  const digest = await sha256(complete);
  if (encodeHex(digest.slice(0, 16)) !== session.id) throw new TypeError('BFQR1 commitment mismatch');
  return decodePublicRecord(complete);
}
