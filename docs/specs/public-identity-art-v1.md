# FrameRudiments public identity artwork, v1

**Status:** experimental deterministic source generators, not cryptographic
identity proof, public-key archival, watermark, or recoverable byte encoding.

`createFrameRudimentsArtworkLayer(record, options)` derives the full
SHA-256 public-record digest (including namespace, kind, algorithm, network,
endian and payload bytes) and returns a `type: rudiment` layer with
`renderer: bytefables-artwork-v1`. Source generators are registered into an
**existing** FrameRudiments `RendererRegistry`, never into a second frame loop.

| Family | Source structure | Main display use |
| --- | --- | --- |
| `sigil` | Seeded radial arms, rings, coloured features | Compact recognisable emblems |
| `constellation` | Seeded node positions, nearest-neighbour links | Graph/agent identity |
| `heraldry` | Shields, bands and nested star geometry | Group/workspace heraldry |
| `topography` | Radial harmonic contours with layered level lines | Terrain/orb style thumbnails |
| `crystal` | Filled polygonal facets and light edges | High-contrast identity gem |
| `mandala` | Radially repeated geometry | Symmetric decorative marks |
| `cellular` | Bounded seeded Conway grid | Retro/game sprites |
| `branching` | Seeded binary fractal branching | Organic branching silhouette |
| `orbital` | Deterministic elliptical systems | Scientific/space identities |

`palette` is `neon`, `pastel` or `mono`; `complexity` is an integer 1..8.
All are source presentation choices. They do not modify the original public
identity and must appear in cache keys along with the immutable renderer
version and FrameRudiments/Pillow dependencies.

The generator derives its local deterministic seed as
`SHA256("ByteFables:framerudiments:artwork:v1\\0" || publicRecordDigest || UTF8(family))`.
It does not receive or inspect original private key material. Rendered outputs
are RGBA source pixels with no network/texture input, clock loop, denoising,
secret-capable backend or post-processing. FrameRudiments retains responsibility
for blending, temporal effects, recorded motion, QA, video and static exports.

```sh
node bin/bytefables.mjs artwork-layer --confirm-public \
  --public-hex 000102ff --namespace danceflow --kind node-id \
  --artwork constellation --palette pastel --complexity 6 \
  --id agent-avatar --bounds 0,0,128,128
```

The current CPU generators are intentionally small and have no claim of 256
bits of visual entropy or collision resistance. Human recognition must be
measured at 16/32px in large populations before preferring a family globally.
Visual similarity is not evidence of byte similarity; the full original
identifier remains the only authoritative lookup value.

Security: reject secret-labelled/unsupported inputs before handing off,
validate and bound every style property, freeze versioned deterministic seeds,
and treat host renderer factories as trusted executable Python modules. Export
and publish only user-approved public identity art. No model weights or remote
inference are required for these nine generators.
