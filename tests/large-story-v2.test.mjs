import test from 'node:test';
import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import { mkdtempSync, writeFileSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { ByteValue, encodeLargeStoryV1, encodeLargeStoryV2, decodeLargeStoryV2,
  LARGE_STORY_V2_SENTENCE_BITS, LARGE_STORY_V2_PAYLOAD_BITS } from '../dist/index.js';
const value = b => ByteValue.public(b, { namespace:'danceflow', kind:'node-id' });
test('v2 new format retains 66 mixed-radix bits, 8 selectors, and separate wire domain', async () => {
  assert.equal(LARGE_STORY_V2_PAYLOAD_BITS,66);
  assert.equal(LARGE_STORY_V2_SENTENCE_BITS,69);
  const x = value(Uint8Array.of(1,2,3));
  assert.match(await encodeLargeStoryV2(x),/^BYTEFABLES-LARGE-STORY-V2 en-GB\/2\n/);
  assert.notEqual(await encodeLargeStoryV1(x), await encodeLargeStoryV2(x));
});
test('v2 roundtrip both locales and many payload lengths, reproducibly', async () => {
  for (const locale of ['en-US','en-GB']) for (const count of [0,1,2,3,7,8,9,16,32,69,128]) {
    const data = Uint8Array.from({length:count},(_,i)=>(i*37+count)%256);
    const story = await encodeLargeStoryV2(value(data),locale);
    const decoded = await decodeLargeStoryV2(story);
    assert.deepEqual(decoded.bytes,data);
    assert.equal(decoded.locale,locale);
    assert.equal(await encodeLargeStoryV2(value(data),locale),story);
    await assert.rejects(()=>decodeLargeStoryV2(story+'\n'),/Invalid|Noncanonical|Malformed|Unknown/);
  }
});
test('eight templates actually selected, with written article agreement', async () => {
  const seen = new Set(); let articles=0;
  for(let j=0;j<320;j++) {
    const data=Uint8Array.of(j&255,(j*17)&255,(j*43)&255);
    const lines=(await encodeLargeStoryV2(value(data))).split('\n').slice(1);
    for(const line of lines){
      if(line.startsWith('Yesterday,'))seen.add('000');
      if(line.startsWith('At dawn,'))seen.add('001');
      if(line.startsWith('The '))seen.add('010');
      if(line.startsWith('At midnight,'))seen.add('011');
      if(line.startsWith('Long ago,'))seen.add('100');
      if(line.startsWith('After the storm,'))seen.add('101');
      if(line.startsWith('Suddenly,')){seen.add('110');articles++}
      if(line.startsWith('Once,')){seen.add('111');articles++}
    }
  }
  assert.equal(seen.size,8);
  assert.ok(articles>0);
});
test('tampering, locale switching, noncanonical article and truncation fail',async()=>{
 const text=await encodeLargeStoryV2(value(Uint8Array.of(0,1,2,3,4,5,6,7)));
 await assert.rejects(()=>decodeLargeStoryV2(text.replace('en-GB','en-US')));
 await assert.rejects(()=>decodeLargeStoryV2(text.replace(' the ',' a ')));
 await assert.rejects(()=>decodeLargeStoryV2(text.split('\n').slice(0,-1).join('\n')));
 await assert.rejects(()=>decodeLargeStoryV2(text.replace(/\b[a-z]{5}\b/, 'zzzzz')));
});
test('opt-in CLI v2 public roundtrip',()=>{
 const cmd = ['bin/bytefables.mjs','story-large-v2-encode','--confirm-public','--public-hex','001122','--namespace','danceflow','--kind','node-id','--raw'];
 const enc=spawnSync(process.execPath,cmd,{encoding:'utf8'});
 assert.equal(enc.status,0,enc.stderr);
 const folder=mkdtempSync(join(tmpdir(),'bf-large-v2-'));try{
 const file=join(folder,'story.txt');writeFileSync(file,enc.stdout);
 const out=spawnSync(process.execPath,['bin/bytefables.mjs','story-large-v2-decode','--confirm-public','--story-file',file],{encoding:'utf8'});
 assert.equal(out.status,0,out.stderr);assert.equal(JSON.parse(out.stdout).publicHex,'001122');
 }finally{rmSync(folder,{recursive:true,force:true})}
});
