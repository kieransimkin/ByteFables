/**
 * Separate experimental large English sentence codec for PUBLIC binary bytes.
 * NOT BIP-39, not wallet compatible, not guaranteed meaningful when spoken.
 * Source word indexes are fixed by bytefables.large-lexicons.v1.
 */
import { assertPublicValue, type PublicByteValue } from '../value.js';
import { sha256 } from '../identity/sha256.js';
import { bytesToBits, bitsToBytes, concatBytes, readU32, writeU32 } from '../utils/binary.js';
import { decodeRadixBits, encodeRadixBits, radixCapacityBits } from './radix.js';
import { largeLexiconIndexV1, largeLexiconWordV1, LARGE_LEXICON_COUNTS_V1,
  type LexiconLocaleV1, type LexiconRoleV1 } from './large-lexicons-v1.js';

const MAGIC = Uint8Array.of(0x42, 0x46, 0x4c, 0x33); // BFL3
const VERSION = 1;
const HEADER_BYTES = 10; // magic4 + version1 + locale1 + length4
const CHECK_BYTES = 16;
export const LARGE_STORY_MAX_PUBLIC_BYTES = 4096;
export const LARGE_STORY_PAYLOAD_BITS = 66;
export const LARGE_STORY_SENTENCE_BITS = 68;
export const LARGE_STORY_FORMAT_V1 = 'BYTEFABLES-LARGE-STORY-V1' as const;
const RADICES = [LARGE_LEXICON_COUNTS_V1.adjectives, LARGE_LEXICON_COUNTS_V1.nouns,
  LARGE_LEXICON_COUNTS_V1.verbs, LARGE_LEXICON_COUNTS_V1.adjectives,
  LARGE_LEXICON_COUNTS_V1.nouns] as const;
const ROLES: readonly LexiconRoleV1[] = ['adjectives','nouns','verbs','adjectives','nouns'];
if (radixCapacityBits(RADICES) !== LARGE_STORY_PAYLOAD_BITS) {
  throw new Error('Breaking lexicon change: 66-bit sentence capacity altered');
}

interface Template { readonly prefix: '00'|'01'|'10'|'11'; readonly start: string; readonly end: string; }
const TEMPLATES: readonly Template[] = Object.freeze([
  { prefix: '00', start: 'Yesterday, the ', end: '.' },
  { prefix: '01', start: 'At dawn, the ', end: '.' },
  { prefix: '10', start: 'The ', end: ' before sunset.' },
  { prefix: '11', start: 'At midnight, the ', end: '.' }
]);
const MIDDLE = /^([a-z]+) ([a-z]+) ([a-z]+) the ([a-z]+) ([a-z]+)$/;
function assertLocale(locale: LexiconLocaleV1): 0 | 1 {
  if (locale === 'en-US') return 0;
  if (locale === 'en-GB') return 1;
  throw new TypeError('Unsupported experimental large-story locale');
}
function template(bits: readonly number[]): Template {
  const p = `${bits[0] ?? 0}${bits[1] ?? 0}`;
  const result = TEMPLATES.find(t => t.prefix === p);
  if (!result) throw new TypeError('Invalid template bits');
  return result;
}
function renderSentence(bits: readonly number[], locale: LexiconLocaleV1): string {
  if (bits.length !== LARGE_STORY_SENTENCE_BITS) throw new RangeError('Wrong sentence bit count');
  const t = template(bits);
  const digits = encodeRadixBits(bits.slice(2), RADICES);
  const words = ROLES.map((role, i) => largeLexiconWordV1(role, locale, digits[i]!));
  return `${t.start}${words[0]} ${words[1]} ${words[2]} the ${words[3]} ${words[4]}${t.end}`;
}
function parseSentence(sentence: string, locale: LexiconLocaleV1): number[] {
  if (!sentence || sentence.length > 256) throw new TypeError('Invalid large-story sentence length');
  const t = TEMPLATES.find(row => sentence.startsWith(row.start) && sentence.endsWith(row.end));
  if (!t) throw new TypeError('Unknown or malformed large-story template');
  const words = MIDDLE.exec(sentence.slice(t.start.length, sentence.length - t.end.length));
  if (!words) throw new TypeError('Invalid large-story grammatical slots');
  const digits = ROLES.map((role, i) => largeLexiconIndexV1(role, locale, words[i + 1]!));
  return [...t.prefix.split('').map(Number), ...decodeRadixBits(digits, RADICES)];
}

export interface LargeStoryResultV1 {
  readonly bytes: Uint8Array;
  readonly locale: LexiconLocaleV1;
  readonly format: typeof LARGE_STORY_FORMAT_V1;
  readonly checksum: 'sha256-128-unkeyed';
}

async function frame(bytes: Uint8Array, locale: LexiconLocaleV1): Promise<Uint8Array> {
  const body = concatBytes(MAGIC, Uint8Array.of(VERSION, assertLocale(locale)), writeU32(bytes.length), bytes);
  return concatBytes(body, (await sha256(body)).slice(0, CHECK_BYTES));
}
async function encodePublicBytes(bytes: Uint8Array, locale: LexiconLocaleV1): Promise<string> {
  assertLocale(locale);
  if (!(bytes instanceof Uint8Array) || bytes.length > LARGE_STORY_MAX_PUBLIC_BYTES) {
    throw new RangeError('Large-story public payload exceeds 4096 bytes');
  }
  const allBits = bytesToBits(await frame(bytes, locale));
  const sentences: string[] = [];
  for (let offset = 0; offset < allBits.length; offset += LARGE_STORY_SENTENCE_BITS) {
    const bits = allBits.slice(offset, offset + LARGE_STORY_SENTENCE_BITS);
    while (bits.length < LARGE_STORY_SENTENCE_BITS) bits.push(0);
    sentences.push(renderSentence(bits, locale));
  }
  return `${LARGE_STORY_FORMAT_V1} ${locale}/1\n${sentences.join('\n')}`;
}

/** Exact binary recovery, but original typed namespace/kind is not included. */
export async function encodeLargeStoryV1(value: PublicByteValue,
  locale: LexiconLocaleV1 = 'en-GB'): Promise<string> {
  assertPublicValue(value);
  return encodePublicBytes(value.toBytes(), locale);
}

export async function decodeLargeStoryV1(text: string): Promise<LargeStoryResultV1> {
  if (typeof text !== 'string' || text.length > 450_000 || text.includes('\r') && !text.includes('\r\n')) {
    throw new TypeError('Malformed or oversized large-story input');
  }
  const canonical = text.replace(/\r\n/g, '\n');
  if (canonical.includes('\r')) throw new TypeError('Unsupported line ending');
  const [heading, ...sentences] = canonical.split('\n');
  const match = /^BYTEFABLES-LARGE-STORY-V1 (en-US|en-GB)\/1$/.exec(heading ?? '');
  if (!match) throw new TypeError('Invalid experimental large-story header');
  const locale = match[1] as LexiconLocaleV1;
  const minCount = Math.ceil((HEADER_BYTES + CHECK_BYTES) * 8 / LARGE_STORY_SENTENCE_BITS);
  const maxCount = Math.ceil((HEADER_BYTES + CHECK_BYTES + LARGE_STORY_MAX_PUBLIC_BYTES) * 8 / LARGE_STORY_SENTENCE_BITS);
  if (sentences.length < minCount || sentences.length > maxCount) {
    throw new RangeError('Invalid large-story sentence count');
  }
  const allBits: number[] = [];
  for (const sentence of sentences) allBits.push(...parseSentence(sentence, locale));
  const header = bitsToBytes(allBits.slice(0, HEADER_BYTES * 8));
  if (!MAGIC.every((b, i) => b === header[i]) || header[4] !== VERSION ||
      header[5] !== assertLocale(locale)) throw new TypeError('Large-story header/check mismatch');
  const size = readU32(header, 6);
  if (size > LARGE_STORY_MAX_PUBLIC_BYTES) throw new RangeError('Payload length exceeds published format limit');
  const requiredBits = (HEADER_BYTES + size + CHECK_BYTES) * 8;
  if (allBits.length < requiredBits || allBits.length >= requiredBits + LARGE_STORY_SENTENCE_BITS ||
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
  return Object.freeze({ bytes, locale, format: LARGE_STORY_FORMAT_V1,
    checksum: 'sha256-128-unkeyed' as const });
}
