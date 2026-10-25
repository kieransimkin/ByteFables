#!/usr/bin/env node
/** Bounded, PUBLIC synthetic cases for independent QR implementations. */
import { encodeQrModel2, qrByteCapacity } from '../dist/index.js';
const cases = [];
for (const version of [1,2,3,4,5,6,7,9,10,12,20,25,32,40]) {
  for (const ecc of ['L','M','Q','H']) {
    const n = Math.min(qrByteCapacity(version, ecc), version*5+4);
    const bytes = Uint8Array.from({length:n},(_,i)=>(i*53+version*13)&255);
    const qr = encodeQrModel2(bytes, {minVersion:version,maxVersion:version,ecc,mask:0});
    cases.push({version,ecc,mask:0,byteHex:Buffer.from(bytes).toString('hex'),
      width:qr.matrix.width, modules:Buffer.from(qr.matrix.toModules()).toString('hex')});
  }
}
process.stdout.write(JSON.stringify(cases)+'\n');
