import test from 'node:test';
import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { ByteValue, encodeHex, encodeExperimentalStory, decodeExperimentalStory } from '../dist/index.js';
import { STORY_PACKS, STORY_THEMES } from '../dist/grammar/themes.js';
import { encodeStoryV2, decodeStoryV2, inspectStoryV2 } from '../dist/grammar/story-v2.js';
import { compileStoryPack, encodeStructuredSentence, decodeStructuredSentence } from '../dist/grammar/structured.js';
import { encodeRadixBits, decodeRadixBits, radixCapacityBits, bigintToBits } from '../dist/grammar/radix.js';
import { auditLexicon } from '../dist/grammar/audit.js';
import { makeVerbAgreementChoices } from '../dist/grammar/agreement.js';
import { scheduleSentenceCapacities } from '../dist/grammar/scheduler.js';

const pub = bytes => ByteValue.public(bytes, { namespace: 'test', kind: 'public-bytes' });
const seeded = (n, seed = 'ByteFables-fixture') => {
  const out = new Uint8Array(n);
  for (let i = 0; i < n; i += 32) {
    const h = createHash('sha256').update(seed).update(String(i)).digest();
    out.set(h.subarray(0, Math.min(32, n - i)), i);
  }
  return out;
};

test('all six theme packs have proven 33–35 bit capacities and complete prefix code', () => {
  assert.deepEqual(STORY_THEMES, ['nature', 'technology', 'music', 'fantasy', 'science', 'humour']);
  for (const theme of STORY_THEMES) {
    const p = STORY_PACKS[theme];
    assert.equal(p.version, 1);
    assert.deepEqual(p.templates.map(t => t.sentenceBits), [33, 34, 35, 35]);
    assert.deepEqual(p.templates.map(t => t.prefix), ['0', '10', '110', '111']);
    assert.ok(p.templates.every(t => t.payloadBits === 32 && t.radices.every(r => r === 256)));
    assert.equal(p.minSentenceBits, 33);
    assert.equal(p.maxSentenceBits, 35);
  }
});

test('single-sentence encoding is injective over representative 33–35 bit samples', () => {
  const used = new Set();
  for (const template of STORY_PACKS.nature.templates) {
    for (let i = 0; i < 2048; i++) {
      const bits = bigintToBits(BigInt(i) * 2000003n % (1n << 32n), 32);
      const sentence = encodeStructuredSentence(template, bits);
      assert.deepEqual(decodeStructuredSentence(STORY_PACKS.nature, sentence),
        [...template.prefix.split('').map(Number), ...bits]);
      assert.ok(!used.has(sentence));
      used.add(sentence);
    }
  }
  assert.equal(used.size, 8192);
});

test('story v2 exact round trips for all primary public key/hash sizes and leading zeroes', async () => {
  for (const theme of STORY_THEMES) {
    for (const n of [0, 1, 2, 4, 16, 20, 24, 28, 32, 33, 48, 64, 65, 78, 96, 128, 255, 512, 4096]) {
      const bytes = seeded(n, theme);
      if (n) bytes[0] = 0;
      if (n > 1) bytes[1] = 0;
      const original = pub(bytes);
      const text = await encodeStoryV2(original, theme);
      const restored = await decodeStoryV2(text);
      assert.equal(restored.theme, theme);
      assert.equal(restored.version, 2);
      assert.equal(restored.checksum, 'sha256-128-unkeyed');
      assert.equal(encodeHex(restored.bytes), encodeHex(bytes));
      assert.equal(await encodeStoryV2(original, theme), text);
      assert.equal(encodeHex((await decodeStoryV2(text.replace(/\n/g, '\r\n'))).bytes), encodeHex(bytes));
      const stats = await inspectStoryV2(original, theme);
      assert.equal(stats.framedBits, (n + 26) * 8);
      assert.equal(stats.inputBits, n * 8);
      assert.ok(stats.sentenceCapacities.reduce((a, b) => a + b, 0) >= stats.framedBits);
      assert.ok(stats.sentenceCapacities.reduce((a, b) => a + b, 0) - stats.framedBits < 35);
    }
  }
});

test('v1 legacy story remains unchanged when v2 is added', async () => {
  const original = pub(Uint8Array.from([0, 1, 2, 255]));
  const old = encodeExperimentalStory(original);
  assert.match(old, /^BYTEFABLES-STORY-PROTOTYPE-1\n/);
  assert.deepEqual(decodeExperimentalStory(old), original.toBytes());
  const newer = await encodeStoryV2(original);
  assert.match(newer, /^BYTEFABLES-STORY-V2 nature\/1\n/);
  await assert.rejects(() => decodeStoryV2(old));
  assert.throws(() => decodeExperimentalStory(newer));
});

test('strict v2 parsing fails closed on tampering, noncanonical and unsupported input', async () => {
  const text = await encodeStoryV2(pub(seeded(32)));
  const lines = text.split('\n');
  await assert.rejects(() => decodeStoryV2(text + '\n' + lines.at(-1)));
  await assert.rejects(() => decodeStoryV2(lines.slice(0, -1).join('\n')));
  await assert.rejects(() => decodeStoryV2(text.replace('nature/1', 'music/1')));
  await assert.rejects(() => decodeStoryV2(text.replace('STORY-V2', 'STORY-V3'))); // no-op if absent; handled below
});

test('v2 rejects changes to valid lexical slots, sentence order and punctuation', async () => {
  const text = await encodeStoryV2(pub(seeded(32)));
  const lines = text.split('\n');
  const changed = [...lines];
  changed[1] = changed[1].replace(/amber|azure|bronze|coral|crimson|golden|indigo|ivory|jade|lilac|mint|pearl|rose|silver|teal|violet/,
    x => x === 'amber' ? 'azure' : 'amber');
  await assert.rejects(() => decodeStoryV2(changed.join('\n')));
  const swapped = [...lines];
  [swapped[2], swapped[3]] = [swapped[3], swapped[2]];
  await assert.rejects(() => decodeStoryV2(swapped.join('\n')));
  await assert.rejects(() => decodeStoryV2(text.replaceAll('.', '!')));
  await assert.rejects(() => decodeStoryV2(text + '\n'));
  await assert.rejects(() => decodeStoryV2(text.toLowerCase()));
  await assert.rejects(() => decodeStoryV2('\ufeff' + text));
  await assert.rejects(() => decodeStoryV2('not-a-story'));
  await assert.rejects(() => decodeStoryV2(text + 'a'.repeat(440001)));
});

test('v2 refuses nonzero last-sentence padding even if the changed sentence parses', async () => {
  const text = await encodeStoryV2(pub(Uint8Array.of(7)));
  const lines = text.split('\n');
  const last = lines.at(-1);
  const pack = STORY_PACKS.nature;
  const template = pack.templates.find(t => last.startsWith(t.marker));
  const bits = decodeStructuredSentence(pack, last);
  bits[bits.length - 1] = 1;
  lines[lines.length - 1] = encodeStructuredSentence(template, bits.slice(template.prefix.length));
  await assert.rejects(() => decodeStoryV2(lines.join('\n')), /padded|padding|canonical|checksum/);
});

test('v2 refuses typed secret objects, invalid public size and unknown theme', async () => {
  const secret = ByteValue.secret(Uint8Array.of(3), { namespace: 'test', kind: 'private-key' });
  await assert.rejects(() => encodeStoryV2(secret), /public/);
  await assert.rejects(() => encodeStoryV2(pub(new Uint8Array(4097))), /limited/);
  await assert.rejects(() => encodeStoryV2(pub(Uint8Array.of(1)), 'unsafe'));
});

const miniSpec = () => {
  const byWord = makeVerbAgreementChoices(
    [{ word: 'snail', number: 'singular' }, { word: 'geese', number: 'plural' }],
    [{ singular: 'crawls', plural: 'crawl' },
      { singular: 'glides', plural: 'glide' },
      { singular: 'wanders', plural: 'wander' }]);
  const grammar = (id, prefix, marker) => ({ id, prefix, parts: [
    { type: 'literal', text: marker },
    { type: 'choice', role: 'subject', words: ['snail', 'geese'] },
    { type: 'literal', text: ' ' },
    { type: 'dependent', role: 'verb', dependsOn: 'subject', byWord },
    { type: 'literal', text: ' near ' },
    { type: 'choice', role: 'place', words: ['moon', 'sun', 'tree', 'rain', 'wind'] },
    { type: 'literal', text: '.' }
  ] });
  return { id: 'mini', version: 1, templates: [
    grammar('first', '0', 'The '), grammar('second', '1', 'Look, the ')
  ] };
};

test('conditional agreement and irregular enumerative coding are reversible', () => {
  const pack = compileStoryPack(miniSpec());
  assert.equal(pack.minSentenceBits, 5); // floor(log2(2 * 3 * 5)) + selector bit
  const seen = new Set();
  for (let i = 0; i < 32; i++) {
    const prefix = i >= 16 ? 1 : 0;
    const template = pack.templates[prefix];
    const bits = bigintToBits(BigInt(i % 16), 4);
    const text = encodeStructuredSentence(template, bits);
    assert.deepEqual(decodeStructuredSentence(pack, text), [prefix, ...bits]);
    assert.ok(!seen.has(text));
    seen.add(text);
  }
  assert.equal(seen.size, 32);
  assert.throws(() => decodeStructuredSentence(pack, 'The geese crawls near moon.'), /Unknown word/);
  assert.throws(() => decodeRadixBits([1, 2, 4], [2, 3, 5]), /outside bit capacity/);
  assert.equal(radixCapacityBits([2, 3, 5]), 4);
  assert.deepEqual(decodeRadixBits(encodeRadixBits([1, 0, 1, 0], [2, 3, 5]), [2, 3, 5]), [1, 0, 1, 0]);
});

test('advanced compiler rejects ambiguous/malformed packs and conditional cardinality failures', () => {
  const clone = () => structuredClone(miniSpec());
  const bad = clone(); bad.templates[1].prefix = '00';
  assert.throws(() => compileStoryPack(bad), /prefix-free/);
  const incomplete = clone(); incomplete.templates[1].prefix = '10';
  assert.throws(() => compileStoryPack(incomplete), /complete/);
  const marker = clone(); marker.templates[1].parts[0].text = 'The ';
  assert.throws(() => compileStoryPack(marker), /marker/);
  const duplicate = clone(); duplicate.templates[0].parts[3].byWord.snail = ['crawls', 'crawls', 'sings'];
  assert.throws(() => compileStoryPack(duplicate), /duplicate/);
  const uneven = clone(); uneven.templates[0].parts[3].byWord.geese = ['crawl', 'glide'];
  assert.throws(() => compileStoryPack(uneven), /equal capacities/);
  const missing = clone(); delete missing.templates[0].parts[3].byWord.geese;
  assert.throws(() => compileStoryPack(missing), /Dependent/);
  const locale = clone(); locale.templates[0].parts[1].words = ['snail', 'escargôt'];
  assert.throws(() => compileStoryPack(locale), /Invalid or duplicate/);
  const adjacent = clone(); adjacent.templates[0].parts.splice(2, 1);
  assert.throws(() => compileStoryPack(adjacent), /adjacent/);
  const hidden = clone(); hidden.templates[0].parts[3].role = 'subject';
  assert.throws(() => compileStoryPack(hidden), /Duplicate/);
});

test('compiled packs defensively snapshot original codebook data', () => {
  const s = miniSpec();
  const pack = compileStoryPack(s);
  const first = encodeStructuredSentence(pack.templates[0], [0, 0, 0, 0]);
  s.templates[0].parts[1].words[0] = 'cow';
  assert.ok(Object.isFrozen(s.templates[0].parts[3].byWord.snail));
  assert.throws(() => { pack.templates[0].parts[1].words[0] = 'cow'; }, /read only/);
  assert.equal(encodeStructuredSentence(pack.templates[0], [0, 0, 0, 0]), first);
});

test('lexicon audit flags obvious homophones and edit distance without overstating coverage', () => {
  const r = auditLexicon(['night', 'knight', 'fox', 'fog', 'fox']);
  assert.equal(r.duplicateCount, 1);
  assert.ok(r.homophoneWarnings.some(x => x.includes('night / knight')));
  assert.ok(r.confusablePairs.some(x => x.includes('fox / fog')));
  assert.throws(() => auditLexicon(new Array(257).fill('a')));
});

test('bounded DP scheduler chooses a deterministic capacity/word-cost plan', () => {
  const modes = [{ id: 'short', bits: 24, cost: 10 }, { id: 'long', bits: 40, cost: 13 }];
  assert.deepEqual(scheduleSentenceCapacities(0, modes), []);
  const schedule = scheduleSentenceCapacities(88, modes);
  assert.equal(schedule.reduce((n, x) => n + x.usedBits, 0), 88);
  assert.equal(schedule.reduce((n, x) => n + x.paddingBits, 0), 0);
  assert.deepEqual(scheduleSentenceCapacities(88, modes), schedule);
  assert.ok(schedule.some(x => x.capacityBits === 40));
  assert.throws(() => scheduleSentenceCapacities(50_001, modes));
  assert.throws(() => scheduleSentenceCapacities(32, [{ id: 'broken', bits: 0, cost: 3 }]));
});
