import test from 'node:test';
import assert from 'node:assert/strict';
import { encodeDeterministicCbor, decodeDeterministicCbor, encodeHex, decodeHex } from '../dist/index.js';

const fixtures = [
  [0, '00'], [23, '17'], [24, '1818'], [255, '18ff'],
  [256, '190100'], [65536, '1a00010000'],
  ['', '60'], ['IETF', '6449455446'],
  [Uint8Array.of(0, 1, 2), '43000102'],
  [[1, 2, 3], '83010203'],
  [new Map([[2, 'b'], [1, 'a']]), 'a2016161026162']
];

test('RFC 8949 deterministic CBOR preferred-form fixture bytes', () => {
  for (const [value, expected] of fixtures) {
    assert.equal(encodeHex(encodeDeterministicCbor(value)), expected);
    assert.equal(encodeHex(encodeDeterministicCbor(decodeDeterministicCbor(decodeHex(expected)))), expected);
  }
});

test('canonical CBOR subset rejects unsupported widths, types, and corrupted encodings', () => {
  for (const hex of [
    '', '1817', '1900ff', '1a0000ffff', '1b0000000000000001',
    '5f', '9f', 'bf', 'f6', 'f4', '20', 'c000', 'fa3f800000',
    '61ff', 'a200000001', 'a201010000', '8201', '0000',
    '5a00100001', '582000', '7f'
  ]) {
    assert.throws(() => decodeDeterministicCbor(decodeHex(hex)), `Expected ${hex} to be rejected`);
  }
  assert.throws(() => encodeDeterministicCbor(-1));
  assert.throws(() => encodeDeterministicCbor(2 ** 32));
  assert.throws(() => encodeDeterministicCbor('x'.repeat(1025)));
  assert.throws(() => encodeDeterministicCbor('\ud800'));
  assert.throws(() => encodeDeterministicCbor(new Map([[24, 1]])));
  assert.throws(() => encodeDeterministicCbor(Array(33).fill(0)));
  let deeplyNested = 0;
  for (let i = 0; i < 9; i++) deeplyNested = [deeplyNested];
  assert.throws(() => encodeDeterministicCbor(deeplyNested));
});

test('map serializer sorts keys, decoder rejects duplicates, preserves byte copies', () => {
  const original = new Map([[5, Uint8Array.of(1)], [0, 'ok']]);
  const encoded = encodeDeterministicCbor(original);
  assert.equal(encodeHex(encoded), 'a200626f6b054101');
  const decoded = decodeDeterministicCbor(encoded);
  decoded.get(5)[0] = 44;
  assert.equal(encoded[encoded.length - 1], 1);
});
