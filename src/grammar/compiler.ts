/**
 * Small deterministic, unambiguous grammar-pack compiler.
 * Currently accepts fixed-length, power-of-two slots, each 1..8 bits.
 * The first literal token identifies a grammar and is unique in its pack.
 */
export type GrammarPart =
  | Readonly<{ type: 'literal'; token: string }>
  | Readonly<{ type: 'choice'; role: string; words: readonly string[] }>;

export interface GrammarSpec {
  readonly id: string;
  readonly parts: readonly GrammarPart[];
}

export interface GrammarPackSpec {
  readonly id: string;
  readonly version: number;
  readonly grammars: readonly GrammarSpec[];
}

export interface CompiledGrammar {
  readonly id: string;
  readonly parts: readonly GrammarPart[];
  readonly payloadBits: number;
  readonly marker: string;
}

export interface CompiledGrammarPack {
  readonly id: string;
  readonly version: number;
  readonly grammars: readonly CompiledGrammar[];
  readonly selectorBits: number;
  readonly payloadBits: number;
  readonly sentenceBits: number;
}

const WORD = /^[a-z]+(?:-[a-z]+)*$/;
const LITERAL = /^[A-Za-z]+(?:-[A-Za-z]+)*$/;
const ID = /^[a-z][a-z0-9-]{0,63}$/;

function isPowerOfTwo(value: number): boolean {
  return Number.isInteger(value) && value > 0 && (value & (value - 1)) === 0;
}

export function compileGrammarPack(spec: GrammarPackSpec): CompiledGrammarPack {
  if (!ID.test(spec.id) || !Number.isSafeInteger(spec.version) || spec.version < 1) {
    throw new TypeError('Grammar pack requires stable ID and positive integer version');
  }
  if (!isPowerOfTwo(spec.grammars.length) || spec.grammars.length > 16) {
    throw new TypeError('Number of grammars must be a power of two (1 to 16)');
  }
  const ids = new Set<string>();
  const markers = new Set<string>();
  const grammars: CompiledGrammar[] = spec.grammars.map(g => {
    if (!ID.test(g.id) || ids.has(g.id)) throw new TypeError('Duplicate or invalid grammar ID');
    ids.add(g.id);
    if (!g.parts.length || g.parts.length > 32 || g.parts[0]?.type !== 'literal') {
      throw new TypeError('Grammar must start with a literal token and have 1–32 parts');
    }
    const marker = g.parts[0].token;
    if (!LITERAL.test(marker) || markers.has(marker)) {
      throw new TypeError('Grammar must have a unique literal first token');
    }
    markers.add(marker);
    let payloadBits = 0;
    const roles = new Set<string>();
    const parts = g.parts.map(part => {
      if (part.type === 'literal') {
        if (!LITERAL.test(part.token)) throw new TypeError('Invalid literal token');
        return Object.freeze({ type: 'literal' as const, token: part.token });
      }
      if (part.type !== 'choice' || !ID.test(part.role) || roles.has(part.role) ||
          !isPowerOfTwo(part.words.length) || part.words.length < 2 || part.words.length > 256) {
        throw new TypeError('Choice requires a distinct role and a power-of-two 2–256 wordlist');
      }
      roles.add(part.role);
      const words = [...part.words];
      if (words.some(w => !WORD.test(w)) || new Set(words).size !== words.length) {
        throw new TypeError(`Choice '${part.role}' has invalid or duplicate words`);
      }
      payloadBits += Math.log2(words.length);
      return Object.freeze({ type: 'choice' as const, role: part.role, words: Object.freeze(words) });
    });
    if (payloadBits === 0) throw new TypeError('Grammar has no data-bearing slots');
    return Object.freeze({ id: g.id, marker, parts: Object.freeze(parts), payloadBits });
  });
  const payloadBits = grammars[0]!.payloadBits;
  if (grammars.some(g => g.payloadBits !== payloadBits)) {
    throw new TypeError('All grammars in a pack must carry the same number of payload bits');
  }
  const selectorBits = Math.log2(grammars.length);
  return Object.freeze({ id: spec.id, version: spec.version,
    grammars: Object.freeze(grammars), selectorBits, payloadBits,
    sentenceBits: selectorBits + payloadBits });
}

function getBits(bits: readonly number[], from: number, count: number): number {
  let output = 0;
  for (let i = 0; i < count; i++) {
    const b = bits[from + i];
    if (b !== 0 && b !== 1) throw new TypeError('Missing or invalid sentence bit');
    output = output * 2 + b;
  }
  return output;
}

function toBits(value: number, count: number): number[] {
  return Array.from({ length: count }, (_, i) => (value >>> (count - 1 - i)) & 1);
}

export function encodeSentence(pack: CompiledGrammarPack, bits: readonly number[]): string {
  if (bits.length !== pack.sentenceBits) throw new RangeError('Incorrect sentence bit length');
  const selector = getBits(bits, 0, pack.selectorBits);
  const grammar = pack.grammars[selector]!;
  let offset = pack.selectorBits;
  const words = grammar.parts.map(part => {
    if (part.type === 'literal') return part.token;
    const count = Math.log2(part.words.length);
    const index = getBits(bits, offset, count);
    offset += count;
    return part.words[index]!;
  });
  return `${words.join(' ')}.`;
}

export function decodeSentence(pack: CompiledGrammarPack, sentence: string): number[] {
  if (typeof sentence !== 'string' || sentence.length > 512 || !sentence.endsWith('.')) {
    throw new TypeError('Invalid sentence terminator');
  }
  const words = sentence.slice(0, -1).split(' ');
  const grammarIndex = pack.grammars.findIndex(g => g.marker === words[0]);
  if (grammarIndex < 0) throw new TypeError('Unrecognised grammar marker');
  const grammar = pack.grammars[grammarIndex]!;
  if (words.length !== grammar.parts.length) throw new TypeError('Incorrect sentence shape');
  const bits = toBits(grammarIndex, pack.selectorBits);
  for (let i = 0; i < words.length; i++) {
    const part = grammar.parts[i]!;
    const word = words[i]!;
    if (part.type === 'literal') {
      if (part.token !== word) throw new TypeError('Unexpected grammar literal');
    } else {
      const index = part.words.indexOf(word);
      if (index < 0) throw new TypeError(`Unknown word in '${part.role}' slot`);
      bits.push(...toBits(index, Math.log2(part.words.length)));
    }
  }
  return bits;
}
