# ByteFables research survey: binary representations, human identity and physical preservation

**Document:** BF-RESEARCH-2026-10
**Surveyed:** 2026-10-25
**Status:** externally researched, not an implementation or certification claim
**Companions:** [format atlas](OUTPUT_FORMAT_ATLAS.md), [pipeline](OUTPUT_PIPELINE.md), [implementation plan](IMPLEMENTATION_PLAN.md), [security](../SECURITY.md)

## 1. Method, scope, provenance and limits

Sources prioritise public normative standards, official implementers and original academic work, with secondary summaries only for discovery. This survey records **what has been specified or demonstrated**, the use case it supports, and where ByteFables needs independent conformance evidence. We did not license/purchase paywalled ISO standards, acquire hardware, inspect raw specimen paper archives, scan generated optical codes, or complete wallet restores. Public abstracts do not substantiate the full behaviour of a proprietary implementation. No planned capability is presented as working.

**Do not interpret "every possible format" literally.** The theoretical space is unbounded: any deterministic bitmap, waveform, movement, texture or physical pattern might depict a value. A useful answer is an open, extensible taxonomy, an intentionally broad candidate list and measurable graduation gates. Adopt new output plugins without expanding the core cryptographic protocol.

Evidence levels: **STD** = published normative specification; **PROPOSAL** = evolving draft; **OPEN** = implementation and published algorithm; **RESEARCH** = reported paper/prototype; **INVENT** = ByteFables experiment to design. Some standards are formal yet have little scanner availability; interoperability must be measured separately.

## 2. Grounded precedent catalogue

### 2.1 Recovery words, text, typed cryptographic records

| Reference | What has been done | Status and ByteFables lesson |
|---|---|---|
| [BIP-39](https://github.com/bitcoin/bips/blob/master/bip-0039.mediawiki) | Entropy plus SHA-256 checksum mapped through 2048-word lists; PBKDF2 separate | Bitcoin ecosystem standard practice. A mnemonic does **not** preserve an arbitrary 512-bit seed. |
| [BIP-32](https://github.com/bitcoin/bips/blob/master/bip-0032.mediawiki), [BIP-380](https://github.com/bitcoin/bips/blob/master/bip-0380.mediawiki), [BIP-388](https://github.com/bitcoin/bips/blob/master/bip-0388.mediawiki) | HD keys and script/policy metadata | Wallet recovery must capture derivation and multisig details; do not mistake seed-only backups for complete recovery. |
| [SLIP-39](https://github.com/satoshilabs/slips/blob/master/slip-0039.md) | Grouped threshold-sharing mnemonics with RS1024 checksum | Share threshold, identifier and passphrase variants are format-bound, not generic interchangeable words. |
| [BIP-93 codex32](https://github.com/bitcoin/bips/blob/master/bip-0093.mediawiki) | Error-correcting checksummed BIP32 seed/share text, designed for manual operations | **Draft** as checked in Oct 2026; formal correction guarantees and human recovery deserve independent verification. |
| [BIP-450 Formosa](https://github.com/bitcoin/bips/blob/master/bip-0450.mediawiki) | 33-bit, grammar-typed mnemonic sentences with `LED_BY` conditional dictionaries | **Draft**, assigned May 2026. Best direct precedent for themed semantic sentence blocks; interoperability is an adapter, not assumed. |
| [Blockchain Commons Bytewords](https://github.com/BlockchainCommons/Research/blob/master/papers/bcr-2020-012-bytewords.md) | 256 indexed words + CRC32 normal/URI/minimal representations | Efficient human transcription for structured binary. Its research documentation is not a universal ISO-type standard. |
| [UR v2](https://github.com/BlockchainCommons/Research/blob/master/papers/bcr-2020-005-ur.md) | Typed CBOR object and fountain-style multi-frame QR transport | Decouple logical record from QR symbol. Version CBOR type and bound fragment/resource costs. |
| [RFC 4648](https://www.rfc-editor.org/rfc/rfc4648.html), [RFC 9285](https://www.rfc-editor.org/rfc/rfc9285.html) | Common Base16/32/64 alphabets; Base45 optimised for QR alphanumeric mode | Require strict canonical decoding; Base45 is not automatically optimal outside QR. |
| [BIP-173](https://github.com/bitcoin/bips/blob/master/bip-0173.mediawiki), [BIP-350](https://github.com/bitcoin/bips/blob/master/bip-0350.mediawiki) | Bech32/Bech32m checksummed address encodings | Preserve HRP, witness version and address type; don't call arbitrary Base32 a Bitcoin address. |
| [RFC 1751](https://www.rfc-editor.org/rfc/rfc1751.html), [RFC 2289](https://www.rfc-editor.org/rfc/rfc2289.html) | Legacy English-word key and one-time password encodings | Useful historical human-factor baseline, not new wallet standards. |
| [Monero mnemonic docs](https://docs.getmonero.org/mnemonics/legacy/), [Electrum](https://electrum.org/) | Chain- and wallet-specific seed conventions | Never silently translate between mnemonics with different derivation/restore assumptions. |
| [BIP-85](https://github.com/bitcoin/bips/blob/master/bip-0085.mediawiki) | Deterministic child entropy **derivation** | Derivation is not reversible reformatting of arbitrary bytes; separate API/category. |
| [BIP-38](https://github.com/bitcoin/bips/blob/master/bip-0038.mediawiki), [Ethereum Web3 Secret Storage](https://ethereum.org/en/developers/docs/data-structures-and-encoding/web3-secret-storage/), [ERC-2335](https://eips.ethereum.org/EIPS/eip-2335) | Existing encrypted private-key formats | Compatibility adapters only after reviewed KDF/passphrase/metadata conformance. |
| [RFC 9580 OpenPGP](https://www.rfc-editor.org/rfc/rfc9580.html), [RFC 8949 CBOR](https://www.rfc-editor.org/rfc/rfc8949.html), [RFC 8610 CDDL](https://www.rfc-editor.org/rfc/rfc8610.html) | Key containers, typed binary interchange and schema description | Strong foundation for self-describing ByteFables public archives and formally specified schema; secret record needs separate gate. |

### 2.2 Optical matrix, barcodes, damage correction and industrial symbols

| Reference | What has been done | Status and ByteFables lesson |
|---|---|---|
| [ISO/IEC 18004:2024 QR](https://webstore.iec.ch/en/publication/99495), [DENSO WAVE ECC guide](https://www.qrcode.com/en/about/error_correction.html) | QR matrix with standard error-correction grades, including Micro QR variants | P0: multiple independent decoders, accurate quiet zone and module pitch. ECC codeword recovery percentages do not equal arbitrary physical surface-damage guarantees. |
| [ISO/IEC 23941 rMQR](https://www.iso.org/standard/77404.html) | Rectangular compact QR | Narrow labels; decoder population smaller than ordinary QR. |
| [ISO/IEC 16022:2024 Data Matrix](https://www.iso.org/standard/80926.html) | ECC200 and robust industrial direct part marking | Prefer flat monochrome module matrix layer; measure engraved/embossed optics. |
| [ISO/IEC 24778 Aztec](https://www.iso.org/standard/82441.html) | Dense 2D marks without an ordinary QR-style quiet zone | Strong second compact optical format; scanner availability varies. |
| [ISO/IEC 15438 PDF417](https://www.iso.org/standard/65502.html) | Stacked 2D code | Good paper ticket, card and long record layouts. |
| [ISO/IEC 20830 Han Xin](https://www.iso.org/standard/69321.html) | Matrix symbology with CJK-useful repertoire | Research international use before implementing own decoder. |
| [ISO/IEC 23634:2022 JAB Code](https://webstore.iec.ch/en/publication/75648) | **Published** multi-colour bar code with specified error correction and reference decoder | Interesting high-capacity/colour experiment; print calibration and decoder support critical. |
| [Ultracode project ISO/CD 25449](https://www.iso.org/standard/90433.html) | Multi-colour 2D symbology | **Draft/under development** in survey; verify final standard status before claiming compatibility. |
| [AIM DotCode](https://www.aimglobal.org/) | Industrial dot-based 2D marking | An AIM symbology specification; avoid inaccurately assigning an ISO/IEC number. |
| [ISO/IEC 15415:2024](https://www.iso.org/standard/76876.html) | Test methodology for 2D symbol print quality | Print export is not finished until actual physical readback/quality grade is measured. |
| [Blockchain Commons UR](https://developer.blockchaincommons.com/ur/), [BBQr](https://bbqr.org/) | QR-framed segmented / animated payloads used in offline Bitcoin signing | Multi-frame is a transport, not an unbounded single QR. Session/framing/fragment deduplication matters. |
| [Base45 RFC 9285](https://www.rfc-editor.org/rfc/rfc9285.html) | Text encoding for QR's alphanumeric symbol alphabet | Choose by actual QR mode; don't double encode if native byte mode and scanner can preserve bytes. |

**Protection layer:** QR and Data Matrix generally use built-in Reed–Solomon; codex32 uses a checksummed correction construction; large-payload optical streams can layer chunk CRC, Reed–Solomon erasure, or fountain codes such as [RaptorQ RFC 6330](https://www.rfc-editor.org/rfc/rfc6330.html). Checksum != repair != authenticated integrity. All ECC budgets require measured symbol loss/erasure models.

### 2.3 Printed archives, physical marks, active/passive media

| Reference | What has been done | Status and ByteFables lesson |
|---|---|---|
| [OPTAR](https://paperbackup.github.io/) | Optical paper file archiver; A4 laser printer + scanner, potentially high density | Published demo explicitly warns of some irreparable bit errors; parity and multiple copies remain essential. |
| [Paperback](https://github.com/ab/paperback) | Printable backup, several human-readable/error-aware representations | Useful precedent for recovery instructions and independent scanner paths. |
| [ISO PDF/A](https://pdfa.org/resource/iso-19005-pdfa/), [Library of Congress PDF/A-4f](https://www.loc.gov/preservation/digital/formats/fdd/fdd000652.shtml) | Long-term archival PDF conventions | Embedded files and fonts need profiles/validation; secret records must avoid unsafe spoolers. |
| [Bokode (MIT Media Lab)](https://www.media.mit.edu/publications/bokode-imperceptible-visual-tags-for-camera-based-interaction-from-a-distance/) | Optically specialised small tags for distance/camera applications | Interesting, but not compatible with commodity QR scanners. |
| [LayerCode 2019](https://www.cs.columbia.edu/cg/layercode/index.html) | 3D-printed layer patterns readable optically | Physical-code experiments must record manufacturing constraints and a real reader. |
| [InfraredTags CHI 2022](https://hcie.csail.mit.edu/research/infraredtags/infraredtags.html) | Hidden embedded QR/ArUco-like marks visible in near infrared | Specialist near-IR camera, printer materials and reader; a research concept rather than wallet-safe archive. |
| [3MF specification](https://3mf.io/spec/), [glTF 2.0](https://registry.khronos.org/glTF/) | 3D manufacturing and interactive scene interchange | Carrier interchange, not by itself a bit-storage standard. |
| [NFC Forum NDEF](https://nfc-forum.org/build/specifications/data-exchange-format-ndef-technical-specification/), [IEC 63652-2:2026](https://webstore.iec.ch/en/publication/106859) | Typed NDEF records for NFC devices/tags | Public tag transport first; NFC tags can be copied/read; not equivalent to authenticated secret storage. |
| [ISO 7816 smart card](https://www.iso.org/standard/77180.html) | Physical secure element/card command standards | If integrated, a *signed response* or challenge protocol differs from treating readable tag bytes as authentic. |

Also study microfilm, punched tape/card, engraving, acid etch, photoengraving, laser-engraved steel/titanium, ceramics, enamel, PCB copper/FR-4, laminated cards, textile/jacquard/embroidery and tactile Braille. Their existence as media does not grant a reliable data codec. Historical photographic and card media require a reader/format archive; longevity is environmental and must be tested. Niche options such as 5D quartz glass and synthetic DNA storage are **research directions**, not deliverable v1 exports or claims of permanence.

### 2.4 Visual identities, artistic rendering, game-engine outputs

| Reference | What has been done | Status and ByteFables lesson |
|---|---|---|
| [GitHub identicons](https://github.blog/news-insights/company-news/identicons/), [Ethereum Blockies](https://github.com/alexvandesande/blockies), [Jdenticon](https://jdenticon.com/) | Compact deterministic geometric avatars | Excellent fast fallback; image itself has limited distinctiveness. |
| [DiceBear](https://www.dicebear.com/), [Robohash](https://robohash.org/) | Many seeded style components/character assemblers | Establish a style registry, licence provenance and deterministic SVG layering. |
| [LifeHash](https://github.com/BlockchainCommons/LifeHash), [OIB](https://developer.blockchaincommons.com/oib/) | Cellular automata hash art; composite Object Identity Block | Pin exact LifeHash variant. Upstream notes different variants need not resemble each other. Preserve full ID alongside art. |
| [OpenSSH Randomart](https://man.openbsd.org/ssh-keygen.1) | Public key image fingerprint | Strong precedent for command-line, non-avatar readout. |
| [Khronos glTF Registry](https://registry.khronos.org/glTF/), [KTX2 Registry](https://registry.khronos.org/KTX/) | Exchangeable 3D assets and GPU textures | For DanceFlow and Unity: SVG/PNG/texture atlas/KTX2/GLB rather than ad-hoc WebGL-only assets. |
| [W3C SVG](https://www.w3.org/TR/SVG2/), [WebGPU](https://www.w3.org/TR/webgpu/) | Scalable graphics and modern accelerated rendering APIs | SVG is the reference artifact for simple art; GPU output is a renderer profile, not a distinct identity hash. |
| [3MF](https://3mf.io/spec/) | Manufacturable mesh/material/units specification | More descriptive than STL for physical tokens; keep fabrication profiles separate. |

Original candidates not yet subject to verification include: constrained-L-system plants, Voronoi/generative geometry, reaction-diffusion life art, polyhedra, orbital sigils, shader fractals, procedural creature assemblers, multispectral 3D surfaces, interactive graph orbs and animated themes. These belong in the **identity-only** lab until a separate proved lossless decoder exists.

### 2.5 Acoustic, spoken, tactile, light and device channels

| Reference | What has been done | Status and ByteFables lesson |
|---|---|---|
| [ggwave](https://github.com/ggerganov/ggwave) | Small data-over-sound FSK modem with ECC; 8–16 bytes/s under stated profiles | Real binary transport distinct from earcons. Evaluate interference, microphones, decoding and codec compatibility. |
| [Quiet](https://github.com/quiet/quiet) | Software data modem over audio | Alternative protocol; interoperability depends on matched physical-layer settings. |
| [ITU-R M.1677](https://www.itu.int/rec/R-REC-M.1677/en) | International Morse code | Interesting simple LED/sound/manual channel; low capacity, requires framing and checksum. |
| [Unicode Braille patterns](https://www.unicode.org/versions/Unicode18.0.0/core-spec/chapter-21/) | 8-dot Braille block has 256 patterns | Underlying physical cell patterns can carry bits, but translation, orientation, embossing quality and reader capability matter. |
| [NFC NDEF](https://nfc-forum.org/build/specifications/data-exchange-format-ndef-technical-specification/) | Typed passive near-field records | Device transport; not permanent, unforgeable or private by itself. |

Investigate audio earcons/rhythms (for recognition), spoken mnemonic readback, haptic vibrations, Morse flashes, watch alerts, e-paper, LEDs, near-IR light, ultrasonic and QR-on-screen optical links. Accessibility and reliable recovery are different output contracts; TTS pronunciation may destroy homophonically ambiguous codes.

## 3. Engineering conclusions supported by the survey

1. **Split codec, protection, symbol, renderer/export and carrier.** Most novel outputs are new exporters on an existing exact binary record, not new crypto.
2. **Start with useful scanner and reader availability.** QR + SVG/PNG/PDF, Bytewords, strict Base32, PDF/A-ready layouts and independent readback provide broader practical value than novel colour or IR symbols.
3. **Keep the public identity gallery separately first-class.** Favicon/sprite atlas/React/WebGL/Unity are practical DanceFlow requirements; they do not need secret handling.
4. **Make exact bit accounting mandatory for story codecs.** Template selectors, filler words, length/version/checksum/padding and variable dictionary cardinalities require a provable decoder.
5. **Secret/key compatibility is not self-declared.** Require upstream official vectors, actual wallet recovery test evidence, process isolation and independent security review before changing maturity from planned.
6. **Archival permanence is a system property.** Device survival, physical durability, decoder documentation, readback evidence, independent copies and future availability of readers matter more than appealing artwork.
7. **Specialist modes stay labelled experimental.** NFC, colour codes, audio modems, 3D tags, braille and microfilm may be excellent in narrower circumstances; readers and licences must be verified.
8. **Don't chase every format at once.** The [implementation plan](IMPLEMENTATION_PLAN.md) assigns a reversible central spine and prioritised, separable workstreams, while the [atlas](OUTPUT_FORMAT_ATLAS.md) preserves long-tail options without false shipping claims.

## 4. Questions for laboratory investigation

- How many visually distinct 16px identity marks remain easy to differentiate when displayed in a 1,000-node graph? Measure human confusion rather than bit length of source hash.
- Can 33-bit semantic sentence grammars pass statistically meaningful transcription tests against same-entropy BIP-39 and Bytewords, with a frozen reversible codebook?
- What QR Data Matrix/Aztec density maximises real-world smartphone readback on paper, engraved steel and low-end LCDs, and how does ECC interact with ink spread/lighting?
- Do two independent scanners/decoders recover the same typed bytes from a printed and intentionally damaged barcode? What fraction of losses is detectable vs repairable?
- What is the smallest reproducible SVG/spritesheet/WebGL atlas renderer that maintains node identity across Node, browser and Unity, including accessibility modes?
- What payload rate and error probability do sound/LED/NFC transports achieve under noisy or occluded real-world conditions? Are extra modalities worth their dependencies?
- Which medium + documentation + open reader + redundancy combination permits complete recovery in 10/25/50 years? Build experiments rather than guarantee lifetime.

The **format survey is descriptive, not permission to process private keys**. Implementing a new exporter remains subject to the sensitivity and adversarial requirements in `SECURITY.md`.
