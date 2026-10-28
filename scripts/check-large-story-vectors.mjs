#!/usr/bin/env node
/** Independently pinned public-only story hashes: semantic tests live in Node test suite. */
import { createHash } from 'node:crypto';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { ByteValue, decodeHex, encodeLargeStoryV1, decodeLargeStoryV1 } from '../dist/index.js';
const root = fileURLToPath(new URL('..', import.meta.url));
const vectors = JSON.parse(readFileSync(fileURLToPath(new URL('../tests/vectors/large-story-v1.json',import.meta.url)),'utf8'));
for (const item of vectors.cases) {
  const value = ByteValue.public(decodeHex(item.publicHex), { namespace: 'test',kind: 'public-bytes' });
  const text = await encodeLargeStoryV1(value, item.locale);
  const hashed = createHash('sha256').update(text,'utf8').digest('hex');
  if (hashed !== item.sha256 || text.split('\n').length - 1 !== item.sentences ||
      !text.startsWith(item.firstLine)) throw new Error(`Large story vector mismatch: ${item.locale}, ${item.publicHex}`);
  const restored = await decodeLargeStoryV1(text);
  if (Buffer.from(restored.bytes).toString('hex') !== item.publicHex) throw new Error('Vector does not roundtrip');
}
console.log('Large-story v1 reference vectors verified');
