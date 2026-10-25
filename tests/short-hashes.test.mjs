import test from 'node:test';
import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { spawnSync } from 'node:child_process';
import { readFile } from 'node:fs/promises';
import {
  ByteValue, SHORT_HASH_LENGTHS, SHORT_HASH_SCHEME, truncateSha256Digest,
  deriveShortPublicHash, deriveShortPublicHashes, identityDigest,
  makeVisualBitPlan, executePublicFormat, PublicRecord
} from '../dist/index.js';

const sourceBytes = Uint8Array.from({length:32}, (_,i) => i);
const source = (bytes=sourceBytes, namespace='danceflow', kind='node-id') =>
  ByteValue.public(bytes, {namespace, kind});

const v = JSON.parse(await readFile(new URL('./vectors/short-public-hashes-v1.json', import.meta.url), 'utf8'));

test('independent SHA-256 framing vector, zero-byte preservation and 3/4/8 prefix hierarchy', async () => {
  const txt = new TextEncoder();
  const u32 = x => {const out = Buffer.alloc(4);out.writeUInt32BE(x);return out;};
  const ns = txt.encode(v.namespace), kind = txt.encode(v.kind), bytes = Buffer.from(v.sourceHex,'hex');
  const framed = Buffer.concat([txt.encode('ByteFables:public-identity:v1\0'),
    u32(ns.length),ns,u32(kind.length),kind,u32(bytes.length),bytes]);
  const expected = createHash('sha256').update(framed).digest('hex');
  assert.equal(expected, v.parentDigestHex, 'Golden vector must independently match canonical SHA-256');
  assert.equal(Buffer.from(await identityDigest(source())).toString('hex'), expected);
  assert.deepEqual(SHORT_HASH_LENGTHS, [3,4,8]);
  const results = await deriveShortPublicHashes(source());
  assert.equal(results.length,3);
  for (const hash of results) {
    assert.equal(hash.scheme,SHORT_HASH_SCHEME);
    assert.equal(hash.parentDigestHex,expected);
    assert.equal(hash.hex,v.output[String(hash.bytes)]);
    assert.equal(hash.hex,expected.slice(0,hash.bytes*2));
    assert.equal(hash.bits,hash.bytes*8);
    assert.equal(hash.label,`bf${hash.bits}-${hash.hex}`);
    assert.equal(hash.guarantee,'display-only');
    assert.deepEqual(hash, await deriveShortPublicHash(source(),hash.bytes));
  }
  assert.ok(results[1].hex.startsWith(results[0].hex));
  assert.ok(results[2].hex.startsWith(results[1].hex));
});

test('truncation operates on exact full digest and returns a defensive copy', () => {
  const full = Uint8Array.from({length:32},(_,i)=>i);
  const first = truncateSha256Digest(full,3);
  assert.deepEqual([...first], [0,1,2]);
  first[0] ^= 255;
  assert.equal(full[0],0);
  for (const badSize of [0,1,2,5,16,32,-1,3.5,NaN]) {
    assert.throws(()=>truncateSha256Digest(full,badSize),/3, 4 or 8/);
  }
  for(const wrong of [new Uint8Array(31),new Uint8Array(33),[],null]) {
    assert.throws(()=>truncateSha256Digest(wrong,3));
  }
  // Mathematical projection test: for all 2^16 possible 2-byte prefixes,
  // the leftmost byte appears EXACTLY 2^8 times. No modulus/rejection bias.
  const counts = new Uint32Array(256);
  for(let i=0;i<65536;i++) {
    full[0]=i>>>8;full[1]=i&255;
    counts[truncateSha256Digest(full,3)[0]]++;
  }
  assert.ok(counts.every(n=>n===256));
});

test('namespace, type, all source bytes affect SHA-256; public-only and strictly shorter output',async()=>{
  const base = await deriveShortPublicHash(source(),8);
  const flipped=sourceBytes.slice();flipped[31]^=1;
  const modified=await deriveShortPublicHash(source(flipped),8);
  assert.notEqual(base.parentDigestHex,modified.parentDigestHex);
  assert.notEqual(base.hex,modified.hex);
  for(const changed of [source(sourceBytes,'other-namespace'),source(sourceBytes,'danceflow','hash-id')]) {
    assert.notEqual(base.parentDigestHex,(await deriveShortPublicHash(changed,8)).parentDigestHex);
  }
  await assert.rejects(deriveShortPublicHash(ByteValue.secret(Uint8Array.of(1,2,3,4,5,6,7,8,9),
    {namespace:'wallet',kind:'private-key'}),3),/public/i);
  await assert.rejects(deriveShortPublicHash(source(new Uint8Array(3)),3),/strictly longer/i);
  await assert.rejects(deriveShortPublicHash(source(new Uint8Array(8)),8),/strictly longer/i);
  await assert.rejects(deriveShortPublicHashes(source(new Uint8Array(8))),/longer than 8/i);
});

test('3/4/8 byte values give exactly 24/32/64 source-feature choices and remain public',async()=>{
  for (const bytes of SHORT_HASH_LENGTHS) {
    const alias = await deriveShortPublicHash(source(),bytes);
    const renderedInput = source(Buffer.from(alias.hex,'hex'));
    const plan = await makeVisualBitPlan(renderedInput);
    assert.equal(plan.bitCount,bytes*8);
    assert.equal(plan.choices.length,bytes*8);
    assert.equal(new Set(plan.choices.map(c=>c.featureId)).size,bytes*8);
    const changed=renderedInput.toBytes();changed[bytes-1] ^= 1;
    const another = await makeVisualBitPlan(source(changed));
    assert.deepEqual(plan.choices.filter((c,i)=>c.bit !== another.choices[i].bit).map(c=>c.bitIndex),[bytes*8-1]);
  }
});

test('registry identity formats expose short prefixes without changing older 96-bit fingerprint',async()=>{
  const record = new PublicRecord(source());
  for(const bytes of SHORT_HASH_LENGTHS){
    const alias=await deriveShortPublicHash(source(),bytes);
    const fmt=await executePublicFormat(`identity/short-hash-${bytes*8}-v1`,record);
    assert.equal(fmt.data,alias.label);
    assert.equal(fmt.guarantee,'identity-only');
  }
  const old=await executePublicFormat('identity/fingerprint-sha256-v1',record);
  assert.match(old.data,/^bf1-[0-9a-f]{24}$/);
});

test('CLI supports shortening and rejects secret confirmations/invalid lengths',()=>{
  const common=['--public-hex',v.sourceHex,'--namespace','danceflow','--kind','node-id'];
  const invoke = (args) => spawnSync(process.execPath,['bin/bytefables.mjs',...args],{encoding:'utf8'});
  const out=invoke(['short-hashes','--confirm-public',...common]);
  assert.equal(out.status,0,out.stderr);
  const result=JSON.parse(out.stdout);
  assert.equal(result.hashes.length,3);
  assert.deepEqual(result.hashes.map(x=>x.hex),[v.output['3'],v.output['4'],v.output['8']]);
  for(const bytes of [3,4,8]){
    const t=invoke(['visual-features','--confirm-public',...common,'--derive-short-bytes',String(bytes),
      '--prompt-bits',String(bytes*8)]);
    assert.equal(t.status,0,t.stderr);
    const plan=JSON.parse(t.stdout);
    assert.equal(plan.bitCount,bytes*8);
    assert.equal(plan.shortDerivation.hex,v.output[String(bytes)]);
    assert.equal(plan.selectedFeatures.length,bytes*8);
  }
  const missing=invoke(['short-hashes',...common]);
  assert.equal(missing.status,1);
  assert.match(missing.stderr,/confirm-public/);
  const invalid=invoke(['visual-features','--confirm-public',...common,'--derive-short-bytes','5']);
  assert.equal(invalid.status,1);
});
