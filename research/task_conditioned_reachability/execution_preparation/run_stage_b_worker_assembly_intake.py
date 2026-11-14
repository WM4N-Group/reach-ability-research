"""Consume pinned Data preconstruction receipts; no prepare/import/dispatch.

A source/input comparability check, not a worker test or native qualification.
Only SHA-verified immutable owner-release bytes are read. NEVER load checkpoints,
create scopes, connect to remote hosts, or interpret SOFTWARE probes as episodes.
"""
from pathlib import Path
import argparse
import hashlib
import json
from .successor_preparation_intake import verify_release
from .successor_aware_choice import need

ROOT='/home/yuanyue/main/work/data-team/consumer-deliveries/AINAV-DATA-STAGEB-NEW-WORKER-CPU-ASSEMBLY-20261114-v1'
RELEASE='e24695b8147a3939b5c3ca2705ec98191ffdc990fb7d0c3ad4712d4ce250fa50'
IDS=('original','lateral_plus_0p04','lateral_minus_0p04')
INITIAL='bf3e2e1f76422adf1a77b1eeae132c2fed36a36058763909d3c52b303bb96da8'
PROTOCOL='dfea3ec252ad995fcb9f4c0ed7f368b3b570e94dcef826bea6577ad68003371d'
EFFECT='39f4dc5ba75085d744d6abbb54c15789a98e8aa1fc041ecc59db08d2d9e11dc8'


def digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()


def difference_paths(a,b,path=''):
    if type(a)!=type(b):return [path]
    if type(a) is dict:
        return [p for key in sorted(set(a)|set(b)) for p in
                ([path+'/'+key] if key not in a or key not in b else difference_paths(a[key],b[key],path+'/'+key))]
    if type(a) is list:
        if len(a)!=len(b):return [path]
        return [p for i,(v,w) in enumerate(zip(a,b)) for p in difference_paths(v,w,path+'/'+str(i))]
    return [] if a==b else [path]


def consume():
    owner=verify_release(ROOT,'release.json',expected_release_sha256=RELEASE,inventory_field='files')
    probes={cid:owner.document('evidence/'+cid+'-v2.stdout') for cid in IDS}
    initial=owner.document('evidence/common-initial-constructor-and-RNG-binding.json')
    overlay=owner.document('evidence/bound-scientific-inputs-and-recording-overlay.json')
    science=overlay['inherited_scientific_preregistration']
    need(digest(initial)==INITIAL==overlay['initial_binding_sha256'], 'Exact common constructor/input binding')
    need(digest(science)==overlay['science_preregistration_sha256']==
         overlay['inherited_source_bound_validation']['preregistration_sha256'], 'Exact N=3 preregistration content')
    need(science['Reach_protocol_sha256']==PROTOCOL and len(science['branches'])==3,
         'Original shared three-branch protocol')
    changes={}
    records=[]
    for cid,offset in zip(IDS,(0.,.04,-.04)):
        row=probes[cid];plan=row['plan']
        need(row['candidate_id']==cid and plan['candidate_id']==cid and plan['seed']==4301,
             'Fixed branch and original seed, not winner-conditioned initial state')
        need(row['initial_binding']==initial and row['initial_binding_sha256']==INITIAL,
             'Same literal configuration/checkpoints/initialization lineage across branches')
        need(plan['native_config_delta']=={'actor_device':{'original':'cpu','actual':'cuda:0'}},
             'Only originally declared device overlay, no silent dynamics/profile change')
        need(row['new_physical_calls']==0 and row['physical_admission'] is False and
             row['actual_Host_constructor_executed'] is False and
             row['actual_runtime_model_capture_or_geometry_constructed'] is False and
             row['geometry_entry_is_explicit_software_port'] is True and
             row['native_module_attempts']==[], 'Keep owner SOFTWARE graph evidence at its actual level')
        need(row['bindings']['same_stow_for_every_branch'] is True and
             row['previous_PUSH_root_proxy_selected_view_not_collapsed'] is True,
             'Common v2 stow and original root/proxy relationships retained in software graph')
        params=dict(row['native_NAV_option']['parameters'])
        need(params==dict(goal_world_x_m=.050000000000000044,goal_world_y_m=-2.+offset,surface_height_m=0.),
             'Source caller actually consumed only the finite NAV subgoal')
        need(plan['preparation_payload']==science['branches'][IDS.index(cid)]['execution_payload'] and
             plan['scope_id']==science['branches'][IDS.index(cid)]['new_scope_id'],
             'Published preregistration/plan payload and scope names must match')
        changes[cid]=difference_paths(probes['original']['plan'],plan)
        need(changes[cid]==([] if cid=='original' else
             ['/candidate_id','/preparation_payload/candidate_id','/scope_id']),
             'Unexpected cross-branch plan differences; no method-specific control/source/initialization')
        records.append(dict(candidate_id=cid,proposed_scope_id=plan['scope_id'],
            effective_NAV_parameters=params,plan_sha256=digest(plan),initial_binding_sha256=INITIAL,
            differences_from_original=changes[cid],scope_created_or_executed_by_this_reader=False))
    need(initial['seed']==4301 and initial['no_random_perturbation_or_seed_selection'] is True and
         initial['actual_full_hidden_state_equality'] is False, 'No hidden-state equality overclaim')
    need(len(initial['actor_files'])==4 and overlay['recording_overlay']['enabled'] is True and
         overlay['recording_overlay']['optional_not_native_success_gate'] is True,
         'Four original checkpoint declarations and explicit optional live-camera overlay')
    return dict(schema='Reach-consumed-Data-new-worker-input-comparability-v1',
        role='CPU_PUBLISHED_SOURCE_AND_INPUT_COMPARABILITY_NOT_NATIVE_ADMISSION',
        Data_release_sha256=RELEASE, verified_member_count=len(owner.members),
        common_initial_input_binding_sha256=INITIAL, science_preregistration_sha256=digest(science),
        cross_branch_plan_difference_paths=changes,source_branch_receipts=records,
        same_seed_config_original_initialization_and_checkpoint_declarations=True,
        checkpoint_bytes_loaded_or_independently_remote_verified_by_Reach=False,
        actual_hidden_model_or_RNG_equivalence='UNKNOWN_NOT_PROVED_BY_SAME_INPUTS',
        original_host_and_native_callsite='Executed in owner software graph, not actual Host/Runtime/capture constructor',
        current_owner_complete_program_freeze=False,physical_admission=False,dispatch=False,
        source_control_alias_fix='Owner now binds exact actually-loaded namespaces; no forced archived-alias import; initial CPU import failures retained',
        raw_camera_overlay='Explicit enabled 192x128/stride20/128MiB optional live capture; actual native camera qualification remains pending',
        previous_11_tests_and3_probes_consumed_not_rerun_or_recounted=True,
        practical_threshold_draft_marker=science['practical_threshold_owner'],
        effect_confirmation_file_sha256=EFFECT,
        effect_confirmation_note='Old draft says Reach pending; attach immutable Reach confirmation supplement at NEW full-program freeze, do not mutate historical release',
        effect_acceptance_not_a_new_native_success_gate=True,
        still_required=['Data exact full-program/fenced entrypoint freeze and canonical authority/lease',
            'This new program own-zero actual model/Actor/root-proxy/capture/geometry/QP integration',
            'Actual paired prefix comparability and distinct control/whole-chain outcomes, not software graph receipts',
            'If enabled: actual live-camera identity/clock/resource qualification in same new program'],
        new_H1_physical_or_independent_TEST_cases=0,new_worlds_or_roots_or_remote_tasks_started=0,
        all_old_closed_scopes_dirty_and_native_gates_preserved=True)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    value=consume()
    with args.output.open('x') as stream:
        json.dump(value,stream,ensure_ascii=False,indent=2,allow_nan=False);stream.write('\n')
    print(json.dumps(dict(status='OWNER_ASSEMBLY_INPUTS_CONSUMED_NOT_NATIVE_ADMISSION',
        members=value['verified_member_count'],same_initial_binding=INITIAL,dispatch=False)))


if __name__=='__main__':main()
