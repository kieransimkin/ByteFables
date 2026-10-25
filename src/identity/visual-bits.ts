/** Public-only bit-by-bit semantic identity plan. DOES NOT encode a reversible image. */
import { assertPublicValue, type PublicByteValue } from '../value.js';
import { identityDigest } from './identity.js';
import { encodeHex } from '../codecs/hex.js';

export const VISUAL_BITS_VERSION = 'bytefables.visual-bits.v1' as const;
const GLOBAL: readonly [string, string, string][] = [
  ['silhouette', 'smooth', 'spiky'],
  ['illumination', 'dark', 'bright'],
  ['saturation', 'muted', 'vibrantly saturated'],
  ['surface-finish', 'matte', 'glossy'],
  ['composition-symmetry', 'symmetrical', 'asymmetrical'],
  ['ornament-density', 'sparsely decorated', 'densely decorated'],
  ['palette-temperature', 'warm-toned', 'cool-toned'],
  ['shape-language', 'organic', 'geometric'],
  ['material', 'wooden', 'metallic'],
  ['lighting-softness', 'softly lit', 'harshly lit'],
  ['surface-markings', 'striped', 'spotted'],
  ['backdrop', 'forested', 'desert-like'],
  ['camera-elevation', 'eye-level view', 'overhead view'],
  ['subject-size', 'miniature', 'monumental'],
  ['atmosphere', 'hazy', 'crystal-clear'],
  ['palette-contrast', 'low-contrast', 'high-contrast'],
  ['edge-language', 'rounded-edged', 'sharp-edged'],
  ['lighting-direction', 'side-lit', 'back-lit'],
  ['detail-scale', 'large simple details', 'fine intricate details'],
  ['body-structure', 'compact', 'elongated'],
  ['background-tone', 'pale background', 'deep-toned background'],
  ['surface-transparency', 'opaque', 'translucent'],
  ['object-geometry', 'faceted', 'continuous-curved'],
  ['perspective', 'flat orthographic', 'dramatic perspective'],
  ['surface-relief', 'flat surface', 'deeply embossed surface'],
  ['light-emission', 'unlit surface', 'self-luminous surface'],
  ['motion-language', 'still poised', 'energetically posed'],
  ['environment-moisture', 'arid environment', 'rain-soaked environment'],
  ['accent-shape', 'circular accents', 'triangular accents'],
  ['dominant-structure', 'solid monolith', 'open lattice'],
  ['colour-count', 'limited colours', 'many distinct colours'],
  ['outline-style', 'fine outlines', 'heavy outlines']
];
const MICRO: readonly [string, string, string][] = [
  ['mark', 'dots', 'lines'],
  ['edge', 'rounded', 'pointed'],
  ['surface', 'matte', 'shimmering'],
  ['texture', 'smooth', 'rough'],
  ['colour', 'amber', 'cyan'],
  ['orientation', 'horizontal', 'vertical'],
  ['geometry', 'circular', 'square'],
  ['relief', 'raised', 'recessed'],
  ['luminance', 'light', 'dark'],
  ['fill', 'solid', 'hollow'],
  ['scale', 'tiny', 'large'],
  ['pattern', 'striped', 'spotted'],
  ['position', 'centered', 'off-center'],
  ['shine', 'unlit', 'glowing'],
  ['density', 'sparse', 'crowded'],
  ['silhouette', 'plain', 'elaborate']
];
export interface VisualBitChoice {
  readonly bitIndex: number;
  readonly bit: 0 | 1;
  readonly featureId: string;
  readonly scope: string;
  readonly property: string;
  readonly zero: string;
  readonly one: string;
  readonly selected: string;
  readonly opposite: string;
  readonly tier: 'primary' | 'micro';
}
export interface VisualBitPlan {
  readonly schema: typeof VISUAL_BITS_VERSION;
  readonly namespace: string;
  readonly kind: string;
  readonly publicHex: string;
  readonly identityDigestHex: string;
  /** Backward-compatible 32-bit seed hint; not unique and not used for production identity verification. */
  readonly visualSeed: number;
  /** Full 64-bit seed as decimal text (not a JS number), for local diffusion engines. */
  readonly visualSeed64: string;
  readonly bitCount: number;
  readonly bitOrder: 'msb0';
  readonly choices: readonly VisualBitChoice[];
}
/** Each source bit has one frozen binary *opposition*, optionally scoped to a numbered motif.
 * Every bit participates in the generated contract, NOT necessarily in a final image or prompt.
 */
export async function makeVisualBitPlan(value: PublicByteValue): Promise<VisualBitPlan> {
  assertPublicValue(value);
  const bytes = value.toBytes();
  if (bytes.length < 1 || bytes.length > 512) throw new RangeError('Visual experiment supports 1..512 PUBLIC bytes');
  const digest = await identityDigest(value);
  const choices: VisualBitChoice[] = [];
  for (let i = 0; i < bytes.length * 8; i++) {
    const bit = ((bytes[i >> 3]! >> (7 - i % 8)) & 1) as 0 | 1;
    const global = i < GLOBAL.length;
    const slot = global ? GLOBAL[i]! : MICRO[(i - GLOBAL.length) % MICRO.length]!;
    const motif = global ? 0 : 1 + Math.floor((i - GLOBAL.length) / MICRO.length);
    const scope = global ? 'main subject' : `motif ${String(motif).padStart(3, '0')}`;
    choices.push(Object.freeze({ bitIndex: i, bit,
      featureId: global ? `primary-${String(i).padStart(3, '0')}` :
        `motif-${String(motif).padStart(3, '0')}-${slot[0]}`,
      scope, property: slot[0], zero: slot[1], one: slot[2],
      selected: slot[1 + bit]!, opposite: slot[2 - bit]!, tier: global ? 'primary' : 'micro' }));
  }
  return Object.freeze({ schema: VISUAL_BITS_VERSION, namespace: value.namespace,
    kind: value.kind, publicHex: encodeHex(bytes), identityDigestHex: encodeHex(digest),
    visualSeed: ((digest[0]! << 24) | (digest[1]! << 16) | (digest[2]! << 8) | digest[3]!) >>> 0,
    visualSeed64: BigInt(`0x${encodeHex(digest.slice(0, 8))}`).toString(),
    bitCount: choices.length, bitOrder: 'msb0', choices: Object.freeze(choices) });
}

export function choosePromptBits(plan: VisualBitPlan, bitBudget: number): readonly VisualBitChoice[] {
  if (!Number.isSafeInteger(bitBudget) || bitBudget < 1 || bitBudget > plan.bitCount) {
    throw new RangeError('bitBudget must be between 1 and the bit count');
  }
  return plan.choices.slice(0, bitBudget);
}

export type BaselinePromptStyle = 'direct' | 'narrative' | 'structured';
export function composeBaselinePrompt(plan: VisualBitPlan, bitBudget = 12,
  style: BaselinePromptStyle = 'direct'): string {
  const chosen = choosePromptBits(plan, bitBudget);
  const attributes = chosen.map(c => `${c.scope} ${c.property}: ${c.selected}`);
  switch (style) {
    case 'direct': return `One original illustrated identity sculpture. ${attributes.join('; ')}. No text or logos.`;
    case 'narrative': return `Illustrate an original fantasy identity sculpture with these deliberate visual choices: ${attributes.join('; ')}. A cohesive visual scene, without text or logos.`;
    case 'structured': return `SUBJECT: original identity sculpture. FEATURES:\n${attributes.map(a => `- ${a}`).join('\n')}\nNO text, logos, letters, numbers.`;
    default: throw new TypeError('Unknown baseline prompt style');
  }
}
