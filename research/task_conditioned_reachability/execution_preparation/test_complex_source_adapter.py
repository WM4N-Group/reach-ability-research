"""Public source-file binding software tests, not actual scene/robot trials."""
from hashlib import sha256
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from .complex_source_adapter import COMMON_LIMITS, build_source_bound_planner, declared_nav_xy

ROOT=Path(__file__).resolve().parents[3]/'protocols/2026-11-15/T-COMPLEX-01-source-v2-methods'
TASK_SHA='99d660dee6c044eb4f531cbf72877df7edbc29fcb6cbaf99273a839ab1bfab1d'
PLACEMENTS_SHA='fd295678be5a14c93be25c94ca7966d888413c9dfbd1f473ae5d232ef0cc2a0b'


class SourceBindingTests(unittest.TestCase):
    def build(self,method='multistep',**overrides):
        args=dict(public_task_path=ROOT/'PUBLIC_TASK_V2.json',expected_task_sha256=TASK_SHA,
            finite_placements_path=ROOT/'FINITE_PLACEMENTS_V2.json',expected_placements_sha256=PLACEMENTS_SHA,
            method=method,journal=lambda row:'SOFTWARE-NOT-NATIVE-JOURNAL',terminal_target_ref='cx-goal')
        args.update(overrides);return build_source_bound_planner(**args)
    def test_public_source_snapshots_have_exact_owner_bytes(self):
        self.assertEqual(sha256((ROOT/'PUBLIC_TASK_V2.json').read_bytes()).hexdigest(),TASK_SHA)
        self.assertEqual(sha256((ROOT/'FINITE_PLACEMENTS_V2.json').read_bytes()).hexdigest(),PLACEMENTS_SHA)
    def test_both_methods_use_identical_public_domain_and_resource_ceilings(self):
        a=self.build('greedy');b=self.build()
        self.assertEqual(a.model.task,b.model.task);self.assertEqual(a.model.placements,b.model.placements)
        self.assertEqual(a.limits,b.limits);self.assertEqual(a.source_pins,b.source_pins)
        self.assertEqual(a.model.initial,b.model.initial)
        with self.assertRaises(TypeError):COMMON_LIMITS['max_depth']=99
        self.assertFalse(a.complete);self.assertFalse(b.complete)
    def test_wrong_sha_or_unpinned_file_refused_before_planning(self):
        for v in ('0'*64,'','xyz'):
            with self.assertRaisesRegex(ValueError,'SHA'):
                self.build(expected_task_sha256=v)
        with self.assertRaisesRegex(ValueError,'SHA'):
            self.build(expected_placements_sha256='0'*64)
    def test_changed_bytes_cannot_silently_use_old_source_pin(self):
        with TemporaryDirectory() as d:
            p=Path(d)/'changed-public-task.json';p.write_bytes((ROOT/'PUBLIC_TASK_V2.json').read_bytes()+b'\n')
            with self.assertRaisesRegex(ValueError,'source SHA/size mismatch'):
                self.build(public_task_path=p)
    def test_nav_domain_is_declarations_not_predetermined_success_route(self):
        p=self.build();points=declared_nav_xy(p.model)
        self.assertEqual(len(points),len(set(points)));self.assertIn(p.model.goal_xy,points)
        self.assertEqual(len(p.model.objects),3);self.assertEqual(len(p.model.placements),6)
        for obj in p.model.objects:
            for x in (obj['initial_xy_m'][0],*obj['allowed_placement_x_m']):
                self.assertIn((round(x-obj['size_m'][0]/2-.58,12),0.),points)
        self.assertEqual(p.decision_count,0);self.assertIsNone(p.pending)


if __name__=='__main__':unittest.main()
