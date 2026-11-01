// Cross-language and network contracts; real GPU readback is a separate required browser job.
import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {runInNewContext} from 'node:vm';
import {webcrypto,createHash} from 'node:crypto';
const alpha=readFileSync(new URL('../integrations/web/artwork-alpha-textures/runtime.js',import.meta.url),'utf8');
const transport=readFileSync(new URL('../integrations/web/artwork-ktx2/ktx2-runtime.js',import.meta.url),'utf8');
const vector=JSON.parse(readFileSync(new URL('./vectors/artwork-ktx2-v1.json',import.meta.url)));
const hash=x=>createHash('sha256').update(x).digest('hex'),clone=x=>structuredClone(x);
const bytes=x=>new Uint8Array(Buffer.from(x,'base64'));
function context(fetch){const c={performance,URL,TextDecoder,TextEncoder,Uint8Array,Float32Array,ArrayBuffer,DataView,crypto:webcrypto,
 location:{href:'http://localhost/ktx2/',origin:'http://localhost'},fetch};
 runInNewContext(alpha,c);runInNewContext(transport,c);return {api:c.ByteFablesKtx2Textures,alpha:c.ByteFablesAlphaTextures};}
function fixture(doc=vector.transport,files=vector.files,calls=[]){return async(url,options)=>{
 calls.push([String(url),options]);const path=new URL(url).pathname.slice('/ktx2/'.length);
 return path==='manifest.json'?new Response(JSON.stringify(doc)):
  path in files?new Response(Buffer.from(files[path],'base64')):new Response('missing',{status:404});};}
function rawLevels(api){return vector.transport.banks.map(b=>api.decode(bytes(vector.files[b.file])).levels);}

test('Python KTX2 files decode to the original bank and layer mip hashes',()=>{
 const {api}=context(fixture());
 for(const bank of vector.transport.banks){const data=bytes(vector.files[bank.file]),parsed=api.decode(data);
  assert.equal(data.length,api.lengthFor(16,bank.layerCount));assert.equal(parsed.size,16);assert.equal(parsed.layers,bank.layerCount);
  parsed.levels.forEach((raw,i)=>assert.equal(hash(raw),vector.source.banks[bank.index].levels[i].sha256));
 }
});
test('strict parser rejects formats, cubemaps, supercompression and malformed offsets',()=>{
 const {api}=context(fixture()),original=bytes(vector.files[vector.transport.banks[0].file]);
 for(const [at,value] of [[12,43],[16,4],[24,32],[28,1],[32,0],[36,6],[40,0],[44,2],[48,0],[52,0],[56,0],[60,0]]){
  const data=original.slice();new DataView(data.buffer).setUint32(at,value,true);assert.throws(()=>api.decode(data));
 }
 for(const at of [64,72,80,88,96]){const data=original.slice();new DataView(data.buffer).setBigUint64(at,2n**63n,true);assert.throws(()=>api.decode(data));}
});
test('parser rejects alpha/colour/orientation metadata changes and invalid PM samples',()=>{
 const {api}=context(fixture()),original=bytes(vector.files[vector.transport.banks[0].file]);
 for(const at of [0,200,214,215,231,300,400]){const data=original.slice();data[at]^=1;assert.throws(()=>api.decode(data));}
 const data=original.slice(),v=new DataView(data.buffer),at=Number(v.getBigUint64(80,true));data.set([255,0,0,1],at);
 assert.throws(()=>api.decode(data),/premultiplied/);
});
test('truncation and appended bytes are never accepted',()=>{
 const {api}=context(fixture()),original=bytes(vector.files[vector.transport.banks[0].file]);
 for(const n of [0,12,79,80,199,291,original.length-1])assert.throws(()=>api.decode(original.subarray(0,n)));
 const appended=new Uint8Array(original.length+1);appended.set(original);assert.throws(()=>api.decode(appended));
});
test('transport loader uses one request per bank and preserves original private-runtime contract',async()=>{
 const calls=[],{api}=context(fixture(undefined,undefined,calls)),bundle=await api.loadBundle('./');
 assert.equal(calls.length,vector.transport.banks.length+2);assert.equal(bundle.manifestSha256,vector.transport.sourceManifest.sha256);
 assert.equal(bundle.manifest.sprites[0].spriteKey,vector.source.sprites[0].spriteKey);
 assert.ok(Object.isFrozen(bundle.manifest));assert.equal(bundle.payload,undefined);
 assert.ok(calls.every(([,o])=>o.credentials==='omit'&&o.redirect==='error'));
 bundle.dispose();bundle.dispose();assert.equal(bundle.disposed,true);
});
test('cross-origin, non-HTTP, credentials and unsafe pins fail closed',async()=>{
 const calls=[],{api}=context(fixture(undefined,undefined,calls));
 for(const url of ['https://evil.invalid/','file:///tmp/','http://user@localhost/ktx2/','./?a=1','./#b'])await assert.rejects(()=>api.loadBundle(url));
 assert.equal(calls.length,0);await assert.rejects(()=>api.loadBundle('./',{manifestSha256:'0'.repeat(64)}),/checksum/);
});
test('file checksums and transport source binding reject changed bytes',async()=>{
 let files=clone(vector.files);files[vector.transport.banks[0].file]=Buffer.from('bad').toString('base64');
 await assert.rejects(()=>context(fixture(undefined,files)).api.loadBundle('./'),/checksum/);
 files=clone(vector.files);files['source-manifest.json']=Buffer.from(JSON.stringify({...vector.source,sourceManifestSha256:'0'.repeat(64)})).toString('base64');
 await assert.rejects(()=>context(fixture(undefined,files)).api.loadBundle('./'),/source manifest checksum/);
});
test('rehashed bank substitution cannot bypass original per-mip checksums',async()=>{
 const doc=clone(vector.transport),files=clone(vector.files),record=doc.banks[0],data=bytes(files[record.file]);
 const at=Number(new DataView(data.buffer).getBigUint64(80,true));data.set([1,1,1,255],at);
 record.sha256=hash(data);files[record.file]=Buffer.from(data).toString('base64');
 await assert.rejects(()=>context(fixture(doc,files)).api.loadBundle('./'),/Mip file checksum/);
});
test('budgets apply before bank fetches and streaming response limits are enforced',async()=>{
 const calls=[],{api}=context(fixture(undefined,undefined,calls));
 await assert.rejects(()=>api.loadBundle('./',{maxTextureBytes:1024}),/memory budget/);assert.equal(calls.length,2);
 await assert.rejects(()=>context(async()=>new Response('x',{headers:{'content-length':'16777217'}})).api.loadBundle('./'),/budget/);
});
test('malicious manifest paths and changed array placement are rejected',()=>{
 const {api}=context(fixture());
 for(const change of [m=>m.banks[0].file='../secret',m=>m.sourceManifest.file='https://evil/',m=>m.banks[0].layerCount=300,
 m=>m.banks[0].byteLength=2**32,m=>m.publicOnly=false,m=>m.unknown=1]){
 const doc=clone(vector.transport);change(doc);assert.throws(()=>api.validateManifest(doc,vector.source));}
});
test('shared fromLevels snapshots caller bytes before first await and verifies all hashes',async()=>{
 const {api,alpha:shared}=context(fixture()),source=bytes(vector.files['source-manifest.json']),payload=rawLevels(api);
 const loading=shared.fromLevels(source,payload);source.fill(0);payload.flat().forEach(x=>x.fill(0));
 const bundle=await loading;assert.equal(bundle.manifest.spriteCount,4);bundle.dispose();
 await assert.rejects(()=>shared.fromLevels(bytes(vector.files['source-manifest.json']),payload),/checksum/);
});
test('shared fromLevels rejects forged layer identity and count without allocating GPU resources',async()=>{
 const {api,alpha:shared}=context(fixture());let source=clone(vector.source);source.sprites[0].levelSha256[0]='0'.repeat(64);
 await assert.rejects(()=>shared.fromLevels(new TextEncoder().encode(JSON.stringify(source)),rawLevels(api)),/layer checksum/);
 source=clone(vector.source);source.sprites[0].spriteKey='bfalpha1-'+'0'.repeat(64);
 await assert.rejects(()=>shared.fromLevels(new TextEncoder().encode(JSON.stringify(source)),rawLevels(api)),/identity checksum/);
 await assert.rejects(()=>shared.fromLevels(bytes(vector.files['source-manifest.json']),[]),/count/);
});
test('pre-aborted KTX2 loads fail before bank data is consumed',async()=>{
 const controller=new AbortController();controller.abort();
 await assert.rejects(()=>context(fixture()).api.loadBundle('./',{signal:controller.signal}),/aborted/);
});
test('renderer is shared, and no external decoder or CSP exception is required',()=>{
 const {api,alpha:shared}=context(fixture());assert.equal(api.WebGLArray,shared.WebGLArray);
 assert.doesNotMatch(transport,/eval\(|new Function|generateMipmap|import\(/);
 const html=readFileSync(new URL('../integrations/web/artwork-ktx2/index.html',import.meta.url),'utf8');
 assert.match(html,/script-src 'self'/);assert.doesNotMatch(html,/unsafe-eval|unsafe-inline/);
});

test('Buffer subclasses are copied rather than retaining Buffer.slice views',async()=>{
 const {api,alpha:shared}=context(fixture()),source=Buffer.from(vector.files['source-manifest.json'],'base64');
 const payload=rawLevels(api).map(bank=>bank.map(data=>Buffer.from(data)));
 const loading=shared.fromLevels(source,payload);source.fill(0);payload.flat().forEach(data=>data.fill(0));
 const bundle=await loading;assert.equal(bundle.manifest.spriteCount,4);bundle.dispose();
});
