import test from 'node:test';
import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import {
  ByteValue, encodeHex, identityDigest, identityFingerprint, renderPixelAvatar
} from '../dist/index.js';

const spec = { namespace: 'danceflow', kind: 'node-id' };
const value = (data, options = spec) => ByteValue.public(data, options);
const u32 = value => Uint8Array.of(value >>> 24, (value >>> 16) & 255, (value >>> 8) & 255, value & 255);

test('public value snapshots the input and never exposes mutable backing bytes', () => {
  const data = Uint8Array.of(1, 2, 3);
  const node = value(data);
  data[0] = 99;
  assert.deepEqual(node.toBytes(), Uint8Array.of(1, 2, 3));
  const copy = node.toBytes();
  copy[1] = 99;
  assert.deepEqual(node.toBytes(), Uint8Array.of(1, 2, 3));
  assert.equal(node.sensitivity, 'public');
  assert.throws(() => value(data, { namespace: 'danceflow', kind: 'private-key' }));
  assert.throws(() => value(data, { namespace: '', kind: 'node-id' }));
});

test('identity digest matches independently calculated length-prefixed SHA-256', async () => {
  const bytes = Uint8Array.of(0, 1, 255);
  const node = value(bytes);
  const enc = new TextEncoder();
  const ns = enc.encode(spec.namespace), kind = enc.encode(spec.kind);
  const expected = createHash('sha256')
    .update(enc.encode('ByteFables:public-identity:v1\0'))
    .update(u32(ns.length)).update(ns)
    .update(u32(kind.length)).update(kind)
    .update(u32(bytes.length)).update(bytes).digest('hex');
  assert.equal(encodeHex(await identityDigest(node)), expected);
  assert.equal(await identityFingerprint(node), `bf1-${expected.slice(0, 24)}`);
  assert.equal((await identityFingerprint(node, 32)).length, 4 + 64);
});

test('identical values have identical avatars and namespace/kind differences change identity', async () => {
  const a = value(Uint8Array.of(1, 2, 3));
  const b = value(Uint8Array.of(1, 2, 3));
  const otherNamespace = value(Uint8Array.of(1, 2, 3), { namespace: 'another', kind: 'node-id' });
  const otherKind = value(Uint8Array.of(1, 2, 3), { namespace: 'danceflow', kind: 'address' });
  assert.equal(await identityFingerprint(a), await identityFingerprint(b));
  assert.notEqual(await identityFingerprint(a), await identityFingerprint(otherNamespace));
  assert.notEqual(await identityFingerprint(a), await identityFingerprint(otherKind));
  const avatar = await renderPixelAvatar(a, { size: 128 });
  assert.equal(avatar, await renderPixelAvatar(b, { size: 128 }));
  assert.notEqual(avatar, await renderPixelAvatar(otherNamespace));
  assert.ok(avatar.startsWith('<svg '));
  assert.ok(avatar.includes('width="128"'));
  await assert.rejects(renderPixelAvatar(a, { size: 1000000 }));
});

test('secret value is rejected by public-facing identity and avatar entry points', async () => {
  const secret = ByteValue.secret(Uint8Array.of(9, 9), { namespace: 'wallet', kind: 'private-key' });
  await assert.rejects(identityDigest(secret));
  await assert.rejects(identityFingerprint(secret));
  await assert.rejects(renderPixelAvatar(secret));
});
