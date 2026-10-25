/** Typed byte values. Type labels are contextual metadata, not encryption. */
export type Sensitivity = 'public' | 'secret';

export interface ByteValueOptions {
  readonly namespace: string;
  readonly kind: string;
}

const NAME_PATTERN = /^[a-z][a-z0-9._:/-]{0,127}$/;
const SECRET_KINDS = new Set([
  'private-key', 'wallet-seed', 'seed', 'secret', 'master-secret', 'secret-share'
]);

function validName(value: string, name: string): string {
  if (typeof value !== 'string' || !NAME_PATTERN.test(value)) {
    throw new TypeError(`${name} must match ${NAME_PATTERN.source}`);
  }
  return value;
}

export const MAX_VALUE_BYTES = 1024 * 1024;

/** PublicByteValue is the only allowed input for public identities and artwork. */
export class ByteValue<S extends Sensitivity> {
  readonly namespace: string;
  readonly kind: string;
  readonly sensitivity: S;
  readonly #bytes: Uint8Array;

  private constructor(bytes: Uint8Array, options: ByteValueOptions, sensitivity: S) {
    if (!(bytes instanceof Uint8Array)) throw new TypeError('Expected Uint8Array');
    if (bytes.byteLength > MAX_VALUE_BYTES) throw new RangeError('Binary value too large');
    this.namespace = validName(options.namespace, 'namespace');
    this.kind = validName(options.kind, 'kind');
    this.sensitivity = sensitivity;
    this.#bytes = new Uint8Array(bytes); // snapshot; no external mutable references
    Object.freeze(this);
  }

  static public(bytes: Uint8Array, options: ByteValueOptions): ByteValue<'public'> {
    if (SECRET_KINDS.has(options.kind)) {
      throw new TypeError('Sensitive object kind cannot be labelled public');
    }
    return new ByteValue(bytes, options, 'public');
  }

  static secret(bytes: Uint8Array, options: ByteValueOptions): ByteValue<'secret'> {
    return new ByteValue(bytes, options, 'secret');
  }

  get byteLength(): number { return this.#bytes.byteLength; }

  /** Explicit byte access returns a copy. Do not log or serialise secret values. */
  toBytes(): Uint8Array { return new Uint8Array(this.#bytes); }
}

export type PublicByteValue = ByteValue<'public'>;
export type SecretByteValue = ByteValue<'secret'>;

/** Runtime guard as well as TypeScript typing: secrets cannot enter public visualisers. */
export function assertPublicValue(value: PublicByteValue): void {
  if (!(value instanceof ByteValue) || value.sensitivity !== 'public') {
    throw new TypeError('A public ByteValue is required');
  }
}
