import test from 'node:test';
import assert from 'node:assert/strict';
import { createHash, randomBytes } from 'node:crypto';
import { readFile } from 'node:fs/promises';
import {
  ByteValue, PublicRecord, encodeHex, decodeHex, encodePublicRecord, decodePublicRecord,
  encodeDeterministicCbor, decodeDeterministicCbor, publicRecordDigest,
  publicRecordFingerprint, identityFingerprint
} from '../dist/index.js';

const make = (bytes, opts = {}) => new PublicRecord(ByteValue.public(bytes, {
  namespace: 'danceflow', kind: 'node-id'
}), opts);

const hex = data => encodeHex(data);

test('public envelope covers typed metadata, length, all bytes and SHA-256 integrity', async () => {
  const sizes = [0, 1, 16, 20, 24, 28, 32, 33, 48, 64, 65, 78, 96, 128, 4096, 1048576];
  for (const len of sizes) {
    const data = Uint8Array.from({ length: len }, (_, i) => (i * 131) & 255);
    if (len > 0) data[0] = 0;
    const record = make(data, { algorithm: 'sha256', network: 'bitcoin', endian: 'big', schemaVersion: 2 });
    const encoded = await encodePublicRecord(record);
    data.fill(255);
    const decoded = await decodePublicRecord(encoded);
    assert.equal(decoded.namespace, 'danceflow');
    assert.equal(decoded.kind, 'node-id');
    assert.equal(decoded.algorithm, 'sha256');
    assert.equal(decoded.network, 'bitcoin');
    assert.equal(decoded.endian, 'big');
    assert.equal(decoded.schemaVersion, 2);
    assert.equal(decoded.byteLength, len);
    assert.deepEqual(decoded.toBytes(), Uint8Array.from({ length: len }, (_, i) => i === 0 ? 0 : (i * 131) & 255));
    assert.deepEqual(await encodePublicRecord(decoded), encoded);
  }
});

test('digest matches independent SHA-256 computation and fixed pinned vector', async () => {
  const record = make(Uint8Array.of(0, 1, 2, 255));
  const encoded = await encodePublicRecord(record);
  const parsed = decodeDeterministicCbor(encoded);
  assert.equal(parsed.get(0), 'BF-PUBLIC');
  assert.equal(parsed.get(1), 1);
  const expectedHash = createHash('sha256')
    .update('ByteFables:public-cbor-envelope:v1\0')
    .update(encodeDeterministicCbor(new Map([...parsed].filter(([k]) => k !== 5))))
    .digest('hex');
  assert.equal(hex(parsed.get(5)), expectedHash);
  assert.equal(hex(await publicRecordDigest(record)), expectedHash);
  const fixtures = JSON.parse(await readFile(new URL('./vectors/public-cbor-v1.json', import.meta.url)));
  assert.equal(hex(encoded), fixtures.testPublicRecord.envelopeHex);
  assert.equal(await publicRecordFingerprint(record), fixtures.testPublicRecord.fingerprint);
  assert.equal(expectedHash, fixtures.testPublicRecord.fullDigestHex);
});

test('tampered checksums, metadata, lengths, versions and types are rejected', async () => {
  const record = make(Uint8Array.of(0, 1, 2));
  const good = await encodePublicRecord(record);
  const wire = decodeDeterministicCbor(good);
  const mutated = change => {
    const m = new Map(wire);
    change(m);
    return encodeDeterministicCbor(m);
  };
  for (const bad of [
    mutated(x => { const bytes = new Uint8Array(x.get(4)); bytes[0] = 99; x.set(4, bytes); }),
    mutated(x => x.set(3, 4)),
    mutated(x => x.set(1, 2)),
    mutated(x => x.set(0, 'NOT-BF')),
    mutated(x => x.set(6, 1)),
    mutated(x => x.set(5, Uint8Array.of(1))),
    mutated(x => { const c = new Map(x.get(2)); c.set(1, 'private-key'); x.set(2, c); }),
    mutated(x => { const c = new Map(x.get(2)); c.set(7, 'extra'); x.set(2, c); }),
    good.subarray(0, good.length - 1)
  ]) {
    await assert.rejects(() => decodePublicRecord(bad));
  }
  assert.throws(() => new PublicRecord(ByteValue.secret(Uint8Array.of(1), { namespace: 'x', kind: 'secret' })));
  assert.throws(() => new PublicRecord(ByteValue.public(Uint8Array.of(1), { namespace: 'x', kind: 'node' }), { algorithm: 'secret key!' }));
});

test('record metadata changes typed digest without changing old bf1 identity scheme', async () => {
  const bytes = Uint8Array.of(0, 0, 1, 2);
  const records = [
    make(bytes), make(bytes, { network: 'bitcoin' }), make(bytes, { algorithm: 'sha256' }),
    make(bytes, { endian: 'little' }), make(bytes, { schemaVersion: 2 })
  ];
  const fingerprint = await Promise.all(records.map(record => publicRecordFingerprint(record)));
  assert.equal(new Set(fingerprint).size, records.length);
  const old = await Promise.all(records.map(record => identityFingerprint(record.value)));
  assert.equal(new Set(old).size, 1);
});

test('public record decoder fuzz-style round trips and rejection of random corruption', async () => {
  for (let i = 0; i < 70; i++) {
    const data = randomBytes(i * 13 % 129);
    const record = make(data);
    const encoded = await encodePublicRecord(record);
    const recovered = await decodePublicRecord(encoded);
    assert.deepEqual(recovered.toBytes(), new Uint8Array(data));
    // Corrupt a payload byte in a still-valid CBOR envelope; checksum must reject.
    if (data.length) {
      const wire = decodeDeterministicCbor(encoded);
      const altered = new Uint8Array(wire.get(4));
      altered[0] ^= 1;
      wire.set(4, altered);
      await assert.rejects(() => decodePublicRecord(encodeDeterministicCbor(wire)));
    }
  }
});
