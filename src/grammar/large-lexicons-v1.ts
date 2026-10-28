/**
 * ByteFables experimental large English lexicons. Public values only.
 * Dataset indices are deliberately fixed, never shuffled, normalised or sorted.
 * en-US/en-GB share the SAME conceptual index, but have distinct written forms.
 */
import { LARGE_LEXICON_DATA_V1 } from './large-lexicon-data-v1.js';

export type LexiconRoleV1 = 'nouns' | 'adjectives' | 'verbs';
export type LexiconLocaleV1 = 'en-US' | 'en-GB';
export const LARGE_LEXICONS_V1 = 'bytefables.large-lexicons.v1' as const;
export const LARGE_LEXICON_COUNTS_V1 = Object.freeze({ nouns: 16396, adjectives: 10569, verbs: 3554 });

interface Dictionary {
  readonly words: readonly string[];
  readonly reverse: ReadonlyMap<string, number>;
}
const cache = new Map<string, Dictionary>();
const ROLES: readonly LexiconRoleV1[] = ['nouns', 'adjectives', 'verbs'];
const LOCALES: readonly LexiconLocaleV1[] = ['en-US', 'en-GB'];

function get(role: LexiconRoleV1, locale: LexiconLocaleV1): Dictionary {
  if (!ROLES.includes(role) || !LOCALES.includes(locale)) {
    throw new TypeError('Unsupported large lexicon role or locale');
  }
  const id = `${role}:${locale}`;
  const existing = cache.get(id);
  if (existing) return existing;
  const source = LARGE_LEXICON_DATA_V1[role];
  const pos = locale === 'en-US' ? 0 : 1;
  const words = source.split('\n').map(line => {
    const alternatives = line.split('|');
    if (alternatives.length > 2) throw new TypeError('Invalid locale alignment');
    return alternatives[pos] ?? alternatives[0]!;
  });
  if (words.length !== LARGE_LEXICON_COUNTS_V1[role] ||
      words.some(word => !/^[a-z]+$/.test(word)) ||
      new Set(words).size !== words.length) {
    throw new TypeError('Invalid large lexicon v1 source; cannot decode safely');
  }
  const frozen = Object.freeze(words);
  const dictionary = Object.freeze({ words: frozen, reverse: new Map(frozen.map((word, index) => [word, index])) });
  cache.set(id, dictionary);
  return dictionary;
}

/** Unmodifiable word array. Never reorder, deduplicate or translate indices. */
export function largeLexiconWordsV1(role: LexiconRoleV1, locale: LexiconLocaleV1): readonly string[] {
  return get(role, locale).words;
}
export function largeLexiconWordV1(role: LexiconRoleV1, locale: LexiconLocaleV1, index: number): string {
  if (!Number.isSafeInteger(index) || index < 0 || index >= LARGE_LEXICON_COUNTS_V1[role]) {
    throw new RangeError('Large lexicon index out of bounds');
  }
  return get(role, locale).words[index]!;
}
export function largeLexiconIndexV1(role: LexiconRoleV1, locale: LexiconLocaleV1, word: string): number {
  if (typeof word !== 'string' || !/^[a-z]+$/.test(word)) {
    throw new TypeError('Large lexicon words require exact lowercase ASCII spelling');
  }
  const index = get(role, locale).reverse.get(word);
  if (index === undefined) throw new RangeError(`Unknown ${locale} ${role} word`);
  return index;
}

/** A regional spelling changes the output text but never the underlying index. */
export function convertLexiconWordV1(role: LexiconRoleV1, input: LexiconLocaleV1,
  output: LexiconLocaleV1, word: string): string {
  return largeLexiconWordV1(role, output, largeLexiconIndexV1(role, input, word));
}
