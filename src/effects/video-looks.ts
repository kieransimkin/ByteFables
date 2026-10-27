/**
 * Declarative PUBLIC visual style recipes for the existing FrameRudiments
 * scoped-post-effects host. No bitmap filtering, shaders or media decoding
 * occurs in ByteFables. Identity artifacts remain decorative-only.
 */
import { PublicRecord, publicRecordDigest } from '../framing/public-record.js';
import { sha256 } from '../identity/sha256.js';
import { concatBytes } from '../utils/binary.js';
import { encodeHex } from '../codecs/hex.js';

export const PUBLIC_VIDEO_LOOK_VERSION = 'bytefables.public-video-look.v1' as const;
const DOMAIN = new TextEncoder().encode('ByteFables:framerudiments:video-look:v1\0');

/** Values and keys are explicitly accepted by the FrameRudiments VisualStyle host. */
const LOOK_DEFINITIONS = [
  { id: 'subtle-film', description: 'Subtle photographic grade and fine grain', visual: { saturation: 0.92, contrast: 1.07, grain: 0.035, vignette: 0.13 } },
  { id: 'noir', description: 'Monochrome high-contrast film', visual: { saturation: 0, contrast: 1.35, grain: 0.08, vignette: 0.42 } },
  { id: 'cool-grade', description: 'Cool hue-shifted, restrained colour', visual: { hue_shift: -18, saturation: 0.85, contrast: 1.13 } },
  { id: 'warm-grade', description: 'Warm saturated colour', visual: { hue_shift: 12, saturation: 1.18, contrast: 1.07 } },
  { id: 'neon-bloom', description: 'Luminous coloured edges', visual: { glow: 7, saturation: 1.35, contrast: 1.18 } },
  { id: 'crt-soft', description: 'Mild scanlines and channel shift', visual: { scanlines: 0.4, scanline_spacing: 4, chromatic_shift: 1, vignette: 0.24 } },
  { id: 'crt-heavy', description: 'Strong phosphor-style scanlines', visual: { scanlines: 0.76, scanline_spacing: 3, chromatic_shift: 2, grain: 0.045 } },
  { id: 'vhs-inspired', description: 'Synthetic analog-video imperfections, not a tape simulation', visual: { glitch: 0.28, scanlines: 0.23, grain: 0.16, chromatic_shift: 2 } },
  { id: 'retro-pixel', description: 'Nearest-neighbour blocks and limited tone', visual: { pixel_size: 6, posterize: 5, dither: 0.35 } },
  { id: 'print-halftone', description: 'Dot screen with high-contrast edges', visual: { halftone: 0.65, contrast: 1.14, edge_mix: 0.25 } },
  { id: 'solar-poster', description: 'Synthetic inverted highlights and reduced colour bands', visual: { solarize: 0.68, posterize: 6, saturation: 1.12 } },
  { id: 'bright-soft', description: 'Soft-focus highlights and diffuse texture', visual: { brightness: 1.12, blur: 2.5, glow: 1.6 } },
  { id: 'crisp-etched', description: 'Sharpened edges and compact detail', visual: { sharpen: 1.15, contrast: 1.14, edge_mix: 0.45 } },
  { id: 'dream-glow', description: 'Diffused light and a luminous haze', visual: { blur: 1.2, glow: 10, saturation: 1.05 } },
  { id: 'scanline-ghost', description: 'Dim scanline texture and grain', visual: { scanlines: 0.58, scanline_spacing: 6, grain: 0.055, vignette: 0.3 } },
  { id: 'minimal-matte', description: 'Reduced saturation and soft matte contrast', visual: { saturation: 0.48, contrast: 0.88, brightness: 1.04 } }
] as const;
export const VIDEO_LOOK_PRESETS = Object.freeze(LOOK_DEFINITIONS.map(x => Object.freeze({ ...x, visual: Object.freeze(x.visual) })));

export type VideoLookId = (typeof LOOK_DEFINITIONS)[number]['id'];
export interface PublicVideoLookOptions {
  /** Explicit look ID or hash-selected among the frozen 16 profiles. */
  readonly look?: VideoLookId | 'auto';
  /** 0 is no effect. The default is 1, the calibrated authored preset. */
  readonly intensity?: number;
  /** Native FrameRudiments effect surface, or the finished frame. */
  readonly target?: string;
  /** Optical / archival recovery regions may not receive artistic effects. */
  readonly purpose?: 'public-art' | 'public-video' | 'optical-recovery';
}

export interface PublicVideoLookPlan {
  readonly schema: typeof PUBLIC_VIDEO_LOOK_VERSION;
  readonly selectedLook: VideoLookId;
  readonly description: string;
  readonly digestHex: string;
  readonly intensity: number;
  readonly target: string;
  readonly grainSeed: number;
  readonly host: 'FrameRudiments';
  readonly recipeVersion: 1;
  readonly reversible: false;
  readonly authenticated: false;
  readonly profileSelectionBits: 4;
  readonly post_effects: null | Readonly<{ frame?: readonly object[]; elements?: Readonly<Record<string, readonly object[]>> }>;
  readonly warning: string;
}

const DEFAULTS: Readonly<Record<string, number>> = Object.freeze({
  saturation: 1, contrast: 1, brightness: 1, gamma: 1, pixel_size: 1,
  scanline_spacing: 4,
  hue_shift: 0, grain: 0, vignette: 0, glow: 0, blur: 0,
  scanlines: 0, chromatic_shift: 0, glitch: 0, posterize: 0, dither: 0,
  halftone: 0, solarize: 0, sharpen: 0, edge_mix: 0
});

function checkTarget(value: string): void {
  if (value !== 'frame' && !/^layer:[a-z][a-z0-9_-]{0,63}$/.test(value)) {
    throw new TypeError('Effect target must be frame or a named FrameRudiments layer');
  }
}

function blendStyle(visual: Readonly<Record<string, number>>, strength: number,
  grainSeed: number): Readonly<Record<string, number>> {
  const scaled: Record<string, number> = {};
  for (const [key, amount] of Object.entries(visual)) {
    const neutral = DEFAULTS[key];
    if (neutral === undefined || !Number.isFinite(amount)) throw new TypeError('Unsupported host style field');
    const value = neutral + (amount - neutral) * strength;
    if (['pixel_size', 'scanline_spacing', 'posterize'].includes(key)) {
      scaled[key] = Math.max(key === 'posterize' ? 0 : 1, Math.round(value));
    } else {
      scaled[key] = Number(value.toFixed(6));
    }
  }
  if ('grain' in scaled && scaled.grain! > 0) scaled.grain_seed = grainSeed;
  return Object.freeze(scaled);
}

/**
 * Produce a host-owned post_effects fragment. Only 4 seed bits select the look;
 * this is emphatically NOT a 256-bit image encoding or a unique identifier.
 */
export async function planPublicVideoLook(
  record: PublicRecord, options: PublicVideoLookOptions = {}
): Promise<PublicVideoLookPlan> {
  if (!(record instanceof PublicRecord)) throw new TypeError('Typed public record required');
  if (options.purpose === 'optical-recovery') {
    throw new RangeError('Artistic effects are forbidden on protected QR / recovery surfaces');
  }
  if (options.purpose !== undefined && !['public-art', 'public-video'].includes(options.purpose)) {
    throw new TypeError('Invalid video-look purpose');
  }
  const intensity = options.intensity ?? 1;
  if (typeof intensity !== 'number' || !Number.isFinite(intensity) || intensity < 0 || intensity > 1) {
    throw new RangeError('Look intensity must be 0..1');
  }
  // Safe default: never apply a whole-frame style that could touch a QR code.
  const target = options.target ?? 'layer:bytefables-identity';
  checkTarget(target);
  if (target === 'frame' && options.purpose !== 'public-video') {
    throw new RangeError('Frame-wide effects require explicit public-video purpose (no protected recovery code)');
  }
  const digest = await publicRecordDigest(record);
  const seed = await sha256(concatBytes(DOMAIN, digest));
  const grainSeed = (seed[1]! << 8) | seed[2]!;
  const id = options.look ?? 'auto';
  const preset = id === 'auto' ? VIDEO_LOOK_PRESETS[(seed[0]! >>> 4) & 0x0f]! :
    VIDEO_LOOK_PRESETS.find(p => p.id === id);
  if (!preset) throw new RangeError('Unknown public video look');
  const visual = blendStyle(preset.visual, intensity, grainSeed);
  const stage = Object.freeze({ id: 'bytefables-video-look-v1', visual });
  const post_effects = intensity === 0 ? null : target === 'frame' ?
    Object.freeze({ frame: Object.freeze([stage]) }) :
    Object.freeze({ elements: Object.freeze({ [target]: Object.freeze([stage]) }) });
  return Object.freeze({ schema: PUBLIC_VIDEO_LOOK_VERSION,
    selectedLook: preset.id, description: preset.description,
    digestHex: encodeHex(digest), intensity, target, grainSeed,
    host: 'FrameRudiments' as const, recipeVersion: 1 as const,
    reversible: false as const, authenticated: false as const,
    profileSelectionBits: 4 as const, post_effects,
    warning: 'Presentation only; never use on recoverable QR/symbol pixels or as cryptographic proof.' });
}
