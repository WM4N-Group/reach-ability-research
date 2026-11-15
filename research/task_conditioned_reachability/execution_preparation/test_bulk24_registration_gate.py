"""Software-only schedule/purpose refusal checks, not physical trials or rows."""
import copy
import unittest
from operations.measure_bulk24_public_boundary import registration_gate, semantic_success_gate, correlate_semantic_successes, PROTOCOL_SHA, PURPOSE


class BulkRegistrationGateTests(unittest.TestCase):
    def setUp(self):
        row = dict(ordinal=1, attempt_key='SOFTWARE_ONLY', split='TRAIN', source_scene_sha256='a'*64,
                   condition_binding_sha256='b'*64,
                   scene_ancestry_key='1245cf2a2c5ffa02a1cc7ae4de61fdd28f70df6eec5f0de5eb3a90a7f7f7d1a8',
                   preparation_payload=dict(candidate_id='original'))
        self.protocol = dict(schema='Reach-bulk24-prospective-new-purpose-collection-v1', data_purpose=PURPOSE,
            current_frozen_critic_refit_allowed=False, attempt_schedule=[dict(copy.deepcopy(row), ordinal=i+1) for i in range(24)],
            scene_split_assignments={'a'*64:'TRAIN'})
        self.acquisition = dict(row, data_purpose=PURPOSE, new_use_protocol_file_sha256=PROTOCOL_SHA)
        self.release = dict(schema='Data-bulk24-first-new-geometry-original-delivery-v1', protocol_sha256=PROTOCOL_SHA,
            ordinal=1, attempt_key='SOFTWARE_ONLY', split='TRAIN', fit_allowed=False,
            current_model_refit_allowed=False, whole_package_model_input_allowed=False)
    def gate(self):
        return registration_gate(self.release, self.protocol, self.acquisition)
    def test_exact_registration_only_not_fit(self):
        self.assertEqual(self.gate()['preparation_payload']['candidate_id'], 'original')
        self.assertFalse(self.release['fit_allowed'])
    def fixed_closed_fixture(self):
        self.release.update(schema='Data-bulk24-fixed-closed-original-delivery-v2', ordinal=2)
        self.acquisition['ordinal'] = 2
    def test_exact_fixed_closed_format_for_new_original_release(self):
        self.fixed_closed_fixture()
        self.assertEqual(self.gate()['ordinal'], 2)
    def test_original_first_format_cannot_be_reused_for_later_ordinals(self):
        self.release['ordinal'] = self.acquisition['ordinal'] = 2
        with self.assertRaises(ValueError): self.gate()
        self.release['schema'] = 'Data-bulk24-fixed-closed-original-delivery-v2'
        self.assertEqual(self.gate()['ordinal'], 2)
        self.release['ordinal'] = self.acquisition['ordinal'] = 1
        with self.assertRaises(ValueError): self.gate()
    def test_fixed_closed_does_not_waive_purpose_and_future_format_rejected(self):
        self.fixed_closed_fixture()
        self.release['whole_package_model_input_allowed'] = True
        with self.assertRaises(ValueError): self.gate()
        self.release['whole_package_model_input_allowed'] = False
        self.release['schema'] = 'Data-bulk24-fixed-closed-original-delivery-v3'
        with self.assertRaises(ValueError): self.gate()
    def test_old_DEV_schema_is_not_relabelled(self):
        self.release['schema'] = 'OLD_DEV'
        with self.assertRaises(ValueError): self.gate()
    def test_role_and_whole_scene_split_cannot_be_promoted(self):
        for field in ('release', 'acquisition'):
            obj = getattr(self, field); before = obj['split']; obj['split'] = 'CALIBRATION'
            with self.assertRaises(ValueError): self.gate()
            obj['split'] = before
        self.protocol['scene_split_assignments']['a'*64] = 'VALIDATION'
        with self.assertRaises(ValueError): self.gate()
    def test_native_worker_training_false_is_not_the_only_purpose_gate(self):
        self.acquisition['data_purpose'] = 'DEV_AUDIT_ONLY'
        with self.assertRaises(ValueError): self.gate()
    def test_no_fit_or_refit_from_collection(self):
        for field in ('fit_allowed','current_model_refit_allowed','whole_package_model_input_allowed'):
            self.release[field] = True
            with self.assertRaises(ValueError): self.gate()
            self.release[field] = False
        self.protocol['current_frozen_critic_refit_allowed'] = True
        with self.assertRaises(ValueError): self.gate()
    def test_scene_candidate_and_binding_cannot_drift(self):
        for field in ('source_scene_sha256','condition_binding_sha256','scene_ancestry_key','preparation_payload'):
            before = self.acquisition[field]; self.acquisition[field] = 'OTHER'
            with self.assertRaises(ValueError): self.gate()
            self.acquisition[field] = before
    def test_no_ordinal_growth_or_boolean_ordinal(self):
        for ordinal in (0,25,True):
            self.release['ordinal'] = ordinal
            with self.assertRaises(ValueError): self.gate()
    def success_fixture(self):
        return dict(passed=True, whole_task_success_claimed=False,
            exact_three_semantic_native_successes=dict(exact_requested_semantic_success_count=3,
                preparation_receipts_not_counted=True, requests=[dict(request=dict(skill=s),status='succeeded')
                    for s in ('NAV','PUSH','CLIMB')]))
    def test_structured_success_is_not_a_boolean(self):
        r=self.success_fixture();self.assertEqual(len(semantic_success_gate(r)),3)
        r['exact_three_semantic_native_successes']=True
        with self.assertRaises(ValueError): semantic_success_gate(r)
    def test_preparation_receipts_cannot_replace_three_requested_skills(self):
        r=self.success_fixture();r['exact_three_semantic_native_successes']['requests'][1]['request']['skill']='NAV'
        with self.assertRaises(ValueError): semantic_success_gate(r)
    def test_missing_terminal_and_whole_mission_are_not_success(self):
        r=self.success_fixture();r['exact_three_semantic_native_successes']['requests'][2]['status']='started'
        with self.assertRaises(ValueError): semantic_success_gate(r)
        r=self.success_fixture();r['whole_task_success_claimed']=True
        with self.assertRaises(ValueError): semantic_success_gate(r)
    def semantic_records(self):
        requests=[];records=[]
        for i,skill in enumerate(('NAV','PUSH','CLIMB')):
            intent='intent'+str(i);native='native'+str(i);ref='/SOFTWARE_ONLY/events.jsonl#'+str(len(records)+1)
            records.append(dict(payload=dict(event='skill_execution_judge_ready',intent_sha256=intent)))
            records.append(dict(payload=dict(event='intent_native_execution_bound',execution_role='interaction',
                intent_sha256=intent,native_option_sha256=native,judgment_ref=ref,native_option=dict(skill=skill))))
            records.append(dict(payload=dict(event='intent_actual_native_outcome',execution_role='interaction',
                intent_sha256=intent,native_option_sha256=native,intent_succeeded=True,
                receipt=dict(status='succeeded',option_sha256=native))))
            requests.append(dict(binding_ref=ref,intent_sha256=intent,native_option_sha256=native,request=dict(skill=skill)))
        return records,requests
    def test_helper_binding_ref_points_to_judge_not_native_binding(self):
        records,requests=self.semantic_records()
        correlate_semantic_successes(records,requests,'/SOFTWARE_ONLY/events.jsonl')
        self.assertEqual(records[0]['payload']['event'],'skill_execution_judge_ready')
    def test_ready_without_exact_native_child_terminal_is_rejected(self):
        records,requests=self.semantic_records();records[-1]['payload']['receipt']['status']='started'
        with self.assertRaises(ValueError): correlate_semantic_successes(records,requests,'/SOFTWARE_ONLY/events.jsonl')
    def test_wrong_judgment_reference_never_matched_by_nearest(self):
        records,requests=self.semantic_records();requests[0]['binding_ref']='/SOFTWARE_ONLY/events.jsonl#2'
        with self.assertRaises(ValueError): correlate_semantic_successes(records,requests,'/SOFTWARE_ONLY/events.jsonl')
    def test_exact_prior_protocol_file(self):
        self.acquisition['new_use_protocol_file_sha256'] = 'c'*64
        with self.assertRaises(ValueError): self.gate()


class BulkRequestedEndpointTests(unittest.TestCase):
    def setUp(self):
        from operations.measure_bulk24_public_boundary import requested_climb_endpoint
        self.read = requested_climb_endpoint
        self.result = dict(passed=False, whole_task_success_claimed=False,
            error_class='RuntimeError', error='base_collision', actual_main_world_sim_s=20.)
        def row(**payload): return dict(payload=payload, sha256='SOFTWARE_ONLY')
        self.rows = {
            1: row(event='skill_execution_judgment', intent_sha256='intent', status='READY',
                spec=dict(skill='CLIMB',target_ref='cuboid-2:upper-entry'),state=dict(time_s=10.)),
            2: row(event='intent_native_execution_bound',intent_sha256='intent',execution_role='interaction',
                judgment_ref='/FIXTURE#1',native_option_sha256='native',
                native_option=dict(skill='CLIMB',target_ref='cuboid-2:upper-entry')),
            3: row(event='ainav_native_receipt',receipt=dict(option_sha256='native',status='started',time_s=10.005)),
            4: row(event='ainav_chain_hard_stop',error='base_collision',native_safety_handling_required=True,automatic_retry=False),
            5: row(event='private_terminal_controller_failure',error='base_collision',model_input=False,
                live_state_written=False,time_s=20.),
        }
    def read_failure(self):
        return self.read(self.rows,'intent','/FIXTURE',self.result,allow_native_hard_stop=True)
    def test_explicit_native_hard_stop_does_not_create_a_failed_receipt(self):
        out = self.read_failure()
        self.assertIsNone(out['native_receipt_status']); self.assertIsNone(out['outcome_sha256'])
        self.assertEqual(out['ready_time_s'],10.);self.assertEqual(out['end_time_s'],20.)
        self.assertEqual(out['source_error'],'base_collision')
    def test_default_success_reader_still_refuses_native_failure(self):
        with self.assertRaises(ValueError): self.read(self.rows,'intent','/FIXTURE',self.result)
    def test_ready_bound_to_other_target_or_judgment_cannot_supply_endpoint(self):
        for field,value in [('judgment_ref','/FIXTURE#99'),('native_option',dict(skill='CLIMB',target_ref='another'))]:
            before=self.rows[2]['payload'][field];self.rows[2]['payload'][field]=value
            with self.assertRaises(ValueError): self.read_failure()
            self.rows[2]['payload'][field]=before
    def test_missing_started_is_not_executed_CLIMB(self):
        self.rows[3]['payload']['receipt']['status']='admitted'
        with self.assertRaises(ValueError): self.read_failure()
    def test_original_result_failure_clock_must_match_not_use_spent_success_time(self):
        self.result['actual_main_world_sim_s']=25.
        with self.assertRaises(ValueError): self.read_failure()
    def test_intervening_native_owner_cannot_be_assigned_to_CLIMB(self):
        self.rows[3.5]=dict(payload=dict(event='native_option_installed'),sha256='SOFTWARE_ONLY')
        with self.assertRaises(ValueError): self.read_failure()
    def test_missing_or_other_error_is_not_original_native_failure(self):
        self.rows[4]['payload']['error']='watchdog'
        with self.assertRaises(ValueError): self.read_failure()
    def test_success_requires_literal_matching_native_terminal(self):
        self.result.update(passed=True)
        self.rows={k:v for k,v in self.rows.items()if k<4}
        self.rows[4]=dict(sha256='SOFTWARE_SUCCESS',payload=dict(event='intent_actual_native_outcome',
            intent_sha256='intent',execution_role='interaction',native_option_sha256='native',intent_succeeded=True,
            receipt=dict(status='succeeded',option_sha256='native',time_s=20.)))
        out=self.read(self.rows,'intent','/FIXTURE',self.result)
        self.assertEqual(out['native_receipt_status'],'succeeded');self.assertEqual(out['outcome_sha256'],'SOFTWARE_SUCCESS')
        self.rows[4]['payload']['receipt']['option_sha256']='OTHER'
        with self.assertRaises(ValueError): self.read(self.rows,'intent','/FIXTURE',self.result)


if __name__ == '__main__': unittest.main()
