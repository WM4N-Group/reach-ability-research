"""Checks against conflicting roles, source drift and duplicate physical budgets."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from bind_piper_v212_registry import bind, sha


class RegistryChecks(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup)
        self.root=Path(temp.name)
        def ref(name):
            p=self.root/name;p.write_text(name)
            return dict(path=str(p),sha256=sha(p))
        self.source=ref('sequence.jsonl');self.report=ref('report.json')
        inventory=ref('inventory.json');self.inventory=inventory
        self.contract=dict(label_schema_version='reach-wm-v212-v1',
                           collection=dict(shared_physical_episode_cap=36))
        (self.root/'label_contract_v1.json').write_text(json.dumps(self.contract))
        self.split=dict(owner='world_model',version='s1',
                        measured_groups={'g1':dict(role='train',episodes=['ep1'],measured_state_fingerprint='g1')},
                        planned_slots=[dict(episode_id='future',role='diagnostic_reserved')],
                        source_role_plan=ref('roleplan.json'),source_new_collection_plan=ref('nextplan.json'))
        self.ledger=[dict(event='import_closed_physical_attempt',episode_id='ep1',charged_attempt_delta=1,reserved_attempt_delta=0),
                     dict(event='reserve_unattempted_plan',episode_id='future',role='diagnostic_reserved',charged_attempt_delta=0,reserved_attempt_delta=1)]
        self.manifest=dict(owner='world_model',actual_charged_attempts=1,active_reserved_attempts=1,
                           shared_physical_episode_cap=36,budget_remaining_including_reserved=35,budget_unreserved=34,
                           group_split=dict(path=str(self.root/'group_split.json'),version='s1'),
                           source_p0_ledger=ref('originalledger.json'),frozen_skill_inventory=inventory,
                           physical_episodes=[dict(episode_id='ep1',group_id='g1',role='train',status='closed',recorded=True,
                               physical_episode_charge=1,task_scope='original_reset_independent_push',skill_version='push-direct-approach-v212',
                               sequence=self.source,report=self.report,metadata=ref('metadata.json'),startup=ref('startup.json'),
                               query_count=1,outcome=dict(verified_task_success=True))],
                           planned_episodes=[dict(episode_id='future',role='diagnostic_reserved')])
        self.labels=dict(label_schema_version='reach-wm-v212-v1',contract_sha256=sha(self.root/'label_contract_v1.json'),
                         episodes=[dict(episode_id='ep1',group_id='g1',owner_recorded_role='train',source_path=self.source['path'],
                             source_sha256=self.source['sha256'],report_sha256=self.report['sha256'],queries=[{}],verified_task_success=True,
                             task_scope='original_reset_independent_push',skill_version='push-direct-approach-v212',skill_bundle_hash=inventory['sha256'])])
        self.labels_path=self.root/'labels.json'

    def run_binding(self):
        (self.root/'group_split.json').write_text(json.dumps(self.split))
        (self.root/'collection_ledger.jsonl').write_text('\n'.join(json.dumps(e) for e in self.ledger)+'\n')
        self.manifest['group_split']['sha256']=sha(self.root/'group_split.json')
        self.manifest['collection_ledger_sha256']=sha(self.root/'collection_ledger.jsonl')
        (self.root/'batch_manifest.json').write_text(json.dumps(self.manifest))
        self.labels_path.write_text(json.dumps(self.labels))
        return bind(self.labels_path,self.root)

    def test_correct_binding_does_not_release_training(self):
        r=self.run_binding()
        self.assertFalse(r['training_released'])
        self.assertFalse(r['reserved_source_outcomes_read'])
        self.assertEqual(r['episode_bindings'][0]['group_split_version'],'s1')
        self.assertEqual(r['labels']['sha256'],sha(self.labels_path))

    def test_non_training_role_rejected_before_raw_reads(self):
        self.manifest['physical_episodes'][0]['role']='diagnostic_reserved'
        with patch('bind_piper_v212_registry.verify_reference',side_effect=AssertionError('raw source opened')):
            with self.assertRaisesRegex(ValueError,'refuse non-training'):
                self.run_binding()

    def test_same_episode_cannot_cross_groups(self):
        self.split['measured_groups']['g2']=dict(role='train',episodes=['ep1'],measured_state_fingerprint='g2')
        with self.assertRaisesRegex(ValueError,'more than one group'):
            self.run_binding()

    def test_budget_disagreement_is_not_accepted(self):
        self.ledger[0]['charged_attempt_delta']=2
        with self.assertRaisesRegex(ValueError,'budget accounting'):
            self.run_binding()

    def test_raw_source_drift_is_not_accepted(self):
        Path(self.source['path']).write_text('changed after collection')
        with self.assertRaisesRegex(ValueError,'checksum mismatch'):
            self.run_binding()

    def test_labels_not_in_registry_cannot_be_silently_bound(self):
        self.labels['episodes'][0]['episode_id']='missing'
        with self.assertRaisesRegex(ValueError,'absent from canonical'):
            self.run_binding()


if __name__=='__main__':
    unittest.main()
