import test from 'node:test';
import assert from 'node:assert/strict';
import { pngCrc32, verifyArtworkPngChunks } from '../dist/engine/png-integrity.js';
import { inspectArtworkPng } from '../dist/index.js';
const signature = [137,80,78,71,13,10,26,10];
const u32 = n => [(n>>>24)&255,(n>>>16)&255,(n>>>8)&255,n&255];
function chunk(type, data) {
  const body = Uint8Array.from([...Buffer.from(type,'ascii'), ...data]);
  return [...u32(data.length), ...body, ...u32(pngCrc32(body))];
}
function fixture() {
  return Uint8Array.from([...signature,
    ...chunk('IHDR',[...u32(2),...u32(2),8,6,0,0,0]),
    ...chunk('IDAT',[120,156,3,0,0,0,0,1]),
    ...chunk('IEND',[])]);
}
test('known CRC and CRC-checked PNG metadata', () => {
  assert.equal(pngCrc32(Buffer.from('123456789')),0xcbf43926);
  const png = fixture();
  assert.deepEqual(inspectArtworkPng(png),{width:2,height:2});
  assert.deepEqual(verifyArtworkPngChunks(png),{chunkCount:3,idatChunks:1,crcVerified:true});
});
test('rejects corrupted data, CRC, trailing bytes and missing IDAT', () => {
  const png = fixture();
  for (const offset of [12, 29, 46, png.length - 1]) {
    const changed = Uint8Array.from(png); changed[offset] ^= 1;
    assert.throws(()=>inspectArtworkPng(changed));
  }
  assert.throws(()=>verifyArtworkPngChunks(Uint8Array.from([...png, 0])));
  assert.throws(()=>verifyArtworkPngChunks(Uint8Array.from([
    ...signature,...chunk('IHDR',[...u32(2),...u32(2),8,6,0,0,0]),...chunk('IEND',[])])));
});
