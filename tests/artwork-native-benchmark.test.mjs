import test from 'node:test';
import assert from 'node:assert/strict';
import { existsSync } from 'node:fs';
import { mkdtemp, readFile, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { parseArgs, validateOptions, prepareSuite } from '../scripts/prepare-artwork-benchmark.mjs';

test('benchmark validates deterministic public workload and selections', () => {
  const cfg = validateOptions();
  assert.equal(cfg.count, 32);
  assert.equal(cfg.families.length, 9);
  assert.deepEqual(cfg.sizes, [16,32,64,128]);
  for (const bad of [{count:0},{count:1001},{count:NaN},{count:1.5},{seed:'../bad'},
    {families:[]},{families:['sigil','sigil']},{palettes:['nope']},{sizes:[17]},
    {sizes:[16,16]},{columns:17},{complexity:9},{rowsPerPage:0},{count:1000}]) {
    assert.throws(() => validateOptions(bad));
  }
  assert.equal(validateOptions({count:1000,families:['sigil'],sizes:[32]}).count,1000);
});

test('CLI rejects ambiguous arguments rather than guessing', () => {
  assert.deepEqual(parseArgs(['--confirm-public','--output','out','--sizes','16,32']).options.sizes,[16,32]);
  for (const argv of [['--output'],['--bogus'],['--count','2','--count','3'],
    ['--output','--confirm-public']]) assert.throws(() => parseArgs(argv));
});

test('public opt-in precedes import or output writes', async () => {
  await assert.rejects(() => prepareSuite('unused',{},{}),/PUBLIC/);
});

test('real TS atlas plans are reproducible and hash-pinned',
  {skip: !existsSync(new URL('../dist/index.js',import.meta.url)) && 'npm run build required'}, async () => {
  const temp = await mkdtemp(join(tmpdir(),'bf-native-plans-'));
  try {
    const options = {count:3,families:['sigil','cellular'],sizes:[16,32],columns:2,rowsPerPage:1};
    const a = await prepareSuite(join(temp,'a'),options,{confirmPublic:true});
    const b = await prepareSuite(join(temp,'b'),options,{confirmPublic:true});
    assert.deepEqual(a,b); assert.equal(a.cases.length,4);
    for (const item of a.cases) {
      const p = JSON.parse(await readFile(join(temp,'a',item.plan),'utf8'));
      assert.equal(p.pages.length,2);
      assert.equal(p.inputCount,3);
      assert.match(item.planSha256,/^[a-f0-9]{64}$/);
      assert.deepEqual(await readFile(join(temp,'a',item.plan)),await readFile(join(temp,'b',item.plan)));
    }
    await assert.rejects(()=>prepareSuite(join(temp,'a'),options,{confirmPublic:true}),/exists/);
  } finally {await rm(temp,{recursive:true,force:true});}
});
