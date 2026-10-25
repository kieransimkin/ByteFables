/** Immutable language data. Word order and grammar markers are wire-format v1.
 * Generated cross-products are frozen to avoid opaque index-table changes.
 * These packs are ByteFables-specific, NOT BIP-450/Formosa-compatible.
 */
import { compileStoryPack, type CompiledStoryPack, type StoryPart, type StoryTemplateSpec } from './structured.js';

const csv = (input: string): readonly string[] => Object.freeze(input.split(' '));

interface ThemeWords {
  readonly appearanceFirst: readonly string[];
  readonly appearanceSecond: readonly string[];
  readonly subjectFirst: readonly string[];
  readonly subjectSecond: readonly string[];
  readonly actionFirst: readonly string[];
  readonly actionSecond: readonly string[];
  readonly placeFirst: readonly string[];
  readonly placeSecond: readonly string[];
}
const INPUTS: Readonly<Record<string, ThemeWords>> = Object.freeze({
  nature: {
    appearanceFirst: csv('amber azure bronze coral crimson golden indigo ivory jade lilac mint pearl rose silver teal violet'),
    appearanceSecond: csv('brave calm cheerful curious dapper elegant gentle happy lively merry nimble playful radiant quiet sleepy wise'),
    subjectFirst: csv('alpine arctic autumn coastal desert forest garden hillside island jungle meadow mountain prairie river woodland winter'),
    subjectSecond: csv('badger beaver butterfly cat deer dolphin eagle fox frog hare hedgehog otter rabbit snail sparrow wolf'),
    actionFirst: csv('ambles dances dreams drifts glides hums hops listens marches naps peers rests sings skips smiles wanders'),
    actionSecond: csv('boldly calmly cheerfully dreamily eagerly gently lightly merrily openly patiently playfully quietly softly swiftly warmly wisely'),
    placeFirst: csv('ancient bright crystal distant ferny golden hidden leafy misty moonlit mossy quiet rocky shaded silent windy'),
    placeSecond: csv('brook canyon clearing coast forest garden glade hill island lagoon meadow orchard ridge river valley woodland')
  },
  technology: {
    appearanceFirst: csv('amber azure carbon copper crystal digital electric emerald glass golden graphite iron neon silver titanium violet'),
    appearanceSecond: csv('adaptive agile compact curious dynamic efficient elegant flexible luminous modular precise quiet resilient stable swift tiny'),
    subjectFirst: csv('autonomous binary cloud cosmic cyber data digital electric future hybrid laser local nano quantum robotic silent'),
    subjectSecond: csv('antenna beacon circuit console drone engine gateway module monitor node probe robot router scanner sensor server'),
    actionFirst: csv('adapts blinks boots calibrates computes connects decodes detects hums listens monitors pulses scans signals syncs transmits'),
    actionSecond: csv('boldly calmly cleanly closely evenly gently lightly locally neatly openly precisely quietly safely softly swiftly wisely'),
    placeFirst: csv('atomic bright central distant electric hidden local luminous magnetic modern modular quiet remote secure silent virtual'),
    placeSecond: csv('archive array chamber cluster console datacenter dock gateway grid hub laboratory network platform station terminal workshop')
  },
  music: {
    appearanceFirst: csv('amber azure blue bronze crimson golden indigo ivory jade lilac magenta pink silver teal violet yellow'),
    appearanceSecond: csv('bright cheerful dreamy elegant funky gentle groovy joyful lively mellow melodic playful rhythmic soulful warm wild'),
    subjectFirst: csv('acoustic ambient bass classical cosmic electric folk funky indie jazz lunar mellow midnight soul vintage zen'),
    subjectSecond: csv('bassist cellist composer dancer drummer flautist guitarist harpist keyboardist pianist rapper saxophonist singer soloist trumpeter violinist'),
    actionFirst: csv('bows dances drums echoes grooves harmonises hums improvises listens marches performs plays raps sings strums sways'),
    actionSecond: csv('boldly brightly calmly dreamily freely gently gladly lightly loudly openly playfully quietly smoothly softly swiftly warmly'),
    placeFirst: csv('acoustic amber crowded distant electric golden intimate lively moonlit open quiet retro silver spacious velvet warm'),
    placeSecond: csv('amphitheatre arena basement booth club concert hall lounge orchestra plaza room stage studio theatre venue warehouse')
  },
  fantasy: {
    appearanceFirst: csv('ancient amber azure bronze crystal crimson emerald golden ivory jade lunar midnight opal ruby silver violet'),
    appearanceSecond: csv('brave curious enchanted fearless gentle glorious hidden luminous magical merry noble radiant royal silent strange wise'),
    subjectFirst: csv('ancient arctic astral autumn celestial crystal desert enchanted forest golden hidden lunar mountain mystic shadow winter'),
    subjectSecond: csv('centaur dragon dryad fairy gargoyle giant goblin griffin knight mage mermaid oracle phoenix sprite troll unicorn'),
    actionFirst: csv('appears bows dances dreams glimmers glides guards hums leaps listens marches rests shines sings wanders watches'),
    actionSecond: csv('boldly brightly calmly dreamily gently gladly magically merrily openly patiently playfully quietly softly swiftly warmly wisely'),
    placeFirst: csv('ancient azure crystal distant emerald enchanted forgotten golden hidden misty moonlit mystic quiet shadow silver twilight'),
    placeSecond: csv('archway bridge castle citadel courtyard forest garden gateway grove keep labyrinth mountain palace portal tower valley')
  },
  science: {
    appearanceFirst: csv('atomic azure binary bright carbon cosmic crystal digital electric golden infrared lunar neon quantum silver ultraviolet'),
    appearanceSecond: csv('active agile bright curious dynamic electric elegant energetic fast gentle luminous precise quiet radiant stable tiny'),
    subjectFirst: csv('atomic binary chemical cosmic crystal digital electric fractal galactic magnetic microscopic molecular orbital quantum stellar thermal'),
    subjectSecond: csv('atom cell comet electron enzyme galaxy ion isotope laser magnet molecule neutron photon planet proton vector'),
    actionFirst: csv('accelerates aligns appears bends changes circulates collides decays drifts expands glows moves orbits pulses rotates vibrates'),
    actionSecond: csv('boldly calmly closely evenly freely gently lightly locally neatly openly precisely quietly rapidly softly smoothly swiftly'),
    placeFirst: csv('atomic bright distant electric frozen hidden inner luminous magnetic microscopic orbital quiet remote solar stellar virtual'),
    placeSecond: csv('array chamber cluster cosmos field galaxy grid laboratory network observatory orbit reactor satellite spectrum system vacuum')
  },
  humour: {
    appearanceFirst: csv('amber azure bouncy bubblegum cheesy cosmic fizzy fuzzy glittery golden jellybean lemon lilac noodle pink purple'),
    appearanceSecond: csv('baffled bubbly cheeky clumsy curious dapper dizzy fluffy goofy happy jolly merry playful silly sleepy wobbly'),
    subjectFirst: csv('acrobatic banana bouncy dancing electric fancy fuzzy garden giggling jellybean lunar mini moonlit rubber sleepy tiny'),
    subjectSecond: csv('aardvark badger banana beaver chicken duck ferret flamingo frog hamster hippo llama otter panda penguin snail'),
    actionFirst: csv('bounces dances giggles glides grins hiccups hops juggles laughs naps nods skips snores spins waddles wiggles'),
    actionSecond: csv('awkwardly boldly cheerfully clumsily dreamily gently happily loudly merrily oddly playfully quietly rapidly sleepily softly wildly'),
    placeFirst: csv('bouncy bright crooked dizzy fluffy giant golden hidden jellybean lemon lopsided moonlit purple rainbow sleepy wobbly'),
    placeSecond: csv('attic balloon bathtub bookshelf carnival closet corridor cupboard garden kitchen meadow office pantry playground staircase wardrobe')
  }
});

function combine(a: readonly string[], b: readonly string[]): readonly string[] {
  if (a.length !== 16 || b.length !== 16 || new Set(a).size !== 16 || new Set(b).size !== 16) {
    throw new TypeError('ByteFables thematic dictionaries must contain 16 unique components each');
  }
  const result = a.flatMap(first => b.map(second => `${first} ${second}`));
  if (new Set(result).size !== 256) throw new TypeError('Duplicate combined phrase');
  return Object.freeze(result);
}

function literal(text: string): StoryPart { return { type: 'literal', text }; }
function slot(role: string, words: readonly string[]): StoryPart { return { type: 'choice', role, words }; }

function buildPack(id: string, words: ThemeWords): CompiledStoryPack {
  const appearance = combine(words.appearanceFirst, words.appearanceSecond);
  const subject = combine(words.subjectFirst, words.subjectSecond);
  const action = combine(words.actionFirst, words.actionSecond);
  const place = combine(words.placeFirst, words.placeSecond);
  const templates: readonly StoryTemplateSpec[] = [
    { id: 'at', prefix: '0', parts: [literal('At the '), slot('place', place), literal(', the '),
      slot('appearance', appearance), literal(' '), slot('subject', subject), literal(' '),
      slot('action', action), literal('.')] },
    { id: 'sometimes', prefix: '10', parts: [literal('Sometimes the '), slot('appearance', appearance), literal(' '),
      slot('subject', subject), literal(' '), slot('action', action), literal(' beside the '),
      slot('place', place), literal('.')] },
    { id: 'beyond', prefix: '110', parts: [literal('Beyond the '), slot('place', place), literal(', the '),
      slot('appearance', appearance), literal(' '), slot('subject', subject), literal(' '),
      slot('action', action), literal('.')] },
    { id: 'when', prefix: '111', parts: [literal('When the '), slot('appearance', appearance), literal(' '),
      slot('subject', subject), literal(' '), slot('action', action), literal(', the '),
      slot('place', place), literal(' glimmers.')] }
  ];
  return compileStoryPack({ id, version: 1, templates });
}

export type StoryTheme = 'nature' | 'technology' | 'music' | 'fantasy' | 'science' | 'humour';
export const STORY_THEMES = Object.freeze(Object.keys(INPUTS) as StoryTheme[]);
export const STORY_PACKS: Readonly<Record<StoryTheme, CompiledStoryPack>> = Object.freeze(
  Object.fromEntries(STORY_THEMES.map(theme => [theme, buildPack(theme, INPUTS[theme]!)])) as Record<StoryTheme, CompiledStoryPack>
);
export function getStoryPack(theme: StoryTheme): CompiledStoryPack {
  if (typeof theme !== 'string' || !Object.hasOwn(STORY_PACKS, theme)) {
    throw new TypeError('Unsupported story theme');
  }
  return STORY_PACKS[theme];
}

/** Self-identifying templates for the alternative DP-scheduled story profile.
 * Their marker is explicit presentation overhead and contributes ZERO bits.
 * Built from the SAME pinned lexicons; the original 33–35-bit packs are unchanged.
 */
function buildScheduledPack(id: string, words: ThemeWords): CompiledStoryPack {
  const appearance = combine(words.appearanceFirst, words.appearanceSecond);
  const subject = combine(words.subjectFirst, words.subjectSecond);
  const action = combine(words.actionFirst, words.actionSecond);
  const place = combine(words.placeFirst, words.placeSecond);
  return compileStoryPack({ id: `scheduled-${id}`, version: 1, templates: [
    { id: 'brief', prefix: '0', parts: [
      literal('By moonlight, the '), slot('appearance', appearance), literal(' '),
      slot('subject', subject), literal(' '), slot('action', action), literal('.')
    ] },
    { id: 'balanced', prefix: '10', parts: [
      literal('Across the '), slot('place', place), literal(', the '),
      slot('appearance', appearance), literal(' '), slot('subject', subject), literal(' '),
      slot('action', action), literal('.')
    ] },
    { id: 'elaborate', prefix: '11', parts: [
      literal('Although the '), slot('place', place), literal(' glimmers, the '),
      slot('appearance', appearance), literal(' '), slot('subject', subject), literal(' '),
      slot('action', action), literal(' near the '), slot('destination', place), literal('.')
    ] }
  ] });
}
export const SCHEDULED_STORY_PACKS: Readonly<Record<StoryTheme, CompiledStoryPack>> = Object.freeze(
  Object.fromEntries(STORY_THEMES.map(theme => [theme,
    buildScheduledPack(theme, INPUTS[theme]!)])) as Record<StoryTheme, CompiledStoryPack>
);
export function getScheduledStoryPack(theme: StoryTheme): CompiledStoryPack {
  if (typeof theme !== 'string' || !Object.hasOwn(SCHEDULED_STORY_PACKS, theme)) {
    throw new TypeError('Unsupported story theme');
  }
  return SCHEDULED_STORY_PACKS[theme];
}
