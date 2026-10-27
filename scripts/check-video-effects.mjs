#!/usr/bin/env node
/** Validate static research metadata; no renderer or optional model is loaded. */
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { VIDEO_LOOK_PRESETS } from '../dist/index.js';

const path = fileURLToPath(new URL('../manifests/video-effects-v1.json', import.meta.url));
const data = JSON.parse(readFileSync(path, 'utf8'));
const fail = msg => { throw new Error(`Video effects catalogue: ${msg}`); };
if (data.schema !== 'bytefables.video-effect-research.v1' ||
    data.renderAuthority !== 'FrameRudiments' || data.inputSensitivity !== 'public-only' ||
    !Array.isArray(data.entries) || data.entries.length < 120 || data.entries.length > 256) {
  fail('invalid catalogue envelope');
}
const allowed = new Set(['existing-frame-rudiments', 'new-frame-rudiments-work', 'research-only']);
const families = new Set(['grading','spatial','optics','compositing','transform','temporal',
  'transitions','retro','scene-depth','tracking-ai','procedural']);
const names = new Set();
for (const e of data.entries) {
  if (typeof e.id !== 'string' || !/^[a-z][a-z0-9-]{1,63}$/.test(e.id) || names.has(e.id)) fail('duplicate or invalid ID');
  names.add(e.id);
  if (!families.has(e.family) || !allowed.has(e.implementation) ||
      typeof e.algorithm !== 'string' || e.algorithm.length < 20 || e.algorithm.length > 260 ||
      !Array.isArray(e.inputs) || !e.inputs.length || e.inputs.length > 8 ||
      e.inputs.some(v => typeof v !== 'string' || !/^[a-z-]+$/.test(v)) ||
      typeof e.temporal !== 'boolean' || e.identityOnly !== true || e.protectedOpticalSafe !== false) {
    fail(`malformed or unsafe effect description: ${e.id}`);
  }
  if (e.implementation === 'existing-frame-rudiments') {
    if (typeof e.nativeContract !== 'string' || !e.nativeContract.length) fail(`missing existing host contract: ${e.id}`);
  } else if (e.nativeContract !== null) {
    fail(`future research must not claim host execution: ${e.id}`);
  }
}
if (VIDEO_LOOK_PRESETS.length !== 16 || new Set(VIDEO_LOOK_PRESETS.map(x => x.id)).size !== 16) {
  fail('public video look presets must be exactly 16 distinct choices');
}
const actualNative = data.entries.filter(e => e.implementation === 'existing-frame-rudiments');
if (actualNative.length < 25) fail('missing host capability inventory');
console.log(`Video effect research catalogue validated: ${data.entries.length} entries across ${families.size} families, ${actualNative.length} host routes, ${VIDEO_LOOK_PRESETS.length} public look recipes.`);
