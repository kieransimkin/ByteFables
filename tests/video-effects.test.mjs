import { test } from 'node:test';
import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import { readFileSync } from 'node:fs';
import {
  ByteValue, PublicRecord, planPublicVideoLook, VIDEO_LOOK_PRESETS, PUBLIC_VIDEO_LOOK_VERSION
} from '../dist/index.js';

const value = (kind = 'node-id', namespace = 'danceflow') => new PublicRecord(
  ByteValue.public(Uint8Array.from({length: 32}, (_, i) => i), {kind, namespace})
);

function cli(...args) {
  return spawnSync(process.execPath, ['bin/bytefables.mjs', ...args], {encoding:'utf8', timeout: 10000});
}

test('public video look is a deterministic host-owned post effect, not a renderer', async () => {
  const a = await planPublicVideoLook(value());
  const b = await planPublicVideoLook(value());
  assert.deepEqual(a, b);
  assert.equal(a.schema, PUBLIC_VIDEO_LOOK_VERSION);
  assert.equal(a.host, 'FrameRudiments');
  assert.equal(a.reversible, false);
  assert.equal(a.authenticated, false);
  assert.equal(a.profileSelectionBits, 4);
  assert.match(a.digestHex, /^[a-f0-9]{64}$/);
  assert.equal(a.post_effects.elements['layer:bytefables-identity'].length, 1);
  assert.equal(a.post_effects.elements['layer:bytefables-identity'][0].id, 'bytefables-video-look-v1');
  assert.equal(a.post_effects.elements['layer:bytefables-identity'][0].visual.grain_seed === undefined ||
    Number.isInteger(a.post_effects.elements['layer:bytefables-identity'][0].visual.grain_seed), true);
  assert.notEqual((await planPublicVideoLook(value('agent-id'))).digestHex, a.digestHex);
  assert.notEqual((await planPublicVideoLook(value('node-id', 'syn'))).digestHex, a.digestHex);
  assert.ok(Object.isFrozen(a));
});

test('all sixteen looks emit bounded, documented existing VisualStyle fields', async () => {
  assert.equal(VIDEO_LOOK_PRESETS.length, 16);
  const neutral = { saturation: 1, contrast: 1, brightness: 1, gamma: 1, pixel_size: 1,
    scanline_spacing: 4, hue_shift: 0, grain: 0, vignette: 0, glow: 0, blur: 0,
    scanlines: 0, chromatic_shift: 0, glitch: 0, posterize: 0, dither: 0,
    halftone: 0, solarize: 0, sharpen: 0, edge_mix: 0, grain_seed: 0 };
  for (const x of VIDEO_LOOK_PRESETS) {
    assert.match(x.id, /^[a-z][a-z-]+$/);
    const got = await planPublicVideoLook(value(), {look: x.id, intensity: 0.5, target: 'layer:agent_01'});
    assert.equal(got.selectedLook, x.id);
    assert.equal(got.target, 'layer:agent_01');
    assert.ok(got.post_effects.elements['layer:agent_01']);
    const vis = got.post_effects.elements['layer:agent_01'][0].visual;
    for (const [field,n] of Object.entries(vis)) {
      assert.ok(field in neutral, `Unknown host field: ${field}`);
      assert.ok(typeof n === 'number' && Number.isFinite(n));
      if (field !== 'grain_seed') {
        const full = x.visual[field];
        const lo=Math.min(neutral[field],full), hi=Math.max(neutral[field],full);
        assert.ok(n >= Math.floor(lo) && n <= Math.ceil(hi), `Out of intensity bound: ${x.id}.${field}`);
      }
    }
  }
  const noOp = await planPublicVideoLook(value(), { intensity:0, look:'noir' });
  assert.equal(noOp.post_effects, null);
});

test('public look planning fails closed on secret input, protected code and invalid settings', async () => {
  const secret = ByteValue.secret(Uint8Array.of(1), {namespace:'danceflow',kind:'node-id'});
  await assert.rejects(planPublicVideoLook(secret), /public record/i);
  const r=value();
  await assert.rejects(planPublicVideoLook(r, {purpose:'optical-recovery'}), /forbidden/i);
  await assert.rejects(planPublicVideoLook(r, {purpose:'optical-recovery',intensity:0}), /forbidden/i);
  await assert.rejects(planPublicVideoLook(r, {target:'frame'}), /Frame-wide effects require/i);
  const explicitFrame = await planPublicVideoLook(r, {target:'frame',purpose:'public-video'});
  assert.equal(explicitFrame.post_effects.frame.length,1);
  for(const strength of [-1, 1.01, Infinity, NaN, '1']) {
    await assert.rejects(planPublicVideoLook(r, {intensity:strength}), /intensity/i);
  }
  for(const target of ['layer:../../private', 'image:qr','post_effects','', 'layer:UPPER', 'layer:'+ 'x'.repeat(100)]) {
    await assert.rejects(planPublicVideoLook(r, {target}), /target/i);
  }
  await assert.rejects(planPublicVideoLook(r, {look:'invented'}), /Unknown public video look/);
});

test('catalogue distinguishes existing native knobs from planned effects', () => {
  const m=JSON.parse(readFileSync(new URL('../manifests/video-effects-v1.json', import.meta.url)));
  assert.equal(m.schema, 'bytefables.video-effect-research.v1');
  assert.ok(m.entries.length >= 140);
  assert.equal(new Set(m.entries.map(e=>e.id)).size,m.entries.length);
  assert.equal(new Set(m.entries.map(e=>e.family)).size,11);
  assert.ok(m.entries.every(x => x.protectedOpticalSafe === false && x.identityOnly === true));
  assert.ok(m.entries.some(e=>e.id==='optical-flow' && e.implementation==='new-frame-rudiments-work'));
  assert.ok(m.entries.some(e=>e.id==='crt-scanlines' && e.nativeContract==='visual.scanlines'));
  assert.ok(m.entries.some(e=>e.id==='lut-3d' && e.nativeContract===null));
});

test('public CLI outputs a FrameRudiments fragment and can browse existing/future effects', () => {
  const args=['--confirm-public','--public-hex','0011223344','--namespace','danceflow','--kind','node-id'];
  const ok=cli('video-look',...args,'--look','crt-soft','--target','layer:agent1','--intensity','0.5');
  assert.equal(ok.status,0,ok.stderr);
  const v=JSON.parse(ok.stdout);
  assert.equal(v.selectedLook,'crt-soft');
  assert.equal(v.post_effects.elements['layer:agent1'].length,1);
  assert.equal(v.post_effects.frame,undefined);
  const c=cli('video-effects','--family','transitions','--json');
  assert.equal(c.status,0,c.stderr);
  const d=JSON.parse(c.stdout);
  assert.ok(d.entries.some(e=>e.id==='radial-reveal'));
  assert.ok(d.entries.every(e=>e.family==='transitions'));
  assert.notEqual(cli('video-look','--public-hex','aa','--namespace','danceflow','--kind','node-id').status,0);
  assert.notEqual(cli('video-effects','--family','irrelevant').status,0);
});
