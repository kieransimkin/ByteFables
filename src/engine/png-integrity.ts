/** CRC-checked PNG chunk inspection for PUBLIC artwork receipts.
 * This checks file transport integrity, not decompression or pixel fidelity.
 */
export interface PngIntegrity {
  readonly chunkCount: number;
  readonly idatChunks: number;
  readonly crcVerified: true;
}
const SIGNATURE = [137, 80, 78, 71, 13, 10, 26, 10] as const;
const U32 = (bytes: Uint8Array, at: number): number =>
  ((bytes[at]! * 0x1000000) + (bytes[at + 1]! << 16) +
    (bytes[at + 2]! << 8) + bytes[at + 3]!) >>> 0;

/** Standard PNG CRC-32 (ISO 3309), calculated across type + data. */
export function pngCrc32(bytes: Uint8Array): number {
  if (!(bytes instanceof Uint8Array)) throw new TypeError('PNG CRC input must be bytes');
  let crc = 0xffffffff;
  for (const octet of bytes) {
    crc ^= octet;
    for (let bit = 0; bit < 8; bit++) crc = crc & 1 ? (crc >>> 1) ^ 0xedb88320 : crc >>> 1;
  }
  return (crc ^ 0xffffffff) >>> 0;
}

/** Bounded chunk walk: requires valid CRCs, order and contiguous IDAT sequence.
 * It intentionally does not decode DEFLATE streams, validate the PNG filter
 * reconstruction or establish that the visible image matches the identity.
 */
export function verifyArtworkPngChunks(bytes: Uint8Array): PngIntegrity {
  if (!(bytes instanceof Uint8Array) || bytes.length < 57 ||
      bytes.length > 128 * 1024 * 1024 ||
      !SIGNATURE.every((n, i) => bytes[i] === n)) {
    throw new TypeError('Invalid PNG signature or size');
  }
  let offset = 8, chunkCount = 0, idatChunks = 0;
  let header = false, ended = false, afterIdat = false, palette = false;
  let colourType = -1;
  while (offset < bytes.length) {
    if (bytes.length - offset < 12) throw new TypeError('Truncated PNG chunk');
    const length = U32(bytes, offset);
    if (length > bytes.length - offset - 12) throw new TypeError('PNG chunk length exceeds file');
    const typeBytes = bytes.subarray(offset + 4, offset + 8);
    const type = String.fromCharCode(...typeBytes);
    if (!/^[A-Za-z]{4}$/.test(type) || (typeBytes[2]! & 0x20) !== 0)
      throw new TypeError('Malformed or noncanonical PNG chunk type');
    const end = offset + 12 + length;
    const actual = U32(bytes, end - 4);
    const expected = pngCrc32(bytes.subarray(offset + 4, end - 4));
    if (actual !== expected) throw new TypeError(`PNG CRC mismatch in ${type}`);
    if (!header && (type !== 'IHDR' || length !== 13)) throw new TypeError('PNG must start with IHDR');
    if (type === 'IHDR') {
      if (header || offset !== 8 || length !== 13) throw new TypeError('Duplicate PNG IHDR');
      header = true;
      colourType = bytes[offset + 17]!;
    } else if (type === 'PLTE') {
      if (palette || idatChunks || length === 0 || length % 3 !== 0 || length > 768 || colourType === 0 || colourType === 4)
        throw new TypeError('Invalid PNG palette');
      palette = true;
    } else if (type === 'IDAT') {
      if (afterIdat || (colourType === 3 && !palette)) throw new TypeError('Invalid PNG IDAT ordering');
      idatChunks++;
    } else if (type === 'IEND') {
      if (!idatChunks || length !== 0 || end !== bytes.length) throw new TypeError('Invalid PNG IEND');
      ended = true;
    } else if ((typeBytes[0]! & 0x20) === 0) {
      throw new TypeError(`Unsupported critical PNG chunk: ${type}`);
    }
    if (idatChunks && type !== 'IDAT') afterIdat = true;
    offset = end;
    chunkCount++;
    if (chunkCount > 100000) throw new RangeError('PNG has too many chunks');
    if (ended) break;
  }
  if (!header || !idatChunks || !ended || offset !== bytes.length) throw new TypeError('Incomplete PNG structure');
  return Object.freeze({ chunkCount, idatChunks, crcVerified: true as const });
}
