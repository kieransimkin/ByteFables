# ByteFables Story V2 — experimental reversible public-data sentence formats

**Status:** Stage 2 prototype specification, 2026-10-25. **NOT BIP-39/BIP-450,
NOT a wallet backup, NOT an authenticator.** These are two separate, immutable,
experimental *raw-byte* serializations. Neither preserves the `ByteValue`
namespace, kind, network, derivation path or wallet metadata. Their contents
MUST be publicly distributable. The phrase format does not increase entropy.

## 1. Inputs and supported formats

| Format | Literal first line | Selection | Raw capacity per sentence |
| --- | --- | --- | --- |
| Prefix | `BYTEFABLES-STORY-V2 THEME/1` | Consume a complete binary prefix code | 33/34/35/35 bits |
| Scheduled | `BYTEFABLES-SCHEDULED-STORY-1 THEME/1` | Explicit marker and deterministic bounded DP | 24/32/40 bits |

`THEME` is one of `nature`, `technology`, `music`, `fantasy`, `science`,
`humour` (in exactly that order; integer theme IDs 0–5). Public source bytes
are 0–4,096 octets, including empty input and leading zeroes.

The decoder accepts LF and CRLF line separators, but no other whitespace,
Unicode normalisation, invisible characters, alternative casing, punctuation,
missing/extra sentences or trailing newline. Each text line is ASCII. This
strictness is a wire property rather than a recommendation to users writing
sentences by hand.

## 2. Binary framing

The two formats use DIFFERENT magic and version values, preventing accidental
cross-protocol decoding:

```
byte 0..3:  ASCII BFS2 (prefix) or BFSV (scheduled)
byte 4:     0x02 (prefix) or 0x01 (scheduled)
byte 5:     theme ID (0..5)
byte 6..9:  source length as unsigned big-endian u32 (0..4096)
byte 10..:  exact original PUBLIC bytes
trailer:    first 16 octets of SHA-256(all previous envelope bytes)
```

Checksum strength is 128 bits of unkeyed SHA-256 for **accidental integrity**.
An active adversary can change the public bytes and recompute the checksum.
This is never a MAC, signature, proof of key ownership, wallet authenticator or
secret protection scheme. A decoded envelope returns raw bytes plus theme only.

Frame length in bits is `8*(26+payloadBytes)`. Bits are MSB-first, zero-padded
only in the last sentence. Recovery must check the full framing and checksum,
then **re-encode the complete phrase and compare exactly**; this rejects
noncanonical padding, alternate schedules, spurious extra sentences and many
ambiguities in future decoders.

## 3. Prefix scheme (`BFS2`)

Six immutable lexicon packs share four prefix-free grammar structures.
Every template has four lexical positions; each has exactly 256 distinct two-word
choices, for `4 * 8 = 32` lexical data bits. The template prefixes are:

```
0     -> "At the [place], the [appearance] [subject] [action]."      (33 bits)
10    -> "Sometimes the [appearance] [subject] [action] beside the [place]." (34 bits)
110   -> "Beyond the [place], the [appearance] [subject] [action]."  (35 bits)
111   -> "When the [appearance] [subject] [action], the [place] glimmers." (35 bits)
```

The prefix is **actual source data**, not an aesthetically derived random choice.
The code is complete and prefix-free: 1/2 + 1/4 + 1/8 + 1/8 = 1. Read that
many leading bits, choose the template, then map the next 32 bits to four
256-word lexemes, in textual slot order. If the final sentence extends past
EOF, zero-fill to its selected capacity. A decoder obtains the prefix from the
visible unique first literal and appends exactly the 32 recovered bits.

This family uses compact deterministic cross-product dictionaries: e.g. a
16-word modifier table followed by a 16-word noun table. The result has 256
unique two-word lexemes. **Index order is fixed**; modifying spelling, sorting,
word count, tense, template literal or punctuation requires a NEW version.

The 33/34/35-bit capacity statement is about formally recoverable bits, not
Shannon entropy of natural language, memory quality or name collision budgets.

## 4. Scheduled scheme (`BFSV`)

This experimental alternative uses three explicitly marked templates:

* `By moonlight, ...`: three 256-entry lexical slots => 24 data bits.
* `Across the ...`: four 256-entry lexical slots => 32 data bits.
* `Although the ...`: five 256-entry lexical slots => 40 data bits.

The grammar marker is a visibly transmitted selector, so it **does not** count
as a data bit. For a frame of `B` bits, a bounded, deterministic dynamic
programming pass chooses a sequence of templates. Each has a fixed format cost
of 10, 13 or 17, plus two cost units for each final padded bit. This model
minimises the total declared cost, not a verified spoken-comprehension metric.
Caller order is the stable tie-break. All sentences except the final one use
all their selected payload capacity; the final sentence is zero padded.

Decoding reads each marker, decodes exactly that template's lexical capacity,
concatenates those bits and validates framing/checksum. Then the canonical
encoder must produce *exactly the same sequence*, including scheduler choices.

The scheduler is also separately exported for later authoring and optimisation;
it operates on integer capacities and costs, not LLM outputs. The limit is
50,000 bits and 16 choices. It is intentionally kept independent from the
reversible prefix scheme, where arbitrary template optimisation would change
which source bits are consumed.

## 5. Grammar compiler and dependent dictionaries

`compileStoryPack` accepts 2–16 templates with unique stable IDs, prefix-free
and complete 1–8-bit binary prefixes, unique literal openers and bounded parts.
A slot has 2–256 unique ASCII lexemes (each 1–4 lexical words); all entries in
one slot have an equal lexical word count for bounded parsing.

For **non-power-of-two** dictionaries, the encoder uses exact mixed-radix
*enumerative coding*: a sequence of dictionary radices `(r1,...,rn)` carries
`floor(log2(product(ri)))` bits. Integer encoding is bijective within that
2^B-subset. The decoder rejects surplus Cartesian-product combinations rather
than applying modulo or returning ambiguous values.

A **dependent dictionary** can change lexical choices according to a prior
independent slot, but every branch must expose the same number of choices and
same token count. The compiler checks the complete dependency map, duplicate
words, role reuse, delimiter boundaries and declared capacities. A separate
`makeVerbAgreementChoices` helper produces frozen singular/plural inflection
branches from explicitly supplied forms; no grammatical inflection is guessed
at recovery time.

The optional `auditLexicon` flags some edit-distance-one confusion and known
homophone pairs. It is NOT an exhaustive linguistic, phonetic or accessibility
qualification and has no authority to change frozen codebooks.

## 6. Stable context and FrameRudiments

ByteFables performs lexical encoding/decoding only. It does not rasterise the
story or provide a second effects pipeline. `createFrameRudimentsStoryPreview`
returns up to four `identity` text blocks for the EXISTING
`framerudiments.project.v1` project, plus eligible `identity:N` effect targets.
The caller MUST supply a checksum-pinned TTF/OTF project font and allow
FrameRudiments to handle actual text rasterisation, compositing, animation and
post-processing. Preview text is deliberately truncated and **not recoverable**
when any sentences are omitted; complete story text must be stored separately.

Do not apply effects, generative paraphrasing, automated translation or
whitespace rewriting to an archival story and then claim it still decodes.
Only unmodified, independently read-back encoded text has a valid lossless
claim.

## 7. Test evidence and migration rules

`tests/vectors/story-v2.json` fixes examples for all six themes and both
formats, plus SHA-256 commitments to the complete compiled pack index/order.
`node scripts/story-vectors.mjs --check` fails whenever those immutable
codebooks or example sentences change. Test suite also covers random and
edge-case payload lengths, exhaustively enumerates a small conditional grammar,
rejects malformed/unrecognised strings, and compares re-encoded texts.

These tests are **not** independent wallet interoperability or external
cryptographic review. No private keys should be entered. For a public
identifier requiring authentication, use the FULL authenticated identifier,
not a story or its unkeyed checksum.

The original `BYTEFABLES-STORY-PROTOTYPE-1` / `BFBL` legacy codec is unchanged
and remains a separately decodable 13-bit experimental format. Changing any
v2 dictionary or grammar requires a new `THEME/N` and framing/registry version
and a documented migration; do NOT rewrite old codebooks in-place.
