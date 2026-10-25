import test from 'node:test';
import assert from 'node:assert/strict';
import { CATALOGUE } from '../dist/index.js';

test('all capabilities publish maturity, safety, and reversibility fields', () => {
  assert.equal(new Set(CATALOGUE.map(x => x.id)).size, CATALOGUE.length);
  for (const entry of CATALOGUE) {
    assert.ok(['lossless', 'identity', 'archival'].includes(entry.category));
    assert.ok(['foundation', 'experimental', 'planned'].includes(entry.maturity));
    assert.equal(typeof entry.reversible, 'boolean');
    assert.equal(typeof entry.handlesSecrets, 'boolean');
    if (entry.maturity === 'planned') assert.equal(entry.handlesSecrets, false);
  }
});
