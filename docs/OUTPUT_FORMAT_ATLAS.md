# ByteFables output-format atlas

**Document:** BF-ATLAS-001
**Status:** research-backed candidate catalogue; **not** an implemented-capability list
**Survey date:** 2026-10-25
**Companion documents:** [pipeline](OUTPUT_PIPELINE.md), [research](RESEARCH_SURVEY_2026-10.md), [roadmap](IMPLEMENTATION_PLAN.md), [security](../SECURITY.md)

## Why this is a taxonomy, not a closed list

It is impossible to enumerate *every possible* depiction or physical medium for bits: any deterministic transform can define a new display. Instead, maintain an **open, testable format registry** covering mature interoperable formats, worthwhile adapters, experimental generative systems, and future transports. Distinguish six independent layers:

1. **Source and purpose**: exact typed public bytes, secret recovery material, pre-existing digest, address, or canonical object. Cryptographic hashes cannot reconstruct their preimages.
2. **Logical encoding**: hex, words, mnemonic-story codewords, structured wallet metadata, CBOR, etc. Lossless only when complete bytes and required context are recoverable.
3. **Protection/framing**: domain/type/length/version, checksum, authentication, cryptographic encryption, error correction, share splitting, and redundancy (distinct operations).
4. **Symbol/representation**: printed characters, QR cells, Data Matrix modules, Braille dots, audible symbols, avatar paths, 3D geometry, time-varying imagery.
5. **Rendering/export**: SVG/PNG/PDF/WAV/glTF/G-code/animation/sprite atlas, including fonts, layout, colours and resolution.
6. **Carrier/medium**: screen, network message, printer, plate, photographic film, NFC, offline file, audio channel, tangible object.

A renderer is **not inherently reversible** merely because its input was a hash or its output is a QR-looking image. A file may hold both a machine-readable recovery payload and a non-reversible decorative avatar. Each must advertise its own capability.

**Status legend:** `F` = implemented foundation; `E` = existing ByteFables prototype; `S` = published standard or interoperable third-party precedent to integrate; `R` = researched precedent without stable ByteFables adapter; `X` = new speculative experiment. None of S/R/X implies supported in ByteFables. All secret uses are blocked until Stage 7 qualification.

## A. Exact text and symbolic encodings (lossless at the specified layer)

| ID / family | Candidate forms | Known status | Practical notes |
|---|---|---|---|
| `text/hex` | Hexadecimal, grouped/line-numbered hex dump | F | Exact binary; add error flags per line |
| `text/base32-rfc4648` | Standard padded and unpadded Base32 | F (unpadded) | Must validate noncanonical trailing bits |
| `text/base64` | RFC 4648 Base64 / Base64url | S | Compact but vulnerable to transcription errors; strict canonical decoding |
| `text/base32-crockford` | Case-tolerant human Base32, optional check symbol | S | Different rules from RFC Base32 |
| `text/base45` | QR-alphanumeric-optimised Base45 | S | RFC 9285, do not double-encode blindly |
| `text/base58check` | Bitcoin-style Base58Check, WIF and other **typed** payloads | S | Checksum plus version prefix; don't conflate addresses and keys |
| `text/bech32` | HRP/checksummed Bech32 and Bech32m | S | Version and witness type strict; do not make generic addresses by accident |
| `text/base36-base62-base85` | Alternate radices, ASCII85, Z85 | R | Audit alphabet, encoding canonicality and available readers |
| `text/base91` | High-density printable character stream | R | Niche, poor hand transcription; optional |
| `text/base10-octal-binary` | Decimal words/digits, octal, raw bits, grouped bitfield | R | Excellent teaching and self-decoding fallback, verbose |
| `text/multibase` | Self-describing multibase prefixes | S/R | Preserve multicodec semantics, do not equate with content identity |
| `text/bytewords` | Normal, URI and minimal forms | S | Blockchain Commons 256-entry dictionary + CRC32; test all styles |
| `text/rfc1751` | 12 six-character-ish English words for 128-bit blocks | S | Legacy human-readable cryptographic encoding |
| `text/rfc2289` | Six-word OTP form | S | Legacy OTP only; not modern wallet backup |
| `text/emoji-lexicon` | Explicit frozen pictographic codebook | X | Only reversible if platform-independent canonical token IDs and parser exist |
| `text/braille-binary` | Uncontracted embossed 8-dot symbols | X | 256 patterns per cell, but define orientation, byte order and tactile discrimination |
| `text/phonetic` | NATO spelling, spoken digits, checksummed codewords | R/X | Speech fallback with robust homophone study |
| `text/dice-notation` | Dice rolls, card suits, tile distributions | X | For manual transcription only; separate from secure RNG/key generation |
| `text/letter-grid` | Coordinate grids, word-search maps, hexagonal letter tiles | X | Formal decoder required, including orientation and row indexing |
| `text/poetic` | Haiku, verse, lyrics with typed dictionaries | X | Story engine extension; no unreviewed LLM decoding |
| `text/grammars` | Temporal-trait, action, place, dialogue, science, fantasy, music | E/X | Current prototype = 13 bits/sentence, future 33+ and variable length |

### Exact-text requirements

- Every adapter identifies the alphabet, version, canonical casing, padding, delimiter, length and allowed character repertoire.
- If an output is spoken or handwritten, include word numbering, chunk IDs, checksums and a checksum-independent representation for recovery.
- Alternate spelling, translation, formatting, line reflow and punctuation cannot change a sealed decoder's result without an explicit, versioned normalization rule.
- Grammar/template variety must preserve injectivity and account for selector bits, frame, checksum and zero padding. LLM-authored free text is a *proposal of codebook content*, never a runtime cryptographic codec.

## B. Mnemonics, wallet/key encodings and structured archives

| ID / family | Intended content | Precedent | Crucial boundary |
|---|---|---|---|
| `wallet/bip39` | 128–256 bits entropy, checksum; separate seed derivation | BIP-39 | 24 words ≠ arbitrary 512-bit payload |
| `wallet/slip39` | Master secret in threshold/group mnemonic shares | SLIP-39 | Share provenance, group/member thresholds and extension versions |
| `wallet/formosa` | Theme-bound BIP-39 word-index representation | BIP-450 draft | Pin accepted themes/versions and verify exact wallet compatibility |
| `wallet/codex32` | Checksummed BIP32 seed/share notation with BCH | BIP-93 draft | Snapshot exact proposal revision; validate stated correction bounds |
| `wallet/seedqr` | Fixed-width BIP-39 index digits | SeedSigner | Exact 12/24 word and numeric framing support |
| `wallet/compact-seedqr` | Compact BIP-39 entropy QR | SeedSigner | Requires specific entropy size and index/raster rules |
| `wallet/electrum` | Electrum-specific versioned wallet mnemonic | Electrum | Not interchangeable with BIP-39 |
| `wallet/monero` | Monero seed/checksum mnemonic variants | Monero | Network-specific derivation and wallet height/context |
| `wallet/algorand` | 25-word account mnemonic | Algorand SDK | Network-specific checksumming, 256-bit key material |
| `wallet/nostr-nip19` | `npub`, `nsec`, `nprofile` etc. | NIP-19 | Public/secret type absolutely distinct |
| `wallet/wif` | Bitcoin wallet import key, Base58Check | Bitcoin | Compression flag and network must be preserved |
| `wallet/bip38` | Passphrase-protected private key record | BIP-38 | Existing format compatibility, no invented encryption |
| `wallet/bip32` | Extended keys with chain code, derivation metadata | BIP-32 | xprv/xpub and network prefixes remain distinct |
| `wallet/bip85` | Derived entropy from BIP-32 root | BIP-85 | Derivation action, NOT re-encoding the same bits |
| `wallet/descriptors` | Addresses, scripts, derivation and multisig metadata | BIP-380/388 | Seed alone may not restore wallet |
| `wallet/psbt` | Partially signed Bitcoin transactions | BIP-174 etc. | Often large; transport via UR/BBQr, not backup mnemonic |
| `wallet/ethereum-v3` | Encrypted JSON keystore | Web3 Secret Storage v3 | Encrypted container; password/security policy critical |
| `wallet/erc2335` | Validator BLS keystore and key path | ERC-2335 | Not interchangeable with Ethereum account keystores |
| `crypto/openpgp` | Armoured encrypted/transferable keys | RFC 9580 | Modern AEAD profile, separate public/private packets |
| `crypto/pem-der-jwk-cose` | Algorithm-specific key containers | RFCs / ecosystem | Keep algorithm, curve, key usages and private components explicit |
| `crypto/ssh` | OpenSSH public/private and fingerprints | OpenSSH | Formatting != certificate or ownership proof |
| `archive/bytefables-cbor` | Type-length-version record, SHA-256 commitment, optional ECC | **proposed** | Draft CDDL & canonical CBOR in separate specification |
| `archive/ur` | `ur:` typed CBOR single/multi-part frames | Blockchain Commons | Fountains and type registry; usable beyond wallets |
| `archive/encrypted` | Reviewed AEAD-wrapped archive | Proposed gated adapter | Never homebrew crypto or passphrase KDF |
| `archive/shares` | SSKR, SLIP-39, codex32 modes, other vetted SSS | Precedent | Shamir is not media ECC; no share-to-avatar leakage |

Formats should support `inspect`, `validate`, `encode`, `decode` only where their upstream standard makes sense. ByteFables must not claim that it can regenerate an original BIP-39 mnemonic from an arbitrary BIP-32 root or reverse a digest.

## C. Optically recoverable symbols and paper codes

| Symbology | Intended use | Evidence | Priority / caution |
|---|---|---|---|
| QR Code Model 2 | Universal static printed/scanned encoding | ISO/IEC 18004:2024 | **P0**; ECC L/M/Q/H, mask, modules, quiet zone |
| Micro QR | Smaller limited-capacity QR | ISO/IEC 18004:2024 | P2; very small payload only |
| rMQR | Rectangular Micro QR | ISO/IEC 23941:2022 | P2; narrow labels |
| Data Matrix ECC200 | Durable DPM, small labels and engraving | ISO/IEC 16022:2024 | **P1**; scanner-readback tests |
| Aztec Code | Compact symbol, low-margin displays | ISO/IEC 24778:2024 | **P1**; configurable error protection |
| PDF417 / Macro PDF417 | Larger paper documents / stacked codes | ISO/IEC 15438 | P1/P2; fragmented documentation |
| MaxiCode | Fixed-form industrial/parcel code | ISO/IEC 16023 | P3; specialised payload rules |
| Han Xin Code | Chinese/binary-capable QR-family code | ISO/IEC 20830:2021 | P3; specialised readers |
| DotCode | Dot-based high-speed marking | AIM ISS DotCode Rev. 2019 (not ISO/IEC) | P3; assess correct standard/version |
| JAB Code | Polychrome, colour-capacity 2D code | ISO/IEC 23634:2022 | P3; print colour calibration required |
| Ultracode | Polychrome symbology, ISO work in progress | ISO/IEC CD 25449 | P4; **not** mark as published international standard |
| Code 128 | General 1D code for short strings | ISO/IEC 15417 | P2; split records into separately framed strips |
| Code 39 / Code 93 | Industrial ASCII-ish 1D alternatives | ISO/IEC 16388 et al. | P3; size/character limits |
| EAN/UPC / ITF | Retail and logistics numbering | GS1/ISO | **Not** general binary containers; reject arbitrary raw key use |
| Legacy colour HCCB | Historical research for dense colour marks | Microsoft Research | P4; compatibility unlikely |
| DataGlyphs / OPTAR | Dot/line microtextures for paper file backup | PARC / OPTAR | P3 experimental, independent scanned byte recovery |
| AprilTag / ArUco | Pose-estimation fiducials, finite IDs | Vision research | Identity marker/AR target, **not** arbitrary lossless bytes |
| Bokode | Micro-optical focal-plane code with lens | MIT Media Lab | P4 research, specialist optics |
| Polar/circular custom glyph | Radial binary sectors/ticks | Proposed | P4 research, must specify scanner/decoder, not QR-compatible |
| Video QR sequence | Ordered frames / packet indexing | Existing wallets | P1; frames lost/reordered/resumed |
| UR fountain QR | Rateless-ish multipart CBOR transport | Blockchain Commons | **P0/P1**; fragment reassembly and bounded memory |
| BBQr / PSBT optical variants | Multipart Bitcoin-specific QR | Bitcoin wallet ecosystem | P2; record exact wallet interoperability |

**Print validity:** Distinguish optical symbology ECC from an outer record checksum. Do not decorate finder/timing modules, clip margins, round data modules, blur or resample a code unless *independent* scanner compatibility tests demonstrate the intended result. ISO/IEC 15415 provides 2D symbol quality testing concepts. A logo in a QR consumes unknown recovery budget; it is never a free enhancement.

## D. Structured layouts and physical display surfaces

- Printable human backup: A4/A5/A6 cards, banknote size, foldable booklet, page-numbered poster, stickers, perforated tickets, wallet insert, label rolls; multiple font/contrast modes; public and secret templates must be different.
- Dual representation: primary 2D code + letter/word fallback + human-readable descriptor + checksum + specimen/example decoder instructions; duplicate recovery information on separate surfaces if policy permits.
- Archival 2D files: vector SVG/SVGZ, EPS, PDF, PDF/A, PostScript, HPGL/PLT, DXF; print grid without relying on a custom web font.
- Raster: PNG and TIFF lossless for machine recovery, BMP/PGM/PBM when bitwise simplicity matters; WebP lossless optional. JPEG/AVIF and lossy WebP for **public art only** unless full post-export barcode readback is proven per target profile.
- 3D physical marking: laser/fibre engraving, dot peen, embossed relief, CNC pocketing, stamping dies, etched metal, ceramic tablets, glass engraving, electrochemical marking, 3D printed plates; CAM exports DXF, SVG, G-code; 3MF/STL/STEP only where validated by manufacturer pipeline.
- Alternative physical channels: Braille embossing, raised tactile dot matrices, manually punched cards/tapes, punched metal, woven/stitched grids, photomicrograph or microfilm; these require separately defined scanner/manual decoders and tolerances.
- Optical/special media research: monochrome microdots, laser-scribed glass, birefringent multilayer optics, retroreflective fiducials, infrared-visible inks/markings, lenticular multi-frame materials. These are not default wallet storage or durable-media claims.
- Storage devices: plain binary file, encrypted removable flash, optical disc, NFC NDEF tag, RFID/EEPROM/smartcard, specialist offline devices; software output does **not** guarantee carrier longevity or confidentiality.
- **Explicitly exclude** unverified steganography, AI-generated pictures containing hidden supposed secrets, watermark-only key backups and ad-hoc secret-bearing token art from recommended recovery methods. Their decoder longevity and corruption tolerance are unknown.

### Output file/container catalogue

| Media class | Candidate artifact types | True purpose |
|---|---|---|
| Source | `.bin`, `.hex`, `.txt`, `.json`, `.cbor`, `.yaml`, `.ur`, `.pem`, `.asc` | Exact records or interoperable cryptographic formats |
| Portable print | `.pdf`, `.svg`, `.eps`, `.ps`, `.tiff`, `.png`, `.pbm`, `.pgm` | Fixed high-contrast optical, vector/greyscale templates |
| Web/public art | `.svg`, `.png`, `.webp`, `.avif`, `.jpeg`, `.ico` | Avatars, favicons, profile/social previews |
| Animation | `.gif`, `.apng`, `.webp` animated, `.webm`, `.mp4`, animated SVG, Lottie JSON, Rive | Moving aliases, optical sequences only in separately specified lossless mode |
| GPU/texture | PNG atlases + JSON, KTX2, DDS, EXR, cubemaps, GLSL/WGSL profiles | High-throughput public sprites and material generation |
| Three-dimensional | `.glb`, `.gltf`, `.usdz`, `.obj`, `.stl`, `.3mf`, `.ply`, `.step` | Public generated sculpture or fabricated code geometry |
| Fabrication | `.dxf`, `.svg`, `.gcode`, `.hpgl`, `.plt`, `.gerber` | Production instructions with safety/manual inspection; not universal |
| Audio | `.wav`, `.flac`, `.ogg`, `.mp3`, `.opus`, `.mid`, scripted TTS text | Spoken identity, musical motif, transport modem when explicitly decodable |
| Haptics/accessibility | Text transcript, VTT/SRT, SSML, Braille BRF, structured vibration sequence | Accessible identification and specialist binary recovery |
| Device transport | NDEF, APDU/ISO7816, data-over-sound packet stream, optical frames | Temporary local transfer; not permanent storage by itself |
| Bundles | ZIP/TAR, BagIt-like manifest, structured backup set | Contents + independent specs/decoder/vectors, not security by itself |

A fixed output file type is a **renderer/exporter**, not proof that the embedded information is lossless. E.g. an identicon PNG is irreversible even though PNG itself is a lossless *image* codec.

## E. Identity-only visual systems (non-reversible unless separately specified)

### E1. Proven visual-language patterns

- 5x5/7x7/9x9 mirrored mosaic identicons (GitHub); Ethereum Blockies/Jazzicon; Jdenticon polygon symmetry; deterministic SVG compositors such as DiceBear; Robohash assembled robots; OpenSSH Randomart; LifeHash `version2`, `detailed`, `fiducial`, `grayscaleFiducial`; Blockchain Commons Object Identity Block.
- Hash-colour/palette, multi-colour swatches, outline/pattern stripes, simple monogram initials, emoji safety-number motifs and human-readable short-check words. Do not equate colour, one emoji or few words with a complete cryptographic fingerprint.
- For every independent implementation, pin version, licence, exact seed/hashing semantics and reference vectors. Do not call an inspired look an exact compatible implementation.

### E2. New procedural 2D identity families

1. **Geometry:** tiled polygons, Voronoi/Delaunay cells, squircle grids, Penrose-like tilings, hexagonal motifs, sacred geometry, kaleidoscope, rotational/reflection symmetries, bilateral/radial patterns, line art, generative calligraphy.
2. **Natural forms:** L-systems/tree silhouettes, leaf venation, animal coats, fingerprints/topographic contour fields, river networks, coastlines, coral growth, crystallisation, snowflakes, nebulae, galaxy/constellation layouts, insect-wing patterns.
3. **Math & dynamics:** cellular automata (Game of Life and beyond), reaction-diffusion, strange attractors, fractals, iterated function systems, Fourier interference, harmonographs, spirographs, wave-function fields, metaballs, particle trails, Penrose/aperiodic tiling themes.
4. **Characters:** deterministic animals, robots, masks, monsters, friendly spirits, folklore creatures, anthropomorphic tools, heraldic beasts, pixel-art faces, paper-cut silhouettes, modular clothing/accessories, biome-based creatures.
5. **Emblems:** shields/crests, heraldry, seals, runes, sigils, stained glass, medallions, tokens, patches, banners, flags, stamp marks, badges (visual art only), knots, mandalas, typographic monograms.
6. **Scenes:** biome/landscape postcards, miniature planets, city skylines, weather, cloud silhouettes, orbital diagrams, isometric rooms, laboratory scenes, machinery, fantasy landscapes and abstract albums/artworks.
7. **Typography:** colourful wordmarks, shaped name plates, responsive calligrams, deterministically chosen type/kerning (pin fonts), text-orbit arrangements, short alias-based logos. Ensure source bytes never leave process to an AI/font service.

### E3. Motion, 3D, spatial and immersive identity

- Animated SVG, CSS, Canvas2D, WebGL/WebGPU, particle fields, shader materials, fluid/reaction simulations, procedural animation loops, spritesheets and skeletal rigs.
- 3D objects: polyhedra/sigils, crystalline avatars, orbital systems, volumetric lattices, knot sculpture, relief stamps, height maps, normal/displacement fields, terrain, mesh glyphs, voxel figures, point clouds, layered hologram-looking graphics (display illusion, not true holographic archive).
- AR markers, spatially tracked ornaments, volumetric previews, interactive orb identity, WebXR scene placement, Unity-compatible GLB/texture atlases.
- Motion must be pinned to a deterministic timeline and simulation/renderer version if exact repeatability is promised. Artistic shader drift is tolerable for identity *style*, not for a bit-exact recovery symbol.

### E4. Auditory, rhythmic, tactile and inclusive identities

- Deterministic musical motifs/earcons, scales/chords, timbral textures, rhythmic phrases, percussion signatures, named-entity TTS, spoken mnemonic, tone sequences, MIDI.
- Accessibility: high-contrast patterns, alt text with complete canonical ID on demand, colour-vision-safe palettes, reduced-motion static fallbacks, tactile silhouettes and braille identity cards.
- Data-over-sound **transport** is separate from musical identity. A tune cannot recreate secret bytes unless a documented error-controlled modulation and demodulation codec exists.
- Haptic/LED vibrations, Morse flashes, watch patterns, Braille displays and tactile buttons: useful identity cues; bit-exact transfer requires its own timing and error-correction protocol.

### E5. Persona and family identity themes

- Node kinds and namespaces may choose a family frame, motif, glyph or palette, but the underlying node ID remains globally stable within its namespace.
- Provide *identity facets*: `default`, `compact`, `profile`, `card`, `orb`, `badge`, `full-bleed`, `animation`, `monochrome`, `print`, `high-contrast`, `tactile`.
- Maintain `identityDigest` and a scoped `styleSeed` separately from manual overrides. Overrides (an uploaded sprite or selected palette) must not rewrite the canonical identity.
- Mixed workloads: 16px favicon/graph dots, 32/64/128/256px avatars, 512/1024px cards, 4K illustrations, sprite atlases, GLSL textures, animated thumbnails, WebGL floating node panels and physical token previews.

## F. Input-size and use-case routing

| Input/purpose | First-choice outputs | Alternate/fallback | Never assume |
|---|---|---|---|
| 16–32 bytes public identifier | SVG avatar + full hex/Base32 + QR | Identity card; ASCII art; printed short code | The avatar uniquely identifies the bytes |
| 20/32-byte blockchain public hash | Network-native address codec, typed QR | Bech32/Base58Check only when protocol permits | The address alone is a private key |
| 32-byte public digest for archive | Hex/Base32 + CRC/SHA-256 envelope + QR | Bytewords and story; dual-channel print | A digest reveals its preimage |
| 32-byte private entropy (FUTURE) | Exact source wallet mnemonic + verifiable offline backup | SeedQR/SLIP-39 when compatible and independently qualified | BIP-39 re-encoding of a different seed is equivalent |
| 64–96-byte public key/signature | Exact binary record + QR/Data Matrix | Base45, framed chunks, PDF | 32-byte algorithms apply to it |
| 78-byte extended key | Wallet-native xpub/xprv and metadata | QR/UR, type-specific mnemonic | All extended keys are public |
| ~1–4 KiB objects | UR v2 fountain or multi-page QR + full-length commitment | PDF417, block-coded optical grids | One tiny QR can scan reliably |
| >4 KiB / post-quantum blobs | Binary/CBOR archive + chunking + index + resilient FEC | Files, USB, printed strip/multipage backup | Mnemonics scale economically |
| Public graph node | Stable 32px SVG/PNG + cached large assets | LOD spritesheet, KTX2, GLB | Rendered visual similarity implies hash similarity |
| Secret transfer (FUTURE) | Offline reviewed protocol with allowlisted device | Typed opt-in QR/secure transport | General browser/printer/NFC APIs are secret-safe |

## G. Scope decisions

- **Integrate first:** plain text/Bytewords, QR, SeedQR *compatibility research*, SVG/PNG/PDF public outputs, favicon and atlas generation, 33-bit story codec, LifeHash and grouped avatar styles.
- **Add once foundation is measured:** Data Matrix/Aztec/PDF417, animated UR, metal and print templates, NFC NDEF, PBR/3D outputs, acoustic public transfer.
- **Experimental lab:** JAB/Ultracode, OPTAR, Bokode, 3D shadow codes, spectral/holographic/IR data marks, Braille byte grids, novelty word grammars and story-driven sound identities.
- **Never silently offer:** proprietary/unsupported key conversion, unverified secret-bearing art, weak checksum described as authentication, remote image/QR APIs for private material, lossy compression as a guaranteed binary backup.

The long tail is valuable for discovery. Each new technique must have a `reference`, `licence`, `decode path`, `fidelity contract`, `threat note` and `test fixture` before being promoted out of research status.
