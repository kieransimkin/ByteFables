# Artwork generator v2 candidate, promotion gate v1

Status: opt-in engineering candidate. **The production `ArtworkRenderer` remains v1.**
This milestone freezes the successful remediation experiments behind a versioned
candidate surface and adds a reproducible promotion gate. It does not silently
change existing artwork, public bundles, sprite keys, mips or identity semantics.

Candidate profile: `bytefables.artwork-generator-v2-candidate.v1`.
Remediation geometry: `bytefables.artwork-remediation-candidate.v2`.

## Scope

The candidate replaces geometry only for `mandala`, `heraldry` and `branching`.
`sigil`, `constellation`, `topography`, `crystal`, `cellular` and `orbital`
delegate byte-for-byte to the existing v1 renderer. The promotion benchmark
checks that unchanged-family contract explicitly across deterministic digests and
all selected native sizes.

Mandala and branching retain the successful candidate-v1 geometry. Heraldry is a
second iteration built around a logical 16x16 geometry grid: coarse shield-top
patterns, tip position, large side tabs, broad field divisions and a coarse emblem
carry identity-bearing bits that survive rasterisation at the minimum 16px size.
This specifically addresses candidate-v1's 16px p05 collapse.

## Frozen vectors

`tests/vectors/artwork-v2-candidate-v1.json` freezes RGBA SHA-256 and non-zero
alpha-pixel counts for selected digests, target families and native sizes. It also
contains delegated v1 vectors. A geometry/profile change therefore requires an
explicit vector/profile update rather than silently changing candidate pixels.

## Promotion benchmark

`benchmark-artwork-v2-promotion.py` compares three renderers using identical
style inputs:

1. production v1;
2. remediation candidate v1;
3. artwork-generator v2 candidate.

For every target family, native size and colour/greyscale/protan/deutan/tritan
screening mode, it records nearest-different-identity p01, p05 and median
statistics. It also counts exact RGBA duplicate groups and records candidate-v2
ratios against both production v1 and the previous remediation candidate.

The engineering manual-promotion gate requires each target family to have:

- small-icon median p05 ratio vs v1 >= 1.10;
- worst p05 ratio vs v1 >= 0.90;
- at least 75% of measured cases improve over v1;
- zero exact candidate-v2 duplicate groups;
- no increase in exact duplicates relative to v1;
- for heraldry, positive 16px p05 in every screening mode;
- all untouched families still byte-identical to v1.

A green gate means **eligible for manual promotion**, not automatically promoted.
It is machine screening, not accessibility certification or a human-recognition
study.

## Version/key boundary

This candidate is not wired into the existing transparent/alpha/KTX2 exporters.
If it is promoted later, that must be a separate versioned source/bundle change.
Changed source RGBA necessarily changes the current source-RGBA-derived sprite
key for the three modified families; existing v1 bundle keys must not be silently
rebound to different pixels. Migration/dual-version lookup therefore belongs to
the promotion milestone, not this candidate milestone.

## Current engineering evidence

The 128-identity development run used the same 16/32/64/128px and five-mode
screening matrix as the existing family experiments. The v2 candidate cleared the
promotion heuristic for all three target families. Heraldry candidate v2 removed
the remaining 16px exact duplicates and changed every 16px mode from p05=0 in the
previous candidate to a positive p05. Full evidence is produced by the workflow
artifact and should be reviewed before any production switch.
