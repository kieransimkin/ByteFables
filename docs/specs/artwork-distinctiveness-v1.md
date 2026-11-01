# Artwork distinctiveness screening v1

Status: experimental screening benchmark, not a human-study result and not an
accessibility certification. The goal is to identify likely visual collisions
among PUBLIC ByteFables identity images before expanding the catalogue.

## Input and scope

Input is a verified `bytefables.transparent-artwork-bundle.v1`. Only saved PNG
pixels are analysed; no artwork is generated or modified by the analyser. The
benchmark can run at 16, 32, 64 and 128 px and keeps results grouped by family as
well as across the whole corpus.

Pairs with the same digest are excluded from the primary different-identity
nearest-neighbour statistic. They are still reported separately as style variants.
This matters because the current public corpus can contain one identity rendered
through several visual families.

## Screening transforms

For each image the analyser creates alpha-composited representations on black,
50% grey and white backgrounds. It reports:

- colour mean-absolute distance on a deterministic 4x4 area-pooled observation grid;
- greyscale distance;
- 64-bit difference-hash Hamming distance;
- exact-pixel duplicate groups;
- three simple colour-vision-deficiency screening transforms (protan/deutan/
  tritan approximations).

The colour-vision transforms are deterministic machine screening transforms only.
They are not a substitute for testing with people who have colour-vision
deficiencies, nor do they model every severity/display/vision condition.

The compact observation grid bounds the pairwise screening workload for large corpora; exact-pixel duplicate detection and dHash still use the full native saved image.

For each size/mode the report records the closest different-digest pairs, minimum,
1st/5th percentile and median nearest-neighbour distance, exact duplicates and
hash collisions, plus within-family nearest-neighbour distributions. A PNG contact sheet shows the closest pairs at the selected
preview size.

No universal pass threshold is hard-coded in v1. Distance distributions are
measurement evidence; a later corpus-scale study can set/version thresholds after
observing real output rather than choosing arbitrary cut-offs in advance.

## CI

The automatic workflow analyses the transparent artifact from each successful
main native benchmark. A separate manual large-corpus workflow can generate
64/128/256 unique public digests and run the same analyser. Large-corpus runs are
explicit because native rendering cost grows with identity count.
