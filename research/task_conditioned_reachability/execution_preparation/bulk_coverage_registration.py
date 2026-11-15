"""Prospective 24-main lane/width sampling registration, no fit/dispatch code.

An exploratory expansion within the SAME original full4 TRAIN ancestor family.
Not new independent TEST scenes, T-complex A/B, or a change to the frozen fit.
"""
from copy import deepcopy
from .successor_aware_choice import need,digest,pin
from .successor_critic import PURPOSE,timestamp

GROUPS=('bulk-g01','bulk-g02','bulk-g09','bulk-g10')
CANDIDATES=('original','lateral_plus_0p04','lateral_minus_0p04')
PREFIXES=('left','right')


def build_bulk24_registration(matrix, baseline, *, registered_at, source_commit, source_files):
    """Fix a 2x2 geometry factorial BEFORE any new native outcomes exist.

    Full original three-request payloads are retained, with task-goal Y explicitly
    translated with the declared lane. Data independently freezes the original
    source helper output/program/model and compares these exact requested intents.
    """
    need(timestamp(registered_at)>=timestamp(baseline['registered_at']),'New prospective registration time')
    need(matrix['schema']=='AINav-bulk-registered-source-matrix-v1' and
         matrix['baseline_case_id']=='full-4' and matrix['shared_initialization_and_ancestor']is True,
         'Exact source-owned full4 ancestor matrix')
    need(tuple(matrix['prefixes'])==PREFIXES and tuple(matrix['candidates'])==CANDIDATES,
         'Original finite prefixes/candidates, never a new policy domain')
    need(matrix['declared_geometries']==10 and matrix['potential_context_candidate_count']==60,
         'Source matrix is a directory, not an already dispatched cohort')
    need(len(source_commit)==40 and all(c in '0123456789abcdef'for c in source_commit)and
         all(pin(h)for h in source_files.values()),'Exact source-owner commit/file pins')
    ancestor=next(s for s in baseline['scenes']if s['case_id']=='full-4')
    groups={g['group_id']:g for g in matrix['groups']}
    need(len(groups)==10 and set(GROUPS)<=set(groups),'Unique source geometry identities')
    selected=[groups[g]for g in GROUPS]
    need({(g['factor_values']['lane_y_m'],g['factor_values']['step_width_m'])for g in selected}==
         {(-1.75,1.4),(-1.75,1.5),(-2.15,1.4),(-2.15,1.5)},'Pre-outcome extreme-lane x width factorial only')
    scenes=[];conditions=[]
    for group in selected:
        case=group['source_case'];base_case=ancestor['scene_key_canonical_payload']['integrated_case']
        need(set(case)==set(base_case)and {k for k in case if case[k]!=base_case[k]}<=
             {'case_id','lane_y_m','step_width_m'},'Only source-declared geometry changes, not materials/control')
        need(case['case_id']==group['case_id']and case['lane_y_m']==group['factor_values']['lane_y_m']and
             case['step_width_m']==group['factor_values']['step_width_m'],'Actual case agrees with public factor labels')
        payload=deepcopy(ancestor['scene_key_canonical_payload']);payload['integrated_case']=deepcopy(case)
        scene_sha=digest(payload)
        scenes.append(dict(group_id=group['group_id'],case_id=case['case_id'],split='TRAIN',
            source_scene_sha256=scene_sha,scene_key_canonical_payload=payload,
            scene_ancestry_key=ancestor['scene_ancestry_key'],same_existing_TRAIN_ancestor=True,
            original_native_protocol_sha256_canonical=None,canonical_native_protocol_binding_owner='Data new program freeze',
            qualified_dynamic_domain=False))
        for side in PREFIXES:
            old=next(c for c in baseline['conditions']if c['condition_key']=='full-4_'+side)
            requests=deepcopy(old['requested_intents']);lane=case['lane_y_m']
            requests[0]['parameters']['goal_world_y_m']=lane+(.15 if side=='left'else -.15)
            requests[1]['parameters']['goal_world_y_m']=lane
            condition_payload=dict(schema='Reach-fixed-scene-prefix-condition-v1',source_scene_sha256=scene_sha,
                prefix_side=side,requested_intents=requests)
            conditions.append(dict(condition_key=group['group_id']+'_'+side,group_id=group['group_id'],
                prefix_side=side,source_scene_sha256=scene_sha,scene_ancestry_key=ancestor['scene_ancestry_key'],
                split='TRAIN',condition_binding_sha256=digest(condition_payload),
                condition_binding_payload=condition_payload,requested_intents=requests,
                task_goal_Y_changes_with_lane=True,whole_task_goal_unchanged_claim=False))
    schedule=[]
    # Fixed cyclic Latin order: each context receives each arm ONCE. Outcome-
    # independent ordinals are not an instruction to bypass owner qualification.
    for round_index in range(3):
        for ci,condition in enumerate(conditions):
            arm=CANDIDATES[(round_index+ci)%3]
            schedule.append(dict(ordinal=len(schedule)+1,attempt_key='g2-bulk24-v1__'+condition['condition_key']+'__'+arm,
                condition_key=condition['condition_key'],group_id=condition['group_id'],prefix_side=condition['prefix_side'],
                split='TRAIN',source_scene_sha256=condition['source_scene_sha256'],
                scene_ancestry_key=ancestor['scene_ancestry_key'],condition_binding_sha256=condition['condition_binding_sha256'],
                candidate_id=arm,preparation_payload=dict(schema='AINav-finite-CLIMB-preparation-selection-v1',
                    target_ref='cuboid-2:upper-entry',candidate_id=arm),
                own_zero_max=1,main_max=1,scope_id=None,physical_program_sha256=None))
    result=dict(schema='Reach-bulk24-prospective-new-purpose-collection-v1',registered_at=registered_at,
        data_purpose=PURPOSE,registration_state='FROZEN_COLLECTION_SCOPE_NOT_FIT_OR_NATIVE_ADMISSION',
        authorization_sha256=baseline['authorization_sha256'],authorization_path=baseline['authorization_path'],
        source_owner_commit=source_commit,source_owner_files_sha256=deepcopy(source_files),
        source_api=dict(module='bulk_registered_conditions',selection_type='BulkCondition',entrypoint='build_condition',
            exact_selection_fields=['group_id','prefix_side','candidate_id'],enabled_default=False,
            source_delta='Additive plan only in a NEW Data-owned source snapshot; original validator/code not bypassed'),
        hypothesis='Declared lane/width changes may expose useful original first-PREPARE input variation or aliasing of the fixed 48-slot view. Neither changed labels nor learnability are guaranteed.',
        design='Pre-outcome 2 extreme lanes x 2 widths x 2 original ground prefixes x 3 fixed preparation candidates = 24 new mains maximum; no seed/reset replication.',
        task_family=baseline['task_family'],prediction_decision=baseline['prediction_decision'],
        decision_horizon=baseline['decision_horizon'],feature_profile=deepcopy(baseline['feature_profile']),
        feature_profile_sha256=baseline['feature_profile_sha256'],feature_extractor_sha256=baseline['feature_extractor_sha256'],
        feature_policy=deepcopy(baseline['feature_policy']),ordered_candidates=list(CANDIDATES),
        require_source_scene_isolation=True,scene_split_assignments={s['source_scene_sha256']:'TRAIN'for s in scenes},
        scenes=scenes,conditions=conditions,attempt_schedule=schedule,
        ancestry_policy='All variants/prefixes/arms belong to existing full4 TRAIN ancestor. Four new geometric declarations are NOT four independent families or heldout/TEST scenes.',
        sampling=dict(max_new_roots=24,max_main_attempts=24,max_own_zero_attempts=24,per_condition_per_candidate=1,
            reset_or_seed_repetitions=0,selected_group_ids=list(GROUPS),unselected_source_groups_not_automatically_queued=True,
            ordering='round-major cyclic Latin arm order; launch eligible rows in ordinal order subject to Data capacity/lease and T priority; completion order may differ',
            meaningful_groups_verified_before_capture=0,independent_ancestor_families=1,statistical_power_claimed=False,
            resource_reservation_already_allocated=False),
        source_binding=dict(physical_owner='Data',compute='root@180.97.68.228:46308',
            candidate_api_sha256=baseline['source_binding']['candidate_api_sha256'],
            common_stow_v2_for_all_arms=True,original_exact_three_request_consumer=True,
            original_runtime_training_allowed_flag_not_rewritten=True,
            compare_helper_requests_and_payload_to_this_manifest_before_new_program_freeze=True),
        physical_limits=deepcopy(baseline['physical_limits']),
        observation_coverage=dict(causal_clock='FIRST ORIGINAL CLIMB PREPARE, same query/Observation/installed-before-first-command binding',
            exact_proprio_diagnostic='round physical_features[2:47] to 6 decimals; report distinct counts/ranges and duplicates, not a meaningful-state or safety guarantee',
            RGBD_hash_difference_is_not_effective_group_proof=True,geometry_labels_are_not_model_features=True,
            aliased_fixed_inputs_not_hidden_by_new_case_ids=True,no_posthoc_new_features_or_private_pose=True,
            no_claim_of_10_effective_groups_from_10_geometry_labels=True),
        stopping=dict(finite_batch_max_main=24,replacement_attempts=0,automatic_retry=False,
            common_source_identity_safety_or_guard_implementation_fault='STOP_THIS_SOURCE_VERSION; retain every failure/charge; no reissue of closed rows',
            ordinary_individual_native_failure='Keep result and all attempt costs; no chasing success or whole-batch stop solely to hide failures',
            predecision_failure='Keep reached=false/features=None/successor_label=None and all actual costs',
            censored_or_unknown='Separate censoring and UNKNOWN; never fabricate a native negative/success time or drop an attempt',
            capacity_or_unqualified_row='No launch without Data own-zero/freeze/lease; leave explicit NOT_ADMITTED/NOT_STARTED, not a replacement',
            batch_end='Publish complete fixed inventory including not-started/failed/unreached/unknown; no automatic fit or extension to the other 36 matrix combinations'),
        labels=deepcopy(baseline['labels']),qualified_entry_condition_family=False,
        training_activation='Collection only. Does NOT modify/append/refit the frozen TRAIN6 model or its CAL/VAL protocol. A separate prospectively fixed model-training/evaluation manifest and actual full-source/feature/label gate are required before any new model version; do not invoke old train-only on this TRAIN-only family registration.',
        old_TRAIN6_or_CAL_VAL_schedule_modified=False,current_frozen_critic_refit_allowed=False,
        independent_TEST=0,statistical_or_dynamic_qualification=False,
        priority='T-COMPLEX-01 full-program qualification/A-B/live video gets first eligible resources; bulk need not wait for all ten geometry groups, but never displaces T or hot-expands old scopes',
        dispatch=False,physical_admission=False,new_scopes_allocated=0,trained_models=0)
    return result
