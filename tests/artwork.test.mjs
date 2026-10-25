import test from 'node:test';
import assert from 'node:assert/strict';
import { execFileSync } from 'node:child_process';
import { ByteValue, PublicRecord, createFrameRudimentsArtworkLayer,
  executePublicFormat, getFormatManifest } from '../dist/index.js';

const source = new PublicRecord(ByteValue.public(Uint8Array.of(0,1,2,3,4),
  {namespace:'danceflow',kind:'node-id'}));

test('all nine experimental artwork families are deterministic FrameRudiments layers', async () => {
  const seen=new Set();
  for (const artwork of ['sigil','constellation','heraldry','topography','crystal','mandala','cellular','branching','orbital']) {
    const opts={id:'identity-art',bounds:[0,0,128,128],artwork,palette:'neon',complexity:4};
    const x=await createFrameRudimentsArtworkLayer(source,opts);
    const y=await createFrameRudimentsArtworkLayer(source,opts);
    assert.deepEqual(x,y);
    assert.equal(x.renderer,'bytefables-artwork-v1');
    assert.equal(x.style.digest_hex.length,64);
    assert.equal(x.style.style,artwork);
    assert.equal(x.type,'rudiment');
    seen.add(JSON.stringify(x.style));
  }
  assert.equal(seen.size,9);
});

test('artwork colours and complexity are presentation choices, not new identity keys', async () => {
  const a=await createFrameRudimentsArtworkLayer(source,{id:'m1',bounds:[0,0,64,64],artwork:'sigil',palette:'pastel'});
  const b=await createFrameRudimentsArtworkLayer(source,{id:'m2',bounds:[0,0,256,256],artwork:'heraldry',palette:'mono',complexity:8});
  assert.equal(a.style.digest_hex,b.style.digest_hex);
  const changed=new PublicRecord(ByteValue.public(Uint8Array.of(0,1,2,3,5),{namespace:'danceflow',kind:'node-id'}));
  assert.notEqual(a.style.digest_hex,(await createFrameRudimentsArtworkLayer(changed,{id:'m1',bounds:[0,0,64,64]})).style.digest_hex);
});

test('untrusted options and secret objects cannot invoke artwork renderer', async () => {
  await assert.rejects(createFrameRudimentsArtworkLayer(source,{id:'art',bounds:[0,0,100,100],artwork:'unknown'}), /Invalid/i);
  await assert.rejects(createFrameRudimentsArtworkLayer(source,{id:'art',bounds:[0,0,100,100],complexity:0}), /Invalid/i);
  await assert.rejects(createFrameRudimentsArtworkLayer(source,{id:'art',bounds:[0,0,100,100],palette:'banana'}), /Invalid/i);
  await assert.rejects(createFrameRudimentsArtworkLayer(source.value,{id:'art',bounds:[0,0,100,100]}), /PublicRecord/i);
});

test('artwork capabilities and public CLI are actually bound', async () => {
  const cap=getFormatManifest('identity/framerudiments-artwork-v1');
  assert.equal(cap.guarantee,'identity-only');
  assert.equal(cap.maturity,'experimental');
  const layer=JSON.parse((await executePublicFormat(cap.formatId,source,{allowExperimental:true})).data);
  assert.equal(layer.renderer,'bytefables-artwork-v1');
  const output=JSON.parse(execFileSync(process.execPath,[new URL('../bin/bytefables.mjs',import.meta.url).pathname,
    'artwork-layer','--confirm-public','--public-hex','00010203',
    '--namespace','danceflow','--kind','node-id','--artwork','constellation'],{encoding:'utf8'}));
  assert.equal(output.layer.style.style,'constellation');
});
