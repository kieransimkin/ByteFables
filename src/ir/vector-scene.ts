/**
 * Minimal validated, renderer-neutral, *public* VectorScene v1.
 * No arbitrary XML, CSS, hyperlinks, fonts, script, or embedded images.
 * Coordinates are integer SVG user units for stable serialisation.
 */
export type HexColor = `#${string}`;
export type VectorPrimitive =
  | Readonly<{ kind: 'rect'; x: number; y: number; width: number; height: number; fill: HexColor }>
  | Readonly<{ kind: 'circle'; cx: number; cy: number; radius: number; fill: HexColor }>
  | Readonly<{ kind: 'line'; x1: number; y1: number; x2: number; y2: number; stroke: HexColor; strokeWidth: number }>
  | Readonly<{ kind: 'path'; d: string; fill: HexColor }>;

export interface VectorSceneSpec {
  readonly width: number;
  readonly height: number;
  readonly title?: string;
  readonly primitives: readonly VectorPrimitive[];
}

export type VectorScene = Readonly<{
  readonly kind: 'vector-scene';
  readonly version: 1;
  readonly sensitivity: 'public';
  readonly width: number;
  readonly height: number;
  readonly title: string;
  readonly primitives: readonly VectorPrimitive[];
}>;

const COLOR = /^#[0-9a-fA-F]{6}$/;
const PATH = /^[0-9.,+\-\sMmLlHhVvZz]+$/;
function coord(n: number, nonzero = false): void {
  if (!Number.isSafeInteger(n) || n < 0 || n > 16384 || (nonzero && n === 0)) {
    throw new RangeError('Vector coordinates must be bounded nonnegative integers');
  }
}
function color(c: string): void {
  if (typeof c !== 'string' || !COLOR.test(c)) throw new TypeError('Expected six-digit hex colour');
}
function validatePrimitive(p: VectorPrimitive): void {
  if (!p || typeof p !== 'object') throw new TypeError('Missing vector primitive');
  switch (p.kind) {
    case 'rect':
      coord(p.x); coord(p.y); coord(p.width, true); coord(p.height, true); color(p.fill); break;
    case 'circle':
      coord(p.cx); coord(p.cy); coord(p.radius, true); color(p.fill); break;
    case 'line':
      coord(p.x1); coord(p.y1); coord(p.x2); coord(p.y2);
      coord(p.strokeWidth, true); color(p.stroke); break;
    case 'path': {
      if (typeof p.d !== 'string' || p.d.length > 16384 || !PATH.test(p.d)) {
        throw new TypeError('Only bounded M/L/H/V/Z vector path syntax is supported');
      }
      const numbers = p.d.match(/[+-]?(?:\d+(?:\.\d*)?|\.\d+)/g) || [];
      if (numbers.length > 2048 || numbers.some(n => !Number.isFinite(+n) || Math.abs(+n) > 16384)) {
        throw new TypeError('Invalid path coordinates');
      }
      color(p.fill);
      break;
    }
    default: throw new TypeError('Unknown vector primitive');
  }
}

export function createVectorScene(spec: VectorSceneSpec): VectorScene {
  if (!spec || !Array.isArray(spec.primitives) || spec.primitives.length > 10000) {
    throw new RangeError('Invalid number of vector primitives');
  }
  coord(spec.width, true); coord(spec.height, true);
  if (spec.width > 8192 || spec.height > 8192) throw new RangeError('Vector viewport too large');
  const title = spec.title ?? '';
  if (typeof title !== 'string' || title.length > 256 || /[\u0000-\u001f\u007f]/.test(title)) {
    throw new TypeError('Invalid vector title');
  }
  const primitives: VectorPrimitive[] = spec.primitives.map(p => {
    validatePrimitive(p);
    return Object.freeze({ ...p });
  });
  return Object.freeze({ kind: 'vector-scene' as const, version: 1 as const,
    sensitivity: 'public' as const, width: spec.width, height: spec.height,
    title, primitives: Object.freeze(primitives) });
}
