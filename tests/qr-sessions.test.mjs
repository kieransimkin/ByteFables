import { test } from 'node:test';
import assert from 'node:assert/strict';
import { execFileSync, spawnSync } from 'node:child_process';
import { ByteValue, PublicRecord, encodePublicQrSession, decodePublicQrSession,
  createPublicQrCard, executePublicFormat, planPublicFormats } from '../dist/index.js';

const record = n => new PublicRecord(ByteValue.public(Uint8Array.from({length:n}, (_,i)=> (i * 37 + 3) & 255),
  {namespace:'danceflow',kind:'node-id'}), {algorithm:'sha256',network:'test',endian:'na'});

test('BFQR1 preserves typed metadata and all payload bytes, with arbitrary frame order', async () => {
  for (const n of [0, 1, 16, 32, 64, 256, 512, 1024]) {
    const source = record(n);
    const s = await encodePublicQrSession(source, {fragmentBytes:64,maxVersion:12,ecc:'Q'});
    assert.equal(s.frames.length,s.dataFrames+s.parityFrames);
    const recovered = await decodePublicQrSession(s.frames.map(x=>x.text).reverse());
    assert.equal(recovered.namespace,'danceflow');
    assert.equal(recovered.algorithm,'sha256');
    assert.equal(recovered.network,'test');
    assert.deepEqual(recovered.toBytes(),source.toBytes());
  }
});

test('one missing frame is recovered with XOR parity; two missing are rejected', async () => {
  const source = record(256);
  const session = await encodePublicQrSession(source,{fragmentBytes:48, parity:true});
  assert.ok(session.dataFrames >= 4);
  for (const missing of [0,1,session.dataFrames-1]) {
    const rem = session.frames.filter(f=>f.index !== missing).map(f=>f.text);
    assert.deepEqual((await decodePublicQrSession(rem)).toBytes(),source.toBytes());
  }
  await assert.rejects(decodePublicQrSession(session.frames.filter(f=>f.index!==0&&f.index!==1).map(f=>f.text)),
    /incomplete/i);
  await assert.rejects(decodePublicQrSession(session.frames.filter(f=>!f.parity&&f.index!==0).map(f=>f.text)),
    /incomplete/i);
});

test('BFQR1 rejects mixed sessions, corruption, missing output or inconsistent duplication', async () => {
  const first=await encodePublicQrSession(record(192),{fragmentBytes:48});
  const second=await encodePublicQrSession(record(193),{fragmentBytes:48});
  await assert.rejects(decodePublicQrSession([first.frames[0].text, second.frames[1].text]),
    /different|incompatible/i);
  const tampered=first.frames[0].text.slice(0,-1)+'!';
  await assert.rejects(decodePublicQrSession([tampered]), /Base64|invalid|corrupted/i);
  await assert.rejects(decodePublicQrSession([]), /requires/i);
  await assert.rejects(decodePublicQrSession([first.frames[0].text]), /incomplete/i);
  const duplicate = [first.frames[0].text, ...first.frames.map(f=>f.text)];
  assert.deepEqual((await decodePublicQrSession(duplicate)).toBytes(),record(192).toBytes());
});

test('BFQR1 fragment/QR capacity limits and layer ID validation', async () => {
  await assert.rejects(encodePublicQrSession(record(64), {maxVersion:1}), /too small/i);
  await assert.rejects(encodePublicQrSession(record(64), {maxVersion:8,fragmentBytes:1000}), /fragment length/i);
  await assert.rejects(encodePublicQrSession(record(1), {ecc:'X'}), /level|version/i);
  await assert.rejects(createPublicQrCard(record(64), {layerIdPrefix:'bad/name'}), /prefix/i);
  const c=await createPublicQrCard(record(64), {fragmentBytes:40,bounds:[0,0,400,400]});
  assert.equal(c.frames[0].layer.renderer, 'bytefables-matrix-v1');
  assert.equal(c.frames[0].layer.style.quiet_zone, 4);
  assert.equal(c.frames[0].postEffectsTarget,`layer:${c.frames[0].layer.id}`);
  assert.equal(c.fullFingerprint.length, 'bfrec1-'.length+64);
});

test('registry describes BFQR1 honestly and rejects execution without experimental opt-in', async () => {
  const planned=planPublicFormats({byteLength:32,goal:'recover-typed',includeExperimental:true});
  assert.ok(planned.some(p=>p.formatId==='archive/public-qr-session-v1'&&p.executable));
  const source=record(32);
  await assert.rejects(executePublicFormat('archive/public-qr-session-v1',source), /opt-in/i);
  const result=await executePublicFormat('archive/public-qr-session-v1',source,{allowExperimental:true});
  const x=JSON.parse(result.data);
  assert.deepEqual((await decodePublicQrSession(x.frames)).toBytes(),source.toBytes());
});

test('CLI public QR export and restore over stdin, no wallet-related secrets', () => {
  const root=new URL('../bin/bytefables.mjs',import.meta.url).pathname;
  const encoded=JSON.parse(execFileSync(process.execPath,[root,'qr-public','--confirm-public',
    '--public-hex','00010203','--namespace','danceflow','--kind','node-id','--fragment-bytes','32'],{encoding:'utf8'}));
  assert.ok(encoded.frames.length>0);
  const parsed=spawnSync(process.execPath,[root,'qr-recover','--confirm-public'],{
    input:JSON.stringify(encoded.frames),encoding:'utf8'
  });
  assert.equal(parsed.status,0,parsed.stderr);
  assert.equal(JSON.parse(parsed.stdout).bytesHex,'00010203');
});
