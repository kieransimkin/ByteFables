#!/usr/bin/env node
/** CPU-only distribution diagnostic. Tests are evidence, not proof of perfect SHA uniformity. */
import { createHash } from 'node:crypto';
import { ByteValue, deriveShortPublicHashes } from '../dist/index.js';

const count = process.argv.length === 2 ? 10000 : Number(process.argv[2]);
if (!Number.isSafeInteger(count) || count < 1 || count > 100000 || process.argv.length > 3) {
  throw new RangeError('Usage: node scripts/profile-short-hashes.mjs [count 1..100000]');
}
const seen = new Map([[3,new Set()], [4,new Set()], [8,new Set()]]);
const collisions = new Map([[3,0],[4,0],[8,0]]);
const oneCounts = new Map([[3,new Uint32Array(24)],[4,new Uint32Array(32)],[8,new Uint32Array(64)]]);
const domain = Buffer.from('ByteFables:short-hash-distribution-test:v1\0');
for(let i=0;i<count;i++) {
  const idx = Buffer.alloc(4);idx.writeUInt32BE(i);
  const src=createHash('sha256').update(domain).update(idx).digest();
  const value=ByteValue.public(src,{namespace:'bytefables-test',kind:'synthetic-public-hash'});
  for (const item of await deriveShortPublicHashes(value)) {
    const set=seen.get(item.bytes);
    if (set.has(item.hex)) collisions.set(item.bytes,collisions.get(item.bytes)+1);
    set.add(item.hex);
    const bytes=Buffer.from(item.hex,'hex');
    const freq=oneCounts.get(item.bytes);
    for (let bit=0;bit<item.bits;bit++)freq[bit]+=((bytes[bit>>3]>>(7-(bit&7)))&1);
  }
}
const profiles = [3,4,8].map(bytes=>{
  const bits=bytes*8;
  const counts=[...oneCounts.get(bytes)];
  const maxBias=Math.max(...counts.map(n=>Math.abs(n/count-0.5)));
  const outputs=2**bits;
  return {bytes,bits,possibleOutputs:String(2n**BigInt(bits)),
    distinct:seen.get(bytes).size,collisionPairsOrDuplicates:collisions.get(bytes),
    expectedCollidingPairs:count*(count-1)/(2*outputs),
    maxAbsoluteBitFrequencyDeviationFromHalf:maxBias,
    interpretation:'Diagnostic for synthetic public values, NOT cryptographic security or an exact uniformity proof'};
});
console.log(JSON.stringify({schema:'bytefables.short-hash-study.v1',samples:count,
  inputGeneration:'SHA-256 of fixed domain and ascending u32 counter',
  profiles},null,2));
