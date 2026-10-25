import test from 'node:test';
import assert from 'node:assert/strict';
import { ByteValue, encodeHex, encodeScheduledStory, decodeScheduledStory, STORY_THEMES,
  SCHEDULED_STORY_PACKS, encodeStoryV2, decodeStoryV2,
  executePublicFormat, PublicRecord, planPublicFormats } from '../dist/index.js';
const pub = b => ByteValue.public(b, { namespace: 'example', kind: 'public-id' });

test('scheduled grammar variants encode exactly 24/32/40 payload bits; template IDs add no bits', () => {
  for (const theme of STORY_THEMES) {
    const pack = SCHEDULED_STORY_PACKS[theme];
    assert.deepEqual(pack.templates.map(t => t.payloadBits), [24, 32, 40]);
    assert.deepEqual(pack.templates.map(t => t.prefix), ['0', '10', '11']);
  }
});

test('scheduled story supports full public binary size range and all themes', async () => {
  for (const theme of STORY_THEMES) {
    for (const n of [0, 1, 2, 16, 20, 24, 32, 33, 48, 64, 65, 78, 96, 128, 256, 512]) {
      const bytes = Uint8Array.from({ length: n }, (_, i) => (i * 13 + n) % 256);
      const text = await encodeScheduledStory(pub(bytes), theme);
      assert.equal(encodeHex((await decodeScheduledStory(text)).bytes), encodeHex(bytes));
      assert.equal(await encodeScheduledStory(pub(bytes), theme), text);
      assert.equal(encodeHex((await decodeScheduledStory(text.replaceAll('\n', '\r\n'))).bytes), encodeHex(bytes));
    }
  }
  const giant = Uint8Array.from({ length: 4096 }, (_, i) => i % 251);
  assert.deepEqual((await decodeScheduledStory(await encodeScheduledStory(pub(giant)))).bytes, giant);
});

test('scheduled story detects corruption, noncanonical schedules and secret inputs', async () => {
  const text = await encodeScheduledStory(pub(Uint8Array.from({ length: 32 }, (_, i) => i)));
  const lines = text.split('\n');
  await assert.rejects(() => decodeScheduledStory(lines.slice(0, -1).join('\n')));
  await assert.rejects(() => decodeScheduledStory(text + '\n' + lines.at(-1)));
  await assert.rejects(() => decodeScheduledStory(text.replace('nature/1', 'music/1')));
  const scrambled = [...lines]; [scrambled[1], scrambled[2]] = [scrambled[2], scrambled[1]];
  await assert.rejects(() => decodeScheduledStory(scrambled.join('\n')));
  await assert.rejects(() => decodeScheduledStory(text.replace(/\.$/, '!')));
  const prefixText = await encodeStoryV2(pub(Uint8Array.of(0)));
  await assert.rejects(() => decodeScheduledStory(prefixText));
  await assert.rejects(() => decodeStoryV2(text));
  const secret = ByteValue.secret(Uint8Array.of(1), { namespace: 'seed', kind: 'private-key' });
  await assert.rejects(() => encodeScheduledStory(secret), /public/);
  await assert.rejects(() => encodeScheduledStory(pub(new Uint8Array(4097))), /PUBLIC/);
});

test('manifest safely dispatches v2 codecs only with experimental opt-in', async () => {
  const record = new PublicRecord(pub(Uint8Array.of(0, 1, 2, 255)));
  const formats = planPublicFormats({ byteLength: 32, includeExperimental: true });
  assert.ok(formats.some(x => x.formatId === 'codec/story-v2-prefix' && x.executable));
  assert.ok(formats.some(x => x.formatId === 'codec/story-v2-scheduled' && x.executable));
  await assert.rejects(() => executePublicFormat('codec/story-v2-prefix', record));
  const prefix = await executePublicFormat('codec/story-v2-prefix', record, { allowExperimental: true });
  const scheduled = await executePublicFormat('codec/story-v2-scheduled', record, { allowExperimental: true });
  assert.deepEqual((await decodeStoryV2(prefix.data)).bytes, record.toBytes());
  assert.deepEqual((await decodeScheduledStory(scheduled.data)).bytes, record.toBytes());
});
