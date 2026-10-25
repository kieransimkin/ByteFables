/** Explicit inflection tables; ByteFables never guesses morphology at decode time. */
export interface GrammaticalSubject {
  readonly word: string;
  readonly number: 'singular' | 'plural';
}
export interface VerbForms {
  readonly singular: string;
  readonly plural: string;
}
const WORD = /^[a-z]+(?:-[a-z]+)*(?: [a-z]+)*$/;

/** Creates the dependent 'byWord' slot table accepted by compileStoryPack. */
export function makeVerbAgreementChoices(
  subjects: readonly GrammaticalSubject[], forms: readonly VerbForms[]
): Readonly<Record<string, readonly string[]>> {
  if (!Array.isArray(subjects) || !Array.isArray(forms) || subjects.length < 2 ||
      subjects.length > 256 || forms.length < 2 || forms.length > 256) {
    throw new TypeError('Agreement requires bounded subject and verb tables');
  }
  if (new Set(subjects.map(s => s.word)).size !== subjects.length ||
      subjects.some(s => !WORD.test(s.word) || !['singular', 'plural'].includes(s.number)) ||
      forms.some(f => !WORD.test(f.singular) || !WORD.test(f.plural))) {
    throw new TypeError('Invalid or duplicate agreement entries');
  }
  const results: Record<string, readonly string[]> = Object.create(null);
  for (const subject of subjects) {
    const choices = forms.map(f => f[subject.number]);
    if (new Set(choices).size !== forms.length) throw new TypeError('Ambiguous agreement forms');
    results[subject.word] = Object.freeze(choices);
  }
  return Object.freeze(results);
}
