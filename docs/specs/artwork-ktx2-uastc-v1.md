# UASTC + Zstd KTX2 transport v1

Status: experimental, PUBLIC, presentation-only. This is a compressed transport
layer over the already-qualified lossless ByteFables KTX2 arrays. It does not
change public identity keys, artwork generation, native mip construction, or the
lossless `bytefables.ktx2-alpha-bundle.v1` reference.

## Frozen encoder profile

Schema: `bytefables.ktx2-uastc-bundle.v1`
Profile: `bytefables.ktx2-uastc-zstd.v1`

Encoding is delegated to **Khronos KTX-Software 4.4.2**. ByteFables does not
implement a second Basis/UASTC codec. The executable must report exactly 4.4.2.
Each lossless KTX2 bank is encoded independently with:

```text
ktx encode --codec uastc --uastc-quality 4 --uastc-rdo \
  --uastc-rdo-l 0.5 --uastc-rdo-m --threads 1 --zstd 18 input.ktx2 output.ktx2
```

`--threads 1` and `--uastc-rdo-m` deliberately remove encoder/RDO thread
nondeterminism. Export encodes each bank twice by default and requires byte-for-
byte identical containers. This is reproducibility of the pinned encoder profile,
not a promise that another KTX release produces identical bytes.

The lossless transport remains authoritative. UASTC is **lossy relative to the
existing premultiplied mip bytes**. Zstd only losslessly compresses the UASTC
payload after that lossy transform.

## Verification and quality gate

Every compressed bank is independently accepted by `ktx validate
--warnings-as-errors`, then all layers and mip levels are transcoded to RGBA8 with
`ktx extract --transcode rgba8 --all --raw`. ByteFables measures the decoded
bytes against the lossless bank and records per-bank and aggregate metrics.

The v1 acceptance policy is intentionally explicit and conservative:

- overall PSNR >= 30 dB;
- mean absolute channel error <= 8;
- maximum channel error <= 96;
- alpha PSNR >= 34 dB;
- mean alpha error <= 6;
- maximum RGB-over-alpha premultiplication overshoot <= 32;
- decoded pixels violating RGB <= alpha <= 10%.

The policy is a machine transport gate, **not human perceptual equivalence**.
A later image-quality study may tighten it but must version any incompatible
policy. The manifest freezes the exact policy used for a successful export.

Verification always checks container checksums, the pinned tool version,
Khronos validation, complete transcode inventory, and the saved decoded-level
hashes. Supplying the original lossless bundle additionally recomputes every
error metric from source bytes. The success manifest is written only after all
checks pass. Failed or partial outputs carry `failure.json` and are not reusable
as successful bundles.

## Runtime boundary

This milestone intentionally does **not** add a home-grown UASTC decoder to the
browser or Unity package. A consumer must use an independently qualified Basis
transcoder suitable for its platform. The existing uncompressed KTX2 path remains
the fallback/reference and the source for exact readback tests.

The adjacent streaming/residency milestone works on verified bank units and is
codec-independent at the cache-policy level, but its browser implementation v1
loads the existing lossless KTX2 banks. It does not silently transcode UASTC.

## Security and provenance

Only fixed source-bank paths from the verified transport manifest are encoded.
The encoder is executed directly without a shell, with bounded process time and
file sizes. Output directories are new and cannot contain the source bundle or
KTX executable. Hashes establish consistency with the selected public manifest;
they are not signatures or proof of identity ownership.

## Commands

```sh
python scripts/export-artwork-ktx2-basis.py --confirm-public --ktx /path/to/ktx \
  export --bundle _work/artwork-ktx2 --output _work/artwork-uastc

python scripts/export-artwork-ktx2-basis.py --confirm-public --ktx /path/to/ktx \
  verify --bundle _work/artwork-uastc --source-bundle _work/artwork-ktx2
```

CI installs the checksum-pinned official KTX 4.4.2 Linux package, so missing or
changed external tooling is a hard failure rather than an implicit fallback.

## Real-artwork CI qualification

`Artwork real UASTC compression qualification` is triggered only after a
successful **push-to-main** `Artwork native compositor benchmark`. It checks out
the exact native run SHA, downloads that run's verified `artwork-ktx2` artifact,
encodes the real public identity banks, then performs source-backed verification
against the downloaded lossless reference. Pull-request artifacts and failed or
non-main native runs cannot enter this job. The resulting UASTC artifact is named
with the originating native commit SHA.
