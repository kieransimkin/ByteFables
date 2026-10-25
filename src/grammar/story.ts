import { assertPublicValue, type PublicByteValue } from '../value.js';
import { bytesToBits, bitsToBytes, concatBytes, readU32, writeU32 } from '../utils/binary.js';
import { crc32 } from '../utils/crc32.js';
import { DEFAULT_GRAMMAR_PACK } from './default-pack.js';
import { encodeSentence, decodeSentence } from './compiler.js';

const MAGIC = Uint8Array.of(0x42, 0x46, 0x42, 0x4c); // BFBL
const VERSION = 1;
const LABEL = 'BYTEFABLES-STORY-PROTOTYPE-1';
const MAX_STORY_BYTES = 4096;
const HEADER_BYTES = 9; // magic[4] || version[1] || length_u32_be[4]
const TRAILER_BYTES = 4; // crc32_u32_be, covers header and payload
const BITS_PER_SENTENCE = DEFAULT_GRAMMAR_PACK.sentenceBits;

/**
 * Experimental, non-wallet-safe demo format. Input must be publicly disclosed bytes.
 * Layout: BFBL | u8 version | u32 BE length | raw bytes | CRC-32 BE.
 * MSB-first bits, 13 per sentence, zero-padded in last sentence.
 */
export function encodeExperimentalStory(input: PublicByteValue): string {
  assertPublicValue(input);
  const bytes = input.toBytes();
  if (bytes.length > MAX_STORY_BYTES) throw new RangeError('Story input is too long');
  const body = concatBytes(MAGIC, Uint8Array.of(VERSION), writeU32(bytes.length), bytes);
  const envelope = concatBytes(body, writeU32(crc32(body)));
  const bits = bytesToBits(envelope);
  const sentences: string[] = [];
  for (let offset = 0; offset < bits.length; offset += BITS_PER_SENTENCE) {
    const chunk = bits.slice(offset, offset + BITS_PER_SENTENCE);
    while (chunk.length < BITS_PER_SENTENCE) chunk.push(0);
    sentences.push(encodeSentence(DEFAULT_GRAMMAR_PACK, chunk));
  }
  return `${LABEL}\n${sentences.join('\n')}`;
}

/** Returns recovered raw bytes only. Caller must supply external type/namespace metadata. */
export function decodeExperimentalStory(story: string): Uint8Array {
  if (typeof story !== 'string') throw new TypeError('Expected a story string');
  const lines = story.replace(/\r\n/g, '\n').split('\n');
  if (lines[0] !== LABEL) throw new TypeError('Unknown or unsupported story format');
  const sentences = lines.slice(1);
  const maxSentences = Math.ceil((HEADER_BYTES + MAX_STORY_BYTES + TRAILER_BYTES) * 8 / BITS_PER_SENTENCE);
  if (sentences.length < Math.ceil((HEADER_BYTES + TRAILER_BYTES) * 8 / BITS_PER_SENTENCE) ||
      sentences.length > maxSentences) {
    throw new RangeError('Invalid number of sentences');
  }
  const bits = sentences.flatMap(sentence => decodeSentence(DEFAULT_GRAMMAR_PACK, sentence));
  const header = bitsToBytes(bits.slice(0, HEADER_BYTES * 8));
  if (!MAGIC.every((b, i) => b === header[i]) || header[4] !== VERSION) {
    throw new TypeError('Invalid story magic or version');
  }
  const payloadLength = readU32(header, 5);
  if (payloadLength > MAX_STORY_BYTES) throw new RangeError('Story claims too much data');
  const expectedBytes = HEADER_BYTES + payloadLength + TRAILER_BYTES;
  const expectedBits = expectedBytes * 8;
  const expectedSentenceCount = Math.ceil(expectedBits / BITS_PER_SENTENCE);
  if (sentences.length !== expectedSentenceCount || bits.slice(expectedBits).some(b => b !== 0)) {
    throw new TypeError('Noncanonical or truncated story bitstream');
  }
  const envelope = bitsToBytes(bits.slice(0, expectedBits));
  const body = envelope.slice(0, -TRAILER_BYTES);
  const expectedCrc = readU32(envelope, body.length);
  if (crc32(body) !== expectedCrc) {
    throw new TypeError('Story checksum mismatch (CRC-32 is not authentication)');
  }
  return body.slice(HEADER_BYTES);
}
