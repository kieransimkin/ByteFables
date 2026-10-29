/** Deterministic PUBLIC identity art contact sheets for FrameRudiments.
 * This module plans layers; the native host owns all rasterization and exports.
 * Artwork is identity-only, never a recoverable encoding or authentication.
 */
import { PublicRecord, publicRecordDigest } from '../framing/public-record.js';
import { encodeHex } from '../codecs/hex.js';
import { createFrameRudimentsArtworkLayer,
  type FrameRudimentsLayer, type IdentityPalette, type IdentityArtworkStyle } from './framerudiments.js';

export const ARTWORK_GALLERY_VERSION = 'bytefables.artwork-gallery.v1' as const;
export const ARTWORK_GALLERY_FAMILIES: readonly IdentityArtworkStyle[] = Object.freeze([
  'sigil', 'constellation', 'heraldry', 'topography', 'crystal',
  'mandala', 'cellular', 'branching', 'orbital'
]);
export const ARTWORK_GALLERY_PALETTES: readonly IdentityPalette[] = Object.freeze([
  'neon', 'pastel', 'mono'
]);

export interface ArtworkGalleryOptions {
  /** Source square size in host pixels. */
  readonly tileSize?: number;
  /** Gap between image tiles, in pixels. */
  readonly gap?: number;
  readonly columns?: number;
  readonly complexity?: number;
  /** For gallery comparisons, select a subset; ordering is preserved. */
  readonly families?: readonly IdentityArtworkStyle[];
  readonly palettes?: readonly IdentityPalette[];
  /** Safe native layer prefix, not a path. */
  readonly idPrefix?: string;
}
export interface ArtworkGalleryTile {
  readonly family: IdentityArtworkStyle;
  readonly palette: IdentityPalette;
  readonly index: number;
  readonly layer: FrameRudimentsLayer;
}
export interface ArtworkGalleryPlan {
  readonly version: typeof ARTWORK_GALLERY_VERSION;
  readonly identityDigestHex: string;
  readonly width: number;
  readonly height: number;
  readonly columns: number;
  readonly rows: number;
  readonly tiles: readonly ArtworkGalleryTile[];
  readonly guarantee: 'presentation-only';
  readonly publicOnly: true;
}
const allowedFamily = new Set<string>(ARTWORK_GALLERY_FAMILIES);
const allowedPalette = new Set<string>(ARTWORK_GALLERY_PALETTES);
function positiveInteger(value: number, minimum: number, maximum: number, name: string): number {
  if (!Number.isSafeInteger(value) || value < minimum || value > maximum)
    throw new RangeError(`Invalid ${name}: expected ${minimum}..${maximum}`);
  return value;
}
function uniqueSubset<T extends string>(items: readonly T[], allowed: Set<string>, name: string): readonly T[] {
  if (!Array.isArray(items) || items.length === 0 ||
      new Set(items).size !== items.length || items.some(i => !allowed.has(i)))
    throw new TypeError(`Invalid ${name} selection`);
  return Object.freeze([...items]);
}
/** 27 stable style/palette comparisons by default, with bounded layer geometry.
 * No source bytes are included in style fields; every renderer receives the
 * context-complete public digest via the existing validated bridge.
 */
export async function createFrameRudimentsArtworkGallery(
  record: PublicRecord, options: ArtworkGalleryOptions = {}
): Promise<ArtworkGalleryPlan> {
  if (!(record instanceof PublicRecord)) throw new TypeError('PublicRecord required');
  const tileSize = positiveInteger(options.tileSize ?? 128, 16, 1024, 'tileSize');
  const gap = positiveInteger(options.gap ?? 16, 0, 256, 'gap');
  const columns = positiveInteger(options.columns ?? 6, 1, 27, 'columns');
  const complexity = positiveInteger(options.complexity ?? 4, 1, 8, 'complexity');
  const prefix = options.idPrefix ?? 'gallery';
  if (!/^[a-z][a-z0-9_-]{0,40}$/.test(prefix)) throw new TypeError('Invalid gallery layer prefix');
  const families = uniqueSubset(options.families ?? ARTWORK_GALLERY_FAMILIES,
    allowedFamily, 'families');
  const palettes = uniqueSubset(options.palettes ?? ARTWORK_GALLERY_PALETTES,
    allowedPalette, 'palettes');
  const count = families.length * palettes.length;
  const usedColumns = Math.min(columns, count);
  const rows = Math.ceil(count / usedColumns);
  const width = usedColumns * tileSize + (usedColumns - 1) * gap;
  const height = rows * tileSize + (rows - 1) * gap;
  // Host layer coordinates are limited to 7680 px in the v1 bridge.
  if (width > 7680 || height > 7680) throw new RangeError('Gallery exceeds host bounds');
  const digestHex = encodeHex(await publicRecordDigest(record));
  const tiles: ArtworkGalleryTile[] = [];
  for (const family of families) for (const palette of palettes) {
    const index = tiles.length;
    const x = (index % usedColumns) * (tileSize + gap);
    const y = Math.floor(index / usedColumns) * (tileSize + gap);
    const layer = await createFrameRudimentsArtworkLayer(record, {
      id: `${prefix}-${index}`, bounds: [x, y, x + tileSize, y + tileSize],
      artwork: family, palette, complexity
    });
    tiles.push(Object.freeze({ family, palette, index, layer }));
  }
  return Object.freeze({ version: ARTWORK_GALLERY_VERSION,
    identityDigestHex: digestHex, width, height, columns: usedColumns, rows,
    tiles: Object.freeze(tiles), guarantee: 'presentation-only' as const,
    publicOnly: true as const });
}
