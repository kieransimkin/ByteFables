/** ByteFables public-only typed archival demonstration record (NOT a wallet backup). */
import { ByteValue, assertPublicValue, type PublicByteValue } from '../value.js';
import { concatBytes } from '../utils/binary.js';
import { encodeHex } from '../codecs/hex.js';
import { sha256 } from '../identity/sha256.js';
import { type CborValue, decodeDeterministicCbor, encodeDeterministicCbor } from './cbor.js';

export type ByteOrder = 'na' | 'big' | 'little';
export interface PublicRecordOptions {
  /** Algorithm describes the bytes ("opaque" when not interpreted). */
  readonly algorithm?: string;
  /** Empty string is the canonical spelling of no network. */
  readonly network?: string;
  readonly endian?: ByteOrder;
  readonly schemaVersion?: number;
}
const NAME = /^[a-z][a-z0-9._:/-]{0,127}$/;
const DOMAIN = new TextEncoder().encode('ByteFables:public-cbor-envelope:v1\0');
const MAGIC = 'BF-PUBLIC';

function name(v: unknown, label: string, allowEmpty = false): string {
  if (typeof v !== 'string' || !(allowEmpty && v === '') && !NAME.test(v)) {
    throw new TypeError(`Invalid public record ${label}`);
  }
  return v;
}

export class PublicRecord {
  readonly value: PublicByteValue;
  readonly algorithm: string;
  readonly network: string;
  readonly endian: ByteOrder;
  readonly schemaVersion: number;

  constructor(value: PublicByteValue, options: PublicRecordOptions = {}) {
    assertPublicValue(value);
    this.value = value;
    this.algorithm = name(options.algorithm ?? 'opaque', 'algorithm');
    this.network = name(options.network ?? '', 'network', true);
    const endian = options.endian ?? 'na';
    if (!['na', 'big', 'little'].includes(endian)) throw new TypeError('Invalid byte order');
    this.endian = endian;
    const schemaVersion = options.schemaVersion ?? 1;
    if (!Number.isSafeInteger(schemaVersion) || schemaVersion < 1 || schemaVersion > 65535) {
      throw new RangeError('Invalid schema version');
    }
    this.schemaVersion = schemaVersion;
    Object.freeze(this);
  }

  get namespace(): string { return this.value.namespace; }
  get kind(): string { return this.value.kind; }
  get byteLength(): number { return this.value.byteLength; }
  toBytes(): Uint8Array { return this.value.toBytes(); }
}

function fields(record: PublicRecord): Map<number, CborValue> {
  return new Map<number, CborValue>([
    [0, record.namespace], [1, record.kind], [2, record.algorithm],
    [3, record.network], [4, record.endian], [5, record.schemaVersion]
  ]);
}

function body(record: PublicRecord): Map<number, CborValue> {
  return new Map<number, CborValue>([
    [0, MAGIC], [1, 1], [2, fields(record)],
    [3, record.byteLength], [4, record.toBytes()]
  ]);
}

/** Typed public record commitment covers ALL context fields, unlike legacy bf1 fingerprints. */
export async function publicRecordDigest(record: PublicRecord): Promise<Uint8Array> {
  if (!(record instanceof PublicRecord)) throw new TypeError('PublicRecord required');
  return sha256(concatBytes(DOMAIN, encodeDeterministicCbor(body(record))));
}

/** Human verification aid only. Not an authenticated identity or key fingerprint. */
export async function publicRecordFingerprint(record: PublicRecord, count = 12): Promise<string> {
  if (!Number.isInteger(count) || count < 12 || count > 32) {
    throw new RangeError('Fingerprint length must be 12–32 bytes');
  }
  return `bfrec1-${encodeHex((await publicRecordDigest(record)).slice(0, count))}`;
}

/** Output is canonical CBOR with an unkeyed SHA-256 integrity check. Public data ONLY. */
export async function encodePublicRecord(record: PublicRecord): Promise<Uint8Array> {
  if (!(record instanceof PublicRecord)) throw new TypeError('PublicRecord required');
  const payload = body(record);
  const digest = await publicRecordDigest(record);
  payload.set(5, digest);
  return encodeDeterministicCbor(payload);
}

function hasOnlyKeys(value: CborValue, keys: readonly number[]): value is Map<number, CborValue> {
  return value instanceof Map && value.size === keys.length && keys.every(k => value.has(k));
}
function requireString(map: Map<number, CborValue>, key: number): string {
  const v = map.get(key);
  if (typeof v !== 'string') throw new TypeError('Incorrect CBOR metadata type');
  return v;
}
function requireNumber(map: Map<number, CborValue>, key: number): number {
  const v = map.get(key);
  if (typeof v !== 'number') throw new TypeError('Incorrect CBOR integer type');
  return v;
}

/** Decoder rejects malleable CBOR, bad checksums, extra fields, and sensitive kinds. */
export async function decodePublicRecord(bytes: Uint8Array): Promise<PublicRecord> {
  const decoded = decodeDeterministicCbor(bytes);
  if (!hasOnlyKeys(decoded, [0, 1, 2, 3, 4, 5]) || decoded.get(0) !== MAGIC ||
      decoded.get(1) !== 1) {
    throw new TypeError('Invalid ByteFables public CBOR envelope');
  }
  const context = decoded.get(2)!;
  if (!hasOnlyKeys(context, [0, 1, 2, 3, 4, 5])) {
    throw new TypeError('Invalid ByteFables public context');
  }
  const payload = decoded.get(4);
  const digest = decoded.get(5);
  if (!(payload instanceof Uint8Array) || !(digest instanceof Uint8Array) || digest.length !== 32 ||
      requireNumber(decoded, 3) !== payload.length) {
    throw new TypeError('Incorrect payload length or integrity field');
  }
  // Recompute from the exact parsed typed fields, never by accepting unchecked extension keys.
  const withoutDigest = new Map(decoded);
  withoutDigest.delete(5);
  const expected = await sha256(concatBytes(DOMAIN, encodeDeterministicCbor(withoutDigest)));
  let mismatch = 0;
  for (let i = 0; i < 32; i++) mismatch |= expected[i]! ^ digest[i]!;
  if (mismatch !== 0) throw new TypeError('Public record integrity check failed');
  const value = ByteValue.public(payload, {
    namespace: requireString(context, 0), kind: requireString(context, 1)
  });
  const endian = requireString(context, 4);
  if (endian !== 'big' && endian !== 'little' && endian !== 'na') {
    throw new TypeError('Invalid public record byte order');
  }
  return new PublicRecord(value, {
    algorithm: requireString(context, 2),
    network: requireString(context, 3),
    endian,
    schemaVersion: requireNumber(context, 5)
  });
}
