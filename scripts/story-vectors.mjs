#!/usr/bin/env node
/** Immutable stage-2 grammar index and story wire-format vectors. */
import { readFile, writeFile } from 'node:fs/promises';
import { createHash } from 'node:crypto';
import {
  ByteValue, encodeStoryV2, encodeScheduledStory,
  STORY_THEMES, STORY_PACKS, SCHEDULED_STORY_PACKS
} from '../dist/index.js';

const sha = (data) => createHash('sha256').update(data).digest('hex');
const input = Uint8Array.from([0, 1, 2, 3, 4, 5, 254, 255]);
const data = ByteValue.public(input, { namespace: 'test', kind: 'public-fixture' });
const vectors = [];
for (const theme of STORY_THEMES) {
  const p = STORY_PACKS[theme];
  const scheduled = SCHEDULED_STORY_PACKS[theme];
  const canonical = pack => ({ id: pack.id, version: pack.version,
    templates: pack.templates.map(t => ({ id: t.id, prefix: t.prefix,
      payloadBits: t.payloadBits, marker: t.marker,
      parts: t.parts.map(x => x.type === 'literal' ? { type: 'literal', text: x.text } :
        { type: x.type, role: x.role, words: x.words, byWord: x.byWord, dependsOn: x.dependsOn }) })) });
  vectors.push({ theme, payloadHex: Buffer.from(input).toString('hex'),
    canonicalPackSha256: sha(JSON.stringify(canonical(p))),
    scheduledPackSha256: sha(JSON.stringify(canonical(scheduled))),
    prefixStory: await encodeStoryV2(data, theme),
    scheduledStory: await encodeScheduledStory(data, theme) });
}
const text = JSON.stringify({ schema: 'bytefables-story-v2-vectors-1',
  status: 'experimental-public-data-only', vectors }, null, 2) + '\n';
const path = new URL('../tests/vectors/story-v2.json', import.meta.url);
if (process.argv[2] === '--write') {
  await writeFile(path, text, 'utf8');
  console.log('Wrote grammar v2 vectors');
} else if (process.argv[2] === '--check') {
  if (await readFile(path, 'utf8') !== text) {
    throw new Error('Story/codebook vectors changed; version migration and explicit review required');
  }
  console.log('Grammar v2 vectors verified');
} else {
  throw new Error('Usage: node scripts/story-vectors.mjs --write|--check');
}
