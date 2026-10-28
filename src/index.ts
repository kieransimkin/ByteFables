export { ByteValue, MAX_VALUE_BYTES, assertPublicValue } from './value.js';
export type { ByteValueOptions, Sensitivity, PublicByteValue, SecretByteValue } from './value.js';
export { encodeHex, decodeHex } from './codecs/hex.js';
export { encodeBase32, decodeBase32 } from './codecs/base32.js';
export { identityDigest, identityFingerprint } from './identity/identity.js';
export { SHORT_HASH_LENGTHS, SHORT_HASH_SCHEME, truncateSha256Digest,
  deriveShortPublicHash, deriveShortPublicHashes } from './identity/short-hash.js';
export type { ShortHashBytes, ShortPublicHash } from './identity/short-hash.js';
export { renderPixelAvatar } from './identity/pixel-avatar.js';
export type { PixelAvatarOptions } from './identity/pixel-avatar.js';
export { CATALOGUE } from './catalogue.js';
export type { Category, Maturity, CatalogueEntry } from './catalogue.js';
export { compileGrammarPack, encodeSentence, decodeSentence } from './grammar/compiler.js';
export { DEFAULT_GRAMMAR_PACK } from './grammar/default-pack.js';
export { encodeExperimentalStory, decodeExperimentalStory } from './grammar/story.js';

// Wave A — public-only typed records and deterministic CBOR subset.
export { encodeDeterministicCbor, decodeDeterministicCbor, MAX_CBOR_BYTES } from './framing/cbor.js';
export type { CborValue } from './framing/cbor.js';
export { PublicRecord, encodePublicRecord, decodePublicRecord,
  publicRecordDigest, publicRecordFingerprint } from './framing/public-record.js';
export type { ByteOrder, PublicRecordOptions } from './framing/public-record.js';
export { FORMAT_MANIFEST, validateFormatManifest, getFormatManifest, listFormatManifests } from './registry/manifest.js';
export type { FormatManifestEntry, FormatCategory, FormatMaturity,
  FormatGuarantee, FormatInput, FormatStandardStatus,
  FormatIntegrity, FormatErrorCorrection } from './registry/manifest.js';
export { planPublicFormats, executePublicFormat, verifyBuiltinRegistry } from './registry/runtime.js';
export type { PublicArtifact, PublicPlanRequest, PlannedFormat } from './registry/runtime.js';
export { ModuleMatrix, moduleMatrixToVectorScene } from './ir/module-matrix.js';
export type { ModuleMatrixSpec, ModuleMatrixSvgOptions } from './ir/module-matrix.js';
export { createVectorScene } from './ir/vector-scene.js';
export type { VectorScene, VectorSceneSpec, VectorPrimitive, HexColor } from './ir/vector-scene.js';
export type { SpatialSceneDraft, TemporalSceneDraft, AcousticPacketStreamDraft,
  TactileSequenceDraft, LayoutDocumentDraft } from './ir/future-interfaces.js';

// FrameRudiments is the sole host for new graphics and effect generation.
export { FRAMERUDIMENTS_BRIDGE_VERSION, createFrameRudimentsIdentityLayer,
  createFrameRudimentsMatrixLayer, createFrameRudimentsSceneLayer,
  createFrameRudimentsFractalLayer,
  frameRudimentsEffectTarget, createFrameRudimentsArtworkLayer } from './engine/framerudiments.js';
export type { FrameRudimentsLayer, LayerPlacement, IdentityLayerOptions,
  IdentityPalette, FractalLayerOptions } from './engine/framerudiments.js';

// Experimental watermark message framing and planning only. No media embedder yet.
export { WATERMARK_MESSAGE_V1, encodePublicWatermarkMessage,
  decodePublicWatermarkMessage, matchesPublicWatermarkMessage } from './watermark/payload.js';
export type { WatermarkDigestBytes, DecodedWatermarkMessage } from './watermark/payload.js';
export { planPublicWatermark } from './watermark/planner.js';
export type { WatermarkCarrier, WatermarkCarrierDescriptor, ImageCarrier, AudioCarrier,
  VideoCarrier, TextCarrier, WatermarkThreat, WatermarkPlanOptions,
  WatermarkPlan } from './watermark/planner.js';

// Stage 2 — versioned reversible grammar stories (PUBLIC binary only).
export { radixCapacityBits, encodeRadixBits, decodeRadixBits, bitsToBigint, bigintToBits } from './grammar/radix.js';
export { compileStoryPack, encodeStructuredSentence, decodeStructuredSentence, selectStoryTemplate } from './grammar/structured.js';
export type { StoryPart, StoryPackSpec, StoryTemplateSpec, CompiledStoryPart, CompiledStoryTemplate, CompiledStoryPack } from './grammar/structured.js';
export { STORY_THEMES, STORY_PACKS, SCHEDULED_STORY_PACKS, getStoryPack, getScheduledStoryPack } from './grammar/themes.js';
export type { StoryTheme } from './grammar/themes.js';
export { encodeStoryV2, decodeStoryV2, inspectStoryV2, STORY_V2_MAX_PAYLOAD_BYTES } from './grammar/story-v2.js';
export type { StoryV2Result, StoryV2Statistics } from './grammar/story-v2.js';
export { encodeScheduledStory, decodeScheduledStory } from './grammar/scheduled-story.js';
export { makeVerbAgreementChoices } from './grammar/agreement.js';
export type { GrammaticalSubject, VerbForms } from './grammar/agreement.js';
export { auditLexicon } from './grammar/audit.js';
export type { LexiconAudit } from './grammar/audit.js';
export { scheduleSentenceCapacities } from './grammar/scheduler.js';
export type { CapacityChoice, ScheduledChunk, ScheduleOptions } from './grammar/scheduler.js';
export { createFrameRudimentsStoryPreview } from './engine/story-panels.js';
export type { FrameStoryPreview, FrameTextBlock, StoryPreviewOptions } from './engine/story-panels.js';

// Experimental LLM/image benchmark: public hash bits to visually opposing axes.
export { VISUAL_BITS_VERSION, makeVisualBitPlan, choosePromptBits, composeBaselinePrompt } from './identity/visual-bits.js';
export type { VisualBitChoice, VisualBitPlan, BaselinePromptStyle } from './identity/visual-bits.js';

// Research-stage public-only fractal identity plans. No reversible key encoding.
export { FRACTAL_SEED_VERSION, FRACTAL_FAMILIES, FRACTAL_BINARY_AXES, planPublicFractal } from './identity/fractal-seed.js';
export type { FractalFamily, FractalPalette, FractalSeedPlan } from './identity/fractal-seed.js';

// Stage 3 — strict standard codecs; wallet-specific recovery remains separately gated.
export { encodeBase64, decodeBase64 } from './codecs/base64.js';
export { encodeBase45, decodeBase45 } from './codecs/base45.js';
export { encodeCrockford32, decodeCrockford32 } from './codecs/crockford32.js';
export { encodeBase58, decodeBase58, encodeBase58Check, decodeBase58Check, decodeBase58CheckForVersion } from './codecs/base58check.js';
export { encodeBech32, decodeBech32, encodeBech32Bytes, decodeBech32Bytes,
  encodeSegwitAddress, decodeSegwitAddress, convertBits } from './codecs/bech32.js';
export type { Bech32Variant } from './codecs/bech32.js';
export { encodeBytewords, decodeBytewords, BYTEWORDS_WORDLIST } from './codecs/bytewords.js';
export type { BytewordsStyle } from './codecs/bytewords.js';
export { encodeBip39PublicEntropy, decodeBip39PublicMnemonic, BIP39_ENGLISH } from './codecs/bip39.js';
export { encodeUrBytesTestOnly, decodeUrBytesTestOnly } from './codecs/ur-bytes-test.js';
export { decodePublicTextFormat } from './registry/decode.js';
export { encodeMultibase, decodeMultibase } from './codecs/multibase.js';
export type { MultibasePrefix } from './codecs/multibase.js';

// QR Model 2 PUBLIC recovery: exact byte-mode codewords and FrameRudiments carriers.
export { encodeQrModel2, qrByteCapacity } from './symbols/qr.js';
export type { QrResult, QrOptions, QrEcc } from './symbols/qr.js';
export { encodePublicQrSession, decodePublicQrSession } from './symbols/qr-frames.js';
export type { PublicQrPlanOptions, PublicQrFrame, PublicQrSession } from './symbols/qr-frames.js';
export { createPublicQrCard } from './engine/public-qr-card.js';
export type { PublicQrCard, PublicQrCardOptions } from './engine/public-qr-card.js';

// Blockchain Commons BCR-2024-001 UR v2 transport; PUBLIC `ur:bytes` TEST fixtures ONLY.
export { UrTestXoshiro256, chooseUrTestFragments, parseUrTestPart,
  encodeUrBytesMultipartTestOnly, decodeUrBytesMultipartTestOnly,
  UrBytesTestDecoder } from './codecs/ur-multipart-test.js';
export type { UrTestPart, UrTestEncodeOptions, UrTestSequence } from './codecs/ur-multipart-test.js';
export { createUrBytesQrTestDeck } from './engine/ur-qr-test.js';
export type { UrBytesQrTestOptions, UrBytesQrTestDeck } from './engine/ur-qr-test.js';

// Public QR recovery sheets rendered and exported by FrameRudiments.
export { createFrameRudimentsRecoveryCardLayer } from './engine/framerudiments.js';
export type { RecoveryCardOptions } from './engine/framerudiments.js';
export { createPublicRecoverySheet } from './engine/public-recovery-sheet.js';
export type { PublicRecoverySheet, PublicRecoverySheetOptions } from './engine/public-recovery-sheet.js';

// Declarative public video looks — existing FrameRudiments filters own rendering.
export { PUBLIC_VIDEO_LOOK_VERSION, VIDEO_LOOK_PRESETS, planPublicVideoLook } from './effects/video-looks.js';
export type { VideoLookId, PublicVideoLookOptions, PublicVideoLookPlan } from './effects/video-looks.js';

// Experimental immutable US/UK past-tense, noun and adjective codebooks.
export { LARGE_LEXICONS_V1, LARGE_LEXICON_COUNTS_V1, largeLexiconWordsV1,
  largeLexiconWordV1, largeLexiconIndexV1, convertLexiconWordV1 } from './grammar/large-lexicons-v1.js';
export type { LexiconRoleV1, LexiconLocaleV1 } from './grammar/large-lexicons-v1.js';
export { LARGE_STORY_FORMAT_V1, LARGE_STORY_PAYLOAD_BITS, LARGE_STORY_SENTENCE_BITS,
  LARGE_STORY_MAX_PUBLIC_BYTES, encodeLargeStoryV1, decodeLargeStoryV1 } from './grammar/large-story-v1.js';
export type { LargeStoryResultV1 } from './grammar/large-story-v1.js';
export { createFrameRudimentsLargeStoryPreview } from './engine/story-panels.js';
