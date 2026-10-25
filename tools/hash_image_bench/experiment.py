"""Reproducible public hash -> opposing visual decisions -> prompts -> model jobs.

Requires only the Python standard library for preparation/prompt benchmarking.
Diffusers/PIL/torch are OPTIONAL and lazy-loaded by the render/evaluation paths.
Secrets MUST NOT be supplied. No remote model downloads or remote LLM endpoints.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import Request, urlopen
import hashlib
import json
import os
import re
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
VERSION = 'bytefables.hash-image-experiment.v1'
STRATEGIES = ('direct', 'narrative', 'structured', 'compact', 'scene', 'contrasts')
MAX_OUTPUT_TEXT = 32768


def stable_json(x):
    return json.dumps(x, sort_keys=True, ensure_ascii=True, separators=(',', ':'))


def digest(x):
    return sha256(stable_json(x).encode('utf8')).hexdigest()


def persist(path: Path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + '.tmp')
    tmp.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + '\n', encoding='utf8')
    tmp.replace(path)


def load(path):
    return json.loads(Path(path).read_text(encoding='utf8'))


def validate_public_hex(s):
    if not isinstance(s, str) or not re.fullmatch(r'(?:[0-9a-fA-F]{2}){1,512}', s):
        raise ValueError('Expected 1..512 byte PUBLIC hex without 0x prefix')
    return s.lower()


def bitplan(public_hex, namespace='danceflow', kind='node-id', *, node_executable='node'):
    """Canonical planning uses ByteFables TS, not a second inconsistent Python bit map."""
    public_hex = validate_public_hex(public_hex)
    cmd = [node_executable, str(ROOT / 'bin' / 'bytefables.mjs'), 'visual-features',
           '--confirm-public', '--public-hex', public_hex, '--namespace', namespace,
           '--kind', kind, '--prompt-bits', '1']
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=ROOT, timeout=15, check=False)
    if result.returncode:
        raise ValueError('ByteFables public feature planner failed (build first)')
    data = json.loads(result.stdout)
    if data.get('bitCount') != len(public_hex) * 4 or len(data.get('choices', [])) != data['bitCount']:
        raise ValueError('Malformed canonical feature plan')
    return {k: v for k, v in data.items() if k not in ('selectedFeatures', 'baselinePrompt', 'baselineStyle', 'promptBitBudget', 'claimsBitExactImage')}


def make_pair_hex(h: str, bit_index: int):
    h = validate_public_hex(h)
    b = bytearray.fromhex(h)
    if not 0 <= bit_index < len(b) * 8:
        raise ValueError('Pair bit index out of range')
    b[bit_index // 8] ^= 1 << (7 - (bit_index % 8))
    return b.hex()


def descriptor(features, *, strategy):
    """Simple deterministic prompt, no language model. True comparator baseline."""
    lines = [f"{a['scope']} {a['property']}: {a['selected']}" for a in features]
    if strategy == 'direct':
        return 'One original illustrated identity sculpture: ' + '; '.join(lines) + '. No letters or logos.'
    if strategy == 'compact':
        return 'Stylized identity sculpture, ' + ', '.join(a['selected'] for a in features) + ', no text.'
    if strategy == 'narrative':
        return 'Imagine a distinctive illustrated identity sculpture with these deliberate visual features: ' + '; '.join(lines) + '. Coherent scene, no writing.'
    if strategy == 'structured':
        return 'SUBJECT: original visual identity sculpture. FEATURES:\n' + '\n'.join('- ' + x for x in lines) + '\nNo text or logos.'
    if strategy == 'scene':
        return 'A singular sculpted identity emblem in an original environment. Main features: ' + '; '.join(x for x in lines if x.startswith('main subject')) + '. Supporting details: ' + '; '.join(x for x in lines if not x.startswith('main subject')) + '. No text.'
    if strategy == 'contrasts':
        return 'Identity sculpture with positive desired features: ' + '; '.join(lines) + '. These choices are deliberate and must not be inverted. No text.'
    raise ValueError('Unknown prompt strategy')


def _contains(text: str, phrase: str):
    """Literal lexical proxy only, not semantic or visual adherence."""
    return re.search(r'(?<![a-z])' + re.escape(phrase.lower()) + r'(?![a-z])', text.lower()) is not None


def audit_prompt(prompt, features):
    selected = [f for f in features if _contains(prompt, f['selected'])]
    absent = [f['featureId'] for f in features if not _contains(prompt, f['selected'])]
    inverted = [f['featureId'] for f in features if _contains(prompt, f['opposite'])]
    return {'selectedCount': len(features), 'literalCoverage': len(selected) / len(features) if features else None,
            'missingFeatureIds': absent, 'oppositePhrasePresent': inverted,
            'warning': 'Lexical diagnostics are NOT proof of correct semantic binding or image bit recovery.'}


def prepare(public_hex: str, output_dir, *, namespace='danceflow', kind='node-id',
            budgets=(8,16,32), strategies=('direct','narrative','structured'),
            paired_bits=(), node_executable='node'):
    """Construct a deterministic experiment matrix and baseline prompt candidates."""
    base = validate_public_hex(public_hex)
    if not budgets or not strategies:
        raise ValueError('Choose at least one feature budget and prompt strategy')
    if any(s not in STRATEGIES for s in strategies):
        raise ValueError('Unknown prompt strategy')
    if any(type(n) is not int or not 1 <= n <= len(base) * 4 for n in budgets):
        raise ValueError('Feature budgets must be 1..hash bits')
    case_values = [('original', base, None)]
    if len(paired_bits) > 32:
        raise ValueError('At most 32 counterfactual pairs per experiment')
    for index in paired_bits:
        if type(index) is not int or not 0 <= index < len(base)*4 or index in (row[2] for row in case_values):
            raise ValueError('Invalid or duplicate counterfactual bit')
        case_values.append((f'flip-{index:04d}', make_pair_hex(base,index), index))
    output_dir = Path(output_dir).resolve()
    if output_dir.exists() and (output_dir / 'experiment.json').exists():
        raise FileExistsError('Experiment already exists; use a new output directory')
    cases, candidates = [], []
    for case_name, h, flipped in case_values:
        plan = bitplan(h, namespace, kind, node_executable=node_executable)
        cases.append({'caseId': case_name, 'flippedBit': flipped, 'sourcePublicHex': h,
                      'digestHex': plan['identityDigestHex'], 'visualSeed': plan['visualSeed'],
                      'visualSeed64': plan['visualSeed64'],
                      'bitCount': plan['bitCount'], 'features': plan['choices']})
        for budget in budgets:
            selected = plan['choices'][:budget]
            for strategy in strategies:
                prompt = descriptor(selected, strategy=strategy)
                row = {'caseId': case_name, 'writerId': 'deterministic-baseline',
                       'strategy': strategy, 'bitBudget': budget, 'prompt': prompt,
                       'negativePrompt': '', 'features': selected,
                       'audit': audit_prompt(prompt, selected)}
                row['candidateId'] = digest({k: row[k] for k in ('caseId','writerId','strategy','bitBudget','prompt')})[:20]
                candidates.append(row)
    experiment = {
        'schema': VERSION, 'createdBy': 'ByteFables / public-only', 'namespace': namespace, 'kind': kind,
        'basePublicHex': base, 'hashBits': len(base)*4, 'axisSpec': 'bytefables.visual-bits.v1',
        'budgets': list(budgets), 'strategies': list(strategies), 'pairedBits': list(paired_bits),
        'cases': cases, 'candidates': candidates,
        'status': 'prompt-baseline-only',
        'guarantees': {'bitToChoiceMapping': 'lossless', 'promptImage': 'NOT reversible',
                       'modelFidelity': 'NOT measured', 'originalKeyExposure': 'PUBLIC INPUT ONLY'}
    }
    experiment['experimentId'] = digest({k: experiment[k] for k in ('schema','namespace','kind','basePublicHex','budgets','strategies','pairedBits')})[:20]
    persist(output_dir / 'experiment.json', experiment)
    return experiment


def _require_loopback(endpoint):
    parsed = urlparse(endpoint)
    if parsed.scheme != 'http' or parsed.hostname not in {'localhost','127.0.0.1','::1'}:
        raise ValueError('Only explicit HTTP loopback LLM endpoints are supported; no cloud hash/feature leaks')
    if parsed.username or parsed.password or parsed.fragment or parsed.query or not parsed.port:
        raise ValueError('Invalid or ambiguous LLM endpoint')
    if parsed.path not in ('/v1/chat/completions','/chat/completions'):
        raise ValueError('Expected an OpenAI-compatible local /v1/chat/completions endpoint')
    return endpoint


def local_llm_prompt(features, *, endpoint, model, strategy, seed, temperature=0.2, timeout=90):
    """Ask an LLM to compose only from binary choices. The source hash is never sent."""
    _require_loopback(endpoint)
    allowed = [{'id': f['featureId'], 'scope':f['scope'], 'property':f['property'],
                'required': f['selected'], 'forbidden':f['opposite']} for f in features]
    system = ("You compose image-generation prompts, not binary data. The feature decisions are fixed; "
              "never replace, invert or hallucinate them. Return a JSON object with string properties "
              "prompt and negative_prompt. Include EVERY required phrase literally in the POSITIVE prompt, "
              "bound it to its stated object scope, and omit every forbidden phrase from the positive prompt. "
              "Do not invent signs, words, QR codes or text. Preserve a coherent visual composition. "
              "The requester supplies public semantic choices, not the underlying source hash.")
    messages = [{'role': 'system', 'content': system}, {'role':'user', 'content':stable_json({
        'task':'Compose a vivid visual identity scene', 'promptStyle':strategy, 'choices':allowed,
        'constraints':['Avoid quoting bit values or hexadecimal strings', 'No letters or logos',
                       'Make main subject dominant', 'For micro motifs preserve numbered scope',
                       'Return strict JSON with prompt, negative_prompt only']})}]
    payload = {'model': model, 'messages': messages, 'stream':False, 'temperature':temperature,
               'seed':seed, 'max_tokens':min(2048, max(512, len(features)*18))}
    req = Request(endpoint, stable_json(payload).encode('utf8'),
                  {'Content-Type':'application/json'}, method='POST')
    t = time.monotonic()
    with urlopen(req, timeout=timeout) as response:
        body = response.read(MAX_OUTPUT_TEXT + 1)
    if len(body) > MAX_OUTPUT_TEXT:
        raise ValueError('Model returned oversized response')
    reply = json.loads(body)
    raw = reply['choices'][0]['message']['content']
    if not isinstance(raw, str) or len(raw) > MAX_OUTPUT_TEXT:
        raise ValueError('Unexpected model output')
    parsed_ok=False
    try:
        obj=json.loads(raw.strip().removeprefix('```json').removeprefix('```').removesuffix('```').strip())
        positive=obj['prompt']; negative=obj.get('negative_prompt','')
        parsed_ok=True
    except (ValueError, KeyError, TypeError):
        positive,negative=raw,''  # Save unstructured failures to measure writer compliance.
    if not isinstance(positive,str) or not isinstance(negative,str):
        raise ValueError('LLM did not return text prompt')
    return {'prompt':positive[:MAX_OUTPUT_TEXT], 'negativePrompt':negative[:MAX_OUTPUT_TEXT],
            'rawResponse':raw, 'durationMs':round((time.monotonic()-t)*1000,2),
            'parseableJson':parsed_ok}


def add_llm_candidates(path, *, endpoint, model, strategies=('narrative','structured'),
                       seed=73, temperature=0.2, max_calls=48):
    experiment=load(Path(path)/'experiment.json')
    if experiment['schema'] != VERSION: raise ValueError('Unrecognised experiment schema')
    base=[x for x in experiment['candidates'] if x['writerId']=='deterministic-baseline']
    rows=[]
    for src in base:
        if src['strategy'] not in strategies:continue
        if len(rows)>=max_calls:break
        t=local_llm_prompt(src['features'],endpoint=endpoint,model=model,
                           strategy=src['strategy'],seed=seed,temperature=temperature)
        row={k:src[k] for k in ('caseId','strategy','bitBudget','features')}
        row.update({'writerId':model,'writerSeed':seed,'temperature':temperature,**t,
                    'audit':audit_prompt(t['prompt'], src['features'])})
        row['candidateId']=digest({k:row[k] for k in ('caseId','strategy','bitBudget','writerId','prompt')})[:20]
        rows.append(row)
    if not rows:raise ValueError('No matching baseline candidates for selected strategies')
    existing={r['candidateId']:r for r in experiment['candidates']}
    existing.update({r['candidateId']:r for r in rows})
    experiment['candidates']=list(existing.values())
    experiment['status']='llm-prompts-created; images-not-yet-generated'
    persist(Path(path)/'experiment.json', experiment)
    return rows


def validate_model_file(path, *, require_files=True):
    """A pinned local path is mandatory; model names are metadata, never downloads."""
    raw = load(path)
    if not isinstance(raw, dict) or not isinstance(raw.get('models'), list) or not raw['models']:
        raise ValueError('Expected models JSON containing a nonempty models array')
    models=[]
    ids=set()
    for entry in raw['models']:
        if not isinstance(entry, dict) or set(entry)-{'id','localPath','revision','steps','guidance','width','height',
                                                 'device','dtype','negativePrompt','notes','family'}:
            raise ValueError('Unknown image model configuration field')
        if not isinstance(entry.get('id'),str) or not re.fullmatch('[a-z0-9][a-z0-9_-]{0,63}',entry['id']) or entry['id'] in ids:
            raise ValueError('Duplicate or invalid image model ID')
        ids.add(entry['id'])
        p=entry.get('localPath')
        if not isinstance(p,str) or not os.path.isabs(p):
            raise ValueError('Model localPath must be an absolute directory; no downloads allowed')
        if require_files and not (Path(p).is_dir() and (Path(p)/'model_index.json').is_file()):
            raise ValueError('Expected pre-downloaded Diffusers pipeline with model_index.json')
        for k,lo,hi in [('steps',1,150),('width',128,2048),('height',128,2048)]:
            if not isinstance(entry.get(k),int) or not lo<=entry[k]<=hi: raise ValueError(f'Invalid {k}')
        if entry['width']%8 or entry['height']%8: raise ValueError('Image dimensions must be multiples of eight')
        if type(entry.get('guidance')) not in (float,int) or not 0<=entry['guidance']<=30:
            raise ValueError('Invalid guidance scale')
        if entry.get('device','cuda') not in ('cuda','cpu','mps'):raise ValueError('Unknown device')
        if entry.get('dtype','float16') not in ('float16','bfloat16','float32'):raise ValueError('Unknown dtype')
        if entry.get('negativePrompt',True) not in (True,False):raise ValueError('Invalid negativePrompt flag')
        models.append(entry)
    return models


def compute_image_diagnostics(path):
    """Low-cost pixel indicators, not a visual-language model or bit accuracy score."""
    try:
        from PIL import Image, ImageFilter, ImageStat
    except ImportError as exc:
        raise RuntimeError('Pillow is required to score image pixel diagnostics') from exc
    with Image.open(path) as im:
        im=im.convert('RGB')
        reduced=im.resize((128,128))
        hsv=reduced.convert('HSV')
        value=hsv.getchannel('V')
        saturation=hsv.getchannel('S')
        lum=reduced.convert('L')
        edge=lum.filter(ImageFilter.FIND_EDGES)
        stat_l=ImageStat.Stat(lum)
        stat_s=ImageStat.Stat(saturation)
        stat_e=ImageStat.Stat(edge)
        small=lum.resize((8,8))
        bits=''.join('1' if x>=sum(small.getdata())/64 else '0' for x in small.getdata())
        return {'lumaMean':round(stat_l.mean[0]/255,4),
                'lumaStd':round(stat_l.stddev[0]/255,4),
                'saturationMean':round(stat_s.mean[0]/255,4),
                'edgeMean':round(stat_e.mean[0]/255,4),
                'perceptualAhash64':f'{int(bits,2):016x}',
                'note':'Diagnostic proxies only, NOT verified compliance with semantic hash bits'}


def render_local_models(experiment_dir, models_path, *, execute=False, max_jobs=48,
                        repetitions=2, seed_policy='paired', allow_cpu=False, only_model=None,
                        only_writer=None, only_strategy=None, only_budget=None):
    """Controlled full writer x generator x seed crossing. Downloads never occur."""
    directory=Path(experiment_dir)
    experiment=load(directory/'experiment.json')
    if experiment.get('schema')!=VERSION:raise ValueError('Unrecognized experiment')
    models=validate_model_file(models_path, require_files=execute)
    if only_model:models=[x for x in models if x['id']==only_model]
    if not models:raise ValueError('No selected local models')
    if not 1<=repetitions<=32 or not 1<=max_jobs<=100000:raise ValueError('Invalid job/repetition bounds')
    if seed_policy not in ('paired','identity'):raise ValueError('Unknown seed policy')
    jobs=[]
    for candidate in experiment['candidates']:
        if only_writer is not None and candidate['writerId'] != only_writer:continue
        if only_strategy is not None and candidate['strategy'] != only_strategy:continue
        if only_budget is not None and candidate['bitBudget'] != only_budget:continue
        for model in models:
            for repeat in range(repetitions):
                case=next(x for x in experiment['cases'] if x['caseId']==candidate['caseId'])
                # Paired policy holds diffusion noise seed fixed across all hashes and prompt writers.
                seed=int(digest({'exp': experiment['experimentId'], 'repeat':repeat})[:16],16) if seed_policy=='paired' else (
                    int(case['visualSeed64'])+repeat) % (2**64)
                job={'jobId':digest({'candidate':candidate['candidateId'], 'model':model['id'],
                                     'seed':seed, 'repeat':repeat})[:24],
                     'caseId':candidate['caseId'], 'candidateId':candidate['candidateId'],
                     'writerId':candidate['writerId'], 'strategy':candidate['strategy'],
                     'bitBudget':candidate['bitBudget'], 'imageModel':model['id'],
                     'repeat':repeat,'seed':seed,'seedPolicy':seed_policy}
                jobs.append((job,model,candidate))
    if len(jobs)>max_jobs:raise ValueError(f'Requested {len(jobs)} model inference jobs exceeds --max-jobs {max_jobs}')
    if not execute:
        return {'status':'dry-run', 'jobCount':len(jobs), 'models':[m['id'] for m in models],
                'jobs':[j for j,_,_ in jobs]}
    try:
        import torch
        from diffusers import DiffusionPipeline
    except ImportError as exc:
        raise RuntimeError('Install PyTorch and diffusers explicitly in a dedicated model environment') from exc
    report=[]
    for model in models:
        device=model.get('device','cuda')
        if device=='cpu' and not allow_cpu:
            raise ValueError('Explicit --allow-cpu required; CPU diffusion inference may be extremely slow')
        if device=='cuda' and not torch.cuda.is_available():
            raise RuntimeError('CUDA not available; no fallback or simulated results')
        dtype={'float16':torch.float16,'bfloat16':torch.bfloat16,'float32':torch.float32}[model.get('dtype','float16')]
        # The path must point to existing local weights. Never fetch Hub metadata or execute remote code.
        pipeline=DiffusionPipeline.from_pretrained(model['localPath'],local_files_only=True,
                    torch_dtype=dtype, use_safetensors=True)
        pipeline.to(device)
        for job,cfg,candidate in jobs:
            if cfg['id']!=model['id']:continue
            receipt=directory/'renders'/f"{job['jobId']}.json"
            if receipt.exists():
                report.append(load(receipt));continue
            image_path=directory/'renders'/f"{job['jobId']}.png"
            inputs={'prompt':candidate['prompt'], 'width':cfg['width'],'height':cfg['height'],
                    'guidance_scale':cfg['guidance'],'num_inference_steps':cfg['steps'],
                    'generator':torch.Generator(device=device).manual_seed(job['seed'])}
            if cfg.get('negativePrompt',True) and candidate.get('negativePrompt'):
                inputs['negative_prompt']=candidate['negativePrompt']
            token_audit={}
            # Record possible prompt truncation. A model's several tokenizers may have different caps.
            for tokenizer_name in ('tokenizer','tokenizer_2','tokenizer_3'):
                tokenizer=getattr(pipeline,tokenizer_name,None)
                if tokenizer is None:continue
                try:
                    used=len(tokenizer(candidate['prompt'],truncation=False)['input_ids'])
                    limit=getattr(tokenizer,'model_max_length',None)
                    token_audit[tokenizer_name]={'tokens':used,'advertisedLimit':limit if isinstance(limit,int) and limit<1000000 else None,
                        'possibleTruncation':bool(isinstance(limit,int) and limit<1000000 and used>limit)}
                except (TypeError,ValueError,AttributeError):
                    token_audit[tokenizer_name]={'status':'unavailable'}
            row={**job,'checkpointPath':cfg['localPath'],'checkpointRevisionClaim':cfg.get('revision','unverified'),
                 'runtimeVersions':{'torch':torch.__version__},'promptTokenAudit':token_audit,
                 'inferenceSettings':{'width':cfg['width'],'height':cfg['height'],
                                      'steps':cfg['steps'],'guidance':cfg['guidance'],
                                      'dtype':model.get('dtype','float16'),'device':device},
                 'promptSha256':sha256(candidate['prompt'].encode('utf8')).hexdigest()}
            try:
                if device=='cuda':torch.cuda.reset_peak_memory_stats()
                begin=time.monotonic()
                result=pipeline(**inputs)
                image=result.images[0]
                image_path.parent.mkdir(parents=True,exist_ok=True)
                image.save(image_path, format='PNG')
                row.update({'status':'completed','elapsedSeconds':round(time.monotonic()-begin,3),
                            'imageFile':str(image_path.relative_to(directory)),
                            'imageSha256':sha256(image_path.read_bytes()).hexdigest(),
                            'metrics':compute_image_diagnostics(image_path)})
                if device=='cuda':row['peakTorchAllocatedBytes']=torch.cuda.max_memory_allocated()
            except (RuntimeError,ValueError,TypeError,OSError) as exc:
                row.update({'status':'failed', 'errorType':type(exc).__name__,
                            'errorNote':str(exc)[:160]})
                image_path.unlink(missing_ok=True)
            persist(receipt,row)
            report.append(row)
        del pipeline
        if device=='cuda':torch.cuda.empty_cache()
    return {'status':'finished','jobs':report}


def assess_judgments(experiment, receipts, decisions):
    """Score independently supplied BLIND image-only binary observations."""
    by_candidate={r['candidateId']:r for r in experiment['candidates']}
    by_job={r['jobId']:r for r in receipts if r.get('status')=='completed'}
    correct=total=0
    per_model={}
    for row in decisions:
        if not isinstance(row,dict) or row.get('jobId') not in by_job or not isinstance(row.get('answers'),dict):
            raise ValueError('Bad blind-judgment record or unknown completed job')
        job=by_job[row['jobId']]
        truth={str(f['bitIndex']):f['bit'] for f in by_candidate[job['candidateId']]['features']}
        group=per_model.setdefault((job['imageModel'],job['writerId'],job['strategy'],job['bitBudget']),[0,0])
        for k,v in row['answers'].items():
            if k not in truth or type(v) is not int or v not in (0,1):
                raise ValueError('Answer must be a 0/1 observation for an explicitly prompted bit')
            success=int(v==truth[k]);correct+=success;total+=1;group[0]+=success;group[1]+=1
    return {'correct':correct,'assessed':total,'bitAccuracy':correct/total if total else None,
            'byCondition':[{'imageModel':a,'writer':b,'strategy':c,'bitBudget':d,
                            'correct':v[0],'assessed':v[1], 'accuracy':v[0]/v[1]} for (a,b,c,d),v in sorted(per_model.items())]}


def _hamming16(a, b):
    return (int(a, 16) ^ int(b, 16)).bit_count()


def report_experiment(path, *, judgments_path=None):
    directory=Path(path)
    experiment=load(directory/'experiment.json')
    candidates=experiment['candidates']
    receipts=[load(p) for p in sorted((directory/'renders').glob('*.json'))] if (directory/'renders').exists() else []
    by_candidate={c['candidateId']:c for c in candidates}
    groups={}
    for c in candidates:
        key=(c['writerId'],c['strategy'],c['bitBudget'])
        group=groups.setdefault(key,{'count':0,'cover':0.0,'contradictions':0,
                                      'parseErrors':0,'promptChars':0,'writerElapsedMs':0})
        group['count']+=1;group['cover']+=c['audit']['literalCoverage']
        group['contradictions']+=len(c['audit']['oppositePhrasePresent'])
        group['promptChars']+=len(c['prompt'])
        group['writerElapsedMs']+=c.get('durationMs',0)
        if c.get('parseableJson') is False:group['parseErrors']+=1
    img_groups={}
    completed=[]
    for r in receipts:
        key=(r['imageModel'],r['writerId'],r['strategy'],r['bitBudget'])
        group=img_groups.setdefault(key,{'attempts':0,'successful':0,'seconds':[],
                                         'peakGpuBytes':[],'luma':[],'saturation':[],'edges':[]})
        group['attempts']+=1
        if r.get('status')!='completed':continue
        completed.append(r)
        group['successful']+=1
        group['seconds'].append(r['elapsedSeconds'])
        if 'peakTorchAllocatedBytes' in r:group['peakGpuBytes'].append(r['peakTorchAllocatedBytes'])
        for field,key2 in (('lumaMean','luma'),('saturationMean','saturation'),('edgeMean','edges')):
            if field in r.get('metrics',{}):group[key2].append(r['metrics'][field])
    paired=[]
    original={(r['candidateId'],r['imageModel'],r['seed']):r for r in completed if r['caseId']=='original'}
    # Compare counterfactual image with same model, prompt writer, strategy, budget and seed.
    for r in completed:
        if not r['caseId'].startswith('flip-'):continue
        cand=by_candidate[r['candidateId']]
        original_candidate=next((c for c in candidates if c['caseId']=='original' and
            (c['writerId'],c['strategy'],c['bitBudget']) ==
            (cand['writerId'],cand['strategy'],cand['bitBudget'])),None)
        if original_candidate is None:continue
        first=original.get((original_candidate['candidateId'],r['imageModel'],r['seed']))
        if first and 'perceptualAhash64' in first.get('metrics',{}) and 'perceptualAhash64' in r.get('metrics',{}):
            paired.append({'flipBit':int(r['caseId'][5:]),'writer':r['writerId'],
                           'model':r['imageModel'],'strategy':r['strategy'],
                           'budget':r['bitBudget'],'seed':r['seed'],
                           'aHashHamming':_hamming16(first['metrics']['perceptualAhash64'],
                                                  r['metrics']['perceptualAhash64']),
                           'warning':'Image difference is NOT evidence that the flipped bit can be recognised.'})
    mean=lambda xs:round(sum(xs)/len(xs),4) if xs else None
    result={'experimentId':experiment['experimentId'],'schema':VERSION,
            'promptCandidates':len(candidates),'renderAttempts':len(receipts),
            'completedImages':len(completed),
            'promptConditions':[{'writer':a,'strategy':b,'bitBudget':c,'count':v['count'],
                                 'literalCoverageMean':mean([v['cover']/v['count']]),
                                 'contradictions':v['contradictions'],
                                 'meanPromptCharacters':round(v['promptChars']/v['count']),
                                 'meanWriterDurationMs':mean([v['writerElapsedMs']/v['count']]),
                                 'jsonParseFailures':v['parseErrors']}
                                for (a,b,c),v in sorted(groups.items())],
            'imageConditions':[{'imageModel':a,'writer':b,'strategy':c,'bitBudget':d,
                                 'attempts':v['attempts'],'completed':v['successful'],
                                 'meanSeconds':mean(v['seconds']),
                                 'maxGpuMemoryBytes':max(v['peakGpuBytes'],default=None),
                                 'meanLuma':mean(v['luma']),'meanSaturation':mean(v['saturation']),
                                 'meanEdgeResponse':mean(v['edges'])}
                                for (a,b,c,d),v in sorted(img_groups.items())],
            'pairedBitFlipDiagnostics':paired,
            'visualMetricsAreProxies':True,
            'imageSemanticBitAccuracy':'unmeasured - supply independent blinded image observations',
            'modelComparison': 'Unmeasured until inference succeeds and independent assessments are provided'}
    score_dir=directory/'scores'
    if score_dir.exists():
        scores=[load(x) for x in sorted(score_dir.glob('*.clip.json'))]
        if scores:
            by_group={}
            for scored in scores:
                r=next((v for v in completed if v['jobId']==scored['jobId']),None)
                if r is None:continue
                key=(r['imageModel'],r['writerId'],r['strategy'],r['bitBudget'])
                g=by_group.setdefault(key,[0,0]);g[0]+=scored['correct'];g[1]+=scored['assessed']
            result['clipProxy']=[{'imageModel':a,'writer':b,'strategy':c,'bitBudget':d,
                                   'correct':v[0],'assessed':v[1],
                                   'unadjustedAgreement':v[0]/v[1]}
                                  for (a,b,c,d),v in sorted(by_group.items()) if v[1]]
            result['clipWarning']='CLIP caption-comparison scores can be biased; not proof of recoverable hash bits.'
    if judgments_path:
        rows=[json.loads(line) for line in Path(judgments_path).read_text().splitlines() if line.strip()]
        result['blindJudgments']=assess_judgments(experiment,receipts,rows)
    persist(directory/'report.json',result)
    _write_gallery(directory,experiment,completed)
    return result


def _write_gallery(directory, experiment, completed):
    from html import escape
    by_candidate={c['candidateId']:c for c in experiment['candidates']}
    blocks=[]
    for r in completed[:300]:
        c=by_candidate[r['candidateId']]
        file=r['imageFile']
        if not file.startswith('renders/') or not file.endswith('.png'):
            continue
        blocks.append('<article><img loading="lazy" src="'+escape(file,quote=True)+'" alt="Generated image" />'
                      +'<h3>'+escape(r['imageModel'])+' · '+escape(c['writerId'])+'</h3>'
                      +'<p>'+escape(c['strategy'])+' / '+str(c['bitBudget'])+' bits / seed '+str(r['seed'])+'</p>'
                      +'<details><summary>View exact prompt</summary><pre>'+escape(c['prompt'])+'</pre></details></article>')
    body='<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width">'
    body+='<title>ByteFables local image benchmark</title><style>body{font:15px system-ui;background:#0d1320;color:#e9edf3;padding:24px}'
    body+='main{display:grid;grid-template-columns:repeat(auto-fill,minmax(220px,1fr));gap:18px}'
    body+='article{background:#182435;padding:12px;border-radius:12px}img{max-width:100%;height:auto}pre{white-space:pre-wrap}'
    body+='summary{cursor:pointer}p{color:#9babca}</style>'
    body+='<h1>ByteFables image experiment</h1><p>Experimental PUBLIC hash art; NOT a lossless hash encoding.</p>'
    body+='<main>'+''.join(blocks)+'</main></html>'
    (directory/'gallery.html').write_text(body,encoding='utf8')


def evaluate_local_clip(experiment_dir, *, model_path, device='cpu', max_images=48, max_bits=32):
    """Exploratory zero-shot two-choice visual contrast, not verified decoded hash bits.

    Uses a separate locally installed CLIP checkpoint. No text/image exfiltration.
    Calibrate with human labels and bit-flip pairs; CLIP itself has language priors.
    """
    path=Path(model_path)
    if not path.is_absolute() or not path.is_dir():
        raise ValueError('CLIP model path must be an existing absolute directory')
    if device not in ('cpu','cuda','mps') or not 1<=max_images<=10000 or not 1<=max_bits<=512:
        raise ValueError('Bad evaluator limits')
    try:
        import torch
        from transformers import CLIPModel, CLIPProcessor
        from PIL import Image
    except ImportError as exc:
        raise RuntimeError('Requires local transformers, torch and Pillow; no auto-install') from exc
    experiment_dir=Path(experiment_dir)
    exp=load(experiment_dir/'experiment.json')
    candidates={x['candidateId']:x for x in exp['candidates']}
    receipts=[load(x) for x in sorted((experiment_dir/'renders').glob('*.json'))]
    receipts=[x for x in receipts if x.get('status')=='completed'][:max_images]
    model=CLIPModel.from_pretrained(str(path),local_files_only=True,use_safetensors=True).to(device)
    processor=CLIPProcessor.from_pretrained(str(path),local_files_only=True)
    model.eval()
    output=[]
    for receipt in receipts:
        candidate=candidates[receipt['candidateId']]
        axes=candidate['features'][:max_bits]
        captions=[]
        for f in axes:
            captions.append(f"An illustration with {f['scope']} having {f['zero']} {f['property']}.")
            captions.append(f"An illustration with {f['scope']} having {f['one']} {f['property']}.")
        with torch.inference_mode():
            text_vecs=[]
            for start in range(0,len(captions),16):
                tok=processor(text=captions[start:start+16],padding=True,truncation=True,return_tensors='pt')
                feat=model.get_text_features(**{k:v.to(device) for k,v in tok.items()})
                if hasattr(feat,'pooler_output'):feat=feat.pooler_output
                text_vecs.append(feat)
            text_vecs=torch.cat(text_vecs,dim=0)
            text_vecs=torch.nn.functional.normalize(text_vecs,dim=-1)
            with Image.open(experiment_dir / receipt['imageFile']) as opened:
                image=opened.convert('RGB')
                pixel=processor(images=image,return_tensors='pt')['pixel_values'].to(device)
            image_feature=model.get_image_features(pixel_values=pixel)
            if hasattr(image_feature,'pooler_output'):image_feature=image_feature.pooler_output
            image_feature=torch.nn.functional.normalize(image_feature,dim=-1)
            similarities=(image_feature @ text_vecs.T).detach().cpu().flatten().tolist()
        judgments=[]
        for i,f in enumerate(axes):
            s0,s1=similarities[2*i:2*i+2]
            predicted=int(s1>s0)
            judgments.append({'bitIndex':f['bitIndex'],'expected':f['bit'],'predicted':predicted,
                              'correct':bool(predicted==f['bit']),'similarity0':round(s0,5),
                              'similarity1':round(s1,5),'signedMargin':round((s1-s0)*(1 if f['bit'] else -1),5)})
        scored={'jobId':receipt['jobId'],'modelPath':str(path),'evaluator':'CLIP dual-caption contrast',
                'assessed':len(judgments),'correct':sum(x['correct'] for x in judgments),
                'accuracy':sum(x['correct'] for x in judgments)/len(judgments) if judgments else None,
                'biasWarning':'Model-dependent proxy. Calibrate on human labels, paired flips, and shuffled controls; NOT proof of 1-bit recovery.',
                'judgments':judgments}
        persist(experiment_dir/'scores'/f"{receipt['jobId']}.clip.json",scored)
        output.append(scored)
    return {'images':len(output),'modelPath':str(path),'scores':output}


def export_framerudiments_assets(experiment_dir, *, bounds=(0,0,512,512)):
    """Produce checksum-pinned image assets and layer fragments for FrameRudiments.

    ByteFables never adds image post-processing, effects or a second renderer.
    The host owns import, compositing, effects, output quality and final rendering.
    """
    path=Path(experiment_dir)
    receipts=[load(f) for f in sorted((path/'renders').glob('*.json'))] if (path/'renders').exists() else []
    if len(bounds)!=4 or not all(type(v) is int and 0<=v<=8192 for v in bounds) or bounds[2]<=bounds[0] or bounds[3]<=bounds[1]:
        raise ValueError('Invalid host bounds')
    out=[]
    for r in receipts:
        if r.get('status')!='completed':continue
        image_path=(path/r['imageFile']).resolve()
        if not image_path.is_relative_to(path.resolve()) or not image_path.is_file():
            raise ValueError('Image receipt points outside experiment or missing file')
        current=sha256(image_path.read_bytes()).hexdigest()
        if current!=r['imageSha256']:
            raise ValueError('Rendered artifact hash changed; refuse host handoff')
        out.append({'jobId':r['jobId'],'sourceImage':str(image_path),'sha256':current,
                    'host':'FrameRudiments','layerFragment':{
                      'id':'bytefables-'+r['jobId'],'type':'sprite',
                      'asset':{'path':str(image_path),'sha256':current},
                      'center':[(bounds[0]+bounds[2])/2,(bounds[1]+bounds[3])/2],
                      'width':bounds[2]-bounds[0], 'bounds':list(bounds)},
                    'effectsTarget':'layer:bytefables-'+r['jobId']})
    record={'schema':'bytefables.image-to-framerudiments.v1','publicOnly':True,
            'renderEngine':'framerudiments','assets':out,
            'note':'Layer fragments must be integrated into a valid host project; no independent ByteFables image effect stack.'}
    persist(path/'framerudiments-assets.json',record)
    return record
