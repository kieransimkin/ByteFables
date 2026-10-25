"""EXPERIMENTAL colored-noise inputs for eligible LOCAL Stable Diffusion pipelines.

This alters the trained Gaussian noise prior. It is not a proven improvement,
not a secret encoder, and not asserted deterministic across torch/GPU versions.
Only a controlled A/B experiment can justify further use.
"""
from __future__ import annotations

import math


def spectral_fractal_latents(seed, shape, *, beta=1.0, mix=0.25):
    """Return float32 CPU latents from seeded Gaussian + normalized 1/f^beta.

    The *same* initial white noise underlies both branches to make controlled
    comparisons. This does NOT preserve iid Gaussian covariance when mix > 0.
    """
    if (type(seed) is not int or seed < 0 or seed >= 2**64 or
            not isinstance(shape,tuple) or len(shape)!=4 or shape[0]!=1 or
            any(type(n) is not int or not 1<=n<=1024 for n in shape) or
            shape[1]>32 or shape[2]<8 or shape[3]<8 or
            math.prod(shape)>4194304 or
            type(beta) not in (float,int) or not math.isfinite(beta) or not 0<=beta<=3 or
            type(mix) not in (float,int) or not math.isfinite(mix) or not 0<=mix<=0.8):
        raise ValueError('Invalid bounded fractal noise recipe')
    try:
        import torch
    except ImportError as exc:
        raise RuntimeError('Optional torch required for spectral fractal-noise experiment') from exc
    generator=torch.Generator(device='cpu').manual_seed(seed % (2**63))
    white=torch.randn(shape,generator=generator,dtype=torch.float32,device='cpu')
    if mix==0:return white
    fy=torch.fft.fftfreq(shape[-2]).view(-1,1)
    fx=torch.fft.fftfreq(shape[-1]).view(1,-1)
    radius=torch.sqrt(fx.square()+fy.square())
    cutoff=max(1/shape[-2],1/shape[-1])
    spectrum=radius.clamp_min(cutoff).pow(-beta/2)
    spectrum[0,0]=0  # no DC spike
    colored=torch.fft.ifft2(torch.fft.fft2(white)*spectrum).real
    centered=colored-colored.mean(dim=(-2,-1),keepdim=True)
    unit=centered/centered.std(dim=(-2,-1),keepdim=True).clamp_min(1e-5)
    blended=(1-mix)*white + mix*unit
    # Explicit standardisation maintains overall magnitude, not independence.
    blended=(blended-blended.mean(dim=(-2,-1),keepdim=True)) / blended.std(dim=(-2,-1),keepdim=True).clamp_min(1e-5)
    return blended


def inject_fractal_latents(pipeline, cfg, inputs, job, *, beta, mix, device, dtype):
    """For audited classic SD/SDXL text2img only; fail closed for other models."""
    from inspect import signature
    if cfg.get('family') not in ('stable-diffusion','stable-diffusion-xl'):
        raise ValueError('Fractal latent injection currently supported only in SD/SDXL text2img research profiles')
    if not hasattr(pipeline,'unet') or not hasattr(pipeline,'vae_scale_factor') or not hasattr(pipeline,'scheduler'):
        raise ValueError('Pipeline lacks audited SD latent shape metadata')
    if 'latents' not in signature(pipeline.__call__).parameters:
        raise ValueError('Diffusers pipeline does not accept a latents argument')
    scale=pipeline.vae_scale_factor
    channels=pipeline.unet.config.in_channels
    w,h=cfg['width'],cfg['height']
    if type(scale) is not int or not 1<=scale<=32 or w%scale or h%scale:
        raise ValueError('Cannot safely derive pipeline latent dimensions')
    shape=(1,channels,h//scale,w//scale)
    # Pipeline scales by init_noise_sigma itself. Do not apply it here.
    noise=spectral_fractal_latents(job['seed'],shape,beta=beta,mix=mix)
    inputs['latents']=noise.to(device=device,dtype=dtype)
    return {'shape':list(shape),'beta':beta,'mix':mix,
            'warning':'Correlated initial noise departs from the diffusion training prior; no quality guarantee'}
