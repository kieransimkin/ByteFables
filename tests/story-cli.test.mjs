import test from 'node:test';
import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import { decodeStoryV2, decodeScheduledStory } from '../dist/index.js';
function run(...args) {
  return spawnSync(process.execPath, ['bin/bytefables.mjs', ...args], { cwd: new URL('..', import.meta.url),
    encoding: 'utf8', timeout: 6000, maxBuffer: 500_000 });
}
const input = ['--confirm-public', '--public-hex', '000102ff', '--namespace', 'test', '--kind', 'public-id'];

test('stage 2 CLI emits verifiable prefix and scheduled public stories', async () => {
  for (const profile of ['prefix', 'scheduled']) {
    const r = run('story-encode', ...input, '--profile', profile, '--theme', 'science', '--stats');
    assert.equal(r.status, 0, r.stderr);
    const result = JSON.parse(r.stdout);
    assert.equal(result.experimental, true);
    assert.equal(result.publicOnly, true);
    const restored = profile === 'prefix' ? await decodeStoryV2(result.story) :
      await decodeScheduledStory(result.story);
    assert.deepEqual(restored.bytes, Uint8Array.of(0, 1, 2, 255));
    assert.equal(run('story-encode', ...input, '--profile', profile, '--theme', 'science', '--stats').stdout,
      r.stdout);
  }
});

test('stage 2 CLI produces FrameRudiments text previews rather than rasterising', () => {
  const r = run('story-preview', ...input, '--theme', 'music', '--max-sentences', '2');
  assert.equal(r.status, 0, r.stderr);
  const preview = JSON.parse(r.stdout);
  assert.equal(preview.target, 'framerudiments.project.v1/identity');
  assert.equal(preview.previewOnly, true);
  assert.ok(preview.omittedSentences > 0);
  assert.deepEqual(preview.effectTargets, ['identity:0', 'identity:1']);
  assert.equal(preview.identities.length, 2);
  assert.ok(preview.identities.every(x => x.style.font_size === 24));
});

test('CLI requires confirmation and rejects private-key kinds and unsupported input', () => {
  const cases = [
    ['story-encode', '--public-hex', 'adff', '--namespace', 'x', '--kind', 'id'],
    ['story-encode', '--confirm-public', '--public-hex', 'adff', '--namespace', 'x', '--kind', 'private-key'],
    ['story-encode', ...input, '--profile', 'malicious'],
    ['story-encode', ...input, '--theme', 'unknown'],
    ['story-preview', ...input, '--box', '0,0,0,0'],
    ['story-preview', ...input, '--max-sentences', '999']
  ];
  for (const args of cases) {
    const r = run(...args);
    assert.notEqual(r.status, 0);
    assert.match(r.stderr, /^ByteFables:/);
    assert.doesNotMatch(r.stderr, /adff/);
  }
});
