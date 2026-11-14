"""Pinned closed-result reader for actual stow selection effects (no replay).

This reader does not self-sign a method comparison. Command-array prefix/source
qualification must come from owner evidence bound to the particular pair.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys
from .stow_choice_effects import audit_effect, compare_effects, compare_with_bound_prefix


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('result','result-sha256','journal','journal-sha256','output'):p.add_argument('--'+key,required=True)
    for key in ('baseline-result','baseline-result-sha256','baseline-journal','baseline-journal-sha256'):
        p.add_argument('--'+key)
    p.add_argument('--prefix-receipt');p.add_argument('--prefix-receipt-sha256')
    for key in ('candidate-freeze','candidate-fork-manifest','baseline-freeze'):
        p.add_argument('--'+key);p.add_argument('--'+key+'-sha256')
    p.add_argument('--selected-package',default='/home/yuanyue/main/work/ainav/consumer-deliveries/AINAV-ABSOLUTE-PLACEMENT-BASELINE-20261113-v1')
    a=p.parse_args();attempts=[];refs=[]
    def fence(event,args):
        if event in ('socket.connect','socket.getaddrinfo','subprocess.Popen','os.system','os.fork','os.posix_spawn'):
            attempts.append(event);raise RuntimeError('Closed metadata only: '+event)
        if event=='import' and str(args[0]).split('.')[0] in ('numpy','torch','mujoco','scipy','onnxruntime','requests','httpx'):
            attempts.append(str(args[0]));raise RuntimeError('No native/physics/model or array replay')
    sys.addaudithook(fence)
    def read_bytes(path,digest):
        path=Path(path)
        if not path.is_absolute() or path.is_symlink():raise ValueError('Explicit absolute original file required')
        raw=path.read_bytes()
        if hashlib.sha256(raw).hexdigest()!=digest:raise ValueError('Source pin mismatch: '+str(path))
        refs.append(dict(path=str(path),sha256=digest))
        return raw
    def read(path,digest,lines=False):
        raw=read_bytes(path,digest)
        return [json.loads(s) for s in raw.decode().splitlines()] if lines else json.loads(raw)
    def effect(result,result_sha,journal,journal_sha):
        r=read(result,result_sha);records=read(journal,journal_sha,True)
        if r.get('phase') not in (None,'main'):raise ValueError('Actual main result required, not successful own-zero')
        # Failure/partial results are kept, not coerced to PASS. A published
        # closed result requires no outstanding teardown errors and an explicit
        # episode storage closure. Absence is UNKNOWN, never an execution gate.
        answer=audit_effect(r,records)
        answer['owner_episode_storage_closed']=r.get('episode_closure',{}).get('storage_complete')
        answer['owner_close_errors']=r.get('close_errors')
        answer['input_result_sha256']=result_sha;answer['input_journal_sha256']=journal_sha
        return answer
    candidate=effect(a.result,a.result_sha256,a.journal,a.journal_sha256)
    result=dict(candidate=candidate,source_inputs=refs,fence_attempts=attempts,
                no_new_execution_or_planner_fit_input=True)
    opts=(a.baseline_result,a.baseline_result_sha256,a.baseline_journal,a.baseline_journal_sha256)
    if any(x is not None for x in opts):
        if not all(x is not None for x in opts):raise ValueError('Complete explicitly pinned baseline metadata required')
        baseline=effect(*opts);result['baseline']=baseline
        source_evidence=None
        source_args=(a.candidate_freeze,a.candidate_freeze_sha256,a.candidate_fork_manifest,a.candidate_fork_manifest_sha256,a.baseline_freeze,a.baseline_freeze_sha256)
        if any(x is not None for x in source_args):
            if not all(x is not None for x in source_args):raise ValueError('Complete explicitly pinned freeze/fork evidence required')
            from .stow_source_qualification import qualify_source_pair,BASE_RELEASE_SHA,V2_BUNDLE_SHA
            package=Path(a.selected_package)
            bundle=Path(__file__).resolve().parents[3]/'evidence/2026-11-13/stow-target-view-repair-v2/delta-bundle/manifest.json'
            release_raw=read_bytes(package/'BASELINE_RELEASE_v1.json',BASE_RELEASE_SHA)
            declared=json.loads(release_raw)
            inputs=dict(baseline_result_bytes=read_bytes(a.baseline_result,a.baseline_result_sha256),
                candidate_result_bytes=read_bytes(a.result,a.result_sha256),
                baseline_freeze_bytes=read_bytes(a.baseline_freeze,a.baseline_freeze_sha256),
                candidate_freeze_bytes=read_bytes(a.candidate_freeze,a.candidate_freeze_sha256),
                fork_manifest_bytes=read_bytes(a.candidate_fork_manifest,a.candidate_fork_manifest_sha256),
                baseline_release_bytes=release_raw,
                baseline_consumer_bytes=read_bytes(package/'absolute_baseline_consumer.py',declared['consumer_code_sha256']),
                v2_bundle_manifest_bytes=read_bytes(bundle,V2_BUNDLE_SHA))
            try:source_evidence=qualify_source_pair(**inputs)
            except (ValueError,KeyError,TypeError) as e:
                # Declared-source evidence failure does not relabel the original
                # native success/failure. It prevents attribution, not execution.
                source_evidence=dict(source_pair_verified=False,status='SOURCE_PAIR_NOT_QUALIFIED',error_type=type(e).__name__,error=str(e))
            result['declared_source_pair_qualification']=source_evidence
        # Do not silently reuse the P1/P2 shared-prefix proof for a new run.
        if a.prefix_receipt or a.prefix_receipt_sha256:
            if not (a.prefix_receipt and a.prefix_receipt_sha256):raise ValueError('Explicit prefix receipt SHA required')
            prefix=read(a.prefix_receipt,a.prefix_receipt_sha256)
            result['comparison']=compare_with_bound_prefix(baseline,candidate,prefix,source_pair_evidence=source_evidence)
        else:result['comparison']=compare_effects(baseline,candidate)
    elif any((a.prefix_receipt,a.prefix_receipt_sha256,a.candidate_freeze,a.candidate_freeze_sha256,a.candidate_fork_manifest,a.candidate_fork_manifest_sha256,a.baseline_freeze,a.baseline_freeze_sha256)):
        raise ValueError('Prefix/source evidence requires a pinned baseline too')
    with Path(a.output).open('x') as f:json.dump(result,f,ensure_ascii=False,indent=2,allow_nan=False);f.write('\n')
    print(json.dumps(dict(status=candidate['intervention_status'],costs=candidate['actual_costs_s']),ensure_ascii=False))


if __name__=='__main__':main()
