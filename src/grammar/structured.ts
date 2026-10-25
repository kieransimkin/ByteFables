/** Stage 2: validated, versioned, reversible sentence grammar compiler.
 * A literal's exact spelling is part of the wire format. Data slots have
 * fixed token counts, permitting bounded deterministic parsing with no NLP.
 */
import { decodeRadixBits, encodeRadixBits, radixCapacityBits } from './radix.js';

export type StoryPart =
  | Readonly<{ type: 'literal'; text: string }>
  | Readonly<{ type: 'choice'; role: string; words: readonly string[] }>
  | Readonly<{ type: 'dependent'; role: string; dependsOn: string; byWord: Readonly<Record<string, readonly string[]>> }>;
export interface StoryTemplateSpec {
  readonly id: string;
  /** Binary prefix code representing actual data bits, not aesthetic entropy. */
  readonly prefix: string;
  readonly parts: readonly StoryPart[];
}
export interface StoryPackSpec {
  readonly id: string;
  readonly version: number;
  readonly templates: readonly StoryTemplateSpec[];
}
export interface CompiledStorySlot {
  readonly type: 'choice' | 'dependent';
  readonly role: string;
  readonly words?: readonly string[];
  readonly dependsOn?: string;
  readonly byWord?: Readonly<Record<string, readonly string[]>>;
  readonly radix: number;
  readonly tokenCount: number;
}
export type CompiledStoryPart = Readonly<{ type: 'literal'; text: string }> | CompiledStorySlot;
export interface CompiledStoryTemplate {
  readonly id: string;
  readonly prefix: string;
  readonly marker: string;
  readonly parts: readonly CompiledStoryPart[];
  readonly radices: readonly number[];
  /** Prefix bits + exact enumerative capacity bits. */
  readonly sentenceBits: number;
  readonly payloadBits: number;
}
export interface CompiledStoryPack {
  readonly id: string;
  readonly version: number;
  readonly templates: readonly CompiledStoryTemplate[];
  readonly minSentenceBits: number;
  readonly maxSentenceBits: number;
}

const IDENTIFIER = /^[a-z][a-z0-9-]{0,63}$/;
const LEXEME = /^[a-z]+(?:-[a-z]+)*(?: [a-z]+(?:-[a-z]+)*){0,3}$/;
const LITERAL = /^[A-Za-z ,.!?\-]{1,96}$/;

function validateWords(words: readonly string[], name: string): { words: readonly string[]; tokenCount: number } {
  if (!Array.isArray(words) || words.length < 2 || words.length > 256 ||
      words.some(w => typeof w !== 'string' || !LEXEME.test(w)) ||
      new Set(words).size !== words.length) {
    throw new TypeError(`Invalid or duplicate words in '${name}'`);
  }
  const tokenCount = words[0]!.split(' ').length;
  if (!words.every(w => w.split(' ').length === tokenCount)) {
    throw new TypeError(`Variable token counts in '${name}' would make parsing ambiguous`);
  }
  return { words: Object.freeze([...words]), tokenCount };
}

export function compileStoryPack(spec: StoryPackSpec): CompiledStoryPack {
  if (!spec || !IDENTIFIER.test(spec.id) || !Number.isSafeInteger(spec.version) || spec.version < 1 ||
      !Array.isArray(spec.templates) || spec.templates.length < 2 || spec.templates.length > 16) {
    throw new TypeError('Story pack requires an ID, version and 2–16 templates');
  }
  const ids = new Set<string>();
  const markers: string[] = [];
  const prefixes: string[] = [];
  const templates = spec.templates.map(t => {
    if (!IDENTIFIER.test(t.id) || ids.has(t.id) || typeof t.prefix !== 'string' ||
        !/^[01]{1,8}$/.test(t.prefix) || !Array.isArray(t.parts) ||
        t.parts.length < 3 || t.parts.length > 32 || t.parts[0]?.type !== 'literal' ||
        t.parts.at(-1)?.type !== 'literal') {
      throw new TypeError('Invalid story template ID, prefix or parts');
    }
    ids.add(t.id);
    prefixes.push(t.prefix);
    const roles = new Map<string, readonly string[]>();
    const usedRoles = new Set<string>();
    const parts: CompiledStoryPart[] = [];
    const radices: number[] = [];
    for (const part of t.parts) {
      if (part.type === 'literal') {
        if (!LITERAL.test(part.text) || (parts.at(-1)?.type !== 'literal' && parts.length > 0 &&
            !/^[ ,.!?]/.test(part.text))) throw new TypeError('Invalid literal text or missing delimiter');
        parts.push(Object.freeze({ type: 'literal' as const, text: part.text }));
      } else {
        if (!IDENTIFIER.test(part.role) || usedRoles.has(part.role) ||
            parts.at(-1)?.type !== 'literal' ||
            !/[ ,.!?]$/.test((parts.at(-1) as { type: 'literal'; text: string }).text)) {
          throw new TypeError('Duplicate/invalid role or adjacent data slots without delimiters');
        }
        usedRoles.add(part.role);
        if (part.type === 'choice') {
          const checked = validateWords(part.words, part.role);
          parts.push(Object.freeze({ type: 'choice', role: part.role,
            words: checked.words, radix: checked.words.length, tokenCount: checked.tokenCount }));
          roles.set(part.role, checked.words);
          radices.push(checked.words.length);
        } else if (part.type === 'dependent') {
          const prior = roles.get(part.dependsOn);
          if (!prior || !part.byWord || Array.isArray(part.byWord) ||
              Object.keys(part.byWord).length !== prior.length ||
              Object.keys(part.byWord).some(w => !prior.includes(w))) {
            throw new TypeError('Dependent dictionary must refer to all words of a preceding independent role');
          }
          let radix = -1;
          let tokenCount = -1;
          const byWord: Record<string, readonly string[]> = Object.create(null);
          for (const word of prior) {
            const checked = validateWords(part.byWord[word]!, part.role);
            if (radix !== -1 && (checked.words.length !== radix || checked.tokenCount !== tokenCount)) {
              throw new TypeError('Dependent branches need equal capacities and token counts');
            }
            radix = checked.words.length;
            tokenCount = checked.tokenCount;
            byWord[word] = checked.words;
          }
          parts.push(Object.freeze({ type: 'dependent', role: part.role,
            dependsOn: part.dependsOn, byWord: Object.freeze(byWord), radix, tokenCount }));
          radices.push(radix);
          // Do not permit transitive dependent dictionaries without explicit model.
        } else {
          throw new TypeError('Unknown grammar part');
        }
      }
    }
    const marker = (parts[0] as { type: 'literal'; text: string }).text;
    if (markers.some(m => marker.startsWith(m) || m.startsWith(marker))) {
      throw new TypeError('Grammar first literal markers must be prefix-distinct');
    }
    markers.push(marker);
    const payloadBits = radixCapacityBits(radices);
    if (payloadBits < 1 || payloadBits + t.prefix.length > 256) {
      throw new RangeError('Grammar capacity outside 1–256 bits');
    }
    return Object.freeze({ id: t.id, prefix: t.prefix, marker,
      parts: Object.freeze(parts), radices: Object.freeze(radices),
      payloadBits, sentenceBits: payloadBits + t.prefix.length });
  });
  for (const p of prefixes) if (prefixes.some(q => p !== q && q.startsWith(p)) ||
      prefixes.filter(q => q === p).length !== 1) {
    throw new TypeError('Story template prefixes must be prefix-free and distinct');
  }
  const longest = Math.max(...prefixes.map(p => p.length));
  const coverage = prefixes.reduce((n, p) => n + (1 << (longest - p.length)), 0);
  if (coverage !== (1 << longest)) throw new TypeError('Template prefix code must be complete');
  return Object.freeze({ id: spec.id, version: spec.version, templates: Object.freeze(templates),
    minSentenceBits: Math.min(...templates.map(t => t.sentenceBits)),
    maxSentenceBits: Math.max(...templates.map(t => t.sentenceBits)) });
}

/** Encode exactly template.payloadBits into grammatical choices. */
export function encodeStructuredSentence(template: CompiledStoryTemplate, bits: readonly number[]): string {
  if (bits.length !== template.payloadBits) throw new RangeError('Wrong sentence payload bit count');
  const digits = encodeRadixBits(bits, template.radices);
  let offset = 0;
  const resolved = new Map<string, string>();
  let output = '';
  for (const part of template.parts) {
    if (part.type === 'literal') { output += part.text; continue; }
    const dictionary = part.type === 'choice' ? part.words! : part.byWord![resolved.get(part.dependsOn!)!];
    if (!dictionary) throw new TypeError('Unresolved grammatical dependency');
    const word = dictionary[digits[offset++]!]!;
    resolved.set(part.role, word);
    output += word;
  }
  return output;
}

/** Returns the prefix and source payload bits, never guessed or normalised text. */
export function decodeStructuredSentence(pack: CompiledStoryPack, sentence: string): number[] {
  if (typeof sentence !== 'string' || sentence.length > 768 || sentence.includes('\n')) {
    throw new TypeError('Invalid sentence text');
  }
  const template = pack.templates.find(t => sentence.startsWith(t.marker));
  if (!template) throw new TypeError('Unknown story template marker');
  let offset = 0;
  const resolved = new Map<string, string>();
  const digits: number[] = [];
  for (const part of template.parts) {
    if (part.type === 'literal') {
      if (!sentence.startsWith(part.text, offset)) throw new TypeError('Incorrect story literal');
      offset += part.text.length;
      continue;
    }
    const dictionary = part.type === 'choice' ? part.words! : part.byWord![resolved.get(part.dependsOn!)!];
    if (!dictionary) throw new TypeError('Unresolved grammatical dependency');
    // Bound each slot to its declared number of lexical words, not greedy regex matching.
    const pattern = new RegExp(`^[a-z]+(?:-[a-z]+)*(?: [a-z]+(?:-[a-z]+)*){${part.tokenCount - 1}}`);
    const match = pattern.exec(sentence.slice(offset));
    if (!match || /[a-z-]/.test(sentence[offset + match[0].length] || '')) {
      throw new TypeError('Unrecognised or noncanonical lexical slot');
    }
    const index = dictionary.indexOf(match[0]);
    if (index === -1) throw new TypeError(`Unknown word in role '${part.role}'`);
    digits.push(index);
    resolved.set(part.role, match[0]);
    offset += match[0].length;
  }
  if (offset !== sentence.length) throw new TypeError('Trailing story text');
  return [...template.prefix.split('').map(Number), ...decodeRadixBits(digits, template.radices)];
}

/** Select a template using the next encoded prefix bits, zero-padding only at EOF. */
export function selectStoryTemplate(pack: CompiledStoryPack, bits: readonly number[]): CompiledStoryTemplate {
  const longest = Math.max(...pack.templates.map(t => t.prefix.length));
  if (bits.slice(0, longest).some(b => b !== 0 && b !== 1)) throw new TypeError('Invalid bits');
  const next = [...bits.slice(0, longest)];
  while (next.length < longest) next.push(0);
  const sequence = next.join('');
  const found = pack.templates.find(t => sequence.startsWith(t.prefix));
  if (!found) throw new TypeError('No matching prefix in grammar pack');
  return found;
}
