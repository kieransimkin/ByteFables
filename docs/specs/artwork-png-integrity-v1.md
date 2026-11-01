# PNG integrity gate for public identity artwork

This additive ByteFables validator checks the exact exported PNG byte stream
from FrameRudiments. It validates every chunk CRC-32, chunk sizes, IHDR-first,
IEND-last, contiguous IDAT, required PLTE for indexed colour and rejects unknown
critical chunks. The previous `inspectArtworkPng` and exported atlas-receipt API
remain available, but now reject files with corrupt chunk CRCs.

This gate **does not decompress IDAT, reconstruct filtered pixels, check colour
profiles or measure visual identity accuracy**. PNG CRC-32 is accidental-damage
detection, not authentication. `sha256Hex` on the receipt binds exact exported
file bytes, but neither checksum certifies authorisation or provenance.

Next gate: FrameRudiments renders real PNG fixtures, an independent PNG decoder
reads exported pixels, and the visual benchmark measures recognition at
16/32/64/128 pixels across many distinct public identities.
