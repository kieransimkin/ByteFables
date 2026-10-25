import { test } from 'node:test';
import assert from 'node:assert/strict';
import {
  UrTestXoshiro256, chooseUrTestFragments, encodeUrBytesMultipartTestOnly,
  decodeUrBytesMultipartTestOnly, parseUrTestPart, UrBytesTestDecoder
} from '../dist/codecs/ur-multipart-test.js';

const source = (n) => Uint8Array.from({length:n}, (_,i) => (i * 43 + 7) & 255);

test('BCR-2024-001 published Wolf xoshiro and shuffle vectors', async () => {
  const rng = await UrTestXoshiro256.fromString('Wolf');
  assert.deepEqual(Array.from({length:20}, () => Number(rng.next() % 100n)),
    [42,81,85,8,82,84,76,73,70,88,2,74,40,48,77,54,88,7,5,88]);
  const shuffle = await UrTestXoshiro256.fromString('Wolf');
  const values = [1,2,3,4,5,6,7,8,9,10];
  assert.deepEqual(Array.from({length:10},()=>values.splice(shuffle.nextIndex(values.length),1)[0]),
    [6,4,9,3,10,5,7,8,1,2]);
});

test('BCR-2024-001 pure part selection, mixed deterministic sequence', async () => {
  assert.deepEqual(await chooseUrTestFragments(1,5,0x12345678), [0]);
  assert.deepEqual(await chooseUrTestFragments(5,5,0x12345678), [4]);
  const a = await chooseUrTestFragments(101,5,0x12345678);
  const b = await chooseUrTestFragments(101,5,0x12345678);
  assert.deepEqual(a, b);
  assert.ok(a.length>0 && a.length<=5 && new Set(a).size === a.length);
});

test('BCR-2024-001 published 50-frame fragment chooser vector', async () => {
  const {crc32} = await import('../dist/utils/crc32.js');
  const rng = await UrTestXoshiro256.fromString('Wolf');
  const sample=Uint8Array.from({length:1024},()=>Math.floor(rng.nextDouble()*256));
  const checksum=crc32(sample);
  assert.equal(checksum,0x2f19f3bb);
  const expected=[
    [0],[1],[2],[3],[4],[5],[6],[7],[8],[9],[10],
    [9],[2,5,6,8,9,10],[8],[1,5],[1],[0,2,4,5,8,10],[5],[2],[2],
    [0,1,3,4,5,7,9,10],[0,1,2,3,5,6,8,9,10],
    [0,2,4,5,7,8,9,10],[3,5],[4],
    [0,1,2,3,4,5,6,7,8,9,10],[0,1,3,4,5,6,7,9,10],
    [6],[5,6],[7],[4,9,10],[5],[10],[1,3,4,5],[6,8],[9],
    [4,5,6,8],[4],[0,10],[2,5,7,10],[4],[0,2,4,6,7,10],
    [9],[1],[3,6],[3,8],[1,2,6,9],[0,2,4,5,6,7,9],[0,4],[9]
  ];
  const actual=[];
  for(let n=1;n<=50;n++)actual.push(await chooseUrTestFragments(n,11,checksum));
  assert.deepEqual(actual,expected);
});

test('UR v2 single-part is compatible with existing test-only codec', async () => {
  const { encodeUrBytesTestOnly, decodeUrBytesTestOnly } = await import('../dist/codecs/ur-bytes-test.js');
  const value = source(4);
  const packet = await encodeUrBytesMultipartTestOnly(value, { fragmentBytes:80 });
  assert.equal(packet.fragmentCount,1);
  assert.equal(packet.frames[0],encodeUrBytesTestOnly(value));
  assert.deepEqual(await decodeUrBytesMultipartTestOnly(packet.frames),value);
  assert.deepEqual(decodeUrBytesTestOnly(packet.frames[0]),value);
});

test('standard UR multipart pure and fountain frames restore arbitrary bytes', async () => {
  for (const size of [16,32,64,128,255,512,1024,4096]) {
    const bytes=source(size);
    const packet=await encodeUrBytesMultipartTestOnly(bytes, {fragmentBytes:64,extraMixedFrames:size <= 60 ? 0 : Math.min(300,Math.ceil(size/64)*8)});
    assert.ok(packet.fragmentCount>=1);
    const first=packet.frames.slice(0,packet.fragmentCount);
    assert.deepEqual(await decodeUrBytesMultipartTestOnly(first.reverse()),bytes);
    if(packet.fragmentCount>1){
      const mixed=packet.frames.slice(packet.fragmentCount);
      assert.deepEqual(await decodeUrBytesMultipartTestOnly(mixed),bytes);
      const decoder=new UrBytesTestDecoder();
      for(const frame of packet.frames.slice(0,packet.fragmentCount))await decoder.receive(frame);
      assert.equal(decoder.progress.complete,true);
      assert.deepEqual(decoder.result,bytes);
    }
  }
});

test('UR decoder tolerates out-of-order, duplicates, and recovers mixed loss', async () => {
  const packet=await encodeUrBytesMultipartTestOnly(source(512),{fragmentBytes:40,extraMixedFrames:90});
  const decoder=new UrBytesTestDecoder();
  const frames=[...packet.frames.slice(packet.fragmentCount)].reverse();
  for(const text of frames) {
    await decoder.receive(text);
    if(decoder.result)break;
  }
  assert.deepEqual(decoder.result,source(512));
  const second=new UrBytesTestDecoder();
  assert.equal(await second.receive(packet.frames[0]),true);
  assert.equal(await second.receive(packet.frames[0]),false);
  await assert.rejects(second.receive('ur:bytes/99-16/'+packet.frames[0].split('/')[2]),/conflicting|noncanonical/i);
});

test('UR parsing rejects errors, corrupt data, and mixed sessions', async () => {
  const packet=await encodeUrBytesMultipartTestOnly(source(300),{fragmentBytes:32,extraMixedFrames:15});
  assert.equal(parseUrTestPart(packet.frames[0]).seqNum,1);
  const altered=packet.frames[0].replace(/.$/,'z');
  assert.throws(()=>parseUrTestPart(altered),/checksum|token|Invalid/i);
  const decoder=new UrBytesTestDecoder();
  await decoder.receive(packet.frames[0]);
  const wrong=await encodeUrBytesMultipartTestOnly(source(310),{fragmentBytes:32});
  await assert.rejects(decoder.receive(wrong.frames[1]),/Mixed|incompatible/i);
  await assert.rejects(decodeUrBytesMultipartTestOnly([packet.frames[0]]),/Incomplete/i);
  await assert.rejects(decodeUrBytesMultipartTestOnly([]),/Expected/i);
  await assert.rejects(encodeUrBytesMultipartTestOnly(new Uint8Array(0)),/1..4096/i);
  await assert.rejects(encodeUrBytesMultipartTestOnly(source(30),{fragmentBytes:512,extraMixedFrames:1}),/single-part/i);
});

test('UR packet fields encode exactly five CBOR array entries; external bytewords decoder compatible', async () => {
  const {decodeBytewords} = await import('../dist/codecs/bytewords.js');
  const {decodeDeterministicCbor} = await import('../dist/framing/cbor.js');
  const packet=await encodeUrBytesMultipartTestOnly(source(100),{fragmentBytes:20});
  const raw=packet.frames[1].split('/')[2];
  const decoded=decodeDeterministicCbor(decodeBytewords(raw,'minimal'));
  assert.equal(decoded.length,5);
  assert.deepEqual(decoded.slice(0,3),[2,packet.fragmentCount,102]);
});

test('frozen UR test fixture remains stable for cross-runtime comparisons', async () => {
  const {readFileSync} = await import('node:fs');
  const file=new URL('./vectors/ur-multipart-v1.json',import.meta.url);
  const fixture=JSON.parse(readFileSync(file,'utf8'));
  const packet=await encodeUrBytesMultipartTestOnly(Uint8Array.from(Buffer.from(fixture.sourceHex,'hex')),
    {fragmentBytes:fixture.fragmentBytes,extraMixedFrames:fixture.extraMixedFrames});
  assert.equal(packet.fragmentCount,fixture.count);
  assert.deepEqual(packet.frames,fixture.frames);
  assert.deepEqual(await decodeUrBytesMultipartTestOnly(fixture.frames),
    Uint8Array.from(Buffer.from(fixture.sourceHex,'hex')));
});
