# Public artwork gallery v1

**Status:** image-output contact-sheet planner for experimental deterministic FrameRudiments artwork. Not a reversible encoding, wallet backup, or authentication mechanism.

`createFrameRudimentsArtworkGallery(record, options)` plans 27 default variants (nine existing artwork families × three palettes), producing validated `bytefables-artwork-v1` native layer descriptors. No image rasterisation, colour conversion, SVG handling, model inference, or postprocessing occurs in ByteFables. The FrameRudiments host remains responsible for these operations, source image outputs, effects, and file exports.

The planner freezes style ordering as `sigil, constellation, heraldry, topography, crystal, mandala, cellular, branching, orbital`; palettes are `neon, pastel, mono`, with family as the outer loop. Each tile's position uses row-major layout, 128-pixel squares, 16-pixel gaps, and six columns by default. The resulting plan is 848 × 704 pixels with 27 tiles. The plan is versioned `bytefables.artwork-gallery.v1`.

Inputs are a validated typed `PublicRecord`, optional unique subsets of families and palettes, a safe layer-ID prefix, integer square sizes 16–1024, gaps 0–256, columns 1–27 and complexity 1–8. Reject any layout extending past the native bridge's 7680-pixel coordinate limit. Include the full domain-separated public-record digest in the plan; never derive artwork from private keys or log raw secret bytes.

```js
const plan = await createFrameRudimentsArtworkGallery(record, {
  columns: 6, tileSize: 128, gap: 16, complexity: 4
});
// Use plan.tiles.map(tile => tile.layer) as the native FrameRudiments layers.
// Render/export through FrameRudiments, not ByteFables.
```

Acceptance already covered by unit tests: deterministic ordering and layout, bounded geometry, immutability, public-record context separation and secret-input rejection. **Not yet evidenced:** actual FrameRudiments end-to-end render, screenshot/contact-sheet artefact, 16/32-pixel human discrimination tests, colour accessibility, 1,000-node graph performance or host-specific export reproducibility. Those remain the next image release gates.
