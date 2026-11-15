"""Selected-B protocol/source CPU contracts, not live B execution acceptance."""
import json,os,sys,unittest
from pathlib import Path
from mujoco_zyh.reselect_B import validate_protocol,compile_entry_and_machine,dependency_hashes

class ExplicitBAdmission(unittest.TestCase):
    def p(self):return json.loads(Path(__file__).with_name('reselect_B_protocol_v1.json').read_text())
    def recorded(self):return json.loads(Path(__file__).with_name('reselect_B_recorded_protocol_v2.json').read_text())
    def test_exact_scope(self):self.assertEqual(validate_protocol(self.p())['scene_recipe'],'research_threebox')
    def test_no_probe_relabeling(self):self.assertNotIn('probe_physics',self.p())
    def test_no_automatic_retry_or_training(self):
        p=self.p();self.assertFalse(p['automatic_retry']);self.assertEqual(p['training_runs'],0);self.assertEqual(p['reset_after_initial_allowed'],0)
    def test_cannot_change_B_identity_or_target(self):
        p=self.p();p['selected_object_id']='middle'
        with self.assertRaises(ValueError):validate_protocol(p)
    def test_original_zero_arm_gate_is_not_claimed(self):self.assertTrue(self.p()['B_entry']['unchanged_other_native_entry_gates'])
    def test_helpers_reused_not_global_alias_swapper(self):
        deps=dependency_hashes();self.assertIn('native_target_context.py',deps);self.assertIn('native_candidate_contact_layout.py',deps)
        self.assertNotIn('multibox_runtime_binding.py',deps)
    def test_bounded_main_episode(self):
        p=self.p();self.assertEqual(p['max_sim_seconds'],180);self.assertEqual(p['max_wall_seconds'],3600);self.assertEqual(p['grace_seconds'],10)
    def test_new_recorded_run_requires_exact_private_capsule_and_new_identity(self):
        from mujoco_zyh.collect import validate_protocol as validate_collection
        p=self.recorded();self.assertEqual(validate_collection(p)['source_id'],'mujoco-A-recovery-selected-B-recorded-20261025-v2')
        self.assertNotEqual(p['source_id'],self.p()['source_id'])
        self.assertEqual(p['private_failure_capsules']['max_capsules'],8)
        p['private_failure_capsules']['max_capsules']=9
        with self.assertRaises(ValueError):validate_collection(p)
    def test_source_pinned_entry_and_machine_hunks_restore_exact_original(self):
        sys.path.insert(0,str(Path(os.environ['ZYH_BUNDLE'])/'switch'))
        Machine,receipt=compile_entry_and_machine(os.environ['ZYH_BUNDLE'])
        self.assertTrue(receipt['inverse_restores_exact_original']);self.assertEqual(receipt['entry_hunks'],2);self.assertEqual(receipt['machine_hunks'],2)
        self.assertTrue(receipt['all_other_native_actor_entry_router_guard_code_unchanged'])

if __name__=='__main__':unittest.main()
