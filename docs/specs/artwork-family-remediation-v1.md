# Artwork family remediation triage v1

Status: engineering screening, not accessibility certification and not a human
recognisability study. This layer consumes a completed
`bytefables.artwork-distinctiveness.v1` report and ranks artwork families for
follow-up without changing artwork, hashes, sprite keys or generator behaviour.

## Ranking

For every family / native size / screening mode, the tool compares that family's
nearest-different-identity p01, p05 and median distance with the corresponding
whole-corpus values. The three ratios are averaged into a relative screening
ratio. Lower values mean the family is unusually collision-prone *relative to the
current corpus* at that size/mode.

There is deliberately no universal pass threshold. The corpus is still small and
machine distances are not human recognition probabilities. The output is a work
queue, not a certification result.

The report records each family's worst and median relative ratios, its weakest
small-icon, colour, greyscale and CVD-screening ratios, and deterministic
recommendations based on the type of its weakest case. Typical actions include
stronger silhouettes at 16/32 px, more luminance/shape cues when greyscale is
weak, and more non-hue cues when CVD transforms expose collisions.

## Outputs

`family-triage.json` is the machine-readable record. `family-ranking.csv` is a
compact sortable view. `REMEDIATION.md` is a human-readable queue containing the
weakest size/mode and suggested next design action for every family.

The automatic family-triage workflow consumes the artifact from a successful
main-branch distinctiveness screening. Large-corpus reports can be passed through
the same script manually without changing the algorithm.
