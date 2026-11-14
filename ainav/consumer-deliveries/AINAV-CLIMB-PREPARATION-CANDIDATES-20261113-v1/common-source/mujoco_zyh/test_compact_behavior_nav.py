"""Protected owner reuse/reference contract. CPU fixtures; no physics/actors."""
import tempfile
from pathlib import Path
from types import SimpleNamespace as NS
from unittest.mock import patch
import unittest
import numpy as np
import torch
from mujoco_zyh.behavior_authority import BehaviorOption
from mujoco_zyh.native_behavior_executor import compact_nav_session, world_snapshot
from mujoco_zyh.resume_nav import ResumeNavRouter, NAV_ARM
from mujoco_zyh.stall_stow import StallStowRouter


class CompactBehaviorNavTests(unittest.TestCase):
    def fixture(self):
        class Command:
            position = np.zeros(18)
        sim = NS(data=NS(time=0., qpos=np.zeros(25), qvel=np.zeros(24)), queue=[],
                 box_push_target=torch.tensor([[1.7, 0., .1]]))
        runtime = NS(sim=sim, last=Command(), n=NS(ee_command=np.zeros(3)), step_count=0)
        native = NS(events=[], results=[], switch_metrics=[])
        prefix = object.__new__(StallStowRouter)
        prefix.r = runtime
        prefix.native = native
        prefix.recovery = NS(complete=True, reference=NAV_ARM.copy(), velocity=np.zeros(6))
        prefix.retired_history_sentinel = object()
        return runtime, native, prefix

    def test_actual_completed_prefix_reused_without_another_PUSH_router(self):
        runtime, native, prefix = self.fixture()
        termination_sentinel = object()
        runtime.sim.termination = termination_sentinel
        with tempfile.TemporaryDirectory() as root, \
             patch('mujoco_zyh.resume_nav.compact_contract', return_value={}), \
             patch.object(StallStowRouter, '__init__', side_effect=AssertionError('No new PUSH owner')):
            nav = ResumeNavRouter(runtime, native, root, completed_prefix=prefix)
            try:
                self.assertIs(nav.prefix, prefix)
                self.assertIs(runtime.sim.termination, termination_sentinel)
            finally:
                nav.policy_log.close();nav.actual_log.close()

    def test_incomplete_wrong_native_or_foreign_owner_rejected(self):
        runtime, native, prefix = self.fixture()
        for field, value in [('r', object()), ('native', object()), ('recovery', NS(complete=False))]:
            before = getattr(prefix, field)
            setattr(prefix, field, value)
            with self.assertRaises(ValueError):
                ResumeNavRouter(runtime, native, '/must-not-create-files', completed_prefix=prefix)
            setattr(prefix, field, before)

    def test_explicit_goal_and_surface_references_do_not_change_world_or_queue(self):
        for height in (0., .4):
            runtime, native, prefix = self.fixture()
            resets = []
            runtime.reset_nav_history = lambda *args: resets.append(args)
            before = world_snapshot(runtime)
            with tempfile.TemporaryDirectory() as root, \
                 patch('mujoco_zyh.resume_nav.compact_contract', return_value={}), \
                 patch('mujoco_zyh.resume_nav.nominal_compact_ee', return_value=np.array([.1, .2, .3])), \
                 patch('mujoco_zyh.resume_nav.make_compact_nav', side_effect=lambda r, g: NS(goal=g.copy())):
                nav = ResumeNavRouter(runtime, native, root, completed_prefix=prefix)
                try:
                    nav.registered_goal_xy = np.array([.07, -2.])
                    nav.declared_surface_height_m = height
                    nav.begin_nav()
                    self.assertTrue(np.array_equal(nav.nav.goal, [.07, -2.]))
                    self.assertEqual(resets, [() if height == 0. else (.4,)])
                    self.assertAlmostEqual(runtime.n.ee_command[2], .3+height)
                    self.assertEqual(before, world_snapshot(runtime))
                    self.assertIs(nav.prefix.retired_history_sentinel, prefix.retired_history_sentinel)
                finally:
                    nav.policy_log.close();nav.actual_log.close()

    def test_single_selected_NAV_option_preserves_completed_owner_and_declared_goal(self):
        runtime, native, prefix = self.fixture()
        params = tuple(sorted(dict(goal_world_x_m=-.08, goal_world_y_m=-2., surface_height_m=0.).items()))
        choice = BehaviorOption('nav-b', 'NAV', 'seen-B', params, .5, 'protected-complete.json')
        before = world_snapshot(runtime)
        with tempfile.TemporaryDirectory() as root, \
             patch('mujoco_zyh.resume_nav.compact_contract', return_value={}):
            session = compact_nav_session(runtime, choice, completed_prefix=prefix,
                root=Path(root), extra_guards=lambda: None)
            try:
                session.enter()
                self.assertEqual(len(session.machine.tasks), 1)
                self.assertEqual(session.machine.tasks[0]['goal'], [-.08, -2.])
                self.assertIs(session.reused_completed_prefix, prefix)
                self.assertFalse(session.machine.complete)
                self.assertEqual(before, world_snapshot(runtime))
            finally:
                session.resume_nav.policy_log.close();session.resume_nav.actual_log.close()


if __name__ == '__main__':
    unittest.main()
