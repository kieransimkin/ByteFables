/** Public-only format execution and capability planning. No secrets or planned handlers. */
import { PublicRecord, encodePublicRecord, publicRecordFingerprint } from '../framing/public-record.js';
import { encodeHex } from '../codecs/hex.js';
import { encodeBase32 } from '../codecs/base32.js';
import { encodeBase45 } from '../codecs/base45.js';
import { encodeBase64 } from '../codecs/base64.js';
import { encodeCrockford32 } from '../codecs/crockford32.js';
import { encodeBytewords } from '../codecs/bytewords.js';
import { encodeBip39PublicEntropy } from '../codecs/bip39.js';
import { encodeUrBytesTestOnly } from '../codecs/ur-bytes-test.js';
import { encodeMultibase } from '../codecs/multibase.js';
import { encodeExperimentalStory } from '../grammar/story.js';
import { encodeStoryV2 } from '../grammar/story-v2.js';
import { encodeScheduledStory } from '../grammar/scheduled-story.js';
import { identityFingerprint } from '../identity/identity.js';
import { deriveShortPublicHash } from '../identity/short-hash.js';
import { renderPixelAvatar } from '../identity/pixel-avatar.js';
import { makeVisualBitPlan } from '../identity/visual-bits.js';
import { planPublicFractal } from '../identity/fractal-seed.js';
import { createFrameRudimentsIdentityLayer, createFrameRudimentsArtworkLayer } from '../engine/framerudiments.js';
import { encodePublicQrSession } from '../symbols/qr-frames.js';
import { encodeQrModel2 } from '../symbols/qr.js';
import { FORMAT_MANIFEST, getFormatManifest, type FormatManifestEntry, type FormatGuarantee } from './manifest.js';

export type PublicArtifact = Readonly<{
  formatId: string;
  version: string;
  guarantee: FormatGuarantee;
  mediaType: string;
  /** Text and SVG representations are strings; application/cbor is bytes. */
  data: string | Uint8Array;
}>;

export interface PublicPlanRequest {
  readonly byteLength: number;
  readonly goal?: 'recover-typed' | 'recover-any' | 'identify' | 'all';
  readonly mediaType?: string;
  /** Experimental formats require explicit inclusion and opt-in execution. */
  readonly includeExperimental?: boolean;
  /** Planned descriptions are not executable and stay excluded by default. */
  readonly includePlanned?: boolean;
}

export type PlannedFormat = Readonly<{
  formatId: string;
  version: string;
  guarantee: FormatGuarantee;
  maturity: FormatManifestEntry['maturity'];
  mediaTypes: readonly string[];
  estimatedExpansion: number | null;
  executable: boolean;
}>;

const adapters: ReadonlyMap<string, (record: PublicRecord) => Promise<string | Uint8Array>> = new Map<string, (record: PublicRecord) => Promise<string | Uint8Array>>([
  ['encodeHex', async (record: PublicRecord) => encodeHex(record.toBytes())],
  ['makeFrameRudimentsArtworkLayer', async record => JSON.stringify(await createFrameRudimentsArtworkLayer(record, {id: 'bytefables-artwork',bounds:[0,0,128,128]}))],
  ['encodeQrRawMatrix', async record => {
    const qr = encodeQrModel2(record.toBytes(), { ecc: 'L' });
    return JSON.stringify({ schema: qr.schema, version: qr.version, ecc: qr.ecc, mask: qr.mask,
      dataBytes: qr.dataBytes, quietZone: qr.matrix.quietZone, width: qr.matrix.width,
      height: qr.matrix.height, modules: [...qr.matrix.toModules()].join('') });
  }],
  ['encodePublicQrPlan', async record => {
    const session = await encodePublicQrSession(record);
    return JSON.stringify({ schema: session.schema, sessionId: session.sessionId,
      dataFrames: session.dataFrames, parityFrames: session.parityFrames,
      qrErrorCorrection: session.qrErrorCorrection, qrMaxVersion: session.qrMaxVersion,
      frames: session.frames.map(f => f.text) });
  }],
  ['encodeBase45', async record => encodeBase45(record.toBytes())],
  ['encodeBase64', async record => encodeBase64(record.toBytes())],
  ['encodeBase64Url', async record => encodeBase64(record.toBytes(), true)],
  ['encodeCrockfordChecked', async record => encodeCrockford32(record.toBytes(), true)],
  ['encodeBytewords', async record => encodeBytewords(record.toBytes())],
  ['encodeBytewordsUri', async record => encodeBytewords(record.toBytes(), 'uri')],
  ['encodeBytewordsMinimal', async record => encodeBytewords(record.toBytes(), 'minimal')],
  ['encodeBip39PublicEntropy', async record => encodeBip39PublicEntropy(record.value)],
  ['encodeUrBytesTestOnly', async record => encodeUrBytesTestOnly(record.toBytes())],
  ['encodeMultibase32', async record => encodeMultibase(record.toBytes(), 'b')],
  ['encodeMultibase64Url', async record => encodeMultibase(record.toBytes(), 'u')],
  ['encodeBase32', async (record: PublicRecord) => encodeBase32(record.toBytes())],
  ['encodePublicRecord', async (record: PublicRecord) => encodePublicRecord(record)],
  ['encodeExperimentalStory', async (record: PublicRecord) => encodeExperimentalStory(record.value)],
  ['encodeStoryV2', async (record: PublicRecord) => encodeStoryV2(record.value)],
  ['encodeScheduledStory', async (record: PublicRecord) => encodeScheduledStory(record.value)],
  ['identityFingerprint', async (record: PublicRecord) => identityFingerprint(record.value)],
  ['deriveShortPublicHash24', async (record: PublicRecord) => (await deriveShortPublicHash(record.value, 3)).label],
  ['deriveShortPublicHash32', async (record: PublicRecord) => (await deriveShortPublicHash(record.value, 4)).label],
  ['deriveShortPublicHash64', async (record: PublicRecord) => (await deriveShortPublicHash(record.value, 8)).label],
  ['publicRecordFingerprint', async (record: PublicRecord) => publicRecordFingerprint(record)],
  ['renderPixelAvatar', async (record: PublicRecord) => renderPixelAvatar(record.value)],
  ['makeVisualBitPlan', async (record: PublicRecord) => JSON.stringify(await makeVisualBitPlan(record.value))],
  ['planPublicFractal', async (record: PublicRecord) => JSON.stringify(await planPublicFractal(record))],
  ['makeFrameRudimentsIdentityLayer', async (record: PublicRecord) =>
    JSON.stringify(await createFrameRudimentsIdentityLayer(record, { id: 'bytefables-identity', bounds: [0, 0, 128, 128] }))]
]);

function runnable(entry: FormatManifestEntry): boolean {
  return entry.input === 'public-record' && entry.maturity !== 'planned' &&
    entry.adapter !== null && adapters.has(entry.adapter);
}

/** Registered planned and intermediate-output formats are descriptive, NOT handlers. */
export function planPublicFormats(request: PublicPlanRequest): readonly PlannedFormat[] {
  if (!Number.isSafeInteger(request.byteLength) || request.byteLength < 0 ||
      request.byteLength > 1048576) {
    throw new RangeError('Invalid planned public byte length');
  }
  const goal = request.goal ?? 'all';
  if (!['recover-typed', 'recover-any', 'identify', 'all'].includes(goal)) {
    throw new TypeError('Invalid format planning goal');
  }
  return FORMAT_MANIFEST.filter(entry => {
    if (entry.input !== 'public-record' || request.byteLength < entry.minInputBytes ||
        request.byteLength > entry.maxInputBytes) return false;
    if (entry.maturity === 'planned' && !request.includePlanned) return false;
    if (entry.maturity === 'experimental' && !request.includeExperimental) return false;
    if (request.mediaType && !entry.mediaTypes.includes(request.mediaType)) return false;
    if (goal === 'recover-typed' && entry.guarantee !== 'reversible-typed') return false;
    if (goal === 'recover-any' && !entry.guarantee.startsWith('reversible-')) return false;
    if (goal === 'identify' && entry.guarantee !== 'identity-only') return false;
    return true;
  }).map(entry => Object.freeze({ formatId: entry.formatId, version: entry.version,
    guarantee: entry.guarantee, maturity: entry.maturity,
    mediaTypes: entry.mediaTypes, estimatedExpansion: entry.estimatedExpansion,
    executable: runnable(entry)
  }));
}

/** Executes ONLY concrete built-in public adapters; never executes planned capabilities. */
export async function executePublicFormat(
  formatId: string, record: PublicRecord, options: { readonly allowExperimental?: boolean } = {}
): Promise<PublicArtifact> {
  if (!(record instanceof PublicRecord)) throw new TypeError('PublicRecord required');
  const entry = getFormatManifest(formatId);
  if (!entry) throw new RangeError('Unknown format');
  if (entry.maturity === 'planned' || !runnable(entry)) {
    throw new RangeError('Format is not implemented for public records');
  }
  if (entry.maturity === 'experimental' && options.allowExperimental !== true) {
    throw new RangeError('Experimental format requires explicit opt-in');
  }
  if (record.byteLength < entry.minInputBytes || record.byteLength > entry.maxInputBytes) {
    throw new RangeError('Input exceeds format capacity');
  }
  const encoded = await adapters.get(entry.adapter!)!(record);
  const encodedSize = typeof encoded === 'string' ? new TextEncoder().encode(encoded).length : encoded.length;
  if (encodedSize > entry.maxOutputBytes) throw new RangeError('Format exceeded output budget');
  return Object.freeze({ formatId: entry.formatId, version: entry.version,
    guarantee: entry.guarantee, mediaType: entry.mediaTypes[0]!, data: encoded });
}

/** CI guard: every declared built-in public-record handler must exist. */
export function verifyBuiltinRegistry(): void {
  for (const entry of FORMAT_MANIFEST) {
    if (entry.adapter && !runnable(entry)) {
      throw new TypeError(`Unbound format adapter: ${entry.formatId}`);
    }
  }
}
