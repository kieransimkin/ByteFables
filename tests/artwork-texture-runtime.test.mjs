// Pure API/GL-call contract tests. Real browser pixel tests are separate.
import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {runInNewContext} from 'node:vm';
import {createHash,webcrypto} from 'node:crypto';
const code=readFileSync(new URL('../integrations/web/artwork-textures/runtime.js',import.meta.url),'utf8');
const fixture=JSON.parse(readFileSync(new URL('./vectors/artwork-textures-v1.json',import.meta.url)));
function runtime(extra={}){const context={performance,URL,TextDecoder,TextEncoder,Uint8Array,Float32Array,ArrayBuffer,
  crypto:webcrypto,location:{href:'http://localhost/textures/',origin:'http://localhost'},...extra};
  runInNewContext(code,context);return context.ByteFablesTextures;}
const plain=x=>JSON.parse(JSON.stringify(x));

test('Python geometry fixture is accepted with both UV conventions and stable sprite keys',()=>{
 const api=runtime();assert.equal(api.validateManifest(fixture),fixture);
 for(const s of fixture.sprites){const identity={profile:fixture.profile,digestHex:s.digestHex,family:s.family,palette:s.palette,
  complexity:s.complexity,nativeSize:s.nativeSize,rgbaSha256:s.rgbaSha256};
  assert.equal(s.spriteKey,'bftexture1-'+createHash('sha256').update(JSON.stringify(identity,null,2)+'\n').digest('hex'));}
});
test('1000-instance layout is explicit about repeated sprites and bounded canvas dimensions',()=>{
 const api=runtime(),grid=api.makeGrid(fixture,1000,40,16);
 assert.equal(grid.instances.length,1000);assert.equal(new Set(grid.instances.map(x=>x.spriteIndex)).size,10);
 assert.deepEqual([grid.width,grid.height],[640,400]);
 for(const args of [[0],[10001],[1000,0],[10000,100,512],[2,2,NaN]])assert.throws(()=>api.makeGrid(fixture,...args));
});
test('full digest plus style lookup never resolves a short alias',()=>{
 const api=runtime();assert.equal(api.lookup(fixture,{digestHex:fixture.sprites[2].digestHex,family:'sigil'}),2);
 assert.throws(()=>api.lookup(fixture,{digestHex:'0000',family:'sigil'}));
 assert.throws(()=>api.lookup(fixture,{digestHex:fixture.sprites[2].digestHex,family:'crystal'}));
});
test('page batching preserves painter order even when pages alternate',()=>{
 const api=runtime(),items=[0,9,1].map(spriteIndex=>({spriteIndex,x:0,y:0,width:16,height:16}));
 assert.deepEqual(plain(api.runs(fixture,items,16,16).map(x=>x.pageIndex)),[0,1,0]);
 for(const bad of [{...items[0],spriteIndex:10},{...items[0],x:-1},{...items[0],width:17}])assert.throws(()=>api.runs(fixture,[bad],16,16));
});
test('manifest parser rejects traversal, duplicates, geometry changes and unsafe memory sizes',()=>{
 const api=runtime();
 const cases=[m=>m.pages[0].file='../private.png',m=>m.pages[0].file='https://example.invalid/x.png',
 m=>m.sprites[0].rect=[0,0,16,16],m=>m.sprites[0].uvTopLeft=[0,0,1,1],m=>m.sprites[0].family='<script>',
 m=>m.sprites[1].digestHex=m.sprites[0].digestHex,m=>m.sampling.mipmaps=true,m=>m.pageSize=65536,
 m=>m.spriteCount=100000,m=>m.publicOnly=false,m=>m.sprites.reverse()];
 for(const mutate of cases){const m=structuredClone(fixture);mutate(m);assert.throws(()=>api.validateManifest(m));}
});
test('loader rejects cross-origin URLs and manifest substitution before loading textures',async()=>{
 let calls=0;const bytes=new TextEncoder().encode(JSON.stringify(fixture));
 const fetch=async()=>{calls++;return new Response(bytes);};const api=runtime({fetch});
 for(const url of ['https://evil.invalid/','http://localhost/textures/?q=x','file:///tmp/','http://user@localhost/'])
  await assert.rejects(()=>api.loadBundle(url));
 assert.equal(calls,0);
 await assert.rejects(()=>api.loadBundle('./',{manifestSha256:'0'.repeat(64)}),/checksum/);assert.equal(calls,1);
});
test('loader enforces manifest byte and decoded texture budgets',async()=>{
 const huge=new Response('x',{headers:{'content-length':String(16777217)}});
 await assert.rejects(()=>runtime({fetch:async()=>huge}).loadBundle('./'),/budget/);
 const bytes=new TextEncoder().encode(JSON.stringify(fixture));
 await assert.rejects(()=>runtime({fetch:async()=>new Response(bytes)}).loadBundle('./',{maxTextureBytes:16384}),/memory budget/);
});
test('Canvas consumer copies supplied native rectangles and rejects use after disposal',()=>{
 const ops=[],ctx={clearRect(...a){ops.push(['clear',...a]);},drawImage(...a){ops.push(['image',...a]);}};
 const canvas={width:32,height:16,getContext:()=>ctx},bundle={manifest:fixture,images:['page0','page1'],disposed:false};
 const api=runtime(),consumer=new api.CanvasAtlas(canvas,bundle),items=api.makeGrid(fixture,2,2,16).instances;
 const result=consumer.draw(items);assert.equal(result.drawCalls,2);
 assert.deepEqual(ops[1],['image','page0',2,2,16,16,0,0,16,16]);assert.equal(ctx.imageSmoothingEnabled,false);
 consumer.dispose();assert.throws(()=>consumer.draw(items),/disposed/);
});
function fakeGL(){let id=0;const calls=[];const gl={calls};
 for(const name of ['MAX_TEXTURE_SIZE','ARRAY_BUFFER','STATIC_DRAW','DYNAMIC_DRAW','FLOAT','VERTEX_SHADER','FRAGMENT_SHADER','COMPILE_STATUS','LINK_STATUS','TEXTURE_2D','TEXTURE_MIN_FILTER','TEXTURE_MAG_FILTER','LINEAR','NEAREST','TEXTURE_WRAP_S','TEXTURE_WRAP_T','CLAMP_TO_EDGE','RGBA8','RGBA','UNSIGNED_BYTE','NO_ERROR','UNPACK_FLIP_Y_WEBGL','UNPACK_PREMULTIPLY_ALPHA_WEBGL','UNPACK_COLORSPACE_CONVERSION_WEBGL','NONE','BLEND','DEPTH_TEST','DITHER','SCISSOR_TEST','COLOR_BUFFER_BIT','TEXTURE0','TRIANGLES'])gl[name]=name;
 for(const name of ['Shader','Program','VertexArray','Buffer','Texture'])gl['create'+name]=()=>({id:++id});
 gl.getParameter=()=>4096;gl.getShaderParameter=()=>true;gl.getProgramParameter=()=>true;
 gl.getAttribLocation=()=>1;gl.getUniformLocation=()=>1;gl.getError=()=>gl.NO_ERROR;
 for(const name of ['shaderSource','compileShader','getShaderInfoLog','attachShader','linkProgram','getProgramInfoLog','bindVertexArray','bindBuffer','bufferData','enableVertexAttribArray','vertexAttribPointer','vertexAttribDivisor','pixelStorei','bindTexture','texParameteri','texImage2D','viewport','disable','clearColor','clear','useProgram','uniform2f','uniform1i','activeTexture','drawArraysInstanced','deleteTexture','deleteBuffer','deleteShader','deleteVertexArray','deleteProgram'])gl[name]=(...args)=>calls.push([name,...args]);
 return gl;}
test('WebGL2 batches instances, disables mipmaps and releases GPU resources',()=>{
 const gl=fakeGL(),listeners={},canvas={width:640,height:400,getContext:()=>gl,
 addEventListener:(n,f)=>listeners[n]=f,removeEventListener:n=>delete listeners[n]};
 const bundle={manifest:fixture,images:[{},{}],disposed:false},api=runtime();
 const renderer=new api.WebGLAtlas(canvas,bundle);const result=renderer.draw(api.makeGrid(fixture,1000,40,16).instances);
 const draws=gl.calls.filter(x=>x[0]==='drawArraysInstanced');assert.equal(draws.reduce((sum,x)=>sum+x[4],0),1000);
 assert.equal(result.drawCalls,draws.length);
 assert.ok(gl.calls.some(x=>x[0]==='texParameteri'&&x[2]===gl.TEXTURE_MIN_FILTER&&x[3]===gl.NEAREST));
 listeners.webglcontextlost({preventDefault(){}});assert.throws(()=>renderer.draw([]),/lost/);
 renderer.dispose();renderer.dispose();assert.equal(gl.calls.filter(x=>x[0]==='deleteTexture').length,2);
});
test('strict-CSP smoke uses locator assertions and image decode rather than eval polling',()=>{
 const smoke=readFileSync(new URL('./browser/artwork-assets-smoke.py',import.meta.url),'utf8');
 assert.doesNotMatch(smoke,/wait_for_function|bypass_csp/);assert.match(smoke,/await image\.decode/);
 const html=readFileSync(new URL('../integrations/web/artwork-textures/index.html',import.meta.url),'utf8');
 assert.doesNotMatch(html,/unsafe-eval|unsafe-inline/);assert.match(html,/script-src 'self'/);
 assert.doesNotMatch(code,/\beval\s*\(|new Function/);
});
