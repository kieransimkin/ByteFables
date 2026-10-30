import test from 'node:test';
import assert from 'node:assert/strict';
import { ByteValue, PublicRecord, createFrameRudimentsArtworkAtlas,
  createArtworkPngReceipt, inspectArtworkPng } from '../dist/index.js';
const record = i => new PublicRecord(ByteValue.public(Uint8Array.of(i), {namespace:'danceflow',kind:'node-id'}));
// The container inspector checks framing and dimensions, not compressed pixels or CRC.
function fixturePng(width, height) {
  const a=[137,80,78,71,13,10,26,10];
  function chunk(type,data){a.push(0,0,0,data.length,...[...type].map(c=>c.charCodeAt(0)),...data,0,0,0,0)}
  const w=[width>>>24,(width>>>16)&255,(width>>>8)&255,width&255];
  const h=[height>>>24,(height>>>16)&255,(height>>>8)&255,height&255];
  chunk('IHDR',[...w,...h,8,6,0,0,0]);chunk('IDAT',[1]);chunk('IEND',[]);
  return Uint8Array.from(a);
}
test('atlas receipt checks completed PNG dimensions, uniqueness and stable digest', async()=>{
  const plan=await createFrameRudimentsArtworkAtlas([record(1),record(2)],{tileSize:32,padding:2,columns:1,rowsPerPage:1});
  const rendered=plan.pages.map(p=>({pageIndex:p.index,pngBytes:fixturePng(p.width,p.height)}));
  const a=await createArtworkPngReceipt(plan,rendered);
  assert.equal(a.pages.length,2);
  assert.equal(a.pages[0].sha256Hex.length,64);
  assert.deepEqual(a,await createArtworkPngReceipt(plan,[...rendered].reverse()));
  await assert.rejects(()=>createArtworkPngReceipt(plan,[rendered[0],rendered[0]]),/repeated/);
  await assert.rejects(()=>createArtworkPngReceipt(plan,[rendered[0]]),/Invalid/);
  await assert.rejects(()=>createArtworkPngReceipt(plan,[{pageIndex:0,pngBytes:fixturePng(1,1)},rendered[1]]),/dimensions/);
});
test('PNG inspector rejects invalid framing and trailing data',()=>{
 const p=fixturePng(40,44);assert.deepEqual(inspectArtworkPng(p),{width:40,height:44});
 assert.throws(()=>inspectArtworkPng(p.subarray(0,p.length-2)));
 assert.throws(()=>inspectArtworkPng(Uint8Array.from([...p,1])));
 assert.throws(()=>inspectArtworkPng(Uint8Array.of(1,2,3)));
});
