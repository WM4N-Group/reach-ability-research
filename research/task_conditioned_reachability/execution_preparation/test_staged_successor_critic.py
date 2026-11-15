"""Regression for the REAL six-TRAIN-before-heldout sequencing deadlock.

Abstract software fixtures ONLY, no captured dataset/model artifact exported.
"""
from copy import deepcopy
import unittest
from unittest.mock import patch
from . import successor_critic as critic
from .test_successor_critic import fixture
from .successor_aware_choice import digest


def staged_fixture():
    data,auth,protocol=fixture()
    protocol['collection_protocol_file_sha256']='f'*64
    protocol['require_source_scene_isolation']=True
    protocol['scene_split_assignments']={digest({'SOFTWARE_SCENE':s}):s for s in critic.SPLITS}
    protocol['stopping']={'TRAIN_gate':dict(minimum_reached_prefix_groups=2,
        minimum_success_rows=3,minimum_verified_postdecision_native_failures=1,
        minimum_distinct_public_proprio_states=2)}
    schedule=[]
    for i,row in enumerate(data['rows']):
        row.update(attempt_key=row['sample_id'],candidate_id=('original','plus','minus')[i%3],
            source_scene_sha256=digest({'SOFTWARE_SCENE':row['split']}),
            new_use_protocol_file_sha256='f'*64)
        schedule.append({k:row[k] for k in ('attempt_key','candidate_id','source_scene_sha256',
                                          'condition_binding_sha256','split')})
    protocol['attempt_schedule']=schedule
    data['collection_protocol_file_sha256']='f'*64
    data['preregistration_sha256']=digest(protocol)
    return data,auth,protocol


def stage(data,phase):
    out=deepcopy(data)
    out['rows']=[r for r in out['rows'] if r['split'] in critic.PHASE_SPLITS[phase]]
    out['closed_attempt_count']=len(out['rows'])
    return out


class StagedSuccessorCriticTests(unittest.TestCase):
    def setUp(self):
        self.data,self.auth,self.protocol=staged_fixture()
        self.train=stage(self.data,'TRAIN_ONLY')

    def test_train_fit_needs_no_heldout_rows_but_keeps_whole_scene_split_map(self):
        result=critic.fit_train_only(self.train,self.auth,self.protocol)
        self.assertEqual(result['training_rows'],6)
        self.assertFalse(result['heldout_used_for_fit'])
        self.assertFalse(result['execution_authorized'])
        with self.assertRaisesRegex(ValueError,'Insufficient'):
            critic.validate_dataset(self.train,self.auth,self.protocol)

    def test_early_fit_refuses_later_heldout_and_incomplete_scheduled_TRAIN(self):
        with self.assertRaisesRegex(ValueError,'later heldout'):
            critic.fit_train_only(self.data,self.auth,self.protocol)
        self.train['rows'].pop(0);self.train['closed_attempt_count']-=1
        with self.assertRaisesRegex(ValueError,'Complete closed scheduled'):
            critic.fit_train_only(self.train,self.auth,self.protocol)

    def test_original_collection_pin_and_assigned_candidate_cannot_be_relabelled(self):
        self.train['rows'][0]['new_use_protocol_file_sha256']='e'*64
        with self.assertRaisesRegex(ValueError,'registered collection purpose'):
            critic.fit_train_only(self.train,self.auth,self.protocol)
        self.train['rows'][0]['new_use_protocol_file_sha256']='f'*64
        self.train['rows'][0]['candidate_id']='minus'
        with self.assertRaisesRegex(ValueError,'assigned arm'):
            critic.fit_train_only(self.train,self.auth,self.protocol)

    def test_fixed_success_floor_and_failure_class_NoGo_not_silent_single_class_fit(self):
        self.protocol['stopping']['TRAIN_gate']['minimum_success_rows']=6
        self.train['preregistration_sha256']=digest(self.protocol)
        with self.assertRaisesRegex(ValueError,'success count gate'):
            critic.fit_train_only(self.train,self.auth,self.protocol)
        self.protocol['stopping']['TRAIN_gate']['minimum_success_rows']=3
        self.train['preregistration_sha256']=digest(self.protocol)
        for row in self.train['rows']:
            row.update(outcome='SUCCESS',full_success_s=20.,successful_task_endpoint_verified=True)
        with self.assertRaisesRegex(ValueError,'No observed success/failure class'):
            critic.fit_train_only(self.train,self.auth,self.protocol)

    def test_calibration_can_score_frozen_model_before_validation_without_refit(self):
        artifact=critic.fit_train_only(self.train,self.auth,self.protocol)
        before=deepcopy(artifact)
        with patch.object(critic,'_fit_heads',side_effect=AssertionError('NO SECOND FIT')):
            out=critic.evaluate_frozen(stage(self.data,'CALIBRATION'),self.auth,self.protocol,artifact,phase='CALIBRATION')
        self.assertEqual(out['heldout_metrics']['CALIBRATION']['rows'],3)
        self.assertEqual(out['heldout_metrics']['VALIDATION']['rows'],0)
        self.assertTrue(out['later_validation_not_collected'])
        self.assertIsNone(out['heldout_metrics']['VALIDATION']['uncalibrated_log_loss'])
        self.assertNotIn('model',out);self.assertEqual(artifact,before)

    def test_full_evaluation_never_refits_even_when_heldout_outcomes_change(self):
        artifact=critic.fit_train_only(self.train,self.auth,self.protocol)
        for row in self.data['rows']:
            if row['split']=='TRAIN':continue
            row.update(outcome='SUCCESS',full_success_s=99.,successful_task_endpoint_verified=True)
        with patch.object(critic,'_fit_heads',side_effect=AssertionError('NO SECOND FIT')):
            out=critic.evaluate_frozen(self.data,self.auth,self.protocol,artifact)
        self.assertFalse(out['model_refitted'])
        self.assertEqual(out['frozen_model_sha256'],artifact['model_sha256'])
        self.assertFalse(out['execution_authorized'])

    def test_changed_TRAIN_snapshot_or_frozen_model_refused(self):
        artifact=critic.fit_train_only(self.train,self.auth,self.protocol)
        self.data['rows'][0]['spent_sim_s']+=1.
        with self.assertRaisesRegex(ValueError,'TRAIN snapshot changed'):
            critic.evaluate_frozen(self.data,self.auth,self.protocol,artifact)
        self.data['rows'][0]['spent_sim_s']-=1.
        artifact['model']['success_weights'][0]+=1.
        with self.assertRaisesRegex(ValueError,'model contents changed'):
            critic.evaluate_frozen(self.data,self.auth,self.protocol,artifact)

    def test_staged_protocol_cannot_use_legacy_full_cohort_refit_entry(self):
        with self.assertRaisesRegex(ValueError,'never a refit after heldout'):
            critic.fit_and_evaluate(self.data,self.auth,self.protocol)


if __name__=='__main__':unittest.main()
