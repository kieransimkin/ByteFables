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
  frameRudimentsEffectTarget } from './engine/framerudiments.js';
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
