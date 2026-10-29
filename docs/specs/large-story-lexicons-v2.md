# Experimental large public story v2 (BFL4)

This is a **new** binary wire format. V1 `BFL3` and all its frozen dictionary indices and text vectors remain unchanged. This is not a wallet, secret-backup or speech-safe format.

## Contract

The same immutable six American/British lists from `large-lexicons-v1` are reused, in the same index order. Each sentence has two adjective slots (radix 10,569), two noun slots (16,396) and one transitive past verb slot (3,554). Their mixed-radix product contains exactly **66 data bits**; the first **3 bits** select one of eight mutually distinct fixed sentence templates. Every sentence carries **69 source bits**. No rounding of individual word capacities is used.

The `BFL4` frame uses ASCII BFL4 (4 bytes), version `02`, locale byte (`00` US or `01` GB), unsigned 32-bit big-endian payload length, 0..4096 public payload bytes, and a 16-byte truncated SHA256 over the entire preceding frame. Encoding is MSB-first into 69-bit blocks, padding only the last block with zeros. The first line is `BYTEFABLES-LARGE-STORY-V2 en-GB/2` or `en-US/2`. Decoder validates canonical case, space, punctuation, article agreement, dictionary order, checksum and exact round-trip re-encoding.

Eight template labels: Yesterday; At dawn; The ... before sunset; At midnight; Long ago; After the storm; Suddenly; Once. The last two have a computed `a`/`an` determiner based on *written initial vowel of the following adjective*. This is a deliberately simple orthographic rule, **not** a claim of phonetic grammatical correctness (e.g., silent h and initial vowel sounding like y). The determiner is redundant text and carries zero bits. All templates retain the same five data-bearing slots, verb/object order and grammar capacity. Naturalness and semantic plausibility are unqualified.

V2 uses separate magic/version, so it cannot decode V1 strings. The checksum is for accidental errors and is **not** authentication. Output is raw bytes and locale only; namespace, kind, networks and provenance are not recovered without a separately encoded public-record envelope. The current codec rejects secrets by typed public-only API.

## Manual test

```sh
npm run check
node bin/bytefables.mjs story-large-v2-encode --confirm-public --public-hex 010203 --namespace danceflow --kind node-id --locale en-GB --raw > public.txt
node bin/bytefables.mjs story-large-v2-decode --confirm-public --story-file public.txt
```

Next engineering gate: reviewed noun animacy and countability tags, a syntactically defensible verb-valency model, homophone/confusability audits, and conditional mixed-radix dictionaries backed by separately frozen vectors. Do **not** silently discard lexical alternatives or claim all past verbs accept every noun as subject/object.
