"""Consume the first new complete-v6 ground result; no world or model replay.

Exact owner metadata/bytes and original PURE contracts recover query-clock and
entry-demand metrics. This is outcome EVIDENCE, never planner/fit input.
"""
import argparse
from copy import deepcopy
from dataclasses import fields
import hashlib
import importlib
import json
import math
from pathlib import Path
import sys

DATA_RELEASE_SHA='8acfef17d7cb4cb6a91e2f9dec26109c9f68b2c07b3123abd2f1783ac24b3774'
BASE_RELEASE_SHA='3098297041dbfa50dd1928ee81ce28c68d3458ed544cc494dea7374177b7c49e'


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--delivery',required=True);parser.add_argument('--mirror',required=True)
    parser.add_argument('--selected-package',required=True);parser.add_argument('--program-freeze',required=True)
    parser.add_argument('--raw-cost-analysis',required=True);parser.add_argument('--output',required=True)
    args=parser.parse_args();out=Path(args.output);out.mkdir(parents=True,exist_ok=False)
    attempts=[]
    def fence(event,values):
        if event in ('socket.connect','socket.getaddrinfo','subprocess.Popen','os.system','os.fork','os.posix_spawn'):
            attempts.append(event);raise RuntimeError('Offline fence: '+event)
        if event=='import' and str(values[0]).split('.')[0] in ('torch','numpy','mujoco','scipy','onnxruntime','requests','httpx'):
            attempts.append(str(values[0]));raise RuntimeError('No model/physics/numerical library')
    sys.addaudithook(fence)
    refs=[]
    def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
    def read(path,expected):
        path=Path(path);assert sha(path)==expected, 'Explicit source pin drift: '+str(path)
        refs.append(dict(path=str(path.resolve()),sha256=expected));return json.loads(path.read_text())
    delivery=Path(args.delivery);mirror=Path(args.mirror);package=Path(args.selected_package)
    release=read(delivery/'release.json',DATA_RELEASE_SHA)
    owner={name:read(delivery/name,h) for name,h in release['files'].items() if name.endswith('.json')}
    stage=owner['actual-stage-result.json'];audit=owner['stream-audit.json']
    base=read(package/'BASELINE_RELEASE_v1.json',BASE_RELEASE_SHA)
    raw=read(mirror/'result.json',release['primary_result_sha256'])
    program=read(args.program_freeze,release['source_program_sha256'])
    assert raw['reference_source_manifest_sha256']==program['original_source_manifest_sha256']==base['original_reference_manifest_sha256']
    assert raw['program_sha256']==release['source_program_sha256']==stage['program_sha256']
    assert raw['baseline_release_sha256']==BASE_RELEASE_SHA
    assert audit['all_stream_checks_passed'] and all(audit['checks'].values())
    assert raw['passed'] and raw['status']=='REQUESTED_API0_PASS' and not raw['close_errors']
    assert raw['episode_closure']['storage_complete'] and stage['actual_stow_verified']
    ledger=read(mirror.parent/'accounting/ledger.json',sha(mirror.parent/'accounting/ledger.json'))
    assert len(ledger['rows'])==2 and all(r['closed'] for r in ledger['rows'])
    assert ledger['rows'][-1]['report_sha256']==release['primary_result_sha256']
    journal=mirror/'events.jsonl';assert sha(journal)==release['primary_journal_sha256']
    records=[json.loads(line) for line in journal.read_text().splitlines()]
    assert len(records)==audit['actual_journal_rows']
    refs.append(dict(path=str(journal),sha256=release['primary_journal_sha256']))
    diagnostic=json.loads(Path(args.raw_cost_analysis).read_text())
    assert diagnostic['original_journal']['sha256']==release['primary_journal_sha256']
    assert diagnostic['original_journal']['last_sha256']==records[-1]['sha256']
    # The exact journal SHA must be in the owner's independently checked raw-source map.
    assert len([h for p,h in audit['raw_source_SHA'].items() if p.endswith('/main/events.jsonl') and h==release['primary_journal_sha256']])==1
    selected=[r for r in records if r['payload']['event']=='skill_intent_selected'];assert len(selected)==1
    selected=selected[0];sel=selected['payload']
    bindings=[r for r in records if r['payload']['event']=='intent_native_execution_bound']
    catalogues=[r for r in records if r['payload']['event']=='semantic_intent_catalogue' and r['sequence']<selected['sequence']]
    assert len(catalogues)==1 and len(bindings)==2
    # No host import/constructor. The original Observation/Intent/Entry/Placement
    # classes only validate metadata and compute their original digests/math.
    source=package/'reference-source';assert 'ainav' not in sys.modules;sys.path.insert(0,str(source))
    contracts=importlib.import_module('ainav.contracts');intents=importlib.import_module('ainav.intents')
    native=importlib.import_module('ainav.native.behavior_authority')
    entry=importlib.import_module('ainav.native.execution_judge')
    placement=importlib.import_module('ainav.native.placement_contract')
    support=importlib.import_module('ainav.native.push_support_gate')
    source_pins=[]
    for name,module in tuple(sys.modules.items()):
        if name=='ainav' or name.startswith('ainav.'):
            path=Path(module.__file__).resolve();key=str(path.relative_to(source.resolve()));h=sha(path)
            assert h==base['complete_reference_source_files_sha256'][key]
            source_pins.append(dict(path=str(path),sha256=h))
    def intent(value):
        v=deepcopy(value);v['parameters']=tuple(tuple(x) for x in v['parameters']);return intents.SkillIntent(**v)
    options=tuple(intent(v) for v in catalogues[0]['payload']['intents'])
    assert any(v.sha256==sel['intent_sha256'] for v in options)
    obs1_path=mirror/'intent-observation-0001.json';obs1=contracts.Observation(obs1_path.read_text().strip())
    first=bindings[0]['payload'];physical_number=int(first['physical_decision_id'].rsplit('-',1)[1])
    semantic_id='ainav-intent-%06d'%(physical_number-1)
    semantic=intents.IntentBatch(semantic_id,obs1,options,first['capability_contract'])
    assert semantic.sha256==sel['semantic_query_sha256']==stage['semantic_query_sha256']
    assert obs1.time_s==catalogues[0]['payload']['time_s']
    physical_proofs=[]
    for order,record in enumerate(bindings,1):
        b=record['payload'];p=mirror/('intent-observation-%04d.json'%order);obs=contracts.Observation(p.read_text().strip())
        assert obs.sha256==b['physical_observation_sha256']
        v=deepcopy(b['native_option']);v['parameters']=tuple(tuple(x) for x in v['parameters']);option=native.BehaviorOption(**v)
        assert option.sha256==b['native_option_sha256']
        batch=intents.ExecutionBatch(b['physical_decision_id'],obs,(option,),b['capability_contract'])
        assert batch.sha256==b['physical_query_sha256']
        physical_proofs.append(dict(role=b['execution_role'],observation_sha256=obs.sha256,physical_query_sha256=batch.sha256,metadata_original_class_digest_match=True))
        refs.append(dict(path=str(p),sha256=sha(p)))
    judgments=[]
    for record in records:
        p=record['payload']
        if p['event']!='skill_execution_judgment':continue
        assert p['intent_sha256']==sel['intent_sha256']
        spec=entry.EntrySpec(**p['spec']);state=entry.EntryState(**p['state'])
        value=entry.judge_entry(spec,state);assert value.sha256==p['judgment_sha256'] and value.status==p['status']
        measured=p['actual_private_measurement']
        witness=support.require_push_source_support(measured['push_source_bounds_xy_m'],spec.source_height_m,
            measured['feet_world_m'],measured['foot_vertical_load_N'])
        judgments.append(dict(source_sequence=record['sequence'],source_event_sha256=record['sha256'],
            original_judgment_sha256=value.sha256,source_status=value.status,time_s=state.time_s,
            original_spec_approach_xy_m=list(spec.approach_xy),recorded_base_xy_m=list(state.base_xy),
            recorded_xy_error_m=value.xy_error_m,recorded_translation_to_entry_disk_lower_bound_m=max(0.,value.xy_error_m-.16),
            original_12N_recorded_support_function_passed=witness['four_current_feet_loaded'],
            actual_full_native_entry_or_dynamic_safety_inferred=False))
    attached=next(r['payload'] for r in records if r['payload']['event']=='full_task_existing_placement_attached')
    c=attached['placement_contract'];keys={f.name for f in fields(placement.PlacementContract)}
    v={k:c[k] for k in keys};v['public_goal_xy_m']=tuple(v['public_goal_xy_m']);v['box_size_m']=tuple(v['box_size_m'])
    contract=placement.PlacementContract(**v);actual=stage['actual_final_placement']['placement']
    assert attached['selected_option_sha256']==bindings[-1]['payload']['native_option_sha256']
    assert contract.sha256==actual['contract_sha256']
    checked=contract.evaluate(box_position=actual['actual_box_position_m'],rotation_world_from_box=actual['actual_box_rotation'],native_goal_xy=contract.drive_goal_xy_m)
    assert checked['placement_geometry_verified'] and abs(checked['public_XY_error_m']-actual['public_XY_error_m'])<1e-14
    q=obs1.time_s;rows=diagnostic['rows'];prep=next(r for r in rows if r['role']=='preparation');push=next(r for r in rows if r['role']=='interaction')
    confirm=stage['actual_native_NN_confirmation']['time_s'];compact=stage['actual_arm_compact_event']['time'];end=stage['actual_final_placement']['time_s']
    assert q<=prep['native_started_s']<=prep['native_terminal_s']<=push['native_started_s']<=confirm<=compact<=end
    assert end==push['native_terminal_s']
    costs=dict(query_to_first_native_start_s=prep['native_started_s']-q,
        original_NAV_preparation_window_s=prep['observed_native_window_s'],
        preparation_terminal_to_PUSH_started_s=push['native_started_s']-prep['native_terminal_s'],
        PUSH_started_to_original_NN_confirmation_s=confirm-push['native_started_s'],
        NN_confirmation_to_actual_arm_compact_s=compact-confirm,
        actual_arm_compact_to_final_latched_receipt_s=end-compact)
    assert abs(sum(costs.values())-(end-q))<1e-9
    result=deepcopy(diagnostic)
    result.update(role='ACTUAL_NEW_ENGINEERING_OUTCOME_AUDIT_ONLY_NOT_PLANNER_OR_FIT',
        source_manifest_sha256=raw['reference_source_manifest_sha256'],selected_executor_source_matches=True,
        source_scope='OWNER_REAL_MAIN_RESULT_AND_RAW_JOURNAL_MATCHED_TO_SELECTED_PROGRAM',run_closure_verified=True,
        original_program_sha256=raw['program_sha256'],semantic_query_time_s=q,
        semantic_query_identity_proof=dict(original_class_sha256=semantic.sha256,selected_record_sha256=sel['semantic_query_sha256'],
            observation_sha256=obs1.sha256,decision_id=semantic_id,serialized_metadata_only_no_image_or_Runtime_reload=True),
        physical_query_identity_proofs=physical_proofs,recorded_entry_judgment_proofs=judgments,
        disjoint_query_to_PUSH_completion_parts_s=costs,query_to_requested_PUSH_completion_s=end-q,
        NN_confirmation_to_final_Push_stow_receipt_s=end-confirm,
        query_to_after_goal_and_next_skill_preparation_s=None,actual_next_Actor_ready=None,
        requested_engineering_PASS=True,full_navigation_success=False,Reach_method_gain_proven=False,
        first_new_engineering_run_not_new_independent_TEST_or_training_admission=True,
        measured_public_XY_error_m=checked['public_XY_error_m'],measured_signed_dock_gap_m=checked['actual_signed_dock_gap_m'],
        original_contract_final_geometry_recomputed=True,original_source_metadata_pins=source_pins,
        independently_reexecuted_physics_or_raw_stream_audit=False,additional_pinned_inputs=refs,fence_attempts=attempts)
    (out/'qualified-first-result-analysis.json').write_text(json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
    print(json.dumps(dict(query_time_s=q,query_to_requested_PUSH_completion_s=end-q,disjoint_parts_s=costs,
        NN_confirmation_to_final_receipt_s=end-confirm,original_entry_judgments=judgments,
        public_XY_error_m=checked['public_XY_error_m'],signed_dock_gap_m=checked['actual_signed_dock_gap_m'],fence_attempts=attempts),ensure_ascii=False))


if __name__=='__main__':main()
