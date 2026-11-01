# Artwork family remediation experiments v1

Status: experimental A/B screening. **Production artwork generation is unchanged.**
This milestone takes the ranked family-remediation queue and tests versioned
candidate geometry for `mandala`, `heraldry` and `branching` against the existing
`ArtworkRenderer` using identical digest/style inputs.

Candidate profile: `bytefables.artwork-remediation-candidate.v1`.

## Candidate goals

- **Mandala:** replace fine repeated radial detail with 4–8 coarse lobes, a large
  seed-dependent central emblem and one asymmetric notch/badge. The goal is
  stronger 16/32 px silhouettes and less rotational aliasing.
- **Heraldry:** vary the shield silhouette and use large structural field divisions
  plus a seed-selected emblem instead of relying mainly on horizontal bands and
  hue. The goal is stronger greyscale/CVD separation.
- **Branching:** vary root/trunk placement, number of primary arms, branch length,
  asymmetry and terminal nodes. The goal is greater macro-structure spread between
  identities rather than nearly symmetric binary trees.

Families outside that set delegate byte-for-byte to the production renderer.
No candidate changes sprite keys, hashes, the production generator domain, or any
saved production bundle.

## A/B measurement

`benchmark-artwork-family-experiments.py` generates 16–256 deterministic public
experiment digests. For each selected family it chooses palette/complexity from
the digest and renders baseline and candidate at the requested native sizes.
The same colour, greyscale, protan, deutan and tritan screening features used by
the distinctiveness benchmark are then compared.

The report records baseline/candidate nearest-different-identity p01, p05 and
median distances and their ratios, plus exact duplicate groups. An engineering
`promising` flag requires all of:

- median small-icon p05 ratio >= 1.05;
- worst p05 ratio >= 0.85;
- at least 60% of measured cases improve;
- the candidate creates no more exact duplicate groups than baseline.

This heuristic only prioritises human review. It **never promotes a candidate into
production automatically** and is not accessibility or recognisability evidence.
A production change must be a separate versioned change followed by the complete
native bundle, mip, KTX2, Unity and distinctiveness qualification chain.

When a baseline percentile is exactly zero because multiple identities collapse to
the same screening feature while the candidate becomes non-zero, the machine
report uses `999.0` as an explicit finite "baseline-zero improvement" sentinel.
It must not be read as a literal 999x perceptual improvement; the accompanying
baseline/candidate percentile values and exact-duplicate counts are authoritative.
