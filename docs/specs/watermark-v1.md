# ByteFables robust watermark operation: Wave A protocol and research gate

**Document:** BF-WM-001 • **Date:** 2026-10-25 • **Status:** message framing implemented;
carrier embedding/detection **not implemented**. Public typed identifiers only.

## Goal, scope, terminology

Add a fourth logical operation, **watermark**, alongside lossless encoding,
identity representation and archival transport. A watermark intentionally
*modifies another carrier* to encode a compact public identity or reference.
Unlike lossless byte-to-words/QR, recovery is statistical and requires an
independent extractor, a declared threat model, evidence of perceptual quality,
measured error rates and a binding back to the full canonical public record.

All public output families may be *candidates* for watermark operations, but
applicability and safety vary. Public photographs, illustrations, animations,
music, video and generator-controlled prose are plausible. Raw `.bin` archives,
checksummed files, XML/JSON protocols, pre-existing signed media, QR/2D symbols,
and CNC/3D codes must not be silently altered: such changes can break their
primary recoverability or signature. For those outputs prefer sidecars, C2PA
manifests, an outer container, or a watermark on a **separate visual decoration
layer**, qualified by independent readback.

**Three properties are distinct:**

- **Imperceptibility**: the change is difficult for ordinary human observers to
  see/hear/read, established by media-appropriate blinded perceptual tests.
- **Robustness**: a *specified* channel/transformation still allows extracting
  the expected public payload at a *measured* error rate.
- **Undetectability**: a statistical/adversarial observer cannot distinguish
  marked from unmarked content. This is a far stronger property and is **not
  claimed**. Robustness, detectability, rate, distortion and key secrecy trade off.

Neither imperceptibility nor survivability is unconditional. Severe crop,
resynthesis, re-rendering, AI regeneration, re-recording or adversarial
watermark removal may destroy any mark. A detected mark never authenticates the
original publisher on its own. The C2PA specification explicitly separates
soft watermark/fingerprint bindings from exact cryptographic hard bindings.

## Wave A implemented: *message* v1

`encodePublicWatermarkMessage(PublicRecord, digestBytes=12)` creates an exact
byte string to feed to a future ECC encoder + medium embedder. The input MUST
be a typed public record; a `ByteValue<'secret'>`, wallet seed, private key or
confidential content may not enter public media output pipelines.

| Offset | Length | Meaning |
|---|---:|---|
| 0 | 4 bytes | UTF-8 ASCII `BFWM` |
| 4 | 1 byte | Version `0x01` |
| 5 | 1 byte | Digest prefix length 12 / 16 / 32 bytes |
| 6 | N bytes | Prefix of `publicRecordDigest(record)` SHA-256 |
| 6 + N | 4 bytes | IEEE CRC-32 (big-endian) of preceding message |

There is no ECC in this format. Message lengths are 22, 26 and 42 bytes,
representing **176, 208 or 336 bits** before any synchronisation, forward error
correction or repetition. `decodePublicWatermarkMessage()` validates framing,
size, allowed digest-prefix lengths and CRC-32. `matchesPublicWatermarkMessage()`
compares the decoded prefix to a full typed public record's digest. The
watermark **does not recover the original bytes** nor prove authenticity.

CRC-32 merely detects many accidental errors; it is not a keyed MAC. SHA-256
prefix collisions remain possible and an adversary can forge a new CRC/digest.
The 96-bit default is intended as a probabilistic lookup handle, not a universal
unique or secure identifier. Full 256-bit digest is supported at increased
capacity cost. Version 1 message framing and vectors in
`tests/vectors/watermark-message-v1.json` are frozen.

**Do not embed these bytes as simple LSB modifications and call them robust**:
spatial resize/JPEG, audio transcode, screenshots and text normalisation could
remove the mark. Use a decoder-independent benchmark before making any claim.

## Wave A implemented: carrier planner

`planPublicWatermark(record, carrier, opts)` produces an immutable **plan**,
never an artifact or a concealed signal. The plan includes:

- a carrier-specific planned format (`watermark/image-spatial`,
  `watermark/audio-spectral`, `watermark/video-temporal`,
  `watermark/text-semantic`) and exact input MIME;
- public watermark message bit requirements, selectable 96/128/256-bit digest
  lengths and no fictitious ECC rate/capacity;
- conservative suitability screening (research eligibility, **not** capacity);
- the FrameRudiments render host, candidate algorithm family, requested
  distortion targets and required evidence;
- explicit `embedderAvailable: false`, `detectorAvailable: false`,
  `robustnessValidated: false` and `imperceptibilityValidated: false`.

The CLI `bytefables watermark-plan` requires `--confirm-public` and only prints
plan metadata. It never reads a carrier, modifies a pixel, saves a file,
embeds anything or reports a successful detection. Carrier-specific planned
registry entries cannot be executed via `executePublicFormat`.

## Future pipeline contract owned by FrameRudiments

```text
PUBLIC typed record -- SHA-256 --> BFWM message --> outer FEC/CRC/interleave
                                                        |
source carrier --> FrameRudiments native signal/effects compositor ----------+
       |                       |                            |
  image pixels            audio PCM                    temporal video frames
       |                       |                            |
 image residual          perceptual spectral         spatial + temporal repetition
       +-----------------------+----------------------------+
                               |
               final encoded artifact / codec
                               |
       independent extractor, unknown crop/synchronisation estimation
                               |
                 probabilistic candidate message
                               |
           FEC decode -> v1 CRC -> full typed public-record match
                               |
            signed manifest/full-ID check where authenticating
```

FrameRudiments owns all reusable generators/effects and their CPU/GPU versions.
ByteFables must not create a second independent media transform loop. FrameRudiments'
current effect graph exposes a fixed set of node kinds. A new **native effect
extension contract** is required upstream before claiming a reusable watermark
insertion point; the existing `RendererRegistry` registers generators, **not**
watermark effects. The native host's audio policy also keeps the master unchanged;
watermarked audio must be a distinctly labelled, explicit opt-in *derivative*.

Proposed native effect descriptors contain: carrier type, insertion stage, ID,
version, model/dependency digest, watermark message hash, FEC/profile, masking
parameters, tile/time synchroniser, compatibility with other effects, input
pixel/sample colour-space/timebase, source sensitivity, resource budget,
provenance and offline fallback. Effects are trusted, explicitly registered,
never dynamically loaded from arbitrary project JSON. Effects must support
`prepare`, `embed`, `finalize`, and extraction/quality-benchmark hooks with
bounded buffers and deterministic time seeds. The entire delivered result
must be independently extracted **after** video/audio encoding, not directly
from the uncompressed compositor frame.

- **Image:** candidate multiscale mid-frequency DCT/DWT/learned residual with
  content-adaptive masking; spatially repeated local marks, pilots and
  geometry-sync to survive *bounded* crop/rotation/scale/JPEG. StegaStamp
  demonstrates real photographed-image recovery, with its own capacity limits.
- **Audio:** candidate spread-spectrum/psychoacoustic band coding, time-sync,
  redundancy and optional learned watermarking (AudioSeal). Sound quality,
  MP3/AAC/Opus, resampling, pitch/time warp, silence/voice-only segments and
  re-recording require separate qualification. AudioSeal's open models use a
  **16-bit optional message**, not arbitrary 96–256-bit hashes; a generic
  interchange decoder cannot be inferred from watermark *presence* detection.
- **Video:** repeated frame-local marks plus optical-flow/crop-time alignment;
  align with native FrameRudiments clocks, frame-rate changes, transcoding,
  frame drops, hard cuts, overlays and partial clip extraction. VideoSeal and
  RivaGAN are candidate reference families, not ByteFables interoperability.
- **Text:** for *generator-controlled* output, choose language-model token
  probabilities or a strictly validated semantic grammar; plain prose cannot
  safely acquire hidden bits without changing words. Extra whitespace, zero-width
  Unicode, typography or alternate punctuation are fragile and generally do
  not survive copy/paste, normalisation or paraphrase. A source-verbatim,
  legally fixed, signed or security-related document must never be rewritten.
  Text watermarks can survive some edits but not arbitrary paraphrase/translation;
  a fixed 96-bit lookup key may exceed a practical excerpt's channel capacity.

## Benchmarks and quantitative release gates

For every candidate format/version/profile and media size, record:

1. Control baseline: unmarked corpus (including intentionally adversarial
   content), observed false-positive rate, confidence calibration and
   *multiple testing* effects. A found pattern alone is not evidence.
2. Positive corpus: a minimum of 1,000 diverse nonsecret samples per supported
   carrier/profile, with independent extraction and exact 96/128/256-bit
   comparison. The chosen sample size determines confidence-interval precision;
   it cannot prove zero false positives.
3. Transform matrix: clean, print/screen photo (image), crop from centre/edge,
   rotate, change resolution, change aspect ratio, JPEG/WebP/AVIF transcode,
   overlay, colour edit; MP3/AAC/Opus/resample/time shift/crop/noise for audio;
   FPS change/frame drop/temporal crop for video; whitespace normalisation,
   excerpting, paraphrase and translation for text (separately graded).
4. Exact distortion severity and fraction retained, attack sequence, data bit
   error rates before/after ECC, failure/abstention rate, false positives,
   confidence quantiles, and CPU/GPU latency and peak memory.
5. Perceptual metrics (e.g. image LPIPS/SSIM + blinded users, audio PEAQ/ABX,
   text meaning-preservation and factuality), plus comparison with original.
   No single metric guarantees "imperceptible" to every person.
6. Deliberate removals, multiple marks, collisions, remixing, downmixing,
   lossy recompression, missing metadata, adversarial signal transformations.
7. Versioned independent decoder and frozen corpus with *final encoded files*,
   not a test on the pre-encoder residual. No claim of an unconditionally
   recoverable hash; report successes and failure cases transparently.

Benchmarks must include a true *blind detection* case that does not supply the
unmarked original. If an algorithm requires the original, label it non-blind
and distinguish an informed comparison from blind extraction. A signed public
identity or C2PA manifest can bind the recovered reference to an authenticated
publisher. CRC or hash prefix alone cannot.

## Consent, provenance and privacy

The content owner must explicitly opt in to watermark insertion. The fact that
content can contain a hidden mark should be documented in project provenance;
ByteFables must not become a covert third-party tracking channel, nor treat
watermarks as DRM or proof of entitlement. Do not retain forensic recipient IDs
or device identifiers without appropriate consent and retention controls.
Public watermark bytes can be repeated, scraped or spoofed. Secret payloads,
private keys, passphrases or account credentials are **never supported** in
this shared public rendering pipeline. Never call outside services or download
model weights without an explicit configured policy. Preserve a clear,
non-watermarked rendering mode and test compare the two.

## References and implementation precedence

- [C2PA 2.5, soft vs hard bindings](https://spec.c2pa.org/specifications/specifications/2.5/specs/ContentCredentials.html)
- [Google SynthID overview](https://deepmind.google/models/synthid/) and
  [SynthID Text limitations](https://ai.google.dev/responsible/docs/safeguards/synthid)
- [StegaStamp](https://github.com/tancik/StegaStamp) (photographed imagery)
- [Meta AudioSeal](https://github.com/facebookresearch/audioseal) (localised speech)
- [Meta VideoSeal research](https://github.com/facebookresearch/videoseal)
- [Meta watermark benchmarking](https://github.com/facebookresearch/omnisealbench)
- [FrameRudiments native effects graph](https://github.com/kieransimkin/FrameRudiments/blob/main/docs/effect-graph-design.md)

Check active licences, pretrained-model terms, current maintained versions,
input capacity and independent bit-level recovery before selecting a dependency.
