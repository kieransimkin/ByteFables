import test from 'node:test';
import assert from 'node:assert/strict';
import { ByteValue, PublicRecord, createFrameRudimentsArtworkGallery,
  ARTWORK_GALLERY_FAMILIES, ARTWORK_GALLERY_PALETTES } from '../dist/index.js';
const makeRecord = (network='testnet') => new PublicRecord(ByteValue.public(
  Uint8Array.of(0,1,2,255), {namespace:'danceflow',kind:'node-id'}),{network});
test('27 image styles planned as nonoverlapping deterministic native layers', async () => {
  const a = await createFrameRudimentsArtworkGallery(makeRecord());
  const b = await createFrameRudimentsArtworkGallery(makeRecord());
  assert.deepEqual(a,b);
  assert.equal(a.tiles.length,ARTWORK_GALLERY_FAMILIES.length*ARTWORK_GALLERY_PALETTES.length);
  assert.equal(a.width,848); assert.equal(a.height,704);
  assert.equal(a.guarantee,'presentation-only'); assert.equal(a.publicOnly,true);
  const ids = new Set();
  for (const tile of a.tiles) {
    assert.equal(tile.layer.renderer,'bytefables-artwork-v1');
    assert.equal(tile.layer.style.digest_hex,a.identityDigestHex);
    assert.equal(tile.layer.style.style,tile.family);
    assert.equal(tile.layer.style.palette,tile.palette);
    assert.ok(!ids.has(tile.layer.id)); ids.add(tile.layer.id);
    const [x0,y0,x1,y1]=tile.layer.bounds;
    assert.equal(x1-x0,128); assert.equal(y1-y0,128);
    assert.ok(x0>=0 && y0>=0 && x1<=a.width && y1<=a.height);
  }
  assert.notEqual((await createFrameRudimentsArtworkGallery(makeRecord('mainnet'))).identityDigestHex,a.identityDigestHex);
});
test('validated custom arrangements, immutable output and secret rejection', async () => {
  const plan=await createFrameRudimentsArtworkGallery(makeRecord(),{
    families:['sigil','orbital'],palettes:['mono'],columns:2,tileSize:32,gap:0,idPrefix:'test'
  });
  assert.equal(plan.tiles.length,2); assert.equal(plan.width,64); assert.equal(plan.height,32);
  assert.throws(()=>plan.tiles.push(null),TypeError);
  for(const options of [ {tileSize:4}, {gap:-1}, {columns:0},
    {families:['sigil','sigil']}, {palettes:['invalid']},
    {idPrefix:'unsafe/dir'}, {columns:27,tileSize:1024}]) {
    await assert.rejects(()=>createFrameRudimentsArtworkGallery(makeRecord(),options));
  }
  await assert.rejects(()=>createFrameRudimentsArtworkGallery(ByteValue.secret(
    Uint8Array.of(1),{namespace:'test',kind:'secret'})),/PublicRecord/);
});
