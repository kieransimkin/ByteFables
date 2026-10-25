#!/usr/bin/env node
/** Generate/check JSON manifest snapshot from the single canonical TS source. */
import { readFile, writeFile } from 'node:fs/promises';
import { FORMAT_MANIFEST, verifyBuiltinRegistry } from '../dist/index.js';
verifyBuiltinRegistry();
const path = new URL('../manifests/formats-v1.json', import.meta.url);
const output = `${JSON.stringify({ schema: 'bytefables-format-manifest-1', formats: FORMAT_MANIFEST }, null, 2)}\n`;
if (process.argv.slice(2).join(' ') === '--write') {
  await writeFile(path, output, { encoding: 'utf8' });
  console.log('Wrote canonical manifest');
} else if (process.argv.slice(2).join(' ') === '--check') {
  const existing = await readFile(path, 'utf8');
  if (existing !== output) throw new Error('Manifest snapshot stale: run node scripts/manifest.mjs --write');
  console.log('Manifest snapshot verified');
} else {
  throw new Error('Use --write or --check');
}
