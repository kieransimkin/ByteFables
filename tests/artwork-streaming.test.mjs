import assert from 'node:assert/strict';
import crypto from 'node:crypto';
import fs from 'node:fs';
import test from 'node:test';
import vm from 'node:vm';

const source=fs.readFileSync(new URL('../integrations/web/artwork-streaming/runtime.js',import.meta.url),'utf8');
vm.runInThisContext(source,{filename:'artwork-streaming/runtime.js'});
const {ResidencyCache,openKtx2}=globalThis.ByteFablesStreaming;
const sleep=ms=>new Promise(r=>setTimeout(r,ms));

test('LRU evicts only unpinned entries and records hits',async()=>{
  const disposed=[];const cache=new ResidencyCache(async key=>({key,byteLength:6}),{budgetBytes:12,disposer:v=>disposed.push(v.key)});
  const a=await cache.acquire('a');a.release();const b=await cache.acquire('b');b.release();
  const a2=await cache.acquire('a');a2.release(); // a becomes newest
  const c=await cache.acquire('c');c.release();
  const s=cache.stats();assert.equal(s.residentBanks,2);assert.equal(s.evictions,1);assert.deepEqual(disposed,['b']);assert.equal(s.hits,1);
  cache.dispose();assert.equal(cache.stats().residentBytes,0);
});

test('concurrent acquires de-duplicate one load and independent leases',async()=>{
  let loads=0,resolve;const gate=new Promise(r=>resolve=r);
  const cache=new ResidencyCache(async key=>{loads++;await gate;return {key,byteLength:4};},{budgetBytes:8});
  const p1=cache.acquire(1),p2=cache.acquire(1);await sleep(5);assert.equal(loads,1);assert.equal(cache.stats().inFlight,1);
  resolve();const [a,b]=await Promise.all([p1,p2]);assert.equal(a.value,b.value);a.release();b.release();assert.equal(cache.stats().loads,1);
});

test('active leases pin memory and prevent unsafe over-budget load',async()=>{
  const cache=new ResidencyCache(async key=>({key,byteLength:6}),{budgetBytes:10});const a=await cache.acquire('a');
  await assert.rejects(cache.acquire('b'),/pinned/);a.release();const b=await cache.acquire('b');assert.equal(cache.stats().residentBanks,1);b.release();
});

test('prefetch, shrink and dispose are bounded and zero/dispose payloads',async()=>{
  const disposed=[];const cache=new ResidencyCache(async key=>({key,byteLength:4}),{budgetBytes:12,disposer:v=>disposed.push(v.key)});
  await cache.prefetch([0,1,2]);assert.equal(cache.stats().residentBytes,12);cache.setBudget(8);assert.equal(cache.stats().residentBanks,2);assert.equal(disposed.length,1);
  const lease=await cache.acquire(1);cache.dispose();assert.equal(cache.stats().disposed,true);assert.ok(cache.stats().residentBytes>0);lease.release();assert.equal(cache.stats().residentBytes,0);
  await assert.rejects(cache.acquire(2),/disposed/);
});

test('aborted waiter does not pin a shared completed load',async()=>{
  let resolve;const gate=new Promise(r=>resolve=r);const cache=new ResidencyCache(async()=>{await gate;return {byteLength:4};},{budgetBytes:8});
  const controller=new AbortController();const p=cache.acquire('x',{signal:controller.signal});controller.abort(new Error('stop'));resolve();await assert.rejects(p,/stop/);
  await sleep(0);assert.equal(cache.stats().residentBanks,1);assert.equal(cache.stats().residentBytes,4);
});

const sha=bytes=>crypto.createHash('sha256').update(bytes).digest('hex');
const jsonBytes=o=>new TextEncoder().encode(JSON.stringify(o));
function makeHttpFixture(){
  const nativeSize=16,levels=5,layersPerBank=1;const banks=[],sprites=[];const files=new Map();
  for(let bank=0;bank<2;bank++){
    const levelRecords=[],levelBytes=[];
    for(let level=0;level<levels;level++){
      const side=nativeSize>>level,raw=new Uint8Array(side*side*4);for(let p=0;p<raw.length;p+=4){raw[p]=bank?0:64;raw[p+1]=level;raw[p+2]=bank?32:0;raw[p+3]=128;}
      levelBytes.push(raw);levelRecords.push({level,size:side,file:`unused-${bank}-${level}`,byteLength:raw.length,sha256:sha(raw)});
    }
    const marker=new Uint8Array([bank+1,7,9]);files.set(`banks/bank-00${bank}.ktx2`,marker);
    banks.push({index:bank,layerCount:1,levels:levelRecords,_decoded:levelBytes,_marker:marker});
    sprites.push({spriteKey:`sprite-${bank}`,digestHex:String(bank).padStart(64,'0'),family:'sigil',palette:'neon',complexity:4,nativeSize,
      bankIndex:bank,layerIndex:0,sourceFile:'x',sourceFileSha256:'0'.repeat(64),sourceRGBAsha256:'1'.repeat(64),levelSha256:levelBytes.map(sha)});
  }
  const source={nativeSize,layersPerBank,spriteCount:2,levelCount:levels,payloadBytes:banks.flatMap(b=>b._decoded).reduce((n,b)=>n+b.length,0),banks:banks.map(({_decoded,_marker,...b})=>b),sprites};
  const sourceBytes=jsonBytes(source);files.set('source-manifest.json',sourceBytes);
  const transport={sourceManifest:{file:'source-manifest.json',byteLength:sourceBytes.length,sha256:sha(sourceBytes)},banks:banks.map((b,i)=>({index:i,layerCount:1,file:`banks/bank-00${i}.ktx2`,byteLength:b._marker.length,sha256:sha(b._marker)}))};
  const manifestBytes=jsonBytes(transport);files.set('manifest.json',manifestBytes);
  return {files,transport,source,banks,manifestBytes};
}

test('openKtx2 lazily integrity-checks banks and evicts under decoded-byte budget',async()=>{
  const fixture=makeHttpFixture();const oldFetch=globalThis.fetch,oldLocation=globalThis.location,oldApi=globalThis.ByteFablesKtx2Textures;
  globalThis.location=new URL('http://example.test/app');
  globalThis.fetch=async url=>{const path=new URL(url).pathname.replace('/bundle/','');const body=fixture.files.get(path);return body?new Response(body,{status:200,headers:{'content-length':String(body.length)}}):new Response('no',{status:404});};
  globalThis.ByteFablesKtx2Textures={
    sha256:async bytes=>sha(bytes),validateManifest:()=>true,
    decode:bytes=>{const bank=bytes[0]-1;return {size:16,layers:1,levels:fixture.banks[bank]._decoded};},
    lookup:(manifest,selector)=>selector.bank
  };
  try{
    const oneBank=fixture.banks[0]._decoded.reduce((n,b)=>n+b.length,0);const bundle=await openKtx2('http://example.test/bundle/',{budgetBytes:oneBank,manifestSha256:sha(fixture.manifestBytes)});
    assert.equal(bundle.stats().residentBanks,0);const a=await bundle.acquireSprite({bank:0});assert.equal(a.sprite.bankIndex,0);a.release();
    const b=await bundle.acquireBank(1);b.release();assert.equal(bundle.stats().residentBanks,1);assert.equal(bundle.stats().evictions,1);assert.equal(bundle.stats().loads,2);
    bundle.dispose();assert.equal(bundle.stats().residentBytes,0);
  }finally{globalThis.fetch=oldFetch;globalThis.location=oldLocation;globalThis.ByteFablesKtx2Textures=oldApi;}
});

test('openKtx2 rejects bank checksum substitution before decode',async()=>{
  const fixture=makeHttpFixture();const oldFetch=globalThis.fetch,oldLocation=globalThis.location,oldApi=globalThis.ByteFablesKtx2Textures;
  globalThis.location=new URL('http://example.test/');let decoded=0;
  globalThis.fetch=async url=>{const path=new URL(url).pathname.replace('/bundle/','');let body=fixture.files.get(path);if(path==='banks/bank-000.ktx2')body=new Uint8Array([99,7,9]);return body?new Response(body,{status:200}):new Response('no',{status:404});};
  globalThis.ByteFablesKtx2Textures={sha256:async bytes=>sha(bytes),validateManifest:()=>true,decode:()=>{decoded++;return {};},lookup:()=>0};
  try{const bundle=await openKtx2('http://example.test/bundle/',{budgetBytes:100000});await assert.rejects(bundle.acquireBank(0),/checksum/);assert.equal(decoded,0);bundle.dispose();}
  finally{globalThis.fetch=oldFetch;globalThis.location=oldLocation;globalThis.ByteFablesKtx2Textures=oldApi;}
});

test('budget shrink fails atomically when pinned bytes exceed new limit',async()=>{
  const disposed=[];const cache=new ResidencyCache(async key=>({key,byteLength:6}),{budgetBytes:12,disposer:v=>disposed.push(v.key)});
  const a=await cache.acquire('a');const b=await cache.acquire('b');
  assert.throws(()=>cache.setBudget(6),/pinned/);assert.equal(cache.stats().budgetBytes,12);assert.equal(cache.stats().residentBanks,2);assert.deepEqual(disposed,[]);
  a.release();b.release();cache.setBudget(6);assert.equal(cache.stats().residentBanks,1);assert.equal(cache.stats().evictions,1);cache.dispose();
});

test('dispose during an in-flight load disposes the completed payload instead of leaking it',async()=>{
  let resolve;const gate=new Promise(r=>resolve=r);const disposed=[];
  const cache=new ResidencyCache(async()=>{await gate;return {id:'late',byteLength:4};},{budgetBytes:8,disposer:v=>disposed.push(v.id)});
  const pending=cache.acquire('late');await sleep(5);cache.dispose();resolve();
  await assert.rejects(pending,/disposed/);await sleep(0);assert.deepEqual(disposed,['late']);assert.equal(cache.stats().residentBytes,0);
});
