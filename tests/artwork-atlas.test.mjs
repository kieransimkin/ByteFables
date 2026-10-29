import test from 'node:test';
import assert from 'node:assert/strict';
import { ByteValue, PublicRecord, createFrameRudimentsArtworkAtlas,
  ARTWORK_ATLAS_VERSION } from '../dist/index.js';

const record = (n, network='') => new PublicRecord(ByteValue.public(
  Uint8Array.of(n & 255, (n >>> 8) & 255), {namespace:'danceflow',kind:'node-id'}), {network});

test('stable multi-page image atlas, UVs, no source bytes in native styles', async () => {
  const records = Array.from({length: 13}, (_, i) => record(i));
  const a = await createFrameRudimentsArtworkAtlas(records, {
    columns:3, rowsPerPage:2, tileSize:32, padding:2, artwork:'orbital', palette:'mono'
  });
  const b = await createFrameRudimentsArtworkAtlas(records, {
    columns:3, rowsPerPage:2, tileSize:32, padding:2, artwork:'orbital', palette:'mono'
  });
  assert.deepEqual(a,b);
  assert.equal(a.version,ARTWORK_ATLAS_VERSION);
  assert.equal(a.inputCount,13);
  assert.equal(a.pages.length,3);
  assert.deepEqual(a.pages.map(p=>p.tiles.length),[6,6,1]);
  assert.equal(a.pages[0].width,108);
  assert.equal(a.pages[0].height,72);
  assert.equal(a.pages[2].height,36);
  assert.deepEqual(a.pages[0].tiles[0].rect,[2,2,34,34]);
  for (const page of a.pages) for (const tile of page.tiles) {
    assert.deepEqual(tile.layer.bounds,tile.rect);
    assert.equal(tile.layer.style.digest_hex,tile.digestHex);
    assert.equal(tile.layer.style.style,'orbital');
    assert.equal(tile.layer.style.palette,'mono');
    assert.ok(tile.uv.every(v=>v>=0 && v<=1));
    assert.equal(tile.layer.style.public_hex,undefined);
  }
  assert.notEqual((await createFrameRudimentsArtworkAtlas([record(1,'testnet')])).pages[0].tiles[0].digestHex,
    (await createFrameRudimentsArtworkAtlas([record(1,'mainnet')])).pages[0].tiles[0].digestHex);
  assert.throws(()=>a.pages.push(null),TypeError);
});

test('atlas rejects secret labels, out-of-bound layouts, invalid options', async () => {
  for (const records of [[], [record(1),null], [ByteValue.secret(Uint8Array.of(1),
    {namespace:'a',kind:'b'})], Array.from({length:1001},()=>record(0))]) {
    await assert.rejects(()=>createFrameRudimentsArtworkAtlas(records));
  }
  for (const options of [{tileSize:0},{padding:-1},{columns:0},{rowsPerPage:100},
    {columns:64,tileSize:512},{complexity:9},{artwork:'unknown'},{palette:'bad'}]) {
    await assert.rejects(()=>createFrameRudimentsArtworkAtlas([record(1)],options));
  }
});

test('thousand-id atlas stays within host geometry and maintains ordered indices', async () => {
  const p = await createFrameRudimentsArtworkAtlas(Array.from({length:1000},(_,i)=>record(i)));
  assert.equal(p.pages.length,4);
  assert.equal(p.pages.flatMap(page=>page.tiles).length,1000);
  assert.deepEqual(p.pages.flatMap(page=>page.tiles).map(t=>t.inputIndex),
    Array.from({length:1000},(_,i)=>i));
});
