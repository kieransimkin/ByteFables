import test from 'node:test';
import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import { ByteValue, makeVisualBitPlan, choosePromptBits, composeBaselinePrompt } from '../dist/index.js';
const wrap = (hex, namespace='danceflow') => ByteValue.public(Uint8Array.from(Buffer.from(hex, 'hex')),
  { namespace, kind: 'node-id' });
test('bit semantics are MSB-first; every public hash bit has a distinct feature identifier', async () => {
  const p = await makeVisualBitPlan(wrap('800001'));
  assert.equal(p.bitCount, 24);
  assert.deepEqual(p.choices.slice(0,9).map(x=>x.bit),[1,0,0,0,0,0,0,0,0]);
  assert.equal(p.choices[0].selected, 'spiky');
  assert.equal(p.choices[0].opposite, 'smooth');
  assert.equal(new Set(p.choices.map(x=>x.featureId)).size, 24);
});
test('every one-bit mutation flips only its own selected choice', async () => {
  const original = await makeVisualBitPlan(wrap('0000000000000000000000000000000000000000000000000000000000000000'));
  for (const i of [0,1,7,8,31,32,63,127,255]) {
    const b = new Uint8Array(32); b[Math.floor(i/8)] = 1 << (7-(i%8));
    const changed = await makeVisualBitPlan(ByteValue.public(b,{namespace:'danceflow',kind:'node-id'}));
    const a = original.choices.filter((x,j)=>x.bit !== changed.choices[j].bit);
    assert.deepEqual(a.map(x=>x.bitIndex),[i]);
    assert.notEqual(original.visualSeed,changed.visualSeed);
  }
  assert.equal(original.choices[32].scope,'motif 001');
  assert.equal(original.choices[255].scope,'motif 014');
});
test('a 512-bit input maps all bits; prompt budget is explicit', async () => {
  const p = await makeVisualBitPlan(wrap('55'.repeat(64)));
  assert.equal(p.bitCount,512);
  assert.equal(new Set(p.choices.map(x=>x.featureId)).size,512);
  assert.equal(choosePromptBits(p,16).length,16);
  assert.match(composeBaselinePrompt(p,8,'structured'),/FEATURES:/);
  assert.throws(()=>choosePromptBits(p,513));
});
test('private inputs are not accepted; planning never implies lossless image generation', async () => {
  const secret=ByteValue.secret(Uint8Array.of(1,2),{namespace:'wallet',kind:'private-key'});
  await assert.rejects(makeVisualBitPlan(secret));
  const cli=spawnSync(process.execPath,['bin/bytefables.mjs','visual-features','--public-hex','00','--namespace','danceflow','--kind','node-id'],{encoding:'utf8'});
  assert.equal(cli.status,1);
  assert.match(cli.stderr,/confirm-public/);
});

test('versioned feature contract matches immutable golden vector', async () => {
  const fs = await import('node:fs/promises');
  const reference=JSON.parse(await fs.readFile(new URL('./vectors/visual-bits-v1.json',import.meta.url),'utf8'));
  const p=await makeVisualBitPlan(wrap(reference.sourceHex));
  assert.equal(p.schema,reference.schema);
  assert.equal(p.identityDigestHex,reference.identityDigestHex);
  assert.equal(p.visualSeed,reference.visualSeed);
  assert.equal(p.visualSeed64,reference.visualSeed64);
  assert.equal(p.bitCount,reference.bitCount);
  assert.deepEqual(p.choices.map(x=>x.featureId),reference.choiceIds);
  assert.deepEqual(p.choices.map(x=>x.bit),reference.choiceBits);
  assert.deepEqual(p.choices.map(x=>x.selected),reference.selected);
  assert.equal(composeBaselinePrompt(p,8,'direct'),reference.baseline8);
});
