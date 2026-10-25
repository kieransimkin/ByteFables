/**
 * DRAFT TYPES ONLY. No implementations, importers, exporters or public catalogue
 * claims. Future IR adapters MUST add validators, caps and dedicated versions.
 */
export interface SpatialSceneDraft {
  readonly kind: 'spatial-scene';
  readonly sensitivity: 'public';
  readonly meshes: readonly { readonly positions: Float32Array; readonly indices: Uint32Array }[];
  readonly coordinateSystem: string;
}
export interface TemporalSceneDraft {
  readonly kind: 'temporal-scene';
  readonly sensitivity: 'public';
  readonly durationMs: number;
  readonly events: readonly { readonly timeMs: number; readonly sceneId: string }[];
}
export interface AcousticPacketStreamDraft {
  readonly kind: 'acoustic-packet-stream';
  readonly sensitivity: 'public';
  readonly sampleRateHz: number;
  readonly protocolId: string;
  readonly frames: readonly Uint8Array[];
}
export interface TactileSequenceDraft {
  readonly kind: 'tactile-sequence';
  readonly sensitivity: 'public';
  readonly events: readonly { readonly offsetMs: number; readonly durationMs: number; readonly intensity: number }[];
}
export interface LayoutDocumentDraft {
  readonly kind: 'layout-document';
  readonly sensitivity: 'public';
  readonly pageWidthUm: number;
  readonly pageHeightUm: number;
  readonly scenes: readonly VectorScene[];
}
import type { VectorScene } from './vector-scene.js';
