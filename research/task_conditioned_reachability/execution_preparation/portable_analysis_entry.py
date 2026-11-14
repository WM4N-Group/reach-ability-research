"""Bootstrap a sealed OFFLINE evaluator at any explicit filesystem location.

Uses only standard library; code/data inputs checked before importing consumer.
No environment/package search, network, subprocess, checkpoint or runtime.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_bundle(root,expected_sha256):
    root=Path(root).resolve();manifest=root/'bundle.json'
    if sha(manifest)!=expected_sha256:raise ValueError('Independently fixed bundle manifest SHA mismatch')
    data=json.loads(manifest.read_text())
    if data['schema']!='reach-sealed-offline-analysis-bundle-v1':raise ValueError('Unknown sealed analysis package')
    for name,ref in data['files'].items():
        p=Path(name)
        if p.is_absolute() or '..' in p.parts:raise ValueError('Package member escapes source root')
        path=root/p
        if not path.is_file() or path.is_symlink() or not path.resolve().is_relative_to(root):
            raise ValueError('Missing/redirected bundle member')
        if sha(path)!=ref['sha256']:raise ValueError('Original source byte identity changed: '+name)
    mappings={}
    for original,relative in data['source_root_mappings'].items():
        p=Path(relative)
        if p.is_absolute() or '..' in p.parts:raise ValueError('Mapped package root escapes seal')
        target=root/p
        if not target.is_dir() or target.is_symlink() or not target.resolve().is_relative_to(root):raise ValueError('Invalid sealed relocation root')
        mappings[original]=str(target)
    return data,mappings


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--bundle-sha256',required=True)
    parser.add_argument('--mode',choices=('phase','repair'),required=True)
    parser.add_argument('--inputs',type=Path,required=True)
    parser.add_argument('--inputs-sha256',required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--allow-fixture',action='store_true')
    parser.add_argument('--evidence-root',type=Path,action='append',default=[],
                        help='Explicit local closed-input roots, never a search path or runtime permission')
    args=parser.parse_args()
    root=Path(__file__).resolve().parent
    data,mappings=load_bundle(root,args.bundle_sha256)
    if args.output.exists():raise ValueError('Never overwrite/reuse an offline result root')
    if args.output.absolute().resolve().is_relative_to(root):raise ValueError('Outputs must not mutate the sealed source bundle')
    evidence_roots=[]
    for path in args.evidence_root:
        if not path.is_absolute() or not path.is_dir() or path.is_symlink():raise ValueError('Existing absolute nonsymlink closed-evidence roots required')
        evidence_roots.append(path.resolve())
    if not args.inputs.is_file() or sha(args.inputs)!=args.inputs_sha256:raise ValueError('Pinned offline invocation required')
    # Resolve imported code only from this already byte-verified package.
    sys.path.insert(0,str(root/'code'))
    from research.task_conditioned_reachability.execution_preparation.analysis_paths import relocated
    with relocated(mappings,allowed_roots=(root,args.inputs.absolute().parent,args.output.absolute().parent,*evidence_roots),strict=True):
        if args.mode=='phase':
            from research.task_conditioned_reachability.execution_preparation.run_observed_handover import run
            result=run(args.inputs,args.inputs_sha256,args.output,allow_fixture=args.allow_fixture)
        else:
            from research.task_conditioned_reachability.execution_preparation.run_exit_repair_evidence import run
            if not args.allow_fixture:
                invocation=json.loads(args.inputs.read_text())
                from research.task_conditioned_reachability.execution_preparation.observed_handover_analysis import read_pinned
                for item in invocation['items']:
                    prior=read_pinned(item['analysis_path'],item['analysis_sha256'])
                    obs=prior['normalized_observation']
                    if obs and obs['provenance']=='EXPLICIT_FIXTURE':raise ValueError('Explicit fixture opt-in required')
            result=run(args.inputs,args.inputs_sha256,args.output)
    result['sealed_bundle_sha256']=args.bundle_sha256
    result['runtime_or_model_or_data_role_admission']=False
    print(json.dumps(result,indent=2))


if __name__=='__main__':
    def fence(event,args):
        if event in ('socket.connect','subprocess.Popen','os.fork','os.exec'):
            raise PermissionError('Read-only analysis cannot connect/launch an execution stack')
    sys.addaudithook(fence);main()
