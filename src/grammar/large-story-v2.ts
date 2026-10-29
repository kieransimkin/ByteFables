/**
 * V2 experimental large English sentence codec for PUBLIC binary bytes.
 * NOT BIP-39, not wallet compatible, not guaranteed meaningful when spoken.
 * Source word indexes are fixed by bytefables.large-lexicons.v1.
 */
import { assertPublicValue, type PublicByteValue } from '../value.js';
import { sha256 } from '../identity/sha256.js';
import { bytesToBits, bitsToBytes, concatBytes, readU32, writeU32 } from '../utils/binary.js';
import { decodeRadixBits, encodeRadixBits, radixCapacityBits } from './radix.js';
import { largeLexiconIndexV1, largeLexiconWordV1, LARGE_LEXICON_COUNTS_V1,
  type LexiconLocaleV1, type LexiconRoleV1 } from './large-lexicons-v1.js';

const MAGIC = Uint8Array.of(0x42, 0x46, 0x4c, 0x34); // BFL4
const VERSION = 2;
const HEADER_BYTES = 10; // magic4 + version1 + locale1 + length4
const CHECK_BYTES = 16;
export const LARGE_STORY_V2_MAX_PUBLIC_BYTES = 4096;
export const LARGE_STORY_V2_PAYLOAD_BITS = 66;
export const LARGE_STORY_V2_SENTENCE_BITS = 69;
export const LARGE_STORY_FORMAT_V2 = 'BYTEFABLES-LARGE-STORY-V2' as const;
const RADICES = [LARGE_LEXICON_COUNTS_V1.adjectives, LARGE_LEXICON_COUNTS_V1.nouns,
  LARGE_LEXICON_COUNTS_V1.verbs, LARGE_LEXICON_COUNTS_V1.adjectives,
  LARGE_LEXICON_COUNTS_V1.nouns] as const;
const ROLES: readonly LexiconRoleV1[] = ['adjectives','nouns','verbs','adjectives','nouns'];
if (radixCapacityBits(RADICES) !== LARGE_STORY_V2_PAYLOAD_BITS) {
  throw new Error('Breaking lexicon change: 66-bit sentence capacity altered');
}

interface Template { readonly prefix: string; readonly start: string; readonly end: string; readonly article: boolean; }
/** The first 3 bits choose exactly one canonical template (never inferred from prose). */
const TEMPLATES: readonly Template[] = Object.freeze([
  { prefix: '000', start: 'Yesterday, the ', end: '.', article: false },
  { prefix: '001', start: 'At dawn, the ', end: '.', article: false },
  { prefix: '010', start: 'The ', end: ' before sunset.', article: false },
  { prefix: '011', start: 'At midnight, the ', end: '.', article: false },
  { prefix: '100', start: 'Long ago, the ', end: '.', article: false },
  { prefix: '101', start: 'After the storm, the ', end: '.', article: false },
  { prefix: '110', start: 'Suddenly, an ', end: ' appeared.', article: true },
  { prefix: '111', start: 'Once, an ', end: ' vanished.', article: true },
]);
const MIDDLE = /^([a-z]+) ([a-z]+) ([a-z]+) the ([a-z]+) ([a-z]+)$/;
/** Initial-vowel orthography is not phonetic a/an agreement. The rendered
 * determiner is always computed from the adjective and never carries data. */
const article = (adjective: string): string => /^[aeiou]/.test(adjective) ? 'an ' : 'a ';
function assertLocale(locale: LexiconLocaleV1): 0 | 1 {
  if (locale === 'en-US') return 0;
  if (locale === 'en-GB') return 1;
  throw new TypeError('Unsupported experimental large-story locale');
}
function template(bits: readonly number[]): Template {
  const p = `${bits[0] ?? 0}${bits[1] ?? 0}${bits[2] ?? 0}`;
  const result = TEMPLATES.find(t => t.prefix === p);
  if (!result) throw new TypeError('Invalid template bits');
  return result;
}
function renderSentence(bits: readonly number[], locale: LexiconLocaleV1): string {
  if (bits.length !== LARGE_STORY_V2_SENTENCE_BITS) throw new RangeError('Wrong sentence bit count');
  const t = template(bits);
  const digits = encodeRadixBits(bits.slice(3), RADICES);
  const words = ROLES.map((role, i) => largeLexiconWordV1(role, locale, digits[i]!));
  const beginning = t.article ? t.start.slice(0, -3) + article(words[0]!) : t.start;
  return `${beginning}${words[0]} ${words[1]} ${words[2]} the ${words[3]} ${words[4]}${t.end}`;
}
function parseSentence(sentence: string, locale: LexiconLocaleV1): number[] {
  if (!sentence || sentence.length > 256) throw new TypeError('Invalid large-story sentence length');
  const t = TEMPLATES.find(row => (row.article ? sentence.startsWith(row.start.slice(0, -3)) : sentence.startsWith(row.start)) && sentence.endsWith(row.end));
  if (!t) throw new TypeError('Unknown or malformed large-story template');
  const preamble = t.article ? t.start.slice(0, -3) : t.start;
  const content = sentence.slice(preamble.length, sentence.length - t.end.length);
  const words = MIDDLE.exec(t.article ? content.replace(/^(?:a|an) /, '') : content);
  if (!words) throw new TypeError('Invalid large-story grammatical slots');
  if (t.article && !content.startsWith(article(words[1]!))) throw new TypeError('Noncanonical article agreement');
  const digits = ROLES.map((role, i) => largeLexiconIndexV1(role, locale, words[i + 1]!));
  return [...t.prefix.split('').map(Number), ...decodeRadixBits(digits, RADICES)];
}

export interface LargeStoryResultV2 {
  readonly bytes: Uint8Array;
  readonly locale: LexiconLocaleV1;
  readonly format: typeof LARGE_STORY_FORMAT_V2;
  readonly checksum: 'sha256-128-unkeyed';
}

async function frame(bytes: Uint8Array, locale: LexiconLocaleV1): Promise<Uint8Array> {
  const body = concatBytes(MAGIC, Uint8Array.of(VERSION, assertLocale(locale)), writeU32(bytes.length), bytes);
  return concatBytes(body, (await sha256(body)).slice(0, CHECK_BYTES));
}
async function encodePublicBytes(bytes: Uint8Array, locale: LexiconLocaleV1): Promise<string> {
  assertLocale(locale);
  if (!(bytes instanceof Uint8Array) || bytes.length > LARGE_STORY_V2_MAX_PUBLIC_BYTES) {
    throw new RangeError('Large-story public payload exceeds 4096 bytes');
  }
  const allBits = bytesToBits(await frame(bytes, locale));
  const sentences: string[] = [];
  for (let offset = 0; offset < allBits.length; offset += LARGE_STORY_V2_SENTENCE_BITS) {
    const bits = allBits.slice(offset, offset + LARGE_STORY_V2_SENTENCE_BITS);
    while (bits.length < LARGE_STORY_V2_SENTENCE_BITS) bits.push(0);
    sentences.push(renderSentence(bits, locale));
  }
  return `${LARGE_STORY_FORMAT_V2} ${locale}/2\n${sentences.join('\n')}`;
}

/** Exact binary recovery, but original typed namespace/kind is not included. */
export async function encodeLargeStoryV2(value: PublicByteValue,
  locale: LexiconLocaleV1 = 'en-GB'): Promise<string> {
  assertPublicValue(value);
  return encodePublicBytes(value.toBytes(), locale);
}

export async function decodeLargeStoryV2(text: string): Promise<LargeStoryResultV2> {
  if (typeof text !== 'string' || text.length > 450_000 || text.includes('\r') && !text.includes('\r\n')) {
    throw new TypeError('Malformed or oversized large-story input');
  }
  const canonical = text.replace(/\r\n/g, '\n');
  if (canonical.includes('\r')) throw new TypeError('Unsupported line ending');
  const [heading, ...sentences] = canonical.split('\n');
  const match = /^BYTEFABLES-LARGE-STORY-V2 (en-US|en-GB)\/2$/.exec(heading ?? '');
  if (!match) throw new TypeError('Invalid experimental large-story header');
  const locale = match[1] as LexiconLocaleV1;
  const minCount = Math.ceil((HEADER_BYTES + CHECK_BYTES) * 8 / LARGE_STORY_V2_SENTENCE_BITS);
  const maxCount = Math.ceil((HEADER_BYTES + CHECK_BYTES + LARGE_STORY_V2_MAX_PUBLIC_BYTES) * 8 / LARGE_STORY_V2_SENTENCE_BITS);
  if (sentences.length < minCount || sentences.length > maxCount) {
    throw new RangeError('Invalid large-story sentence count');
  }
  const allBits: number[] = [];
  for (const sentence of sentences) allBits.push(...parseSentence(sentence, locale));
  const header = bitsToBytes(allBits.slice(0, HEADER_BYTES * 8));
  if (!MAGIC.every((b, i) => b === header[i]) || header[4] !== VERSION ||
      header[5] !== assertLocale(locale)) throw new TypeError('Large-story header/check mismatch');
  const size = readU32(header, 6);
  if (size > LARGE_STORY_V2_MAX_PUBLIC_BYTES) throw new RangeError('Payload length exceeds published format limit');
  const requiredBits = (HEADER_BYTES + size + CHECK_BYTES) * 8;
  if (allBits.length < requiredBits || allBits.length >= requiredBits + LARGE_STORY_V2_SENTENCE_BITS ||
      allBits.slice(requiredBits).some(bit => bit !== 0)) {
    throw new TypeError('Large-story bits truncated, extended or noncanonical padding');
  }
  const payload = bitsToBytes(allBits.slice(0, requiredBits));
  const body = payload.subarray(0, HEADER_BYTES + size);
  const calculated = (await sha256(body)).slice(0, CHECK_BYTES);
  let mismatch = 0;
  for (let i = 0; i < CHECK_BYTES; i++) mismatch |= calculated[i]! ^ payload[HEADER_BYTES + size + i]!;
  if (mismatch !== 0) throw new TypeError('Large-story checksum mismatch; not authentication');
  const bytes = body.slice(HEADER_BYTES);
  if (await encodePublicBytes(bytes, locale) !== canonical) {
    throw new TypeError('Noncanonical large-story text');
  }
  return Object.freeze({ bytes, locale, format: LARGE_STORY_FORMAT_V2,
    checksum: 'sha256-128-unkeyed' as const });
}
