#!/usr/bin/env node
/** Independently pins the official source text and compiled codebook in CI. */
import { createHash } from 'node:crypto';
import { readFile } from 'node:fs/promises';
import assert from 'node:assert/strict';
import { BIP39_ENGLISH } from '../dist/index.js';
const source = await readFile(new URL('../src/codecs/wordlists/bip39-english.txt', import.meta.url));
const digest = createHash('sha256').update(source).digest('hex');
assert.equal(digest, '2f5eed53a4727b4bf8880d8f3f199efc90e58503646d9ff8eff3a2ed3b24dbda');
const words = source.toString('utf8').trimEnd().split('\n');
assert.equal(words.length, 2048);
assert.deepEqual(words, BIP39_ENGLISH);
assert.equal(words.length, new Set(words).size);
console.log('Official BIP-39 English wordlist and frozen TS bundle verified');
