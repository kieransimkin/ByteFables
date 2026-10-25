/** Validated binary module-grid IR. NOT a QR encoder or a recovery format. */
import { createVectorScene, type VectorScene, type HexColor } from './vector-scene.js';

export interface ModuleMatrixSpec {
  readonly formatId: string;
  readonly width: number;
  readonly height: number;
  /** Row-major byte array of values 0 or 1; never a borrowed/mutable backing buffer. */
  readonly modules: Uint8Array;
  readonly quietZone?: number;
}
const FORMAT = /^[a-z][a-z0-9-]*(?:\/[a-z][a-z0-9-]*)+$/;

export class ModuleMatrix {
  readonly kind = 'module-matrix';
  readonly version = 1;
  readonly sensitivity = 'public';
  readonly formatId: string;
  readonly width: number;
  readonly height: number;
  readonly quietZone: number;
  readonly #modules: Uint8Array;

  constructor(spec: ModuleMatrixSpec) {
    if (!spec || typeof spec.formatId !== 'string' || !FORMAT.test(spec.formatId)) {
      throw new TypeError('ModuleMatrix needs a namespaced format ID');
    }
    const { width, height } = spec;
    if (!Number.isSafeInteger(width) || !Number.isSafeInteger(height) ||
        width < 1 || height < 1 || width > 256 || height > 256 || width * height > 65536 ||
        !(spec.modules instanceof Uint8Array) || spec.modules.length !== width * height ||
        spec.modules.some(v => v !== 0 && v !== 1)) {
      throw new TypeError('ModuleMatrix requires 1..256 binary cells in row-major order');
    }
    const quietZone = spec.quietZone ?? 4;
    if (!Number.isSafeInteger(quietZone) || quietZone < 0 || quietZone > 32) {
      throw new RangeError('Invalid module quiet zone');
    }
    this.formatId = spec.formatId;
    this.width = width;
    this.height = height;
    this.quietZone = quietZone;
    this.#modules = new Uint8Array(spec.modules);
    Object.freeze(this);
  }

  at(x: number, y: number): number {
    if (!Number.isSafeInteger(x) || !Number.isSafeInteger(y) ||
        x < 0 || x >= this.width || y < 0 || y >= this.height) {
      throw new RangeError('Matrix coordinates out of range');
    }
    return this.#modules[y * this.width + x]!;
  }

  toModules(): Uint8Array { return new Uint8Array(this.#modules); }
}

export interface ModuleMatrixSvgOptions {
  readonly pitch?: number;
  readonly foreground?: HexColor;
  readonly background?: HexColor;
}

/** Diagnostic conversion only. Production pixels/effects belong to FrameRudiments. */
export function moduleMatrixToVectorScene(matrix: ModuleMatrix, opts: ModuleMatrixSvgOptions = {}): VectorScene {
  if (!(matrix instanceof ModuleMatrix)) throw new TypeError('ModuleMatrix required');
  const pitch = opts.pitch ?? 4;
  if (!Number.isSafeInteger(pitch) || pitch < 1 || pitch > 16) {
    throw new RangeError('Module pitch must be 1–16');
  }
  const foreground = opts.foreground ?? '#000000';
  const background = opts.background ?? '#ffffff';
  const width = (matrix.width + 2 * matrix.quietZone) * pitch;
  const height = (matrix.height + 2 * matrix.quietZone) * pitch;
  if (width > 8192 || height > 8192) throw new RangeError('Module matrix output is too large');
  const primitives: Array<
    { kind: 'rect'; x: number; y: number; width: number; height: number; fill: HexColor } |
    { kind: 'path'; d: string; fill: HexColor }
  > = [{ kind: 'rect', x: 0, y: 0, width, height, fill: background }];
  let path = '';
  let runCount = 0;
  function flush(): void {
    if (path) primitives.push({ kind: 'path', d: path.trim(), fill: foreground });
    path = '';
    runCount = 0;
  }
  for (let y = 0; y < matrix.height; y++) {
    let x = 0;
    while (x < matrix.width) {
      if (matrix.at(x, y) === 0) { x++; continue; }
      const start = x;
      while (x < matrix.width && matrix.at(x, y) === 1) x++;
      const x0 = (start + matrix.quietZone) * pitch;
      const x1 = (x + matrix.quietZone) * pitch;
      const y0 = (y + matrix.quietZone) * pitch;
      const y1 = y0 + pitch;
      path += `M${x0} ${y0}L${x1} ${y0}L${x1} ${y1}L${x0} ${y1}Z `;
      if (++runCount === 200) flush(); // bounded path coordinates and string length
    }
  }
  flush();
  return createVectorScene({ width, height,
    title: `Public module matrix: ${matrix.formatId}`, primitives });
}
