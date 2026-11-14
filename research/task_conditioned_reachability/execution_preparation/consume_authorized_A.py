"""Consume WM's ALREADY COMPLETED authorized A batch. Never execute its runner.

Numerical consistency / response diagnostic only. No actual outcomes, model
loading, world, training, score-to-ready conversion, or implicit world projection.
"""
import csv
from datetime import datetime
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
from .recorded_v9_diagnostics import load_recorded_owner_sources
from .native_climb_continuation import load_requirements
from .model_sufficiency import rows_from_raw_batch,analyze

RELEASE=Path('/home/yuanyue/re-nav/GO2-PIPER/docs/common_v9_A_three_candidate_predictions_v4.json')
RELEASE_SHA='dab33a0392aa369fa4fc167b5dc711f320464b07ccbbd7265b1ff4e810b80905'
INTEROP=Path('/home/yuanyue/re-nav/GO2-PIPER/scripts/piper_world_model/skill_effect_offline_v3/reach_interop.py')
INTEROP_SHA='9abc4b494f30cb1bb1deb3bc349f908e7b56735e83e300ef7bf040a4d40c2d22'
PACK=Path('/home/yuanyue/re-nav/artifacts/go2-piper-world-model/WM-day1-stage-producer-20261112-v1/candidate-input-pack.json')
PACK_SHA='8a29d435d0f64b4ab71af8c7bf632626b5fbeaed2c5fcbde914490c35a141951'


def read(path,digest):
    raw=Path(path).read_bytes()
    if hashlib.sha256(raw).hexdigest()!=digest:raise ValueError('Published A artifact changed; no silent repin or fallback to fake')
    return json.loads(raw)


def consume():
    release=read(RELEASE,RELEASE_SHA)
    if (release['schema']!='common-v9-authorized-A-three-candidate-predictions-v4'
        or release['is_real_inference'] is not True or release['synthetic'] is not False
        or release['real_runtime_qualified_for_this_completed_attempt'] is not True
        or release['checkpoint_sha256']!='7a6ba61e89d824cd3e0a78f469a0925f91c784ab1f77ed4273365d6c313f569c'):
        raise ValueError('Qualified completed real-A release required')
    public,original_rows=load_recorded_owner_sources()
    if release['query_input_sha256']!=public['input_sha256']:raise ValueError('One frozen query, not arbitrary new observation')
    selected={name:read(release[name]['path'],release[name]['sha256']) for name in ('result','all_candidate_outputs','replay_check','postcheck','closure')}
    result,output,replay,post,closure=(selected[k] for k in ('result','all_candidate_outputs','replay_check','postcheck','closure'))
    if (not replay['passed'] or not post['passed'] or not closure['closed'] or closure['cleanup_failed']
        or result['status']!='COMPLETED' or closure['automatic_retry']):raise ValueError('Incomplete/replay-mismatched A cannot enter accepted-response analysis')
    if any(result['call_attempts'][k]!=1 for k in ('load_attempts','causal_filter_attempts','predict_batch_attempts')):raise ValueError('Unexpected call budget')
    if (post['GPU_initialized'] or post['decoder_calls'] or post['grad_updates']
        or not post['shared_posterior_unchanged']):raise ValueError('Scope or common-state violation')
    pack=read(PACK,PACK_SHA)
    if hashlib.sha256(INTEROP.read_bytes()).hexdigest()!=INTEROP_SHA:raise ValueError('WM role-mapping source drift')
    old_path=sys.path[:]
    try:
        sys.path.insert(0,str(INTEROP.parent.parent))
        spec=importlib.util.spec_from_file_location('reach_real_A_owner_mapper',INTEROP)
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        payload=module.raw_batch_payload(result,output,dict(pack=pack))
    finally:sys.path[:]=old_path
    # No fixture opt-in: the real owner branch must preserve completed real role.
    if payload['source_role']!='AUTHORIZED_CAUSAL_PRODUCER_OUTPUT' or not payload['forward_executed']:
        raise ValueError('New real output must not be confused with fake CLI')
    normalized=rows_from_raw_batch(public,original_rows,payload)
    sufficient=analyze(public,normalized,load_requirements())
    raw_rows=[]
    for row in output['rows']:
        if row['frame']!='WORLD_POSITIVE_X' or row['actual_outcome_used'] or row['physical_dispatch']:
            raise ValueError('Producer role/frame/actual-data boundary changed')
        m=row['motion_mean_anchor_body_m']
        if (row['world_terminal_pose'] is not None or row['success_conditioned_cost'] is not None or row['next_ready'] is not None
            or row['actual_outcome_used']):raise ValueError('Unexpected new outcome/stage qualification, explicit adapter revision required')
        raw_rows.append(dict(distance_m=row['push_distance_m'],source_role=row['source_role'],
                             box_dx_anchor_body_m=m[0],robot_dx_anchor_body_m=m[2],
                             relative_box_minus_robot_dx_anchor_body_m=m[0]-m[2],
                             relative_displacement_is_not_world_clearance=True,
                             native_terminal_success_or_failure_elapsed_s=row['native_terminal_event_elapsed_s'],
                             successful_stage_cost_s=None,actual_next_ready=None,physical_dispatch=False))
    return dict(schema='reach-real-A-response-and-sufficiency-v1',at=datetime.now().astimezone().isoformat(),
                release_sha256=RELEASE_SHA,owner_source_mapper_sha256=INTEROP_SHA,
                query_input_sha256=public['input_sha256'],checkpoint_sha256=release['checkpoint_sha256'],
                data_role='AUTHORIZED_NEW_CAUSAL_MODEL_PREDICTIONS_UNCALIBRATED_NOT_PHYSICAL_OUTCOMES',
                raw_response_rows=raw_rows,original06_replay=replay,
                source_execution=release['execution'],levels=sufficient['levels'],
                sufficiency=sufficient,more_rows_fixed_only_action_response_coverage=True,
                prior_structural_NoGo_confirmed=True,world_terminal_pose_inferred=False,
                online_action=None,model_reloaded_by_Reach=False,new_forward_calls_by_Reach=0,
                actual_outcomes_opened=False,fit_norm_training=False,physical_dispatch=False)


if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    def fence(event,args):
        if event in ('socket.connect','subprocess.Popen'):raise PermissionError('Read completed A only; do not launch/rehydrate another batch')
    sys.addaudithook(fence)
    result=consume();a.output.mkdir(parents=True,exist_ok=False)
    with (a.output/'response-and-sufficiency.json').open('x') as f:json.dump(result,f,ensure_ascii=False,indent=2);f.write('\n')
    with (a.output/'three-candidate-response.csv').open('x') as f:
        w=csv.DictWriter(f,fieldnames=list(result['raw_response_rows'][0]));w.writeheader();w.writerows(result['raw_response_rows'])
    print(json.dumps(dict(raw_response=result['raw_response_rows'],levels=result['levels']),indent=2))
