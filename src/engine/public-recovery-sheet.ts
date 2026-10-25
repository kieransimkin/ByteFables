/** Declarative public-only print sheets hosted by FrameRudiments.
 * No PNG/PDF is rendered by this TypeScript code.
 * Recoverable QR modules must NEVER receive arbitrary post effects.
 */
import { PublicRecord, publicRecordFingerprint } from '../framing/public-record.js';
import { encodePublicQrSession, type PublicQrPlanOptions } from '../symbols/qr-frames.js';
import { createFrameRudimentsRecoveryCardLayer, type FrameRudimentsLayer,
  type LayerPlacement } from './framerudiments.js';

export interface PublicRecoverySheetOptions extends PublicQrPlanOptions {
  readonly pageBounds?: LayerPlacement['bounds'];
  readonly layerPrefix?: string;
}
export interface PublicRecoverySheet {
  readonly schema: 'bytefables.public-recovery-sheet.v1';
  readonly kind: 'PUBLIC RECORD';
  readonly canonicalFingerprint: string;
  readonly transport: 'BFQR1';
  readonly count: number;
  readonly frames: readonly Readonly<{ index: number; caption: string; text: string;
    layer: FrameRudimentsLayer; excludedFromEffects: true }>[];
  readonly constraints: readonly string[];
}

export async function createPublicRecoverySheet(record: PublicRecord,
  opts: PublicRecoverySheetOptions = {}): Promise<PublicRecoverySheet> {
  if (!(record instanceof PublicRecord)) throw new TypeError('PUBLIC record required');
  const bounds = opts.pageBounds ?? [0, 0, 1024, 1440];
  const prefix = opts.layerPrefix ?? 'bytefables-public-card';
  if (!/^[a-z][a-z0-9_-]{0,42}$/.test(prefix)) throw new TypeError('Invalid print-card layer prefix');
  const qr = await encodePublicQrSession(record, opts);
  const fingerprint = await publicRecordFingerprint(record, 32);
  const frames = qr.frames.map((frame, i) => {
    const caption = frame.parity ? `Recovery parity - ${qr.dataFrames} data frames` :
      `Frame ${frame.index+1} of ${qr.dataFrames}`;
    const layer = createFrameRudimentsRecoveryCardLayer(frame.qr.matrix, {
      id: `${prefix}-${i}`, bounds, caption, fingerprint,
      kind: `${record.namespace} / ${record.kind}`, manualText: frame.text
    });
    return Object.freeze({ index:i, caption, text:frame.text, layer,
      excludedFromEffects:true as const });
  });
  return Object.freeze({ schema:'bytefables.public-recovery-sheet.v1' as const,
    kind:'PUBLIC RECORD' as const, canonicalFingerprint:fingerprint,
    transport:'BFQR1' as const, count:frames.length, frames:Object.freeze(frames),
    constraints:Object.freeze([
      'FrameRudiments native renderer ONLY; print page without optical post effects',
      'Exactly four white QR quiet-zone modules; integer-size modules; no lossy resampling',
      'Output is PUBLIC test/source data; not a private-key or wallet-backup format',
      'Read back the exported PNG/printed sheet with an independent scanner before claiming recovery'
    ]) });
}
