/* Static demo; redraws only on user input, no background animation loop. */
(async function () {
  'use strict';
  const api=globalThis.ByteFablesTextures, node=id=>document.getElementById(id), status=node('status');
  let bundle,consumer,grid;
  const inspect=()=>{if(!grid)return;const i=Number(node('inspect').value);
    if(!Number.isInteger(i)||i<0||i>=grid.instances.length){node('identity').textContent='Choose an existing instance number.';return;}
    const sprite=bundle.manifest.sprites[grid.instances[i].spriteIndex];
    node('identity').textContent=JSON.stringify({instance:i,digestHex:sprite.digestHex,family:sprite.family,
      palette:sprite.palette,complexity:sprite.complexity,spriteKey:sprite.spriteKey,pageIndex:sprite.pageIndex,
      nativeSize:sprite.nativeSize,rect:sprite.rect},null,2);};
  const draw=()=>{try{
    if(consumer)consumer.dispose();
    const old=node('scene'),canvas=document.createElement('canvas');canvas.id='scene';canvas.setAttribute('aria-label','Public identity sprite grid');old.replaceWith(canvas);
    const size=node('size').value==='native'?bundle.manifest.nativeSize:Number(node('size').value);
    grid=api.makeGrid(bundle.manifest,Number(node('count').value),40,size);canvas.width=grid.width;canvas.height=grid.height;
    const backend=node('backend').value;
    consumer=backend==='webgl2'?new api.WebGLAtlas(canvas,bundle):new api.CanvasAtlas(canvas,bundle);
    const measured=consumer.draw(grid.instances);
    status.textContent=`Ready: ${measured.instances} instances via ${measured.backend}.`;
    node('stats').textContent=`${bundle.manifest.spriteCount} unique identity/style entries · ${bundle.manifest.pages.length} texture pages · ${measured.drawCalls} draw calls · ${measured.submitMilliseconds.toFixed(2)} ms CPU submission`;
    node('inspect').max=String(grid.instances.length-1);inspect();
  }catch(error){status.textContent=`Display failed: ${error.message}. Select Canvas2D if WebGL2 is unavailable.`;}};
  try{
    bundle=await api.loadBundle('./');node('draw').disabled=false;
    node('controls').addEventListener('submit',e=>{e.preventDefault();draw();});node('inspect').addEventListener('input',inspect);
    globalThis.addEventListener('pagehide',()=>{if(consumer)consumer.dispose();bundle.dispose();},{once:true});draw();
  }catch(error){status.textContent=`Texture load failed: ${error.message}`;}
})();
