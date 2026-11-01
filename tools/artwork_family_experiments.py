"""A/B distinctiveness experiments for versioned artwork remediation candidates."""
from __future__ import annotations

import csv
import hashlib
import json
import math
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

from bytefables_framerudiments.artwork import ArtworkRenderer, BRIDGE
from bytefables_framerudiments.artwork_remediation import RemediationArtworkRenderer, PROFILE as CANDIDATE_PROFILE, SUPPORTED_FAMILIES
from tools.artwork_distinctiveness import MODES, _feature, _nearest, _percentiles
from tools.artwork_native_benchmark import _json
from tools.artwork_transparent_bundle import _new_output, _failure

SCHEMA = 'bytefables.artwork-family-experiment.v1'
TRIAGE_SCHEMA = 'bytefables.artwork-family-triage.v1'
DOMAIN = b'ByteFables:family-experiment:v1\0'
PALETTES = ('neon','pastel','mono')


def _expect(v, message):
    if not v: raise ValueError(message)


def _digests(count:int)->list[str]:
    _expect(type(count) is int and 16 <= count <= 256, 'Identity count must be 16..256')
    return [hashlib.sha256(DOMAIN + i.to_bytes(4,'big')).hexdigest() for i in range(count)]


def _style(digest:str,family:str)->dict:
    raw=bytes.fromhex(digest)
    return {'bridge_version':BRIDGE,'digest_hex':digest,'style':family,
            'palette':PALETTES[raw[0]%len(PALETTES)],'complexity':2+raw[1]%6}


def _rgba(renderer)->np.ndarray:
    image=renderer.render(0)
    try:return np.asarray(image,dtype=np.float32)/255.0
    finally:image.close()


def _duplicates(images:list[np.ndarray])->int:
    groups={}
    for i,image in enumerate(images):
        h=hashlib.sha256((image*255+0.5).astype(np.uint8).tobytes()).hexdigest();groups.setdefault(h,[]).append(i)
    return sum(1 for v in groups.values() if len(v)>1)


def _ratio(candidate:float,baseline:float)->float:
    if baseline <= 0:return 1.0 if candidate <= 0 else 999.0
    return candidate/baseline


def _select_families(families,triage_path:Path|None)->list[str]:
    if families:
        result=list(dict.fromkeys(families))
    elif triage_path is not None:
        doc=json.loads(Path(triage_path).read_bytes())
        _expect(doc.get('schema')==TRIAGE_SCHEMA and doc.get('status')=='passed','Expected successful family triage v1')
        result=[x.get('family') for x in doc.get('families',[]) if x.get('family') in SUPPORTED_FAMILIES]
    else:
        result=['mandala','heraldry','branching']
    _expect(result and all(x in SUPPORTED_FAMILIES for x in result),'No supported remediation families selected')
    return result


def _preview(family:str,digests:list[str],size:int,output:Path,count:int=12)->None:
    count=min(count,len(digests));cell=size+24
    canvas=Image.new('RGB',(cell*2,cell*count),(28,28,28));draw=ImageDraw.Draw(canvas)
    try:
        for row,digest in enumerate(digests[:count]):
            style=_style(digest,family)
            for col,renderer in enumerate((ArtworkRenderer((size,size),style),RemediationArtworkRenderer((size,size),style))):
                img=renderer.render(0)
                try:
                    plate=Image.new('RGB',(size,size),(128,128,128));plate.paste(img,mask=img.getchannel('A'))
                    canvas.paste(plate,(col*cell+(cell-size)//2,row*cell+2))
                finally:img.close()
            draw.text((2,row*cell+size+4),digest[:10],fill=(235,235,235))
        output.parent.mkdir(parents=True,exist_ok=True);canvas.save(output,format='PNG',optimize=True)
    finally:canvas.close()


def run_experiments(output:Path,*,families=None,triage_path:Path|None=None,identities:int=128,
                    sizes=(16,32,64,128),preview_size:int=32)->dict:
    selected=_select_families(families,triage_path);sizes=tuple(int(x) for x in sizes)
    _expect(sizes and all(x in (16,32,64,128) for x in sizes) and len(set(sizes))==len(sizes),'Invalid experiment sizes')
    _expect(preview_size in sizes,'Preview size must be included')
    digests=_digests(identities);output=_new_output(Path(output),());output.mkdir(parents=True)
    try:
        families_out=[];rows=[]
        for family in selected:
            cases=[];baseline_dupes=0;candidate_dupes=0
            for size in sizes:
                base=[];candidate=[];items=[]
                for digest in digests:
                    style=_style(digest,family);items.append({'digestHex':digest})
                    base.append(_rgba(ArtworkRenderer((size,size),style)))
                    candidate.append(_rgba(RemediationArtworkRenderer((size,size),style)))
                baseline_dupes += _duplicates(base);candidate_dupes += _duplicates(candidate)
                for mode in MODES:
                    bf=[_feature(x,mode) for x in base];cf=[_feature(x,mode) for x in candidate]
                    _,bn=_nearest(bf,items,False);_,cn=_nearest(cf,items,False)
                    bdist=_percentiles(bn);cdist=_percentiles(cn)
                    ratios={k:round(_ratio(cdist[k],bdist[k]),6) for k in ('p01','p05','median')}
                    case={'size':size,'mode':mode,'baseline':bdist,'candidate':cdist,'ratios':ratios}
                    cases.append(case);rows.append((family,size,mode,bdist['p01'],cdist['p01'],ratios['p01'],bdist['p05'],cdist['p05'],ratios['p05'],bdist['median'],cdist['median'],ratios['median']))
            p05=[c['ratios']['p05'] for c in cases];small=[c['ratios']['p05'] for c in cases if c['size']<=32]
            improved=sum(1 for x in p05 if x>1.0)/len(p05)
            summary={'worstP05Ratio':round(min(p05),6),'medianP05Ratio':round(float(np.median(p05)),6),
                     'smallIconMedianP05Ratio':round(float(np.median(small)),6),'improvedCaseFraction':round(improved,6),
                     'baselineExactDuplicateGroups':baseline_dupes,'candidateExactDuplicateGroups':candidate_dupes}
            summary['promising']=bool(summary['smallIconMedianP05Ratio']>=1.05 and summary['worstP05Ratio']>=0.85 and
                                      summary['improvedCaseFraction']>=0.60 and candidate_dupes<=baseline_dupes)
            families_out.append({'family':family,'summary':summary,'cases':cases})
            _preview(family,digests,preview_size,output/f'{family}-preview.png')
        report={'schema':SCHEMA,'status':'passed','candidateProfile':CANDIDATE_PROFILE,'identities':identities,
                'sizes':list(sizes),'modes':list(MODES),'families':families_out,
                'heuristic':{'smallIconMedianP05RatioAtLeast':1.05,'worstP05RatioAtLeast':0.85,'improvedCaseFractionAtLeast':0.60,
                             'note':'Engineering A/B heuristic only; never auto-promotes production artwork.'},
                'warning':'Synthetic deterministic A/B screening, not human recognisability or accessibility certification.'}
        (output/'report.json').write_bytes(_json(report))
        with (output/'comparison.csv').open('w',newline='',encoding='utf-8') as f:
            w=csv.writer(f);w.writerow(['family','size','mode','baseline_p01','candidate_p01','p01_ratio','baseline_p05','candidate_p05','p05_ratio','baseline_median','candidate_median','median_ratio']);w.writerows(rows)
        lines=['# Artwork remediation A/B review','',f'Candidate profile: `{CANDIDATE_PROFILE}`. Production artwork is unchanged.','']
        for item in families_out:
            s=item['summary'];lines += [f"## {item['family']}",f"- promising heuristic: **{str(s['promising']).lower()}**",f"- small-icon median p05 ratio: {s['smallIconMedianP05Ratio']:.3f}×",f"- worst p05 ratio: {s['worstP05Ratio']:.3f}×",f"- improved case fraction: {s['improvedCaseFraction']:.1%}",f"- exact duplicate groups baseline/candidate: {s['baselineExactDuplicateGroups']} / {s['candidateExactDuplicateGroups']}",'']
        (output/'REVIEW.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
        return report
    except Exception as exc:
        _failure(output,exc);raise
