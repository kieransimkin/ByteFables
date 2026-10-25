/** Frozen, validated *descriptive* capability metadata. Planned entries are NEVER executable. */
export type FormatMaturity = 'foundation' | 'experimental' | 'planned';
export type FormatCategory = 'codec' | 'identity' | 'symbol' | 'scene' | 'exporter' | 'archive' | 'watermark';
export type FormatGuarantee = 'reversible-raw' | 'reversible-typed' | 'identity-only' | 'presentation-only' | 'probabilistic-recovery';
export type FormatInput = 'public-record' | 'module-matrix' | 'vector-scene' | 'public-record-and-carrier';
export type FormatStandardStatus = 'published' | 'draft' | 'internal' | 'research';
export type FormatIntegrity = 'none' | 'crc32-accidental' | 'sha256-unkeyed' | 'format-specific';
export type FormatErrorCorrection = 'none' | 'format-specific';

export interface FormatManifestEntry {
  readonly formatId: string;
  readonly version: string;
  readonly category: FormatCategory;
  readonly maturity: FormatMaturity;
  readonly guarantee: FormatGuarantee;
  readonly input: FormatInput;
  readonly sensitivity: 'public-only';
  /** Format identifiers are informational; never grant secret handling through metadata. */
  readonly reference: string;
  readonly standardStatus: FormatStandardStatus;
  readonly license: string;
  readonly referenceVectors: string | null;
  readonly decoder: string | null;
  readonly minInputBytes: number;
  readonly maxInputBytes: number;
  readonly maxOutputBytes: number;
  readonly capacity: 'byte-exact' | 'digest-prefix' | 'visual-bounded' | 'symbol-defined' | 'story-13' | 'story-variable' | 'carrier-dependent';
  /** Approximate encoded size relative to the input, for planning, not a guarantee. */
  readonly estimatedExpansion: number | null;
  readonly mediaTypes: readonly string[];
  readonly carriers: readonly string[];
  readonly integrity: FormatIntegrity;
  readonly errorCorrection: FormatErrorCorrection;
  readonly deterministic: boolean;
  readonly offlineSafe: boolean;
  readonly runtime: readonly ('node' | 'browser')[];
  /** Handler name is optional even on implemented formats; input kind may need an IR. */
  readonly adapter: string | null;
}

const NAME = /^[a-z][a-z0-9-]*(?:\/[a-z][a-z0-9-]*)+$/;
const SEMVER = /^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$/;
const MIME = /^[a-z]+\/[a-z0-9.+-]+$/;
const REF = /^https:\/\//;
const CATEGORIES: readonly FormatCategory[] = ['codec', 'identity', 'symbol', 'scene', 'exporter', 'archive', 'watermark'];
const GUARANTEES: readonly FormatGuarantee[] = ['reversible-raw', 'reversible-typed', 'identity-only', 'presentation-only', 'probabilistic-recovery'];
const MATURITIES: readonly FormatMaturity[] = ['foundation', 'experimental', 'planned'];
const INPUTS: readonly FormatInput[] = ['public-record', 'module-matrix', 'vector-scene', 'public-record-and-carrier'];
const STANDARDS: readonly FormatStandardStatus[] = ['published', 'draft', 'internal', 'research'];
const INTEGRITIES: readonly FormatIntegrity[] = ['none', 'crc32-accidental', 'sha256-unkeyed', 'format-specific'];
const ECC: readonly FormatErrorCorrection[] = ['none', 'format-specific'];
const CAPACITIES = ['byte-exact', 'digest-prefix', 'visual-bounded', 'symbol-defined', 'story-13', 'story-variable', 'carrier-dependent'];

/** Validates untrusted plugin declarations and returns deep-frozen defensive copies. */
export function validateFormatManifest(entries: readonly FormatManifestEntry[]): readonly FormatManifestEntry[] {
  if (!Array.isArray(entries) || entries.length > 512) throw new TypeError('Invalid manifest size');
  const ids = new Set<string>();
  const outputs = entries.map(entry => {
    if (!entry || !NAME.test(entry.formatId) || !SEMVER.test(entry.version) ||
      ids.has(entry.formatId) || !CATEGORIES.includes(entry.category) ||
      !MATURITIES.includes(entry.maturity) || !GUARANTEES.includes(entry.guarantee) ||
      !INPUTS.includes(entry.input) || entry.sensitivity !== 'public-only' ||
      !STANDARDS.includes(entry.standardStatus) || !REF.test(entry.reference) ||
      typeof entry.license !== 'string' || entry.license.length === 0 ||
      (entry.referenceVectors !== null && (typeof entry.referenceVectors !== 'string' || !entry.referenceVectors)) ||
      (entry.decoder !== null && (typeof entry.decoder !== 'string' || !entry.decoder)) ||
      !CAPACITIES.includes(entry.capacity) || !INTEGRITIES.includes(entry.integrity) ||
      !ECC.includes(entry.errorCorrection) || typeof entry.deterministic !== 'boolean' ||
      typeof entry.offlineSafe !== 'boolean' || !Array.isArray(entry.mediaTypes) ||
      !entry.mediaTypes.length || entry.mediaTypes.some((x: string) => !MIME.test(x)) ||
      new Set(entry.mediaTypes).size !== entry.mediaTypes.length ||
      !Array.isArray(entry.carriers) || !entry.carriers.length ||
      entry.carriers.some((x: string) => typeof x !== 'string' || !/^[a-z][a-z-]*$/.test(x)) ||
      new Set(entry.carriers).size !== entry.carriers.length ||
      !Array.isArray(entry.runtime) || !entry.runtime.length ||
      entry.runtime.some((x: string) => x !== 'node' && x !== 'browser') ||
      new Set(entry.runtime).size !== entry.runtime.length ||
      (entry.adapter !== null && (typeof entry.adapter !== 'string' || !/^[a-z][a-zA-Z0-9]*$/.test(entry.adapter))) ||
      !Number.isSafeInteger(entry.minInputBytes) || entry.minInputBytes < 0 ||
      !Number.isSafeInteger(entry.maxInputBytes) || entry.maxInputBytes < entry.minInputBytes ||
      !Number.isSafeInteger(entry.maxOutputBytes) || entry.maxOutputBytes < 0 ||
      (entry.estimatedExpansion !== null && (!Number.isFinite(entry.estimatedExpansion) || entry.estimatedExpansion <= 0)) ||
      (entry.maturity === 'planned' && entry.adapter !== null) ||
      (entry.category === 'watermark' && (entry.input !== 'public-record-and-carrier' ||
        entry.guarantee !== 'probabilistic-recovery' || entry.capacity !== 'carrier-dependent' ||
        entry.maturity !== 'planned')) ||
      ((entry.guarantee === 'reversible-raw' || entry.guarantee === 'reversible-typed') && !entry.decoder && entry.maturity !== 'planned')) {
      throw new TypeError(`Invalid capability declaration: ${entry?.formatId ?? 'unknown'}`);
    }
    ids.add(entry.formatId);
    return Object.freeze({ ...entry, mediaTypes: Object.freeze([...entry.mediaTypes]),
      carriers: Object.freeze([...entry.carriers]), runtime: Object.freeze([...entry.runtime]) });
  });
  return Object.freeze(outputs);
}

const RFC4648 = 'https://www.rfc-editor.org/rfc/rfc4648.html';
const CBOR = 'https://www.rfc-editor.org/rfc/rfc8949.html';
const BIP39 = 'https://github.com/bitcoin/bips/blob/master/bip-0039.mediawiki';
const QR = 'https://www.iso.org/standard/83389.html';

// Single TS source of truth; manifests/formats-v1.json is its checked-in, generated snapshot.
export const FORMAT_MANIFEST = validateFormatManifest([
  {
    formatId: 'codec/hex', version: '1.0.0', category: 'codec', maturity: 'foundation',
    guarantee: 'reversible-raw', input: 'public-record', sensitivity: 'public-only',
    reference: RFC4648, standardStatus: 'published', license: 'MIT',
    referenceVectors: 'tests/vectors/v1.json', decoder: 'decodeHex',
    minInputBytes: 0, maxInputBytes: 1048576, maxOutputBytes: 2097152,
    capacity: 'byte-exact', estimatedExpansion: 2, mediaTypes: ['text/plain'],
    carriers: ['text'], integrity: 'none', errorCorrection: 'none',
    deterministic: true, offlineSafe: true, runtime: ['node', 'browser'], adapter: 'encodeHex'
  },
  {
    formatId: 'codec/rfc4648-base32-nopad', version: '1.0.0', category: 'codec', maturity: 'foundation',
    guarantee: 'reversible-raw', input: 'public-record', sensitivity: 'public-only',
    reference: RFC4648, standardStatus: 'published', license: 'MIT',
    referenceVectors: 'tests/vectors/v1.json', decoder: 'decodeBase32',
    minInputBytes: 0, maxInputBytes: 1048576, maxOutputBytes: 1677722,
    capacity: 'byte-exact', estimatedExpansion: 1.6, mediaTypes: ['text/plain'],
    carriers: ['text'], integrity: 'none', errorCorrection: 'none',
    deterministic: true, offlineSafe: true, runtime: ['node', 'browser'], adapter: 'encodeBase32'
  },
  {
    formatId: 'archive/public-cbor-v1', version: '1.0.0', category: 'archive', maturity: 'foundation',
    guarantee: 'reversible-typed', input: 'public-record', sensitivity: 'public-only',
    reference: CBOR, standardStatus: 'internal', license: 'MIT',
    referenceVectors: 'tests/vectors/public-cbor-v1.json', decoder: 'decodePublicRecord',
    minInputBytes: 0, maxInputBytes: 1048576, maxOutputBytes: 1050624,
    capacity: 'byte-exact', estimatedExpansion: 1.01, mediaTypes: ['application/cbor'],
    carriers: ['binary', 'file'], integrity: 'sha256-unkeyed', errorCorrection: 'none',
    deterministic: true, offlineSafe: true, runtime: ['node', 'browser'], adapter: 'encodePublicRecord'
  },
  {
    formatId: 'codec/story-prototype-13', version: '1.0.0', category: 'codec', maturity: 'experimental',
    guarantee: 'reversible-raw', input: 'public-record', sensitivity: 'public-only',
    reference: 'https://github.com/kieransimkin/ByteFables/blob/main/docs/DESIGN.md',
    standardStatus: 'internal', license: 'MIT', referenceVectors: 'tests/vectors/v1.json',
    decoder: 'decodeExperimentalStory', minInputBytes: 0, maxInputBytes: 4096,
    maxOutputBytes: 270000, capacity: 'story-13', estimatedExpansion: 65,
    mediaTypes: ['text/plain'], carriers: ['text'], integrity: 'crc32-accidental',
    errorCorrection: 'none', deterministic: true, offlineSafe: true, runtime: ['node', 'browser'],
    adapter: 'encodeExperimentalStory'
  },
  {
    formatId: 'codec/story-v2-prefix', version: '1.0.0', category: 'codec', maturity: 'experimental',
    guarantee: 'reversible-raw', input: 'public-record', sensitivity: 'public-only',
    reference: 'https://github.com/kieransimkin/ByteFables/blob/main/docs/specs/story-v2.md',
    standardStatus: 'internal', license: 'MIT', referenceVectors: 'tests/vectors/story-v2.json',
    decoder: 'decodeStoryV2', minInputBytes: 0, maxInputBytes: 4096,
    maxOutputBytes: 440000, capacity: 'story-variable', estimatedExpansion: 35,
    mediaTypes: ['text/plain'], carriers: ['text'], integrity: 'sha256-unkeyed',
    errorCorrection: 'none', deterministic: true, offlineSafe: true, runtime: ['node', 'browser'],
    adapter: 'encodeStoryV2'
  },
  {
    formatId: 'codec/story-v2-scheduled', version: '1.0.0', category: 'codec', maturity: 'experimental',
    guarantee: 'reversible-raw', input: 'public-record', sensitivity: 'public-only',
    reference: 'https://github.com/kieransimkin/ByteFables/blob/main/docs/specs/story-v2.md',
    standardStatus: 'internal', license: 'MIT', referenceVectors: 'tests/vectors/story-v2.json',
    decoder: 'decodeScheduledStory', minInputBytes: 0, maxInputBytes: 4096,
    maxOutputBytes: 440000, capacity: 'story-variable', estimatedExpansion: 35,
    mediaTypes: ['text/plain'], carriers: ['text'], integrity: 'sha256-unkeyed',
    errorCorrection: 'none', deterministic: true, offlineSafe: true, runtime: ['node', 'browser'],
    adapter: 'encodeScheduledStory'
  },
  {
    formatId: 'identity/fingerprint-sha256-v1', version: '1.0.0', category: 'identity', maturity: 'foundation',
    guarantee: 'identity-only', input: 'public-record', sensitivity: 'public-only',
    reference: 'https://github.com/kieransimkin/ByteFables/blob/main/docs/DESIGN.md',
    standardStatus: 'internal', license: 'MIT', referenceVectors: 'tests/vectors/v1.json', decoder: null,
    minInputBytes: 0, maxInputBytes: 1048576, maxOutputBytes: 68,
    capacity: 'digest-prefix', estimatedExpansion: null, mediaTypes: ['text/plain'],
    carriers: ['text'], integrity: 'none', errorCorrection: 'none', deterministic: true,
    offlineSafe: true, runtime: ['node', 'browser'], adapter: 'identityFingerprint'
  },
  // Short display aliases: fixed-prefix projection of the FULL canonical 256-bit public identity.
  // Cannot be used for authentication or full node lookup.
  {
    formatId: 'identity/short-hash-24-v1', version: '1.0.0', category: 'identity', maturity: 'foundation',
    guarantee: 'identity-only', input: 'public-record', sensitivity: 'public-only',
    reference: 'https://github.com/kieransimkin/ByteFables/blob/main/docs/specs/short-public-hashes-v1.md',
    standardStatus: 'internal', license: 'MIT', referenceVectors: 'tests/vectors/short-public-hashes-v1.json',
    decoder: null, minInputBytes: 4, maxInputBytes: 1048576, maxOutputBytes: 48,
    capacity: 'digest-prefix', estimatedExpansion: null, mediaTypes: ['text/plain'],
    carriers: ['text'], integrity: 'none', errorCorrection: 'none', deterministic: true,
    offlineSafe: true, runtime: ['node', 'browser'], adapter: 'deriveShortPublicHash24'
  },
  {
    formatId: 'identity/short-hash-32-v1', version: '1.0.0', category: 'identity', maturity: 'foundation',
    guarantee: 'identity-only', input: 'public-record', sensitivity: 'public-only',
    reference: 'https://github.com/kieransimkin/ByteFables/blob/main/docs/specs/short-public-hashes-v1.md',
    standardStatus: 'internal', license: 'MIT', referenceVectors: 'tests/vectors/short-public-hashes-v1.json',
    decoder: null, minInputBytes: 5, maxInputBytes: 1048576, maxOutputBytes: 48,
    capacity: 'digest-prefix', estimatedExpansion: null, mediaTypes: ['text/plain'],
    carriers: ['text'], integrity: 'none', errorCorrection: 'none', deterministic: true,
    offlineSafe: true, runtime: ['node', 'browser'], adapter: 'deriveShortPublicHash32'
  },
  {
    formatId: 'identity/short-hash-64-v1', version: '1.0.0', category: 'identity', maturity: 'foundation',
    guarantee: 'identity-only', input: 'public-record', sensitivity: 'public-only',
    reference: 'https://github.com/kieransimkin/ByteFables/blob/main/docs/specs/short-public-hashes-v1.md',
    standardStatus: 'internal', license: 'MIT', referenceVectors: 'tests/vectors/short-public-hashes-v1.json',
    decoder: null, minInputBytes: 9, maxInputBytes: 1048576, maxOutputBytes: 48,
    capacity: 'digest-prefix', estimatedExpansion: null, mediaTypes: ['text/plain'],
    carriers: ['text'], integrity: 'none', errorCorrection: 'none', deterministic: true,
    offlineSafe: true, runtime: ['node', 'browser'], adapter: 'deriveShortPublicHash64'
  },
  {
    formatId: 'identity/record-fingerprint-v1', version: '1.0.0', category: 'identity', maturity: 'foundation',
    guarantee: 'identity-only', input: 'public-record', sensitivity: 'public-only',
    reference: 'https://github.com/kieransimkin/ByteFables/blob/main/docs/specs/bytefables-public-record-v1.md',
    standardStatus: 'internal', license: 'MIT', referenceVectors: 'tests/vectors/public-cbor-v1.json',
    decoder: null, minInputBytes: 0, maxInputBytes: 1048576, maxOutputBytes: 71,
    capacity: 'digest-prefix', estimatedExpansion: null, mediaTypes: ['text/plain'],
    carriers: ['text'], integrity: 'none', errorCorrection: 'none', deterministic: true,
    offlineSafe: true, runtime: ['node', 'browser'], adapter: 'publicRecordFingerprint'
  },
  {
    formatId: 'identity/pixel-avatar-v1', version: '1.0.0', category: 'identity', maturity: 'foundation',
    guarantee: 'identity-only', input: 'public-record', sensitivity: 'public-only',
    reference: 'https://github.com/kieransimkin/ByteFables/blob/main/docs/DESIGN.md',
    standardStatus: 'internal', license: 'MIT', referenceVectors: 'tests/vectors/v1.json', decoder: null,
    minInputBytes: 0, maxInputBytes: 1048576, maxOutputBytes: 20000,
    capacity: 'visual-bounded', estimatedExpansion: null, mediaTypes: ['image/svg+xml'],
    carriers: ['vector', 'screen'], integrity: 'none', errorCorrection: 'none',
    deterministic: true, offlineSafe: true, runtime: ['node', 'browser'], adapter: 'renderPixelAvatar'
  },
  {
    formatId: 'identity/visual-bit-contract-v1', version: '1.0.0', category: 'identity',
    maturity: 'experimental', guarantee: 'identity-only', input: 'public-record',
    sensitivity: 'public-only',
    reference: 'https://github.com/kieransimkin/ByteFables/blob/main/docs/specs/hash-image-benchmark-v1.md',
    standardStatus: 'internal', license: 'MIT', referenceVectors: 'tests/vectors/visual-bits-v1.json',
    decoder: null, minInputBytes: 1, maxInputBytes: 512, maxOutputBytes: 2097152,
    capacity: 'visual-bounded', estimatedExpansion: null, mediaTypes: ['application/json'],
    carriers: ['file', 'text'], integrity: 'none', errorCorrection: 'none',
    deterministic: true, offlineSafe: true, runtime: ['node', 'browser'],
    adapter: 'makeVisualBitPlan'
  },
  {
    formatId: 'identity/fractal-seed-plan-v1', version: '1.0.0', category: 'identity',
    maturity: 'experimental', guarantee: 'identity-only', input: 'public-record',
    sensitivity: 'public-only',
    reference: 'https://github.com/kieransimkin/ByteFables/blob/main/docs/specs/fractal-seeding-v1.md',
    standardStatus: 'internal', license: 'MIT', referenceVectors: 'tests/fractal.test.mjs',
    decoder: null, minInputBytes: 1, maxInputBytes: 512, maxOutputBytes: 8192,
    capacity: 'visual-bounded', estimatedExpansion: null, mediaTypes: ['application/json'],
    carriers: ['file', 'text'], integrity: 'none', errorCorrection: 'none',
    deterministic: true, offlineSafe: true, runtime: ['node', 'browser'], adapter: 'planPublicFractal'
  },
  {
    formatId: 'symbol/module-matrix-ir-v1', version: '1.0.0', category: 'symbol', maturity: 'foundation',
    guarantee: 'presentation-only', input: 'module-matrix', sensitivity: 'public-only',
    reference: 'https://github.com/kieransimkin/ByteFables/blob/main/docs/specs/frame-bridge-v1.md',
    standardStatus: 'internal', license: 'MIT', referenceVectors: 'tests/vectors/framerudiments-v1.json',
    decoder: null, minInputBytes: 1, maxInputBytes: 65536, maxOutputBytes: 131072,
    capacity: 'symbol-defined', estimatedExpansion: null, mediaTypes: ['application/json'],
    carriers: ['project'], integrity: 'none', errorCorrection: 'none',
    deterministic: true, offlineSafe: true, runtime: ['node', 'browser'], adapter: null
  },
  {
    formatId: 'scene/vector-scene-ir-v1', version: '1.0.0', category: 'scene', maturity: 'foundation',
    guarantee: 'presentation-only', input: 'vector-scene', sensitivity: 'public-only',
    reference: 'https://github.com/kieransimkin/ByteFables/blob/main/docs/specs/frame-bridge-v1.md',
    standardStatus: 'internal', license: 'MIT', referenceVectors: 'tests/vectors/framerudiments-v1.json', decoder: null,
    minInputBytes: 0, maxInputBytes: 10000, maxOutputBytes: 4194304,
    capacity: 'visual-bounded', estimatedExpansion: null, mediaTypes: ['application/json'],
    carriers: ['project'], integrity: 'none', errorCorrection: 'none',
    deterministic: true, offlineSafe: true, runtime: ['node', 'browser'], adapter: null
  },
  {
    formatId: 'codec/bytewords', version: '1.0.0', category: 'codec', maturity: 'planned',
    guarantee: 'reversible-raw', input: 'public-record', sensitivity: 'public-only',
    reference: 'https://github.com/BlockchainCommons/Research/blob/master/papers/bcr-2020-012-bytewords.md',
    standardStatus: 'published', license: 'TBD-review-upstream', referenceVectors: null, decoder: null,
    minInputBytes: 0, maxInputBytes: 1048576, maxOutputBytes: 4194304,
    capacity: 'byte-exact', estimatedExpansion: 2, mediaTypes: ['text/plain'],
    carriers: ['text', 'print'], integrity: 'format-specific', errorCorrection: 'none',
    deterministic: true, offlineSafe: true, runtime: ['node', 'browser'], adapter: null
  },
  {
    formatId: 'symbol/qr-model2', version: '1.0.0', category: 'symbol', maturity: 'planned',
    guarantee: 'reversible-raw', input: 'public-record', sensitivity: 'public-only',
    reference: QR, standardStatus: 'published', license: 'TBD-review-encoder',
    referenceVectors: null, decoder: null, minInputBytes: 0, maxInputBytes: 2953,
    maxOutputBytes: 8388608, capacity: 'symbol-defined', estimatedExpansion: null,
    mediaTypes: ['image/svg+xml', 'image/png'], carriers: ['vector', 'print', 'screen'],
    integrity: 'format-specific', errorCorrection: 'format-specific',
    deterministic: true, offlineSafe: true, runtime: ['node', 'browser'], adapter: null
  },
  {
    formatId: 'exporter/framerudiments-layer-v1', version: '1.0.0',
    category: 'exporter', maturity: 'experimental', guarantee: 'presentation-only',
    input: 'public-record', sensitivity: 'public-only',
    reference: 'https://github.com/kieransimkin/FrameRudiments/blob/main/docs/rudiment-renderers.md',
    standardStatus: 'internal', license: 'MIT', referenceVectors: 'tests/vectors/framerudiments-v1.json',
    decoder: null, minInputBytes: 0, maxInputBytes: 1048576,
    maxOutputBytes: 8192, capacity: 'visual-bounded', estimatedExpansion: null,
    mediaTypes: ['application/json'], carriers: ['project'], integrity: 'none',
    errorCorrection: 'none', deterministic: true, offlineSafe: true,
    runtime: ['node', 'browser'], adapter: 'makeFrameRudimentsIdentityLayer'
  },
  {
    formatId: 'wallet/bip39', version: '1.0.0', category: 'archive', maturity: 'planned',
    guarantee: 'reversible-raw', input: 'public-record', sensitivity: 'public-only',
    reference: BIP39, standardStatus: 'published', license: 'TBD-review-upstream',
    referenceVectors: null, decoder: null, minInputBytes: 16, maxInputBytes: 32,
    maxOutputBytes: 1024, capacity: 'byte-exact', estimatedExpansion: null,
    mediaTypes: ['text/plain'], carriers: ['text', 'print'], integrity: 'format-specific',
    errorCorrection: 'none', deterministic: true, offlineSafe: true,
    runtime: ['node', 'browser'], adapter: null
  },
  {
    formatId: 'identity/lifehash', version: '1.0.0', category: 'identity', maturity: 'planned',
    guarantee: 'identity-only', input: 'public-record', sensitivity: 'public-only',
    reference: 'https://developer.blockchaincommons.com/lifehash/',
    standardStatus: 'published', license: 'TBD-review-upstream', referenceVectors: null,
    decoder: null, minInputBytes: 0, maxInputBytes: 1048576,
    maxOutputBytes: 500000, capacity: 'visual-bounded', estimatedExpansion: null,
    mediaTypes: ['image/svg+xml', 'image/png'], carriers: ['screen', 'vector'],
    integrity: 'none', errorCorrection: 'none', deterministic: true, offlineSafe: true,
    runtime: ['node', 'browser'], adapter: null
  },
  {
    formatId: 'watermark/image-spatial', version: '1.0.0', category: 'watermark',
    maturity: 'planned', guarantee: 'probabilistic-recovery',
    input: 'public-record-and-carrier', sensitivity: 'public-only',
    reference: 'https://github.com/tancik/StegaStamp', standardStatus: 'research', license: 'TBD-review-upstream',
    referenceVectors: null, decoder: null,
    minInputBytes: 0, maxInputBytes: 1048576, maxOutputBytes: 0,
    capacity: 'carrier-dependent', estimatedExpansion: null,
    mediaTypes: ['image/png', 'image/jpeg', 'image/webp'], carriers: ['project'],
    integrity: 'format-specific', errorCorrection: 'format-specific',
    deterministic: false, offlineSafe: true, runtime: ['node', 'browser'], adapter: null
  },
  {
    formatId: 'watermark/audio-spectral', version: '1.0.0', category: 'watermark',
    maturity: 'planned', guarantee: 'probabilistic-recovery',
    input: 'public-record-and-carrier', sensitivity: 'public-only',
    reference: 'https://github.com/facebookresearch/audioseal', standardStatus: 'research', license: 'TBD-review-upstream',
    referenceVectors: null, decoder: null,
    minInputBytes: 0, maxInputBytes: 1048576, maxOutputBytes: 0,
    capacity: 'carrier-dependent', estimatedExpansion: null,
    mediaTypes: ['audio/wav', 'audio/flac', 'audio/mpeg'], carriers: ['project'],
    integrity: 'format-specific', errorCorrection: 'format-specific',
    deterministic: false, offlineSafe: true, runtime: ['node', 'browser'], adapter: null
  },
  {
    formatId: 'watermark/video-temporal', version: '1.0.0', category: 'watermark',
    maturity: 'planned', guarantee: 'probabilistic-recovery',
    input: 'public-record-and-carrier', sensitivity: 'public-only',
    reference: 'https://github.com/facebookresearch/videoseal', standardStatus: 'research', license: 'TBD-review-upstream',
    referenceVectors: null, decoder: null,
    minInputBytes: 0, maxInputBytes: 1048576, maxOutputBytes: 0,
    capacity: 'carrier-dependent', estimatedExpansion: null,
    mediaTypes: ['video/mp4', 'video/webm'], carriers: ['project'],
    integrity: 'format-specific', errorCorrection: 'format-specific',
    deterministic: false, offlineSafe: true, runtime: ['node', 'browser'], adapter: null
  },
  {
    formatId: 'watermark/text-semantic', version: '1.0.0', category: 'watermark',
    maturity: 'planned', guarantee: 'probabilistic-recovery',
    input: 'public-record-and-carrier', sensitivity: 'public-only',
    reference: 'https://ai.google.dev/responsible/docs/safeguards/synthid', standardStatus: 'research', license: 'TBD-review-upstream',
    referenceVectors: null, decoder: null,
    minInputBytes: 0, maxInputBytes: 1048576, maxOutputBytes: 0,
    capacity: 'carrier-dependent', estimatedExpansion: null,
    mediaTypes: ['text/plain', 'text/markdown'], carriers: ['project'],
    integrity: 'format-specific', errorCorrection: 'format-specific',
    deterministic: false, offlineSafe: true, runtime: ['node', 'browser'], adapter: null
  }
]);

export function getFormatManifest(formatId: string): FormatManifestEntry | undefined {
  return FORMAT_MANIFEST.find(entry => entry.formatId === formatId);
}

export function listFormatManifests(options: {
  readonly category?: FormatCategory;
  readonly maturity?: FormatMaturity;
} = {}): readonly FormatManifestEntry[] {
  return FORMAT_MANIFEST.filter(e =>
    (!options.category || e.category === options.category) &&
    (!options.maturity || e.maturity === options.maturity));
}
