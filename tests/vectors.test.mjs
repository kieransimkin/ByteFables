import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { createHash } from 'node:crypto';
import {
  ByteValue, decodeHex, encodeHex, identityDigest, identityFingerprint,
  renderPixelAvatar, encodeExperimentalStory, decodeExperimentalStory
} from '../dist/index.js';

const vectors = JSON.parse(readFileSync(new URL('./vectors/v1.json', import.meta.url), 'utf8'));

test('immutable public identity vectors', async () => {
  for (const vector of vectors.identity) {
    const value = ByteValue.public(decodeHex(vector.hex), vector);
    assert.equal(encodeHex(await identityDigest(value)), vector.digestHex);
    assert.equal(await identityFingerprint(value), vector.fingerprint);
    const svg = await renderPixelAvatar(value);
    assert.equal(createHash('sha256').update(svg).digest('hex'), vector.svgSha256);
  }
});

test('immutable experimental sentence vectors', () => {
  for (const vector of vectors.story) {
    const bytes = decodeHex(vector.hex);
    const value = ByteValue.public(bytes, { namespace: 'test', kind: 'opaque' });
    assert.equal(encodeExperimentalStory(value), vector.text);
    assert.equal(encodeHex(decodeExperimentalStory(vector.text)), vector.hex);
  }
});
