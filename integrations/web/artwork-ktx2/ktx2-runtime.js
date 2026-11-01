/* Strict ByteFables KTX2 transport adapter; procedural rendering remains in the native host. */
(function(global) {
  'use strict';
  const PROFILE='bytefables.ktx2-rgba8-array.v1',SCHEMA='bytefables.ktx2-alpha-bundle.v1';
  const api=global.ByteFablesAlphaTextures;
  if(!api?.fromLevels)throw new Error('Load the current trusted alpha-runtime.js before KTX2 transport');
  const check=(yes,message)=>{if(!yes)throw new Error(message);};
  const integer=(x,lo,hi)=>Number.isSafeInteger(x)&&x>=lo&&x<=hi;
  const hex=x=>typeof x==='string'&&/^[0-9a-f]{64}$/.test(x);
  const keys=(o,names)=>check(o&&typeof o==='object'&&!Array.isArray(o)&&Object.keys(o).length===names.length&&
    names.every(k=>Object.prototype.hasOwnProperty.call(o,k)),'Unexpected KTX2 manifest fields');
  const equal=(a,b)=>a.length===b.length&&a.every((n,i)=>n===b[i]);
  const magic=Uint8Array.of(171,75,84,88,32,50,48,187,13,10,26,10);
  function descriptor(){
    const data=new Uint8Array(92),v=new DataView(data.buffer);
    v.setUint32(0,92,true);v.setUint16(8,2,true);v.setUint16(10,88,true);
    data.set([1,0,1,1],12);data[20]=4;
    [0,1,2,15].forEach((channel,i)=>{const at=28+i*16;v.setUint16(at,i*8,true);data[at+2]=7;data[at+3]=channel;v.setUint32(at+12,255,true);});
    return data;
  }
  function metadata(){
    const parts=[];let length=0;
    for(const [key,value] of [['KTXorientation','rd'],['KTXwriter','ByteFables KTX2 transport v1'],['org.bytefables.profile',PROFILE]]){
      const bytes=new TextEncoder().encode(`${key}\0${value}\0`),part=new Uint8Array(4+Math.ceil(bytes.length/4)*4);
      new DataView(part.buffer).setUint32(0,bytes.length,true);part.set(bytes,4);parts.push(part);length+=part.length;
    }
    const data=new Uint8Array(length);let at=0;for(const p of parts){data.set(p,at);at+=p.length;}return data;
  }
  const dfd=descriptor(),kvd=metadata();
  function lengthFor(size,layers){
    check([16,32,64,128].includes(size)&&integer(layers,1,256),'Invalid KTX2 array dimensions');
    const count=Math.log2(size)+1;
    return 80+24*count+dfd.length+kvd.length+Array.from({length:count},(_,l)=>(size>>l)**2*layers*4).reduce((a,b)=>a+b,0);
  }
  function decode(bytes){
    check(bytes instanceof Uint8Array&&bytes.length>=80&&bytes.length<=32*1024*1024&&equal(bytes.subarray(0,12),magic),'Invalid KTX2 container');
    const v=new DataView(bytes.buffer,bytes.byteOffset,bytes.byteLength),u32=n=>v.getUint32(n,true);
    const u64=n=>{const value=v.getBigUint64(n,true);check(value<=BigInt(Number.MAX_SAFE_INTEGER),'Unsafe KTX2 64-bit field');return Number(value);};
    const size=u32(20),layers=u32(32),count=Math.log2(size)+1;
    check(bytes.length===lengthFor(size,layers),'KTX2 truncated or trailing data');
    check(u32(12)===37&&u32(16)===1&&u32(24)===size&&u32(28)===0&&u32(36)===1&&u32(40)===count&&
      u32(44)===0&&u64(64)===0&&u64(72)===0,'Unsupported KTX2 format/alpha-array profile');
    const dfdAt=80+24*count,kvdAt=dfdAt+dfd.length;
    check(u32(48)===dfdAt&&u32(52)===dfd.length&&u32(56)===kvdAt&&u32(60)===kvd.length,'Invalid KTX2 descriptor offsets');
    check(equal(bytes.subarray(dfdAt,kvdAt),dfd)&&equal(bytes.subarray(kvdAt,kvdAt+kvd.length),kvd),'KTX2 alpha/colour/orientation mismatch');
    let cursor=kvdAt+kvd.length;const levels=new Array(count);
    for(let level=count-1;level>=0;level--){const at=80+level*24,length=(size>>level)**2*layers*4;
      check(u64(at)===cursor&&u64(at+8)===length&&u64(at+16)===length,'Invalid KTX2 level offset/order/length');
      const data=bytes.subarray(cursor,cursor+length);
      for(let i=0;i<data.length;i+=4)check(data[i]<=data[i+3]&&data[i+1]<=data[i+3]&&data[i+2]<=data[i+3],'Invalid premultiplied KTX2 pixel');
      levels[level]=data;cursor+=length;
    }
    check(cursor===bytes.length,'KTX2 payload mismatch');return {size,layers,levels};
  }
  function validateManifest(m,source){
    api.validateManifest(source);
    keys(m,['schema','profile','status','publicOnly','guarantee','sourceManifest','banks','viewerFiles']);
    check(m.schema===SCHEMA&&m.profile===PROFILE&&m.status==='passed'&&m.publicOnly===true&&m.guarantee==='presentation-only','Unsupported KTX2 bundle');
    keys(m.sourceManifest,['file','sha256','byteLength']);
    check(m.sourceManifest.file==='source-manifest.json'&&hex(m.sourceManifest.sha256)&&integer(m.sourceManifest.byteLength,1,16*1024*1024),'Invalid KTX2 source reference');
    check(Array.isArray(m.banks)&&m.banks.length===source.banks.length,'KTX2 bank inventory mismatch');
    m.banks.forEach((b,i)=>{keys(b,['index','layerCount','file','byteLength','sha256']);
      check(b.index===i&&b.layerCount===source.banks[i].layerCount&&b.file===`banks/bank-${String(i).padStart(3,'0')}.ktx2`&&
        b.byteLength===lengthFor(source.nativeSize,b.layerCount)&&hex(b.sha256),'Invalid KTX2 bank reference');});
    check(Array.isArray(m.viewerFiles)&&m.viewerFiles.length===5,'Invalid KTX2 viewer inventory');
    ['index.html','alpha-runtime.js','ktx2-runtime.js','demo.js','demo.css'].forEach((name,i)=>{const f=m.viewerFiles[i];
      keys(f,['file','byteLength','sha256']);check(f.file===name&&integer(f.byteLength,1,256*1024)&&hex(f.sha256),'Invalid KTX2 viewer reference');});
    return m;
  }
  async function fetchBounded(url,limit,signal){
    const response=await fetch(url,{signal,credentials:'omit',redirect:'error',cache:'no-store'});
    check(response.ok&&response.body,'KTX2 HTTP failure');
    check(Number(response.headers.get('content-length')||0)<=limit,'KTX2 HTTP body budget exceeded');
    const reader=response.body.getReader(),parts=[];let length=0;
    try{for(;;){const p=await reader.read();if(p.done)break;length+=p.value.length;
      check(length<=limit,'KTX2 HTTP body budget exceeded');parts.push(p.value);}}
    finally{await reader.cancel().catch(()=>{});reader.releaseLock();}
    const bytes=new Uint8Array(length);let at=0;for(const p of parts){bytes.set(p,at);at+=p.length;}return bytes;
  }
  const parse=bytes=>JSON.parse(new TextDecoder('utf-8',{fatal:true}).decode(bytes));
  async function loadBundle(baseURL,options={}){
    const base=new URL(baseURL,global.location.href);
    check(['http:','https:'].includes(base.protocol)&&base.origin===global.location.origin&&!base.username&&!base.password&&
      !base.search&&!base.hash&&base.pathname.endsWith('/'),'KTX2 requires a same-origin HTTP directory');
    const budget=options.maxTextureBytes??64*1024*1024;
    check(integer(budget,1024,128*1024*1024),'Invalid KTX2 texture budget');
    if(options.manifestSha256!==undefined)check(hex(options.manifestSha256),'Invalid KTX2 manifest pin');
    const bytes=await fetchBounded(new URL('manifest.json',base),16*1024*1024,options.signal),digest=await api.sha256(bytes);
    if(options.manifestSha256!==undefined)check(digest===options.manifestSha256,'KTX2 manifest checksum mismatch');
    const m=parse(bytes);
    // Source path is hard-coded: no unvalidated manifest value becomes a URL.
    const sourceBytes=await fetchBounded(new URL('source-manifest.json',base),16*1024*1024,options.signal),source=parse(sourceBytes);
    validateManifest(m,source);
    check(sourceBytes.length===m.sourceManifest.byteLength&&await api.sha256(sourceBytes)===m.sourceManifest.sha256,'KTX2 source manifest checksum mismatch');
    check(source.payloadBytes<=budget,'KTX2 texture memory budget exceeded');
    const payload=[],containers=[];
    try{
      for(const bank of m.banks){if(options.signal?.aborted)throw new Error('KTX2 load aborted');
        const data=await fetchBounded(new URL(bank.file,base),bank.byteLength,options.signal);containers.push(data);
        check(data.length===bank.byteLength&&await api.sha256(data)===bank.sha256,'KTX2 file checksum mismatch');
        const parsed=decode(data);check(parsed.size===source.nativeSize&&parsed.layers===bank.layerCount,'KTX2 array dimensions mismatch');
        payload.push(parsed.levels);
      }
      // The original runtime rechecks every identity, level and layer checksum,
      // snapshots the bytes and owns GPU lifecycle. No second renderer is added.
      return await api.fromLevels(sourceBytes,payload,{...options,manifestSha256:m.sourceManifest.sha256});
    } finally {containers.forEach(data=>data.fill(0));}
  }
  global.ByteFablesKtx2Textures=Object.freeze({decode,validateManifest,lengthFor,loadBundle,
    lookup:api.lookup,makeGrid:api.makeGrid,runs:api.runs,WebGLArray:api.WebGLArray,sha256:api.sha256});
})(globalThis);
