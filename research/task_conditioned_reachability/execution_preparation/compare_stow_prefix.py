"""Owner-invoked, streaming CLOSED NPZ pair check; never a physics launcher.

Read only already-recorded issued/delayed/PD/state arrays. This is the narrow
intervention-prefix comparison, NOT a repetition of the full stream audit.
Large arrays stay at Data; all outputs are evidence-only, never optimizer input.
"""
import hashlib
import json
from pathlib import Path

FIELDS=('issued','delayed','q_before','dq_before','raw_torque','torque')


def need(ok,msg):
    if not ok:raise ValueError(msg)


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def _capture(raw):
    found=[]
    for result in raw.get('actual_native_results',[]):
        if result.get('skill')!='push':continue
        for e in result.get('finish',{}).get('protected_stow',{}).get('events',[]):
            if e.get('event')=='actual_unloaded_supported_retreat_and_full_path_checked':found.append(e['time'])
    return found[0] if len(found)==1 else None


def compare_closed_prefix(baseline_root,candidate_root,*,baseline_result_sha256,candidate_result_sha256):
    import numpy as np  # Already-owned analysis environment only; no package installation.
    refs=[]
    def read(p,expected):
        need(not p.is_symlink() and sha(p)==expected,'Pinned closed metadata drift: '+str(p))
        refs.append(dict(path=str(p.resolve()),sha256=expected));return json.loads(p.read_text())
    roots=[Path(x).resolve() for x in (baseline_root,candidate_root)]
    need(roots[0]!=roots[1] and baseline_result_sha256!=candidate_result_sha256,'Distinct closed runs, not self-comparison')
    raws=[read(r/'result.json',h) for r,h in zip(roots,(baseline_result_sha256,candidate_result_sha256))]
    indices=[]
    for root,raw in zip(roots,raws):
        closure=raw['episode_closure']
        need(closure['storage_complete'] is True,'Closed stored episode required; not a live array tail')
        indices.append(read(root/'episode/index.json',closure['index_sha256']))
    def chunks(root,index):
        expected=1
        for row in index['commands']:
            rel=Path(row['path']);p=root/'episode'/rel
            need(not rel.is_absolute() and '..' not in rel.parts and not p.is_symlink() and
                 p.resolve().is_relative_to(root/'episode') and sha(p)==row['sha256'],'Pinned existing command chunk only')
            with np.load(p,allow_pickle=False) as z:
                ticks=z['physical_tick'];times=z['time_s'];n=len(ticks)
                need(n>0 and np.array_equal(ticks,np.arange(expected,expected+n)),'Continuous original200Hz physical ticks')
                need(np.allclose(times,ticks*.005,rtol=0,atol=1e-7),'Original time/tick identity')
                arrays={k:z[k] for k in FIELDS}
                need(all(len(a)==n and np.isfinite(a).all() for a in arrays.values()),'Finite recorded prefix arrays')
                need(arrays['issued'].shape==(n,5,18) and arrays['delayed'].shape==(n,5,18),'Original issued/delayed ABI')
                need(all(arrays[k].shape==(n,18) for k in FIELDS[2:]),'Original joint/torque ABI')
                refs.append(dict(path=str(p.resolve()),sha256=row['sha256']))
                yield arrays
                expected+=n
    streams=[iter(chunks(r,ix)) for r,ix in zip(roots,indices)]
    buffers=[None,None];offsets=[0,0];first={k:None for k in FIELDS};compared=0
    while True:
        ended=False
        for i in (0,1):
            if buffers[i] is None or offsets[i]==len(buffers[i]['issued']):
                buffers[i]=next(streams[i],None);offsets[i]=0
                if buffers[i] is None:ended=True
        if ended:break
        n=min(len(buffers[i]['issued'])-offsets[i] for i in (0,1))
        for field in FIELDS:
            if first[field] is not None:continue
            a,b=(buffers[i][field][offsets[i]:offsets[i]+n] for i in (0,1))
            if a.dtype!=b.dtype:
                first[field]=compared+1;continue
            # Exact BIT equality, not allclose (even signed zero differs).
            aa=a.view(np.uint8).reshape(n,-1);bb=b.view(np.uint8).reshape(n,-1)
            diff=np.flatnonzero(np.any(aa!=bb,axis=1))
            if len(diff):first[field]=compared+int(diff[0])+1
        compared+=n;offsets=[x+n for x in offsets]
    captures=[_capture(raw) for raw in raws]
    same_capture=(all(type(t) in (int,float) for t in captures) and abs(captures[0]-captures[1])<=1e-9)
    tick=round(captures[1]/.005) if same_capture else None
    if tick is not None:need(abs(captures[1]-tick*.005)<1e-7,'Recorded capture on original200Hz grid')
    same_requests=raws[0].get('selected_requests') is not None and raws[0].get('selected_requests')==raws[1].get('selected_requests')
    model_same=(raws[0].get('actual_model_numeric_sha256') is not None and raws[0].get('actual_model_numeric_sha256')==raws[1].get('actual_model_numeric_sha256'))
    scope_same=raws[0].get('scope_id')==raws[1].get('scope_id')
    matched={k:(compared>=tick and (v is None or v>tick)) if tick is not None else None for k,v in first.items()}
    eligible=same_requests and model_same and not scope_same and same_capture and compared>=tick
    return dict(schema='reach-owner-closed-stow-intervention-prefix-v1',role='AUDIT_ONLY_NOT_PLANNER_INPUT_OR_FIT',
        baseline_result_sha256=baseline_result_sha256,candidate_result_sha256=candidate_result_sha256,
        baseline_scope_id=raws[0].get('scope_id'),candidate_scope_id=raws[1].get('scope_id'),
        same_requests=same_requests,same_numeric_model=model_same,original_capture_times_s=captures,
        capture_boundary_physics_tick=tick,compared_common_physics_steps=compared,
        first_bitwise_difference_tick=first,bitwise_equal_through_capture_by_field=matched,
        prefix_match=(all(matched.values()) if eligible else None),
        different_motor_commands_observed=first['issued'] is not None,
        comparison_covers_only_recorded_command_and_joint_arrays_not_full_base_contact_state=True,
        native_safety_or_causal_task_benefit_or_new_solver_proven=False,source_inputs=refs,new_physics_or_model_calls=0)


def main():
    import argparse,sys
    p=argparse.ArgumentParser(description=__doc__)
    for k in ('baseline-root','candidate-root','baseline-result-sha256','candidate-result-sha256','output'):
        p.add_argument('--'+k,required=True)
    a=p.parse_args()
    def fence(event,args):
        if event in ('socket.connect','socket.getaddrinfo','subprocess.Popen','os.system','os.fork','os.posix_spawn'):
            raise RuntimeError('Only recorded closed arrays: '+event)
        if event=='import' and str(args[0]).split('.')[0] in ('torch','mujoco','onnxruntime','requests','httpx'):
            raise RuntimeError('No Runtime/Actor/native simulation/model')
    sys.addaudithook(fence)
    result=compare_closed_prefix(a.baseline_root,a.candidate_root,baseline_result_sha256=a.baseline_result_sha256,candidate_result_sha256=a.candidate_result_sha256)
    with Path(a.output).open('x') as f:json.dump(result,f,ensure_ascii=False,indent=2,allow_nan=False);f.write('\n')
    print(json.dumps({k:result[k] for k in ('prefix_match','capture_boundary_physics_tick','first_bitwise_difference_tick')},ensure_ascii=False))


if __name__=='__main__':main()
