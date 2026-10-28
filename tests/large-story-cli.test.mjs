import test from 'node:test';
import assert from 'node:assert/strict';
import { execFileSync, spawnSync } from 'node:child_process';
import { mkdtempSync, writeFileSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';

const binary='bin/bytefables.mjs';
const invoke=(args)=>spawnSync(process.execPath,[binary,...args],{cwd:process.cwd(),encoding:'utf8',timeout:15000});

test('public grammar metadata and central experimental codec manifest are discoverable',()=>{
  const result=invoke(['story-large-lexicons']);
  assert.equal(result.status,0,result.stderr);
  const doc=JSON.parse(result.stdout);
  assert.deepEqual(doc.counts,{nouns:16396,adjectives:10569,verbs:3554});
  assert.equal(doc.sentenceBits,68);
  const formats=JSON.parse(invoke(['formats','--json']).stdout);
  assert.ok(formats.some(f=>f.formatId==='codec/large-story-v1' && f.maturity==='experimental'));
});

test('CLI encodes and decodes a real public sentence via raw file',()=>{
  const dir=mkdtempSync(join(tmpdir(),'bytefables-large-cli-'));
  try {
    const out=invoke(['story-large-encode','--confirm-public','--public-hex','000102030405',
      '--namespace','danceflow','--kind','node-id','--locale','en-GB','--raw']);
    assert.equal(out.status,0,out.stderr);
    assert.match(out.stdout,/^BYTEFABLES-LARGE-STORY-V1 en-GB\/1\n/);
    const path=join(dir,'story-public.txt');writeFileSync(path,out.stdout);
    const restored=invoke(['story-large-decode','--confirm-public','--story-file',path]);
    assert.equal(restored.status,0,restored.stderr);
    assert.equal(JSON.parse(restored.stdout).publicHex,'000102030405');
    assert.equal(JSON.parse(restored.stdout).locale,'en-GB');
  } finally { rmSync(dir,{recursive:true,force:true}); }
});

test('CLI requires explicit public confirmation and rejects secret claim and unsupported locale',()=>{
  const args=['--public-hex','deadbeef','--namespace','danceflow','--kind','node-id'];
  assert.notEqual(invoke(['story-large-encode',...args]).status,0);
  assert.notEqual(invoke(['story-large-encode','--confirm-public',...args,'--locale','fr-FR']).status,0);
  assert.notEqual(invoke(['story-large-decode','--story-file','does-not-exist']).status,0);
});
