/** Alternative ByteFables scheduled story, with self-describing 24/32/40-bit
 * templates and a bounded deterministic DP schedule. NOT wallet interoperable.
 */
import { assertPublicValue, type PublicByteValue } from '../value.js';
import { sha256 } from '../identity/sha256.js';
import { bytesToBits, bitsToBytes, concatBytes, readU32, writeU32 } from '../utils/binary.js';
import { decodeStructuredSentence, encodeStructuredSentence } from './structured.js';
import { scheduleSentenceCapacities, type CapacityChoice } from './scheduler.js';
import { STORY_THEMES, getScheduledStoryPack, type StoryTheme } from './themes.js';
import { STORY_V2_MAX_PAYLOAD_BYTES } from './story-v2.js';

const MARKER = 'BYTEFABLES-SCHEDULED-STORY-1';
const MAGIC = Uint8Array.of(0x42, 0x46, 0x53, 0x56); // BFSV
const VERSION = 1;
const HEADER = 10;
const CHECK = 16;
const MAX_TEXT_LENGTH = 440_000;

async function envelope(bytes: Uint8Array, theme: StoryTheme): Promise<Uint8Array> {
  if (!(bytes instanceof Uint8Array) || bytes.length > STORY_V2_MAX_PAYLOAD_BYTES) {
    throw new RangeError('Scheduled story accepts up to 4,096 PUBLIC bytes');
  }
  const themeId = STORY_THEMES.indexOf(theme);
  if (themeId < 0) throw new TypeError('Unknown scheduled story theme');
  const content = concatBytes(MAGIC, Uint8Array.of(VERSION, themeId), writeU32(bytes.length), bytes);
  return concatBytes(content, (await sha256(content)).slice(0, CHECK));
}

function capacities(theme: StoryTheme): readonly CapacityChoice[] {
  const templates = getScheduledStoryPack(theme).templates;
  // Fixed costs are frozen format specification decisions; no NLP/model calls.
  return templates.map((t, index) => Object.freeze({ id: t.id,
    bits: t.payloadBits, cost: [10, 13, 17][index]! }));
}

async function encodeBytes(bytes: Uint8Array, theme: StoryTheme): Promise<string> {
  const framed = await envelope(bytes, theme);
  const bits = bytesToBits(framed);
  const pack = getScheduledStoryPack(theme);
  const schedule = scheduleSentenceCapacities(bits.length, capacities(theme), { paddingCost: 2 });
  const sentences = schedule.map(chunk => {
    const template = pack.templates.find(t => t.id === chunk.id)!;
    const payload = bits.slice(chunk.startBit, chunk.startBit + chunk.usedBits);
    while (payload.length < template.payloadBits) payload.push(0);
    return encodeStructuredSentence(template, payload);
  });
  return `${MARKER} ${theme}/1\n${sentences.join('\n')}`;
}

export async function encodeScheduledStory(input: PublicByteValue, theme: StoryTheme = 'nature'): Promise<string> {
  assertPublicValue(input);
  return encodeBytes(input.toBytes(), theme);
}

export async function decodeScheduledStory(text: string): Promise<{ readonly bytes: Uint8Array; readonly theme: StoryTheme }> {
  if (typeof text !== 'string' || text.length > MAX_TEXT_LENGTH) throw new TypeError('Invalid story size');
  const normalized = text.replace(/\r\n/g, '\n');
  if (normalized.includes('\r')) throw new TypeError('Unsupported line ending');
  const lines = normalized.split('\n');
  const header = /^BYTEFABLES-SCHEDULED-STORY-1 (nature|technology|music|fantasy|science|humour)\/1$/.exec(lines[0] || '');
  if (!header) throw new TypeError('Unsupported scheduled-story version');
  const theme = header[1] as StoryTheme;
  const pack = getScheduledStoryPack(theme);
  const sentences = lines.slice(1);
  if (sentences.length < 1 || sentences.length > Math.ceil((STORY_V2_MAX_PAYLOAD_BYTES + HEADER + CHECK) * 8 / 24) + 1) {
    throw new RangeError('Invalid scheduled-story sentence count');
  }
  const decodedBits: number[] = [];
  for (const sentence of sentences) {
    const template = pack.templates.find(t => sentence.startsWith(t.marker));
    if (!template) throw new TypeError('Unknown scheduled-story template');
    const phraseBits = decodeStructuredSentence(pack, sentence);
    decodedBits.push(...phraseBits.slice(template.prefix.length)); // marker is explicit: no selector entropy.
  }
  if (decodedBits.length < HEADER * 8) throw new TypeError('Truncated scheduled-story header');
  const parsed = bitsToBytes(decodedBits.slice(0, HEADER * 8));
  if (!MAGIC.every((b, i) => parsed[i] === b) || parsed[4] !== VERSION ||
      parsed[5] !== STORY_THEMES.indexOf(theme)) throw new TypeError('Scheduled-story envelope version mismatch');
  const byteLength = readU32(parsed, 6);
  if (byteLength > STORY_V2_MAX_PAYLOAD_BYTES) throw new RangeError('Oversized scheduled-story payload');
  const requiredBits = (HEADER + byteLength + CHECK) * 8;
  if (decodedBits.length < requiredBits || decodedBits.length >= requiredBits + 40 ||
      decodedBits.slice(requiredBits).some(b => b !== 0)) {
    throw new TypeError('Truncated or noncanonical scheduled-story padding');
  }
  const full = bitsToBytes(decodedBits.slice(0, requiredBits));
  const body = full.slice(0, HEADER + byteLength);
  const expected = (await sha256(body)).slice(0, CHECK);
  let diff = 0;
  for (let i = 0; i < CHECK; i++) diff |= expected[i]! ^ full[HEADER + byteLength + i]!;
  if (diff) throw new TypeError('Scheduled-story checksum mismatch');
  const bytes = body.slice(HEADER);
  if (await encodeBytes(bytes, theme) !== normalized) throw new TypeError('Noncanonical scheduled-story sequence');
  return Object.freeze({ bytes, theme });
}
