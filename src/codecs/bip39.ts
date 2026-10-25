/** BIP-39 English entropy <-> mnemonic, for PUBLIC fixtures and interoperability
 * evaluation only. No wallet seed creation/import, secret handling or storage.
 * An actual seed/entropy used to control funds is secret, regardless of label.
 */
import { assertPublicValue, type PublicByteValue } from '../value.js';
import { sha256 } from '../identity/sha256.js';
import { BIP39_ENGLISH } from './wordlists/bip39-english.js';
import { bytesToBits, bitsToBytes } from '../utils/binary.js';

const SIZES = new Set([16, 20, 24, 28, 32]);
const WORDS = new Map(BIP39_ENGLISH.map((word, index) => [word, index]));
if (BIP39_ENGLISH.length !== 2048 || WORDS.size !== 2048 ||
    BIP39_ENGLISH[0] !== 'abandon' || BIP39_ENGLISH[2047] !== 'zoo') {
  throw new Error('BIP-39 wordlist was altered');
}

export async function encodeBip39PublicEntropy(value: PublicByteValue): Promise<string> {
  assertPublicValue(value);
  const entropy = value.toBytes();
  if (!SIZES.has(entropy.length)) throw new RangeError('BIP-39 only encodes 128/160/192/224/256 bits of entropy');
  const checksumBits = entropy.length / 4;
  const bits = bytesToBits(entropy).concat(bytesToBits(await sha256(entropy)).slice(0, checksumBits));
  const output: string[] = [];
  for (let i = 0; i < bits.length; i += 11) {
    const index = bits.slice(i, i + 11).reduce((n, bit) => (n << 1) | bit, 0);
    output.push(BIP39_ENGLISH[index]!);
  }
  return output.join(' ');
}

/** Explicitly decodes PUBLIC TEST mnemonics. Never pass an actual wallet seed here. */
export async function decodeBip39PublicMnemonic(text: string): Promise<Uint8Array> {
  if (typeof text !== 'string' || text.length > 240 || !/^[a-z]+(?: [a-z]+)*$/.test(text)) {
    throw new TypeError('BIP-39 English words must be canonical lowercase ASCII separated by one space');
  }
  const tokens = text.split(' ');
  if (![12, 15, 18, 21, 24].includes(tokens.length)) throw new TypeError('Invalid BIP-39 word count');
  const bits: number[] = [];
  for (const token of tokens) {
    const n = WORDS.get(token);
    if (n === undefined) throw new TypeError('Unknown BIP-39 English word');
    for (let i = 10; i >= 0; i--) bits.push((n >>> i) & 1);
  }
  const entropyBits = tokens.length * 32 / 3;
  const entropy = bitsToBytes(bits.slice(0, entropyBits));
  const expected = bytesToBits(await sha256(entropy)).slice(0, bits.length - entropyBits);
  let difference = 0;
  for (let i = 0; i < expected.length; i++) difference |= expected[i]! ^ bits[entropyBits + i]!;
  if (difference) throw new TypeError('BIP-39 checksum mismatch');
  return entropy;
}

export { BIP39_ENGLISH } from './wordlists/bip39-english.js';
