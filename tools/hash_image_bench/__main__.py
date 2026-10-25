"""Run with: python -m tools.hash_image_bench --help"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from .experiment import (STRATEGIES, prepare, add_llm_candidates, render_local_models,
                         report_experiment, validate_model_file, evaluate_local_clip, export_framerudiments_assets)


def positive_integers(value):
    vals=tuple(int(x) for x in value.split(',') if x.strip())
    if not vals or len(vals)>50 or any(v<0 for v in vals):raise argparse.ArgumentTypeError('Expected comma-separated nonnegative integers')
    return vals


def main():
    p=argparse.ArgumentParser(description='ByteFables local-only public-hash image-model profiling')
    subs=p.add_subparsers(dest='command',required=True)
    prep=subs.add_parser('prepare',help='Generate frozen bit decisions and deterministic prompt baselines')
    prep.add_argument('--confirm-public',action='store_true',required=True,
                     help='Confirm input is a public hash, never a secret/private key')
    prep.add_argument('--public-hex',required=True)
    prep.add_argument('--namespace',default='danceflow')
    prep.add_argument('--kind',default='node-id')
    prep.add_argument('--output',required=True)
    prep.add_argument('--budgets',type=positive_integers,default=(8,16,32))
    prep.add_argument('--strategies',default='direct,narrative,structured')
    prep.add_argument('--paired-bits',type=positive_integers,default=())
    prep.add_argument('--node',default='node')
    prompt=subs.add_parser('write-prompts',help='Use local OpenAI-compatible LLM to write prompts')
    prompt.add_argument('--experiment',required=True)
    prompt.add_argument('--endpoint',required=True,help='HTTP loopback, e.g. http://127.0.0.1:11434/v1/chat/completions')
    prompt.add_argument('--model',required=True)
    prompt.add_argument('--strategies',default='narrative,structured')
    prompt.add_argument('--seed',type=int,default=73)
    prompt.add_argument('--temperature',type=float,default=0.2)
    prompt.add_argument('--max-calls',type=int,default=48)
    render=subs.add_parser('render',help='Local Diffusers images; no automatic model downloads')
    render.add_argument('--experiment',required=True)
    render.add_argument('--models',required=True,help='JSON list of locally installed Diffusers pipelines')
    render.add_argument('--execute',action='store_true',help='Actually use GPU, otherwise print dry-run')
    render.add_argument('--max-jobs',type=int,default=48)
    render.add_argument('--repetitions',type=int,default=2)
    render.add_argument('--seed-policy',choices=['paired','identity'],default='paired')
    render.add_argument('--allow-cpu',action='store_true')
    render.add_argument('--only-model')
    render.add_argument('--only-writer')
    render.add_argument('--only-strategy')
    render.add_argument('--only-budget',type=int)
    report=subs.add_parser('report',help='Aggregate prompt checks and actual image receipts')
    report.add_argument('--experiment',required=True)
    report.add_argument('--blind-judgments',help='JSONL with jobId and answers, made without seeing hash choices')
    clip=subs.add_parser('score-clip',help='Exploratory CLIP contrast with a local checkpoint (not proof of bit recovery)')
    clip.add_argument('--experiment',required=True)
    clip.add_argument('--model-path',required=True)
    clip.add_argument('--device',choices=['cpu','cuda','mps'],default='cpu')
    clip.add_argument('--max-images',type=int,default=48)
    clip.add_argument('--max-bits',type=int,default=32)
    assets=subs.add_parser('host-assets',help='Create SHA-pinned generated-image sprite fragments for FrameRudiments')
    assets.add_argument('--experiment',required=True)
    info=subs.add_parser('models',help='Show local model-config validation and candidate list')
    info.add_argument('--models',required=True)
    args=p.parse_args()
    if args.command=='prepare':
        out=prepare(args.public_hex,args.output,namespace=args.namespace,kind=args.kind,
                    budgets=args.budgets,strategies=tuple(args.strategies.split(',')),
                    paired_bits=args.paired_bits,node_executable=args.node)
        result={'experimentId':out['experimentId'],'cases':len(out['cases']),
                'candidates':len(out['candidates']),'bitCount':out['hashBits'],'path':str(Path(args.output).resolve())}
    elif args.command=='write-prompts':
        if not 0<=args.temperature<=2 or not 1<=args.max_calls<=1000 or args.seed<0:
            p.error('Invalid LLM parameter bounds')
        result={'created':len(add_llm_candidates(args.experiment,endpoint=args.endpoint,
                      model=args.model,strategies=tuple(args.strategies.split(',')),seed=args.seed,
                      temperature=args.temperature,max_calls=args.max_calls))}
    elif args.command=='render':
        result=render_local_models(args.experiment,args.models,execute=args.execute,
            max_jobs=args.max_jobs,repetitions=args.repetitions,
            seed_policy=args.seed_policy,allow_cpu=args.allow_cpu,only_model=args.only_model,
            only_writer=args.only_writer,only_strategy=args.only_strategy,only_budget=args.only_budget)
    elif args.command=='report':
        result=report_experiment(args.experiment,judgments_path=args.blind_judgments)
    elif args.command=='score-clip':
        result=evaluate_local_clip(args.experiment,model_path=args.model_path,
                                   device=args.device,max_images=args.max_images,max_bits=args.max_bits)
    elif args.command=='host-assets':
        result=export_framerudiments_assets(args.experiment)
    else:
        result={'models':validate_model_file(args.models,require_files=False)}
    print(json.dumps(result,indent=2,ensure_ascii=False))


if __name__=='__main__':
    try:main()
    except (ValueError, FileNotFoundError, FileExistsError,RuntimeError,TimeoutError) as e:
        import sys
        print(f'ByteFables image bench: {e}',file=sys.stderr)
        sys.exit(2)
