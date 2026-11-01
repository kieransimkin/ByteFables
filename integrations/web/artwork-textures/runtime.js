/* PUBLIC pre-rendered texture consumer. No artwork generation, effects or telemetry. */
(function (global) {
  'use strict';
  const SCHEMA = 'bytefables.artwork-texture-bundle.v1';
  const FAMILIES = ['sigil','constellation','heraldry','topography','crystal','mandala','cellular','branching','orbital'];
  const HEX = /^[0-9a-f]{64}$/;
  const check = (yes, message) => { if (!yes) throw new Error(message); };
  const integer = (n, lo, hi) => Number.isSafeInteger(n) && n >= lo && n <= hi;
  const same = (a, b) => Array.isArray(a) && a.length === b.length && a.every((v, i) => v === b[i]);
  const sortKey = s => [s.family, s.palette, s.complexity, s.digestHex].join('/');
  const identity = s => ({profile:'bytefables.texture-layout.v1', digestHex:s.digestHex,
    family:s.family, palette:s.palette, complexity:s.complexity, nativeSize:s.nativeSize, rgbaSha256:s.rgbaSha256});

  function validateManifest(m) {
    check(m && m.schema === SCHEMA && m.profile === 'bytefables.texture-layout.v1' &&
      m.status === 'passed' && m.publicOnly === true && m.guarantee === 'presentation-only' &&
      m.resampled === false && HEX.test(m.sourceManifestSha256), 'Invalid PUBLIC texture manifest');
    check([16,32,64,128].includes(m.nativeSize) && integer(m.pageSize,64,4096) &&
      !(m.pageSize & (m.pageSize-1)) && integer(m.padding,1,16) && integer(m.spriteCount,1,8192), 'Invalid texture dimensions');
    const pitch = m.nativeSize + 2*m.padding, columns = Math.floor(m.pageSize/pitch), capacity = columns**2;
    check(columns > 0, 'Sprite does not fit page');
    const pageCount = Math.ceil(m.spriteCount/capacity);
    check(pageCount <= 128 && pageCount*m.pageSize**2 <= 67108864 &&
      Array.isArray(m.pages) && m.pages.length === pageCount &&
      Array.isArray(m.sprites) && m.sprites.length === m.spriteCount, 'Texture inventory/budget mismatch');
    const sampling = m.sampling;
    check(sampling && sampling.origin === 'top-left' && sampling.wrap === 'clamp-to-edge' &&
      sampling.mipmaps === false && same(sampling.filters,['nearest','linear']) &&
      sampling.colourConversion === 'none' && sampling.premultipliedAlpha === false, 'Unsupported texture sampling contract');
    m.pages.forEach((p, i) => check(p && p.index === i && p.file === `pages/page-${String(i).padStart(3,'0')}.png` &&
      p.width === m.pageSize && p.height === m.pageSize && integer(p.byteLength,57,Math.min(67108864,m.pageSize**2*5+65536)) &&
      HEX.test(p.sha256) && HEX.test(p.rgbaSha256) &&
      p.spriteCount === Math.min(capacity,m.spriteCount-i*capacity), 'Invalid texture page'));
    let previous = '';
    m.sprites.forEach((s, i) => {
      check(s && HEX.test(s.digestHex) && FAMILIES.includes(s.family) && ['mono','neon','pastel'].includes(s.palette) &&
        integer(s.complexity,1,8) && s.nativeSize === m.nativeSize && HEX.test(s.rgbaSha256) &&
        HEX.test(s.sourceFileSha256) && /^bftexture1-[0-9a-f]{64}$/.test(s.spriteKey), 'Invalid sprite identity');
      check(s.sourceFile === `assets/${s.family}-${s.palette}-c${s.complexity}/${s.digestHex}/${m.nativeSize}.png`, 'Invalid source path');
      const key = sortKey(s); check(key > previous, 'Noncanonical or duplicate sprite order'); previous = key;
      const cell = i%capacity, x = cell%columns*pitch+m.padding, y = Math.floor(cell/columns)*pitch+m.padding;
      check(s.pageIndex === Math.floor(i/capacity) && same(s.rect,[x,y,x+m.nativeSize,y+m.nativeSize]) &&
        same(s.uvTopLeft,[x/m.pageSize,y/m.pageSize,(x+m.nativeSize)/m.pageSize,(y+m.nativeSize)/m.pageSize]) &&
        same(s.uvBottomLeft,[x/m.pageSize,1-(y+m.nativeSize)/m.pageSize,(x+m.nativeSize)/m.pageSize,1-y/m.pageSize]),
        'Sprite geometry/UV mismatch');
    });
    return m;
  }

  async function sha256(bytes) {
    check(global.crypto && global.crypto.subtle, 'Web Crypto requires HTTPS or loopback HTTP');
    const digest = await global.crypto.subtle.digest('SHA-256', bytes);
    return Array.from(new Uint8Array(digest), b=>b.toString(16).padStart(2,'0')).join('');
  }

  async function limitedFetch(url, maximum, signal) {
    const response = await fetch(url, {signal, credentials:'omit', redirect:'error', cache:'no-store'});
    check(response.ok, `Asset HTTP failure: ${response.status}`);
    check(Number(response.headers.get('content-length') || 0) <= maximum, 'HTTP body budget exceeded');
    check(response.body, 'Streaming response is required');
    const reader = response.body.getReader(), parts = []; let total = 0;
    try {
      for (;;) {
        const part = await reader.read(); if (part.done) break;
        total += part.value.byteLength;
        check(total <= maximum, 'HTTP body budget exceeded'); parts.push(part.value);
      }
    } finally { await reader.cancel().catch(()=>{}); reader.releaseLock(); }
    const output = new Uint8Array(total); let at = 0;
    for (const part of parts) { output.set(part,at); at += part.length; }
    return output;
  }

  async function loadBundle(baseURL, options = {}) {
    const base = new URL(baseURL, global.location.href);
    check(['http:','https:'].includes(base.protocol) && base.origin === global.location.origin &&
      !base.username && !base.password && !base.search && !base.hash && base.pathname.endsWith('/'),
      'Bundle must be a same-origin HTTP directory');
    const budget = options.maxTextureBytes ?? 64*1024*1024;
    check(integer(budget,16384,256*1024*1024), 'Invalid texture memory budget');
    if (options.manifestSha256 !== undefined) check(HEX.test(options.manifestSha256), 'Invalid manifest pin');
    const data = await limitedFetch(new URL('manifest.json',base),16*1024*1024,options.signal);
    const manifestHash = await sha256(data);
    if (options.manifestSha256 !== undefined) check(manifestHash === options.manifestSha256, 'Manifest checksum mismatch');
    const manifest = validateManifest(JSON.parse(new TextDecoder('utf-8',{fatal:true}).decode(data)));
    check(manifest.pages.length*manifest.pageSize**2*4 <= budget, 'Texture memory budget exceeded');
    // Geometry is validated synchronously; identity-to-pixel keys are checked here.
    for (const s of manifest.sprites) {
      const key = await sha256(new TextEncoder().encode(JSON.stringify(identity(s),null,2)+'\n'));
      check(s.spriteKey === 'bftexture1-'+key, 'Sprite identity/pixel checksum mismatch');
    }
    const images = [];
    try {
      for (const page of manifest.pages) {
        const png = await limitedFetch(new URL(page.file,base),page.byteLength,options.signal);
        check(png.length === page.byteLength && await sha256(png) === page.sha256, 'Texture file checksum mismatch');
        const bitmap = await createImageBitmap(new Blob([png],{type:'image/png'}),
          {premultiplyAlpha:'none',colorSpaceConversion:'none',imageOrientation:'none'});
        images.push(bitmap);
        check(bitmap.width === page.width && bitmap.height === page.height, 'Decoded texture dimensions mismatch');
        const c = document.createElement('canvas'); c.width=page.width; c.height=page.height;
        const ctx=c.getContext('2d',{willReadFrequently:true}); check(ctx,'Canvas readback unavailable');
        ctx.drawImage(bitmap,0,0);
        const pixels=ctx.getImageData(0,0,c.width,c.height).data;
        check(await sha256(pixels) === page.rgbaSha256, 'Decoded texture page checksum mismatch');
        c.width=1; c.height=1;
        if (options.signal?.aborted) throw new Error('Texture load aborted');
      }
    } catch(error) { images.forEach(im=>im.close()); throw error; }
    const freeze = x => { if (x && typeof x === 'object') { Object.values(x).forEach(freeze); Object.freeze(x); } return x; };
    try { freeze(manifest); } catch(error) { images.forEach(im=>im.close()); throw error; }
    let disposed = false;
    return {manifest, manifestSha256:manifestHash, images:Object.freeze(images),
      get disposed(){return disposed;}, dispose(){if (!disposed) images.forEach(im=>im.close()); disposed=true;}};
  }

  function lookup(manifest, selection) {
    const {digestHex,family,palette='neon',complexity=4} = selection;
    check(HEX.test(digestHex), 'Full identity digest required');
    const index = manifest.sprites.findIndex(s=>s.digestHex===digestHex && s.family===family && s.palette===palette && s.complexity===complexity);
    check(index >= 0, 'Identity/style is absent from texture bundle'); return index;
  }

  function makeGrid(manifest, count=1000, columns=40, displaySize=manifest.nativeSize) {
    check(integer(count,1,10000) && integer(columns,1,100) && integer(displaySize,1,512), 'Invalid grid workload');
    const width=columns*displaySize, height=Math.ceil(count/columns)*displaySize;
    check(width<=8192 && height<=8192 && width*height<=16777216, 'Canvas pixel budget exceeded');
    return {width,height,instances:Array.from({length:count},(_,i)=>({spriteIndex:i%manifest.sprites.length,
      x:(i%columns)*displaySize,y:Math.floor(i/columns)*displaySize,width:displaySize,height:displaySize}))};
  }

  function runs(manifest, instances, width, height) {
    check(integer(width,1,8192)&&integer(height,1,8192)&&width*height<=16777216, 'Canvas pixel budget exceeded');
    check(Array.isArray(instances)&&instances.length<=10000, 'Instance budget exceeded');
    const output=[];
    for (const item of instances) {
      check(item && integer(item.spriteIndex,0,manifest.sprites.length-1) &&
        integer(item.x,0,width)&&integer(item.y,0,height)&&integer(item.width,1,width)&&integer(item.height,1,height)&&
        item.x+item.width<=width&&item.y+item.height<=height, 'Invalid sprite instance');
      const s=manifest.sprites[item.spriteIndex]; let run=output[output.length-1];
      if (!run || run.pageIndex!==s.pageIndex) {run={pageIndex:s.pageIndex,items:[]};output.push(run);}
      run.items.push(item);
    }
    return output; // Contiguous runs preserve painter order for overlapping sprites.
  }

  class CanvasAtlas {
    constructor(canvas,bundle,{filter='nearest'}={}) {
      check(['nearest','linear'].includes(filter), 'Unsupported filter');
      check(bundle && !bundle.disposed, 'Texture bundle is disposed');
      validateManifest(bundle.manifest);
      check(Array.isArray(bundle.images) && bundle.images.length === bundle.manifest.pages.length, 'Texture image inventory mismatch');
      this.canvas=canvas;this.bundle=bundle;this.filter=filter;this.closed=false;
      this.ctx=canvas.getContext('2d');check(this.ctx,'Canvas2D unavailable');
    }
    draw(instances) {
      check(!this.closed&&!this.bundle.disposed,'Texture consumer is disposed');
      const {canvas,ctx,bundle}=this; runs(bundle.manifest,instances,canvas.width,canvas.height);
      const start=performance.now();ctx.clearRect(0,0,canvas.width,canvas.height);ctx.imageSmoothingEnabled=this.filter==='linear';
      for(const item of instances){const s=bundle.manifest.sprites[item.spriteIndex],r=s.rect;
        ctx.drawImage(bundle.images[s.pageIndex],r[0],r[1],r[2]-r[0],r[3]-r[1],item.x,item.y,item.width,item.height);}
      return {backend:'canvas2d',instances:instances.length,drawCalls:instances.length,submitMilliseconds:performance.now()-start};
    }
    dispose(){this.closed=true;}
  }

  const VERTEX=`#version 300 es
  in vec2 corner; in vec4 destination; in vec4 sourceUV;
  uniform vec2 viewport; out vec2 uv;
  void main(){vec2 p=destination.xy+corner*destination.zw;
    gl_Position=vec4(p.x/viewport.x*2.0-1.0,1.0-p.y/viewport.y*2.0,0,1);
    uv=mix(sourceUV.xy,sourceUV.zw,corner);}`;
  const FRAGMENT=`#version 300 es
  precision highp float; uniform sampler2D atlas; in vec2 uv; out vec4 colour;
  void main(){colour=texture(atlas,uv);}`;

  class WebGLAtlas {
    constructor(canvas,bundle,{filter='nearest'}={}) {
      check(['nearest','linear'].includes(filter), 'Unsupported filter');
      check(bundle && !bundle.disposed, 'Texture bundle is disposed');
      validateManifest(bundle.manifest);
      check(Array.isArray(bundle.images) && bundle.images.length === bundle.manifest.pages.length, 'Texture image inventory mismatch');
      this.canvas=canvas;this.bundle=bundle;this.closed=false;this.lost=false;this.textures=[];this.buffers=[];this.shaders=[];
      const gl=canvas.getContext('webgl2',{alpha:true,antialias:false,premultipliedAlpha:false});
      check(gl,'WebGL2 unavailable; use a separate canvas for Canvas2D fallback');this.gl=gl;
      try {
        check(bundle.manifest.pageSize<=gl.getParameter(gl.MAX_TEXTURE_SIZE),'Device texture size limit exceeded');
        const compile=(type,text)=>{const s=gl.createShader(type);check(s,'Shader allocation failed');this.shaders.push(s);
          gl.shaderSource(s,text);gl.compileShader(s);check(gl.getShaderParameter(s,gl.COMPILE_STATUS),gl.getShaderInfoLog(s));return s;};
        this.program=gl.createProgram();check(this.program,'Program allocation failed');
        gl.attachShader(this.program,compile(gl.VERTEX_SHADER,VERTEX));gl.attachShader(this.program,compile(gl.FRAGMENT_SHADER,FRAGMENT));
        gl.linkProgram(this.program);check(gl.getProgramParameter(this.program,gl.LINK_STATUS),gl.getProgramInfoLog(this.program));
        this.vao=gl.createVertexArray();check(this.vao,'Vertex array allocation failed');gl.bindVertexArray(this.vao);
        const buffer=()=>{const b=gl.createBuffer();check(b,'Buffer allocation failed');this.buffers.push(b);gl.bindBuffer(gl.ARRAY_BUFFER,b);return b;};
        buffer();gl.bufferData(gl.ARRAY_BUFFER,new Float32Array([0,0,1,0,0,1,0,1,1,0,1,1]),gl.STATIC_DRAW);
        const corner=gl.getAttribLocation(this.program,'corner');gl.enableVertexAttribArray(corner);gl.vertexAttribPointer(corner,2,gl.FLOAT,false,0,0);
        this.instances=buffer();
        for(const [name,offset] of [['destination',0],['sourceUV',16]]){const a=gl.getAttribLocation(this.program,name);
          gl.enableVertexAttribArray(a);gl.vertexAttribPointer(a,4,gl.FLOAT,false,32,offset);gl.vertexAttribDivisor(a,1);}
        gl.pixelStorei(gl.UNPACK_FLIP_Y_WEBGL,false);gl.pixelStorei(gl.UNPACK_PREMULTIPLY_ALPHA_WEBGL,false);
        gl.pixelStorei(gl.UNPACK_COLORSPACE_CONVERSION_WEBGL,gl.NONE);
        for(const image of bundle.images){const texture=gl.createTexture();check(texture,'Texture allocation failed');this.textures.push(texture);
          gl.bindTexture(gl.TEXTURE_2D,texture);gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_MIN_FILTER,filter==='linear'?gl.LINEAR:gl.NEAREST);
          gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_MAG_FILTER,filter==='linear'?gl.LINEAR:gl.NEAREST);
          gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_WRAP_S,gl.CLAMP_TO_EDGE);gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_WRAP_T,gl.CLAMP_TO_EDGE);
          gl.texImage2D(gl.TEXTURE_2D,0,gl.RGBA8,gl.RGBA,gl.UNSIGNED_BYTE,image);}
        check(gl.getError()===gl.NO_ERROR,'WebGL upload failed');
        this.onLost=e=>{e.preventDefault();this.lost=true;};canvas.addEventListener('webglcontextlost',this.onLost);
      }catch(error){this.dispose();throw error;}
    }
    draw(instances) {
      check(!this.closed&&!this.lost&&!this.bundle.disposed,'Texture context is lost or disposed');
      const {gl,canvas,bundle}=this, batches=runs(bundle.manifest,instances,canvas.width,canvas.height),start=performance.now();
      gl.viewport(0,0,canvas.width,canvas.height);gl.disable(gl.BLEND);gl.disable(gl.DEPTH_TEST);gl.disable(gl.DITHER);gl.disable(gl.SCISSOR_TEST);
      gl.clearColor(0,0,0,0);gl.clear(gl.COLOR_BUFFER_BIT);gl.useProgram(this.program);gl.bindVertexArray(this.vao);
      gl.uniform2f(gl.getUniformLocation(this.program,'viewport'),canvas.width,canvas.height);gl.uniform1i(gl.getUniformLocation(this.program,'atlas'),0);
      gl.activeTexture(gl.TEXTURE0);
      for(const run of batches){const values=new Float32Array(run.items.length*8);
        run.items.forEach((p,i)=>values.set([p.x,p.y,p.width,p.height,...bundle.manifest.sprites[p.spriteIndex].uvTopLeft],i*8));
        gl.bindTexture(gl.TEXTURE_2D,this.textures[run.pageIndex]);gl.bindBuffer(gl.ARRAY_BUFFER,this.instances);
        gl.bufferData(gl.ARRAY_BUFFER,values,gl.DYNAMIC_DRAW);gl.drawArraysInstanced(gl.TRIANGLES,0,6,run.items.length);}
      check(gl.getError()===gl.NO_ERROR,'WebGL draw failed');
      return {backend:'webgl2',instances:instances.length,drawCalls:batches.length,submitMilliseconds:performance.now()-start};
    }
    dispose(){if(this.closed)return;this.closed=true;const gl=this.gl;if(!gl)return;
      if(this.onLost)this.canvas.removeEventListener('webglcontextlost',this.onLost);
      this.textures.forEach(t=>gl.deleteTexture(t));this.buffers.forEach(b=>gl.deleteBuffer(b));this.shaders.forEach(s=>gl.deleteShader(s));
      if(this.vao)gl.deleteVertexArray(this.vao);if(this.program)gl.deleteProgram(this.program);}
  }
  global.ByteFablesTextures=Object.freeze({validateManifest,loadBundle,lookup,makeGrid,runs,CanvasAtlas,WebGLAtlas});
})(globalThis);
