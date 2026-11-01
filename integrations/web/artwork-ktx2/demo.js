(function(){'use strict';const $=id=>document.getElementById(id),api=globalThis.ByteFablesKtx2Textures;
let bundle,renderer;
function inspect(){const index=Number($('inspect').value);if(!Number.isSafeInteger(index)||index<0||index>=bundle.manifest.spriteCount)return;
  $('identity').textContent=JSON.stringify(bundle.manifest.sprites[index],null,2);}
function draw(){try{const canvas=$('canvas'),grid=api.makeGrid(bundle.manifest,Number($('count').value),40,Number($('size').value));
  renderer?.dispose();canvas.width=grid.width;canvas.height=grid.height;
  renderer=new api.WebGLArray(canvas,bundle,{filter:$('filter').value});
  $('viewport').className=$('background').value;
  const result=renderer.draw(grid.instances);
  $('status').textContent=`${result.instances} instances · ${bundle.manifest.spriteCount} unique identity/style entries · ${result.drawCalls} draw calls · ${result.submitMilliseconds.toFixed(2)} ms CPU submission · ${(result.payloadBytes/1048576).toFixed(2)} MiB texture payload`;
}catch(error){$('status').textContent='Display failed: '+error.message;}}
$('render').addEventListener('click',draw);$('inspect').addEventListener('input',()=>bundle&&inspect());
api.loadBundle('./').then(value=>{bundle=value;$('inspect').max=String(bundle.manifest.spriteCount-1);inspect();draw();})
 .catch(error=>{$('status').textContent='Load failed: '+error.message;});
addEventListener('pagehide',()=>{renderer?.dispose();bundle?.dispose();});})();
