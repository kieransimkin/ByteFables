"""Compare public fractal identity generators through FrameRudiments factories.

No Diffusers weights and no second rendering/effects engine. This is a STATIC
synthetic source experiment; FrameRudiments owns all compositing and effects.
"""
from __future__ import annotations

from hashlib import sha256
from pathlib import Path
import html
import json
import subprocess
import time

from .experiment import ROOT, VERSION, compute_image_diagnostics, digest, load, persist

FAMILIES = ('julia', 'burning-ship', 'ifs-fern', 'fbm')
MODES = ('avalanche', 'axis-isolated')


def _layer_for_case(case, experiment, family, size, quality):
    command = [
        'node', str(ROOT/'bin'/'bytefables.mjs'), 'fractal-layer', '--confirm-public',
        '--public-hex', case['sourcePublicHex'], '--namespace', experiment['namespace'],
        '--kind', experiment['kind'], '--family', family, '--quality', quality,
        '--bounds', f'0,0,{size},{size}', '--id', 'fractal-generator'
    ]
    run = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, timeout=15, check=False)
    if run.returncode:
        raise ValueError('Canonical TypeScript fractal planning failed; run npm run build')
    layer = json.loads(run.stdout)
    if layer.get('renderer') != 'bytefables-fractal-v1' or layer.get('type') != 'rudiment':
        raise ValueError('Unexpected ByteFables fractal layer plan')
    return layer


def _pair_metrics(original_path, changed_path):
    from PIL import Image, ImageChops, ImageStat
    with Image.open(original_path) as original, Image.open(changed_path) as changed:
        a,b = original.convert('RGB'),changed.convert('RGB')
        if a.size != b.size:raise ValueError('Cannot compare different image extents')
        difference=ImageChops.difference(a,b)
        histogram = difference.histogram()
        # Bytes changed across RGB channels, not evidence of which source bit is visible.
        changed_channels=sum(a.size[0]*a.size[1] - histogram[i*256] for i in range(3))
        means=ImageStat.Stat(difference).mean
        return {'channelChangeFraction':round(changed_channels/(a.width*a.height*3),5),
                'meanAbsoluteRgbDifference':round(sum(means)/(3*255),5)}


def _import_host_generator():
    try:
        from bytefables_framerudiments.fractals import FractalRenderer
    except ImportError as exc:
        raise RuntimeError('Install ByteFables FrameRudiments generator adapter into the local Python runtime: pip install -e integrations/framerudiments') from exc
    return FractalRenderer


def render_fractal_study(experiment_dir, *, families=FAMILIES, modes=MODES,
                         size=128, quality='draft', max_images=100):
    """Render/cross-check exact source-bit counterfactuals and hash-avalanche mode."""
    if not isinstance(families, (list,tuple)) or not families or any(f not in FAMILIES for f in families) or len(set(families)) != len(families):
        raise ValueError('Unknown or repeated fractal family')
    if not isinstance(modes,(list,tuple)) or not modes or any(m not in MODES for m in modes) or len(set(modes)) != len(modes):
        raise ValueError('Unknown or repeated fractal mode')
    if type(size) is not int or not 16 <= size <= 512 or size*size > 262144:
        raise ValueError('Public fractal benchmark size must be 16..512')
    if quality not in ('draft','standard') or not 1<=max_images<=2000:
        raise ValueError('Invalid quality or max-images limit')
    path=Path(experiment_dir).resolve()
    exp=load(path/'experiment.json')
    if exp.get('schema') != VERSION or not exp.get('cases'):
        raise ValueError('Invalid public experiment')
    count=len(exp['cases'])*len(families)*len(modes)
    if count>max_images:raise ValueError(f'{count} fractal frames exceeds max-images={max_images}')
    from PIL import Image
    Renderer=_import_host_generator()
    import inspect
    import PIL
    import sys
    source_path=Path(inspect.getsourcefile(Renderer))
    renderer_source_sha=sha256(source_path.read_bytes()).hexdigest()
    runtime_versions={'python':'.'.join(map(str,sys.version_info[:3])),
                      'pillow':PIL.__version__}
    case_layers={(case['caseId'],f):_layer_for_case(case,exp,f,size,quality)
                 for case in exp['cases'] for f in families}
    base_id=exp['cases'][0]['caseId']
    receipts=[]
    for mode in modes:
        for family in families:
            for case in exp['cases']:
                layer=case_layers[(case['caseId'],family)]
                config=dict(layer['style'])
                if mode=='axis-isolated':
                    # Experimental counterfactual only: preserve the unflipped
                    # fractal seed to measure separately the eight visible axes.
                    # Flipping any higher bit then has no effect by design.
                    config['seed_hex']=case_layers[(base_id,family)]['style']['seed_hex']
                source={'caseId':case['caseId'],'family':family,'seedMode':mode,'size':size,
                        'quality':quality,'style':config,
                        'rendererSourceSha256':renderer_source_sha}
                name=digest(source)[:24]
                target=path/'fractal'/'renders'/f'{name}.png'
                receipt_path=path/'fractal'/'renders'/f'{name}.json'
                if receipt_path.is_file():
                    item=load(receipt_path)
                    if not target.is_file() or sha256(target.read_bytes()).hexdigest()!=item.get('imageSha256'):
                        raise ValueError('Saved fractal image changed or disappeared')
                    receipts.append(item)
                    continue
                started=time.monotonic()
                image=Renderer((size,size),config).render(None)
                target.parent.mkdir(parents=True,exist_ok=True)
                image.save(target,format='PNG',optimize=False)
                image_sha=sha256(target.read_bytes()).hexdigest()
                diagnostics=compute_image_diagnostics(target)
                with Image.open(target) as im:
                    small=im.convert('RGB').resize((64,64))
                    histogram=small.getcolors(4096) or []
                dominant=max((entry[0] for entry in histogram), default=0)/4096
                warnings=[]
                if diagnostics['lumaStd']<.05:warnings.append('low-luminance-contrast')
                if diagnostics['edgeMean']<.02:warnings.append('low-spatial-detail')
                if dominant>.55:warnings.append('dominant-flat-colour')
                receipt={'schema':'bytefables.fractal-benchmark-result.v1','caseId':case['caseId'],
                         'flippedBit':case['flippedBit'],'family':family,'seedMode':mode,
                         'sourceIdentityDigestHex':case['digestHex'],'recipe':source,
                         'recipeSha256':sha256(json.dumps(source,sort_keys=True).encode()).hexdigest(),
                         'imageFile':str(target.relative_to(path)),'imageSha256':image_sha,
                         'elapsedSeconds':round(time.monotonic()-started,4),
                         'runtimeVersions':runtime_versions,
                         'metrics':{**diagnostics,'dominantColorFraction64':round(dominant,4)},
                         'visualQualityWarnings':warnings,
                         'claimsRecoverableBits':False,'generator':'FrameRudiments/bytefables-fractal-v1'}
                persist(receipt_path,receipt)
                receipts.append(receipt)
    by_key={(r['caseId'],r['family'],r['seedMode']):r for r in receipts}
    deltas=[]
    for mode in modes:
        for family in families:
            base=by_key[(base_id,family,mode)]
            for case in exp['cases'][1:]:
                other=by_key[(case['caseId'],family,mode)]
                delta=_pair_metrics(path/base['imageFile'],path/other['imageFile'])
                ah1=int(base['metrics']['perceptualAhash64'],16)
                ah2=int(other['metrics']['perceptualAhash64'],16)
                deltas.append({'family':family,'seedMode':mode,'flippedBit':case['flippedBit'],
                               'ahashHamming64':(ah1^ah2).bit_count(),**delta})
    report={'schema':'bytefables.fractal-benchmark-report.v1','publicOnly':True,
            'sourceExperimentId':exp['experimentId'],'images':len(receipts),
            'uniquePngSha256':len({r['imageSha256'] for r in receipts}),
            'receipts':receipts,'pairComparisons':deltas,
            'disclaimer':'Image differences/ahash are weak perceptual proxies, NOT recoverable hash bits. No diffusion model was executed.'}
    persist(path/'fractal'/'report.json',report)
    _write_gallery(path,report)
    return report


def _write_gallery(path,report):
    rows=[]
    for item in report['receipts']:
        url=item['imageFile'].removeprefix('fractal/')
        rows.append('<article><img loading="lazy" alt="Deterministic fractal sprite" src="'+html.escape(url,quote=True)+'">'
                    '<p>'+html.escape(item['family'])+' / '+html.escape(item['seedMode'])+' / '+html.escape(item['caseId'])+'</p>'
                    '<small>'+item['imageSha256'][:16]+'</small></article>')
    source='''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>ByteFables fractal counterfactuals</title>
    <style>body{font:15px system-ui;background:#121924;color:#edf4ff;padding:24px} main{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:16px} article{background:#263044;border-radius:12px;padding:12px} img{width:100%;image-rendering:pixelated}small{color:#abbacc}</style>
    <h1>Fractal-seeded public identities</h1><p>Rendered by ByteFables generators in FrameRudiments. Not key backups; no diffusion model used.</p><main>'''+''.join(rows)+'</main></html>'
    (path/'fractal'/'gallery.html').write_text(source,encoding='utf8')
