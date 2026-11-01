/* Versioned PUBLIC premultiplied texture arrays. Consumes pixels; never generates artwork. */
(function(global) {
  'use strict';
  const SCHEMA='bytefables.alpha-texture-array-bundle.v1', PROFILE='bytefables.premultiplied-area-mips.v1';
  const FAMILIES=['sigil','constellation','heraldry','topography','crystal','mandala','cellular','branching','orbital'];
  const HEX=/^[0-9a-f]{64}$/, bundles=new WeakMap();
  const check=(yes,message)=>{if(!yes)throw new Error(message);};
  const integer=(n,lo,hi)=>Number.isSafeInteger(n)&&n>=lo&&n<=hi;
  const hex=x=>typeof x==='string'&&HEX.test(x);
  const keys=(o,names)=>check(o&&typeof o==='object'&&!Array.isArray(o)&&
    Object.keys(o).length===names.length&&names.every(n=>Object.prototype.hasOwnProperty.call(o,n)), 'Unexpected manifest fields');
  const equal=(a,b)=>JSON.stringify(a)===JSON.stringify(b);
  const identity=s=>({profile:PROFILE,digestHex:s.digestHex,family:s.family,palette:s.palette,
    complexity:s.complexity,nativeSize:s.nativeSize,sourceRGBAsha256:s.sourceRGBAsha256});
  const sampling={storage:'RGBA8',alpha:'premultiplied',origin:'top-left',colourSpace:'stored-samples-no-transfer',
    wrap:'clamp-to-edge',filters:['nearest','linear-mipmap-linear'],mipSource:'isolated-original-area',generatedOnGPU:false};

  function validateManifest(m) {
    keys(m,['schema','profile','status','publicOnly','guarantee','nativeSize','layersPerBank','spriteCount',
      'levelCount','payloadBytes','sourceManifestSha256','sampling','banks','sprites','viewerFiles']);
    check(m.schema===SCHEMA&&m.profile===PROFILE&&m.status==='passed'&&m.publicOnly===true&&
      m.guarantee==='presentation-only'&&hex(m.sourceManifestSha256),'Invalid public alpha texture manifest');
    check([16,32,64,128].includes(m.nativeSize)&&integer(m.layersPerBank,1,256)&&integer(m.spriteCount,1,1024),
      'Invalid texture dimensions/count');
    const levels=Math.log2(m.nativeSize)+1;
    const total=m.spriteCount*Array.from({length:levels},(_,l)=>(m.nativeSize>>l)**2*4).reduce((a,b)=>a+b,0);
    check(m.levelCount===levels&&m.payloadBytes===total&&total<=128*1024*1024,'Texture byte budget/count mismatch');
    keys(m.sampling,Object.keys(sampling));
    check(Object.entries(sampling).every(([k,v])=>equal(m.sampling[k],v)),'Unsupported alpha/sampling contract');
    check(Array.isArray(m.banks)&&m.banks.length===Math.ceil(m.spriteCount/m.layersPerBank),'Bank inventory mismatch');
    m.banks.forEach((bank,b)=>{
      keys(bank,['index','layerCount','levels']);
      const count=Math.min(m.layersPerBank,m.spriteCount-b*m.layersPerBank);
      check(bank.index===b&&bank.layerCount===count&&Array.isArray(bank.levels)&&bank.levels.length===levels,'Invalid bank dimensions');
      bank.levels.forEach((record,l)=>{
        keys(record,['level','size','file','byteLength','sha256']);const size=m.nativeSize>>l;
        check(record.level===l&&record.size===size&&record.byteLength===size*size*count*4&&hex(record.sha256)&&
          record.file===`levels/bank-${String(b).padStart(3,'0')}-mip-${String(l).padStart(2,'0')}.rgba`,'Invalid mip geometry/path');
      });
    });
    check(Array.isArray(m.sprites)&&m.sprites.length===m.spriteCount,'Sprite count mismatch');let previous='';
    m.sprites.forEach((s,i)=>{
      keys(s,['spriteKey','digestHex','family','palette','complexity','nativeSize','bankIndex','layerIndex',
        'sourceFile','sourceFileSha256','sourceRGBAsha256','levelSha256']);
      check(hex(s.digestHex)&&FAMILIES.includes(s.family)&&['neon','pastel','mono'].includes(s.palette)&&
        integer(s.complexity,1,8)&&s.nativeSize===m.nativeSize&&hex(s.sourceFileSha256)&&hex(s.sourceRGBAsha256)&&
        typeof s.spriteKey==='string'&&/^bfalpha1-[0-9a-f]{64}$/.test(s.spriteKey),'Invalid sprite identity');
      const order=[s.family,s.palette,s.complexity,s.digestHex].join('/');
      check(order>previous,'Duplicate/noncanonical sprite order');previous=order;
      check(s.bankIndex===Math.floor(i/m.layersPerBank)&&s.layerIndex===i%m.layersPerBank&&
        s.sourceFile===`assets/${s.family}-${s.palette}-c${s.complexity}/${s.digestHex}/${m.nativeSize}.png`,
        'Sprite source/placement mismatch');
      check(Array.isArray(s.levelSha256)&&s.levelSha256.length===levels&&s.levelSha256.every(hex),'Invalid layer mip hashes');
    });
    check(Array.isArray(m.viewerFiles)&&m.viewerFiles.length===4,'Viewer inventory mismatch');
    ['index.html','runtime.js','demo.js','demo.css'].forEach((name,i)=>{
      const f=m.viewerFiles[i];keys(f,['file','byteLength','sha256']);
      check(f.file===name&&integer(f.byteLength,1,256*1024)&&hex(f.sha256),'Invalid viewer record');
    });
    return m;
  }

  async function sha256(bytes) {
    check(global.crypto?.subtle,'Web Crypto requires HTTPS or loopback HTTP');
    const result=await global.crypto.subtle.digest('SHA-256',bytes);
    return Array.from(new Uint8Array(result),n=>n.toString(16).padStart(2,'0')).join('');
  }
  async function limitedFetch(url,maximum,signal) {
    const response=await fetch(url,{signal,credentials:'omit',redirect:'error',cache:'no-store'});
    check(response.ok&&response.body,`Asset HTTP failure: ${response.status}`);
    check(Number(response.headers.get('content-length')||0)<=maximum,'HTTP body budget exceeded');
    const reader=response.body.getReader(),parts=[];let total=0;
    try {for(;;){const part=await reader.read();if(part.done)break;total+=part.value.byteLength;
      check(total<=maximum,'HTTP body budget exceeded');parts.push(part.value);}}
    finally {await reader.cancel().catch(()=>{});reader.releaseLock();}
    const data=new Uint8Array(total);let at=0;for(const part of parts){data.set(part,at);at+=part.length;}return data;
  }
  function checkPixels(data) {
    for(let i=0;i<data.length;i+=4)check(data[i]<=data[i+3]&&data[i+1]<=data[i+3]&&data[i+2]<=data[i+3],
      'Invalid premultiplied pixel');
  }
  function freeze(value) {if(value&&typeof value==='object'){Object.values(value).forEach(freeze);Object.freeze(value);}return value;}
  async function loadBundle(baseURL,options={}) {
    const base=new URL(baseURL,global.location.href);
    check(['http:','https:'].includes(base.protocol)&&base.origin===global.location.origin&&!base.username&&
      !base.password&&!base.search&&!base.hash&&base.pathname.endsWith('/'),'Bundle must be a same-origin HTTP directory');
    const budget=options.maxTextureBytes??64*1024*1024;
    check(integer(budget,1024,128*1024*1024),'Invalid texture memory budget');
    if(options.manifestSha256!==undefined)check(hex(options.manifestSha256),'Invalid manifest pin');
    const bytes=await limitedFetch(new URL('manifest.json',base),16*1024*1024,options.signal),digest=await sha256(bytes);
    if(options.manifestSha256!==undefined)check(digest===options.manifestSha256,'Manifest checksum mismatch');
    const manifest=validateManifest(JSON.parse(new TextDecoder('utf-8',{fatal:true}).decode(bytes)));
    check(manifest.payloadBytes<=budget,'Texture memory budget exceeded');
    for(const s of manifest.sprites)check(s.spriteKey==='bfalpha1-'+await sha256(new TextEncoder().encode(
      JSON.stringify(identity(s),null,2)+'\n')),'Sprite identity checksum mismatch');
    const payload=[];
    try {
      for(const bank of manifest.banks){const levels=[];payload.push(levels);
        for(const record of bank.levels){const data=await limitedFetch(new URL(record.file,base),record.byteLength,options.signal);
          levels.push(data);check(data.length===record.byteLength&&await sha256(data)===record.sha256,'Mip file checksum mismatch');
          checkPixels(data);
          const length=record.size**2*4;
          for(let layer=0;layer<bank.layerCount;layer++){
            const sprite=manifest.sprites[bank.index*manifest.layersPerBank+layer];
            check(await sha256(data.subarray(layer*length,(layer+1)*length))===sprite.levelSha256[record.level],
              'Sprite layer checksum mismatch');
          }
          if(options.signal?.aborted)throw new Error('Texture load aborted');
        }
      }
      freeze(manifest);
    } catch(error){payload.flat().forEach(a=>a.fill(0));throw error;}
    const state={payload,disposed:false};
    const bundle=Object.freeze({manifest,manifestSha256:digest,get disposed(){return state.disposed;},
      dispose(){if(!state.disposed){state.payload.flat().forEach(a=>a.fill(0));state.payload=[];state.disposed=true;}}});
    bundles.set(bundle,state);return bundle;
  }
  async function fromLevels(manifestBytes, levels, options={}) {
    // A transport adapter cannot bypass the original hashes, bounds or alpha rules.
    check(manifestBytes instanceof Uint8Array&&manifestBytes.length<=16*1024*1024,'Invalid manifest bytes');
    const bytes=new Uint8Array(manifestBytes),manifest=validateManifest(JSON.parse(new TextDecoder('utf-8',{fatal:true}).decode(bytes)));
    const budget=options.maxTextureBytes??64*1024*1024;
    check(integer(budget,1024,128*1024*1024)&&manifest.payloadBytes<=budget,'Texture memory budget exceeded');
    if(options.manifestSha256!==undefined)check(hex(options.manifestSha256),'Invalid manifest pin');
    check(Array.isArray(levels)&&levels.length===manifest.banks.length,'Bank payload count mismatch');
    // Validate every length BEFORE copying. No asynchronous suspension until all
    // caller-owned arrays have been snapshotted; later mutation cannot affect GPU data.
    manifest.banks.forEach((b,i)=>{check(Array.isArray(levels[i])&&levels[i].length===manifest.levelCount,'Mip payload count mismatch');
      b.levels.forEach((r,l)=>check(levels[i][l] instanceof Uint8Array&&levels[i][l].length===r.byteLength,'Mip payload length mismatch'));});
    const payload=levels.map(bank=>bank.map(data=>new Uint8Array(data)));
    try {
      const digest=await sha256(bytes);
      if(options.manifestSha256!==undefined)check(digest===options.manifestSha256,'Manifest checksum mismatch');
      for(const s of manifest.sprites)check(s.spriteKey==='bfalpha1-'+await sha256(new TextEncoder().encode(
        JSON.stringify(identity(s),null,2)+'\n')),'Sprite identity checksum mismatch');
      for(const bank of manifest.banks)for(const record of bank.levels){
        if(options.signal?.aborted)throw new Error('Texture load aborted');
        const data=payload[bank.index][record.level];
        check(await sha256(data)===record.sha256,'Mip file checksum mismatch');checkPixels(data);
        const length=record.size**2*4;
        for(let layer=0;layer<bank.layerCount;layer++)check(await sha256(data.subarray(layer*length,(layer+1)*length))===
          manifest.sprites[bank.index*manifest.layersPerBank+layer].levelSha256[record.level],'Sprite layer checksum mismatch');
      }
      if(options.signal?.aborted)throw new Error('Texture load aborted');
      freeze(manifest);const state={payload,disposed:false};
      const bundle=Object.freeze({manifest,manifestSha256:digest,get disposed(){return state.disposed;},
        dispose(){if(!state.disposed){state.payload.flat().forEach(a=>a.fill(0));state.payload=[];state.disposed=true;}}});
      bundles.set(bundle,state);return bundle;
    } catch(error){payload.flat().forEach(a=>a.fill(0));throw error;}
  }
  function lookup(manifest,{digestHex,family,palette='neon',complexity=4}) {
    check(hex(digestHex),'Full identity digest required');
    const i=manifest.sprites.findIndex(s=>s.digestHex===digestHex&&s.family===family&&s.palette===palette&&s.complexity===complexity);
    check(i>=0,'Identity/style absent from bundle');return i;
  }
  function makeGrid(manifest,count=1000,columns=40,displaySize=manifest.nativeSize) {
    check(integer(count,1,10000)&&integer(columns,1,100)&&integer(displaySize,1,512),'Invalid grid workload');
    const width=columns*displaySize,height=Math.ceil(count/columns)*displaySize;canvasBounds(width,height);
    return {width,height,instances:Array.from({length:count},(_,i)=>({spriteIndex:i%manifest.spriteCount,
      x:i%columns*displaySize,y:Math.floor(i/columns)*displaySize,width:displaySize,height:displaySize}))};
  }
  function canvasBounds(w,h) {check(integer(w,1,8192)&&integer(h,1,8192)&&w*h<=16777216,'Canvas pixel budget exceeded');}
  function runs(manifest,instances,width,height) {
    canvasBounds(width,height);check(Array.isArray(instances)&&instances.length<=10000,'Instance budget exceeded');const result=[];
    for(const p of instances){check(p&&integer(p.spriteIndex,0,manifest.spriteCount-1)&&integer(p.x,0,width)&&integer(p.y,0,height)&&
      integer(p.width,1,width)&&integer(p.height,1,height)&&p.x+p.width<=width&&p.y+p.height<=height,'Invalid sprite instance');
      const opacity=p.opacity??1,lod=p.lod??Math.max(0,Math.min(manifest.levelCount-1,Math.log2(manifest.nativeSize/Math.max(p.width,p.height))));
      check(Number.isFinite(lod)&&lod>=0&&lod<=manifest.levelCount-1&&Number.isFinite(opacity)&&opacity>=0&&opacity<=1,'Invalid LOD/opacity');
      const s=manifest.sprites[p.spriteIndex];let batch=result[result.length-1];
      if(!batch||batch.bankIndex!==s.bankIndex){batch={bankIndex:s.bankIndex,items:[]};result.push(batch);}
      batch.items.push({x:p.x,y:p.y,width:p.width,height:p.height,layerIndex:s.layerIndex,lod,opacity});
    }return result; // Never sort by texture: overlap order is meaningful.
  }
  const VERTEX=`#version 300 es
precision highp float;
layout(location=0) in vec2 corner;
layout(location=1) in vec4 destination;
layout(location=2) in vec3 selection;
uniform vec2 viewport;
out vec2 uv;
flat out vec3 chosen;
void main(){vec2 p=destination.xy+corner*destination.zw;gl_Position=vec4(p.x/viewport.x*2.-1.,1.-p.y/viewport.y*2.,0.,1.);uv=corner;chosen=selection;}`;
  const FRAGMENT=`#version 300 es
precision highp float;
precision highp sampler2DArray;
in vec2 uv;
flat in vec3 chosen;
uniform sampler2DArray sprites;
out vec4 color;
void main(){color=textureLod(sprites,vec3(uv,chosen.x),chosen.y)*chosen.z;}`;

  class WebGLArray {
    constructor(canvas,bundle,{filter='nearest'}={}) {
      const state=bundles.get(bundle);check(state&&!state.disposed,'Verified live bundle required');
      check(['nearest','linear-mipmap-linear'].includes(filter),'Unsupported sampling filter');
      this.canvas=canvas;this.bundle=bundle;this.closed=false;this.lost=false;this.textures=[];this.buffers=[];this.shaders=[];
      const gl=canvas.getContext('webgl2',{alpha:true,premultipliedAlpha:true,antialias:false,depth:false,stencil:false});
      check(gl,'WebGL2 unavailable; no silent opaque or CPU fallback');this.gl=gl;
      try {
        const m=bundle.manifest;
        check(m.nativeSize<=gl.getParameter(gl.MAX_TEXTURE_SIZE)&&m.banks.every(b=>b.layerCount<=gl.getParameter(gl.MAX_ARRAY_TEXTURE_LAYERS)),
          'Device texture-array limits exceeded');
        const shader=(type,code)=>{const s=gl.createShader(type);check(s,'Shader allocation failed');this.shaders.push(s);
          gl.shaderSource(s,code);gl.compileShader(s);check(gl.getShaderParameter(s,gl.COMPILE_STATUS),gl.getShaderInfoLog(s));return s;};
        this.program=gl.createProgram();check(this.program,'Program allocation failed');
        gl.attachShader(this.program,shader(gl.VERTEX_SHADER,VERTEX));gl.attachShader(this.program,shader(gl.FRAGMENT_SHADER,FRAGMENT));
        gl.linkProgram(this.program);check(gl.getProgramParameter(this.program,gl.LINK_STATUS),gl.getProgramInfoLog(this.program));
        this.vao=gl.createVertexArray();check(this.vao,'VAO allocation failed');gl.bindVertexArray(this.vao);
        const buffer=()=>{const b=gl.createBuffer();check(b,'Buffer allocation failed');this.buffers.push(b);gl.bindBuffer(gl.ARRAY_BUFFER,b);return b;};
        buffer();gl.bufferData(gl.ARRAY_BUFFER,new Float32Array([0,0,1,0,0,1,0,1,1,0,1,1]),gl.STATIC_DRAW);
        gl.enableVertexAttribArray(0);gl.vertexAttribPointer(0,2,gl.FLOAT,false,0,0);
        this.instances=buffer();gl.enableVertexAttribArray(1);gl.vertexAttribPointer(1,4,gl.FLOAT,false,28,0);gl.vertexAttribDivisor(1,1);
        gl.enableVertexAttribArray(2);gl.vertexAttribPointer(2,3,gl.FLOAT,false,28,16);gl.vertexAttribDivisor(2,1);
        gl.pixelStorei(gl.UNPACK_ALIGNMENT,1);gl.pixelStorei(gl.UNPACK_FLIP_Y_WEBGL,false);
        gl.pixelStorei(gl.UNPACK_PREMULTIPLY_ALPHA_WEBGL,false);gl.pixelStorei(gl.UNPACK_COLORSPACE_CONVERSION_WEBGL,gl.NONE);
        for(const bank of m.banks){const t=gl.createTexture();check(t,'Texture allocation failed');this.textures.push(t);
          gl.bindTexture(gl.TEXTURE_2D_ARRAY,t);
          gl.texStorage3D(gl.TEXTURE_2D_ARRAY,m.levelCount,gl.RGBA8,m.nativeSize,m.nativeSize,bank.layerCount);
          for(const record of bank.levels)gl.texSubImage3D(gl.TEXTURE_2D_ARRAY,record.level,0,0,0,record.size,record.size,bank.layerCount,
            gl.RGBA,gl.UNSIGNED_BYTE,state.payload[bank.index][record.level]);
          gl.texParameteri(gl.TEXTURE_2D_ARRAY,gl.TEXTURE_MIN_FILTER,filter==='nearest'?gl.NEAREST_MIPMAP_NEAREST:gl.LINEAR_MIPMAP_LINEAR);
          gl.texParameteri(gl.TEXTURE_2D_ARRAY,gl.TEXTURE_MAG_FILTER,filter==='nearest'?gl.NEAREST:gl.LINEAR);
          for(const axis of [gl.TEXTURE_WRAP_S,gl.TEXTURE_WRAP_T,gl.TEXTURE_WRAP_R])gl.texParameteri(gl.TEXTURE_2D_ARRAY,axis,gl.CLAMP_TO_EDGE);
          gl.texParameteri(gl.TEXTURE_2D_ARRAY,gl.TEXTURE_MAX_LEVEL,m.levelCount-1);
          check(gl.getError()===gl.NO_ERROR,'Texture-array upload failed');
        }
        this.onLost=e=>{e.preventDefault();this.lost=true;};canvas.addEventListener('webglcontextlost',this.onLost);
      } catch(error){this.dispose();throw error;}
    }
    draw(instances,{background=[0,0,0,0]}={}) {
      check(!this.closed&&!this.lost&&!this.bundle.disposed&&!this.gl.isContextLost(),'Texture context lost or disposed');
      check(Array.isArray(background)&&background.length===4&&background.every(n=>integer(n,0,255)),'Invalid clear colour');
      const {gl,canvas,bundle}=this,batches=runs(bundle.manifest,instances,canvas.width,canvas.height),start=performance.now();
      gl.viewport(0,0,canvas.width,canvas.height);gl.disable(gl.DEPTH_TEST);gl.disable(gl.DITHER);gl.disable(gl.SCISSOR_TEST);gl.disable(gl.CULL_FACE);
      gl.colorMask(true,true,true,true);gl.enable(gl.BLEND);gl.blendEquationSeparate(gl.FUNC_ADD,gl.FUNC_ADD);
      gl.blendFuncSeparate(gl.ONE,gl.ONE_MINUS_SRC_ALPHA,gl.ONE,gl.ONE_MINUS_SRC_ALPHA);
      const alpha=background[3]/255;gl.clearColor(background[0]/255*alpha,background[1]/255*alpha,background[2]/255*alpha,alpha);
      gl.clear(gl.COLOR_BUFFER_BIT);gl.useProgram(this.program);gl.bindVertexArray(this.vao);
      gl.uniform2f(gl.getUniformLocation(this.program,'viewport'),canvas.width,canvas.height);
      gl.uniform1i(gl.getUniformLocation(this.program,'sprites'),0);gl.activeTexture(gl.TEXTURE0);
      for(const batch of batches){const data=new Float32Array(batch.items.length*7);
        batch.items.forEach((p,i)=>data.set([p.x,p.y,p.width,p.height,p.layerIndex,p.lod,p.opacity],i*7));
        gl.bindTexture(gl.TEXTURE_2D_ARRAY,this.textures[batch.bankIndex]);gl.bindBuffer(gl.ARRAY_BUFFER,this.instances);
        gl.bufferData(gl.ARRAY_BUFFER,data,gl.DYNAMIC_DRAW);gl.drawArraysInstanced(gl.TRIANGLES,0,6,batch.items.length);}
      check(gl.getError()===gl.NO_ERROR,'WebGL array draw failed');
      return {backend:'webgl2-array',instances:instances.length,drawCalls:batches.length,payloadBytes:bundle.manifest.payloadBytes,
        submitMilliseconds:performance.now()-start};
    }
    readPixels() {
      check(!this.closed&&!this.lost&&!this.bundle.disposed&&!this.gl.isContextLost(),'Texture context lost or disposed');
      const {gl,canvas}=this;canvasBounds(canvas.width,canvas.height);const row=canvas.width*4,data=new Uint8Array(row*canvas.height);
      gl.readPixels(0,0,canvas.width,canvas.height,gl.RGBA,gl.UNSIGNED_BYTE,data);check(gl.getError()===gl.NO_ERROR,'Readback failed');
      const top=new Uint8Array(data.length);for(let y=0;y<canvas.height;y++)top.set(data.subarray(y*row,(y+1)*row),(canvas.height-1-y)*row);
      return top; // Top-left, premultiplied bytes. NOT unassociated Canvas pixels.
    }
    dispose(){if(this.closed)return;this.closed=true;const gl=this.gl;if(!gl)return;
      if(this.onLost)this.canvas.removeEventListener('webglcontextlost',this.onLost);
      this.textures.forEach(t=>gl.deleteTexture(t));this.buffers.forEach(b=>gl.deleteBuffer(b));this.shaders.forEach(s=>gl.deleteShader(s));
      if(this.vao)gl.deleteVertexArray(this.vao);if(this.program)gl.deleteProgram(this.program);}
  }
  global.ByteFablesAlphaTextures=Object.freeze({validateManifest,sha256,loadBundle,fromLevels,lookup,makeGrid,runs,WebGLArray});
})(globalThis);
