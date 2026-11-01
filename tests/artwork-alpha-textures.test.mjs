// Loader/GL-call contract tests, not a claim of real GPU execution.
import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {runInNewContext} from 'node:vm';
import {webcrypto,createHash} from 'node:crypto';
const code=readFileSync(new URL('../integrations/web/artwork-alpha-textures/runtime.js',import.meta.url),'utf8');
const vector=JSON.parse(readFileSync(new URL('./vectors/artwork-alpha-textures-v1.json',import.meta.url)));
const clone=x=>structuredClone(x),plain=x=>JSON.parse(JSON.stringify(x));
const hash=x=>createHash('sha256').update(x).digest('hex');
function context(extra={}){const c={performance,URL,TextDecoder,TextEncoder,Uint8Array,Float32Array,ArrayBuffer,crypto:webcrypto,
 location:{href:'http://localhost/alpha/',origin:'http://localhost'},...extra};runInNewContext(code,c);return c.ByteFablesAlphaTextures;}
function fetchFixture(manifest=vector.manifest,files=vector.files,calls=[]){return async(url,options)=>{
 calls.push([String(url),options]);const path=new URL(url).pathname.slice('/alpha/'.length);
 if(path==='manifest.json')return new Response(JSON.stringify(manifest));
 if(!(path in files))return new Response('missing',{status:404});return new Response(Buffer.from(files[path],'base64'));};}
async function loaded(extra={}){const api=context({fetch:fetchFixture(),...extra});return [api,await api.loadBundle('./')];}
function fakeGL({error=false,maxLayers=256}={}){let id=0;const calls=[],gl={calls};
 for(const name of ['MAX_TEXTURE_SIZE','MAX_ARRAY_TEXTURE_LAYERS','ARRAY_BUFFER','STATIC_DRAW','DYNAMIC_DRAW','FLOAT',
 'VERTEX_SHADER','FRAGMENT_SHADER','COMPILE_STATUS','LINK_STATUS','TEXTURE_2D_ARRAY','TEXTURE_MIN_FILTER','TEXTURE_MAG_FILTER',
 'NEAREST_MIPMAP_NEAREST','LINEAR_MIPMAP_LINEAR','NEAREST','LINEAR','TEXTURE_WRAP_S','TEXTURE_WRAP_T','TEXTURE_WRAP_R','TEXTURE_MAX_LEVEL',
 'CLAMP_TO_EDGE','RGBA8','RGBA','UNSIGNED_BYTE','NO_ERROR','UNPACK_ALIGNMENT','UNPACK_FLIP_Y_WEBGL','UNPACK_PREMULTIPLY_ALPHA_WEBGL',
 'UNPACK_COLORSPACE_CONVERSION_WEBGL','NONE','DEPTH_TEST','DITHER','SCISSOR_TEST','CULL_FACE','BLEND','FUNC_ADD','ONE','ONE_MINUS_SRC_ALPHA',
 'COLOR_BUFFER_BIT','TEXTURE0','TRIANGLES'])gl[name]=name;
 for(const type of ['Shader','Program','VertexArray','Buffer','Texture'])gl['create'+type]=()=>({id:++id});
 gl.getParameter=p=>p===gl.MAX_ARRAY_TEXTURE_LAYERS?maxLayers:4096;
 gl.getShaderParameter=()=>true;gl.getProgramParameter=()=>true;gl.getUniformLocation=()=>1;gl.getError=()=>error?'ERROR':gl.NO_ERROR;gl.isContextLost=()=>false;
 for(const name of ['shaderSource','compileShader','getShaderInfoLog','attachShader','linkProgram','getProgramInfoLog','bindVertexArray',
 'bindBuffer','bufferData','enableVertexAttribArray','vertexAttribPointer','vertexAttribDivisor','pixelStorei','bindTexture','texParameteri',
 'texStorage3D','texSubImage3D','viewport','disable','enable','colorMask','blendEquationSeparate','blendFuncSeparate','clearColor','clear',
 'useProgram','uniform2f','uniform1i','activeTexture','drawArraysInstanced','deleteTexture','deleteBuffer','deleteShader','deleteVertexArray',
 'deleteProgram','readPixels'])gl[name]=(...args)=>calls.push([name,...args]);return gl;}
function canvasFor(gl){const events={};return {width:640,height:400,events,getContext:()=>gl,
 addEventListener:(n,f)=>events[n]=f,removeEventListener:n=>delete events[n]};}

test('Python manifest/vector includes complete isolated mip chains and stable keys',()=>{
 const api=context();assert.equal(api.validateManifest(vector.manifest),vector.manifest);
 for(const s of vector.manifest.sprites){const identity={profile:vector.manifest.profile,digestHex:s.digestHex,family:s.family,palette:s.palette,
 complexity:s.complexity,nativeSize:s.nativeSize,sourceRGBAsha256:s.sourceRGBAsha256};
 assert.equal(s.spriteKey,'bfalpha1-'+hash(JSON.stringify(identity,null,2)+'\n'));}
});
test('loader verifies file and per-layer hashes, freezes metadata, and keeps raw payload private',async()=>{
 const calls=[],api=context({fetch:fetchFixture(undefined,undefined,calls)}),bundle=await api.loadBundle('./');
 assert.equal(calls.length,11);assert.equal(bundle.banks,undefined);assert.equal(bundle.payload,undefined);
 assert.ok(Object.isFrozen(bundle.manifest.sprites[0]));assert.ok(calls.every(([,o])=>o.credentials==='omit'&&o.redirect==='error'));
 bundle.dispose();bundle.dispose();assert.equal(bundle.disposed,true);
});
test('cross-origin, credentials, redirects, paths and bad pins fail before uploads',async()=>{
 const calls=[],api=context({fetch:fetchFixture(undefined,undefined,calls)});
 for(const url of ['https://evil.invalid/','file:///tmp/','http://user@localhost/alpha/','./?query=1','./#fragment'])await assert.rejects(()=>api.loadBundle(url));
 assert.equal(calls.length,0);
 await assert.rejects(()=>api.loadBundle('./',{manifestSha256:'0'.repeat(64)}),/checksum/);
});
test('loader rejects oversized response, pixel budgets and corruption',async()=>{
 await assert.rejects(()=>context({fetch:async()=>new Response('x',{headers:{'content-length':'16777217'}})}).loadBundle('./'),/budget/);
 await assert.rejects(()=>context({fetch:fetchFixture()}).loadBundle('./',{maxTextureBytes:1024}),/memory budget/);
 const files=clone(vector.files);files[Object.keys(files)[0]]=Buffer.from('bad').toString('base64');
 await assert.rejects(()=>context({fetch:fetchFixture(undefined,files)}).loadBundle('./'),/checksum/);
});
test('loader rejects substituted per-layer hashes and forged sprite identity keys',async()=>{
 let m=clone(vector.manifest);m.sprites[0].levelSha256[0]='0'.repeat(64);
 await assert.rejects(()=>context({fetch:fetchFixture(m)}).loadBundle('./'),/layer checksum/);
 m=clone(vector.manifest);m.sprites[0].spriteKey='bfalpha1-'+'0'.repeat(64);
 await assert.rejects(()=>context({fetch:fetchFixture(m)}).loadBundle('./'),/identity checksum/);
});
test('loader validates PM samples even if payload hashes are recomputed',async()=>{
 const m=clone(vector.manifest),files=clone(vector.files),rec=m.banks[0].levels[4],raw=Buffer.from(files[rec.file],'base64');
 raw[0]=255;raw[3]=1;files[rec.file]=raw.toString('base64');rec.sha256=hash(raw);m.sprites[0].levelSha256[4]=hash(raw.subarray(0,4));
 await assert.rejects(()=>context({fetch:fetchFixture(m,files)}).loadBundle('./'),/premultiplied/);
});
test('manifest rejects changed dimensions, alpha contracts and path traversal',()=>{
 const api=context();for(const change of [m=>m.banks[0].levels[0].file='../x',m=>m.banks[0].layerCount=300,m=>m.levelCount=1,
 m=>m.sampling.alpha='straight',m=>m.sampling.generatedOnGPU=true,m=>m.nativeSize=1024,m=>m.spriteCount=100000,
 m=>m.sprites[0].layerIndex=1,m=>m.sprites.reverse(),m=>m.unexpected=1,m=>m.sprites[0].levelSha256=[]]){
 const m=clone(vector.manifest);change(m);assert.throws(()=>api.validateManifest(m));}
});
test('lookup requires full digest and matching style',()=>{
 const api=context();assert.equal(api.lookup(vector.manifest,{digestHex:vector.manifest.sprites[2].digestHex,family:'sigil'}),2);
 assert.throws(()=>api.lookup(vector.manifest,{digestHex:'123',family:'sigil'}));
 assert.throws(()=>api.lookup(vector.manifest,{digestHex:'f'.repeat(64),family:'sigil'}));
});
test('LOD selection is bounded and batching preserves painter order across banks',()=>{
 const api=context(),items=[0,2,1].map(spriteIndex=>({spriteIndex,x:0,y:0,width:4,height:4}));
 const batches=api.runs(vector.manifest,items,16,16);assert.deepEqual(plain(batches.map(b=>b.bankIndex)),[0,1,0]);
 assert.equal(batches[0].items[0].lod,2);assert.equal(api.runs(vector.manifest,[{...items[0],width:1,height:1}],16,16)[0].items[0].lod,4);
 for(const patch of [{lod:5},{lod:NaN},{opacity:2},{width:0},{x:-1},{spriteIndex:4}])
 assert.throws(()=>api.runs(vector.manifest,[{...items[0],...patch}],16,16));
});
test('1000/10000 repeated-instance workloads are bounded and not called unique identities',()=>{
 const api=context(),grid=api.makeGrid(vector.manifest,1000,40,8);assert.deepEqual([grid.width,grid.height],[320,200]);
 assert.equal(grid.instances.length,1000);assert.equal(new Set(grid.instances.map(i=>i.spriteIndex)).size,4);
 assert.equal(api.makeGrid(vector.manifest,10000,100,1).instances.length,10000);
 for(const args of [[10001],[1000,40,512],[0],[1000,0,8]])assert.throws(()=>api.makeGrid(vector.manifest,...args));
});
test('GPU uploads each supplied level with texture arrays and never generates page mips',async()=>{
 const [api,bundle]=await loaded(),gl=fakeGL(),canvas=canvasFor(gl),renderer=new api.WebGLArray(canvas,bundle);
 const uploads=gl.calls.filter(c=>c[0]==='texSubImage3D');assert.equal(uploads.length,10);
 assert.equal(gl.calls.filter(c=>c[0]==='texStorage3D').length,2);
 assert.equal(uploads[0][2],0);assert.equal(uploads[4][6],1);assert.equal(uploads[4][8],2);
 assert.doesNotMatch(code,/generateMipmap/);
 renderer.draw(api.makeGrid(bundle.manifest,1000,40,16).instances,{background:[255,255,255,255]});
 const draws=gl.calls.filter(c=>c[0]==='drawArraysInstanced');assert.equal(draws.reduce((n,c)=>n+c[4],0),1000);
 assert.ok(gl.calls.some(c=>c[0]==='blendFuncSeparate'&&c.slice(1).join()===['ONE','ONE_MINUS_SRC_ALPHA','ONE','ONE_MINUS_SRC_ALPHA'].join()));
 renderer.dispose();renderer.dispose();assert.equal(gl.calls.filter(c=>c[0]==='deleteTexture').length,2);bundle.dispose();
});
test('trilinear sampling is opt-in; loss and disposal fail closed',async()=>{
 const [api,bundle]=await loaded(),gl=fakeGL(),canvas=canvasFor(gl),renderer=new api.WebGLArray(canvas,bundle,{filter:'linear-mipmap-linear'});
 assert.ok(gl.calls.some(c=>c[0]==='texParameteri'&&c[2]===gl.TEXTURE_MIN_FILTER&&c[3]===gl.LINEAR_MIPMAP_LINEAR));
 canvas.events.webglcontextlost({preventDefault(){}});assert.throws(()=>renderer.draw([]),/lost/);renderer.dispose();
 assert.throws(()=>renderer.readPixels(),/disposed/);bundle.dispose();assert.throws(()=>new api.WebGLArray(canvas,bundle),/live bundle/);
});
test('allocation failures and hardware layer limits release partial GPU resources',async()=>{
 const [api,bundle]=await loaded(),gl=fakeGL({error:true});assert.throws(()=>new api.WebGLArray(canvasFor(gl),bundle),/upload/);
 assert.equal(gl.calls.filter(c=>c[0]==='deleteTexture').length,1);
 const low=fakeGL({maxLayers:1});assert.throws(()=>new api.WebGLArray(canvasFor(low),bundle),/limits/);
 assert.equal(low.calls.filter(c=>c[0]==='texStorage3D').length,0);bundle.dispose();
});
test('arbitrary bundle objects cannot bypass byte verification',()=>{
 const api=context();assert.throws(()=>new api.WebGLArray(canvasFor(fakeGL()),{manifest:vector.manifest,disposed:false}),/Verified/);
});
test('runtime and preview preserve strict CSP and do not generate procedural art',()=>{
 const html=readFileSync(new URL('../integrations/web/artwork-alpha-textures/index.html',import.meta.url),'utf8');
 assert.match(html,/script-src 'self'/);assert.doesNotMatch(html,/unsafe-eval|unsafe-inline/);
 assert.doesNotMatch(code,/\beval\s*\(|new Function/);assert.match(code,/sampler2DArray/);assert.match(code,/textureLod/);
});
