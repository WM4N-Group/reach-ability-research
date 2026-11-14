"""Check incremental source eligibility and observed-terminal window semantics."""
import unittest

from export_piper_v212_registered_train import select_closed_train
from export_piper_v212_labels import auxiliary_queries


class IncrementChecks(unittest.TestCase):
    def setUp(self):
        self.manifest=dict(physical_episodes=[dict(episode_id='new-train',role='train',group_id='g',
             status='closed',recorded=True,skill_version='push-direct-approach-v212',
             task_scope='original_reset_independent_push')])
        self.split=dict(measured_groups={'g':dict(role='train',episodes=['new-train'])})

    def test_explicit_closed_training_source_is_selected(self):
        self.assertEqual(select_closed_train(self.manifest,self.split,['new-train']),self.manifest['physical_episodes'])

    def test_non_train_source_rejected_before_any_io(self):
        self.manifest['physical_episodes'][0]['role']='diagnostic_reserved'
        with self.assertRaisesRegex(ValueError,'Only explicit training'):
            select_closed_train(self.manifest,self.split,['new-train'])

    def test_started_but_not_closed_source_is_not_labeled(self):
        self.manifest['physical_episodes'][0]['status']='running'
        with self.assertRaisesRegex(ValueError,'Running, planned'):
            select_closed_train(self.manifest,self.split,['new-train'])

    def test_role_is_not_inferred_from_seed(self):
        self.split['measured_groups']['g']['episodes']=[]
        with self.assertRaisesRegex(ValueError,'membership'):
            select_closed_train(self.manifest,self.split,['new-train'])

    def test_duplicate_id_cannot_duplicate_labels(self):
        with self.assertRaisesRegex(ValueError,'distinct episode IDs'):
            select_closed_train(self.manifest,self.split,['new-train','new-train'])

    def test_observed_terminal_can_complete_label_but_is_not_new_query(self):
        states=[dict(legal_hand_contact=True,invalid_hand_contact=False,forbidden_box_contact=False)
                for _ in range(51)]
        rows=[dict(step=i,time_s=i*.02,clearance_m=.06) for i in range(51)]
        queries=auxiliary_queries(states,rows,.02)
        self.assertTrue(queries[0]['targets'][1]['valid']) # endpoint1.0 is observed terminal after
        self.assertEqual(queries[0]['targets'][1]['observed_sample_count'],51)
        self.assertAlmostEqual(queries[-1]['query_time_s'],.9)
        self.assertFalse(queries[-1]['targets'][1]['valid'])
        self.assertTrue(all(q['query_time_s']<1.0 for q in queries))


if __name__=='__main__':unittest.main()
