#!/usr/bin/env node
/** PUBLIC synthetic corpus -> existing TS atlas planner. This file renders no pixels. */
import { createHash } from 'node:crypto';
import { mkdir, mkdtemp, writeFile, rename, rm, lstat } from 'node:fs/promises';
import { dirname, resolve, join } from 'node:path';
import { fileURLToPath } from 'node:url';

export const SUITE_SCHEMA = 'bytefables.artwork-native-benchmark-suite.v1';
const FAMILIES = ['sigil', 'constellation', 'heraldry', 'topography', 'crystal',
  'mandala', 'cellular', 'branching', 'orbital'];
const PALETTES = ['neon', 'pastel', 'mono'];
const SIZES = [16, 32, 64, 128];
const sha = bytes => createHash('sha256').update(bytes).digest('hex');
const json = value => JSON.stringify(value, null, 2) + '\n';
function integer(value, min, max, label) {
  if (!Number.isSafeInteger(value) || value < min || value > max) throw new Error(`Invalid ${label}`);
  return value;
}
function subset(values, allowed, label) {
  if (!Array.isArray(values) || !values.length || new Set(values).size !== values.length ||
      values.some(v => !allowed.includes(v))) throw new Error(`Invalid ${label}`);
  return [...values];
}
export function validateOptions(options = {}) {
  const cfg = {
    count: integer(options.count ?? 32, 1, 1000, 'count'),
    seed: options.seed ?? 'public-fixture-1',
    families: subset(options.families ?? FAMILIES, FAMILIES, 'families'),
    palettes: subset(options.palettes ?? ['neon'], PALETTES, 'palettes'),
    sizes: subset(options.sizes ?? SIZES, SIZES, 'sizes'),
    complexity: integer(options.complexity ?? 4, 1, 8, 'complexity'),
    columns: integer(options.columns ?? 8, 1, 16, 'columns'),
    rowsPerPage: integer(options.rowsPerPage ?? 16, 1, 16, 'rowsPerPage'),
  };
  if (typeof cfg.seed !== 'string' || !/^[a-zA-Z0-9_-]{1,64}$/.test(cfg.seed)) throw new Error('Invalid public seed label');
  const cases = cfg.families.length * cfg.palettes.length * cfg.sizes.length;
  if (cases * cfg.count > 8192 || cases * cfg.count * (cfg.count - 1) / 2 * 4 > 16_000_000)
    throw new Error('Suite exceeds bounded tile/pair workload; reduce count or style/size selections');
  return cfg;
}
export async function prepareSuite(output, options, { confirmPublic = false } = {}) {
  if (confirmPublic !== true) throw new Error('Explicit PUBLIC confirmation required');
  const cfg = validateOptions(options);
  if (typeof output !== 'string' || !output.length) throw new Error('Output directory required');
  const destination = resolve(output);
  try { await lstat(destination); throw new Error('Output already exists; choose a new directory'); }
  catch (e) { if (e.code !== 'ENOENT') throw e; }
  // Only the existing ByteFables public APIs assign namespaces and compute record digests.
  const { ByteValue, PublicRecord, createFrameRudimentsArtworkAtlas } = await import('../dist/index.js');
  const records = Array.from({ length: cfg.count }, (_, i) => {
    const bytes = createHash('sha256').update('ByteFables:artwork-benchmark-corpus:v1\0')
      .update(cfg.seed).update('\0').update(String(i)).digest();
    return new PublicRecord(ByteValue.public(Uint8Array.from(bytes), {
      namespace: 'bytefables-benchmark', kind: 'fixture-id'
    }), { network: 'synthetic' });
  });
  await mkdir(dirname(destination), { recursive: true });
  const staging = await mkdtemp(join(dirname(destination), '.bf-benchmark-'));
  try {
    await mkdir(join(staging, 'plans'));
    const cases = [];
    for (const family of cfg.families) for (const palette of cfg.palettes) for (const size of cfg.sizes) {
      const id = `${family}-${palette}-${size}`;
      const plan = await createFrameRudimentsArtworkAtlas(records, {
        artwork: family, palette, complexity: cfg.complexity, tileSize: size,
        padding: 4, columns: Math.min(cfg.columns, cfg.count), rowsPerPage: cfg.rowsPerPage
      });
      const payload = json(plan);
      const path = `plans/${id}.json`;
      await writeFile(join(staging, path), payload, { encoding: 'utf8', flag: 'wx' });
      cases.push({ id, plan: path, planSha256: sha(payload), family, palette, sourceSize: size });
    }
    const suite = { schema: SUITE_SCHEMA, publicOnly: true, guarantee: 'presentation-only',
      corpus: { id: 'bytefables.public-benchmark-corpus.v1', seed: cfg.seed, count: cfg.count }, cases };
    await writeFile(join(staging, 'suite.json'), json(suite), { encoding: 'utf8', flag: 'wx' });
    try { await lstat(destination); throw new Error('Output appeared during planning; refusing overwrite'); }
    catch (e) { if (e.code !== 'ENOENT') throw e; }
    await rename(staging, destination);
    return suite;
  } finally { await rm(staging, { recursive: true, force: true }); }
}
export function parseArgs(argv) {
  const result = { options: {}, confirmPublic: false };
  const seen = new Set();
  const keys = { '--count': 'count', '--seed': 'seed', '--families': 'families',
    '--palettes': 'palettes', '--sizes': 'sizes', '--complexity': 'complexity',
    '--columns': 'columns', '--rows-per-page': 'rowsPerPage' };
  for (let i = 0; i < argv.length; i++) {
    const key = argv[i];
    if (seen.has(key)) throw new Error(`Repeated option: ${key}`);
    seen.add(key);
    if (key === '--help') { result.help = true; continue; }
    if (key === '--confirm-public') { result.confirmPublic = true; continue; }
    if (key !== '--output' && !Object.hasOwn(keys, key)) throw new Error(`Unknown option: ${key}`);
    const value = argv[++i];
    if (value === undefined || value.startsWith('--')) throw new Error(`Missing value for ${key}`);
    if (key === '--output') result.output = value;
    else if (['--families', '--palettes'].includes(key)) result.options[keys[key]] = value.split(',');
    else if (key === '--sizes') result.options.sizes = value.split(',').map(Number);
    else result.options[keys[key]] = key === '--seed' ? value : Number(value);
  }
  return result;
}
async function main() {
  const args = parseArgs(process.argv.slice(2));
  if (args.help) {
    console.log('Usage: node scripts/prepare-artwork-benchmark.mjs --confirm-public --output NEW_DIR\n' +
      '  [--count 32] [--seed public-fixture-1] [--families sigil,crystal,...]\n' +
      '  [--palettes neon,pastel,mono] [--sizes 16,32,64,128] [--complexity 4]\n' +
      '  [--columns 8] [--rows-per-page 16]\nSynthetic public fixtures only; no image rendering or model downloads.');
    return;
  }
  const suite = await prepareSuite(args.output, args.options, args);
  console.log(JSON.stringify({ output: resolve(args.output), cases: suite.cases.length,
    identitiesPerCase: suite.corpus.count }, null, 2));
}
if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  main().catch(error => { console.error(`Artwork planning failed: ${error.message}`); process.exitCode = 2; });
}
