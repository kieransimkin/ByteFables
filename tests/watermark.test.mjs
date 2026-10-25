import test from 'node:test';
import assert from 'node:assert/strict';
import {
  ByteValue, PublicRecord, encodeHex, decodePublicWatermarkMessage,
  encodePublicWatermarkMessage, matchesPublicWatermarkMessage,
  planPublicWatermark, FORMAT_MANIFEST, executePublicFormat
} from '../dist/index.js';

const make = (suffix = 255) => new PublicRecord(
  ByteValue.public(Uint8Array.of(0, 1, 2, suffix), { namespace: 'danceflow', kind: 'node-id' }),
  { network: 'testnet', algorithm: 'sha256', endian: 'big' }
);

test('watermark message exact 96/128/256-bit digest prefixes and CRC recovery', async () => {
  const record = make();
  const fingerprints = [];
  for (const bytes of [12, 16, 32]) {
    const encoded = await encodePublicWatermarkMessage(record, bytes);
    assert.equal(encoded.length, bytes + 10);
    assert.equal(encodeHex(encoded.slice(0, 6)), `4246574d01${bytes.toString(16).padStart(2, '0')}`);
    const decoded = decodePublicWatermarkMessage(encoded);
    assert.equal(decoded.version, 1);
    assert.equal(decoded.digestBytes, bytes);
    assert.equal(decoded.digest.length, bytes);
    assert.match(decoded.fingerprint, /^bfrec1-[0-9a-f]+$/);
    assert.equal(decoded.fingerprint.length, 'bfrec1-'.length + bytes * 2);
    assert.ok(await matchesPublicWatermarkMessage(encoded, record));
    assert.equal(await matchesPublicWatermarkMessage(encoded, make(254)), false);
    fingerprints.push(decoded.fingerprint);
    // Defensive copying of parsed digest.
    decoded.digest.fill(0);
    assert.equal(await matchesPublicWatermarkMessage(encoded, record), true);
    const modified = encoded.slice();
    modified[6] ^= 0x01;
    assert.throws(() => decodePublicWatermarkMessage(modified), /CRC/);
  }
  assert.ok(fingerprints[2].startsWith(fingerprints[1]));
  assert.ok(fingerprints[1].startsWith(fingerprints[0]));
});

test('watermark message rejects malformed header, lengths and secret input', async () => {
  const good = await encodePublicWatermarkMessage(make());
  for (const offset of [0, 1, 2, 3, 4, 5, good.length - 1]) {
    const changed = good.slice(); changed[offset] ^= 0x80;
    assert.throws(() => decodePublicWatermarkMessage(changed));
  }
  assert.throws(() => decodePublicWatermarkMessage(good.slice(0, -1)));
  assert.throws(() => decodePublicWatermarkMessage(new Uint8Array(1000)));
  await assert.rejects(() => encodePublicWatermarkMessage(make(), 5));
  await assert.rejects(() => encodePublicWatermarkMessage(ByteValue.secret(Uint8Array.of(1), {
    namespace: 'wallet', kind: 'private-key'
  })));
  await assert.rejects(() => matchesPublicWatermarkMessage(good, ByteValue.secret(Uint8Array.of(1), {
    namespace: 'wallet', kind: 'private-key'
  })));
});

test('all four watermark carriers have planning-only, non-executable operation contracts', async () => {
  const carriers = [
    { kind: 'image', mimeType: 'image/jpeg', width: 1920, height: 1080 },
    { kind: 'audio', mimeType: 'audio/wav', sampleRate: 48000, channels: 2, durationSeconds: 45 },
    { kind: 'video', mimeType: 'video/mp4', width: 1920, height: 1080, fps: 30, durationSeconds: 60 },
    { kind: 'text', mimeType: 'text/plain', tokenCount: 2000, generationControlled: true }
  ];
  const expected = ['watermark/image-spatial', 'watermark/audio-spectral',
    'watermark/video-temporal', 'watermark/text-semantic'];
  for (let i = 0; i < carriers.length; i++) {
    const p = await planPublicWatermark(make(), carriers[i]);
    assert.equal(p.operation, 'watermark');
    assert.equal(p.formatId, expected[i]);
    assert.equal(p.eligibleForResearch, true);
    assert.equal(p.status, 'planning-only');
    assert.equal(p.messageBits, 176);
    assert.equal(p.digestBits, 96);
    assert.equal(p.eccBits, null);
    assert.equal(p.measuredCapacityBits, null);
    assert.equal(p.detectorAvailable, false);
    assert.equal(p.embedderAvailable, false);
    assert.equal(p.imperceptibilityValidated, false);
    assert.equal(p.robustnessValidated, false);
    assert.ok(Object.isFrozen(p));
    assert.ok(Object.isFrozen(p.testDistortions));
    assert.equal(FORMAT_MANIFEST.find(f => f.formatId === p.formatId).category, 'watermark');
    await assert.rejects(() => executePublicFormat(p.formatId, make()));
  }
});

test('watermark planner fails closed on unsuited media, unsupported MIME and distortion claims', async () => {
  const record = make();
  const tiny = await planPublicWatermark(record, { kind: 'image', mimeType: 'image/png', width: 20, height: 20 });
  assert.equal(tiny.eligibleForResearch, false);
  assert.equal(tiny.blockers.length, 1);
  const prose = await planPublicWatermark(record, { kind: 'text', mimeType: 'text/markdown',
    tokenCount: 100, generationControlled: false });
  assert.equal(prose.eligibleForResearch, false);
  assert.equal(prose.blockers.length, 2);
  assert.equal((await planPublicWatermark(record, { kind: 'video', mimeType: 'video/webm',
    width: 1280, height: 720, fps: 60, durationSeconds: 5 }, { digestBytes: 32 })).messageBits, 336);
  await assert.rejects(() => planPublicWatermark(record, { kind: 'image', mimeType: 'image/gif', width: 256, height: 256 }));
  await assert.rejects(() => planPublicWatermark(record, { kind: 'audio', mimeType: 'audio/wav', sampleRate: -1, channels: 2, durationSeconds: 20 }));
  await assert.rejects(() => planPublicWatermark(record, { kind: 'video', mimeType: 'video/mp4', width: 300, height: 300, fps: 0, durationSeconds: 4 }));
  await assert.rejects(() => planPublicWatermark(record, { kind: 'text', mimeType: 'text/plain', tokenCount: 2000, generationControlled: 'yes' }));
  await assert.rejects(() => planPublicWatermark(record, { kind: 'image', mimeType: 'image/png', width: 256, height: 256 },
    { testDistortions: ['crop', 'crop'] }));
  await assert.rejects(() => planPublicWatermark(record, { kind: 'image', mimeType: 'image/png', width: 256, height: 256 },
    { testDistortions: ['always-survive'] }));
  await assert.rejects(() => planPublicWatermark(record, { kind: 'image', mimeType: 'image/png', width: 256, height: 256 },
    { testDistortions: ['paraphrase'] }));
});

test('immutable cross-runtime watermark message v1 golden vectors', async () => {
  const { readFile } = await import('node:fs/promises');
  const v = JSON.parse(await readFile(new URL('./vectors/watermark-message-v1.json', import.meta.url)));
  assert.equal(v.schema, 'bytefables.watermark-vectors.v1');
  const record = make();
  for (const bytes of [12, 16, 32]) {
    assert.equal(encodeHex(await encodePublicWatermarkMessage(record, bytes)),
      v.messages[String(bytes * 8)]);
  }
});
