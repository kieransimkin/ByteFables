import { test } from 'node:test';
import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { encodeQrModel2, qrByteCapacity, ModuleMatrix } from '../dist/index.js';

const ascii = s => new TextEncoder().encode(s);
const digest = bytes => createHash('sha256').update(bytes).digest('hex');

test('QR Model 2 standard byte capacities (versions 1–40)', () => {
  assert.deepEqual(['L', 'M', 'Q', 'H'].map(level => qrByteCapacity(1, level)), [17, 14, 11, 7]);
  assert.deepEqual(['L', 'M', 'Q', 'H'].map(level => qrByteCapacity(2, level)), [32, 26, 20, 14]);
  assert.deepEqual(['L', 'M', 'Q', 'H'].map(level => qrByteCapacity(40, level)), [2953, 2331, 1663, 1273]);
  assert.throws(() => qrByteCapacity(41), RangeError);
  assert.throws(() => qrByteCapacity(0), RangeError);
});

test('small forced-mask QR matches frozen independently generated modules', () => {
  const qr = encodeQrModel2(ascii('HELLO WORLD'), { ecc: 'H', minVersion: 2, maxVersion: 2, mask: 2 });
  assert.equal(qr.version, 2);
  assert.equal(qr.ecc, 'H');
  assert.equal(qr.mask, 2);
  assert.equal(qr.matrix.width, 25);
  assert.equal(qr.matrix.quietZone, 4);
  assert.equal(qr.dataCapacityBytes, 14);
  assert.equal(qr.matrix.formatId, 'symbol/qr-model2');
  // Independent Python qrcode library v2/H/forced-mask-2 reference.
  assert.equal(digest(qr.matrix.toModules()),
    '3a901e49a0bec2eaedbdf5d08d27a794f0b329eda67843b5ca15a9f0a9f2a489');
  // Data are deterministic, and callers cannot mutate the symbol's backing bytes.
  const copy = qr.matrix.toModules();
  copy[0] ^= 1;
  assert.notEqual(qr.matrix.toModules()[0], copy[0]);
  assert.deepEqual(qr.matrix.toModules(), encodeQrModel2(ascii('HELLO WORLD'),
    { ecc: 'H', minVersion: 2, maxVersion: 2, mask: 2 }).matrix.toModules());
});

test('all standard QR versions and ECC levels are supported', () => {
  const versions = [1, 2, 3, 4, 5, 6, 7, 9, 10, 12, 20, 25, 32, 40];
  for (const v of versions) for (const ecc of ['L', 'M', 'Q', 'H']) {
    const n = Math.max(1, Math.min(qrByteCapacity(v, ecc), v * 5 + 4));
    const data = Uint8Array.from({ length: n }, (_, i) => (i * 53 + v * 13) & 255);
    const result = encodeQrModel2(data, { minVersion: v, maxVersion: v, ecc, mask: 0 });
    assert.equal(result.matrix.width, 17 + v * 4);
    assert.equal(result.matrix.height, 17 + v * 4);
    assert.ok(result.matrix.toModules().some(bit => bit === 0));
    assert.ok(result.matrix.toModules().some(bit => bit === 1));
  }
});

test('QR capacity, version, mask and input validation fail closed', () => {
  assert.throws(() => encodeQrModel2(Uint8Array.from({length:18}, () => 1), {ecc:'L',maxVersion:1}), /too large/i);
  assert.throws(() => encodeQrModel2(Uint8Array.of(0), {ecc:'T'}), RangeError);
  assert.throws(() => encodeQrModel2(Uint8Array.of(0), {mask:8}), RangeError);
  assert.throws(() => encodeQrModel2(Uint8Array.of(0), {minVersion:2,maxVersion:1}), RangeError);
  assert.throws(() => encodeQrModel2('not bytes'), TypeError);
  assert.throws(() => encodeQrModel2(new Uint8Array(2954)), TypeError);
});

test('one-byte changes alter the QR code, but are not a cryptographic identity proof', () => {
  const a = encodeQrModel2(ascii('SOURCE-1'), {ecc:'Q'});
  const b = encodeQrModel2(ascii('SOURCE-2'), {ecc:'Q'});
  assert.notEqual(digest(a.matrix.toModules()), digest(b.matrix.toModules()));
  assert.ok(a.matrix instanceof ModuleMatrix);
});
