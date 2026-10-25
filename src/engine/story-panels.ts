/** Declarative story preview for FrameRudiments' existing identity text layers.
 * FrameRudiments still owns text rasterisation, fonts, effects and compositing.
 * This is NOT a recovery artifact: omitted sentences MUST NOT be hidden.
 */
import { assertPublicValue, type PublicByteValue } from '../value.js';
import { encodeStoryV2 } from '../grammar/story-v2.js';
import { type StoryTheme } from '../grammar/themes.js';

export type FrameTextBlock = Readonly<{
  readonly text: string;
  readonly style: Readonly<{
    readonly box: readonly [number, number, number, number];
    readonly font_size: number;
    readonly colour: string;
  }>;
}>;
export interface StoryPreviewOptions {
  /** Project-relative text box. The caller supplies a pinned font to FrameRudiments. */
  readonly box: readonly [number, number, number, number];
  readonly fontSize?: number;
  readonly color?: 'white' | 'amber' | 'mint';
  /** 1–4 displayed lines. No data is secretly embedded by truncating preview. */
  readonly maxSentences?: number;
}
export interface FrameStoryPreview {
  readonly target: 'framerudiments.project.v1/identity';
  readonly sourceFormat: 'BYTEFABLES-STORY-V2';
  readonly previewOnly: true;
  readonly omittedSentences: number;
  readonly identities: readonly FrameTextBlock[];
  readonly effectTargets: readonly string[];
}

export async function createFrameRudimentsStoryPreview(
  input: PublicByteValue, theme: StoryTheme, options: StoryPreviewOptions
): Promise<FrameStoryPreview> {
  assertPublicValue(input);
  if (!options || !Array.isArray(options.box) || options.box.length !== 4 ||
      options.box.some(n => !Number.isSafeInteger(n) || n < 0 || n > 7680) ||
      options.box[0]! >= options.box[2]! || options.box[1]! >= options.box[3]!) {
    throw new TypeError('Invalid FrameRudiments text placement');
  }
  const size = options.fontSize ?? 24;
  const count = options.maxSentences ?? 2;
  const color = options.color ?? 'white';
  if (!Number.isSafeInteger(size) || size < 8 || size > 256 ||
      !Number.isSafeInteger(count) || count < 1 || count > 4 ||
      !['white', 'amber', 'mint'].includes(color)) throw new TypeError('Invalid story text style');
  const story = await encodeStoryV2(input, theme);
  const sentences = story.split('\n').slice(1);
  const colours: Readonly<Record<string, string>> = { white: '#ffffff', amber: '#f5cc80', mint: '#9fe7ce' };
  const identities = Object.freeze(sentences.slice(0, count).map(sentence =>
    Object.freeze({ text: sentence, style: Object.freeze({ box: Object.freeze([...options.box]) as
        unknown as readonly [number, number, number, number],
      font_size: size, colour: colours[color]! }) })));
  return Object.freeze({ target: 'framerudiments.project.v1/identity' as const,
    sourceFormat: 'BYTEFABLES-STORY-V2' as const, previewOnly: true as const,
    omittedSentences: Math.max(0, sentences.length - count), identities,
    effectTargets: Object.freeze(identities.map((_, i) => `identity:${i}`)) });
}
