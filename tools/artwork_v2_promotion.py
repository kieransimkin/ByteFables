"""Measure whether the opt-in artwork-v2 candidate is ready for manual promotion.

No production renderer is changed by this tool.  It compares v1, the previous
remediation candidate, and the v2 candidate over deterministic public digests.
The result is an engineering promotion gate, not human-recognition evidence.
"""
from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

from bytefables_framerudiments.artwork import ArtworkRenderer, BRIDGE, PATTERNS
from bytefables_framerudiments.artwork_remediation import RemediationArtworkRenderer
from bytefables_framerudiments.artwork_remediation_v2 import RemediationArtworkRendererV2
from bytefables_framerudiments.artwork_v2 import ArtworkRendererV2Candidate, PROFILE as V2_PROFILE, TARGET_FAMILIES
from tools.artwork_distinctiveness import MODES, _feature, _nearest, _percentiles
from tools.artwork_native_benchmark import _json
from tools.artwork_transparent_bundle import _new_output, _failure

SCHEMA = 'bytefables.artwork-v2-promotion.v1'
DOMAIN = b'ByteFables:artwork-v2-promotion:v1\0'
PALETTES = ('neon','pastel','mono')
UNCHANGED_FAMILIES = tuple(sorted(set(PATTERNS) - set(TARGET_FAMILIES)))


def _expect(value, message):
    if not value:
        raise ValueError(message)


def _digests(count: int) -> list[str]:
    _expect(type(count) is int and 32 <= count <= 512, 'Promotion identity count must be 32..512')
    return [hashlib.sha256(DOMAIN + i.to_bytes(4,'big')).hexdigest() for i in range(count)]


def _style(digest: str, family: str) -> dict:
    raw = bytes.fromhex(digest)
    return {'bridge_version':BRIDGE,'digest_hex':digest,'style':family,
            'palette':PALETTES[raw[0] % 3],'complexity':2 + raw[1] % 6}


def _rgba(renderer) -> np.ndarray:
    image = renderer.render(0)
    try:
        return np.asarray(image,dtype=np.float32)/255.0
    finally:
        image.close()


def _duplicates(images: list[np.ndarray]) -> int:
    groups={}
    for image in images:
        digest=hashlib.sha256((image*255+0.5).astype(np.uint8).tobytes()).hexdigest()
        groups[digest]=groups.get(digest,0)+1
    return sum(1 for n in groups.values() if n>1)


def _ratio(candidate: float, baseline: float) -> float:
    if baseline <= 0:
        return 1.0 if candidate <= 0 else 999.0
    return candidate / baseline


def _preview(family: str, digests: list[str], size: int, output: Path, count: int = 12) -> None:
    count=min(count,len(digests)); cell=size+26
    canvas=Image.new('RGB',(cell*3,cell*count),(26,26,26)); draw=ImageDraw.Draw(canvas)
    labels=('v1','candidate-v1','v2-candidate')
    try:
        for row,digest in enumerate(digests[:count]):
            style=_style(digest,family)
            renderers=(ArtworkRenderer((size,size),style),RemediationArtworkRenderer((size,size),style),ArtworkRendererV2Candidate((size,size),style))
            for col,renderer in enumerate(renderers):
                image=renderer.render(0)
                try:
                    plate=Image.new('RGB',(size,size),(128,128,128));plate.paste(image,mask=image.getchannel('A'))
                    canvas.paste(plate,(col*cell+(cell-size)//2,row*cell+2))
                finally:image.close()
                if row==0:draw.text((col*cell+2,size+6),labels[col],fill=(235,235,235))
            draw.text((2,row*cell+size+15),digest[:10],fill=(210,210,210))
        output.parent.mkdir(parents=True,exist_ok=True);canvas.save(output,format='PNG',optimize=True)
    finally:canvas.close()


def _unchanged_contract(digests: list[str], sizes: tuple[int,...]) -> dict:
    comparisons=0
    for family in UNCHANGED_FAMILIES:
        for size in sizes:
            # 16 identities per unchanged family is enough to catch accidental
            # routing/seed changes without multiplying the expensive A/B matrix.
            for digest in digests[:16]:
                style=_style(digest,family)
                a=ArtworkRenderer((size,size),style).render(0);b=ArtworkRendererV2Candidate((size,size),style).render(0)
                try:
                    _expect(a.tobytes()==b.tobytes(),f'v2 candidate changed delegated family {family}')
                finally:a.close();b.close()
                comparisons+=1
    return {'families':list(UNCHANGED_FAMILIES),'comparisons':comparisons,'byteExact':True}


def run_promotion(output: Path, *, identities: int = 256, sizes=(16,32,64,128), preview_size: int = 32) -> dict:
    sizes=tuple(int(x) for x in sizes)
    _expect(sizes and all(x in (16,32,64,128) for x in sizes) and len(set(sizes))==len(sizes),'Invalid promotion sizes')
    _expect(preview_size in sizes,'Promotion preview size must be included')
    digests=_digests(identities);output=_new_output(Path(output),());output.mkdir(parents=True)
    try:
        unchanged=_unchanged_contract(digests,sizes)
        families=[];rows=[]
        for family in sorted(TARGET_FAMILIES):
            cases=[];base_dupes=old_dupes=v2_dupes=0
            for size in sizes:
                base=[];old=[];v2=[];items=[]
                for digest in digests:
                    style=_style(digest,family);items.append({'digestHex':digest})
                    base.append(_rgba(ArtworkRenderer((size,size),style)))
                    candidate=_rgba(ArtworkRendererV2Candidate((size,size),style));v2.append(candidate)
                    # Candidate-v2 changes only heraldry. Mandala/branching are
                    # exactly candidate-v1, so reuse the measured pixels instead
                    # of rendering the same geometry twice in large studies.
                    old.append(_rgba(RemediationArtworkRenderer((size,size),style)) if family=='heraldry' else candidate)
                base_dupes+=_duplicates(base);old_dupes+=_duplicates(old);v2_dupes+=_duplicates(v2)
                for mode in MODES:
                    distributions={}
                    for name,images in (('baseline',base),('candidateV1',old),('v2',v2)):
                        features=[_feature(image,mode) for image in images]
                        _,nearest=_nearest(features,items,False);distributions[name]=_percentiles(nearest)
                    v2rat={k:round(_ratio(distributions['v2'][k],distributions['baseline'][k]),6) for k in ('p01','p05','median')}
                    priorrat={k:round(_ratio(distributions['v2'][k],distributions['candidateV1'][k]),6) for k in ('p01','p05','median')}
                    case={'size':size,'mode':mode,**distributions,'v2VsBaseline':v2rat,'v2VsCandidateV1':priorrat}
                    cases.append(case);rows.append((family,size,mode,distributions['baseline']['p05'],distributions['candidateV1']['p05'],distributions['v2']['p05'],v2rat['p05'],priorrat['p05']))
            ratios=[c['v2VsBaseline']['p05'] for c in cases];small=[c['v2VsBaseline']['p05'] for c in cases if c['size']<=32]
            improved=sum(1 for x in ratios if x>1.0)/len(ratios)
            heraldry16=[c for c in cases if c['size']==16] if family=='heraldry' else []
            summary={'worstP05Ratio':round(min(ratios),6),'medianP05Ratio':round(float(np.median(ratios)),6),
                     'smallIconMedianP05Ratio':round(float(np.median(small)),6),'improvedCaseFraction':round(improved,6),
                     'baselineExactDuplicateGroups':base_dupes,'candidateV1ExactDuplicateGroups':old_dupes,'v2ExactDuplicateGroups':v2_dupes,
                     'heraldry16AllModesPositive':bool(not heraldry16 or all(c['v2']['p05']>0 for c in heraldry16))}
            summary['eligibleForManualPromotion']=bool(summary['smallIconMedianP05Ratio']>=1.10 and summary['worstP05Ratio']>=0.90 and
                summary['improvedCaseFraction']>=0.75 and summary['v2ExactDuplicateGroups']==0 and
                summary['v2ExactDuplicateGroups']<=summary['baselineExactDuplicateGroups'] and summary['heraldry16AllModesPositive'])
            families.append({'family':family,'summary':summary,'cases':cases})
            _preview(family,digests,preview_size,output/f'{family}-promotion-preview.png')
        eligible=all(x['summary']['eligibleForManualPromotion'] for x in families) and unchanged['byteExact']
        report={'schema':SCHEMA,'status':'passed','candidateProfile':V2_PROFILE,'identities':identities,'sizes':list(sizes),'modes':list(MODES),
                'unchangedFamilies':unchanged,'families':families,'manualPromotionEligible':eligible,
                'gate':{'smallIconMedianP05RatioAtLeast':1.10,'worstP05RatioAtLeast':0.90,'improvedCaseFractionAtLeast':0.75,
                        'v2ExactDuplicateGroups':0,'heraldry16AllModesP05Positive':True,
                        'note':'Engineering gate only; promotion remains a separate explicit code/version change.'},
                'warning':'Machine A/B screening only; not human recognisability or accessibility certification.'}
        (output/'report.json').write_bytes(_json(report))
        with (output/'comparison.csv').open('w',newline='',encoding='utf-8') as f:
            w=csv.writer(f);w.writerow(['family','size','mode','baseline_p05','candidate_v1_p05','v2_p05','v2_vs_baseline','v2_vs_candidate_v1']);w.writerows(rows)
        lines=['# Artwork generator v2 candidate promotion review','',f'Profile: `{V2_PROFILE}`','',f'Global manual-promotion gate: **{str(eligible).lower()}**','']
        for item in families:
            s=item['summary'];lines += [f"## {item['family']}",f"- eligible: **{str(s['eligibleForManualPromotion']).lower()}**",f"- exact duplicate groups v1 / candidate-v1 / v2: {s['baselineExactDuplicateGroups']} / {s['candidateV1ExactDuplicateGroups']} / {s['v2ExactDuplicateGroups']}",f"- small-icon median p05 ratio vs v1: {s['smallIconMedianP05Ratio']:.3f}×",f"- worst p05 ratio vs v1: {s['worstP05Ratio']:.3f}×",f"- improved-case fraction: {s['improvedCaseFraction']:.1%}",f"- heraldry 16px p05 positive in every mode: {str(s['heraldry16AllModesPositive']).lower()}",'']
        (output/'PROMOTION.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
        return report
    except Exception as exc:
        _failure(output,exc);raise
