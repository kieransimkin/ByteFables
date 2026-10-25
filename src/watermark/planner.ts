/**
 * Carrier-agnostic planning only: no concealment, no media mutation, no decoder.
 * A plan cannot be advertised as imperceptible, robust, or shipped.
 * FrameRudiments owns future media-specific embedding/detection/effect graphs.
 */
import { PublicRecord } from '../framing/public-record.js';
import { getFormatManifest } from '../registry/manifest.js';
import { encodePublicWatermarkMessage, type WatermarkDigestBytes } from './payload.js';

export type WatermarkCarrier = 'image' | 'audio' | 'video' | 'text';
export type ImageCarrier = Readonly<{
  kind: 'image'; mimeType: 'image/png' | 'image/jpeg' | 'image/webp'; width: number; height: number;
}>;
export type AudioCarrier = Readonly<{
  kind: 'audio'; mimeType: 'audio/wav' | 'audio/flac' | 'audio/mpeg';
  sampleRate: number; channels: number; durationSeconds: number;
}>;
export type VideoCarrier = Readonly<{
  kind: 'video'; mimeType: 'video/mp4' | 'video/webm';
  width: number; height: number; fps: number; durationSeconds: number;
}>;
export type TextCarrier = Readonly<{
  kind: 'text'; mimeType: 'text/plain' | 'text/markdown';
  tokenCount: number; generationControlled: boolean;
}>;
export type WatermarkCarrierDescriptor = ImageCarrier | AudioCarrier | VideoCarrier | TextCarrier;

export type WatermarkThreat =
  | 'crop' | 'scale' | 'recompress' | 'rotate' | 'colour-edit'
  | 'noise' | 'resample' | 'time-crop' | 'time-stretch'
  | 'frame-drop' | 'paraphrase' | 'reformat' | 'excerpt';

export interface WatermarkPlanOptions {
  readonly digestBytes?: WatermarkDigestBytes;
  /** Attack-model choices are test goals, not supported guarantees. */
  readonly testDistortions?: readonly WatermarkThreat[];
}

export type WatermarkPlan = Readonly<{
  readonly schema: 'bytefables.watermark-plan.v1';
  readonly operation: 'watermark';
  readonly carrier: WatermarkCarrier;
  readonly formatId: string;
  readonly mediaType: string;
  readonly rendererHost: 'framerudiments';
  readonly strategy: string;
  readonly status: 'planning-only';
  readonly eligibleForResearch: boolean;
  readonly blockers: readonly string[];
  readonly messageBits: number;
  readonly digestBits: number;
  readonly eccBits: null;
  readonly measuredCapacityBits: null;
  readonly detectorAvailable: false;
  readonly embedderAvailable: false;
  readonly robustnessValidated: false;
  readonly imperceptibilityValidated: false;
  readonly testDistortions: readonly WatermarkThreat[];
  readonly evidenceRequired: readonly string[];
}>;

const THREATS: readonly WatermarkThreat[] = [
  'crop', 'scale', 'recompress', 'rotate', 'colour-edit', 'noise', 'resample',
  'time-crop', 'time-stretch', 'frame-drop', 'paraphrase', 'reformat', 'excerpt'
];
const CARRIER_METHODS: Readonly<Record<WatermarkCarrier, { formatId: string; strategy: string;
  threats: readonly WatermarkThreat[] }>> = Object.freeze({
  image: { formatId: 'watermark/image-spatial', strategy: 'multiscale image-domain residual, tiled synchronisation, FEC',
    threats: ['crop', 'scale', 'recompress', 'rotate', 'colour-edit'] },
  audio: { formatId: 'watermark/audio-spectral', strategy: 'psychoacoustic subband spread spectrum with synchronisation and FEC',
    threats: ['noise', 'recompress', 'resample', 'time-crop', 'time-stretch'] },
  video: { formatId: 'watermark/video-temporal', strategy: 'frame-local spatial marks plus temporal redundancy, FEC and sync',
    threats: ['crop', 'scale', 'recompress', 'frame-drop', 'time-crop'] },
  text: { formatId: 'watermark/text-semantic', strategy: 'generator-controlled constrained lexical choice with statistical decoding',
    threats: ['reformat', 'excerpt', 'paraphrase'] }
});

const COUNTERMEASURES = Object.freeze([
  'independent blind detector with ground-truth message/error accounting',
  'measured false-positive and false-negative rates on unmarked controls',
  'perceptual quality tests and human review; no universal invisibility claim',
  'recoverability after real post-export transforms; report exact tested limits',
  'rate-distortion-capacity measurements at each message size and ECC strength',
  'carrier owner opt-in, public-only payload, no tracking or confidential keys'
]);

function safeInteger(v: number, max: number): boolean {
  return Number.isSafeInteger(v) && v > 0 && v <= max;
}
function safeNumber(v: number, max: number): boolean {
  return typeof v === 'number' && Number.isFinite(v) && v > 0 && v <= max;
}

/**
 * Prepare a research plan for hiding a PUBLIC typed-record digest in another
 * medium. This never modifies images/audio/video/text and cannot promise
 * recovery. The actual watermark MUST be applied and decoded by a qualified
 * FrameRudiments pipeline, with a test corpus and explicit transform budget.
 */
export async function planPublicWatermark(
  record: PublicRecord, carrier: WatermarkCarrierDescriptor, options: WatermarkPlanOptions = {}
): Promise<WatermarkPlan> {
  if (!(record instanceof PublicRecord)) throw new TypeError('Public record required');
  if (!carrier || typeof carrier !== 'object' || !Object.hasOwn(CARRIER_METHODS, carrier.kind)) {
    throw new TypeError('Unknown watermark carrier');
  }
  const allowed = CARRIER_METHODS[carrier.kind];
  const entry = getFormatManifest(allowed.formatId);
  if (!entry || entry.maturity !== 'planned' || entry.category !== 'watermark' ||
      entry.input !== 'public-record-and-carrier' || !entry.mediaTypes.includes(carrier.mimeType)) {
    throw new TypeError('Carrier MIME or manifest does not match the watermark research format');
  }
  const requested = options.testDistortions ?? allowed.threats;
  if (!Array.isArray(requested) || requested.length > 12 ||
      requested.some(x => !THREATS.includes(x) || !allowed.threats.includes(x)) ||
      new Set(requested).size !== requested.length) {
    throw new TypeError('Unsupported or duplicated watermark distortion type');
  }
  const digestBytes = options.digestBytes ?? 12;
  const messageBits = (await encodePublicWatermarkMessage(record, digestBytes)).byteLength * 8;
  const blockers: string[] = [];
  // These are conservative *research eligibility* screens, not capacities or proofs.
  switch (carrier.kind) {
    case 'image':
      if (!safeInteger(carrier.width, 65536) || !safeInteger(carrier.height, 65536)) {
        throw new RangeError('Invalid image extent');
      }
      if (carrier.width < 256 || carrier.height < 256) blockers.push('Image too small for initial multiscale watermark experiments');
      break;
    case 'audio':
      if (!safeInteger(carrier.sampleRate, 384000) || !safeInteger(carrier.channels, 64) ||
          !safeNumber(carrier.durationSeconds, 86400)) throw new RangeError('Invalid audio signal specification');
      if (carrier.sampleRate < 16000 || carrier.durationSeconds < 5) {
        blockers.push('Audio duration/rate too low for first blind-detector experiment');
      }
      break;
    case 'video':
      if (!safeInteger(carrier.width, 65536) || !safeInteger(carrier.height, 65536) ||
          !safeNumber(carrier.fps, 240) || !safeNumber(carrier.durationSeconds, 86400)) {
        throw new RangeError('Invalid video signal specification');
      }
      if (carrier.width < 256 || carrier.height < 256 || carrier.durationSeconds < 3 || carrier.fps < 5) {
        blockers.push('Video too small/short for initial spatial/temporal redundancy experiments');
      }
      break;
    case 'text':
      if (!Number.isSafeInteger(carrier.tokenCount) || carrier.tokenCount < 0 || carrier.tokenCount > 10_000_000 ||
          typeof carrier.generationControlled !== 'boolean') {
        throw new RangeError('Invalid text carrier specification');
      }
      if (!carrier.generationControlled) blockers.push('Arbitrary fixed prose cannot be edited for a semantic watermark');
      if (carrier.tokenCount < 1000) blockers.push('Text too short for the initial long-form language watermark experiment');
      break;
  }
  const plan: WatermarkPlan = {
    schema: 'bytefables.watermark-plan.v1', operation: 'watermark',
    carrier: carrier.kind, formatId: allowed.formatId, mediaType: carrier.mimeType,
    rendererHost: 'framerudiments', strategy: allowed.strategy, status: 'planning-only',
    eligibleForResearch: blockers.length === 0, blockers: Object.freeze(blockers),
    messageBits, digestBits: digestBytes * 8, eccBits: null, measuredCapacityBits: null,
    detectorAvailable: false, embedderAvailable: false,
    robustnessValidated: false, imperceptibilityValidated: false,
    testDistortions: Object.freeze([...requested]), evidenceRequired: COUNTERMEASURES
  };
  return Object.freeze(plan);
}
