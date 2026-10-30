# Artwork PNG export receipts v1

`createArtworkPngReceipt(atlasPlan, [{pageIndex,pngBytes}, ...])` independently
checks the PNG signature, bounded chunk layout, IHDR dimensions, page uniqueness,
and exact SHA-256 of each completed output file. It accepts pages in arbitrary
order and returns them in atlas order. The source bytes are PUBLIC only.

This is an **export provenance receipt**, not a PNG image validator or visual
quality certification. PNG CRC, zlib decompression, frame pixels, colour profiles,
actual use of the specified artwork layers and perceptual recognisability all
require independent post-render readback in FrameRudiments. No secrets, wallet
backups, or authenticity/ownership claims are supported. Do not publish a receipt
as evidence that the artwork faithfully represents the hash without that check.

The API adds no rendering engine or additional host dependency. Use FrameRudiments
to save actual PNG bytes, then pass the saved-file contents to the receipt API.
The output may be stored as JSON alongside the matching PNGs.
