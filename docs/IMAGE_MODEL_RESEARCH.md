# ByteFables — compact prompt writers and image generators (October 2026)

**Research status:** curated starting shortlist, not a performance ranking.
Upstream model capabilities, license conditions, quantized releases, model-card
revisions and the hardware environment must be checked immediately before a run.
A small denoiser/transformer weight count is not the total pipeline footprint.

## Local image generators

| Candidate | Published size/role | Why profile it | Practical caveat |
|---|---|---|---|
| [BK-SDM-Tiny](https://github.com/Nota-NetsPresso/BK-SDM) | 0.33B U-Net / ~0.50B total | Small classic latent diffusion baseline | Image fidelity and binding vary with noise steps |
| [PixArt-α 512](https://huggingface.co/PixArt-alpha/PixArt-XL-2-512x512) | ~0.6B DiT, plus text encoder/VAE | Lightweight transformer architecture | OpenRAIL model license; struggles with multi-object composition |
| [Sana 600M 512](https://huggingface.co/Efficient-Large-Model/Sana_600M_512px_diffusers) | ~0.59B core, plus Gemma encoder/VAE | Competitive efficient generator | Sana docs cite ~9GB for standard 0.6B setup; component licensing matters |
| [Segmind SSD-1B](https://github.com/segmind/SSD-1B) | ~1.3B distilled SDXL architecture | Stronger quality/latency comparison | Full model can demand much more VRAM than parameter count suggests |
| [FLUX.2 Klein 4B](https://bfl.ai/models/flux-2-klein) | 4B family, Apache-2.0 variants | Compact higher-quality control | Supplier lists ~8.4GB for one configuration, higher for another; investigate actual host |
| [SD v1.5 + LCM](https://huggingface.co/latent-consistency/lcm-lora-sdv1-5) | SD 1.5 class with fast sampler adapter | Timing/steps ablation | Requires compatible base and sampler; licensing and source revision |
| [Sana-1.5 1.6B](https://nvlabs.github.io/Sana/docs/sana/) | 1.6B backbone | Larger accuracy control | Official docs indicate ~12GB standard inference configuration |

### Prompt writers

- **Sub-billion:** [SmolLM2-360M](https://huggingface.co/HuggingFaceTB/SmolLM2-360M-Instruct), [Qwen3-0.6B](https://huggingface.co/Qwen/Qwen3-0.6B), [Qwen3.5-0.8B](https://huggingface.co/Qwen/Qwen3.5-0.8B), [Gemma 3 270M](https://deepmind.google/models/gemma/gemma-3/).
- **1–2B:** SmolLM2-1.7B-Instruct, Qwen3-1.7B, Qwen3.5-2B, Gemma 3 1B.
- **Larger compact control:** SmolLM3-3B, Qwen3.5-4B, optionally Phi-4-mini.
- **Baselines:** the original deterministic choice-list compositor, with
  direct, terse, narrative, hierarchical/structured, contrast-guarded and
  scene-focused styles; these are as important as model comparisons.

Record writer quantization, chat template, revision, sampling temperature,
max generated tokens and throughput. One model may need tokenizer-specific
JSON-mode guidance; do not interpret malformed output as image-model failure.

## Benchmark/evaluation precedents

- [TIFA (ICCV 2023)](https://openaccess.thecvf.com/content/ICCV2023/html/Hu_TIFA_Accurate_and_Interpretable_Text-to-Image_Faithfulness_Evaluation_with_Question_Answering_ICCV_2023_paper.html): VQA-based attribute and compositional faithfulness; useful for blind feature-level questions.
- [T2I-CompBench++ (TPAMI 2025)](https://pubmed.ncbi.nlm.nih.gov/40031217/): attribute binding, object/spatial relationships, numeracy and complex compositions; shows that prompt compliance and image quality require distinct measurements.
- [GenEval](https://github.com/djghosh13/geneval): object/colour/spatial evaluation, but doesn't establish arbitrary hash-bit information capacity.
- [Sana paper (ICLR 2025)](https://proceedings.iclr.cc/paper_files/paper/2025/hash/34345e243156da67605d4b63d71c8d98-Abstract-Conference.html): architecture-size, latency and image-fidelity trade-offs.
- [BK-SDM paper and model card](https://github.com/Nota-NetsPresso/BK-SDM/blob/main/MODEL_CARD.md): small-denoiser efficiency comparisons.

### Important research risks

1. **Visual conflict:** 256 binary adjectives imply 256 independent visual
   constraints. Small generators will ignore or conflict many constraints.
   Testing 8/16/32/64/128/256 budgets is necessary to measure saturation.
2. **Prompt position effects:** long prompts may be truncated, and front-loaded
   choices may have higher influence; shuffle group order under a frozen
   counterfactual experiment while retaining bit IDs.
3. **Language priors:** CLIP/VLM may favour one opposite even without an image.
   Calibrate caption priors and score balanced paired flips.
4. **Noise confounding:** identical inputs with different diffusion seeds can
   look more different than one-bit-flipped inputs. Run both common-noise and
   identity-seeded settings.
5. **Aesthetic versus information:** unusually pretty output needn't expose the
   source bit choices. Human blind evaluation and 16/32px retrieval are essential.
6. **Different native sizes:** evaluate a controlled common resolution where
   supported *and* native recommended profiles, reported separately.
7. **Model bias/sampling:** deterministic text or image decoding settings may
   reduce diversity while improving apparent feature agreement; include
   repeated seeds and track exact configurations.
8. **Licenses/privacy:** research weights may have use restrictions and require
   model-card approvals. Public node identities are the only permitted inputs.

## Execution guidance

The tiny image candidates span multiple Diffusers pipelines and model-specific
kwargs. Start with the dedicated optional GPU worker, perform one smoke render
per model using an 8-bit deterministic prompt, then increment the run matrix.
Pin locally downloaded model trees and external Python dependencies. The demo
config uses nonexistent placeholder absolute paths on purpose: there is no
silent network download or assumption the operator has GPU access.

Use frame-based host compositing for chosen identity art in FrameRudiments; raw
Diffusers PNGs exist solely as experimental evidence and must not be confused
with FrameRudiments production renders.
