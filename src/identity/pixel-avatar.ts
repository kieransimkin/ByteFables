import { assertPublicValue, type PublicByteValue } from '../value.js';
import { concatBytes } from '../utils/binary.js';
import { sha256 } from './sha256.js';
import { identityDigest } from './identity.js';

const DOMAIN = new TextEncoder().encode('ByteFables:pixel-avatar:v1\0');

export interface PixelAvatarOptions {
  /** Output pixel extent, used only as an SVG width/height. Defaults to 128. */
  readonly size?: number;
}

/**
 * @deprecated Compatibility output for public legacy vectors only. New production
 * identity imagery MUST use FrameRudiments via the declarative generator bridge.
 * This function remains stable and does not gain effects, animation or new styles.
 */
export async function renderPixelAvatar(value: PublicByteValue, opts: PixelAvatarOptions = {}): Promise<string> {
  assertPublicValue(value);
  const size = opts.size ?? 128;
  if (!Number.isSafeInteger(size) || size < 16 || size > 4096) {
    throw new RangeError('SVG size must be an integer between 16 and 4096');
  }
  const seed = await sha256(concatBytes(DOMAIN, await identityDigest(value)));
  const hue = ((seed[16]! << 8) | seed[17]!) % 360;
  const hue2 = (hue + 125) % 360;
  const rectangles: string[] = [];
  for (let y = 0; y < 5; y++) {
    for (let x = 0; x < 3; x++) {
      const bitIndex = y * 3 + x;
      if (!(seed[bitIndex >>> 3]! & (1 << (bitIndex & 7)))) continue;
      const fill = (seed[18]! & (1 << (bitIndex & 7))) ? `hsl(${hue2} 75% 74%)` : `hsl(${hue} 70% 64%)`;
      const positions = x === 2 ? [2] : [x, 4 - x];
      for (const px of positions) {
        rectangles.push(`<rect x="${px * 16 + 10}" y="${y * 16 + 10}" width="16" height="16" fill="${fill}"/>`);
      }
    }
  }
  return `<svg xmlns="http://www.w3.org/2000/svg" width="${size}" height="${size}" viewBox="0 0 100 100" role="img" aria-label="Deterministic identity pattern"><rect width="100" height="100" rx="12" fill="#111827"/>${rectangles.join('')}</svg>`;
}
