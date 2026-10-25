import {
  ByteValue, encodeExperimentalStory, decodeExperimentalStory,
  identityFingerprint, renderPixelAvatar, encodeHex
} from '../dist/index.js';

const value = ByteValue.public(Uint8Array.from([0, 1, 2, 3, 255]), {
  namespace: 'danceflow-demo', kind: 'node-id'
});
console.log('Public identity fingerprint:', await identityFingerprint(value));
console.log('SVG identicon bytes:', (await renderPixelAvatar(value)).length);
const story = encodeExperimentalStory(value);
console.log('Prototype story (not a wallet backup):\n' + story);
console.log('Round-trip:', encodeHex(decodeExperimentalStory(story)) === encodeHex(value.toBytes()));
