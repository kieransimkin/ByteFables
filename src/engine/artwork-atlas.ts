/** Public-only batch atlas planner for the existing FrameRudiments artwork renderer.
 * This is a transport/layout descriptor, NOT a bitmap exporter or identity proof.
 */
import { PublicRecord, publicRecordDigest } from '../framing/public-record.js';
import { encodeHex } from '../codecs/hex.js';
import { createFrameRudimentsArtworkLayer,
  type FrameRudimentsLayer, type IdentityArtworkStyle, type IdentityPalette } from './framerudiments.js';

export const ARTWORK_ATLAS_VERSION = 'bytefables.artwork-atlas.v1' as const;
export interface ArtworkAtlasOptions {
  readonly tileSize?: number;
  readonly padding?: number;
  readonly columns?: number;
  readonly rowsPerPage?: number;
  readonly artwork?: IdentityArtworkStyle;
  readonly palette?: IdentityPalette;
  readonly complexity?: number;
}
export interface ArtworkAtlasTile {
  readonly inputIndex: number;
  readonly digestHex: string;
  /** Position within one atlas page; includes no implicit padding around texture. */
  readonly rect: readonly [number, number, number, number];
  /** UVs [u0,v0,u1,v1] in top-left image origin convention. */
  readonly uv: readonly [number, number, number, number];
  readonly layer: FrameRudimentsLayer;
}
export interface ArtworkAtlasPage {
  readonly index: number;
  readonly width: number;
  readonly height: number;
  readonly tiles: readonly ArtworkAtlasTile[];
}
export interface ArtworkAtlasPlan {
  readonly version: typeof ARTWORK_ATLAS_VERSION;
  readonly guarantee: 'presentation-only';
  readonly publicOnly: true;
  readonly inputCount: number;
  readonly pages: readonly ArtworkAtlasPage[];
}
function integer(v: number, lo: number, hi: number, field: string): number {
  if (!Number.isSafeInteger(v) || v < lo || v > hi) throw new RangeError(`Invalid ${field}`);
  return v;
}
/**
 * Same order in => same tile IDs/positions out, for a pinned FrameRudiments renderer.
 * The art source is a context-complete hash; the original payload is never
 * included in layer descriptors. Image pixels and final export checksums MUST
 * be independently verified by the FrameRudiments host.
 */
export async function createFrameRudimentsArtworkAtlas(
  records: readonly PublicRecord[], options: ArtworkAtlasOptions = {}
): Promise<ArtworkAtlasPlan> {
  if (!Array.isArray(records) || records.length < 1 || records.length > 1000 ||
      records.some(record => !(record instanceof PublicRecord))) {
    throw new TypeError('Atlas requires 1..1000 typed PUBLIC records');
  }
  const tileSize = integer(options.tileSize ?? 64, 16, 512, 'tileSize');
  const padding = integer(options.padding ?? 4, 0, 64, 'padding');
  const columns = integer(options.columns ?? 16, 1, 64, 'columns');
  const rowsPerPage = integer(options.rowsPerPage ?? 16, 1, 64, 'rowsPerPage');
  const complexity = integer(options.complexity ?? 4, 1, 8, 'complexity');
  const step = tileSize + 2 * padding;
  const capacity = columns * rowsPerPage;
  // v1 bridge has hard upper coordinate bound of 7680.
  const width = columns * step;
  if (width > 7680 || rowsPerPage * step > 7680) throw new RangeError('Atlas exceeds host pixel bounds');
  const pages: ArtworkAtlasPage[] = [];
  for (let offset = 0; offset < records.length; offset += capacity) {
    const batch = records.slice(offset, offset + capacity);
    const pageIndex = pages.length;
    const rows = Math.ceil(batch.length / columns);
    const height = rows * step;
    const tiles: ArtworkAtlasTile[] = [];
    for (let i = 0; i < batch.length; i++) {
      const inputIndex = offset + i;
      const x = (i % columns) * step + padding;
      const y = Math.floor(i / columns) * step + padding;
      const rect = Object.freeze([x, y, x + tileSize, y + tileSize]) as readonly [number,number,number,number];
      const uv = Object.freeze([x/width, y/height, (x+tileSize)/width, (y+tileSize)/height]) as readonly [number,number,number,number];
      const record = batch[i]!;
      const layer = await createFrameRudimentsArtworkLayer(record, {
        id: `atlas-${pageIndex}-${i}`, bounds: rect,
        ...(options.artwork === undefined ? {} : { artwork: options.artwork }),
        ...(options.palette === undefined ? {} : { palette: options.palette }),
        complexity
      });
      tiles.push(Object.freeze({ inputIndex, digestHex: encodeHex(await publicRecordDigest(record)),
        rect, uv, layer }));
    }
    pages.push(Object.freeze({ index: pageIndex, width, height, tiles: Object.freeze(tiles) }));
  }
  return Object.freeze({ version: ARTWORK_ATLAS_VERSION,
    guarantee: 'presentation-only' as const, publicOnly: true as const,
    inputCount: records.length, pages: Object.freeze(pages) });
}
