"""Screen saved transparent identity images for likely visual collisions.

This is deterministic machine screening, not accessibility certification or a
human recognisability study. It consumes verified PNG pixels only.
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
import math
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

from tools.artwork_asset_bundle import _bytes, _file, _no_links, _expect, MAX_REPORT_BYTES
from tools.artwork_native_benchmark import _read_json, _json, _sha
from tools.artwork_transparent_bundle import verify_transparent_bundle, _new_output, _failure

SCHEMA='bytefables.artwork-distinctiveness.v1'
MODES=('colour','greyscale','protan','deutan','tritan')
BACKGROUNDS=((0,0,0),(128,128,128),(255,255,255))
FEATURE_SIDE=4  # bounded perceptual screening grid; exact duplicates still use native pixels.
# Deterministic screening matrices; not a clinical simulation.
CVD={
 'protan':np.array([[0.152286,1.052583,-0.204868],[0.114503,0.786281,0.099216],[-0.003882,-0.048116,1.051998]],dtype=np.float32),
 'deutan':np.array([[0.367322,0.860646,-0.227968],[0.280085,0.672501,0.047413],[-0.011820,0.042940,0.968881]],dtype=np.float32),
 'tritan':np.array([[1.255528,-0.076749,-0.178779],[-0.078411,0.930809,0.147602],[0.004733,0.691367,0.303900]],dtype=np.float32),
}


def _png_record(asset:dict,size:int)->dict:
    wanted=f"assets/{asset['family']}-{asset['palette']}-c{asset['complexity']}/{asset['digestHex']}/{size}.png"
    found=[r for r in asset['files'] if r.get('format')=='png' and r.get('file')==wanted]
    _expect(len(found)==1,'Transparent PNG inventory mismatch')
    return found[0]


def _load_rgba(root:Path,asset:dict,size:int)->np.ndarray:
    rec=_png_record(asset,size);raw=_bytes(_file(root,rec['file']),2*1024*1024)
    _expect(len(raw)==rec['byteLength'] and _sha(raw)==rec['sha256'],'Transparent PNG changed')
    with Image.open(io.BytesIO(raw)) as image:
        _expect(image.format=='PNG' and image.mode=='RGBA' and image.size==(size,size),'Unexpected distinctiveness source image')
        pixels=np.asarray(image,dtype=np.float32)/255.0
    source=next(x for x in asset['sources'] if x['size']==size)
    _expect(hashlib.sha256((pixels*255.0+0.5).astype(np.uint8).tobytes()).hexdigest()==source['rgbaSha256'],'Decoded PNG pixels changed')
    return pixels


def _composite(rgba:np.ndarray,bg:tuple[int,int,int])->np.ndarray:
    rgb=rgba[...,:3];a=rgba[...,3:4];background=np.asarray(bg,dtype=np.float32).reshape(1,1,3)/255.0
    return rgb*a+background*(1.0-a)


def _mode(rgb:np.ndarray,name:str)->np.ndarray:
    if name=='colour':return rgb
    if name=='greyscale':
        y=rgb[...,0]*0.2126+rgb[...,1]*0.7152+rgb[...,2]*0.0722
        return np.repeat(y[...,None],3,axis=2)
    return np.clip(np.tensordot(rgb,CVD[name].T,axes=1),0.0,1.0)


def _pool(image:np.ndarray,side:int=FEATURE_SIDE)->np.ndarray:
    h,w=image.shape[:2];_expect(h==w and h>=side and h%side==0,'Distinctiveness pooling requires square power-of-two native images')
    factor=h//side
    if image.ndim==2:return image.reshape(side,factor,side,factor).mean(axis=(1,3))
    return image.reshape(side,factor,side,factor,image.shape[2]).mean(axis=(1,3))

def _feature(rgba:np.ndarray,mode:str)->np.ndarray:
    parts=[]
    for bg in BACKGROUNDS:parts.append(_pool(_mode(_composite(rgba,bg),mode)).reshape(-1))
    # Alpha is kept separately so two equally coloured but differently shaped icons do not collapse.
    parts.append(_pool(rgba[...,3]).reshape(-1))
    return np.concatenate(parts).astype(np.float32)


def _dhash(rgba:np.ndarray)->int:
    image=Image.fromarray((rgba*255+0.5).astype(np.uint8),'RGBA')
    try:
        bg=Image.new('RGB',image.size,(128,128,128));bg.paste(image,mask=image.getchannel('A'))
        small=bg.convert('L').resize((9,8),Image.Resampling.BOX);a=np.asarray(small,dtype=np.int16)
    finally:image.close()
    bits=(a[:,1:]>a[:,:-1]).reshape(-1);value=0
    for bit in bits:value=(value<<1)|int(bit)
    return value


def _nearest(features:list[np.ndarray],items:list[dict],same_digest:bool=False)->tuple[list[dict],list[float]]:
    # Block-vectorised L1 keeps a 2k+ asset screening run bounded without allocating N x N x D.
    matrix=np.stack(features).astype(np.float32,copy=False);n=len(items);digests=np.asarray([x['digestHex'] for x in items],dtype=object)
    pairs=[];nearest=[];block=64
    for start in range(0,n,block):
        end=min(n,start+block);distance=np.mean(np.abs(matrix[start:end,None,:]-matrix[None,:,:]),axis=2)
        for local,i in enumerate(range(start,end)):
            allowed=(digests==digests[i]) if same_digest else (digests!=digests[i]);allowed[i]=False
            if not np.any(allowed):continue
            row=np.where(allowed,distance[local],np.inf);j=int(np.argmin(row));value=float(row[j]);nearest.append(value)
            if i<j:pairs.append({'a':i,'b':j,'distance':round(value,8)})
    unique={(p['a'],p['b']):p for p in pairs}
    return sorted(unique.values(),key=lambda x:(x['distance'],x['a'],x['b'])),nearest


def _percentiles(values:list[float])->dict:
    _expect(values,'No different-identity comparisons available')
    a=np.asarray(values,dtype=np.float64)
    return {'min':round(float(np.min(a)),8),'p01':round(float(np.quantile(a,.01)),8),
            'p05':round(float(np.quantile(a,.05)),8),'median':round(float(np.median(a)),8)}


def _contact_sheet(root:Path,items:list[dict],pairs:list[dict],size:int,output:Path,limit:int=20)->None:
    pairs=pairs[:limit];cell=max(80,size+20);canvas=Image.new('RGB',(cell*2,max(1,len(pairs))*cell),(24,24,24));draw=ImageDraw.Draw(canvas)
    try:
        for row,pair in enumerate(pairs):
            for col,key in enumerate(('a','b')):
                item=items[pair[key]];rec=_png_record(item,size)
                with Image.open(_file(root,rec['file'])) as src:
                    icon=Image.new('RGB',(size,size),(128,128,128));icon.paste(src,mask=src.getchannel('A'))
                x=col*cell+(cell-size)//2;y=row*cell+2;canvas.paste(icon,(x,y))
                label=f"{item['family']} {item['digestHex'][:8]}";draw.text((col*cell+2,y+size+2),label,fill=(235,235,235))
            draw.text((cell-35,row*cell+2),f"{pair['distance']:.4f}",fill=(255,255,255))
        output.parent.mkdir(parents=True,exist_ok=True);canvas.save(output,format='PNG',optimize=True)
    finally:canvas.close()


def analyse_distinctiveness(bundle:Path,output:Path,*,sizes=(16,32,64,128),preview_size=64,top_pairs=50)->dict:
    root=_no_links(bundle);verify=verify_transparent_bundle(root);doc,manifest_sha=_read_json(_file(root,'manifest.json'),MAX_REPORT_BYTES)
    sizes=tuple(int(x) for x in sizes);_expect(sizes and all(x in (16,32,64,128) for x in sizes) and len(set(sizes))==len(sizes),'Invalid distinctiveness sizes')
    _expect(preview_size in sizes and type(top_pairs) is int and 1<=top_pairs<=500,'Invalid distinctiveness options')
    items=sorted(doc['assets'],key=lambda a:(a['family'],a['palette'],a['complexity'],a['digestHex']))
    _expect(len(items)==doc['assetCount']==verify['assets'],'Transparent asset inventory mismatch')
    output=_new_output(output,(root,));output.mkdir(parents=True)
    try:
        size_reports=[];preview_pairs=None
        for size in sizes:
            rgba=[_load_rgba(root,item,size) for item in items]
            dhashes=[_dhash(x) for x in rgba]
            exact={}
            for i,x in enumerate(rgba):exact.setdefault(hashlib.sha256((x*255+0.5).astype(np.uint8).tobytes()).hexdigest(),[]).append(i)
            exact_groups=[v for v in exact.values() if len(v)>1]
            hash_groups={}
            for i,h in enumerate(dhashes):hash_groups.setdefault(h,[]).append(i)
            dhash_groups=[v for v in hash_groups.values() if len(v)>1]
            modes={}
            for mode in MODES:
                features=[_feature(x,mode) for x in rgba];different,nearest=_nearest(features,items,False);same,_=_nearest(features,items,True)
                family_summary={}
                for family in sorted({x['family'] for x in items}):
                    indices=[i for i,x in enumerate(items) if x['family']==family]
                    if len({items[i]['digestHex'] for i in indices})<2:continue
                    _,family_nearest=_nearest([features[i] for i in indices],[items[i] for i in indices],False)
                    family_summary[family]=_percentiles(family_nearest)
                modes[mode]={'nearestDifferentDigest':different[:top_pairs],'nearestDifferentDigestDistribution':_percentiles(nearest),
                             'nearestSameDigestStyleVariant':same[:min(top_pairs,len(same))],'withinFamilyDistribution':family_summary}
                if size==preview_size and mode=='colour':preview_pairs=different
            size_reports.append({'size':size,'assets':len(items),'uniqueDigests':len({x['digestHex'] for x in items}),
                                 'featureSide':FEATURE_SIDE,'exactPixelDuplicateGroups':exact_groups,'dHashCollisionGroups':dhash_groups,'modes':modes})
        report={'schema':SCHEMA,'status':'passed','publicOnly':True,'manifestSha256':manifest_sha,'assetCount':len(items),
                'uniqueDigests':len({x['digestHex'] for x in items}),'sizes':list(sizes),'screeningModes':list(MODES),
                'backgrounds':[list(x) for x in BACKGROUNDS],'results':size_reports,
                'warning':'Machine collision screening only; not accessibility certification or human recognisability evidence.'}
        (output/'report.json').write_bytes(_json(report))
        # Human-readable closest-pair CSV uses the preview-size colour metric.
        with (output/'closest-pairs.csv').open('w',newline='',encoding='utf-8') as f:
            w=csv.writer(f);w.writerow(['rank','distance','a_family','a_digest','b_family','b_digest'])
            for rank,p in enumerate((preview_pairs or [])[:top_pairs],1):
                a,b=items[p['a']],items[p['b']];w.writerow([rank,p['distance'],a['family'],a['digestHex'],b['family'],b['digestHex']])
        _contact_sheet(root,items,preview_pairs or [],preview_size,output/'closest-pairs.png',min(20,top_pairs))
        return report
    except Exception as exc:
        _failure(output,exc);raise
