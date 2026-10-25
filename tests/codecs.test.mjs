import test from 'node:test';
import assert from 'node:assert/strict';
import { encodeHex, decodeHex, encodeBase32, decodeBase32 } from '../dist/index.js';

const utf8 = text => new TextEncoder().encode(text);
const ascii = bytes => new TextDecoder().decode(bytes);

test('hex is fully reversible, including null bytes, and emits canonical lowercase', () => {
  const bytes = Uint8Array.from({ length: 256 }, (_, i) => i);
  assert.equal(encodeHex(bytes).length, 512);
  assert.deepEqual(decodeHex(encodeHex(bytes)), bytes);
  assert.deepEqual(decodeHex('00FEFF'), Uint8Array.of(0, 254, 255));
  assert.deepEqual(decodeHex(''), new Uint8Array());
});

test('hex rejects odd nibbles, prefixes, whitespace and bad symbols', () => {
  for (const text of ['a', '0x11', 'ab cd', 'z0', 'ab\n', 'f́']) {
    assert.throws(() => decodeHex(text));
  }
});

test('RFC 4648 Base32 test vectors, unpadded uppercase', () => {
  const vectors = [
    ['', ''], ['f', 'MY'], ['fo', 'MZXQ'], ['foo', 'MZXW6'],
    ['foob', 'MZXW6YQ'], ['fooba', 'MZXW6YTB'], ['foobar', 'MZXW6YTBOI']
  ];
  for (const [source, encoded] of vectors) {
    assert.equal(encodeBase32(utf8(source)), encoded);
    assert.equal(ascii(decodeBase32(encoded)), source);
  }
});

test('Base32 exact roundtrips at all tail lengths', () => {
  for (let length = 0; length <= 512; length++) {
    const value = Uint8Array.from({ length }, (_, i) => (i * 197 + 41) & 255);
    assert.deepEqual(decodeBase32(encodeBase32(value)), value);
  }
});

test('Base32 rejects bad alphabet, padding, impossible lengths, nonzero residual bits', () => {
  for (const text of ['MZ', 'MZXR', 'MZXW7', 'mY', 'MY======', 'M', 'ABC', '0I1L']) {
    assert.throws(() => decodeBase32(text), text);
  }
});
