# Public artwork sprite-atlas planning v1

Status: experimental, **identity-only**. No secret inputs, pixel renderer, recoverable binary data, or authentication claims.

`createFrameRudimentsArtworkAtlas(records, options)` accepts 1–1000 typed `PublicRecord` values and creates deterministic per-page `bytefables-artwork-v1` FrameRudiments layer descriptors. The page atlas is row-major, uses fixed tile dimensions and padding, and returns per-tile UV rectangles in a **top-left origin** texture convention. GPU clients using bottom-left coordinates must flip v explicitly. Each tile retains its full context-complete record digest, renderer ID and style metadata.

Default size is 64px tiles, 4px per-side padding, 16 columns and 16 rows per page. Up to 1000 records yield four pages. The final page height is cropped to populated rows; width remains fixed at configured columns. Page bounds must not exceed FrameRudiments' 7680px limit. Neither layout nor source hash is evidence of visual distinctiveness.

```js
const atlas = await createFrameRudimentsArtworkAtlas(publicRecords, {
  tileSize: 64, padding: 4, columns: 16, rowsPerPage: 16,
  artwork: 'crystal', palette: 'neon'
});
// For each page: send page.tiles.map(t => t.layer) to FrameRudiments.
// After rendering, attach the exported PNG's actual byte SHA-256 in the host receipt.
// UVs are for the exact page dimensions, not an assumed square texture.
```

The atlas is a **layout plan**, not a completed PNG, sprite sheet or independently measured performance result. Do not mark a page rendered until a FrameRudiments export is written and its dimensions, complete tile count, digest and actual image file checksum are verified. Native effects may alter pixels and must be included in the provenance receipt. Follow-up gates: native image export/readback, visual 16/32px confusion benchmarks, browser/Unity UV validation, color accessibility, performance with 1000 nodes and frozen cross-runtime vectors. Existing V1/V2 word formats and avatar seeds remain unmodified.
