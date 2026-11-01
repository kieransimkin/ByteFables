# Artwork PNG export receipts v1

`createArtworkPngReceipt(atlasPlan, [{pageIndex,pngBytes}, ...])` independently
checks the PNG signature, bounded chunk layout, every chunk CRC-32, critical
chunk ordering, IHDR dimensions, page uniqueness, and exact SHA-256 of each
completed output file. It accepts pages in arbitrary
order and returns them in atlas order. The source bytes are PUBLIC only.

This is an **export provenance receipt**, not a PNG image validator or visual
quality certification. CRC checks are implemented. Zlib decompression and decoded
pixel checks are available in [atlas readback](artwork-atlas-readback-v1.md).
The [native benchmark](artwork-native-benchmark-v1.md) adds actual FrameRudiments
composition, saved-file readback and source-on-matte comparisons. Colour-profile
qualification and human recognisability studies remain separate gates. No secrets, wallet
backups, or authenticity/ownership claims are supported. Do not publish a receipt
as evidence that the artwork faithfully represents the hash without that check.

The API adds no rendering engine or additional host dependency. Use FrameRudiments
to save actual PNG bytes, then pass the saved-file contents to the receipt API.
The output may be stored as JSON alongside the matching PNGs.
