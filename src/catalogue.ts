/** Explicit maturity flags keep prototypes from being presented as wallet-ready standards. */
export type Category = 'lossless' | 'identity' | 'archival';
export type Maturity = 'foundation' | 'experimental' | 'planned';
export interface CatalogueEntry {
  readonly id: string;
  readonly category: Category;
  readonly maturity: Maturity;
  readonly reversible: boolean;
  readonly handlesSecrets: boolean;
}

const ENTRIES: CatalogueEntry[] = [
  { id: 'hex', category: 'lossless', maturity: 'foundation', reversible: true, handlesSecrets: false },
  { id: 'rfc4648-base32-nopad', category: 'lossless', maturity: 'foundation', reversible: true, handlesSecrets: false },
  { id: 'bytefables-story-prototype-1', category: 'lossless', maturity: 'experimental', reversible: true, handlesSecrets: false },
  { id: 'public-identity-sha256-v1', category: 'identity', maturity: 'foundation', reversible: false, handlesSecrets: false },
  { id: 'pixel-avatar-v1', category: 'identity', maturity: 'foundation', reversible: false, handlesSecrets: false },
  { id: 'short-hash-24-v1', category: 'identity', maturity: 'foundation', reversible: false, handlesSecrets: false },
  { id: 'short-hash-32-v1', category: 'identity', maturity: 'foundation', reversible: false, handlesSecrets: false },
  { id: 'short-hash-64-v1', category: 'identity', maturity: 'foundation', reversible: false, handlesSecrets: false },
  { id: 'bip39', category: 'archival', maturity: 'planned', reversible: true, handlesSecrets: false },
  { id: 'bytewords-ur', category: 'archival', maturity: 'planned', reversible: true, handlesSecrets: false },
  { id: 'qr', category: 'archival', maturity: 'planned', reversible: true, handlesSecrets: false },
  { id: 'slip39', category: 'archival', maturity: 'planned', reversible: true, handlesSecrets: false }
];
export const CATALOGUE: readonly CatalogueEntry[] = Object.freeze(ENTRIES.map(x => Object.freeze(x)));
