# BF-EXPERIMENT-IMAGE-001: hash-bit-conditioned text-to-image profiling

**Status:** research prototype / PUBLIC ONLY / not a recoverable hash representation. 2026-10-25.

## Mission

Evaluate which local small language models can express a fixed set of bit-conditioned
visual choices, and which compact image diffusion engines actually render those
features as stated. The image is a recognisable **identity view** and must never
be represented as a bit-exact key backup, cryptographic fingerprint, proof of
ownership, or secret watermark.

The four operations are intentionally separate:

1. **Mapping:** every bit of a *public* source byte sequence maps to a frozen
   opposing pair of scene features. This stage is deterministic and bijective
   between bit values and *labelled choices* when the source length and codebook
   version are known. Mapping alone contains the original bits; an image doesn't.
2. **Writing:** a compact language model rewrites selected decisions into an
   image prompt, compared against deterministic baselines. The original hash is
   not given to the LLM. The selected choice, opposing choice and visual scope
   are included, so the LLM must not silently invert the bit's meaning.
3. **Generation:** image checkpoints run under explicit local paths, immutable
   revisions, model-specific guidance/step settings, controlled noise seeds and
   bounded budgets. No weights are auto-downloaded.
4. **Evaluation:** independent feature judgments, controlled bit flips, image
   distinctiveness, runtime and memory. No visual metric is treated as a proof
   of bit-by-bit recovery or cryptographic uniqueness.

## Feature codebook `bytefables.visual-bits.v1`

Bit order is MSB-first: bit 0 corresponds to the highest bit of source byte 0.
No bits are truncated in the **feature plan**. Supported PUBLIC sources are
1 to 512 bytes, including common 160/256/384/512-bit identifiers.

- Indices 0..31 target 32 named global attributes: silhouette, illumination,
  saturation, material, symmetry, density, geometry, lighting and related
  scene attributes. Each has one explicit zero phrase and one explicit one phrase.
- Indices 32 onward occupy separate numbered **micro-motifs**. Sixteen
  stable micro-attributes repeat per numbered motif (e.g. motif 001 edge and
  motif 014 edge are separate slot/feature combinations). This provides a
  deterministic way to assign even thousands of source bits to distinct
  *position-labelled* binary choices; it does **not** mean a tiny image model can
  draw or a viewer can recover thousands of spatially independent markings.
- No bit controls another bit's polarity. A one-bit mutation changes exactly
  one chosen feature and also the derived identity-noise seed.
- A zero/one adjective may also be chosen elsewhere for another scope. The
  lexical prompt audit therefore remains a diagnostic, not a full proof that
  scene attributes are noncontradictory.

The public input bytes, namespace and object kind are retained in experiment
metadata and domain-separated using the existing `identityDigest`. The first 32 digest bits form the legacy `visualSeed` hint, and
the first 64 digest bits form `visualSeed64` (decimal string). Neither LLM input nor visual decoding needs
access to the original public-hex string for normal prompt writing. The
**full** original bytes affect the identity-seed digest even when the prompt
budget limits the number of semantic features.

### Semantic capacity versus generated-image capacity

If a 256-bit value has a budget of only 16 prompted features, the prompt can
express at most 16 of its source bits through those binary features. The
remaining 240 bits are still in the manifest and may affect the image's
pseudorandom diffusion seed, but **cannot be claimed as visible/recoverable**.
If the seed policy is `paired`, a flip to an unprompted bit leaves both prompt
and noise seed unchanged: the resulting model call is identical by design.

Even with a 64-bit diffusion seed, collisions remain possible; it is not a
256-bit cryptographic identity. Even when all 256 feature choices enter the prompt, a generative model may omit
features, invert attributes, collapse micro-motifs, lose orientation, or produce
similar pictures for different input hashes. Prompt-conditioned image creation
is many-to-many and in no sense a guaranteed error-correcting code.

If a genuinely recoverable image is required, overlay or embed a separately
**verified** QR/matrix/other lossless encoding with real readback, using
FrameRudiments' protected optical rendering profile, not this artistic codec.

## Compact 24/32/64-bit profiles

ByteFables supports direct PUBLIC 3-, 4- and 8-byte hash inputs or deterministic
shortening from a longer typed PUBLIC hash. It uses the existing SHA-256
identity digest and **leftmost 3/4/8-byte truncation**, not modulo or XOR folding.
See [the short-hash specification](short-public-hashes-v1.md) for provenance,
exact distribution assumptions and collision budgets.

- Short profiles contain exactly **24, 32, 64 source bits**; no additional
  distinguishable identities are created by deriving longer noise seeds.
- Automatic experiment budgets: `8,16,24` for 3-byte; `8,16,32` for 4-byte;
  and `8,16,32,64` for 8-byte. Explicit budgets over capacity fail.
- `prepare --short-hash-bytes {3,4,8}` stores full input provenance, performs
  the initial derivation once, and then treats the shortened bytes as the
  benchmarked input. This is NOT equivalent to flipping a bit in the original
  full digest before shortening.
- `pairedBits` for shortened profiles refer to **short-hash bit positions**,
  allowing clean one-feature counterfactual experiments. These modified aliases
  are synthetic feature-control vectors, not necessarily derivable from a
  known longer value.
- Compare separate long-input avalanche experiments by flipping a long input
  bit *before* the SHA-256 step, then examining the short-prefix difference.
- Always report collisions at the level of the **actual shortened byte values**
  as well as any subsequent visual collisions. Retain the complete canonical
  parent ID as ground truth.

## Experiment matrix

For each source value:

- budgets: default `8,16,32`; research ladder `4,8,16,32,64,128,256`
  (omit budgets larger than the input's bit count);
- prompt strategies: `direct`, `compact`, `narrative`, `structured`, `scene`,
  `contrasts`; all strategy outputs use the same chosen feature contract;
- writers: frozen deterministic baseline, then each small local LLM and
  decoding settings, saving raw response, prompt, negative prompt, profile and
  lexical audit;
- generators: a matrix of locally pinned diffusion checkpoints, samplers,
  steps, resolution and guidance. Supported reference adapter is Diffusers.
  Batch sizes and other speed comparisons must be stratified by resolution;
- seeds: at least 3 repeats; `paired` policy fixes diffusion noise for a
  controlled one-bit comparison; `identity` policy uses the identity digest
  seed for production-like avatar rendering;
- counterfactuals: flip exactly one bit at a time while keeping all other bits,
  writer configuration and paired diffusion seed unchanged. Each flipped bit
  yields a separate public identifier, not an additional secret;
- evaluations: small-icon renderings (16px/32px), full-res exports and
  independent annotation/VLM scoring. No unvalidated interpolation or effects.

A first 4-writer × 5-generator × 3-budget × 4-style × 3-seed × 10-hash matrix
would request **7,200 images**. Use staged experimental-design sampling and
paired subsets before allocating that much GPU time. The CLI enforces an
explicit `--max-jobs` ceiling; the default is intentionally small.

### Stage A / low-cost pilot

Use 8 and 16 bits, two prompt strategies, one baseline plus two LLM writers,
three tiny diffusion models, two paired seeds and ten PUBLIC synthetic hashes.
Hold one bit at a time constant/flip it across a balanced case list. Establish
prompt truncation, inference compatibility and a realistic time budget before
further expansion. Record all denominators: absent or failed images cannot
silently vanish from aggregate success rates.

### Stage B / power curve

Measure 4, 8, 16, 32, 64, 128 and 256 selected visual attributes with fixed
seed and prompt strategy, balanced zero/one choices, controlled one-bit flips,
and two output resolutions. Use paired samples to identify effective attribute
retention and cross-feature interference, with an held-out evaluation model.
For example, if *independent, balanced* binary features each have measured
error probability e, an illustrative upper estimate for a binary symmetric
channel is `1 - H2(e)` bits per feature. Real errors are correlated, CLIP/VLM
scores are biased and dependence violations destroy any claim of a rigorous
image information capacity from this simple formula.

### Stage C / style and model selection

Cross the best-performing prompt-writing strategies against all locally
qualified generators. Include a stronger reference model as a control. Rank
**Pareto trade-offs**, not a single beauty number: measured visual bit
agreement, recognisability, quality, speed, peak VRAM, portability and cost.

## Prompt-writing policy

The source hash MUST NOT be included in model messages. Send only the selected
bit-conditioned decisions with named feature IDs/scopes and the two alternatives.
Require the LLM to return JSON `{"prompt":"...", "negative_prompt":"..."}`.
The positive text must contain the literal selected phrase for each prompted
axis; keep both the raw model completion and canonicalized prompt for audit.
No rewriting can change an axis ID, bit assignment, selected feature or
canonical input identity. Categorical sampling is fixed per experiment.

Prompt variants should test concise tags, natural language, explicit scene
objects, attribute-binding phrases, negative terms (only for models supporting
negative prompts), feature ordering and repetitions. A free narrative is
allowed only if all selected instructions survive. Do not secretly drop
contradictions, rewrite the hash, or postselect images without recording all
attempts. Excessively long prompts are expected to be truncated by some
text encoders: record token lengths per tokenizer where possible.

The local OpenAI-compatible writer endpoint MUST be HTTP loopback; external
image APIs or hosted LLMs are deliberately not part of the default harness.
Run each writer in its own process/model endpoint as necessary. Persist model
revision, quantization, tokenizer/chat template, sampling seed, temperature,
latency and response. Resource usage of LLM writers should be profiled by the
same host/process monitor if available.

## Scoring and statistical methods

### Writer metrics

- JSON format validity, selected phrase coverage, opposite phrase leakage
  (literal checks are imperfect), prompt length/tokens, response latency;
- image-independent quality review: clarity, ability to bind attributes to
  correct object, scene coherence, ambiguity and unnatural phrasing;
- prompt diversity across hashes *without* changing bit meaning;
- budget retention and prompt truncation by the image engine tokenizer.

### Image metrics

1. **Primary:** blinded per-feature human or independently calibrated VLM
   binary answers, per-feature 0/1 confusion and confidence, balanced accuracy;
   measured against a chance baseline and with annotation inter-rater checks.
2. **Automatable proxy:** locally installed CLIP dual-caption comparison for
   selected/opposing choices (`score-clip`). CLIP semantic/textual priors can
   corrupt this metric; do not present it as exact bit-recovery rate. VQA/TIFA
   methods are future optional evaluators.
3. **Pixel diagnostics:** mean luminance, saturation, edge energy, exact SHA-256
   image file hash and 64-bit average hash. These cannot tell whether the image
   actually depicts a particular semantic feature.
4. **Counterfactuals:** same noise seed, flip one source bit, compare blinded
   attribute responses and thumbnail distances. A causal visual change is
   weaker than successful recovery of the input choice.
5. **Distinctiveness:** between-identity versus within-identity feature
   distances (LPIPS/DINOv2/CLIP, if locally available); nearest-neighbour
   retrieval at 16px and 32px; collision/confusion analysis for a large hash set.
6. **Runtime:** per-image cold/warm latency, GPU peak allocated and process
   memory where measurable, failure rates and OOMs, steps, resolution, energy
   only if actually instrumented by external tools.
7. **Robustness:** thumbnail crop/scale/compression/palette transforms with
   independent assessment. This is an identity usability study, *not* the
   robust watermark system and *not* recovery of exact secret data.

Report confidence intervals by bootstrap over **hash identities** (not image
pixels). Compare paired bit-flip trials within the same writer/model/seed and
avoid comparing 512px vs 1024px, different prompt truncation, or censored
OOM attempts as if identical conditions. Include baseline failure counts.

## Rendering ownership

Image diffusion models generate *source artwork*; ByteFables does not add a
competing effects, animation or final export engine. `host-assets` produces
SHA-256-pinned sprite assets with declarative FrameRudiments `layer` fragments,
and target IDs for its existing post-effects/effect graph. Full compositor,
colours, gradients, alpha, camera, transformations, animation and production
raster/video export are **FrameRudiments responsibilities**. Future native
FrameRudiments improvements should introduce reusable prompt-conditioned
image source generators and effect plugins for visual embellishments.

Neither the old `renderPixelAvatar` compatibility SVG function nor a raw
Diffusers `image.save` used as **unprocessed benchmark evidence** is a competing
production renderer. Capture raw model pixels for fair benchmarking; process
selected images through FrameRudiments only in a separately labelled downstream
presentation step. Do not score only embellished previews or let effects
change the independent source image benchmark.

## Safety / deployment

PUBLIC hashes only. Reject `ByteValue<'secret'>` at the API boundary; never
put wallet private keys, entropy, credentials or unpublished identifiers on
command lines or into generation model prompts. The python tool does not
accept any generic arbitrary secret file ingestion; its public hex is still
visible in process listings. No external HTTP hosts, automatic model downloads,
telemetry or nonlocal AI APIs are supported.

Model weights, tokenizers and prompt templates can be untrusted; pin files and
license conditions. Native checkpoint deserializers and Python packages may
execute code: run dedicated GPU workers under user-approved sandbox policies,
with workspace file and resource auditing. `use_safetensors=True` is a safer
loading preference, not a complete sandbox. Keep cached weights under the
model-owning project's ignored `models/` directory. Do not publish synthetic
illustrations as proof of key ownership or encode secret-backed avatar art.

## Implementation status

- **Implemented and CPU-tested:** TypeScript bit-feature ledger, three baseline
  prompt styles (plus Python baseline strategies), bit-flip fixtures, local
  loopback LLM caller, prompt provenance, local model config validation,
  explicit Diffusers runner, inference receipts, image/prompt diagnostics,
  optional offline CLIP evaluator, blinded-judgment importer, FrameRudiments
  image-asset handoff, local HTML gallery and report aggregation.
- **Not measured here:** real tiny LLM output quality, GPU diffusion results,
  actual image recognisability, bit accuracy, artwork uniqueness and
  FrameRudiments native host integration. These require installed model weights,
  GPU runtimes and independent assessment. Optional CLIP executor is untested
  without local Transformers weights and does not establish accuracy by itself.
- **Not promised:** mathematically reversible artistic images, undetectable
  watermarking, security authentication, error-correcting private-key archival.

## Example commands

```sh
npm ci --ignore-scripts
npm run check
python -m tools.hash_image_bench prepare \\
  --confirm-public --public-hex 000102030405060708090a0b0c0d0e0f101112131415161718191a1b1c1d1e1f \\
  --output _work/hash-image-01 --budgets 8,16,32 \\
  --strategies direct,structured,narrative --paired-bits 0,1,7,31

# Start any supported local OpenAI-compatible LLM separately, then:
python -m tools.hash_image_bench write-prompts --experiment _work/hash-image-01 \\
  --endpoint http://127.0.0.1:11434/v1/chat/completions \\
  --model qwen3:0.6b --strategies structured,narrative --max-calls 24

# Edit the JSON config so every model localPath names an actual, approved local checkpoint.
python -m tools.hash_image_bench render --experiment _work/hash-image-01 \\
  --models experiments/tiny-image-models.example.json --only-model sana-06b \\
  --only-writer qwen3:0.6b --only-budget 8 --repetitions 3 --max-jobs 48

# Remove dry-run by adding --execute. Local GPU and Diffusers must already exist.
python -m tools.hash_image_bench report --experiment _work/hash-image-01
python -m tools.hash_image_bench host-assets --experiment _work/hash-image-01
```

The `--execute` switch is deliberately required for GPU inference. The example
model list is only a **configuration template**; none of its paths exists here.
To run the full cross-product, set an explicit large `--max-jobs` and plan VRAM.
