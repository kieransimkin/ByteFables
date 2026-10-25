import test from 'node:test';
import assert from 'node:assert/strict';
import { ByteValue, DEFAULT_GRAMMAR_PACK as pack,
  compileGrammarPack, encodeSentence, decodeSentence,
  encodeExperimentalStory, decodeExperimentalStory, encodeHex } from '../dist/index.js';

const publicBytes = bytes => ByteValue.public(bytes, {
  namespace: 'test', kind: 'opaque'
});

function bits(n, width) {
  return Array.from({ length: width }, (_, i) => (n >>> (width - i - 1)) & 1);
}

test('demo grammar carries 13 bits: 1 selector and 12 lexical bits', () => {
  assert.equal(pack.selectorBits, 1);
  assert.equal(pack.payloadBits, 12);
  assert.equal(pack.sentenceBits, 13);
  assert.equal(pack.grammars.length, 2);
});

test('all 8192 grammar codewords round-trip with no ambiguity', () => {
  const sentences = new Set();
  for (let i = 0; i < 8192; i++) {
    const code = bits(i, 13);
    const sentence = encodeSentence(pack, code);
    assert.deepEqual(decodeSentence(pack, sentence), code);
    sentences.add(sentence);
  }
  assert.equal(sentences.size, 8192);
});

test('generated sentence is grammatical and can include the snail vocabulary', () => {
  // Template 0; adjective silly index 10, animal snail index 13, adverb sometimes index 3.
  const sentence = encodeSentence(pack, [0, ...bits(10, 4), ...bits(13, 4), ...bits(3, 4)]);
  assert.equal(sentence, 'The silly snail sometimes rests.');
  assert.deepEqual(decodeSentence(pack, sentence), [0, ...bits(10, 4), ...bits(13, 4), ...bits(3, 4)]);
});

test('compiler rejects duplicate entries, non-power-of-two dictionaries and markers', () => {
  const grammar = (words, marker = 'The') => ({ id: 'phrase', parts: [
    { type: 'literal', token: marker },
    { type: 'choice', role: 'animal', words }
  ] });
  assert.throws(() => compileGrammarPack({ id: 'demo', version: 1,
    grammars: [grammar(['snail', 'snail'])] }), /duplicate/);
  assert.throws(() => compileGrammarPack({ id: 'demo', version: 1,
    grammars: [grammar(['snail', 'otter', 'fox'])] }), /power-of-two/);
  assert.throws(() => compileGrammarPack({ id: 'demo', version: 1,
    grammars: [grammar(['snail', 'otter']), { ...grammar(['fox', 'cat']), id: 'different' }] }), /unique literal/);
  assert.throws(() => compileGrammarPack({ id: 'demo', version: 1,
    grammars: [grammar(['snail', 'otter']), { ...grammar(['fox', 'cat', 'bear', 'dog'], 'At'), id: 'different' }] }), /same number/);
});

test('decoder rejects sentence errors and noncanonical spelling', () => {
  const v = encodeSentence(pack, bits(110, 13));
  assert.throws(() => decodeSentence(pack, v.replace('The', 'A')));
  assert.throws(() => decodeSentence(pack, v.toLowerCase()));
  assert.throws(() => decodeSentence(pack, v.slice(0, -1)));
  assert.throws(() => decodeSentence(pack, `${v} extra`));
});

test('story roundtrips common key/hash sizes, arbitrary lengths and zero bytes', () => {
  for (const length of [0, 1, 2, 16, 20, 24, 28, 32, 33, 48, 64, 65, 78, 96, 256, 512, 4096]) {
    const bytes = Uint8Array.from({ length }, (_, i) => (i * 61 + length) & 255);
    const story = encodeExperimentalStory(publicBytes(bytes));
    assert.equal(encodeHex(decodeExperimentalStory(story)), encodeHex(bytes));
    assert.equal(encodeExperimentalStory(publicBytes(bytes)), story);
    assert.deepEqual(decodeExperimentalStory(story.replace(/\n/g, '\r\n')), bytes);
  }
});

test('story rejects corruption, truncation, extra sentences and secret inputs', () => {
  const source = Uint8Array.from({ length: 32 }, (_, i) => i);
  const story = encodeExperimentalStory(publicBytes(source));
  const lines = story.split('\n');
  assert.throws(() => decodeExperimentalStory(lines.slice(0, -1).join('\n')));
  assert.throws(() => decodeExperimentalStory(story + '\n' + lines.at(-1)));
  assert.throws(() => decodeExperimentalStory(story.replace('BYTEFABLES-STORY', 'OTHER-STORY')));
  const changed = [...lines];
  const target = changed.findIndex(line => line.startsWith('The '));
  const tokens = changed[target].split(' ');
  tokens[1] = tokens[1] === 'silly' ? 'brave' : 'silly';
  changed[target] = tokens.join(' ');
  assert.throws(() => decodeExperimentalStory(changed.join('\n')));
  const secret = ByteValue.secret(source, { namespace: 'wallet', kind: 'private-key' });
  assert.throws(() => encodeExperimentalStory(secret), /public/);
  assert.throws(() => encodeExperimentalStory(publicBytes(new Uint8Array(4097))), /too long/);
});

test('last-sentence unused bits must be zero', () => {
  const story = encodeExperimentalStory(publicBytes(Uint8Array.of(5)));
  const lines = story.split('\n');
  const last = decodeSentence(pack, lines.at(-1));
  last[last.length - 1] = 1; // 14-byte envelope is padded to 9 x 13 bits.
  lines[lines.length - 1] = encodeSentence(pack, last);
  assert.throws(() => decodeExperimentalStory(lines.join('\n')), /Noncanonical/);
});
