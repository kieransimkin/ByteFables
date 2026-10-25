# BF-FRACTAL-001 — Fractal-seeded PUBLIC identity and model experiments

**Status:** Research implementation, 2026-10-25. Not a wallet backup, not an interoperable visual hash standard, not an authenticated identifier.

## Objective and non-goals

Test whether deterministic fractal imagery supplies more visually distinctive and more controllable node avatars than the existing pixel identicon or small text-to-image models. Compare **direct procedural sprites**, **fractal-conditioned image-to-image generation**, and **fractal-correlated diffusion latents**, always against matched non-fractal controls.

A public hash drives these views; the full original canonical identifier remains the authority. **No image is claimed to contain or preserve every source bit**. Visual similarity is not a collision-resistance guarantee. The system MUST NOT be used to generate images from wallet secrets or pass these bytes to model services.

## Research precedents

- Scott Draves, *The Flame Algorithm* and `flam3`: IFS with contractive transforms and non-linear variations, density-based render and colour accumulation. https://flam3.com/flame_draves.pdf . The upstream flam3 code is GPL and is not copied here.
- Kataoka et al., *Pre-training without Natural Images* (ACCV 2020): fractal generated datasets for visual representation learning. https://openaccess.thecvf.com/content/ACCV2020/html/Kataoka_Pre-training_without_Natural_Images_ACCV_2020_paper.html
- Anderson et al., *Improving Fractal Pre-Training* (WACV 2022): efficient sampling of useful IFS parameter families and stylisation. https://openaccess.thecvf.com/content/WACV2022/papers/Anderson_Improving_Fractal_Pre-Training_WACV_2022_paper.pdf
- `fractal-hash` (MIT): independent example of fractal cryptographic fingerprints, ANSI/SVG/PNG and cross-platform vector tests. https://github.com/tyrenker/fractal-hash . ByteFables is not wire- or pixel-compatible.
- Hugging Face Diffusers Stable Diffusion `latents` input: existing models can accept externally generated Gaussian latents. https://huggingface.co/docs/diffusers/api/pipelines/stable_diffusion/text2img
- Hugging Face Diffusers img2img: existing image-to-image pipelines can condition on a supplied source image. https://huggingface.co/docs/diffusers/using-diffusers/img2img

## Binary data and explicit feature controls

The ByteFables version-one seed derivation is:

```
canonicalRecordDigest = publicRecordDigest(typed PUBLIC record) # existing canonical CBOR/domain contract
seed256 = SHA256(UTF8('ByteFables:fractal-seed:v1\\0') || canonicalRecordDigest)
featureBits[0..7] = bits 0..7 of original PUBLIC payload in MSB-first order
```

The domain string contains an actual NUL byte (0x00), not the printable backslash and zero characters. The same public typed object always produces the same seed. Namespace, kind, network, byte order and other canonical record metadata are already bound into `publicRecordDigest`.

The first eight source bits select eight opposing axes. These decisions are *not* a decoder, because most axes are not perceptually independent or equally visible:

| Bit | Zero | One | Intended influence |
|---|---|---|---|
| 0 | smooth | spiky | radial deformation strength |
| 1 | dark | bright | background/exposure |
| 2 | muted | saturated | chroma |
| 3 | matte | glossy | highlight shading |
| 4 | bilateral | asymmetric | horizontal geometry policy |
| 5 | sparse | dense | IFS sampling or iterative detail |
| 6 | warm | cool | hue range |
| 7 | organic | angular | shape/geometry details |

Other bits **do influence the full seed256 via SHA-256 avalanche**. There is no assertion that bit 31 corresponds to a dedicated 31st independently observable feature. High visual variation from a single-bit flip is not the same as recovering the bit value or preserving a 256-bit information capacity.

### Counterfactual protocols

- `avalanche`: recompute the whole seed for each modified public hash. Measures whole-identity visual sensitivity. Direct feature changes and background random changes are confounded by design.
- `axis-isolated`: hold the ORIGINAL seed constant while changing only the eight explicit feature bits. For `bit >= 8`, the pictures MUST be identical; that is an expected null control and an honest capacity boundary.
- Run both for each family and use identical canvas size, palette setting and quality level across pairs.

### Built-in experimental procedural families

1. `julia`: escape-time iteration of `z <- z² + c`; select from curated parameter neighbourhoods and jitter using seed bits.
2. `burning-ship`: absolute-coordinate escape-time variation; may degenerate into uniform regions for some seeds.
3. `ifs-fern`: seeded chaos-game, bounded histogram density and log-density colour; small sprites can lose thin structures.
4. `fbm`: multi-octave deterministic value noise with 2D lattice hashing; continuous structures, often low-contrast at small sizes.

All four use FrameRudiments' **trusted `RendererRegistry` source-layer interface** `bytefables-fractal-v1`; ByteFables owns no alternative clock, effects compositor, shader graph, image encoding or video pipeline. `render-fractals` invokes precisely that plugin as an offline static-source test fixture, and emits PNGs and receipts for independent study. The host handles final sprites/effects, antialiasing and export.

Limits: maximum 262,144 source pixels per generated image, max width/height 1,024, fully explicit palette/quality enums, bounded parameter families and no dynamic script/asset execution. For cross-platform correctness, version the exact renderer, Pillow/Python and backend. The current tests establish same-runtime repeatability, **not** bit-identical GPU/CPU behaviour across libraries or machines.

## Small image model comparison matrix

Keep the **prompt-writing LLM, prompt budget, prompt strategy, model checkpoint, resolution, scheduler, guidance, seed and inference steps** fixed across only-one-factor A/B comparisons.

1. `gaussian`: standard Diffusers text-to-image with ordinary IID Gaussian initial noise (existing baseline).
2. `gaussian, seedPolicy=identity`: still IID Gaussian, with seed selected by the public hash instead of paired across cases.
3. `fractal-spectral`: SD/SDXL-only experimental mixture of IID Gaussian noise and FFT-filtered 1/f^beta correlated noise. The original white-noise sample is shared between baseline and treatment, then blended and normalised. **This breaks the trained IID prior**; no quality improvement is implied. Candidate grid: beta `{0.5,1.0,2.0}`, mix `{0.15,0.35,0.65}` with controls for beta=0 and mix=0 (normal Gaussian).
4. `fractal-img2img`: SHA-verified FrameRudiments procedural fractal raster fed to a compatible local SD/SDXL image-to-image pipeline using `AutoPipelineForImage2Image.from_pipe`; strength controls how much of the original pattern survives. Candidate grid: strength `{0.3,0.55,0.8}` for each fractal family.
5. Later: ControlNet/T2I-adapter and IP-Adapter, for models with **confirmed** pre-downloaded, compatible checkpoints and provenance. Also investigate phase-only Fourier transforms that preserve Gaussian distribution while making public-hash-conditioned orthogonal noise transforms.

Methods 3 and 4 are experimental, explicitly opt-in, must not be silently combined or labelled as measured improvement. Import of local models remains manual, with licenses and checkpoint revisions pinned. The tool never downloads weights.

## Profiling and failure gates

- **Structural:** seed repeatability at the same runtime; correct bit and namespace separation; exact checksum of each PNG; same file for axis-isolated flips beyond eight controls.
- **Visual:** actual image luminance std, saturation, edge density, perceptual aHash distance, mean absolute RGB difference, repeated-output collisions, downsampled 16/32/64px recognisability, confusability matrix.
- **Semantic:** independently blinded opposing-axis classification (human or calibrated model); report balanced accuracy and confidence, not just CLIP similarity.
- **Compositional:** compare 8/16/32 prompt-bit budgets with and without fractal conditioning, using multiple small LLM prompt writers. The `fractal` prompt strategy explicitly adds self-similar visual language without claiming to encode additional bits.
- **Resources:** CPU/GPU peak memory, latency (cold/warm separately), output size, energy estimate only when measurable, caching potential.
- **Out of distribution:** identify degenerate, blank, sparse or low-contrast outputs, and fraction of seeds causing unstable/ugly output. Do NOT discard these silently.
- **Security:** no private key input, no automatic cloud inference, no claim of watermarking or reversible mnemonic recovery.

A full experiment should sample at least 1,000 public pseudorandom identities and 1,000 single-bit flips across bit positions (or a justified stratified subset) before drawing visual distinctiveness conclusions. The small synthetic demo is a software smoke test, not that statistical study. Human assessment should be blinded to which source bit was flipped and to the generating method.

## Commands

```bash
# Node/TypeScript core first
npm ci --ignore-scripts
npm run check
python -m pip install -e ./integrations/framerudiments

# Experimental PUBLIC input only; synthetic sample below
python -m tools.hash_image_bench prepare --confirm-public \
  --public-hex 000102030405060708090a0b0c0d0e0f101112131415161718191a1b1c1d1e1f \
  --budgets 8,16,32 --strategies direct,fractal,narrative,structured \
  --paired-bits 0,1,6,31 --output _work/fractal-study

# True CPU procedural PNGs; includes both avalanche and axis-isolated controls
python -m tools.hash_image_bench render-fractals --experiment _work/fractal-study \
  --families julia,burning-ship,ifs-fern,fbm --modes avalanche,axis-isolated --size 128

# Dry-run the 2 AI treatment types (NO model loads without --execute):
python -m tools.hash_image_bench render --experiment _work/fractal-study \
  --models experiments/tiny-image-models.example.json --latent-policy fractal-spectral \
  --fractal-beta 1.0 --fractal-mix 0.25 --max-jobs 100000
python -m tools.hash_image_bench render --experiment _work/fractal-study \
  --models experiments/tiny-image-models.example.json --conditioning-policy fractal-img2img \
  --fractal-family julia --img2img-strength 0.55 --max-jobs 100000
```

`--execute` additionally requires locally downloaded valid checkpoints and a compatible runtime. Results always carry the checkpoint claim, model settings, source image checksum, source recipe, inference technique and experiment ID. Neither tests nor the demo provide fake image-model rankings.
