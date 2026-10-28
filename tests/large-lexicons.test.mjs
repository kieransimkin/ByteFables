import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { createHash } from 'node:crypto';
import { execFileSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { resolve } from 'node:path';
import { ByteValue } from '../dist/index.js';
import { LARGE_LEXICON_COUNTS_V1, largeLexiconWordsV1, largeLexiconWordV1,
  largeLexiconIndexV1, convertLexiconWordV1 } from '../dist/grammar/large-lexicons-v1.js';
import { encodeLargeStoryV1, decodeLargeStoryV1, LARGE_STORY_PAYLOAD_BITS,
  LARGE_STORY_SENTENCE_BITS, LARGE_STORY_MAX_PUBLIC_BYTES } from '../dist/grammar/large-story-v1.js';

const root = resolve(fileURLToPath(new URL('..', import.meta.url)));
const src = resolve(root, 'src/grammar/wordlists/large-v1');
// Historical published input hashes are pinned by scripts/generate-lexicons-v1.mjs.
const rawHash = path => createHash('sha256').update(readFileSync(path)).digest('hex');
const pub = n => ByteValue.public(n, { namespace: 'test', kind: 'public-byte-sequence' });
const source = (n, label) => {
  const result = new Uint8Array(n);
  for (let i = 0; i < n; i += 32) {
    const d = createHash('sha256').update(label).update(String(i)).digest();
    result.set(d.subarray(0, Math.min(32, n - i)), i);
  }
  return result;
};

test('six pinned wordlists and generated cross-runtime lookup module are unchanged', () => {
  execFileSync(process.execPath, [resolve(root, 'scripts/generate-lexicons-v1.mjs'), '--check'], { cwd: root });
  for (const [role, count] of Object.entries(LARGE_LEXICON_COUNTS_V1)) {
    for (const locale of ['en-US','en-GB']) {
      const written = readFileSync(resolve(src, `${role}.${locale.toLowerCase()}.txt`),'utf8').trimEnd().split('\n');
      const compiled = largeLexiconWordsV1(role, locale);
      assert.equal(written.length, count);
      assert.deepEqual(compiled, written);
      assert.equal(new Set(compiled).size, count);
      assert.equal(rawHash(resolve(src, `${role}.${locale.toLowerCase()}.txt`)).length, 64);
      assert.ok(Object.isFrozen(compiled));
      for (const idx of [0, 1, Math.floor(count/2), count - 1]) {
        assert.equal(largeLexiconIndexV1(role, locale, largeLexiconWordV1(role,locale,idx)),idx);
      }
    }
  }
});

test('all regional spellings share immutable conceptual indices', () => {
  for (const role of ['nouns','adjectives','verbs']) {
    const us = largeLexiconWordsV1(role,'en-US');
    const gb = largeLexiconWordsV1(role,'en-GB');
    assert.equal(us.length,gb.length);
    let n = 0;
    for (let i=0;i<us.length;i++) {
      if(us[i]!==gb[i]) n++;
      assert.equal(convertLexiconWordV1(role,'en-US','en-GB',us[i]),gb[i]);
      assert.equal(convertLexiconWordV1(role,'en-GB','en-US',gb[i]),us[i]);
    }
    assert.equal(n,{nouns:179,adjectives:177,verbs:265}[role]);
  }
  assert.equal(convertLexiconWordV1('nouns','en-US','en-GB','color'),'colour');
  assert.equal(convertLexiconWordV1('verbs','en-US','en-GB','organized'),'organised');
  assert.throws(()=>largeLexiconIndexV1('nouns','en-GB','color'));
  assert.throws(()=>largeLexiconIndexV1('verbs','en-US','Organized'));
  assert.throws(()=>largeLexiconWordV1('adjectives','en-GB',99999));
});

test('real mixed-radix capacity is 66 payload bits plus two template-selector bits', () => {
  assert.equal(LARGE_STORY_PAYLOAD_BITS,66);
  assert.equal(LARGE_STORY_SENTENCE_BITS,68);
  assert.equal(LARGE_STORY_MAX_PUBLIC_BYTES,4096);
});

test('experimental US and UK v1 sentences recover arbitrary PUBLIC bytes, including padding', async () => {
  for (const locale of ['en-US','en-GB']) {
    for (const n of [0,1,2,3,16,20,24,32,33,64,96,128,512,4096]) {
      const original=source(n,locale);
      const encoded=await encodeLargeStoryV1(pub(original),locale);
      const decoded=await decodeLargeStoryV1(encoded);
      assert.equal(decoded.locale,locale);
      assert.deepEqual(decoded.bytes,original);
      assert.equal(encoded,(await encodeLargeStoryV1(pub(original),locale)));
    }
  }
});

test('locale header, wording, lexical mutations, size and trailing text cannot be silently accepted', async () => {
  const text=await encodeLargeStoryV1(pub(source(48,'mutations')),'en-GB');
  const [heading,...lines]=text.split('\n');
  await assert.rejects(decodeLargeStoryV1(text.replace('en-GB','en-US')));
  await assert.rejects(decodeLargeStoryV1(`${text}\n${lines[0]}`));
  await assert.rejects(decodeLargeStoryV1(`${text}\n`));
  await assert.rejects(decodeLargeStoryV1(text.replace('the ','the  ')));
  await assert.rejects(decodeLargeStoryV1(`${heading}\n${lines.slice(0,-1).join('\n')}`));
  await assert.rejects(decodeLargeStoryV1(text.replace('Yesterday,','tomorrow,')));
  await assert.rejects(decodeLargeStoryV1(text.replace(/([a-z]{4,})/,'changed')));
  await assert.rejects(decodeLargeStoryV1('BYTEFABLES-STORY-V2 nature/1\n' + lines.join('\n')));
  await assert.rejects(decodeLargeStoryV1(text.toUpperCase()));
  assert.deepEqual((await decodeLargeStoryV1(text.replace(/\n/g,'\r\n'))).bytes,source(48,'mutations'));
});

test('sensitivity checks reject private values and oversize input', async () => {
  await assert.rejects(encodeLargeStoryV1(ByteValue.secret(Uint8Array.of(1), { namespace: 'secret', kind:'key' })));
  await assert.rejects(encodeLargeStoryV1(pub(source(4097,'oversize'))));
  await assert.rejects(encodeLargeStoryV1(pub(new Uint8Array(1)), 'fr-FR'));
});

test('standard registry plans and executes only opt-in experimental public large stories', async () => {
  const { PublicRecord, executePublicFormat, decodePublicTextFormat, planPublicFormats } = await import('../dist/index.js');
  const value=pub(source(16,'registry-large'));
  const record=new PublicRecord(value);
  assert.ok(planPublicFormats({byteLength:16,goal:'recover-any',includeExperimental:true})
    .some(row=>row.formatId==='codec/large-story-v1' && row.executable));
  await assert.rejects(executePublicFormat('codec/large-story-v1',record));
  const output=await executePublicFormat('codec/large-story-v1',record,{allowExperimental:true});
  assert.equal(output.guarantee,'reversible-raw');
  await assert.rejects(decodePublicTextFormat('codec/large-story-v1',output.data));
  assert.deepEqual(await decodePublicTextFormat('codec/large-story-v1',output.data,{allowExperimental:true}),value.toBytes());
});

test('large-story preview hands only tagged text layers to FrameRudiments', async () => {
  const { createFrameRudimentsLargeStoryPreview } = await import('../dist/index.js');
  const item = await createFrameRudimentsLargeStoryPreview(pub(source(48,'host-bridge')),
    'en-GB', { box:[0,0,640,180], maxSentences:2, fontSize:19 });
  assert.equal(item.target,'framerudiments.project.v1/identity');
  assert.equal(item.previewOnly,true);
  assert.equal(item.sourceFormat,'BYTEFABLES-LARGE-STORY-V1');
  assert.equal(item.identities.length,2);
  assert.ok(item.omittedSentences>0);
  assert.deepEqual(item.effectTargets,['identity:0','identity:1']);
  await assert.rejects(createFrameRudimentsLargeStoryPreview(pub(source(4,'bad-box')),
    'en-US',{box:[10,5,10,90]}));
  await assert.rejects(createFrameRudimentsLargeStoryPreview(ByteValue.secret(Uint8Array.of(1),
    {namespace:'test',kind:'private'}),'en-GB',{box:[0,0,640,180]}));
});
