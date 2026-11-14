"""Synthetic-only reserved contract checks. Never opens a real reserved source."""
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from bind_piper_v212_registry import sha
from export_piper_v212_diagnostic import PHYSICAL_KEYS, convert, export
from piper_v212_diagnostic_contract import (
    ROLE, AUDIT_SCHEMA, PROTOCOL_SCHEMA, code_hashes, purpose_permissions, select_reserved,
)
from release_piper_v212_diagnostic import release


class Geometry:
    def clearance(self, joints):
        return joints[0]


def dump(path, data):
    path.write_text(json.dumps(data, allow_nan=False))
    return dict(path=str(path), sha256=sha(path))


def trace(n=55, terminal=True):
    def state(step):
        s = {k: [0.] for k in PHYSICAL_KEYS}
        s.update(joint_position_rad=[.08 - step * .0001] + [0.] * 5,
                 legal_hand_contact=step >= 1, invalid_hand_contact=False, forbidden_box_contact=False)
        return s
    return [dict(index=i, env_id=0, interval_start_s=i * .02, interval_end_s=(i + 1) * .02,
                 before=state(i), after=state(i + 1), terminal=terminal and i == n - 1,
                 after_captured_before_reset=terminal and i == n - 1,
                 termination_flags=dict(box_settled=False, time_out=terminal and i == n - 1)) for i in range(n)]


class DiagnosticChecks(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.shared = self.root / 'shared'; self.shared.mkdir()
        self.meta = dict(control_dt_s=.02, joint_names=[f'joint{i}' for i in range(1, 7)],
                         num_envs=1, model_action_authority=False, recorder_sha256='rec', evaluator_sha256='eval')
        self.rows = trace()
        sequence = self.root / 'sequence.jsonl'
        sequence.write_text(''.join(json.dumps(r) + '\n' for r in self.rows))
        self.item = dict(episode_id='synthetic-attempt', group_id='synthetic-measured-group', role=ROLE,
                         status='closed', recorded=True, model_action_authority=False,
                         skill_version='push-direct-approach-v212', task_scope='original_reset_independent_push',
                         sequence=dict(path=str(sequence), sha256=sha(sequence)),
                         metadata=dump(self.root / 'metadata.json', self.meta),
                         startup=dump(self.root / 'startup.json', {'synthetic': True}),
                         report=dump(self.root / 'report.json', {'synthetic': True}))
        self.split = dict(owner='world_model', version='synthetic-split-v1', measured_groups={
            self.item['group_id']: dict(role=ROLE, episodes=[self.item['episode_id']],
                                        measured_state_fingerprint=self.item['group_id'])})
        split_ref = dump(self.shared / 'group_split.json', self.split)
        contract_ref = dump(self.shared / 'label_contract_v1.json', dict(label_schema_version='reach-wm-v212-v1',
            auxiliary_target=dict(threshold_m=.035, horizons_s=[.4, 1.], current_evaluator_declared_control_period_s=.02)))
        self.auditor = dump(self.root / 'owner-auditor.json', {'synthetic_auditor': True})
        self.consumer = dump(self.root / 'consumer-auditor.json', {'synthetic_consumer': True})
        self.protocol = dict(schema=PROTOCOL_SCHEMA, owner='world_model', frozen_before_collection=True,
                             purpose='diagnostic_evaluation_only', permissions=purpose_permissions(True),
                             episode_ids=[self.item['episode_id']], split_version=self.split['version'],
                             label_contract_sha256=contract_ref['sha256'], reach_code_sha256=code_hashes(),
                             owner_evaluation_lock=dump(self.root / 'scoring-lock.json', {'synthetic_lock': True, 'frozen': True, 'read_only_scoring': True, 'allow_fitting': False}),
                             consumer_auditor=self.consumer, observation_auditor=self.auditor,
                             recorder_sha256='rec', evaluator_sha256='eval')
        self.protocol_path = self.root / 'protocol.json'; dump(self.protocol_path, self.protocol)
        self.audit = dict(schema=AUDIT_SCHEMA, owner='world_model', passed=True,
                          episode_id=self.item['episode_id'], group_id=self.item['group_id'], role=ROLE,
                          evaluation_protocol_sha256=sha(self.protocol_path), collection_started_after_freeze=True,
                          sources={k: self.item[k] for k in ('sequence', 'report', 'metadata', 'startup')},
                          execution_status='normal_timeout', no_cross_reset=True, source_integrity_passed=True,
                          auditor=self.auditor, valid_interval_count=len(self.rows), final_after_available=True,
                          verified_task_success=False, verified_goal_time_s=None)
        self.item['diagnostic_observation_audit'] = dump(self.root / 'audit.json', self.audit)
        self.manifest = dict(owner='world_model', group_split=dict(version=self.split['version'], sha256=split_ref['sha256']),
                             physical_episodes=[self.item], frozen_skill_inventory={'sha256': 'geometry'})
        self.save_manifest()

    def save_manifest(self):
        dump(self.shared / 'batch_manifest.json', self.manifest)

    def converted(self, rows=None, audit=None):
        return convert(self.item, audit or self.audit, self.rows if rows is None else rows, self.meta, Geometry())

    def export_labels(self):
        with patch('export_piper_v212_diagnostic.load_geometry', return_value=(Geometry(), {'manifest_sha256': 'geometry'})):
            return export(self.shared, self.root, self.protocol_path, [self.item['episode_id']])

    def release_fixture(self):
        labels = self.export_labels()
        lp = self.root / 'labels.json'; dump(lp, labels)
        alignment = dict(schema='reach-v212-diagnostic-consumer-alignment-v1', passed=True,
                         independently_recomputed=True, labels_sha256=sha(lp),
                         evaluation_protocol_sha256=sha(self.protocol_path), contract_sha256=labels['contract_sha256'],
                         split_version=self.split['version'], auditor=self.consumer, episodes=deepcopy(labels['episodes']))
        ap = self.root / 'alignment.json'; dump(ap, alignment)
        return lp, ap, alignment

    def test_explicit_closed_reserved_selection(self):
        self.assertEqual(select_reserved(self.manifest, self.split, [self.item['episode_id']]), [self.item])

    def test_train_dev_roles_rejected_before_raw_io(self):
        for role in ('train', 'development_calibration'):
            with self.subTest(role=role), patch('export_piper_v212_diagnostic.observation_audit') as raw:
                self.item['role'] = role; self.split['measured_groups'][self.item['group_id']]['role'] = role
                dump(self.shared / 'group_split.json', self.split)
                self.manifest['group_split']['sha256'] = sha(self.shared / 'group_split.json'); self.save_manifest()
                with self.assertRaisesRegex(ValueError, 'reserved role'):
                    self.export_labels()
                raw.assert_not_called()

    def test_planned_running_rejected_before_raw_io(self):
        for status in ('planned', 'running'):
            self.item['status'] = status; self.save_manifest()
            with patch('export_piper_v212_diagnostic.observation_audit') as raw:
                with self.assertRaisesRegex(ValueError, 'owner-closed'): self.export_labels()
                raw.assert_not_called()

    def test_cross_role_reset_collision_rejected(self):
        other = dict(self.item, episode_id='sibling', role='train')
        self.manifest['physical_episodes'].append(other)
        with self.assertRaisesRegex(ValueError, 'Cross-role'): select_reserved(self.manifest, self.split, [self.item['episode_id']])

    def test_duplicate_split_membership_rejected(self):
        self.split['measured_groups']['other'] = dict(role=ROLE, episodes=[self.item['episode_id']], measured_state_fingerprint='other')
        with self.assertRaisesRegex(ValueError, 'Duplicate split'): select_reserved(self.manifest, self.split, [self.item['episode_id']])

    def test_duplicate_ids_rejected(self):
        with self.assertRaisesRegex(ValueError, 'distinct'): select_reserved(self.manifest, self.split, [self.item['episode_id']] * 2)

    def test_preparation_is_not_final_protocol(self):
        self.protocol['schema'] = 'world-model-v212-reserved-diagnostic-preparation-v1'; self.protocol['dispatch_enabled'] = False
        dump(self.protocol_path, self.protocol)
        with patch('export_piper_v212_diagnostic.observation_audit') as raw:
            with self.assertRaisesRegex(ValueError, 'Final owner-frozen'): self.export_labels()
            raw.assert_not_called()

    def test_freeze_code_drift_rejected(self):
        self.protocol['reach_code_sha256']['export_piper_v212_diagnostic.py'] = 'wrong'
        dump(self.protocol_path, self.protocol)
        with self.assertRaisesRegex(ValueError, 'code drift'): self.export_labels()

    def test_export_has_no_purpose_release(self):
        labels = self.export_labels()
        self.assertEqual(labels['permissions'], purpose_permissions(False))
        self.assertEqual(labels['episode_count'], 1)

    def test_normal_timeout_is_known_false(self):
        e = self.converted()
        self.assertIs(e['verified_task_success'], False)
        self.assertTrue(e['stages']['push_complete']['valid'])

    def test_native_failure_and_success(self):
        self.rows[-1]['termination_flags'] = dict(base_contact=True)
        self.audit['execution_status'] = 'native_termination'
        self.assertIs(self.converted()['verified_task_success'], False)
        self.rows[-1]['termination_flags'] = dict(box_settled=True, time_out=False)
        self.audit.update(execution_status='normal_completion', verified_task_success=True, verified_goal_time_s=1.1)
        self.assertIs(self.converted()['verified_task_success'], True)

    def test_terminal_after_is_target_not_query_and_no_padding(self):
        e = self.converted()
        self.assertEqual(e['last_valid_observation_time_s'], 1.1)
        self.assertEqual(e['queries'][-1]['query_time_s'], 1.)
        full = e['queries'][1]['targets'][1]
        self.assertTrue(full['valid'])
        self.assertAlmostEqual(full['value'], .08 - 55 * .0001 - .035)
        partial = e['queries'][2]['targets'][1]
        self.assertIsNone(partial['value']); self.assertFalse(partial['valid'])
        self.assertIsNotNone(partial['observed_prefix_min'])

    def test_runtime_unknown_preserves_complete_windows(self):
        self.rows[-1]['terminal'] = False
        self.audit.update(execution_status='runtime_error', verified_task_success=None)
        e = self.converted()
        self.assertIsNone(e['stages']['push_complete']['value'])
        self.assertFalse(e['stages']['push_complete']['valid'])
        self.assertTrue(e['queries'][0]['targets'][1]['valid'])
        self.assertFalse(e['queries'][-1]['targets'][1]['valid'])
        self.assertTrue(e['stages']['contact_established']['valid'])

    def test_runtime_unknown_must_not_be_filled_with_false(self):
        self.audit.update(execution_status='runtime_error', verified_task_success=False)
        with self.assertRaisesRegex(ValueError, 'cannot be filled'): self.converted()

    def test_missing_after_keeps_last_before_query(self):
        self.rows = trace(n=56, terminal=False); self.rows[-1].pop('after')
        self.audit.update(valid_interval_count=56, final_after_available=False, execution_status='runtime_error', verified_task_success=None)
        e = self.converted()
        self.assertEqual(e['queries'][-1]['query_time_s'], 1.1)
        self.assertFalse(e['queries'][-1]['targets'][0]['valid'])
        self.assertTrue(e['queries'][1]['targets'][1]['valid'])

    def test_missing_log_zero_queries_retained(self):
        self.audit.update(valid_interval_count=0, final_after_available=False, execution_status='missing_log', verified_task_success=None)
        e = self.converted(rows=[])
        self.assertEqual(e['queries'], []); self.assertTrue(e['no_valid_queries'])
        self.assertIsNone(e['last_valid_observation_time_s']); self.assertIsNone(e['verified_task_success'])

    def test_missing_geometry_masks_only_auxiliary(self):
        self.rows[5]['before']['joint_position_rad'][0] = float('nan')
        self.rows[4]['after']['joint_position_rad'][0] = float('nan')
        # Same recorded object for equality, as a nonfinite channel has no geometry evidence.
        self.rows[4]['after']['joint_position_rad'] = self.rows[5]['before']['joint_position_rad']
        e = self.converted()
        self.assertFalse(e['queries'][0]['targets'][0]['valid'])
        self.assertIs(e['verified_task_success'], False)

    def test_reset_timing_and_state_gap_rejected(self):
        for mutation in ('terminal', 'time', 'state'):
            rows = deepcopy(self.rows)
            if mutation == 'terminal': rows[2]['terminal'] = True
            elif mutation == 'time': rows[2]['interval_start_s'] += .02
            else: rows[2]['before']['box_position_xyz'] = [9.]
            with self.subTest(mutation=mutation), self.assertRaises(ValueError): self.converted(rows=rows)

    def test_non_pre_reset_terminal_after_rejected(self):
        self.rows[-1]['after_captured_before_reset'] = False
        with self.assertRaisesRegex(ValueError, 'before reset'): self.converted()

    def test_substituted_source_sha_blocks_export(self):
        Path(self.item['sequence']['path']).write_text('changed')
        with self.assertRaises(ValueError): self.export_labels()

    def test_release_is_diagnostic_only(self):
        lp, ap, _ = self.release_fixture()
        r = release(lp, ap, self.shared, self.protocol_path)
        self.assertEqual(r['permissions'], purpose_permissions(True))
        self.assertFalse(r['training_released']); self.assertFalse(r['development_evaluation_released'])

    def test_consumer_pass_failure_or_copied_claim_rejected(self):
        for key in ('passed', 'independently_recomputed'):
            lp, ap, a = self.release_fixture(); a[key] = False; dump(ap, a)
            with self.assertRaisesRegex(ValueError, 'Independent consumer'): release(lp, ap, self.shared, self.protocol_path)

    def test_consumer_mask_value_identity_drift_rejected(self):
        for mutation in ('value', 'mask', 'group', 'status', 'time'):
            lp, ap, a = self.release_fixture(); ep = a['episodes'][0]
            if mutation == 'value': ep['queries'][0]['targets'][0]['value'] += .001
            elif mutation == 'mask': ep['queries'][0]['targets'][0]['valid'] = False
            elif mutation == 'group': ep['group_id'] = 'other'
            elif mutation == 'status': ep['execution_status'] = 'normal_completion'
            else: ep['queries'][0]['query_time_s'] = .1
            dump(ap, a)
            with self.subTest(mutation=mutation), self.assertRaisesRegex(ValueError, 'alignment differs'):
                release(lp, ap, self.shared, self.protocol_path)

    def test_per_file_hash_not_top_level_ready(self):
        lp, ap, a = self.release_fixture(); a['labels_sha256'] = 'wrong'; dump(ap, a)
        with self.assertRaisesRegex(ValueError, 'file/protocol'): release(lp, ap, self.shared, self.protocol_path)

    def test_protocol_or_consumer_code_drift_blocks_release(self):
        lp, ap, _ = self.release_fixture()
        Path(self.consumer['path']).write_text('changed')
        with self.assertRaises(ValueError): release(lp, ap, self.shared, self.protocol_path)

    def test_current_source_role_drift_blocks_release(self):
        lp, ap, _ = self.release_fixture(); self.item['role'] = 'train'; self.save_manifest()
        with self.assertRaises(ValueError): release(lp, ap, self.shared, self.protocol_path)

    def test_missing_log_inventory_can_release_but_has_no_score(self):
        self.item.update(recorded=False, sequence=None, metadata=None, startup=None, report=None)
        self.audit.update(valid_interval_count=0, final_after_available=False, execution_status='missing_log',
                          verified_task_success=None, sources={k: None for k in ('sequence','report','metadata','startup')})
        self.item['diagnostic_observation_audit'] = dump(self.root / 'audit.json', self.audit); self.save_manifest()
        lp, ap, _ = self.release_fixture(); r = release(lp, ap, self.shared, self.protocol_path)
        self.assertEqual(r['attempt_count'], 1); self.assertEqual(r['valid_auxiliary_targets'], 0)
        self.assertEqual(r['zero_query_episode_ids'], [self.item['episode_id']])


    def test_preparation_cannot_be_wrapped_as_scoring_lock(self):
        lock = dict(schema='world-model-v212-reserved-diagnostic-preparation-v1', dispatch_enabled=False)
        self.protocol['owner_evaluation_lock'] = dump(self.root / 'scoring-lock.json', lock)
        dump(self.protocol_path, self.protocol)
        with self.assertRaisesRegex(ValueError, 'must be final/read-only'): self.export_labels()

    def test_protocol_binding_required_before_source_reads(self):
        self.audit['evaluation_protocol_sha256'] = 'other-lock'
        self.item['diagnostic_observation_audit'] = dump(self.root / 'audit.json', self.audit); self.save_manifest()
        with self.assertRaisesRegex(ValueError, 'not bound'): self.export_labels()

    def test_short_prefix_does_not_require_old_builder_minimum(self):
        self.rows = trace(n=1, terminal=False)
        self.rows[0]['after']['legal_hand_contact'] = False
        self.audit.update(valid_interval_count=1, execution_status='runtime_error', verified_task_success=None)
        e = self.converted()
        self.assertEqual(len(e['queries']), 1)
        self.assertTrue(e['no_complete_auxiliary_targets'])
        self.assertIsNone(e['stages']['contact_established']['value'])

    def test_verified_goal_survives_later_runtime_error(self):
        self.rows[-1]['terminal'] = False
        self.audit.update(execution_status='runtime_error', verified_task_success=True, verified_goal_time_s=.9)
        e = self.converted()
        self.assertTrue(e['stages']['push_complete']['valid'])
        self.assertIs(e['stages']['push_complete']['value'], True)
        self.assertEqual(e['stages']['push_complete']['observed_until_s'], .9)

    def test_normal_terminal_without_after_or_flags_is_not_a_failure_label(self):
        self.audit['final_after_available'] = False
        with self.assertRaisesRegex(ValueError, 'pre-reset terminal'): self.converted()
        self.audit['final_after_available'] = True
        self.rows[-1]['termination_flags'] = {}
        with self.assertRaisesRegex(ValueError, 'flags missing'): self.converted()

    def test_missing_geometry_after_gap_does_not_rejoin_for_target(self):
        self.rows[5]['before']['joint_position_rad'] = []
        self.rows[4]['after']['joint_position_rad'] = []
        e = self.converted()
        t = e['queries'][0]['targets'][0]
        self.assertFalse(t['valid'])
        self.assertEqual(t['observed_sample_count'], 5)
        self.assertTrue(e['queries'][2]['targets'][0]['valid'])

    def test_two_same_reset_attempts_count_as_one_group(self):
        sibling = dict(self.item, episode_id='synthetic-related-repeat')
        self.manifest['physical_episodes'].append(sibling)
        self.split['measured_groups'][self.item['group_id']]['episodes'].append(sibling['episode_id'])
        selected = select_reserved(self.manifest, self.split, [self.item['episode_id'], sibling['episode_id']])
        self.assertEqual(len(selected), 2); self.assertEqual(len({e['group_id'] for e in selected}), 1)

    def test_permission_escalation_in_export_blocks_release(self):
        lp, ap, a = self.release_fixture()
        labels = json.loads(lp.read_text()); labels['permissions']['allowed_for_new_v212_training'] = True
        dump(lp, labels); a['labels_sha256'] = sha(lp); dump(ap, a)
        with self.assertRaisesRegex(ValueError, 'purpose isolation'): release(lp, ap, self.shared, self.protocol_path)

    def test_consumer_tolerance_is_only_numerical(self):
        lp, ap, a = self.release_fixture()
        a['episodes'][0]['queries'][0]['targets'][0]['value'] += 1e-8
        dump(ap, a)
        self.assertTrue(release(lp, ap, self.shared, self.protocol_path)['diagnostic_evaluation_released'])


if __name__ == '__main__':
    unittest.main()
