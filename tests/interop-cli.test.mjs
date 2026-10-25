import test from 'node:test';
import assert from 'node:assert/strict';
import { execFileSync, spawnSync } from 'node:child_process';
import { ByteValue, PublicRecord, executePublicFormat, decodePublicTextFormat, encodeHex } from '../dist/index.js';
const record = () => new PublicRecord(ByteValue.public(Uint8Array.of(0, 1, 2, 255), { namespace: 'danceflow', kind: 'node-id' }));

test('public dispatcher encodes and decodes all Stage 3 raw formats', async () => {
  const fixture = record();
  const ids = ['codec/hex', 'codec/rfc4648-base32-nopad', 'codec/base45',
    'codec/base64-padded', 'codec/base64url-nopad', 'codec/crockford32-check',
    'codec/bytewords', 'codec/bytewords-uri', 'codec/bytewords-minimal',
    'codec/multibase-base32', 'codec/multibase-base64url'];
  for (const id of ids) {
    const result = await executePublicFormat(id, fixture);
    assert.equal(result.formatId, id);
    assert.equal(encodeHex(await decodePublicTextFormat(id, result.data)), '000102ff', id);
  }
  const cbor = await executePublicFormat('codec/ur-bytes-test-only', fixture, { allowExperimental: true });
  await assert.rejects(() => decodePublicTextFormat(cbor.formatId, cbor.data));
  assert.equal(encodeHex(await decodePublicTextFormat(cbor.formatId, cbor.data, { allowExperimental: true })), '000102ff');
  await assert.rejects(() => decodePublicTextFormat('wallet/bip39', 'abandon abandon'));
  await assert.rejects(() => decodePublicTextFormat('identity/pixel-avatar-v1', 'anything'));
});

test('BIP39 public fixture remains explicitly experimental in registry and CLI', async () => {
  const r = new PublicRecord(ByteValue.public(new Uint8Array(16), { namespace: 'test', kind: 'fixture' }));
  await assert.rejects(() => executePublicFormat('codec/bip39-public-fixture', r));
  const a = await executePublicFormat('codec/bip39-public-fixture', r, { allowExperimental: true });
  assert.match(a.data, /^abandon /);
  assert.equal(encodeHex(await decodePublicTextFormat(a.formatId, a.data, { allowExperimental: true })), '00'.repeat(16));
  const invoked = spawnSync(process.execPath, ['bin/bytefables.mjs', 'decode-public-text',
    '--confirm-public', '--format', 'codec/bip39-public-fixture', '--text', a.data, '--experimental'], { encoding: 'utf8' });
  assert.equal(invoked.status, 0, invoked.stderr);
  assert.equal(JSON.parse(invoked.stdout).bytesHex, '00'.repeat(16));
  const refused = spawnSync(process.execPath, ['bin/bytefables.mjs', 'decode-public-text',
    '--format', 'codec/bip39-public-fixture', '--text', a.data, '--experimental'], { encoding: 'utf8' });
  assert.notEqual(refused.status, 0);
  assert.match(refused.stderr, /confirm-public/);
});
