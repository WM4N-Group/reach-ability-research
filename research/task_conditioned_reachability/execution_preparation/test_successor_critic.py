"""Learner/admission math tests on explicit SOFTWARE fixtures, not new samples.
No dataset files, audit labels, actors or research model artifacts are consumed.
"""
from copy import deepcopy
import unittest
from .successor_critic import PURPOSE,validate_dataset,_fit_heads,predict_offline,fit_and_evaluate,_score_diagnostics
from .successor_aware_choice import digest


def fixture():
    auth=dict(user_reply='运行',at='2020-01-01T00:00:00+00:00',permission_for_old_data_relabelling=False,
              approved_scope=['small high-level candidate-conditioned successor success and duration model'])
    protocol=dict(authorization_sha256='a'*64,feature_profile_sha256='b'*64,
        feature_profile={'names':['SOFTWARE_PHYSICAL_SLOT_'+str(i) for i in range(48)]},
        qualified_entry_condition_family=True,minimum_groups={'TRAIN':2,'CALIBRATION':1,'VALIDATION':1},
        physical_limits={'max_sim_s':240.})
    rows=[]
    for group in range(4):
        for action in range(3):
            x=[0.]*48;x[1]=(0.,.04,-.04)[action];x[2]=float(group)/10.;x[47]=0.
            success=not(action==2 and group%2==1)
            rows.append(dict(sample_id=f'SOFTWARE-{group}-{action}',scope_id=f'NEW_SOFTWARE-{group}-{action}',
                data_purpose=PURPOSE,old_audit_ancestor=False,guard_and_stream_integrity_verified=True,
                source_result_sha256='c'*64,source_feature_event_sha256='d'*64,condition_binding_sha256=digest({'SOFTWARE_GROUP':group}),
                captured_at='2020-01-03T00:00:00+00:00',split=('TRAIN','TRAIN','CALIBRATION','VALIDATION')[group],
                physical_features=x,outcome='SUCCESS' if success else 'NATIVE_GUARD_FAILURE',
                current_READY_s=10.+group/10.,full_success_s=20.+group/10. if success else None,
                READY_source_verified=True,successful_task_endpoint_verified=success,native_guard_failure_verified=not success,spent_sim_s=100.+group))
    data=dict(purpose=PURPOSE,origin='FUTURE_NEW_CAPTURE',training_allowed=True,authorization_sha256='a'*64,
              preregistration_sha256=digest(protocol),feature_profile_sha256='b'*64,preregistered_at='2020-01-02T00:00:00+00:00',rows=rows,all_closed_attempts_accounted=True,closed_attempt_count=len(rows))
    return data,auth,protocol


class SuccessorCriticTests(unittest.TestCase):
    def setUp(self):self.data,self.auth,self.protocol=fixture()
    def validate(self):return validate_dataset(self.data,self.auth,self.protocol)

    def test_fixed_cpu_heads_fit_only_train_and_remain_uncalibrated_unknown(self):
        result=fit_and_evaluate(self.data,self.auth,self.protocol)
        self.assertEqual(result['model']['fit_rows'],6);self.assertEqual(result['model']['successful_full_time_fit_rows'],5)
        self.assertEqual(result['model']['current_time_fit_rows'],6)
        p=predict_offline(result['model'],self.data['rows'][0]['physical_features'])
        self.assertEqual(p['complete_successor_feasibility'],'UNKNOWN');self.assertFalse(p['execution_authorized'])
        self.assertFalse(result['model']['deployment_qualified']);self.assertFalse(result['model']['success_score_is_calibrated_probability'])

    def test_guard_failure_not_given_success_time_or_dropped_from_classifier(self):
        result=fit_and_evaluate(self.data,self.auth,self.protocol)
        self.assertEqual(result['model']['success_classifier_fit_rows'],6)
        self.assertEqual(result['heldout_metrics']['VALIDATION']['guard_failures'],1)
        self.data['rows'][5]['full_success_s']=1.
        with self.assertRaisesRegex(ValueError,'NOT successful'):self.validate()

    def test_old_audit_role_and_pregrant_capture_refused_before_fit(self):
        self.data['origin']='HISTORICAL_SEEN_DEV_AUDIT_ONLY'
        with self.assertRaisesRegex(ValueError,'audit data never'):self.validate()
        self.data['origin']='FUTURE_NEW_CAPTURE';self.data['rows'][0]['captured_at']='2019-12-31T00:00:00+00:00'
        with self.assertRaisesRegex(ValueError,'post-preregistration'):self.validate()

    def test_closed_scope_cannot_be_renamed_as_new_training_role(self):
        self.data['rows'][0]['scope_id']='data-climb-prep-stageB-original-20261114-v1'
        with self.assertRaisesRegex(ValueError,'historical scopes'):self.validate()

    def test_same_condition_group_cannot_be_frame_or_arm_split(self):
        self.data['rows'][1]['split']='VALIDATION'
        with self.assertRaisesRegex(ValueError,'cannot cross'):self.validate()

    def test_heldout_features_and_labels_never_change_fitted_parameters(self):
        model=_fit_heads(self.validate());changed=deepcopy(self.data)
        for row in changed['rows']:
            if row['split']=='TRAIN':continue
            row['physical_features'][2]=999.;row['outcome']='SUCCESS';row['full_success_s']=100.;row['successful_task_endpoint_verified']=True
        other=_fit_heads(validate_dataset(changed,self.auth,self.protocol))
        self.assertEqual(model,other)

    def test_censoring_is_not_class_zero_and_spending_retained(self):
        row=self.data['rows'][4];row.update(outcome='CENSORED',full_success_s=None,spent_sim_s=55.)
        result=fit_and_evaluate(self.data,self.auth,self.protocol)
        self.assertEqual(result['model']['success_classifier_fit_rows'],5)
        self.assertEqual(result['censored_rows'],1);self.assertEqual(result['all_rows_and_failures_retained'],12)

    def test_missing_physical_features_never_imputed_or_metadata_injected(self):
        self.data['rows'][0]['physical_features'][2]=None
        with self.assertRaisesRegex(ValueError,'silent missing'):self.validate()
        self.data['rows'][0]['physical_features'][2]='UUID'
        with self.assertRaisesRegex(ValueError,'silent missing'):self.validate()

    def test_current_ready_and_native_failure_need_source_witnesses(self):
        self.data['rows'][0]['READY_source_verified']=False
        with self.assertRaisesRegex(ValueError,'Recorded READY'):self.validate()
        self.data['rows'][0]['READY_source_verified']=True;self.data['rows'][5]['native_guard_failure_verified']=False
        with self.assertRaisesRegex(ValueError,'collector/resource'):self.validate()

    def test_unqualified_or_no_entry_state_variation_cannot_trigger_fit(self):
        self.protocol['qualified_entry_condition_family']=False;self.data['preregistration_sha256']=digest(self.protocol)
        with self.assertRaisesRegex(ValueError,'Qualified legal entry-state'):self.validate()
        self.protocol['qualified_entry_condition_family']=True;self.data['preregistration_sha256']=digest(self.protocol)
        for row in self.data['rows']:row['physical_features'][2]=0.
        with self.assertRaisesRegex(ValueError,'No observed entry-state'):self.validate()

    def test_no_class_variation_is_no_go_not_automatic_failure_mining(self):
        for row in self.data['rows']:
            row.update(outcome='SUCCESS',full_success_s=20.,successful_task_endpoint_verified=True)
        with self.assertRaisesRegex(ValueError,'No observed success/failure'):self.validate()

    def test_predecision_failures_stay_in_attempt_denominator_without_fake_features(self):
        self.data['unreached_decision_attempts']=[dict(scope_id='NEW_SOFTWARE_UNREACHED',data_purpose=PURPOSE,old_audit_ancestor=False,source_result_sha256='e'*64,
            captured_at='2020-01-03T00:00:00+00:00',decision_reached=False,physical_features=None,spent_sim_s=7.)]
        self.data['closed_attempt_count']=13
        result=fit_and_evaluate(self.data,self.auth,self.protocol)
        self.assertEqual(result['total_closed_attempts'],13);self.assertEqual(len(result['unreached_decision_attempts']),1)
        self.assertEqual(result['model']['fit_rows'],6)
        self.assertEqual(result['known_spent_sim_s'],sum(r['spent_sim_s'] for r in self.data['rows'])+7.)
        spend=result['attempt_spending']
        self.assertEqual(spend['unreached_decision']['known_spent_sim_s'],7.)
        self.assertEqual(spend['attempts'],13);self.assertTrue(spend['spend_complete'])
        self.assertFalse(spend['known_spend_is_lower_bound']);self.assertFalse(spend['missing_spend_imputed'])
        self.data['closed_attempt_count']=12
        with self.assertRaisesRegex(ValueError,'attempt denominator'):self.validate()

    def test_missing_prefix_and_reached_spend_are_unknown_not_zero(self):
        self.data['rows'][0]['spent_sim_s']=None
        self.data['unreached_decision_attempts']=[dict(scope_id='NEW_SOFTWARE_MISSING_PREFIX',data_purpose=PURPOSE,
            old_audit_ancestor=False,source_result_sha256='e'*64,captured_at='2020-01-03T00:00:00+00:00',
            decision_reached=False,physical_features=None,spent_sim_s=None)]
        self.data['closed_attempt_count']=13
        result=fit_and_evaluate(self.data,self.auth,self.protocol)
        spend=result['attempt_spending']
        self.assertEqual(result['missing_spend_attempts'],2);self.assertEqual(result['missing_spend_rows'],1)
        self.assertEqual(spend['reached_decision']['missing_spend_attempts'],1)
        self.assertEqual(spend['unreached_decision']['missing_spend_attempts'],1)
        self.assertFalse(spend['spend_complete']);self.assertTrue(spend['known_spend_is_lower_bound'])
        self.assertFalse(spend['missing_spend_imputed'])
        self.assertEqual(result['known_spent_sim_s'],sum(r['spent_sim_s'] for r in self.data['rows'][1:]))
        self.assertIsNone(result['unreached_decision_attempts'][0]['spent_sim_s'])

    def test_scope_aliases_cannot_inflate_attempt_or_training_denominators(self):
        self.data['rows'][1]['scope_id']=self.data['rows'][0]['scope_id']
        with self.assertRaisesRegex(ValueError,'counted once'):self.validate()
        self.data,self.auth,self.protocol=fixture()
        attempt=dict(scope_id=self.data['rows'][0]['scope_id'],data_purpose=PURPOSE,old_audit_ancestor=False,
            source_result_sha256='e'*64,captured_at='2020-01-03T00:00:00+00:00',
            decision_reached=False,physical_features=None,spent_sim_s=7.)
        self.data['unreached_decision_attempts']=[attempt];self.data['closed_attempt_count']=13
        with self.assertRaisesRegex(ValueError,'counted once'):self.validate()
        attempt['scope_id']='NEW_SOFTWARE_PREFIX'
        self.data['unreached_decision_attempts'].append(deepcopy(attempt));self.data['closed_attempt_count']=14
        with self.assertRaisesRegex(ValueError,'counted once'):self.validate()

    def test_blank_prefix_scope_and_nonfinite_charges_are_refused(self):
        attempt=dict(scope_id=' ',data_purpose=PURPOSE,old_audit_ancestor=False,source_result_sha256='e'*64,
            captured_at='2020-01-03T00:00:00+00:00',decision_reached=False,physical_features=None,spent_sim_s=7.)
        self.data['unreached_decision_attempts']=[attempt];self.data['closed_attempt_count']=13
        with self.assertRaisesRegex(ValueError,'New predecision scope'):self.validate()
        attempt['scope_id']='NEW_SOFTWARE_PREFIX'
        for invalid in (float('nan'),float('inf'),-1.,True):
            attempt['spent_sim_s']=invalid
            with self.assertRaisesRegex(ValueError,'prefix costs'):self.validate()
        attempt['spent_sim_s']=7.
        for invalid in (float('nan'),float('inf'),-1.,True):
            self.data['rows'][0]['spent_sim_s']=invalid
            with self.assertRaisesRegex(ValueError,'missing is not zero'):self.validate()

    def test_raw_diagnostic_failure_misses_have_failure_not_attempt_denominator(self):
        pairs=[({'outcome':'SUCCESS'},.5),({'outcome':'NATIVE_GUARD_FAILURE'},.8),
               ({'outcome':'NATIVE_GUARD_FAILURE'},.2),({'outcome':'CENSORED'},.99)]
        d=_score_diagnostics(pairs)
        self.assertEqual(d['known_outcome_rows'],3);self.assertEqual(d['censored_excluded'],1)
        self.assertEqual(d['native_failures'],2);self.assertEqual(d['native_failures_scored_success'],1)
        self.assertEqual(d['native_failure_miss_rate'],.5)
        self.assertEqual(d['failure_fraction_among_scored_success'],.5)
        self.assertEqual(d['success_false_refusal_rate'],0.)
        self.assertFalse(d['threshold_is_deployment_rule'])

    def test_absent_classes_or_no_scored_success_report_undefined_rates_not_zero(self):
        only_success=_score_diagnostics([({'outcome':'SUCCESS'},.2)])
        self.assertIsNone(only_success['native_failure_miss_rate'])
        self.assertIsNone(only_success['failure_fraction_among_scored_success'])
        self.assertEqual(only_success['success_false_refusal_rate'],1.)
        only_failure=_score_diagnostics([({'outcome':'NATIVE_GUARD_FAILURE'},.2)])
        self.assertEqual(only_failure['native_failure_miss_rate'],0.)
        self.assertIsNone(only_failure['success_false_refusal_rate'])
        only_censored=_score_diagnostics([({'outcome':'CENSORED'},.9)])
        self.assertEqual(only_censored['known_outcome_rows'],0)
        self.assertIsNone(only_censored['native_failure_miss_rate'])
        self.assertIsNone(only_censored['success_false_refusal_rate'])

    def test_heldout_raw_score_diagnostics_do_not_promote_unknown_to_native_pass(self):
        result=fit_and_evaluate(self.data,self.auth,self.protocol)
        for metrics in result['heldout_metrics'].values():
            self.assertEqual(metrics['full_successor_feasibility_UNKNOWN_rows'],metrics['rows'])
            self.assertEqual(metrics['full_successor_feasibility_UNKNOWN_fraction'],1.)
            self.assertEqual(metrics['qualified_native_or_execution_PASS_predictions'],0)
            self.assertEqual(metrics['raw_score_diagnostic']['raw_uncalibrated_score_threshold'],.5)
            self.assertEqual(metrics['train_only_constant_score_diagnostic']['raw_uncalibrated_score_threshold'],.5)
            self.assertFalse(metrics['raw_score_diagnostic']['threshold_is_deployment_rule'])
            self.assertIsNotNone(metrics['current_READY_time_MAE_s'])
            self.assertIsNotNone(metrics['train_only_mean_baseline_current_READY_time_MAE_s'])
        self.assertFalse(result['execution_authorized']);self.assertFalse(result['model']['deployment_qualified'])

    def test_censored_heldout_rows_remain_in_unknown_coverage_not_class_diagnostics(self):
        row=self.data['rows'][-1];row.update(outcome='CENSORED',full_success_s=None)
        result=fit_and_evaluate(self.data,self.auth,self.protocol);v=result['heldout_metrics']['VALIDATION']
        self.assertEqual(v['raw_score_diagnostic']['known_outcome_rows'],2)
        self.assertEqual(v['raw_score_diagnostic']['censored_excluded'],1)
        self.assertEqual(v['full_successor_feasibility_prediction_rows'],3)
        self.assertEqual(v['full_successor_feasibility_UNKNOWN_rows'],3)
        self.assertIsNone(v['raw_score_diagnostic']['native_failure_miss_rate'])

    def test_missing_group_or_wrong_protocol_or_future_clock_refused(self):
        self.data['rows']=[r for r in self.data['rows'] if r['split']!='CALIBRATION'];self.data['closed_attempt_count']=len(self.data['rows'])
        with self.assertRaisesRegex(ValueError,'Insufficient'):self.validate()
        self.data,self.auth,self.protocol=fixture();self.data['preregistration_sha256']='e'*64
        with self.assertRaisesRegex(ValueError,'frozen collection'):self.validate()
        self.data['preregistration_sha256']=digest(self.protocol);self.data['rows'][0]['captured_at']='2099-01-01T00:00:00+00:00'
        with self.assertRaisesRegex(ValueError,'future timestamps'):self.validate()


if __name__=='__main__':unittest.main()
