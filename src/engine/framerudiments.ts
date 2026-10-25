/**
 * Public-only, declarative bridge to FrameRudiments' trusted Python renderer registry.
 * ByteFables determines WHAT to show; FrameRudiments owns all pixels, transforms,
 * modulation, scoped effects, compositing, antialiasing, animation and final media.
 * This module never invokes a rendering process or creates an image.
 */
import { PublicRecord, publicRecordDigest } from '../framing/public-record.js';
import { encodeHex } from '../codecs/hex.js';
import { ModuleMatrix } from '../ir/module-matrix.js';
import { createVectorScene, type VectorScene } from '../ir/vector-scene.js';
import { planPublicFractal, type FractalFamily, type FractalPalette } from '../identity/fractal-seed.js';

export const FRAMERUDIMENTS_BRIDGE_VERSION = 'bytefables.framerudiments.layer.v1';
export type IdentityPalette = 'neon' | 'mono' | 'pastel';
export interface LayerPlacement {
  /** FrameRudiments project-layer ID, unique within a project. */
  readonly id: string;
  /** Pixel bounds [left, top, right, bottom], relative to project frame. */
  readonly bounds: readonly [number, number, number, number];
}
export interface IdentityLayerOptions extends LayerPlacement {
  readonly palette?: IdentityPalette;
}
export type FrameRudimentsLayer = Readonly<{
  readonly id: string;
  readonly type: 'rudiment';
  readonly renderer: 'bytefables-pixel-v1' | 'bytefables-matrix-v1' | 'bytefables-scene-v1' | 'bytefables-fractal-v1';
  readonly bounds: readonly [number, number, number, number];
  readonly motion: Readonly<{ kind: 'named'; pattern: 'circle' }>;
  readonly axes: readonly [number];
  readonly history_frames: 1;
  readonly style: Readonly<Record<string, unknown>>;
}>;
const LAYER_ID = /^[a-z][a-z0-9_-]{0,63}$/;
const ABSOLUTE_VECTOR_PATH = /^[0-9.,+\-\sMLHVZ]+$/;

/** v1 bridge accepts closed, explicit absolute paths, not all SVG path syntax. */
function validateClosedAbsolutePath(d: string): void {
  if (!ABSOLUTE_VECTOR_PATH.test(d) || d.length > 4096) {
    throw new TypeError('FrameRudiments only supports bounded absolute M/L/H/V/Z paths');
  }
  const tokens = d.match(/[MLHVZ]|[+-]?(?:\d+(?:\.\d*)?|\.\d+)/g);
  if (!tokens || tokens.length > 2048 ||
      tokens.join('') !== d.replace(/[\s,]/g, '')) {
    throw new TypeError('Malformed absolute vector path');
  }
  let i = 0;
  let cmd: string | null = null;
  let count = 0;
  let closed = 0;
  while (i < tokens.length) {
    const token = tokens[i]!;
    if (/^[MLHVZ]$/.test(token)) { cmd = token; i++; }
    if (!cmd) throw new TypeError('Missing vector path command');
    if (cmd === 'Z') {
      if (count < 3) throw new TypeError('Open or undersized vector polygon');
      closed++;
      count = 0;
      cmd = null;
      continue;
    }
    if (cmd !== 'M' && count === 0) throw new TypeError('Vector polygon must start with M');
    const arity = cmd === 'M' || cmd === 'L' ? 2 : 1;
    if (i + arity > tokens.length) throw new TypeError('Missing vector coordinate');
    for (let j = 0; j < arity; j++) {
      const n = Number(tokens[i + j]);
      if (!Number.isFinite(n) || n < 0 || n > 16384 ||
          /^[MLHVZ]$/.test(tokens[i + j]!)) {
        throw new TypeError('Invalid vector coordinate');
      }
    }
    i += arity;
    count++;
    if (cmd === 'M') cmd = 'L';
  }
  if (count !== 0 || closed === 0) throw new TypeError('Vector path must close with Z');
}

function immutableStyle<T>(value: T): T {
  if (Array.isArray(value)) return Object.freeze(value.map(x => immutableStyle(x))) as T;
  if (value !== null && typeof value === 'object') {
    const copy = Object.fromEntries(Object.entries(value).map(([k, v]) => [k, immutableStyle(v)]));
    return Object.freeze(copy) as T;
  }
  return value;
}

function base(options: LayerPlacement, renderer: FrameRudimentsLayer['renderer'],
  style: Readonly<Record<string, unknown>>): FrameRudimentsLayer {
  if (!options || typeof options.id !== 'string' || !LAYER_ID.test(options.id) ||
      !Array.isArray(options.bounds) || options.bounds.length !== 4 ||
      options.bounds.some(n => !Number.isSafeInteger(n) || n < 0 || n > 7680) ||
      options.bounds[2]! <= options.bounds[0]! ||
      options.bounds[3]! <= options.bounds[1]!) {
    throw new TypeError('Invalid FrameRudiments layer ID or pixel bounds');
  }
  return Object.freeze({
    id: options.id, type: 'rudiment' as const, renderer,
    bounds: Object.freeze([...options.bounds]) as unknown as readonly [number, number, number, number],
    // FrameRudiments requires a native motion route even for a static identity.
    // The generator deliberately ignores this motion; other native effects may use it.
    motion: Object.freeze({ kind: 'named' as const, pattern: 'circle' as const }),
    axes: Object.freeze([0]) as readonly [number], history_frames: 1 as const,
    style: immutableStyle(style)
  });
}

/** Static public identicon provider. The host's layer:ID post effects remain available. */
export async function createFrameRudimentsIdentityLayer(
  record: PublicRecord, options: IdentityLayerOptions
): Promise<FrameRudimentsLayer> {
  if (!(record instanceof PublicRecord)) throw new TypeError('A typed PUBLIC record is required');
  const palette = options.palette ?? 'neon';
  if (!['neon', 'mono', 'pastel'].includes(palette)) throw new TypeError('Invalid identity palette');
  // Context-complete SHA-256 commitment, never the secret or original raw key bytes.
  const digestHex = encodeHex(await publicRecordDigest(record));
  return base(options, 'bytefables-pixel-v1', {
    bridge_version: FRAMERUDIMENTS_BRIDGE_VERSION, digest_hex: digestHex, palette
  });
}

/**
 * Pass already-encoded PUBLIC modules to the native FrameRudiments pipeline.
 * This is NOT a QR encoder. FrameRudiments effects may damage recoverable
 * symbols: only independent post-export scanning can establish recoverability.
 */
export function createFrameRudimentsMatrixLayer(
  matrix: ModuleMatrix, options: LayerPlacement
): FrameRudimentsLayer {
  if (!(matrix instanceof ModuleMatrix)) throw new TypeError('PUBLIC ModuleMatrix required');
  const bits = [...matrix.toModules()].join('');
  return base(options, 'bytefables-matrix-v1', {
    bridge_version: FRAMERUDIMENTS_BRIDGE_VERSION,
    format_id: matrix.formatId, width: matrix.width, height: matrix.height,
    quiet_zone: matrix.quietZone, modules: bits
  });
}

/**
 * Strict vector primitive handoff. Native FrameRudiments owns shape rasterisation
 * and its existing effects graph. SVG is only a debug/compatibility exporter.
 * v1 bridge supports absolute M/L/H/V/Z paths; unsupported paths fail closed.
 */
export function createFrameRudimentsSceneLayer(
  scene: VectorScene, options: LayerPlacement
): FrameRudimentsLayer {
  const checked = createVectorScene(scene);
  if (checked.primitives.length > 1000) throw new RangeError('FrameRudiments scene exceeds 1,000 shapes');
  for (const item of checked.primitives) {
    if (item.kind === 'path') validateClosedAbsolutePath(item.d);
  }
  // Copy into plain JSON-compatible data; no arbitrary SVG, scripts, URLs or commands.
  return base(options, 'bytefables-scene-v1', {
    bridge_version: FRAMERUDIMENTS_BRIDGE_VERSION,
    scene: { width: checked.width, height: checked.height,
      primitives: checked.primitives.map(item => ({ ...item })) }
  });
}

export interface FractalLayerOptions extends LayerPlacement {
  readonly family?: FractalFamily;
  readonly palette?: FractalPalette;
  readonly quality?: 'draft' | 'standard';
}

/**
 * Public data -> deterministic, registered FrameRudiments fractal generator.
 * Only the frozen public digest and 8 explicitly chosen source bits reach the
 * host; all effects, modulation and media rendering stay in FrameRudiments.
 */
export async function createFrameRudimentsFractalLayer(
  record: PublicRecord, options: FractalLayerOptions
): Promise<FrameRudimentsLayer> {
  if (!options || !Array.isArray(options.bounds) || options.bounds.length !== 4) {
    throw new TypeError('Fractal layer requires a bounded viewport');
  }
  const width = options.bounds[2]! - options.bounds[0]!;
  const height = options.bounds[3]! - options.bounds[1]!;
  if (!Number.isSafeInteger(width) || !Number.isSafeInteger(height) ||
      width < 16 || height < 16 || width > 1024 || height > 1024 ||
      width * height > 262144) {
    throw new RangeError('Fractal layer viewport requires 16..1024 px and <=262144 source pixels');
  }
  const family = options.family ?? 'julia';
  const palette = options.palette ?? 'neon';
  const quality = options.quality ?? 'draft';
  if (!['draft', 'standard'].includes(quality)) throw new TypeError('Invalid fractal quality');
  const plan = await planPublicFractal(record, family, palette);
  return base(options, 'bytefables-fractal-v1', {
    bridge_version: FRAMERUDIMENTS_BRIDGE_VERSION,
    family: plan.family, palette: plan.palette,
    seed_hex: plan.seedHex, feature_bits: plan.featureBits, quality
  });
}

/** Caller's native FrameRudiments project owns effect_graph and post_effects. */
export function frameRudimentsEffectTarget(layer: FrameRudimentsLayer): string {
  if (!layer || !LAYER_ID.test(layer.id)) throw new TypeError('Invalid layer');
  return `layer:${layer.id}`;
}
