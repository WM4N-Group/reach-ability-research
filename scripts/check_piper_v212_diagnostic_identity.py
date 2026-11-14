"""Synthetic identity-only regression. No reserved raw source is ever opened."""
from copy import deepcopy
import json
from pathlib import Path
import unittest
from unittest.mock import patch

import check_piper_v212_diagnostic as fixtures
from check_piper_v212_diagnostic import dump
import piper_v212_diagnostic_identity_v1 as adapted
from piper_v212_diagnostic_contract import code_hashes, purpose_permissions
from bind_piper_v212_registry import sha, verify_reference


class IdentityChecks(unittest.TestCase):
    def setUp(self):
        self.f = fixtures.DiagnosticChecks('test_explicit_closed_reserved_selection')
        self.f.setUp()
        self.addCleanup(self.f.doCleanups)
        self.root = self.f.root
        self.report = dict(path=str(self.root/'synthetic-historical-report'), sha256=adapted.REPORT_SHA)
        self.sequence = dump(self.root/'synthetic-peer-sequence.json', dict(synthetic=True))
        self.alias = dict(episode_id=adapted.ALIAS, recorded=False, role='receipt_baseline_only', status='closed',
                          physical_episode_charge=1, group_id=adapted.GROUP, report=self.report, group_association=adapted.ASSOCIATION)
        self.peer = dict(episode_id=adapted.PEER, recorded=True, role='train', status='closed',
                         group_id=adapted.GROUP, sequence=self.sequence, report=self.report)
        self.f.manifest['physical_episodes'].extend([self.alias, self.peer])
        self.f.split['measured_groups'][adapted.GROUP] = dict(role='train', measured_state_fingerprint=adapted.GROUP,
                                                            episodes=[adapted.ALIAS, adapted.PEER])
        dump(self.f.shared/'group_split.json', self.f.split)
        self.f.manifest['group_split']['sha256'] = sha(self.f.shared/'group_split.json'); self.f.save_manifest()
        # Main metadata proof is mocked only in unit tests, not in production.
        self.decision = dump(self.root/'decision.json', dict(schema='main-receipt-identity-decision-evidence-v1',
            exact_alias=dict(episode_id=adapted.ALIAS, peer_episode_id=adapted.PEER, group_id=adapted.GROUP,
                             report_sha256=adapted.REPORT_SHA)))
        self.addendum = dict(schema=adapted.ADDENDUM_SCHEMA, identity_only=True, after_reserved_outcome_read=True,
            unchanged={x: True for x in adapted.UNCHANGED}, original_protocol=dict(path=str(self.f.protocol_path), sha256=sha(self.f.protocol_path)),
            original_scoring_lock=self.f.protocol['owner_evaluation_lock'],
            reach_adapter=dict(path=adapted.__file__,sha256=sha(adapted.__file__)),
            consumer_auditor=self.f.consumer, observation_auditor=self.f.auditor,
            main_decision=self.decision, owner_identity_addendum=dump(self.root/'owner-addendum.json', dict(
                schema='world-model-v212-receipt-identity-addendum-v1',scope='exact_legacy_receipt_identity_only',
                after_known_5311_physical_failure=True,scoring_mathematics_changed=False,
                models_normalizers_references_changed=False,raw_registry_roles_changed=False,
                original_owner_lock=self.f.protocol['owner_evaluation_lock'],
                original_evaluation_protocol=dict(path=str(self.f.protocol_path),sha256=sha(self.f.protocol_path)),
                owner_adapter_code_sha256={})))
        self.ap = self.root/'identity-addendum.json'; dump(self.ap,self.addendum)
        self.decision_patch = patch.object(adapted, 'DECISION_SHA', self.decision['sha256']); self.decision_patch.start()
        self.addCleanup(self.decision_patch.stop)
        # Only the synthetic historical report bytes are stubbed. All protocol,
        # source, auditor, code and label checks still use actual fixture files.
        def check(ref):
            if ref != self.report: verify_reference(ref)
        self.ref_patch = patch.object(adapted,'verify_reference',side_effect=check)
        self.verify = self.ref_patch.start(); self.addCleanup(self.ref_patch.stop)

    def select(self):
        return adapted.select_reserved(self.f.manifest,self.f.split,[self.f.item['episode_id']])

    def export(self):
        return adapted.export(self.f.shared,self.root,self.f.protocol_path,[self.f.item['episode_id']],self.ap)

    def release_fixture(self):
        labels=self.export();lp=self.root/'adapted-labels.json';dump(lp,labels)
        a=dict(schema='reach-v212-diagnostic-consumer-alignment-v1',passed=True,independently_recomputed=True,
               labels_sha256=sha(lp),evaluation_protocol_sha256=sha(self.f.protocol_path),
               contract_sha256=labels['contract_sha256'],split_version=self.f.split['version'],
               auditor=self.f.consumer,episodes=deepcopy(labels['episodes']),identity_addendum_sha256=sha(self.ap))
        ap=self.root/'adapted-alignment.json';dump(ap,a)
        return lp,ap,a

    def test_only_pinned_receipt_may_project_for_validation(self):
        original=deepcopy(self.f.manifest)
        self.assertEqual(self.select(),[self.f.item]);self.assertEqual(self.f.manifest,original)
        self.assertEqual(self.verify.call_count,3)

    def test_old_guard_still_rejects_alias(self):
        with self.assertRaisesRegex(ValueError,'Cross-role'):
            adapted.original.select_reserved(self.f.manifest,self.f.split,[self.f.item['episode_id']])

    def test_alias_cannot_be_selected_as_reserved_or_turned_into_sample(self):
        with self.assertRaisesRegex(ValueError,'reserved role'):
            adapted.select_reserved(self.f.manifest,self.f.split,[adapted.ALIAS])

    def test_alias_identity_mutations_rejected_before_raw_reads(self):
        for key,value in [('recorded',True),('sequence',self.sequence),('role','train'),('status','running'),
                          ('physical_episode_charge',0),('group_id','other'),('group_association','unregistered')]:
            old=deepcopy(self.alias);self.alias[key]=value;self.verify.reset_mock()
            with self.subTest(key=key),self.assertRaises(ValueError):self.select()
            self.verify.assert_not_called();self.alias.clear();self.alias.update(old)

    def test_peer_identity_mutations_rejected(self):
        for key,value in [('recorded',False),('sequence',None),('role','diagnostic_reserved'),('status','running'),('group_id','other')]:
            old=deepcopy(self.peer);self.peer[key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):self.select()
            self.peer.clear();self.peer.update(old)

    def test_mismatched_report_hash_rejected(self):
        self.alias['report']=dict(self.report,sha256='wrong')
        with self.assertRaisesRegex(ValueError,'report SHA'):self.select()

    def test_missing_alias_peer_or_split_member_rejected(self):
        for which in ('alias','peer','membership'):
            m,s=deepcopy(self.f.manifest),deepcopy(self.f.split)
            if which=='membership':s['measured_groups'][adapted.GROUP]['episodes'].remove(adapted.PEER)
            else:m['physical_episodes']=[e for e in m['physical_episodes'] if e['episode_id'] != (adapted.ALIAS if which=='alias' else adapted.PEER)]
            with self.subTest(which=which),self.assertRaises(ValueError):adapted.select_reserved(m,s,[self.f.item['episode_id']])

    def test_actual_report_bytes_must_match(self):
        self.verify.side_effect=verify_reference
        with self.assertRaises(FileNotFoundError):self.select()

    def test_unrelated_receipt_cannot_inherit_exception(self):
        self.f.manifest['physical_episodes'].append(dict(self.alias,episode_id='unrecognized-receipt'))
        self.f.split['measured_groups'][adapted.GROUP]['episodes'].append('unrecognized-receipt')
        with self.assertRaises(ValueError):self.select()

    def test_recorded_cross_role_collision_still_rejected_before_report_io(self):
        self.f.item['role']='train'
        self.verify.reset_mock()
        with self.assertRaisesRegex(ValueError,'Cross-role'):self.select()
        self.verify.assert_not_called()

    def test_duplicate_or_wrong_fingerprint_still_rejected(self):
        self.f.split['measured_groups'][self.f.item['group_id']]['measured_state_fingerprint']='other'
        with self.assertRaisesRegex(ValueError,'fingerprint'):self.select()

    def test_kernel_namespace_is_private_and_original_hashes_unchanged(self):
        before=code_hashes()
        import export_piper_v212_diagnostic as original_export
        old_registry=original_export.registry
        kernel=adapted.adapted_kernel('export_piper_v212_diagnostic.py',self.ap,self.f.protocol_path)
        self.assertIs(original_export.registry,old_registry)
        self.assertIsNot(kernel.registry,old_registry)
        self.assertEqual(before,code_hashes())

    def test_export_preserves_every_episode_value_and_original_protocol(self):
        # Kernel geometry stub only; no physics/model execution.
        from check_piper_v212_diagnostic import Geometry
        with patch('export_piper_v212_labels.load_geometry',return_value=(Geometry(),{'manifest_sha256':'geometry'})):
            labels=self.export()
        expected=self.f.converted();expected['group_split_version']=self.f.split['version'];expected['skill_bundle_hash']='geometry'
        self.assertEqual(labels['episodes'],[expected])
        self.assertEqual(labels['permissions'],purpose_permissions(False))
        self.assertEqual(labels['reach_code_sha256'],code_hashes())
        self.assertEqual(labels['evaluation_protocol']['sha256'],sha(self.f.protocol_path))
        self.assertTrue(labels['post_outcome_identity_adaptation'])

    def test_adapted_release_is_still_diagnostic_only(self):
        from check_piper_v212_diagnostic import Geometry
        with patch('export_piper_v212_labels.load_geometry',return_value=(Geometry(),{'manifest_sha256':'geometry'})):
            lp,ap,_=self.release_fixture()
        r=adapted.release(lp,ap,self.f.shared,self.f.protocol_path,self.ap)
        self.assertEqual(r['permissions'],purpose_permissions(True));self.assertEqual(r['identity_addendum']['sha256'],sha(self.ap))
        self.assertEqual(r['attempt_count'],1);self.assertFalse(r['training_released'])

    def test_consumer_must_confirm_addendum(self):
        from check_piper_v212_diagnostic import Geometry
        with patch('export_piper_v212_labels.load_geometry',return_value=(Geometry(),{'manifest_sha256':'geometry'})):
            lp,ap,a=self.release_fixture()
        a['identity_addendum_sha256']='wrong';dump(ap,a)
        with self.assertRaisesRegex(ValueError,'confirm'):adapted.release(lp,ap,self.f.shared,self.f.protocol_path,self.ap)

    def test_no_silent_refreeze_or_semantic_change(self):
        for key in ('identity_only','after_reserved_outcome_read'):
            old=self.addendum[key];self.addendum[key]=False;dump(self.ap,self.addendum)
            with self.subTest(key=key),self.assertRaisesRegex(ValueError,'Explicit post-outcome'):
                adapted.validate_addendum(self.ap,self.f.protocol_path,[self.f.item['episode_id']],self.f.split['version'],self.f.protocol['label_contract_sha256'])
            self.addendum[key]=old
        self.addendum['unchanged']['label_semantics']=False;dump(self.ap,self.addendum)
        with self.assertRaisesRegex(ValueError,'preserve'):
            adapted.validate_addendum(self.ap,self.f.protocol_path,[self.f.item['episode_id']],self.f.split['version'],self.f.protocol['label_contract_sha256'])

    def test_addendum_cannot_replace_original_scoring_lock(self):
        self.addendum['original_scoring_lock']=dict(self.addendum['original_scoring_lock'],sha256='other');dump(self.ap,self.addendum)
        with self.assertRaisesRegex(ValueError,'scoring lock'):
            adapted.validate_addendum(self.ap,self.f.protocol_path,[self.f.item['episode_id']],self.f.split['version'],self.f.protocol['label_contract_sha256'])


    def test_original_consumer_output_can_use_explicit_execution_receipt(self):
        from check_piper_v212_diagnostic import Geometry
        with patch('export_piper_v212_labels.load_geometry',return_value=(Geometry(),{'manifest_sha256':'geometry'})):
            lp,ap,a=self.release_fixture()
        a.pop('identity_addendum_sha256');dump(ap,a)
        execution=dict(schema='world-model-v212-identity-adapted-execution-v1',mode='consumer',
            identity_addendum=self.addendum['owner_identity_addendum'],
            original_evaluation_protocol=self.addendum['original_protocol'],
            original_scoring_lock=self.addendum['original_scoring_lock'],
            output=dict(path=str(ap),sha256=sha(ap)),scoring_mathematics_changed=False,
            models_normalizers_references_changed=False,raw_roles_changed=False)
        ep=self.root/'execution.json';dump(ep,execution)
        r=adapted.release(lp,ap,self.f.shared,self.f.protocol_path,self.ap,ep)
        self.assertEqual(r['consumer_identity_execution']['sha256'],sha(ep))
        execution['output']['sha256']='other';dump(ep,execution)
        with self.assertRaisesRegex(ValueError,'execution receipt binding'):
            adapted.release(lp,ap,self.f.shared,self.f.protocol_path,self.ap,ep)

    def test_arbitrary_unrecorded_receipt_outside_group_cannot_skip_checks(self):
        self.f.manifest['physical_episodes'].append(dict(self.alias,episode_id='unrecognized-receipt',group_id=None))
        with self.assertRaisesRegex(ValueError,'No other receipt'):self.select()


if __name__=='__main__':unittest.main()
