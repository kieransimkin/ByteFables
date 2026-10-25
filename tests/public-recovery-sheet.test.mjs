import { test } from 'node:test';
import assert from 'node:assert/strict';
import { spawnSync, execFileSync } from 'node:child_process';
import { ByteValue, PublicRecord, createPublicRecoverySheet, createUrBytesQrTestDeck,
  decodeUrBytesMultipartTestOnly, decodePublicQrSession, executePublicFormat, planPublicFormats,
  ModuleMatrix, createFrameRudimentsRecoveryCardLayer } from '../dist/index.js';
const make = n => new PublicRecord(ByteValue.public(Uint8Array.from({length:n},(_,i)=>i),
  {namespace:'danceflow',kind:'node-id'}));

test('public QR print sheet is declarative, public-only, and recoverable', async () => {
  const record=make(240);
  const sheet=await createPublicRecoverySheet(record,{fragmentBytes:48,parity:true,pageBounds:[0,0,1024,1440]});
  assert.equal(sheet.transport,'BFQR1');
  assert.ok(sheet.frames.length>2);
  for(const page of sheet.frames){
    assert.equal(page.layer.renderer,'bytefables-public-card-v1');
    assert.equal(page.layer.style.format_id,'symbol/qr-model2');
    assert.equal(page.layer.style.quiet_zone,4);
    assert.equal(page.layer.style.fingerprint,sheet.canonicalFingerprint);
    assert.equal(page.layer.style.manual_text,page.text);
    assert.equal(page.excludedFromEffects,true);
  }
  assert.deepEqual((await decodePublicQrSession(sheet.frames.map(f=>f.text))).toBytes(),record.toBytes());
});

test('a public card rejects non-QR matrices, insufficient quiet zone and unsafe text', async () => {
  const matrix=new ModuleMatrix({formatId:'symbol/qr-model2',width:21,height:21,
    modules:new Uint8Array(441),quietZone:4});
  const config={id:'public-card',bounds:[0,0,1024,1440],caption:'Frame 1 of 2',
    fingerprint:'bfrec1-'+'a'.repeat(64),kind:'danceflow / node-id',manualText:'BFQR1:abc_012'};
  assert.equal(createFrameRudimentsRecoveryCardLayer(matrix,config).renderer,'bytefables-public-card-v1');
  assert.throws(()=>createFrameRudimentsRecoveryCardLayer(matrix,{...config,manualText:'<script/>'}),/invalid/i);
  assert.throws(()=>createFrameRudimentsRecoveryCardLayer(matrix,{...config,bounds:[0,0,128,128]}),/at least/i);
  assert.throws(()=>createFrameRudimentsRecoveryCardLayer(
    new ModuleMatrix({formatId:'symbol/qr-model2',width:21,height:21,modules:new Uint8Array(441),quietZone:1}),config),/quiet/i);
  assert.throws(()=>createFrameRudimentsRecoveryCardLayer(
    new ModuleMatrix({formatId:'symbol/arbitrary-matrix',width:21,height:21,modules:new Uint8Array(441)}),config),/QR/i);
  await assert.rejects(createPublicRecoverySheet(make(32),{layerPrefix:'bad/../prefix'}),/prefix/i);
});

test('UR test-only deck produces QR matrices and recovers from its text', async () => {
  const bytes=Uint8Array.from({length:256},(_,i)=>i);
  const deck=await createUrBytesQrTestDeck(bytes,{id:'urt',bounds:[0,0,512,512],
    fragmentBytes:32,extraMixedFrames:20,maxVersion:14});
  assert.ok(deck.frames.length>8);
  assert.equal(deck.schema,'bytefables.ur-bytes-qr-test.v1');
  assert.equal(deck.frames[0].layer.renderer,'bytefables-matrix-v1');
  assert.equal(deck.frames[0].layer.style.quiet_zone,4);
  assert.deepEqual(await decodeUrBytesMultipartTestOnly(deck.frames.map(f=>f.text)),bytes);
});

test('manifest includes UR test-only and requires explicit opt-in', async () => {
  const list=planPublicFormats({byteLength:128,goal:'recover-any',includeExperimental:true});
  const ur=list.find(x=>x.formatId==='codec/ur-bytes-multipart-test-only');
  assert.equal(ur.executable,true);
  const rec=make(128);
  await assert.rejects(executePublicFormat('codec/ur-bytes-multipart-test-only',rec),/opt-in/i);
  const artifact=await executePublicFormat('codec/ur-bytes-multipart-test-only',rec,{allowExperimental:true});
  assert.deepEqual(await decodeUrBytesMultipartTestOnly(JSON.parse(artifact.data).frames),rec.toBytes());
});

test('public-only CLI streams UR fixtures and emits print-sheet plan', () => {
  const bin=new URL('../bin/bytefables.mjs',import.meta.url).pathname;
  const input='00'.repeat(132);
  const ur=JSON.parse(execFileSync(process.execPath,[bin,'ur-test-encode','--confirm-public',
    '--public-hex',input,'--fragment-bytes','32','--mixed-frames','20'],{encoding:'utf8'}));
  assert.ok(ur.fragmentCount>1);
  const restored=spawnSync(process.execPath,[bin,'ur-test-recover','--confirm-public'],
    {input:JSON.stringify(ur.frames),encoding:'utf8'});
  assert.equal(restored.status,0,restored.stderr);
  assert.equal(JSON.parse(restored.stdout).bytesHex,input);
  const sheet=JSON.parse(execFileSync(process.execPath,[bin,'public-print-sheet','--confirm-public',
    '--public-hex','a5'.repeat(70),'--namespace','danceflow','--kind','node-id',
    '--fragment-bytes','42'],{encoding:'utf8'}));
  assert.ok(sheet.frames.length>=2);
  assert.equal(sheet.frames[0].layer.renderer,'bytefables-public-card-v1');
  assert.match(sheet.frames[0].text,/^BFQR1:/);
});
