import test from 'node:test';
import assert from 'node:assert/strict';
import { ByteValue, encodeStoryV2, createFrameRudimentsStoryPreview } from '../dist/index.js';
const value = ByteValue.public(Uint8Array.of(0, 1, 2, 255), { namespace: 'danceflow', kind: 'node-id' });

test('FrameRudiments story preview returns only native identity text configuration', async () => {
  const story = await encodeStoryV2(value, 'music');
  const output = await createFrameRudimentsStoryPreview(value, 'music', {
    box: [0, 0, 640, 120], color: 'mint', fontSize: 22, maxSentences: 3
  });
  const lines = story.split('\n').slice(1);
  assert.equal(output.target, 'framerudiments.project.v1/identity');
  assert.equal(output.previewOnly, true);
  assert.deepEqual(output.identities.map(x => x.text), lines.slice(0, 3));
  assert.equal(output.omittedSentences, lines.length - 3);
  assert.deepEqual(output.effectTargets, ['identity:0', 'identity:1', 'identity:2']);
  assert.ok(output.identities.every(x => x.style.font_size === 22 && x.style.colour === '#9fe7ce'));
  assert.ok(output.identities.every(x => !('raster' in x) && !('effects' in x)));
  assert.ok(!('render' in output) && !('png' in output));
  assert.ok(Object.isFrozen(output.identities));
});

test('FrameRudiments preview rejects secret and invalid layouts, and marks loss of recoverability', async () => {
  const secret = ByteValue.secret(Uint8Array.of(1, 2), { namespace: 'wallet', kind: 'private-key' });
  const box = [0, 0, 300, 90];
  await assert.rejects(() => createFrameRudimentsStoryPreview(secret, 'music', { box }), /public/);
  await assert.rejects(() => createFrameRudimentsStoryPreview(value, 'music', { box: [0, 1, 0, 30] }));
  await assert.rejects(() => createFrameRudimentsStoryPreview(value, 'music', { box, maxSentences: 5 }));
  await assert.rejects(() => createFrameRudimentsStoryPreview(value, 'music', { box, fontSize: 5 }));
  const result = await createFrameRudimentsStoryPreview(value, 'fantasy', { box, maxSentences: 1 });
  assert.equal(result.identities.length, 1);
  assert.ok(result.omittedSentences > 0);
  assert.equal(result.previewOnly, true);
});
