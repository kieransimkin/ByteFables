/* Bounded async KTX2 bank residency. Loads pixels; never generates artwork. */
(function(global){
  'use strict';
  const VERSION='bytefables.streaming-residency.v1';
  const check=(yes,msg)=>{if(!yes)throw new Error(msg);};
  const integer=(n,lo,hi)=>Number.isSafeInteger(n)&&n>=lo&&n<=hi;
  const hex=x=>typeof x==='string'&&/^[0-9a-f]{64}$/.test(x);
  const now=()=>global.performance?.now?.()??Date.now();

  function aborted(signal){if(signal?.aborted)throw signal.reason??new DOMException('Aborted','AbortError');}
  function waitWithSignal(promise,signal){
    if(!signal)return promise;aborted(signal);
    return new Promise((resolve,reject)=>{
      const onAbort=()=>reject(signal.reason??new DOMException('Aborted','AbortError'));
      signal.addEventListener('abort',onAbort,{once:true});
      promise.then(v=>{signal.removeEventListener('abort',onAbort);resolve(v);},e=>{signal.removeEventListener('abort',onAbort);reject(e);});
    });
  }

  class ResidencyCache {
    constructor(loader,options={}){
      check(typeof loader==='function','Residency loader is required');
      const budget=options.budgetBytes??16*1024*1024;
      check(integer(budget,1,128*1024*1024),'Residency budget must be 1..128 MiB');
      this.loader=loader;this.sizeOf=options.sizeOf??(v=>v?.byteLength??0);this.disposer=options.disposer??(()=>{});
      check(typeof this.sizeOf==='function'&&typeof this.disposer==='function','Invalid residency callbacks');
      this.budget=budget;this.entries=new Map();this.loading=new Map();this.clock=0;this.closed=false;
      this.counters={loads:0,hits:0,evictions:0,residentBytes:0,peakResidentBytes:0};
    }
    _requireOpen(){check(!this.closed,'Residency cache is disposed');}
    _touch(entry){entry.last=++this.clock;}
    _evictFor(required,exclude){
      check(integer(required,0,128*1024*1024)&&required<=this.budget,'Single bank exceeds residency budget');
      while(this.counters.residentBytes+required>this.budget){
        let victimKey=null,victim=null;
        for(const [key,e] of this.entries){if(key===exclude||e.refs!==0)continue;if(!victim||e.last<victim.last){victim=e;victimKey=key;}}
        check(victim,'Residency budget is pinned by active leases');
        this.entries.delete(victimKey);this.counters.residentBytes-=victim.bytes;this.counters.evictions++;this.disposer(victim.value);
      }
    }
    async _resident(key){
      this._requireOpen();let entry=this.entries.get(key);
      if(entry){this.counters.hits++;this._touch(entry);return entry;}
      let pending=this.loading.get(key);
      if(!pending){
        pending=(async()=>{
          const value=await this.loader(key);let accepted=false;
          try{
            this._requireOpen();const bytes=this.sizeOf(value);check(integer(bytes,1,128*1024*1024),'Loader returned invalid residency size');
            this._evictFor(bytes,key);const e={value,bytes,refs:0,last:0};this._touch(e);this.entries.set(key,e);
            this.counters.loads++;this.counters.residentBytes+=bytes;this.counters.peakResidentBytes=Math.max(this.counters.peakResidentBytes,this.counters.residentBytes);
            accepted=true;return e;
          }finally{if(!accepted)this.disposer(value);}
        })();
        this.loading.set(key,pending);pending.finally(()=>this.loading.delete(key)).catch(()=>{});
      }
      return pending;
    }
    async acquire(key,options={}){
      this._requireOpen();aborted(options.signal);const entry=await waitWithSignal(this._resident(key),options.signal);aborted(options.signal);
      this._requireOpen();entry.refs++;this._touch(entry);let released=false;const cache=this;
      return Object.freeze({key,value:entry.value,release(){if(released)return;released=true;entry.refs--;check(entry.refs>=0,'Residency lease underflow');
        cache._touch(entry);if(cache.closed&&entry.refs===0&&cache.entries.get(key)===entry){cache.entries.delete(key);cache.counters.residentBytes-=entry.bytes;cache.disposer(entry.value);}}});
    }
    async prefetch(keys,options={}){
      this._requireOpen();check(Array.isArray(keys)&&keys.length<=1024,'Invalid prefetch list');
      for(const key of keys){aborted(options.signal);await waitWithSignal(this._resident(key),options.signal);}return this.stats();
    }
    setBudget(bytes){
      this._requireOpen();check(integer(bytes,1,128*1024*1024),'Residency budget must be 1..128 MiB');
      let pinned=0;for(const e of this.entries.values())if(e.refs!==0)pinned+=e.bytes;
      check(pinned<=bytes,'Residency budget is pinned by active leases');this.budget=bytes;this._evictFor(0,null);return this.stats();
    }
    stats(){return Object.freeze({...this.counters,budgetBytes:this.budget,residentBanks:this.entries.size,inFlight:this.loading.size,disposed:this.closed});}
    dispose(){if(this.closed)return;this.closed=true;this.loading.clear();for(const [key,e] of [...this.entries])if(e.refs===0){this.entries.delete(key);this.counters.residentBytes-=e.bytes;this.disposer(e.value);}}
  }

  async function fetchBounded(url,limit,signal){
    const response=await fetch(url,{signal,credentials:'omit',redirect:'error',cache:'no-store'});check(response.ok&&response.body,'Streaming HTTP failure');
    const declared=Number(response.headers.get('content-length')||0);check(!declared||declared<=limit,'Streaming HTTP body budget exceeded');
    const reader=response.body.getReader(),parts=[];let length=0;
    try{for(;;){const p=await reader.read();if(p.done)break;length+=p.value.length;check(length<=limit,'Streaming HTTP body budget exceeded');parts.push(p.value);}}
    finally{await reader.cancel().catch(()=>{});reader.releaseLock();}
    const bytes=new Uint8Array(length);let at=0;for(const p of parts){bytes.set(p,at);at+=p.length;}return bytes;
  }
  const parse=bytes=>JSON.parse(new TextDecoder('utf-8',{fatal:true}).decode(bytes));

  async function openKtx2(baseURL,options={}){
    const api=global.ByteFablesKtx2Textures;check(api,'Load ByteFables alpha and KTX2 runtimes before streaming runtime');
    const base=new URL(baseURL,global.location.href);check(['http:','https:'].includes(base.protocol)&&base.origin===global.location.origin&&!base.username&&!base.password&&!base.search&&!base.hash&&base.pathname.endsWith('/'),'Streaming requires a same-origin HTTP directory');
    const openSignal=options.signal;const transportBytes=await fetchBounded(new URL('manifest.json',base),16*1024*1024,openSignal);
    const transportSha=await api.sha256(transportBytes);if(options.manifestSha256!==undefined){check(hex(options.manifestSha256)&&transportSha===options.manifestSha256,'Streaming transport pin mismatch');}
    const transport=parse(transportBytes);const sourceBytes=await fetchBounded(new URL('source-manifest.json',base),16*1024*1024,openSignal);const source=parse(sourceBytes);
    api.validateManifest(transport,source);check(sourceBytes.length===transport.sourceManifest.byteLength&&await api.sha256(sourceBytes)===transport.sourceManifest.sha256,'Streaming source manifest checksum mismatch');
    const budget=options.budgetBytes??Math.min(16*1024*1024,source.payloadBytes);check(integer(budget,1,128*1024*1024),'Invalid streaming budget');
    const disposedLevels=levels=>levels.forEach(level=>level.fill(0));
    async function loader(bankIndex){
      check(integer(bankIndex,0,transport.banks.length-1),'Invalid streaming bank index');const bank=transport.banks[bankIndex],original=source.banks[bankIndex];
      const data=await fetchBounded(new URL(bank.file,base),bank.byteLength,undefined);check(data.length===bank.byteLength&&await api.sha256(data)===bank.sha256,'Streaming KTX2 bank checksum mismatch');
      const parsed=api.decode(data);check(parsed.size===source.nativeSize&&parsed.layers===bank.layerCount,'Streaming KTX2 bank geometry mismatch');
      const levels=parsed.levels.map(level=>new Uint8Array(level));data.fill(0);
      try{
        for(let level=0;level<levels.length;level++){
          const raw=levels[level],record=original.levels[level];check(raw.length===record.byteLength&&await api.sha256(raw)===record.sha256,'Streaming decoded level checksum mismatch');
          const per=(source.nativeSize>>level)**2*4;
          for(let layer=0;layer<bank.layerCount;layer++){
            const sprite=source.sprites[bankIndex*source.layersPerBank+layer];check(sprite&&await api.sha256(raw.subarray(layer*per,(layer+1)*per))===sprite.levelSha256[level],'Streaming sprite mip checksum mismatch');
          }
        }
      }catch(error){disposedLevels(levels);throw error;}
      return Object.freeze({bankIndex,size:source.nativeSize,layers:bank.layerCount,levels:Object.freeze(levels)});
    }
    const cache=new ResidencyCache(loader,{budgetBytes:budget,sizeOf:v=>v.levels.reduce((n,b)=>n+b.length,0),disposer:v=>disposedLevels(v.levels)});
    let closed=false;
    const requireOpen=()=>check(!closed,'Streaming bundle is disposed');
    return Object.freeze({transport,manifest:source,transportSha256:transportSha,cache,
      async acquireBank(index,opts={}){requireOpen();return cache.acquire(index,opts);},
      async acquireSprite(selector,opts={}){requireOpen();const spriteIndex=api.lookup(source,selector),sprite=source.sprites[spriteIndex],lease=await cache.acquire(sprite.bankIndex,opts);
        return Object.freeze({spriteIndex,sprite,bank:lease.value,release:lease.release});},
      async prefetchBanks(indices,opts={}){requireOpen();check(Array.isArray(indices)&&indices.every(i=>integer(i,0,transport.banks.length-1)),'Invalid streaming prefetch indices');return cache.prefetch(indices,opts);},
      setBudget(bytes){requireOpen();return cache.setBudget(bytes);},stats(){return cache.stats();},
      dispose(){if(closed)return;closed=true;cache.dispose();}
    });
  }
  global.ByteFablesStreaming=Object.freeze({VERSION,ResidencyCache,openKtx2});
})(globalThis);
