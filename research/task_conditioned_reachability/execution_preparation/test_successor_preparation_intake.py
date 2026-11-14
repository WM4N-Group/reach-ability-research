"""New contract-join tests only; native/physics qualification is NOT exercised."""
from dataclasses import asdict, replace
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from .successor_preparation_intake import (
    verify_release, build_intake, minimal_public_input, unavailable_model_check,
    VerifiedRelease, IDS, CONTRACT, EXAMPLES, COMMON, consume_owner_public_api,
)
from .successor_aware_choice import DecisionInput, InputValue

AINAV_ROOT = '/home/yuanyue/main/work/ainav/consumer-deliveries/AINAV-CLIMB-PREPARATION-CANDIDATES-20261113-v1'
DATA_ROOT = '/home/yuanyue/main/work/data-team/consumer-deliveries/AINAV-DATA-SUCCESSOR-AWARE-PAIRED-CAPTURE-CPU-TEMPLATE-20261113-v1'
AINAV_SHA = '0c17d2e70139a86a14b7a87fa9fb2cd6ed1bd37d8873a009a7b7613bea40718e'
DATA_SHA = '26df01074ec037fae456ef25b695fe20ac7ec4ffb704f6ede5e38852688dba18'


def owner_snapshots():
    return (verify_release(AINAV_ROOT, 'CANDIDATE_RELEASE_v1.json',
                           expected_release_sha256=AINAV_SHA, inventory_field='files_sha256'),
            verify_release(DATA_ROOT, 'release.json',
                           expected_release_sha256=DATA_SHA, inventory_field='files'))


def changed(snapshot, name, mutate):
    """Deliberately synthetic in-memory corruption, NOT a verified owner release."""
    members = dict(snapshot.members)
    row = json.loads(members[name]); mutate(row)
    members[name] = json.dumps(row).encode()
    return replace(snapshot, members=tuple(members.items()))


class ReleaseIntegrityTests(unittest.TestCase):
    def fixture(self, root, members=None):
        members = members or {'a.json': b'{"example":true}'}
        release = dict(files={n:hashlib.sha256(b).hexdigest() for n,b in members.items()})
        for name, raw in members.items():(root/name).write_bytes(raw)
        raw = json.dumps(release).encode(); (root/'release.json').write_bytes(raw)
        return hashlib.sha256(raw).hexdigest()

    def test_capture_immutable_verified_bytes(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); pin=self.fixture(root)
            snap=verify_release(root,'release.json',expected_release_sha256=pin,inventory_field='files')
            (root/'a.json').write_text('tampered after intake')
            self.assertEqual(snap.document('a.json'), {'example':True})

    def test_release_pin_mismatch_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); self.fixture(root)
            with self.assertRaisesRegex(ValueError, 'Release SHA mismatch'):
                verify_release(root,'release.json',expected_release_sha256='0'*64,inventory_field='files')

    def test_member_tamper_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); pin=self.fixture(root); (root/'a.json').write_text('{}')
            with self.assertRaisesRegex(ValueError, 'Member SHA mismatch'):
                verify_release(root,'release.json',expected_release_sha256=pin,inventory_field='files')

    def test_traversal_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); raw=json.dumps({'files':{'../escape':'a'*64}}).encode()
            (root/'release.json').write_bytes(raw)
            with self.assertRaisesRegex(ValueError, 'Canonical relative'):
                verify_release(root,'release.json',expected_release_sha256=hashlib.sha256(raw).hexdigest(),inventory_field='files')

    def test_symlink_member_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); pin=self.fixture(root)
            (root/'other').write_bytes((root/'a.json').read_bytes()); (root/'a.json').unlink()
            (root/'a.json').symlink_to(root/'other')
            with self.assertRaisesRegex(ValueError, 'Regular member'):
                verify_release(root,'release.json',expected_release_sha256=pin,inventory_field='files')


class OwnerJoinTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.a, cls.b = owner_snapshots()
        cls.d, cls.s, cls.p, cls.payloads = build_intake(cls.a, cls.b)

    def reject(self, name, mutate, message):
        with self.assertRaisesRegex(ValueError, message):
            build_intake(changed(self.a,name,mutate),self.b)

    def test_all_317_owner_members_integrity_checked(self):
        self.assertEqual((len(self.a.members),len(self.b.members)), (299,18))

    def test_three_same_task_common_profile_no_fake_direct_arm(self):
        self.assertEqual(tuple(c.candidate_id for c in self.d.candidates), IDS)
        self.assertEqual(len({c.task_sha256 for c in self.d.candidates}),1)
        self.assertEqual(len({c.execution_profile_sha256 for c in self.d.candidates}),1)
        self.assertIsNone(self.d.direct_id)
        self.assertEqual(self.d.role,'CPU_TEST_ONLY')

    def test_domain_expansion_rejected(self):
        self.reject(CONTRACT,lambda x:x['candidate_ids'].append('extra'), 'three-candidate')

    def test_success_gate_relaxation_rejected(self):
        self.reject(CONTRACT,lambda x:x.update(original_controller_guards_QP_queue_FIFO_12N_4s_unchanged=False), 'contract changed')

    def test_wrong_common_stow_only_verifier_rejected(self):
        self.reject(COMMON,lambda x:x['changed_original_source_files'].pop(), 'three-file')

    def test_current_source_pin_mismatch_rejected(self):
        self.reject(COMMON,lambda x:x['source_delta_pins'].update({'ainav/native/execution_judged_course.py':'a'*64}), 'does not match')

    def test_moved_CLIMB_reference_rejected(self):
        self.reject(EXAMPLES,lambda x:x['candidates'][1].update(original_approach_xy=[0.,-1.96]), 'NAV preparation goal')

    def test_changed_offset_rejected(self):
        self.reject(EXAMPLES,lambda x:x['candidates'][1].update(NAV_goal_xy=[.05,-1.8]), 'NAV preparation goal')

    def test_boolean_height_not_number(self):
        self.reject(EXAMPLES,lambda x:x['candidates'][0].update(source_surface_height_m=False), 'NAV preparation goal')

    def test_payload_extra_actuator_override_rejected(self):
        self.reject(EXAMPLES,lambda x:x['execution_payloads'][1].update(force=12.), 'no extra control')

    def test_payload_wrong_target_rejected(self):
        self.reject(EXAMPLES,lambda x:x['execution_payloads'][1].update(target_ref='other'), 'same-target')

    def test_posthoc_cost_is_not_prospective_prediction(self):
        self.reject(EXAMPLES,lambda x:x['candidates'][1].update(predicted_complete_successor_cost_s=1.), 'not a prospective')

    def test_private_world_pose_not_in_public_schema(self):
        inp=DecisionInput(self.d.task.sha256,self.s.sha256,0.,'HIGH_LEVEL_PLANNER',
            (InputValue('base_world_xy',[0.,0.],'ONLINE_PUBLIC',0.,'forged public label'),))
        with self.assertRaisesRegex(ValueError,'Unregistered'):self.s.validate(inp)

    def test_static_example_no_fabricated_xyz_or_native_observation(self):
        inputs=minimal_public_input(self.d,self.s,self.p,decision_time_s=0.)
        self.assertEqual(len(inputs.values[1].value),2)
        self.assertTrue(all('NOT_FRESH_OBSERVATION' in x.source_ref for x in inputs.values))

    def test_no_dynamic_model_abstains_not_zero_or_pass(self):
        inp=minimal_public_input(self.d,self.s,self.p,decision_time_s=0.)
        out=unavailable_model_check(self.d,self.s,inp)
        self.assertTrue(all(r['candidate_id'] is None and r['execution_authorized'] is False for r in out.values()))
        self.assertEqual(out['current_greedy']['status'],'UNRESOLVED_COMMON_FEASIBILITY')
        self.assertEqual(out['successor_aware']['status'],'UNRESOLVED_COMMON_FEASIBILITY')
        self.assertEqual(out['direct_strong']['status'],'NOT_APPLICABLE_NO_OWNER_DIRECT_CANDIDATE')
        self.assertTrue(all(r['shared_candidate_evaluations']==3 for r in out.values()))

    def test_stage_B_is_three_branch_not_faked_two_policies(self):
        self.assertEqual(len(self.p['branches']),3)
        self.assertFalse(self.p['dispatch']); self.assertFalse(self.p['physical_admission'])
        self.assertTrue(all(x['scope_ids'] is None for x in self.p['branches']))
        self.assertIn('UNKNOWN_COST_MODEL',self.p['online_current_only_and_successor_aware'])
        self.assertTrue(any('hardcodes two policy arms' in x for x in self.p['missing_owner_bindings']))

    def test_actual_owner_public_API_consumes_all_three_finite_payloads(self):
        result=consume_owner_public_api(self.a,self.p,self.payloads)
        self.assertEqual(len(result['selections']),3)
        self.assertFalse(result['bind_to_host_called'])
        self.assertFalse(result['Host_or_Runtime_constructed'])

    def test_motor_equivalence_left_unknown(self):
        self.assertTrue(all(b['actual_control_equivalence'].startswith('UNKNOWN') for b in self.p['branches']))
        self.assertEqual(self.p['new_physical_H1_cases'],0)

    def test_ready_branch_no_forced_nav_and_fresh_native_clocks_not_inferred(self):
        self.assertIn('No forced NAV',self.p['original_READY_at_decision'])
        self.assertIn('still require owner binding',self.p['stage_clocks'])
        self.assertTrue(self.p['raw_third_view']['old_missing_footage_must_not_be_backfilled'])


if __name__ == '__main__':unittest.main()
