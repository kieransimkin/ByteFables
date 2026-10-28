# Large English noun/adjective/past-verb lexicons and public story v1

**Status:** experimental, public-data-only written English. **Not** BIP-39,
Formosa/BIP-450, a secret backup format, a spoken mnemonic, or an authentication
mechanism. This specification is independent of existing ByteFables Story V2.

## Source research and immutable inputs

Three user-supplied research archives dated 27 October 2026 were inspected and
supplied the following *ordered, aligned* source lists. They were not generated
by a random word filler or downloaded from a third-party package at build time.
The original full chat exports, audits and alternatives remain research inputs;
the six canonical text lists and this format's references are checked in.

| Lexical role | Aligned US/UK entries | Different regional spellings | Max US length | Bits in isolated fixed-size slot |
| --- | ---: | ---: | ---: | ---: |
| Nouns | **16,396** | 179 | 10 | 14 |
| Adjectives | **10,569** | 177 | 16 | 13 |
| Past-tense transitive verbs | **3,554** | 265 | 20 | 11 |

The source archive SHA-256 hashes (the `(1)` and `(2)` suffixes are local duplicate
archive download names, not new language revisions):

- noun `noun_list_chat_full_export_2026-10-27(1).zip`: `30c06c8f0ea3b9503267dc71eede9cb774a8404a6ae5f5ef2b711408ad6aa948`
- adjective `adjective_chat_full_export_2026-10-27(1).zip`: `22d1043ecdc69a4ddf8d276a936781d7884f2eb24f05eecd82de8ec62d6d7138`
- verb `past_tense_verb_chat_export_2026-10-27(2).zip`: `ba597ead3eb544ba16c5095e7f23503bb24cf820c0a44045e322792aed7605eb`

The **3,613-entry** English past-tense research lists contain 59 duplicate
spellings; we use the already-deduplicated, aligned **3,554-entry** US/UK pair
rather than allowing ambiguous indexes. French translations contain duplicate
surface forms and are not a reversible codec. We do not silently reindex the
original 3,613 rows or treat a many-to-one translation as invertible.

The noun research's 16,396 entries already incorporate the homophone review and
restored US/UK forms. The original 10-character noun target does **not** hold
for every British spelling: 16 UK spellings exceed it. They are preserved rather
than truncated because index alignment takes priority. Some source entries are
plurals, rare, abstract or technical words, and some verb/object combinations are
semantically unnatural. The adjective corpus also includes multi-category words.
No grammatical naturalness, homophone-free speech, lexical frequency, or
intellectual-property provenance certification is inferred from the input lists.

The six files under `src/grammar/wordlists/large-v1/` are the canonical sources.
`node scripts/generate-lexicons-v1.mjs --check` checks their byte SHA-256,
row counts, per-locale uniqueness and the exact generated TypeScript module.
**Never alphabetise or edit the files in place** after releasing vectors. A
correction, translation, plural policy or pronunciation filter needs a new pack
ID/version and immutable migration/test vectors.

## Locale semantics

The same integer index points to an aligned conceptual item in en-US and en-GB,
with spelling differences such as `color/colour` and `organized/organised`.
An encoded story header always fixes its locale; a decoder NEVER guesses it.
Written spelling is exact lower-case ASCII. An index can be converted to the
other locale, but the resulting *text* is not the same canonical document.
En-US and en-GB are **separate codebook dialects with shared indices**, not
translations through untrusted NLP. Reversal of ordinary free text, speech
recognition and homophone-disambiguation are out of scope.

## Mathematically reversible sentence encoding

Each sentence uses precisely five data-bearing lexical slots:

1. adjective 1 — radix 10,569;
2. noun 1 — radix 16,396;
3. past-tense transitive verb — radix 3,554;
4. adjective 2 — radix 10,569;
5. noun 2 — radix 16,396.

Mixed-radix enumerative coding maps a 66-bit integer into those five indices
without modulo folding. The full product exceeds `2^66` but is below `2^67`,
so combinations outside the 66-bit range are **invalid**, never aliased.
The first **two** input bits select one of four visible sentence templates;
they are not free entropy. Each sentence consumes exactly **68 bits**.

| Prefix bits | Exact template |
| --- | --- |
| `00` | `Yesterday, the ADJ NOUN VERB the ADJ NOUN.` |
| `01` | `At dawn, the ADJ NOUN VERB the ADJ NOUN.` |
| `10` | `The ADJ NOUN VERB the ADJ NOUN before sunset.` |
| `11` | `At midnight, the ADJ NOUN VERB the ADJ NOUN.` |

The past tense avoids ordinary present-tense 3rd-person suffix agreement, but
it does not establish semantic compatibility (for example, people and abstract
nouns may act or be objects differently). Fixed filler words add no payload.

### Byte frame, ordering and canonical validation

```
line 1:  BYTEFABLES-LARGE-STORY-V1 en-US/1  (or en-GB/1)
byte 0..3: ASCII BFL3
byte 4:    0x01 format version
byte 5:    locale index, 0=en-US, 1=en-GB
byte 6..9: unsigned big-endian payload size, 0..4096
byte 10..: exact original PUBLIC bytes
trailer:   first 16 bytes of SHA-256(all preceding frame bytes)
```

The frame is expanded into MSB-first bits and divided into **68-bit** chunks;
only the last chunk may have zero padding. Decoder verifies template spelling,
role dictionaries, index range, padding, frame size and SHA-256 checksum, then
re-encodes and requires byte-for-byte identical canonical text. LF and CRLF are
accepted, but input case, punctuation, spaces, missing/extra sentences and
trailing newlines cannot be modified. The checksum detects accidental errors
but cannot authenticate data against an adversary able to recompute SHA-256.

The decoded result is **raw bytes plus locale only**: no network, key type,
original namespace, original mnemonic or wallet derivation path. Use an
independently validated typed public-record envelope if that context matters.
Absolutely no private seeds, keys, passwords or wallet material may enter this
experimental encoder or public CLI.

## Development and examples

```sh
node scripts/generate-lexicons-v1.mjs --check
npm run check
node bin/bytefables.mjs story-large-lexicons
node bin/bytefables.mjs story-large-encode --confirm-public \
  --public-hex 00010203 --namespace danceflow --kind node-id \
  --locale en-GB --raw > example-public-story.txt
node bin/bytefables.mjs story-large-decode --confirm-public \
  --story-file example-public-story.txt
```

The runtime TypeScript bundle contains a compact US/UK index-aligned pair
representation and requires no network, model weights, Node filesystem API or
runtime dependency. The original plain-text lists remain in the repository for
provenance; the generated bundle is checked against them in CI.

## Further research gates

- Improve semantically compatible subject/verb/object combinations using
  fixed-cardinality dependent dictionaries or an explicitly proven enumerative
  constraint code. Never secretly reject combinations based on a language model.
- Audit homophones, pronunciations, contractions, proper nouns, collective
  nouns and regional vocabulary. Written distinctness ≠ spoken distinctness.
- Gather independent proof of lexicon licensing/provenance and maintain its
  accepted/removed-entry audit before external wordlist distribution.
- Independently test NFKD/normalisation and cross-runtime fixtures if adding
  other languages; do not add unversioned automatic spell correction.
- Compare sentence comprehensibility and reading errors using blinded humans
  before offering this as a mnemonic representation to a general audience.

FrameRudiments-only preview of long stories is available via
`createFrameRudimentsLargeStoryPreview(value, 'en-GB', {box:[0,0,640,180]})`.
It returns native identity-text fragments and reports the number of **omitted**
sentences; it is a non-reversible thumbnail, not an archival encoding.
