"""Pure CPU path contracts; no lock is acquired and no old root is edited."""
import unittest
from pathlib import Path
from mujoco_zyh.collect import resolve_resource_dir,CANONICAL_RESOURCE_DIR
from mujoco_zyh.option_probe import load_plan,case_protocol

class CanonicalLocks(unittest.TestCase):
    def test_flat_registered_root_uses_canonical_default(self):self.assertEqual(resolve_resource_dir(CANONICAL_RESOURCE_DIR/'one',{}),CANONICAL_RESOURCE_DIR)
    def test_nested_root_without_explicit_scope_is_refused(self):
        with self.assertRaises(ValueError):resolve_resource_dir(CANONICAL_RESOURCE_DIR/'study/episodes/a',{})
    def test_nested_with_explicit_canonical_scope(self):self.assertEqual(resolve_resource_dir(CANONICAL_RESOURCE_DIR/'study/episodes/a',dict(resource_lock_dir=str(CANONICAL_RESOURCE_DIR))),CANONICAL_RESOURCE_DIR)
    def test_foreign_or_relative_scope_refused(self):
        for scope in ('local','/tmp','/mnt/yuanyue/data/go2-piper-world-model/study'):
            with self.assertRaises(ValueError):resolve_resource_dir(CANONICAL_RESOURCE_DIR/'study/a',dict(resource_lock_dir=scope))
    def test_formal_live_root_outside_registered_directory_refused(self):
        with self.assertRaises(ValueError):resolve_resource_dir('/tmp/test',dict(resource_lock_dir=str(CANONICAL_RESOURCE_DIR)))
    def test_all_new_option_case_builders_explicit(self):
        for case in load_plan()['cases']:self.assertEqual(case_protocol(case)['resource_lock_dir'],str(CANONICAL_RESOURCE_DIR))

if __name__=='__main__':unittest.main()
