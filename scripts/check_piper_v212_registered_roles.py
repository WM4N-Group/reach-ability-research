"""Checks for training/development separation in export and consumer release."""
from copy import deepcopy
import unittest

from export_piper_v212_registered_roles import select_closed_role
from release_piper_v212_increment import permissions


class RegisteredRoleChecks(unittest.TestCase):
    def setUp(self):
        self.manifest=dict(physical_episodes=[dict(episode_id='ep',group_id='g',role='development_calibration',
             status='closed',recorded=True,skill_version='push-direct-approach-v212',task_scope='original_reset_independent_push')])
        self.split=dict(measured_groups={'g':dict(role='development_calibration',episodes=['ep'])})
        self.labels=dict(contract_sha256='contract',group_split_version='s1',episodes=[dict(episode_id='ep',group_id='g',
             owner_recorded_role='development_calibration',queries=[dict(targets=[dict(valid=True),dict(valid=False)])])])
        self.align=dict(passed=True,contract_sha256='contract',split_version='s1',valid_auxiliary_targets=1,
             censored_auxiliary_targets=1,maximum_label_difference_m=0.,episodes=[dict(episode_id='ep',group_id='g',
             role='development_calibration',queries=1)])

    def test_development_source_is_selected_only_explicitly(self):
        self.assertEqual(len(select_closed_role(self.manifest,self.split,['ep'],'development_calibration')),1)

    def test_development_cannot_be_selected_as_training(self):
        with self.assertRaisesRegex(ValueError,'Requested role differs'):
            select_closed_role(self.manifest,self.split,['ep'],'train')

    def test_reserved_request_rejected_before_source_io(self):
        with self.assertRaisesRegex(ValueError,'reserved sources stay unread'):
            select_closed_role(self.manifest,self.split,['ep'],'diagnostic_reserved')

    def test_running_episode_rejected(self):
        self.manifest['physical_episodes'][0]['status']='running'
        with self.assertRaisesRegex(ValueError,'Running, planned'):
            select_closed_role(self.manifest,self.split,['ep'],'development_calibration')

    def test_split_role_mismatch_rejected(self):
        self.split['measured_groups']['g']['role']='train'
        with self.assertRaisesRegex(ValueError,'membership'):
            select_closed_role(self.manifest,self.split,['ep'],'development_calibration')

    def test_train_request_matches_explicit_role(self):
        self.manifest['physical_episodes'][0]['role']='train';self.split['measured_groups']['g']['role']='train'
        self.assertEqual(len(select_closed_role(self.manifest,self.split,['ep'],'train')),1)

    def test_dev_release_never_permits_weight_fitting(self):
        r=permissions(self.labels,self.align)
        self.assertTrue(r['development_evaluation']);self.assertFalse(r['weight_fitting'])

    def test_train_release_is_for_training_role_only(self):
        self.labels['episodes'][0]['owner_recorded_role']='train';self.align['episodes'][0]['role']='train'
        r=permissions(self.labels,self.align)
        self.assertTrue(r['weight_fitting']);self.assertFalse(r['development_evaluation'])

    def test_failed_consumer_alignment_blocks_release(self):
        self.align['passed']=False
        with self.assertRaisesRegex(ValueError,'has not passed'):permissions(self.labels,self.align)

    def test_mixed_role_file_is_not_released(self):
        extra=deepcopy(self.labels['episodes'][0]);extra['episode_id']='other';extra['owner_recorded_role']='train'
        self.labels['episodes'].append(extra)
        with self.assertRaisesRegex(ValueError,'one non-reserved role'):permissions(self.labels,self.align)

    def test_geometry_difference_beyond_tolerance_blocks_release(self):
        self.align['maximum_label_difference_m']=1e-3
        with self.assertRaisesRegex(ValueError,'geometry difference'):permissions(self.labels,self.align)

    def test_group_mismatch_blocks_release(self):
        self.align['episodes'][0]['group_id']='different'
        with self.assertRaisesRegex(ValueError,'role, group'):permissions(self.labels,self.align)


if __name__=='__main__':unittest.main()
