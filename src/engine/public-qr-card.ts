/** PUBLIC-only recovery card fragments. FrameRudiments draws/exports the assets. */
import { PublicRecord, publicRecordFingerprint } from '../framing/public-record.js';
import { createFrameRudimentsMatrixLayer, type FrameRudimentsLayer } from './framerudiments.js';
import { encodePublicQrSession, type PublicQrPlanOptions } from '../symbols/qr-frames.js';

export interface PublicQrCardOptions extends PublicQrPlanOptions {
  readonly layerIdPrefix?: string;
  readonly bounds?: readonly [number, number, number, number];
}
export interface PublicQrCard {
  readonly schema: 'bytefables.public-qr-card.v1';
  readonly fullFingerprint: string;
  readonly label: string;
  readonly count: number;
  readonly frames: readonly Readonly<{
    index: number;
    isParity: boolean;
    text: string;
    layer: FrameRudimentsLayer;
    caption: string;
    postEffectsTarget: string;
  }>[];
}

/**
 * This method emits declarative FrameRudiments fragments, NOT QR pixels.
 * QR recovery surfaces MUST disable arbitrary post effects and respect a
 * 4-module white quiet zone. Use `frameRudimentsEffectTarget` only for other
 * visual treatments; never distort a recovery matrix in a printed backup.
 */
export async function createPublicQrCard(record: PublicRecord,
  opts: PublicQrCardOptions = {}): Promise<PublicQrCard> {
  if (!(record instanceof PublicRecord)) throw new TypeError('PublicRecord required');
  const prefix = opts.layerIdPrefix ?? 'bytefables-qr';
  if (!/^[a-z][a-z0-9_-]{0,50}$/.test(prefix)) throw new TypeError('Invalid QR card layer prefix');
  const bounds = opts.bounds ?? [0, 0, 512, 512];
  if (bounds[2] - bounds[0] < 64 || bounds[3] - bounds[1] < 64) {
    throw new RangeError('QR card viewport must be at least 64px');
  }
  const session = await encodePublicQrSession(record, opts);
  const fullFingerprint = await publicRecordFingerprint(record, 32);
  const shortFingerprint = await publicRecordFingerprint(record, 12);
  const frames = session.frames.map(frame => {
    const id = `${prefix}-${frame.index}`;
    const layer = createFrameRudimentsMatrixLayer(frame.qr.matrix, { id, bounds });
    return Object.freeze({ index: frame.index, isParity: frame.parity, text: frame.text,
      layer, caption: `${shortFingerprint} • ${frame.parity ? 'recovery parity' : `part ${frame.index + 1}/${frame.count}`}`,
      postEffectsTarget: `layer:${id}` });
  });
  return Object.freeze({ schema: 'bytefables.public-qr-card.v1' as const,
    fullFingerprint, label: shortFingerprint, count: session.dataFrames,
    frames: Object.freeze(frames) });
}
