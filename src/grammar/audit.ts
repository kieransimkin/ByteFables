/** Human-facing lexical warnings, not an exhaustive linguistic safety proof. */
export interface LexiconAudit {
  readonly count: number;
  readonly duplicateCount: number;
  readonly nonAsciiCount: number;
  readonly confusablePairs: readonly string[];
  readonly homophoneWarnings: readonly string[];
  readonly truncated: boolean;
}

const KNOWN_HOMOPHONES = Object.freeze([
  ['night', 'knight'], ['sun', 'son'], ['sea', 'see'], ['blue', 'blew'],
  ['hare', 'hair'], ['flower', 'flour'], ['right', 'write'], ['rain', 'reign'],
  ['peace', 'piece'], ['to', 'too'], ['their', 'there'], ['deer', 'dear']
]);

function nearOne(a: string, b: string): boolean {
  if (Math.abs(a.length - b.length) > 1 || a === b) return false;
  let i = 0;
  let j = 0;
  let edits = 0;
  while (i < a.length && j < b.length) {
    if (a[i] === b[j]) { i++; j++; continue; }
    edits++;
    if (edits > 1) return false;
    if (a.length > b.length) i++;
    else if (b.length > a.length) j++;
    else { i++; j++; }
  }
  return edits + Number(i < a.length || j < b.length) <= 1;
}

/** Edit-distance-one and a small explicit homophone list, including compound words. */
export function auditLexicon(words: readonly string[], maxWarnings = 64): LexiconAudit {
  if (!Array.isArray(words) || words.length > 256 || words.some(w => typeof w !== 'string') ||
      !Number.isSafeInteger(maxWarnings) || maxWarnings < 1 || maxWarnings > 512) {
    throw new TypeError('Invalid audit input');
  }
  const duplicates = words.length - new Set(words).size;
  const nonAscii = words.filter(w => /[^a-z -]/.test(w)).length;
  const near: string[] = [];
  const sound: string[] = [];
  let truncated = false;
  for (let i = 0; i < words.length; i++) {
    for (let j = i + 1; j < words.length; j++) {
      const a = words[i]!;
      const b = words[j]!;
      if (nearOne(a, b)) {
        if (near.length < maxWarnings) near.push(`${a} / ${b}`);
        else truncated = true;
      }
      if (KNOWN_HOMOPHONES.some(([x, y]) =>
        a.split(' ').includes(x!) && b.split(' ').includes(y!) ||
        a.split(' ').includes(y!) && b.split(' ').includes(x!))) {
        if (sound.length < maxWarnings) sound.push(`${a} / ${b}`);
        else truncated = true;
      }
    }
  }
  return Object.freeze({ count: words.length, duplicateCount: duplicates,
    nonAsciiCount: nonAscii, confusablePairs: Object.freeze(near),
    homophoneWarnings: Object.freeze(sound), truncated });
}
