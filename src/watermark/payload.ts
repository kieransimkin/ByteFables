/**
 * Public-only watermark *message* v1. This does not embed or extract signals.
 * Media watermarking, error-correcting codes and blind detection belong in
 * FrameRudiments' independently tested carrier-specific pipelines.
 */
import { PublicRecord, publicRecordDigest } from '../framing/public-record.js';
import { crc32 } from '../utils/crc32.js';
import { concatBytes, readU32, writeU32 } from '../utils/binary.js';
import { encodeHex } from '../codecs/hex.js';

export const WATERMARK_MESSAGE_V1 = 'bytefables.watermark-message.v1';
/** SHA-256 prefix sizes supported by this early public binding specification. */
export type WatermarkDigestBytes = 12 | 16 | 32;
const PREFIX = Uint8Array.of(0x42, 0x46, 0x57, 0x4d, 1); // "BFWM", version 1
const LENGTHS: readonly WatermarkDigestBytes[] = [12, 16, 32];

export interface DecodedWatermarkMessage {
  readonly version: 1;
  readonly digestBytes: WatermarkDigestBytes;
  readonly fingerprint: string;
  /** Copy of the digest prefix, not enough to reconstruct the public record. */
  readonly digest: Uint8Array;
  readonly checksum: 'crc32-accidental';
}

/**
 * Exact message intended for an eventual ECC encoder + carrier-specific embedder.
 * Reusable across image/audio/video/text; message itself does not survive any
 * distortion until a separately qualified embedder + detector is implemented.
 */
export async function encodePublicWatermarkMessage(
  record: PublicRecord, digestBytes: WatermarkDigestBytes = 12
): Promise<Uint8Array> {
  if (!(record instanceof PublicRecord)) throw new TypeError('Typed public record required');
  if (!LENGTHS.includes(digestBytes)) throw new RangeError('Watermark digest must be 12, 16 or 32 bytes');
  const digest = (await publicRecordDigest(record)).slice(0, digestBytes);
  const body = concatBytes(PREFIX, Uint8Array.of(digestBytes), digest);
  return concatBytes(body, writeU32(crc32(body)));
}

/** Decode recovered, fully assembled message bits. CRC is not authentication. */
export function decodePublicWatermarkMessage(data: Uint8Array): DecodedWatermarkMessage {
  if (!(data instanceof Uint8Array) || ![22, 26, 42].includes(data.length)) {
    throw new TypeError('Invalid ByteFables watermark message length');
  }
  for (let i = 0; i < PREFIX.length; i++) {
    if (data[i] !== PREFIX[i]) throw new TypeError('Unknown watermark magic or version');
  }
  const count = data[5];
  if (count !== 12 && count !== 16 && count !== 32 || data.length !== count + 10) {
    throw new TypeError('Unsupported watermark digest size');
  }
  const checksum = readU32(data, data.length - 4);
  if (checksum !== crc32(data.subarray(0, data.length - 4))) {
    throw new TypeError('Watermark message CRC-32 mismatch');
  }
  const digest = data.slice(6, 6 + count);
  return { version: 1, digestBytes: count, fingerprint: `bfrec1-${encodeHex(digest)}`,
    digest, checksum: 'crc32-accidental' };
}

/**
 * Compare extracted candidate against the *full* typed public record's hash.
 * A matching unkeyed hash prefix is only a content lookup aid, NOT provenance,
 * evidence of ownership, or a replacement for a signature/C2PA hard binding.
 */
export async function matchesPublicWatermarkMessage(
  recovered: Uint8Array, candidate: PublicRecord
): Promise<boolean> {
  if (!(candidate instanceof PublicRecord)) throw new TypeError('Typed public record required');
  const decoded = decodePublicWatermarkMessage(recovered);
  const expected = await publicRecordDigest(candidate);
  let different = 0;
  for (let i = 0; i < decoded.digestBytes; i++) {
    different |= decoded.digest[i]! ^ expected[i]!;
  }
  return different === 0;
}
