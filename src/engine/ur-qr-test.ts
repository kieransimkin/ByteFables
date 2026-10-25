/** Test-only Blockchain Commons ur:bytes v2 QR handoff.
 * QR generation is exact; FrameRudiments remains the only presentation engine.
 * Not intended for production wallet exchange or private key handling.
 */
import { encodeUrBytesMultipartTestOnly, type UrTestEncodeOptions } from '../codecs/ur-multipart-test.js';
import { encodeQrModel2, type QrEcc } from '../symbols/qr.js';
import { createFrameRudimentsMatrixLayer, type FrameRudimentsLayer,
  type LayerPlacement } from './framerudiments.js';

export type UrBytesQrTestOptions = UrTestEncodeOptions & LayerPlacement & Readonly<{
  ecc?: QrEcc;
  maxVersion?: number;
  mask?: number;
}>;
export interface UrBytesQrTestDeck {
  readonly schema: 'bytefables.ur-bytes-qr-test.v1';
  readonly warning: string;
  readonly frames: readonly Readonly<{
    index: number; text: string; layer: FrameRudimentsLayer;
  }>[];
}

export async function createUrBytesQrTestDeck(bytes: Uint8Array,
  opts: UrBytesQrTestOptions): Promise<UrBytesQrTestDeck> {
  const session = await encodeUrBytesMultipartTestOnly(bytes, opts);
  if (session.frames.length > 128) throw new RangeError('Optical test deck supports at most 128 frames');
  const frames = session.frames.map((text, index) => {
    const qr = encodeQrModel2(new TextEncoder().encode(text), { ecc: opts.ecc ?? 'Q',
      maxVersion: opts.maxVersion ?? 14, ...(opts.mask === undefined ? {} : {mask: opts.mask}) });
    const layer = createFrameRudimentsMatrixLayer(qr.matrix, {
      id: `${opts.id}-${index}`, bounds: opts.bounds
    });
    return Object.freeze({ index, text, layer });
  });
  return Object.freeze({ schema: 'bytefables.ur-bytes-qr-test.v1' as const,
    warning: 'PUBLIC test-only ur:bytes; independently scan output PNGs; never wallet/secret data',
    frames: Object.freeze(frames) });
}
