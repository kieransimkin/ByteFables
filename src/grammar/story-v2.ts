/** ByteFables story v2: exact public-data-only narrative transport.
 * NOT BIP-39, NOT BIP-450/Formosa, NOT intended for private keys.
 */
import { assertPublicValue, type PublicByteValue } from '../value.js';
import { sha256 } from '../identity/sha256.js';
import { bytesToBits, bitsToBytes, concatBytes, readU32, writeU32 } from '../utils/binary.js';
import { decodeStructuredSentence, encodeStructuredSentence, selectStoryTemplate } from './structured.js';
import { STORY_THEMES, getStoryPack, type StoryTheme } from './themes.js';

const LABEL = 'BYTEFABLES-STORY-V2';
const MAGIC = Uint8Array.of(0x42, 0x46, 0x53, 0x32); // BFS2
const VERSION = 2;
const HEADER_BYTES = 10; // magic4 + version1 + theme1 + u32 length4
const CHECK_BYTES = 16; // truncated SHA-256; accidental integrity, NOT authentication
export const STORY_V2_MAX_PAYLOAD_BYTES = 4096;
const MAX_STORY_LENGTH = 440_000;

export interface StoryV2Result {
  readonly bytes: Uint8Array;
  readonly theme: StoryTheme;
  readonly version: 2;
  readonly checksum: 'sha256-128-unkeyed';
  readonly byteLength: number;
}

function parseTheme(theme: string): StoryTheme {
  if (!STORY_THEMES.includes(theme as StoryTheme)) throw new TypeError('Unrecognised story theme');
  return theme as StoryTheme;
}

async function frameBytes(bytes: Uint8Array, theme: StoryTheme): Promise<Uint8Array> {
  if (!(bytes instanceof Uint8Array) || bytes.length > STORY_V2_MAX_PAYLOAD_BYTES) {
    throw new RangeError('Story v2 payload is limited to 4,096 public bytes');
  }
  const themeId = STORY_THEMES.indexOf(theme);
  if (themeId < 0) throw new TypeError('Unsupported story theme');
  const body = concatBytes(MAGIC, Uint8Array.of(VERSION, themeId), writeU32(bytes.length), bytes);
  const checksum = (await sha256(body)).slice(0, CHECK_BYTES);
  return concatBytes(body, checksum);
}

/** Prefix-coded selection consumes real encoded bits, not derived artistic randomness. */
export async function encodeStoryV2(input: PublicByteValue, theme: StoryTheme = 'nature'): Promise<string> {
  assertPublicValue(input);
  return encodeStoryV2Bytes(input.toBytes(), theme);
}

async function encodeStoryV2Bytes(bytes: Uint8Array, theme: StoryTheme): Promise<string> {
  const pack = getStoryPack(theme);
  const framed = await frameBytes(bytes, theme);
  const bits = bytesToBits(framed);
  const sentences: string[] = [];
  for (let index = 0; index < bits.length;) {
    const template = selectStoryTemplate(pack, bits.slice(index));
    const capacity = template.sentenceBits;
    const chunk = bits.slice(index, index + capacity);
    while (chunk.length < capacity) chunk.push(0);
    const prefix = template.prefix.split('').map(Number);
    if (prefix.some((b, i) => chunk[i] !== b)) {
      throw new TypeError('Invalid template selector');
    }
    sentences.push(encodeStructuredSentence(template, chunk.slice(prefix.length)));
    index += capacity;
  }
  return `${LABEL} ${theme}/1\n${sentences.join('\n')}`;
}

/** Recover raw bytes only. Source namespace, kind, network and key use are NOT preserved. */
export async function decodeStoryV2(text: string): Promise<StoryV2Result> {
  if (typeof text !== 'string' || text.length > MAX_STORY_LENGTH || text.includes('\r') &&
      !/\r\n/.test(text)) {
    throw new TypeError('Invalid story v2 input');
  }
  // Only CRLF -> LF is supported; all lexical whitespace is an immutable codebook rule.
  const normalized = text.replace(/\r\n/g, '\n');
  if (normalized.includes('\r')) throw new TypeError('Unexpected carriage return');
  const lines = normalized.split('\n');
  const match = /^BYTEFABLES-STORY-V2 (nature|technology|music|fantasy|science|humour)\/1$/.exec(lines[0] || '');
  if (!match) throw new TypeError('Unsupported or malformed story v2 header');
  const theme = parseTheme(match[1]!);
  const pack = getStoryPack(theme);
  const sentences = lines.slice(1);
  const maxSentenceCount = Math.ceil((STORY_V2_MAX_PAYLOAD_BYTES + HEADER_BYTES + CHECK_BYTES) * 8 /
    pack.minSentenceBits) + 1;
  const minSentenceCount = Math.ceil((HEADER_BYTES + CHECK_BYTES) * 8 / pack.maxSentenceBits);
  if (sentences.length < minSentenceCount || sentences.length > maxSentenceCount) {
    throw new RangeError('Invalid sentence count');
  }
  const bits: number[] = [];
  for (const sentence of sentences) {
    bits.push(...decodeStructuredSentence(pack, sentence));
  }
  if (bits.length < (HEADER_BYTES + CHECK_BYTES) * 8) {
    throw new TypeError('Truncated story header');
  }
  const header = bitsToBytes(bits.slice(0, HEADER_BYTES * 8));
  if (!MAGIC.every((b, i) => b === header[i]) || header[4] !== VERSION ||
      header[5] !== STORY_THEMES.indexOf(theme)) {
    throw new TypeError('Story marker, version or theme mismatch');
  }
  const size = readU32(header, 6);
  if (size > STORY_V2_MAX_PAYLOAD_BYTES) throw new RangeError('Story declares excessive payload');
  const requiredBits = (HEADER_BYTES + size + CHECK_BYTES) * 8;
  if (bits.length < requiredBits || bits.length >= requiredBits + pack.maxSentenceBits ||
      bits.slice(requiredBits).some(b => b !== 0)) {
    throw new TypeError('Truncated, extended or nonzero-padded story');
  }
  const envelope = bitsToBytes(bits.slice(0, requiredBits));
  const body = envelope.subarray(0, HEADER_BYTES + size);
  const expected = (await sha256(body)).slice(0, CHECK_BYTES);
  const actual = envelope.subarray(HEADER_BYTES + size);
  // Full-buffer comparison (not authentication; not an attacker-controlled key check).
  let mismatch = 0;
  for (let i = 0; i < CHECK_BYTES; i++) mismatch |= expected[i]! ^ actual[i]!;
  if (mismatch !== 0) throw new TypeError('Story integrity mismatch (not cryptographic authentication)');
  const recovered = body.slice(HEADER_BYTES);
  // The canonical re-encoder makes extra sentences, alternative splitting,
  // nonminimal padding, and alternate but mathematically valid strings invalid.
  if (await encodeStoryV2Bytes(recovered, theme) !== normalized) {
    throw new TypeError('Noncanonical story sequence');
  }
  return Object.freeze({ bytes: recovered, theme, version: 2 as const,
    checksum: 'sha256-128-unkeyed' as const, byteLength: size });
}

export interface StoryV2Statistics {
  readonly theme: StoryTheme;
  readonly inputBits: number;
  readonly framedBits: number;
  readonly sentenceCount: number;
  readonly sentenceCapacities: readonly number[];
  readonly visibleWordCount: number;
  readonly textCharacters: number;
  readonly format: 'bytefables-story-v2';
}

/** Real lengths from the canonical framed bitstream; no claimed entropy from filler words. */
export async function inspectStoryV2(input: PublicByteValue, theme: StoryTheme = 'nature'): Promise<StoryV2Statistics> {
  assertPublicValue(input);
  const text = await encodeStoryV2(input, theme);
  const pack = getStoryPack(theme);
  const sentences = text.split('\n').slice(1);
  return Object.freeze({ theme, inputBits: input.byteLength * 8,
    framedBits: (HEADER_BYTES + input.byteLength + CHECK_BYTES) * 8,
    sentenceCount: sentences.length,
    sentenceCapacities: Object.freeze(sentences.map(s => {
      const prefix = pack.templates.find(t => s.startsWith(t.marker));
      if (!prefix) throw new TypeError('Generated story had an unknown marker');
      return prefix.sentenceBits;
    })),
    visibleWordCount: sentences.reduce((n, s) => n + s.split(/\s+/).length, 0),
    textCharacters: text.length, format: 'bytefables-story-v2' as const });
}
