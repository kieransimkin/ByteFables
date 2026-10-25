import test from 'node:test';
import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';

function cli(...args) {
  return spawnSync(process.execPath, ['bin/bytefables.mjs', ...args],
    { cwd: new URL('..', import.meta.url), encoding: 'utf8', timeout: 4000, maxBuffer: 512 * 1024 });
}

test('public-only CLI lists formats, plans and emits deterministic FrameRudiments host layer', () => {
  const listing = cli('formats', '--json');
  assert.equal(listing.status, 0, listing.stderr);
  const formats = JSON.parse(listing.stdout);
  assert.ok(formats.some(f => f.formatId === 'exporter/framerudiments-layer-v1' &&
    f.maturity === 'experimental'));
  const request = ['framerudiments-layer', '--confirm-public', '--public-hex', '000102ff',
    '--namespace', 'danceflow', '--kind', 'node-id', '--id', 'avatar-one',
    '--bounds', '0,0,128,128', '--palette', 'mono'];
  const result = cli(...request);
  assert.equal(result.status, 0, result.stderr);
  const layer = JSON.parse(result.stdout);
  assert.equal(layer.id, 'avatar-one');
  assert.equal(layer.renderer, 'bytefables-pixel-v1');
  assert.equal(layer.style.palette, 'mono');
  assert.match(layer.style.digest_hex, /^[0-9a-f]{64}$/);
  assert.equal(cli(...request).stdout, result.stdout);
});

test('public-only CLI refuses unconfirmed or invalid input without dumping it', () => {
  for (const args of [
    ['framerudiments-layer', '--public-hex', 'ab12', '--namespace', 'x', '--kind', 'y'],
    ['framerudiments-layer', '--confirm-public', '--public-hex', 'bad hex',
      '--namespace', 'x', '--kind', 'y'],
    ['framerudiments-layer', '--confirm-public', '--public-hex', '1234',
      '--namespace', 'x', '--kind', 'y', '--bounds', '0,0,0,0'],
    ['framerudiments-layer', '--confirm-public', '--public-hex', '1234',
      '--namespace', 'x', '--kind', 'y', '--untrusted', 'x']
  ]) {
    const result = cli(...args);
    assert.notEqual(result.status, 0);
    assert.match(result.stderr, /^ByteFables:/);
    assert.doesNotMatch(result.stderr, /ab12|1234|bad hex/);
  }
});

test('watermark-plan CLI covers each public carrier without promising an embedder', () => {
  const base = ['watermark-plan', '--confirm-public', '--public-hex', '000102ff',
    '--namespace', 'danceflow', '--kind', 'node-id'];
  const cases = [
    ['image', ['--mime-type', 'image/png', '--width', '512', '--height', '512']],
    ['audio', ['--mime-type', 'audio/wav', '--sample-rate', '48000', '--channels', '2', '--duration-seconds', '12']],
    ['video', ['--mime-type', 'video/mp4', '--width', '640', '--height', '480', '--fps', '24', '--duration-seconds', '8']],
    ['text', ['--mime-type', 'text/plain', '--token-count', '2000', '--generation-controlled']]
  ];
  for (const [kind, args] of cases) {
    const cmd = [...base, '--carrier', kind, ...args, '--digest-bytes', '16'];
    const result = cli(...cmd);
    assert.equal(result.status, 0, result.stderr);
    const plan = JSON.parse(result.stdout);
    assert.equal(plan.carrier, kind);
    assert.equal(plan.messageBits, 208);
    assert.equal(plan.eligibleForResearch, true);
    assert.equal(plan.embedderAvailable, false);
    assert.equal(plan.detectorAvailable, false);
    assert.equal(cli(...cmd).stdout, result.stdout);
  }
  const bad = cli(...base, '--carrier', 'text', '--mime-type', 'text/plain',
    '--token-count', '100', '--digest-bytes', '7');
  assert.notEqual(bad.status, 0);
  assert.doesNotMatch(bad.stderr, /000102ff/);
});
