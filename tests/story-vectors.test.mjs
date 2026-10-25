import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { createHash } from 'node:crypto';
import { ByteValue, encodeHex, encodeStoryV2, decodeStoryV2,
  encodeScheduledStory, decodeScheduledStory, STORY_THEMES } from '../dist/index.js';

const doc = JSON.parse(readFileSync(new URL('./vectors/story-v2.json', import.meta.url)));
test('immutable v2 story vectors and codebook digests are present', async () => {
  assert.equal(doc.schema, 'bytefables-story-v2-vectors-1');
  assert.equal(doc.status, 'experimental-public-data-only');
  assert.equal(doc.vectors.length, STORY_THEMES.length);
  for (const row of doc.vectors) {
    const bytes = Uint8Array.from(Buffer.from(row.payloadHex, 'hex'));
    const publicBytes = ByteValue.public(bytes, { namespace: 'test', kind: 'public-fixture' });
    assert.match(row.canonicalPackSha256, /^[0-9a-f]{64}$/);
    assert.match(row.scheduledPackSha256, /^[0-9a-f]{64}$/);
    assert.equal(await encodeStoryV2(publicBytes, row.theme), row.prefixStory);
    assert.equal(await encodeScheduledStory(publicBytes, row.theme), row.scheduledStory);
    assert.equal(encodeHex((await decodeStoryV2(row.prefixStory)).bytes), row.payloadHex);
    assert.equal(encodeHex((await decodeScheduledStory(row.scheduledStory)).bytes), row.payloadHex);
  }
});
