/** Independently validate completed PNG exports from the FrameRudiments host.
 * ByteFables never rasterises artwork or treats a digest as proof of authorship.
 */
import { sha256 } from '../identity/sha256.js';
import { encodeHex } from '../codecs/hex.js';
import { ARTWORK_ATLAS_VERSION, type ArtworkAtlasPlan } from './artwork-atlas.js';

export const ARTWORK_EXPORT_RECEIPT_VERSION = 'bytefables.artwork-export-receipt.v1' as const;
export interface ArtworkPngPage {
  readonly pageIndex: number;
  readonly pngBytes: Uint8Array;
}
export interface ArtworkPngReceiptPage {
  readonly pageIndex: number;
  readonly width: number;
  readonly height: number;
  readonly byteLength: number;
  readonly sha256Hex: string;
  readonly tileCount: number;
}
export interface ArtworkPngReceipt {
  readonly version: typeof ARTWORK_EXPORT_RECEIPT_VERSION;
  readonly atlasVersion: typeof ARTWORK_ATLAS_VERSION;
  readonly inputCount: number;
  readonly publicOnly: true;
  readonly guarantee: 'presentation-only';
  readonly pages: readonly ArtworkPngReceiptPage[];
}
const SIGNATURE = [137,80,78,71,13,10,26,10];
function u32(bytes: Uint8Array, p: number): number {
  return (bytes[p]! * 0x1000000 + (bytes[p+1]! << 16) + (bytes[p+2]! << 8) + bytes[p+3]!) >>> 0;
}
/** Minimal strict PNG container walk. Does not replace an independent pixel decoder. */
export function inspectArtworkPng(bytes: Uint8Array): { width: number; height: number } {
  if (!(bytes instanceof Uint8Array) || bytes.length < 45 || bytes.length > 128 * 1024 * 1024 ||
      !SIGNATURE.every((n,i) => bytes[i] === n)) throw new TypeError('Invalid PNG signature or size');
  let p = 8, width = 0, height = 0, ihdr = 0, idat = 0, iend = 0;
  while (p < bytes.length) {
    if (bytes.length - p < 12) throw new TypeError('Truncated PNG chunk');
    const len = u32(bytes, p);
    if (len > bytes.length - p - 12) throw new TypeError('Invalid PNG chunk length');
    const type = String.fromCharCode(...bytes.subarray(p+4,p+8));
    if (!/^[A-Za-z]{4}$/.test(type)) throw new TypeError('Invalid PNG chunk type');
    if (p === 8 && (type !== 'IHDR' || len !== 13)) throw new TypeError('PNG must begin with IHDR');
    if (type === 'IHDR') {
      if (ihdr++ || p !== 8 || len !== 13) throw new TypeError('Duplicate PNG header');
      width = u32(bytes,p+8); height = u32(bytes,p+12);
      if (!width || !height || width > 7680 || height > 7680 ||
          bytes[p+16] !== 8 || ![0,2,3,4,6].includes(bytes[p+17]!) ||
          bytes[p+18] !== 0 || bytes[p+19] !== 0 || bytes[p+20] !== 0)
        throw new TypeError('Unsupported or invalid PNG header');
    }
    if (type === 'IDAT') idat++;
    if (type === 'IEND') {
      if (len !== 0 || iend++ || p + 12 !== bytes.length) throw new TypeError('Invalid PNG end');
    }
    p += len + 12;
    if (iend) break;
  }
  if (ihdr !== 1 || !idat || iend !== 1 || p !== bytes.length) throw new TypeError('Incomplete PNG');
  return { width, height };
}
/** Receipts are evidence of *exact exported file bytes*, not optical correctness.
 * CRCs, decompression, decoded pixels, and visual recognisability need a separate
 * native-host/image-decoder readback check before qualification.
 */
export async function createArtworkPngReceipt(
  plan: ArtworkAtlasPlan, rendered: readonly ArtworkPngPage[]
): Promise<ArtworkPngReceipt> {
  if (!plan || plan.version !== ARTWORK_ATLAS_VERSION || plan.publicOnly !== true ||
      !Array.isArray(plan.pages) || !Array.isArray(rendered) || rendered.length !== plan.pages.length ||
      plan.inputCount < 1 || plan.inputCount > 1000) throw new TypeError('Invalid public atlas export');
  const byPage = new Map<number, Uint8Array>();
  for (const item of rendered) {
    if (!item || !Number.isSafeInteger(item.pageIndex) ||
        !(item.pngBytes instanceof Uint8Array) || byPage.has(item.pageIndex))
      throw new TypeError('Invalid, repeated or missing exported page');
    byPage.set(item.pageIndex, item.pngBytes);
  }
  const pages: ArtworkPngReceiptPage[] = [];
  for (const page of plan.pages) {
    const bytes = byPage.get(page.index);
    if (!bytes) throw new TypeError('Missing atlas PNG page');
    const size = inspectArtworkPng(bytes);
    if (size.width !== page.width || size.height !== page.height) {
      throw new TypeError(`Atlas PNG page ${page.index} dimensions mismatch`);
    }
    pages.push(Object.freeze({ pageIndex: page.index, width: size.width, height: size.height,
      byteLength: bytes.length, sha256Hex: encodeHex(await sha256(bytes)), tileCount: page.tiles.length }));
  }
  return Object.freeze({ version: ARTWORK_EXPORT_RECEIPT_VERSION, atlasVersion: ARTWORK_ATLAS_VERSION,
    inputCount: plan.inputCount, publicOnly: true, guarantee: 'presentation-only',
    pages: Object.freeze(pages) });
}
