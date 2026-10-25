/** Public-only deterministic fractal parameter contract; graphics belong to FrameRudiments. */
import { PublicRecord, publicRecordDigest } from '../framing/public-record.js';
import { encodeHex } from '../codecs/hex.js';
import { sha256 } from './sha256.js';
import { concatBytes } from '../utils/binary.js';

export const FRACTAL_SEED_VERSION = 'bytefables.fractal-seed.v1' as const;
const DOMAIN = new TextEncoder().encode('ByteFables:fractal-seed:v1\0');
export const FRACTAL_FAMILIES = ['julia', 'burning-ship', 'ifs-fern', 'fbm'] as const;
export type FractalFamily = typeof FRACTAL_FAMILIES[number];
export type FractalPalette = 'neon' | 'pastel' | 'mono';

export const FRACTAL_BINARY_AXES = Object.freeze([
  ['silhouette', 'smooth', 'spiky'],
  ['illumination', 'dark', 'bright'],
  ['saturation', 'muted', 'saturated'],
  ['surface-finish', 'matte', 'glossy'],
  ['symmetry', 'bilateral', 'asymmetric'],
  ['detail-density', 'sparse', 'dense'],
  ['colour-temperature', 'warm', 'cool'],
  ['geometry', 'organic', 'angular']
] as const);

export interface FractalSeedPlan {
  readonly schema: typeof FRACTAL_SEED_VERSION;
  readonly family: FractalFamily;
  readonly seedHex: string;
  readonly digestHex: string;
  readonly featureBits: string;
  readonly palette: FractalPalette;
  readonly axes: readonly Readonly<{ index: number; property: string; selected: string }> [];
  readonly identityOnly: true;
  readonly effectiveRecoverableBits: null;
}

/**
 * 8 explicit source-bit feature axes; all other source bytes influence the
 * avalanche seed, NOT individually recoverable visual choices. An image cannot
 * certify any particular bit. Neither input bytes nor private keys enter the
 * native image renderer, only a context-bound public digest and eight decisions.
 */
export async function planPublicFractal(record: PublicRecord,
  family: FractalFamily = 'julia', palette: FractalPalette = 'neon'): Promise<FractalSeedPlan> {
  if (!(record instanceof PublicRecord)) throw new TypeError('A typed PUBLIC record is required');
  if (!FRACTAL_FAMILIES.includes(family)) throw new TypeError('Invalid fractal family');
  if (!(['neon', 'pastel', 'mono'] as const).includes(palette)) throw new TypeError('Invalid fractal palette');
  const bytes = record.toBytes();
  if (bytes.length < 1 || bytes.length > 512) throw new RangeError('Fractal feature contract requires 1..512 PUBLIC bytes');
  const digest = await publicRecordDigest(record);
  const seed = await sha256(concatBytes(DOMAIN, digest));
  const featureBits = Array.from({length: 8}, (_, i) =>
    String((bytes[i >> 3]! >> (7 - (i % 8))) & 1)).join('');
  const axes = FRACTAL_BINARY_AXES.map(([name, zero, one], index) => Object.freeze({
    index, property: name, selected: featureBits[index] === '1' ? one : zero
  }));
  return Object.freeze({schema: FRACTAL_SEED_VERSION, family, seedHex: encodeHex(seed),
    digestHex: encodeHex(digest), featureBits, palette,
    axes: Object.freeze(axes), identityOnly: true as const, effectiveRecoverableBits: null});
}
