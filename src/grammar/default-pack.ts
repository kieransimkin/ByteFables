import { compileGrammarPack } from './compiler.js';

/**
 * Deliberately tiny 13-bit demonstration. NOT an interoperable wallet mnemonic.
 * The two markers ('The', 'At') carry one structural selector bit;
 * the three four-bit lexical slots carry another twelve bits.
 * Lexicon ordering is frozen for prototype-1 test vectors.
 */
const adjectives = [
  'brave', 'bright', 'calm', 'curious', 'daring', 'gentle', 'happy', 'merry',
  'quiet', 'shy', 'silly', 'sleepy', 'swift', 'tiny', 'witty', 'zany'
] as const;
const animals = [
  'badger', 'bat', 'bear', 'cat', 'crab', 'dog', 'fox', 'goat',
  'hare', 'mole', 'newt', 'otter', 'owl', 'snail', 'tiger', 'wolf'
] as const;
const adverbs = [
  'always', 'usually', 'often', 'sometimes', 'occasionally', 'rarely',
  'seldom', 'never', 'regularly', 'frequently', 'intermittently',
  'periodically', 'habitually', 'routinely', 'continually', 'sporadically'
] as const;
const verbs = [
  'ambles', 'blinks', 'dances', 'dreams', 'hums', 'jumps', 'listens',
  'marches', 'pauses', 'rests', 'sings', 'sleeps', 'smiles', 'spins',
  'waits', 'wanders'
] as const;

export const DEFAULT_GRAMMAR_PACK = compileGrammarPack({
  id: 'bytefables-demo', version: 1,
  grammars: [
    { id: 'trait-frequency', parts: [
      { type: 'literal', token: 'The' },
      { type: 'choice', role: 'adjective', words: adjectives },
      { type: 'choice', role: 'animal', words: animals },
      { type: 'choice', role: 'adverb', words: adverbs },
      { type: 'literal', token: 'rests' }
    ] },
    { id: 'morning-action', parts: [
      { type: 'literal', token: 'At' },
      { type: 'literal', token: 'dawn' },
      { type: 'literal', token: 'the' },
      { type: 'choice', role: 'adjective', words: adjectives },
      { type: 'choice', role: 'animal', words: animals },
      { type: 'choice', role: 'verb', words: verbs }
    ] }
  ]
});
