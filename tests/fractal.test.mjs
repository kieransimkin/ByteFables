import test from 'node:test';
import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import { readFile } from 'node:fs/promises';
import {
  ByteValue, PublicRecord, FRACTAL_FAMILIES, FRACTAL_BINARY_AXES,
  planPublicFractal, createFrameRudimentsFractalLayer, frameRudimentsEffectTarget,
  executePublicFormat, encodeHex
} from '../dist/index.js';

function publicRecord(bytes, kind='node-id') {
  return new PublicRecord(ByteValue.public(bytes, {namespace:'danceflow',kind}));
}
const place={id:'fractal',bounds:[0,0,128,128]};
const source=Uint8Array.from({length:32},(_,i)=>i);

test('all four seeded fractal families are registered, with eight named opposed axes', async () => {
  assert.deepEqual([...FRACTAL_FAMILIES], ['julia','burning-ship','ifs-fern','fbm']);
  assert.equal(FRACTAL_BINARY_AXES.length,8);
  const p=await planPublicFractal(publicRecord(source));
  assert.equal(p.schema, 'bytefables.fractal-seed.v1');
  assert.equal(p.featureBits,'00000000');
  assert.equal(p.seedHex.length,64);
  assert.equal(p.axes.length,8);
  assert.deepEqual(p.axes.map(a=>a.selected),FRACTAL_BINARY_AXES.map(a=>a[1]));
  assert.equal(p.identityOnly,true);
  assert.equal(p.effectiveRecoverableBits,null);
  assert.deepEqual(await planPublicFractal(publicRecord(source)),p);
  assert.throws(()=>{p.axes[0].selected='different';},TypeError);
});

test('full hash drives avalanche but first eight source bits retain opposing semantics', async () => {
  const raw=Uint8Array.from(source);
  const base=await planPublicFractal(publicRecord(raw));
  const bit0=Uint8Array.from(raw);bit0[0]^=0x80;
  const changed0=await planPublicFractal(publicRecord(bit0));
  assert.equal(changed0.featureBits,'10000000');
  assert.notEqual(changed0.seedHex,base.seedHex);
  const bit31=Uint8Array.from(raw);bit31[3]^=1;
  const changed31=await planPublicFractal(publicRecord(bit31));
  assert.equal(changed31.featureBits,base.featureBits);
  assert.notEqual(changed31.seedHex,base.seedHex);
  assert.notEqual((await planPublicFractal(publicRecord(raw,'other-kind'))).seedHex,base.seedHex);
});

test('FrameRudiments is the generator/effects owner, not an inline SVG art substitute', async () => {
  const r=publicRecord(source);
  for(const family of FRACTAL_FAMILIES){
    const layer=await createFrameRudimentsFractalLayer(r,{...place,family,palette:'pastel',quality:'standard'});
    assert.equal(layer.renderer,'bytefables-fractal-v1');
    assert.equal(layer.style.family,family);
    assert.equal(layer.style.quality,'standard');
    assert.equal(layer.style.feature_bits,'00000000');
    assert.deepEqual(layer.motion,{kind:'named',pattern:'circle'});
    assert.equal(frameRudimentsEffectTarget(layer),'layer:fractal');
    assert.equal(layer.style.seed_hex,(await planPublicFractal(r,family,'pastel')).seedHex);
    assert.throws(()=>{layer.style.seed_hex='corrupted';},TypeError);
  }
  for(const options of [{...place,family:'mysterious'},{...place,quality:'bogus'},{...place,palette:'red'}, {id:'large',bounds:[0,0,1024,1024]}]){
    await assert.rejects(()=>createFrameRudimentsFractalLayer(r,options));
  }
  await assert.rejects(()=>createFrameRudimentsFractalLayer(ByteValue.secret(Uint8Array.of(1),{namespace:'danceflow',kind:'key'}),place));
});

test('fractal manifest remains opt-in, descriptive and public only', async()=>{
  const record=publicRecord(source);
  await assert.rejects(()=>executePublicFormat('identity/fractal-seed-plan-v1',record),/opt-in/);
  const artifact=await executePublicFormat('identity/fractal-seed-plan-v1',record,{allowExperimental:true});
  assert.equal(artifact.mediaType,'application/json');
  const p=JSON.parse(artifact.data);
  assert.equal(p.seedHex,(await planPublicFractal(record)).seedHex);
  assert.equal(p.identityOnly,true);
});

test('TS and Python fractal bridge uses a frozen public-only vector and CLI exposes no secret route',async()=>{
  const v=JSON.parse(await readFile(new URL('./vectors/fractal-v1.json',import.meta.url)));
  const r=publicRecord(Uint8Array.from(Buffer.from(v.publicHex,'hex')));
  assert.equal(encodeHex(r.toBytes()),v.publicHex);
  const layer=await createFrameRudimentsFractalLayer(r,v.options);
  assert.deepEqual(layer,v.layer);
  const cmd=spawnSync(process.execPath,['bin/bytefables.mjs','fractal-layer',
    '--confirm-public','--public-hex',v.publicHex,'--namespace','danceflow','--kind','node-id',
    '--id','fractal','--bounds','0,0,128,128','--family','julia','--palette','neon','--quality','draft'],
    {encoding:'utf8',timeout:10000});
  assert.equal(cmd.status,0,cmd.stderr);
  assert.deepEqual(JSON.parse(cmd.stdout),v.layer);
  const bad=spawnSync(process.execPath,['bin/bytefables.mjs','fractal-layer','--public-hex','00',
    '--namespace','danceflow','--kind','node-id'],{encoding:'utf8',timeout:10000});
  assert.notEqual(bad.status,0);
});
