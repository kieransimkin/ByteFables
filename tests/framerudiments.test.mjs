import test from 'node:test';
import assert from 'node:assert/strict';
import {
  ByteValue, PublicRecord, ModuleMatrix, createVectorScene, encodeHex,
  publicRecordDigest, createFrameRudimentsIdentityLayer, createFrameRudimentsMatrixLayer,
  createFrameRudimentsSceneLayer, frameRudimentsEffectTarget,
  executePublicFormat, FRAMERUDIMENTS_BRIDGE_VERSION
} from '../dist/index.js';

const record = () => new PublicRecord(ByteValue.public(Uint8Array.of(0, 1, 2, 255), {
  namespace: 'danceflow', kind: 'node-id'
}), { network: 'testnet' });
const layout = { id: 'avatar-one', bounds: [10, 20, 138, 148] };

test('typed public record produces a stable, native FrameRudiments generator layer', async () => {
  const r = record();
  const layer = await createFrameRudimentsIdentityLayer(r, layout);
  assert.equal(layer.type, 'rudiment');
  assert.equal(layer.renderer, 'bytefables-pixel-v1');
  assert.deepEqual(layer.bounds, layout.bounds);
  assert.equal(layer.style.bridge_version, FRAMERUDIMENTS_BRIDGE_VERSION);
  assert.equal(layer.style.digest_hex, encodeHex(await publicRecordDigest(r)));
  assert.equal(layer.style.palette, 'neon');
  assert.deepEqual(layer.motion, { kind: 'named', pattern: 'circle' });
  assert.equal(frameRudimentsEffectTarget(layer), 'layer:avatar-one');
  assert.deepEqual(await createFrameRudimentsIdentityLayer(r, layout), layer);
  assert.equal(layer.style.digest_hex.includes('000102ff'), false);
  assert.throws(() => { layer.style.palette = 'bogus'; }, TypeError);
  assert.throws(() => { layer.bounds[0] = 999; }, TypeError);
});

test('typed context affects the FRAME input without changing legacy identity v1', async () => {
  const r = record();
  const changed = new PublicRecord(r.value, { network: 'mainnet' });
  assert.notEqual((await createFrameRudimentsIdentityLayer(r, layout)).style.digest_hex,
    (await createFrameRudimentsIdentityLayer(changed, layout)).style.digest_hex);
  await assert.rejects(() => createFrameRudimentsIdentityLayer(ByteValue.secret(Uint8Array.of(5), {
    namespace: 'test', kind: 'secret'
  }), layout), /PUBLIC|PublicRecord/i);
  await assert.rejects(() => createFrameRudimentsIdentityLayer(r, { ...layout, palette: 'secret' }), /palette/i);
  for (const bad of [{ ...layout, id: 'bad:exec' }, { id: 'x', bounds: [0,0,0,1] },
    { id: 'x', bounds: [0,0,999999,1] }]) {
    await assert.rejects(() => createFrameRudimentsIdentityLayer(r, bad));
  }
});

test('public matrix and vector scene export plugin input without constructing pixels', () => {
  const matrix = new ModuleMatrix({ formatId: 'test/matrix', width: 3, height: 2,
    modules: Uint8Array.of(1,0,1,0,1,0), quietZone: 2 });
  const layer = createFrameRudimentsMatrixLayer(matrix, { id: 'symbol', bounds: [0, 0, 64, 64] });
  assert.equal(layer.renderer, 'bytefables-matrix-v1');
  assert.equal(layer.style.modules, '101010');
  assert.equal(layer.style.format_id, 'test/matrix');
  assert.equal(layer.style.quiet_zone, 2);
  assert.equal(layer.style.width, 3);
  assert.equal(layer.style.height, 2);
  const scene = createVectorScene({ width: 100, height: 100, primitives: [
    { kind: 'rect', x: 0, y: 0, width: 10, height: 20, fill: '#123456' },
    { kind: 'path', d: 'M10 10L20 10L20 20L10 20Z', fill: '#aabbcc' }
  ]});
  const l2 = createFrameRudimentsSceneLayer(scene, { id: 'scene', bounds: [0,0,128,128] });
  assert.equal(l2.renderer, 'bytefables-scene-v1');
  assert.deepEqual(l2.style.scene.primitives, scene.primitives);
  const badScene = createVectorScene({ width: 1, height: 1,
    primitives: [{ kind: 'path', d: 'm0 0l1 0z', fill: '#000000' }] });
  assert.throws(() => createFrameRudimentsSceneLayer(badScene, layout), /absolute/);
});

test('manifest format returns a declarative JSON layer and opt-in experimental boundary', async () => {
  const r = record();
  await assert.rejects(() => executePublicFormat('exporter/framerudiments-layer-v1', r));
  const artifact = await executePublicFormat('exporter/framerudiments-layer-v1', r, { allowExperimental: true });
  assert.equal(artifact.mediaType, 'application/json');
  assert.equal(artifact.guarantee, 'presentation-only');
  const layer = JSON.parse(artifact.data);
  assert.equal(layer.renderer, 'bytefables-pixel-v1');
  assert.equal(layer.style.digest_hex, encodeHex(await publicRecordDigest(r)));
  assert.equal(layer.style.palette, 'neon');
});

test('immutable FrameRudiments fragment vectors track TS/Python bridge contract', async () => {
  const { readFile } = await import('node:fs/promises');
  const fixture = JSON.parse(await readFile(new URL('./vectors/framerudiments-v1.json', import.meta.url)));
  assert.equal(fixture.schema, 'bytefables-framerudiments-vector-1');
  assert.equal(fixture.publicOnly, true);
  assert.deepEqual(fixture.identity, await createFrameRudimentsIdentityLayer(record(), layout));
  const matrix = new ModuleMatrix({ formatId: 'test/matrix', width: 3, height: 2,
    modules: Uint8Array.of(1,0,1,0,1,0), quietZone: 2 });
  assert.deepEqual(fixture.matrix, createFrameRudimentsMatrixLayer(matrix,
    { id: 'symbol', bounds: [0,0,70,60] }));
});

test('strict renderer bridge rejects unclosed or underspecified SVG paths before host', () => {
  for (const d of ['M1 1L10 10', 'L1 1L2 2Z', 'M1 1Z', 'M1 1L10 1Z',
    'M1 1L2 2<script>Z', 'M1 1L2 2L3 3Z junk']) {
    if (d.includes('<') || d.includes('junk')) {
      assert.throws(() => createVectorScene({ width: 10, height: 10,
        primitives: [{ kind: 'path', d, fill: '#000000' }] }));
    } else {
      const scene = createVectorScene({ width: 10, height: 10,
        primitives: [{ kind: 'path', d, fill: '#000000' }] });
      assert.throws(() => createFrameRudimentsSceneLayer(scene, layout));
    }
  }
});
