#!/usr/bin/env python3
"""Require the independent Khronos ktx tool to validate and extract every array image."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from tools.artwork_ktx2_bundle import verify_ktx2_bundle


def qualify(bundle: Path, executable: Path) -> dict:
    root=Path(bundle).resolve(strict=True);tool=Path(executable).resolve(strict=True)
    verified=verify_ktx2_bundle(root)
    manifest=json.loads((root/'manifest.json').read_text(encoding='utf-8'))
    source=json.loads((root/'source-manifest.json').read_text(encoding='utf-8'))
    def command(*args):
        process=subprocess.run([str(tool),*map(str,args)],capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=120)
        output=(process.stdout+process.stderr)
        if len(output)>256*1024:raise ValueError('Khronos command output limit exceeded')
        if process.returncode:raise ValueError(f'Khronos command failed ({process.returncode}): {output[:4000]}')
        return output.strip()
    version=command('--version');reports=[];images=0
    for bank in manifest['banks']:
        path=root/bank['file'];validation=command('validate',path)
        with tempfile.TemporaryDirectory(prefix='bytefables-ktx-readback-') as temporary:
            extracted=Path(temporary)
            command('extract','--all','--raw',path,extracted)
            expected_names=set()
            for level in range(source['levelCount']):
                for layer in range(bank['layerCount']):
                    name=f'output_level{level}_layer{layer}.raw';expected_names.add(name)
                    image=extracted/name;size=source['nativeSize']>>level
                    if not image.is_file() or image.stat().st_size!=size*size*4:
                        raise ValueError(f'Khronos extraction missing/wrong size: {name}')
                    sprite=source['sprites'][bank['index']*source['layersPerBank']+layer]
                    if hashlib.sha256(image.read_bytes()).hexdigest()!=sprite['levelSha256'][level]:
                        raise ValueError(f'Khronos independent pixel mismatch: {name}')
                    images+=1
            if {p.name for p in extracted.iterdir()}!=expected_names:raise ValueError('Unexpected Khronos extraction inventory')
        reports.append({'file':bank['file'],'validationOutput':validation,'imagesVerified':bank['layerCount']*source['levelCount']})
    return {'status':'passed','independentToolExecuted':True,'toolVersion':version,
            'toolSha256':hashlib.sha256(tool.read_bytes()).hexdigest(),'manifestSha256':verified['manifestSha256'],
            'imagesVerified':images,'banks':reports,
            'warning':'Qualification of this uncompressed profile, not all KTX2 formats or signed authenticity.'}


def main() -> int:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bundle',required=True,type=Path);parser.add_argument('--ktx',required=True,type=Path)
    parser.add_argument('--report',type=Path);args=parser.parse_args()
    if args.report and args.report.exists():parser.error('Report already exists')
    try:result=qualify(args.bundle,args.ktx)
    except Exception as exc:result={'status':'failed','exception':type(exc).__name__,'message':str(exc)[:4000]}
    text=json.dumps(result,indent=2)+'\n'
    if args.report:
        args.report.parent.mkdir(parents=True,exist_ok=True)
        with args.report.open('x',encoding='utf-8') as f:f.write(text)
    print(text,end='');return 0 if result['status']=='passed' else 1


if __name__=='__main__':raise SystemExit(main())
