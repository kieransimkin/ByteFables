/** Bitcoin Base58Check: mandatory explicit version bytes plus double-SHA256 CRC-like check.
 * It detects transcription mistakes but does not authenticate keys or addresses.
 */
import { sha256 } from '../identity/sha256.js';
import { concatBytes } from '../utils/binary.js';
const ALPHABET = '123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz';

export function encodeBase58(bytes: Uint8Array): string {
  if (!(bytes instanceof Uint8Array) || bytes.length > 256) throw new RangeError('Base58 supports up to 256 bytes');
  let number = 0n;
  for (const b of bytes) number = (number << 8n) | BigInt(b);
  let digits = '';
  while (number > 0n) {
    const remainder = Number(number % 58n);
    digits = ALPHABET[remainder]! + digits;
    number /= 58n;
  }
  for (const b of bytes) { if (b !== 0) break; digits = '1' + digits; }
  return digits;
}

export function decodeBase58(encoded: string): Uint8Array {
  if (typeof encoded !== 'string' || encoded.length > 350) throw new TypeError('Invalid Base58 length');
  let number = 0n;
  for (const c of encoded) {
    const digit = ALPHABET.indexOf(c);
    if (digit < 0) throw new TypeError('Invalid Base58 character');
    number = number * 58n + BigInt(digit);
  }
  const decoded: number[] = [];
  while (number > 0n) {
    decoded.unshift(Number(number & 255n));
    number >>= 8n;
  }
  const zeroes = encoded.match(/^1*/)?.[0].length ?? 0;
  const result = Uint8Array.from([...Array<number>(zeroes).fill(0), ...decoded]);
  if (result.length > 256 || encodeBase58(result) !== encoded) throw new TypeError('Noncanonical Base58');
  return result;
}

async function checksum(data: Uint8Array): Promise<Uint8Array> {
  return (await sha256(await sha256(data))).slice(0, 4);
}

/** Version is mandatory; callers must determine the right network and key type. */
export async function encodeBase58Check(payload: Uint8Array, version: Uint8Array): Promise<string> {
  if (!(payload instanceof Uint8Array) || !(version instanceof Uint8Array) ||
      version.length < 1 || version.length > 4 || payload.length > 248) {
    throw new TypeError('Explicit 1–4 byte version and bounded payload required');
  }
  const body = concatBytes(version, payload);
  return encodeBase58(concatBytes(body, await checksum(body)));
}

export async function decodeBase58Check(encoded: string, versionLength: number): Promise<{ version: Uint8Array; payload: Uint8Array }> {
  if (!Number.isInteger(versionLength) || versionLength < 1 || versionLength > 4) {
    throw new RangeError('Explicit version length required');
  }
  const bytes = decodeBase58(encoded);
  if (bytes.length < versionLength + 4) throw new TypeError('Truncated Base58Check');
  const body = bytes.slice(0, -4);
  const expected = await checksum(body);
  let diff = 0;
  for (let i = 0; i < 4; i++) diff |= expected[i]! ^ bytes[body.length + i]!;
  if (diff !== 0) throw new TypeError('Base58Check checksum mismatch');
  return { version: body.slice(0, versionLength), payload: body.slice(versionLength) };
}

/** Variant that rejects network/version ambiguity instead of returning an unchecked version. */
export async function decodeBase58CheckForVersion(encoded: string, expectedVersion: Uint8Array): Promise<Uint8Array> {
  if (!(expectedVersion instanceof Uint8Array) || expectedVersion.length < 1 || expectedVersion.length > 4) {
    throw new TypeError('Expected explicit version bytes');
  }
  const record = await decodeBase58Check(encoded, expectedVersion.length);
  let diff = 0;
  for (let i = 0; i < expectedVersion.length; i++) diff |= record.version[i]! ^ expectedVersion[i]!;
  if (diff) throw new TypeError('Base58Check unexpected network/version prefix');
  return record.payload;
}
