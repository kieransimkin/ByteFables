import { test } from 'node:test';
import assert from 'node:assert/strict';
import { randomBytes } from 'node:crypto';
import {
  ByteValue, encodeHex, decodeBase45, encodeBase45,
  decodeBase64, encodeBase64, decodeCrockford32, encodeCrockford32,
  encodeBase58, decodeBase58, encodeBase58Check, decodeBase58Check, decodeBase58CheckForVersion,
  decodeBech32, encodeBech32, encodeBech32Bytes, decodeBech32Bytes,
  decodeSegwitAddress, encodeSegwitAddress,
  encodeBytewords, decodeBytewords, BYTEWORDS_WORDLIST,
  encodeBip39PublicEntropy, decodeBip39PublicMnemonic, BIP39_ENGLISH,
  encodeUrBytesTestOnly, decodeUrBytesTestOnly, encodeMultibase, decodeMultibase
} from '../dist/index.js';

const ascii = text => new TextEncoder().encode(text);
const hex = bytes => encodeHex(bytes);
const PUBLIC = entropy => ByteValue.public(entropy, { namespace: 'test', kind: 'public-entropy-fixture' });

test('RFC 9285 Base45 official examples and strict rejection', () => {
  assert.equal(encodeBase45(ascii('AB')), 'BB8');
  assert.equal(encodeBase45(ascii('Hello!!')), '%69 VD92EX0');
  assert.equal(hex(decodeBase45('BB8')), hex(ascii('AB')));
  assert.throws(() => decodeBase45(':::'), /Noncanonical/);
  assert.throws(() => decodeBase45('9'), /length/);
  assert.throws(() => decodeBase45('abc'), /character/);
});

test('RFC 4648 Base64 classic and URL-safe, canonical tail bits', () => {
  const vectors = [['', ''], ['f', 'Zg=='], ['fo', 'Zm8='], ['foo', 'Zm9v'],
    ['foob', 'Zm9vYg=='], ['fooba', 'Zm9vYmE='], ['foobar', 'Zm9vYmFy']];
  for (const [raw, expected] of vectors) {
    assert.equal(encodeBase64(ascii(raw)), expected);
    assert.equal(hex(decodeBase64(expected)), hex(ascii(raw)));
  }
  assert.equal(encodeBase64(Uint8Array.of(255, 254, 253), true), '__79');
  assert.equal(hex(decodeBase64('__79', true)), 'fffefd');
  for (const invalid of ['Zg', 'Zg===', 'Zh==', 'Zg==\n', 'Zm9v=', 'Zg==a']) {
    assert.throws(() => decodeBase64(invalid));
  }
  assert.throws(() => decodeBase64('Zh', true));
});

test('Crockford Base32 with aliases, check symbols and strict exact bytes', () => {
  const source = Uint8Array.of(0, 1, 2, 250, 255);
  const encoded = encodeCrockford32(source);
  assert.equal(hex(decodeCrockford32(encoded)), hex(source));
  const checked = encodeCrockford32(source, true);
  assert.equal(hex(decodeCrockford32(checked, true)), hex(source));
  assert.throws(() => decodeCrockford32(checked.slice(0, -1) + (checked.endsWith('Z') ? 'Y' : 'Z'), true), /mismatch/);
  assert.equal(hex(decodeCrockford32('O0', false)), '00');
  assert.equal(hex(decodeCrockford32('l0', false)), '08');
  assert.throws(() => decodeCrockford32('ZZ'), /padding/);
  assert.throws(() => decodeCrockford32('*0'));
});

test('Bitcoin Base58Check requires explicit version and rejects corruption', async () => {
  const bytes = Uint8Array.of(0, 0, 7, 8, 255);
  assert.equal(hex(decodeBase58(encodeBase58(bytes))), hex(bytes));
  assert.equal(encodeBase58(Uint8Array.of()), '');
  const version = Uint8Array.of(0);
  const data = new Uint8Array(20);
  const address = await encodeBase58Check(data, version);
  assert.equal(address, '1111111111111111111114oLvT2');
  const decoded = await decodeBase58Check(address, 1);
  assert.equal(hex(decoded.version), '00');
  assert.equal(hex(decoded.payload), '00'.repeat(20));
  assert.equal(hex(await decodeBase58CheckForVersion(address, Uint8Array.of(0))), '00'.repeat(20));
  await assert.rejects(() => decodeBase58CheckForVersion(address, Uint8Array.of(111)), /network/);
  await assert.rejects(decodeBase58Check(address.slice(0, -1) + '3', 1), /checksum/);
  await assert.rejects(() => encodeBase58Check(data, Uint8Array.of()), /version/);
  assert.throws(() => decodeBase58('0'), /character/);
});

test('BIP-173 and BIP-350 published Bech32/Bech32m examples and segregation', () => {
  assert.equal(decodeBech32('A12UEL5L').variant, 'bech32');
  assert.equal(decodeBech32('A1LQFN3A').variant, 'bech32m');
  assert.equal(encodeBech32('a', Uint8Array.of(), 'bech32'), 'a12uel5l');
  assert.equal(encodeBech32('a', Uint8Array.of(), 'bech32m'), 'a1lqfn3a');
  for (const invalid of ['A1lqfn3a', '1pzry9x0s0muk', 'x1b4n0q5v', 'a1lqfn3b']) {
    assert.throws(() => decodeBech32(invalid));
  }
  const bytes = Uint8Array.of(0, 1, 2, 255);
  const text = encodeBech32Bytes('bf', bytes, 'bech32m');
  const decoded = decodeBech32Bytes(text);
  assert.equal(decoded.hrp, 'bf');
  assert.equal(decoded.variant, 'bech32m');
  assert.equal(hex(decoded.bytes), hex(bytes));
  assert.throws(() => decodeBech32Bytes(encodeBech32('bf', Uint8Array.of(1), 'bech32m')));
  const w0 = encodeSegwitAddress('bc', 0, new Uint8Array(20));
  assert.equal(decodeSegwitAddress(w0).version, 0);
  const w1 = encodeSegwitAddress('tb', 1, new Uint8Array(32));
  assert.equal(decodeSegwitAddress(w1).version, 1);
  assert.throws(() => decodeSegwitAddress(encodeBech32('bc', Uint8Array.of(1, ...new Uint8Array(32)), 'bech32')));
  assert.throws(() => encodeSegwitAddress('bc', 0, Uint8Array.of(1, 2)));
});

test('Blockchain Commons BCR-2020-012 Bytewords exact reference vector', () => {
  assert.equal(BYTEWORDS_WORDLIST.length, 256);
  const raw = Buffer.from('d99d6ca20150c7098580125e2ab0981253468b2dbc5202c11947da', 'hex');
  const standard = 'tuna next jazz oboe acid good slot axis limp lava brag holy door puff monk brag guru frog luau drop roof grim also safe chef fuel twin solo aqua work bald';
  const minimal = 'tantjzoeadgdstaslplabghydrpfmkbggufgludprfgmaosecffltnsoaawkbd';
  assert.equal(encodeBytewords(raw), standard);
  assert.equal(encodeBytewords(raw, 'uri'), standard.replaceAll(' ', '-'));
  assert.equal(encodeBytewords(raw, 'minimal'), minimal);
  assert.equal(hex(decodeBytewords(standard)), hex(raw));
  assert.equal(hex(decodeBytewords(minimal, 'minimal')), hex(raw));
  assert.equal(hex(decodeBytewords(standard.replaceAll(' ', '-'), 'uri')), hex(raw));
  assert.throws(() => decodeBytewords(standard.replace('bald', 'barn')), /checksum/);
  assert.throws(() => decodeBytewords(standard.toUpperCase()), /Unknown/);
  assert.throws(() => decodeBytewords(minimal.slice(0, -2), 'minimal'), /checksum/);
});

test('BIP-39 official English wordlist and published mnemonic entropy fixtures', async () => {
  assert.equal(BIP39_ENGLISH.length, 2048);
  assert.equal(new Set(BIP39_ENGLISH).size, 2048);
  const cases = [
    ['00'.repeat(16), 'abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon about'],
    ['7f'.repeat(16), 'legal winner thank year wave sausage worth useful legal winner thank yellow'],
    ['ff'.repeat(16), 'zoo zoo zoo zoo zoo zoo zoo zoo zoo zoo zoo wrong'],
    ['00'.repeat(24), 'abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon agent'],
    ['00'.repeat(32), [...Array(23).fill('abandon'), 'art'].join(' ')],
    ['ff'.repeat(32), [...Array(23).fill('zoo'), 'vote'].join(' ')],
    ['77c2b00716cec7213839159e404db50d', 'jelly better achieve collect unaware mountain thought cargo oxygen act hood bridge']
  ];
  for (const [entropy, phrase] of cases) {
    assert.equal(await encodeBip39PublicEntropy(PUBLIC(Buffer.from(entropy, 'hex'))), phrase);
    assert.equal(hex(await decodeBip39PublicMnemonic(phrase)), entropy);
  }
  await assert.rejects(decodeBip39PublicMnemonic(cases[0][1].replace('about', 'above')), /checksum/);
  await assert.rejects(decodeBip39PublicMnemonic('other other'), /count/);
  await assert.rejects(decodeBip39PublicMnemonic(cases[0][1].replace('abandon', 'foobar')), /Unknown/);
  await assert.rejects(encodeBip39PublicEntropy(ByteValue.secret(new Uint8Array(16), { namespace: 'test', kind: 'entropy' })));
  await assert.rejects(encodeBip39PublicEntropy(PUBLIC(new Uint8Array(33))), /only encodes/);
});

test('random byte round trips and malformed canonical encodings', async () => {
  for (const len of [0, 1, 2, 3, 4, 16, 20, 24, 32, 33, 65, 256]) {
    for (let j = 0; j < 4; j++) {
      const data = new Uint8Array(randomBytes(len));
      for (const [encode, decode] of [[encodeBase45, decodeBase45],
        [bytes => encodeBase64(bytes), text => decodeBase64(text)],
        [bytes => encodeBase64(bytes, true), text => decodeBase64(text, true)],
        [bytes => encodeCrockford32(bytes, true), text => decodeCrockford32(text, true)],
        [bytes => encodeBytewords(bytes, 'minimal'), text => decodeBytewords(text, 'minimal')]]) {
        assert.equal(hex(decode(encode(data))), hex(data), `round trip ${len} bytes`);
      }
    }
  }
});

test('UR v2 test-only single part canonical CBOR and Bytewords', () => {
  const original = Uint8Array.of(0, 1, 2, 255);
  const encoded = encodeUrBytesTestOnly(original);
  assert.match(encoded, /^ur:bytes\/[a-z]+$/);
  assert.equal(hex(decodeUrBytesTestOnly(encoded)), hex(original));
  assert.equal(hex(decodeUrBytesTestOnly(encoded.toUpperCase())), hex(original));
  assert.throws(() => decodeUrBytesTestOnly(encoded.replace('/','/1-2/')));
  assert.throws(() => decodeUrBytesTestOnly(encoded.replace('bytes/', 'crypto-seed/')));
  assert.throws(() => decodeUrBytesTestOnly(encoded.slice(0, -2) + 'aa'));
  assert.throws(() => encodeUrBytesTestOnly(new Uint8Array(4097)));
});

test('Multibase b/f/z/m/u canonical tags and strict roundtrips', () => {
  const sample = new Uint8Array([0, 0, 1, 255]);
  for (const prefix of ['b', 'f', 'z', 'm', 'u']) {
    const encoded = encodeMultibase(sample, prefix);
    const decoded = decodeMultibase(encoded);
    assert.equal(decoded.prefix, prefix);
    assert.equal(hex(decoded.bytes), hex(sample));
  }
  assert.equal(encodeMultibase(Uint8Array.of(0x66, 0x6f, 0x6f), 'b'), 'bmzxw6');
  assert.throws(() => decodeMultibase('BMZXW6'));
  assert.throws(() => decodeMultibase('z0'));
  assert.throws(() => decodeMultibase('x00'));
});

test('BIP-350 independent SegWit address vectors, checksum and padding rejections', () => {
  const accepted = [
    ['BC1QW508D6QEJXTDG4Y5R3ZARVARY0C5XW7KV8F3T4', 0, '751e76e8199196d454941c45d1b3a323f1433bd6'],
    ['bc1p0xlxvlhemja6c4dqv22uapctqupfhlxm9h8z3k2e72q4k9hcz7vqzk5jj0', 1, '79be667ef9dcbbac55a06295ce870b07029bfcdb2dce28d959f2815b16f81798']
  ];
  for (const [text, version, program] of accepted) {
    const decoded = decodeSegwitAddress(text);
    assert.equal(decoded.version, version);
    assert.equal(hex(decoded.program), program);
    assert.equal(encodeSegwitAddress(decoded.hrp, version, decoded.program), text.toLowerCase());
  }
  const rejected = [
    'bc1p0xlxvlhemja6c4dqv22uapctqupfhlxm9h8z3k2e72q4k9hcz7vqh2y7hd',
    'bc1qw508d6qejxtdg4y5r3zarvary0c5xw7kemeawh',
    'bc1pw5dgrnzv',
    'bc1p0xlxvlhemja6c4dqv22uapctqupfhlxm9h8z3k2e72q4k9hcz7v07qwwzcrf',
    'tb1p0xlxvlhemja6c4dqv22uapctqupfhlxm9h8z3k2e72q4k9hcz7vpggkg4j'
  ];
  for (const text of rejected) assert.throws(() => decodeSegwitAddress(text), text);
});

test('BIP-39 round trip for all five allowed entropy lengths', async () => {
  for (const n of [16, 20, 24, 28, 32]) {
    for (let i = 0; i < 10; i++) {
      const data = new Uint8Array(randomBytes(n));
      const mnemonic = await encodeBip39PublicEntropy(PUBLIC(data));
      assert.equal(mnemonic.split(' ').length, 3 * n / 4);
      assert.equal(hex(await decodeBip39PublicMnemonic(mnemonic)), hex(data));
    }
  }
});
