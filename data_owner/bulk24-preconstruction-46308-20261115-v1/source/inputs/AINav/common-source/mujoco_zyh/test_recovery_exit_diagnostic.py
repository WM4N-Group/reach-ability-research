"""CPU registration/roles only; passing is NOT physical recovery acceptance."""
import json
from pathlib import Path
import unittest
from mujoco_zyh.recovery_exit_diagnostic import CASES,case_protocol,validate_protocol
from mujoco_zyh.collect import validate_protocol as validate_any,resolve_resource_dir


class DiagnosticRegistration(unittest.TestCase):
    def test_two_fixed_known_development_conditions_not_new_heldout(self):
        self.assertEqual(set(CASES),{'joint2','base-speed'})
        for name in CASES:
            p=case_protocol(name);validate_any(p)
            self.assertEqual(p['role'],'development');self.assertFalse(p['training_allowed'])
            self.assertFalse(p['forecast_study_training_authorized']);self.assertNotIn('option_forecast_case',p)
            self.assertTrue(p['known_condition_NOT_independent_new_sample'].startswith('train-'))

    def test_no_threshold_control_seed_role_or_budget_flip(self):
        for field,value in [('seed',99),('role','test'),('training_allowed',True),('max_sim_seconds',23),('max_wall_seconds',601),
                            ('automatic_retry',True),('reset_after_initial_allowed',1),('WM_forwards',1),('WM_control',True),('training_runs',1)]:
            p=case_protocol('joint2');p[field]=value
            with self.subTest(field=field),self.assertRaises(ValueError):validate_protocol(p)

    def test_geometry_and_capsule_budget_cannot_be_silently_changed(self):
        p=case_protocol('joint2');p['initial_probe_geometry']['initial_box_dy_m']=.4
        with self.assertRaises(ValueError):validate_protocol(p)
        self.assertEqual(case_protocol('joint2')['initial_probe_geometry']['initial_box_dy_m'],.06)
        p=case_protocol('joint2');p['private_failure_capsules']['max_bytes']*=2
        with self.assertRaises(ValueError):validate_protocol(p)

    def test_only_canonical_shared_resource_scope(self):
        p=case_protocol('joint2')
        self.assertEqual(str(resolve_resource_dir(Path('/mnt/yuanyue/data/go2-piper-world-model/exit-capsule-joint2-20261025-v1'),p)),p['resource_lock_dir'])
        p['resource_lock_dir']='/tmp/private-locks'
        with self.assertRaises(ValueError):validate_protocol(p)

    def test_one_shot_small_budget_no_MJB_or_scene_relabel(self):
        for name in CASES:
            p=case_protocol(name)
            self.assertEqual(p['episodes'],1);self.assertEqual(p['max_sim_seconds'],22)
            self.assertEqual(p['max_wall_seconds'],600);self.assertEqual(p['grace_seconds'],10)
            self.assertEqual(p['auxiliary_calibration_worlds_allowed'],1)
            self.assertEqual(p['auxiliary_calibration_max_sim_seconds'],10.5)
            self.assertFalse(p['full_state_review']);self.assertEqual(p['selected_object_id'],'probe_object')
            self.assertEqual(p['scene_recipe'],'zyh_native_single_box')

    def test_unknown_case_refused_not_auto_generated(self):
        p=case_protocol('joint2');p['recovery_exit_diagnostic_case']='lucky-seed-retry'
        with self.assertRaises(ValueError):validate_protocol(p)

    def test_original_safety_and_controller_configuration_preserved(self):
        old=json.loads(Path(__file__).with_name('soft_stall_stow_protocol_v7.json').read_text())
        for name in CASES:
            p=case_protocol(name)
            for key in ('recovery_limits','reference_update_hz','reference_implementation_interior_reserve','unload_control','retreat','balance_COM_reference','delay_ms','stall_stow_mode'):
                self.assertEqual(p[key],old[key])

    def test_old_protocol_does_not_install_diagnostic_recorder(self):
        old=json.loads(Path(__file__).with_name('soft_stall_stow_protocol_v7.json').read_text())
        validate_any(old);self.assertNotIn('recovery_exit_diagnostic_case',old);self.assertNotIn('private_failure_capsules',old)


class ActualKernelLockEvidence(unittest.TestCase):
    def test_real_owned_flock_and_path_inode_equality(self):
        import fcntl,tempfile
        from mujoco_zyh.collect import held_lock_evidence
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'CPU-fixture.lock'
            with path.open('a+') as f:
                with self.assertRaises(ValueError):held_lock_evidence([f],[path])
                fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB)
                rows=held_lock_evidence([f],[path]);self.assertEqual(rows[0]['inode'],path.stat().st_ino)
                self.assertTrue(rows[0]['independent_contender_blocked']);self.assertNotEqual(rows[0]['independent_contender']['PID'],rows[0]['PID'])

    def test_missing_fd_or_replaced_inode_cannot_claim_holding(self):
        import fcntl,tempfile
        from mujoco_zyh.collect import held_lock_evidence
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'CPU-fixture.lock'
            with path.open('a+') as f:
                fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB)
                with self.assertRaises(ValueError):held_lock_evidence([],[path])
                path.rename(Path(temp)/'preserved-old-fixture.lock');path.touch()
                with self.assertRaises(ValueError):held_lock_evidence([f],[path])


if __name__=='__main__':unittest.main()
