"""Narrow negative/attribution checks for incoming control results, not research cases."""
from copy import deepcopy
import unittest
from .stow_path_choice import optimize
from .stow_choice_effects import (audit_choice, audit_effect, compare_effects, compare_with_bound_prefix, REVIEWED_PROGRAM_PAIR)


def q(x):return [x,0.,0.,0.,0.,0.]


def decision(blocked=False):
    return optimize(q(0.),q(0.),[q(.3),q(.1)],guard_segment=lambda a,b:'blocked' if blocked else '')


def run(*, enabled=False, capture=3.,compact=6.,terminal=10.,climb=20.,passed=True,scope='baseline'):
    """Explicit SOFTWARE fixture, no claimed native geometry or execution."""
    times=[(capture,'actual_unloaded_supported_retreat_and_full_path_checked'),
           (compact,'actual_arm_compact_safe_pose_reached'),
           (terminal,'failed_PUSH_stow_1s_plus3s_verified_NO_NAV')]
    times.extend([(compact,f'actual_safe_arm_waypoint_{i}') for i in range(1 if enabled else 2)])
    events=[dict(time=t,event=n) for t,n in times]
    stow=dict(events=events,stow_verified=passed,native_PUSH_attempt_failed=True)
    raw=dict(scope_id=scope,passed=passed,episode_closure=dict(storage_complete=True),close_errors=[],selected_requests=[dict(skill='PUSH'),dict(skill='CLIMB')],
             actual_native_results=[dict(skill='push',finish=dict(protected_stow=stow))])
    records=[dict(sequence=1,payload=dict(event='placement_original_native_clock_confirmed',time_s=1.))]
    if enabled:records.append(dict(sequence=2,payload=dict(event='reach_selected_ground_confirmed_stow_path_choice',**decision())))
    records.extend([dict(sequence=3,payload=dict(event='intent_native_execution_bound',native_option=dict(skill='CLIMB'),native_option_sha256='climb')),
                    dict(sequence=4,payload=dict(event='ainav_native_receipt',receipt=dict(option_sha256='climb',status='started',time_s=terminal+1.))),
                    dict(sequence=5,payload=dict(event='ainav_native_receipt',receipt=dict(option_sha256='climb',status='succeeded',time_s=climb)))])
    return raw,records


class StowChoiceEffectsTests(unittest.TestCase):
    def test_two_waypoints_are_only_original_and_direct(self):
        r=audit_choice(decision())
        self.assertEqual(r['ordered_subsequence_count'],2)
        self.assertEqual(r['classification'],'DIRECT_BASELINE_EQUIVALENT')
        self.assertFalse(r['domain_contains_any_strategy_beyond_original_and_direct'])
        self.assertFalse(r['novel_solver'])

    def test_blocked_graph_does_not_cut_task(self):
        r=audit_choice(decision(True));self.assertFalse(r['changed'])
        self.assertIsNone(r['schedule_reduction_s'])

    def test_unknown_guard_not_a_successful_choice(self):
        r=audit_choice(dict(status='GUARD_UNKNOWN_ORIGINAL_FOR_NATIVE_RECHECK',changed=False))
        self.assertIsNone(r['expected_completed_waypoints'])
        with self.assertRaises(ValueError):audit_choice(dict(status='GUARD_UNKNOWN_ORIGINAL_FOR_NATIVE_RECHECK',changed=True))

    def test_tampered_graph_and_schedule_refused(self):
        for corruption in ('optimality','duplicate','guard','endpoint','duration','verify'):
            with self.subTest(corruption=corruption):
                d=decision()
                if corruption=='optimality':d['chosen_reference_duration_interval_s']['upper_s']+=1.
                elif corruption=='duplicate':d['edge_witnesses'].append(deepcopy(d['edge_witnesses'][0]))
                elif corruption=='guard':d['edge_witnesses'][0]['guard_pass']=None
                elif corruption=='endpoint':d['chosen_waypoints'][-1]=q(.2)
                elif corruption=='duration':d['edge_witnesses'][0]['timing']['actual_completion_time_upper_s']=5.
                else:d['unchanged_original_final_verify_min_s']=0.
                with self.assertRaises(ValueError):audit_choice(d)

    def test_original_baseline_is_not_reach_intervention(self):
        e=audit_effect(*run())
        self.assertEqual(e['intervention_status'],'NO_REACH_DECISION_OBSERVED')
        self.assertEqual(e['completed_original_waypoint_count'],2)
        self.assertIsNone(e['selected_count_matches_terminal_events'])
        self.assertTrue(e['original_stow_verified_literal'])
        # The original misleading failed_PUSH event name is NOT a failed task.
        self.assertTrue(e['owner_literal_task_passed'])

    def test_actual_v1_failure_is_not_mislabeled_as_an_unchanged_success(self):
        raw=dict(scope_id='failed-v1',passed=False,status='FAILED_NO_RETRY',error_class='RuntimeError',
                 error='Selected ground placement owner/runtime identity mismatch',stow_choice_records=[],
                 actual_selection_recorded=False,actual_choice_changed=False)
        e=audit_effect(raw,[])
        self.assertEqual(e['intervention_status'],'BINDING_IDENTITY_REFUSED_BEFORE_SELECTION')
        self.assertFalse(e['owner_literal_task_passed']);self.assertEqual(e['owner_literal_status'],'FAILED_NO_RETRY')
        self.assertTrue(all(x is None for x in e['actual_costs_s'].values()))

    def test_selected_path_consumption_checked_against_original_events(self):
        raw,records=run(enabled=True);e=audit_effect(raw,records)
        self.assertTrue(e['selected_count_matches_terminal_events'])
        self.assertIsNone(e['explicit_selector_time_s'])
        self.assertTrue(e['selector_same_update_boundary_inferred_from_pinned_call_order'])
        raw['actual_native_results'][0]['finish']['protected_stow']['events'].append(dict(time=5.,event='actual_safe_arm_waypoint_1'))
        with self.assertRaisesRegex(ValueError,'consumption'):audit_effect(raw,records)

    def test_actual_result_and_journal_selector_records_must_match(self):
        raw,records=run(enabled=True)
        raw.update(stow_choice_records=[deepcopy(records[1]['payload'])],actual_selection_recorded=True,actual_choice_changed=True)
        self.assertTrue(audit_effect(raw,records)['selected_count_matches_terminal_events'])
        raw['stow_choice_records'][0]['changed']=False
        with self.assertRaisesRegex(ValueError,'selector records disagree'):audit_effect(raw,records)

    def test_missing_optional_events_preserve_literal_result(self):
        raw,records=run(enabled=True)
        raw['actual_native_results'][0]['finish']['protected_stow']['events']=[]
        e=audit_effect(raw,records);self.assertTrue(e['owner_literal_task_passed'])
        self.assertIsNone(e['actual_costs_s']['capture_to_compact'])
        self.assertIsNone(e['selected_count_matches_terminal_events'])

    def test_shortened_four_second_verification_refused(self):
        with self.assertRaisesRegex(ValueError,'4s'):audit_effect(*run(compact=7.,terminal=10.))

    def test_no_silent_duplicate_or_preNN_selector(self):
        raw,records=run(enabled=True)
        d=deepcopy(records[1]);records.append(d)
        with self.assertRaisesRegex(ValueError,'multiple'):audit_effect(raw,records)
        records.pop();records[1]['sequence']=0
        with self.assertRaisesRegex(ValueError,'NN confirmation'):audit_effect(raw,records)

    def test_explicit_timestamp_must_match_native_call_boundary(self):
        raw,records=run(enabled=True);records[1]['payload']['time_s']=2.
        with self.assertRaisesRegex(ValueError,'capture clock'):audit_effect(raw,records)

    def test_pair_without_prefix_and_source_is_not_causal(self):
        a=audit_effect(*run());b=audit_effect(*run(enabled=True,scope='candidate',compact=5.,terminal=9.,climb=18.))
        r=compare_effects(a,b)
        self.assertEqual(r['observed_candidate_minus_baseline_s']['capture_to_CLIMB_success'],-2.)
        self.assertFalse(r['single_development_pair_attribution_eligible'])
        self.assertIsNone(r['successful_capture_to_CLIMB_reduction_s'])

    def test_coupled_successor_penalty_can_erase_local_gain(self):
        a=audit_effect(*run());b=audit_effect(*run(enabled=True,scope='candidate',compact=5.,terminal=9.,climb=21.))
        r=compare_effects(a,b,prefix_match=True,source_delta_verified=True)
        self.assertTrue(r['single_development_pair_attribution_eligible'])
        self.assertEqual(r['attributed_local_capture_to_stow_reduction_s'],1.)
        self.assertEqual(r['attributed_successor_penalty_s'],2.)
        self.assertEqual(r['successful_capture_to_CLIMB_reduction_s'],-1.)
        self.assertTrue(r['local_gain_erased_by_successor'])
        self.assertTrue(r['direct_baseline_equivalence']);self.assertFalse(r['novel_algorithm_proven'])

    def test_missing_consumption_or_storage_is_not_attribution(self):
        a=audit_effect(*run());b=audit_effect(*run(enabled=True,scope='candidate'))
        for field in ('selected_count_matches_terminal_events','owner_result_storage_closed'):
            c=deepcopy(b);c[field]=None
            r=compare_effects(a,c,prefix_match=True,source_delta_verified=True)
            self.assertFalse(r['single_development_pair_attribution_eligible'])
            self.assertIsNone(r['successful_capture_to_CLIMB_reduction_s'])

    def test_failed_shorter_run_cannot_be_claimed_as_gain(self):
        a=audit_effect(*run());b=audit_effect(*run(enabled=True,scope='candidate',passed=False,compact=5.,terminal=9.,climb=18.))
        r=compare_effects(a,b,prefix_match=True,source_delta_verified=True)
        self.assertFalse(r['both_literal_success']);self.assertIsNone(r['successful_capture_to_CLIMB_reduction_s'])

    def test_prefix_receipt_must_bind_this_result_pair_and_reviewed_programs(self):
        a=audit_effect(*run());b=audit_effect(*run(enabled=True,scope='candidate'))
        a.update(input_result_sha256='a'*64,program_sha256=REVIEWED_PROGRAM_PAIR[0])
        b.update(input_result_sha256='b'*64,program_sha256=REVIEWED_PROGRAM_PAIR[1])
        fields=('issued','delayed','q_before','dq_before','raw_torque','torque')
        receipt=dict(schema='reach-owner-closed-stow-intervention-prefix-v1',baseline_result_sha256='a'*64,
            candidate_result_sha256='b'*64,prefix_match=True,capture_boundary_physics_tick=600,
            compared_common_physics_steps=700,original_capture_times_s=[3.,3.],same_requests=True,same_numeric_model=True,
            bitwise_equal_through_capture_by_field={k:True for k in fields},
            first_bitwise_difference_tick={k:601 for k in fields},different_motor_commands_observed=True)
        r=compare_with_bound_prefix(a,b,receipt)
        self.assertTrue(r['single_development_pair_attribution_eligible']);self.assertFalse(r['novel_algorithm_proven'])
        b['program_sha256']='unreviewed'
        self.assertFalse(compare_with_bound_prefix(a,b,receipt)['single_development_pair_attribution_eligible'])
        receipt['candidate_result_sha256']='old-P1-P2-proof'
        with self.assertRaisesRegex(ValueError,'different result pair'):compare_with_bound_prefix(a,b,receipt)

    def test_new_program_needs_explicit_pair_bound_source_evidence(self):
        a=audit_effect(*run());b=audit_effect(*run(enabled=True,scope='candidate'))
        a.update(input_result_sha256='a'*64,program_sha256=REVIEWED_PROGRAM_PAIR[0])
        b.update(input_result_sha256='b'*64,program_sha256='new-program-not-legacy-whitelist')
        fields=('issued','delayed','q_before','dq_before','raw_torque','torque')
        prefix=dict(schema='reach-owner-closed-stow-intervention-prefix-v1',baseline_result_sha256='a'*64,
            candidate_result_sha256='b'*64,prefix_match=True,capture_boundary_physics_tick=600,
            compared_common_physics_steps=700,original_capture_times_s=[3.,3.],same_requests=True,same_numeric_model=True,
            bitwise_equal_through_capture_by_field={k:True for k in fields},
            first_bitwise_difference_tick={k:601 for k in fields})
        self.assertFalse(compare_with_bound_prefix(a,b,prefix)['single_development_pair_attribution_eligible'])
        evidence=dict(schema='reach-exact-v2-declared-source-pair-qualification-v1',source_pair_verified=True,
            baseline_result_sha256=a['input_result_sha256'],candidate_result_sha256=b['input_result_sha256'],
            baseline_program_sha256=a['program_sha256'],candidate_program_sha256=b['program_sha256'])
        r=compare_with_bound_prefix(a,b,prefix,source_pair_evidence=evidence)
        self.assertTrue(r['single_development_pair_attribution_eligible']);self.assertFalse(r['novel_algorithm_proven'])
        evidence['candidate_program_sha256']='other-program'
        with self.assertRaisesRegex(ValueError,'different result/program pair'):
            compare_with_bound_prefix(a,b,prefix,source_pair_evidence=evidence)

    def test_explicit_rejected_source_does_not_fall_back_to_legacy_pair(self):
        a=audit_effect(*run());b=audit_effect(*run(enabled=True,scope='candidate'))
        a.update(input_result_sha256='a',program_sha256=REVIEWED_PROGRAM_PAIR[0])
        b.update(input_result_sha256='b',program_sha256=REVIEWED_PROGRAM_PAIR[1])
        prefix=dict(schema='reach-owner-closed-stow-intervention-prefix-v1',baseline_result_sha256='a',
                    candidate_result_sha256='b',prefix_match=None)
        r=compare_with_bound_prefix(a,b,prefix,source_pair_evidence=dict(source_pair_verified=False))
        self.assertIsNone(r['source_delta_verified']);self.assertFalse(r['single_development_pair_attribution_eligible'])

    def test_prefix_receipt_cannot_move_the_intervention_boundary(self):
        a=audit_effect(*run());b=audit_effect(*run(enabled=True,scope='candidate'))
        a['input_result_sha256']='a';b['input_result_sha256']='b'
        receipt=dict(schema='reach-owner-closed-stow-intervention-prefix-v1',baseline_result_sha256='a',candidate_result_sha256='b',
                     prefix_match=True,capture_boundary_physics_tick=601,compared_common_physics_steps=700,original_capture_times_s=[3.,3.])
        with self.assertRaisesRegex(ValueError,'intervention boundary'):compare_with_bound_prefix(a,b,receipt)

    def test_same_scope_or_changed_requests_or_bad_prefix_not_a_controlled_pair(self):
        a=audit_effect(*run());b=audit_effect(*run(enabled=True,scope='candidate'))
        for field in ('scope_id','selected_requests','prefix'):
            c=deepcopy(b)
            if field=='scope_id':c[field]=a[field]
            elif field=='selected_requests':c[field]=[dict(skill='different')]
            r=compare_effects(a,c,prefix_match=field!='prefix',source_delta_verified=True)
            self.assertFalse(r['single_development_pair_attribution_eligible'])
        with self.assertRaises(ValueError):compare_effects(a,b,prefix_match=1)


if __name__=='__main__':unittest.main()
