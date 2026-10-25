/** Blockchain Commons Bytewords BCR-2020-012, including big-endian CRC-32.
 * This is a raw-byte ("brutal") representation, not a typed UR envelope.
 */
import { crc32 } from '../utils/crc32.js';
import { concatBytes, readU32, writeU32 } from '../utils/binary.js';

// Exact 256-word, version-frozen reference dictionary, index = byte value.
const WORDS = `
able acid also apex aqua arch atom aunt
away axis back bald barn belt beta bias
blue body brag brew bulb buzz calm cash
cats chef city claw code cola cook cost
crux curl cusp cyan dark data days deli
dice diet door down draw drop drum dull
duty each easy echo edge epic even exam
exit eyes fact fair fern figs film fish
fizz flap flew flux foxy free frog fuel
fund gala game gear gems gift girl glow
good gray grim guru gush gyro half hang
hard hawk heat help high hill holy hope
horn huts iced idea idle inch inky into
iris iron item jade jazz join jolt jowl
judo jugs jump junk jury keep keno kept
keys kick kiln king kite kiwi knob lamb
lava lazy leaf legs liar limp lion list
logo loud love luau luck lung main many
math maze memo menu meow mild mint miss
monk nail navy need news next noon note
numb obey oboe omit onyx open oval owls
paid part peck play plus poem pool pose
puff puma purr quad quiz race ramp real
redo rich road rock roof ruby ruin runs
rust safe saga scar sets silk skew slot
soap solo song stub surf swan taco task
taxi tent tied time tiny toil tomb toys
trip tuna twin ugly undo unit urge user
vast very veto vial vibe view visa void
vows wall wand warm wasp wave waxy webs
what when whiz wolf work yank yawn yell
yoga yurt zaps zero zest zinc zone zoom`.trim().split(/\s+/);
if (WORDS.length !== 256 || new Set(WORDS).size !== 256) throw new Error('Invalid frozen Bytewords dictionary');
const MINIMAL = WORDS.map(w => w[0]! + w[3]!);
if (new Set(MINIMAL).size !== 256) throw new Error('Invalid Bytewords minimal dictionary');
const INDEX = new Map(WORDS.map((word, i) => [word, i]));
const MIN_INDEX = new Map(MINIMAL.map((word, i) => [word, i]));

export type BytewordsStyle = 'standard' | 'uri' | 'minimal';

export function encodeBytewords(body: Uint8Array, style: BytewordsStyle = 'standard'): string {
  if (!(body instanceof Uint8Array) || body.length > 1048576) throw new RangeError('Bytewords expects bounded bytes');
  if (!['standard', 'uri', 'minimal'].includes(style)) throw new TypeError('Unknown Bytewords style');
  const all = concatBytes(body, writeU32(crc32(body)));
  if (style === 'minimal') return [...all].map(n => MINIMAL[n]).join('');
  return [...all].map(n => WORDS[n]).join(style === 'uri' ? '-' : ' ');
}

export function decodeBytewords(encoded: string, style: BytewordsStyle = 'standard'): Uint8Array {
  if (typeof encoded !== 'string' || encoded.length > 6000000 || !['standard', 'uri', 'minimal'].includes(style)) {
    throw new TypeError('Invalid Bytewords input or style');
  }
  const tokens = style === 'minimal' ? encoded.match(/.{2}/g) ?? [] : encoded.split(style === 'uri' ? '-' : ' ');
  if (style === 'minimal' && encoded.length % 2 || tokens.length < 4 || tokens.length > 1048580) {
    throw new TypeError('Invalid minimal Bytewords length');
  }
  if (style !== 'minimal' && (tokens.length < 4 || tokens.length > 1048580)) throw new TypeError('Invalid Bytewords token count');
  const index = style === 'minimal' ? MIN_INDEX : INDEX;
  const bytes = tokens.map(word => {
    const number = index.get(word);
    if (number === undefined) throw new TypeError('Unknown or noncanonical Bytewords token');
    return number;
  });
  const data = Uint8Array.from(bytes);
  const body = data.slice(0, -4);
  if (crc32(body) !== readU32(data, data.length - 4)) throw new TypeError('Bytewords checksum mismatch');
  return body;
}

export const BYTEWORDS_WORDLIST = Object.freeze([...WORDS]);
