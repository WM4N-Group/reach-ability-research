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
            current_frozen_critic_refit_allowed=False, attempt_schedule=[copy.deepcopy(row) for _ in range(24)],
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


if __name__ == '__main__': unittest.main()
