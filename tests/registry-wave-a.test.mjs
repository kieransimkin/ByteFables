import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import {
  ByteValue, PublicRecord, FORMAT_MANIFEST, validateFormatManifest,
  getFormatManifest, listFormatManifests, planPublicFormats,
  executePublicFormat, decodePublicRecord, verifyBuiltinRegistry,
  decodeHex, encodeBase32
} from '../dist/index.js';
const value = () => new PublicRecord(ByteValue.public(Uint8Array.of(0, 1, 2, 255), {
  namespace: 'danceflow', kind: 'node-id'
}));

test('immutable manifest snapshot and public-only metadata contract', async () => {
  verifyBuiltinRegistry();
  const file = JSON.parse(await readFile(new URL('../manifests/formats-v1.json', import.meta.url)));
  assert.equal(file.schema, 'bytefables-format-manifest-1');
  assert.deepEqual(file.formats, FORMAT_MANIFEST);
  assert.equal(getFormatManifest('symbol/qr-model2').maturity, 'planned');
  assert.equal(listFormatManifests({ maturity: 'planned' }).length, 8);
  for (const f of FORMAT_MANIFEST) {
    assert.ok(Object.isFrozen(f));
    assert.ok(Object.isFrozen(f.mediaTypes));
    assert.equal(f.sensitivity, 'public-only');
    if (f.maturity === 'planned') assert.equal(f.adapter, null);
  }
  assert.throws(() => FORMAT_MANIFEST.push({}));
  assert.throws(() => FORMAT_MANIFEST[0].mediaTypes.push('text/plain'));
});

test('manifest validation rejects invalid definitions without mutating inputs', () => {
  const valid = FORMAT_MANIFEST[0];
  assert.throws(() => validateFormatManifest([valid, valid]), /Duplicate|Invalid/i);
  const bad = property => validateFormatManifest([{ ...valid, ...property }]);
  assert.throws(() => bad({ formatId: 'not-a-namespace' }));
  assert.throws(() => bad({ version: 'latest' }));
  assert.throws(() => bad({ maxInputBytes: -1 }));
  assert.throws(() => bad({ maxOutputBytes: NaN }));
  assert.throws(() => bad({ mediaTypes: ['not-svg'] }));
  assert.throws(() => bad({ sensitivity: 'secret' }));
  assert.throws(() => bad({ maturity: 'planned' }));
  assert.throws(() => bad({ decoder: null }));
  const copy = [{ ...valid, mediaTypes: ['text/plain'] }];
  validateFormatManifest(copy);
  copy[0].mediaTypes[0] = 'application/json';
  assert.equal(FORMAT_MANIFEST[0].mediaTypes[0], 'text/plain');
});

test('capacity planner filters by goal, input size, maturity and media type', () => {
  const typed = planPublicFormats({ byteLength: 32, goal: 'recover-typed' });
  assert.deepEqual(typed.map(x => x.formatId), ['archive/public-cbor-v1']);
  assert.equal(typed[0].guarantee, 'reversible-typed');
  assert.equal(typed[0].executable, true);
  const names = planPublicFormats({ byteLength: 32, goal: 'identify' });
  assert.ok(names.some(x => x.formatId === 'identity/pixel-avatar-v1'));
  assert.ok(!names.some(x => x.formatId === 'symbol/qr-model2'));
  const planned = planPublicFormats({ byteLength: 32, includePlanned: true });
  assert.equal(planned.find(x => x.formatId === 'symbol/qr-model2').executable, false);
  assert.ok(planned.some(x => x.formatId === 'wallet/bip39'));
  const huge = planPublicFormats({ byteLength: 1048576 });
  assert.ok(!huge.some(x => x.formatId === 'codec/story-prototype-13'));
  assert.ok(planPublicFormats({ byteLength: 128, goal: 'recover-any', mediaType: 'image/png' }).length === 0);
  assert.throws(() => planPublicFormats({ byteLength: -1 }));
  assert.throws(() => planPublicFormats({ byteLength: NaN }));
  assert.throws(() => planPublicFormats({ byteLength: 32, goal: 'decrypt-secret' }));
});

test('dispatcher runs installed public adapters and refuses planned, secret and unapproved experimental', async () => {
  const record = value();
  const hex = await executePublicFormat('codec/hex', record);
  assert.equal(hex.data, '000102ff');
  assert.equal((await executePublicFormat('codec/rfc4648-base32-nopad', record)).data,
    encodeBase32(record.toBytes()));
  const cbor = await executePublicFormat('archive/public-cbor-v1', record);
  assert.deepEqual((await decodePublicRecord(cbor.data)).toBytes(), record.toBytes());
  assert.ok((await executePublicFormat('identity/pixel-avatar-v1', record)).data.startsWith('<svg'));
  assert.match((await executePublicFormat('identity/record-fingerprint-v1', record)).data, /^bfrec1-/);
  await assert.rejects(() => executePublicFormat('wallet/bip39', record));
  await assert.rejects(() => executePublicFormat('symbol/qr-model2', record));
  await assert.rejects(() => executePublicFormat('codec/story-prototype-13', record));
  await assert.rejects(() => executePublicFormat('bad-format', record));
  await assert.rejects(() => executePublicFormat('codec/hex', ByteValue.secret(decodeHex('00'), {
    namespace: 'x', kind: 'secret'
  })));
  assert.match((await executePublicFormat('codec/story-prototype-13', record,
    { allowExperimental: true })).data, /^BYTEFABLES-STORY-PROTOTYPE-1/);
});
