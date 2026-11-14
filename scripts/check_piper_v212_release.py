"""Check that a passed alignment cannot release unaligned or held-out sources."""
from copy import deepcopy
import unittest

from release_piper_v212_p0_labels import validate_evidence


class P0ReleaseChecks(unittest.TestCase):
    def setUp(self):
        labels=dict(label_schema_version='s1',contract_sha256='c1',episodes=[])
        p0=dict(passed=True,labels_sha256='labels',contract_sha256='c1',split_version='split1',
                queries=3,valid_auxiliary_targets=3,censored_auxiliary_targets=3,
                maximum_label_difference_m=0.,geometry_numerical_tolerance_m=1e-7,episodes=[])
        alignment=dict(world_model_consumer_passed=True,label_schema_version='s1',labels_sha256='labels',
                       contract=dict(sha256='c1'),group_split=dict(version='split1'))
        binding=dict(label_schema_version='s1',group_split_version='split1',labels=dict(sha256='labels'),episode_bindings=[])
        split=dict(version='split1',measured_groups={});manifest=dict(physical_episodes=[])
        for i in range(3):
            ep,group=f'ep{i}',f'g{i}'
            labels['episodes'].append(dict(episode_id=ep,group_id=group,source_sha256=f's{i}',report_sha256=f'r{i}',
                                           queries=[dict(targets=[dict(valid=True),dict(valid=False)])]))
            p0['episodes'].append(dict(episode_id=ep,group_id=group,role='train',passed=True,query_count=1))
            binding['episode_bindings'].append(dict(episode_id=ep,group_id=group,role='train'))
            split['measured_groups'][group]=dict(role='train',episodes=[ep])
            manifest['physical_episodes'].append(dict(episode_id=ep,group_id=group,role='train',
                    sequence=dict(sha256=f's{i}'),report=dict(sha256=f'r{i}')))
        historical=dict(passed=True,contract_sha256='c1',allowed_for_new_domain_training=False)
        self.args=[labels,binding,alignment,p0,historical,split,manifest,deepcopy(split),deepcopy(manifest)]

    def test_three_aligned_episodes_are_exact_scope(self):
        self.assertEqual(validate_evidence(*self.args),['ep0','ep1','ep2'])

    def test_consumer_must_have_confirmed(self):
        self.args[2]['world_model_consumer_passed']=False
        with self.assertRaisesRegex(ValueError,'consumer checks must pass'):
            validate_evidence(*self.args)

    def test_current_role_change_to_reserved_blocks_release(self):
        self.args[7]['measured_groups']['g1']['role']='diagnostic_reserved'
        with self.assertRaisesRegex(ValueError,'no longer train'):
            validate_evidence(*self.args)

    def test_historical_sources_are_never_released(self):
        self.args[4]['allowed_for_new_domain_training']=True
        with self.assertRaisesRegex(ValueError,'Historical diagnostic'):
            validate_evidence(*self.args)

    def test_fourth_label_episode_cannot_inherit_approval(self):
        self.args[0]['episodes'].append(deepcopy(self.args[0]['episodes'][0]))
        with self.assertRaisesRegex(ValueError,'exactly the three'):
            validate_evidence(*self.args)

    def test_growth_of_other_registry_groups_does_not_expand_release(self):
        self.args[8]['physical_episodes'].append(dict(episode_id='new',role='train'))
        self.args[7]['measured_groups']['gnew']=dict(role='train',episodes=['new'])
        self.assertEqual(validate_evidence(*self.args),['ep0','ep1','ep2'])

    def test_source_hash_drift_blocks_release(self):
        self.args[8]['physical_episodes'][0]['sequence']['sha256']='changed'
        with self.assertRaisesRegex(ValueError,'source identity'):
            validate_evidence(*self.args)

    def test_mask_count_drift_blocks_release(self):
        self.args[3]['valid_auxiliary_targets']=4
        with self.assertRaisesRegex(ValueError,'target checks differ'):
            validate_evidence(*self.args)


if __name__=='__main__':unittest.main()
