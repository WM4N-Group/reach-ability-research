"""Pinned P2 incremental EVIDENCE consumption; no array re-audit or planner input.

Recompute actual receipt windows and original CLIMB EntryJudgment/ExecutionBatch
metadata. Shared command prefix remains OWNER-audited, not independently read.
"""
import argparse
from copy import deepcopy
import hashlib
import importlib
import json
from pathlib import Path
import sys

RELEASE_SHA='d9b6198c7ea5253a23efa878af6d943fdb4fb23709b99a8c8645ceba1420df49'
BASE_SHA='3098297041dbfa50dd1928ee81ce28c68d3458ed544cc494dea7374177b7c49e'


def consume(delivery, mirror, selected_package):
    delivery,mirror,selected_package=map(Path,(delivery,mirror,selected_package))
    refs=[]
    def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
    def read(path,expected,*,lines=False):
        if sha(path)!=expected:raise ValueError('Source pin drift: '+str(path))
        refs.append(dict(path=str(path.resolve()),sha256=expected))
        return [json.loads(l) for l in path.read_text().splitlines()] if lines else json.loads(path.read_text())
    release=read(delivery/'release.json',RELEASE_SHA)
    owner={k:read(delivery/k,v) for k,v in release['files'].items() if k.endswith('.json')}
    stage=owner['actual-successor-stage-costs.json']
    base=read(selected_package/'BASELINE_RELEASE_v1.json',BASE_SHA)
    raw=read(mirror/'result.json',release['primary_result_sha256'])
    records=read(mirror/'events.jsonl',release['primary_journal_sha256'],lines=True)
    if not (release['scope_closed'] and raw['passed'] and raw['status']=='REQUESTED_API0_PASS'
            and not raw['close_errors'] and raw['episode_closure']['storage_complete']
            and raw['program_sha256']==release['source_program_sha256']
            and raw['baseline_release_sha256']==BASE_SHA
            and raw['reference_source_manifest_sha256']==base['original_reference_manifest_sha256']):
        raise ValueError('Exact original completed P2 evidence required')
    # Do not import Runtime, a host, Actor or model. Load original pure classes.
    source=(selected_package/'reference-source').resolve()
    if 'ainav' in sys.modules:raise ValueError('Run in a fresh offline process, no foreign ainav module')
    sys.dont_write_bytecode=True  # selected delivery is read-only, including caches
    sys.path.insert(0,str(source))
    contracts=importlib.import_module('ainav.contracts')
    intents=importlib.import_module('ainav.intents')
    native=importlib.import_module('ainav.native.behavior_authority')
    entry=importlib.import_module('ainav.native.execution_judge')
    source_pins=[]
    for name,module in tuple(sys.modules.items()):
        if name=='ainav' or name.startswith('ainav.'):
            path=Path(module.__file__).resolve();rel=str(path.relative_to(source))
            if sha(path)!=base['complete_reference_source_files_sha256'][rel]:
                raise ValueError('Original class source drift: '+rel)
            source_pins.append(dict(path=str(path),sha256=sha(path)))
    def payloads(event):return [r for r in records if r['payload']['event']==event]
    def intent(v):
        v=deepcopy(v);v['parameters']=tuple(tuple(x) for x in v['parameters'])
        return intents.SkillIntent(**v)
    selected=payloads('skill_intent_selected')
    if len(selected)!=2:raise ValueError('Two original engineering requests required')
    selected=selected[-1];selected_intent=intent(selected['payload']['intent'])
    if selected_intent.skill!='CLIMB':raise ValueError('Actual successor is not CLIMB')
    bindings=[r for r in payloads('intent_native_execution_bound') if r['payload']['intent_sha256']==selected_intent.sha256]
    catalogue=[r for r in payloads('semantic_intent_catalogue') if r['sequence']<selected['sequence']][-1]
    options=tuple(intent(v) for v in catalogue['payload']['intents'])
    first=bindings[0]['payload'];obs=contracts.Observation((mirror/'intent-observation-0003.json').read_text().strip())
    semantic_id='ainav-intent-%06d'%(int(first['physical_decision_id'].rsplit('-',1)[1])-1)
    query=intents.IntentBatch(semantic_id,obs,options,first['capability_contract'])
    if query.sha256!=selected['payload']['semantic_query_sha256'] or selected_intent.sha256!=selected['payload']['intent_sha256']:
        raise ValueError('Original semantic intent/query digest mismatch')
    windows=[];metadata=[]
    for order,r in enumerate(bindings,3):
        b=r['payload'];path=mirror/('intent-observation-%04d.json'%order)
        obs=contracts.Observation(path.read_text().strip())
        refs.append(dict(path=str(path.resolve()),sha256=sha(path)))
        v=deepcopy(b['native_option']);v['parameters']=tuple(tuple(x) for x in v['parameters'])
        option=native.BehaviorOption(**v)
        batch=intents.ExecutionBatch(b['physical_decision_id'],obs,(option,),b['capability_contract'])
        if not (obs.sha256==b['physical_observation_sha256'] and option.sha256==b['native_option_sha256']
                and batch.sha256==b['physical_query_sha256']):raise ValueError('Original physical metadata digest mismatch')
        receipts=[r for r in payloads('ainav_native_receipt') if r['payload']['receipt']['option_sha256']==option.sha256]
        if [r['payload']['receipt']['status'] for r in receipts]!=['started','succeeded']:
            raise ValueError('Exact literal successor receipts required')
        a,z=[r['payload']['receipt']['time_s'] for r in receipts]
        windows.append(dict(role=b['execution_role'],native_skill=option.skill,first_motor_s=a,terminal_s=z,
                            duration_s=z-a,receipt_sequences=[r['sequence'] for r in receipts]))
        metadata.append(dict(role=b['execution_role'],original_option_sha256=option.sha256,
                             original_observation_sha256=obs.sha256,original_query_sha256=batch.sha256))
    judgments=[]
    for r in payloads('skill_execution_judgment'):
        p=r['payload']
        if p['intent_sha256']!=selected_intent.sha256:continue
        value=entry.judge_entry(entry.EntrySpec(**p['spec']),entry.EntryState(**p['state']))
        if value.sha256!=p['judgment_sha256'] or value.status!=p['status']:
            raise ValueError('Original CLIMB entry judgment mismatch')
        judgments.append(dict(sequence=r['sequence'],envelope_sha256=r['sha256'],judgment_sha256=value.sha256,
                              status=value.status,time_s=value.state.time_s,
                              original_reference_approach_xy_m=list(value.spec.approach_xy),
                              recorded_xy_error_m=value.xy_error_m))
    if [v['status'] for v in judgments]!=['PREPARE','READY']:raise ValueError('Original prepare/ready order required')
    boundary=payloads('completed_placement_boundary_latched')
    confirmation=payloads('placement_original_native_clock_confirmed')
    if len(boundary)!=1 or len(confirmation)!=1 or len(windows)!=2:raise ValueError('Unique original boundaries required')
    stow=boundary[0]['payload']['time_s'];nn=confirmation[0]['payload']['time_s']
    prep,climb=windows
    if not (prep['native_skill']=='NAV' and climb['native_skill']=='CLIMB'
            and stow<=prep['first_motor_s']<=prep['terminal_s']<=climb['first_motor_s']<=climb['terminal_s']
            and judgments[-1]['time_s']==prep['terminal_s']):raise ValueError('Same-world native boundary mismatch')
    costs=dict(actual_native_NN_confirmation_to_guarded_stow_s=stow-nn,
               actual_after_stow_to_CLIMB_first_motor_s=climb['first_motor_s']-stow,
               actual_after_stow_to_CLIMB_terminal_s=climb['terminal_s']-stow,
               actual_successor_preparation_native_window_sum_s=prep['duration_s'])
    for key,value in costs.items():
        if abs(value-stage['stage_costs'][key])>1e-10:raise ValueError('Owner stage cost mismatch: '+key)
    ready_pointer=stage['actual_original_CLIMB_entry_judgment_source']
    if ready_pointer['one_based_line']!=judgments[-1]['sequence']+1 or ready_pointer['envelope_sha256']!=judgments[-1]['envelope_sha256']:
        raise ValueError('Owner corrected structured READY pointer mismatch')
    return dict(schema='reach-P2-incremental-original-consumer-evidence-v1',role='AUDIT_ONLY_NOT_PLANNER_INPUT_OR_FIT',
        original_source_and_completed_result_identity_checked=True,original_journal_sha256=release['primary_journal_sha256'],
        journal_rows_read=len(records),necessary_successor_records_independently_consumed=True,
        independent_whole_stream_or_command_array_audit=False,semantic_query_sha256=query.sha256,
        original_successor_metadata=metadata,original_successor_windows=windows,original_CLIMB_judgments=judgments,
        actual_stow_terminal_s=stow,recomputed_costs_s=costs,
        decomposition_after_stow_s=dict(wait_to_NAV=prep['first_motor_s']-stow,original_NAV=prep['duration_s'],
            wait_to_CLIMB=climb['first_motor_s']-prep['terminal_s'],original_CLIMB=climb['duration_s']),
        owner_only_common_prefix_bitwise_equal=release['common_prefix_bitwise_equal'],
        owner_only_common_prefix_steps=release['common_command_prefix_steps'],
        actor_activation_time_s=None,method_advantage_proven=False,independent_generalization_samples_added=0,
        new_physics_or_model_calls=0,source_inputs=refs,pure_original_class_source_pins=source_pins)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for arg in ('delivery','mirror','selected-package','output'):p.add_argument('--'+arg,required=True)
    args=p.parse_args()
    attempts=[]
    def fence(event,values):
        if event in ('socket.connect','socket.getaddrinfo','subprocess.Popen','os.system','os.fork','os.posix_spawn'):
            attempts.append(event);raise RuntimeError('Offline evidence-only fence: '+event)
        if event=='import' and str(values[0]).split('.')[0] in ('torch','numpy','mujoco','scipy','onnxruntime','requests','httpx'):
            attempts.append(str(values[0]));raise RuntimeError('No physics/model/numerical library')
    sys.addaudithook(fence)
    result=consume(args.delivery,args.mirror,args.selected_package);result['fence_attempts']=attempts
    out=Path(args.output);out.mkdir(parents=True,exist_ok=False)
    (out/'consumption.json').write_text(json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
    print(json.dumps(result['recomputed_costs_s'],indent=2))


if __name__=='__main__':main()
