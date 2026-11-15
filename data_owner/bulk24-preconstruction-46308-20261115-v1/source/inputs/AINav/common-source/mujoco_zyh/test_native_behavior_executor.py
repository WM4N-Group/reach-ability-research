"""CPU handoff/command provenance tests; fixtures never step MuJoCo."""
import os
from dataclasses import replace
from types import SimpleNamespace as NS
import unittest
import numpy as np
from mujoco_zyh.behavior_authority import BehaviorOption
from mujoco_zyh.native_behavior_executor import (NativeOptionExecutor, NativeOptionSession,
    array_sha, world_snapshot, compile_option_push_machine)


def option(skill='NAV', token='choice', **kw):
    return BehaviorOption(token, skill, 'seen-target', (), .02, 'entry.json', **kw)


class Command:
    def __init__(self):
        self.position = np.zeros(18)
        self.value = np.zeros((5, 18))
    def array(self):
        return self.value.copy()


class Machine:
    def __init__(self, runtime):
        self.r = runtime
        self.tasks = [dict(skill='nav')]
        self.complete = False
        self.finish = None
        self.enters = 0
        self.updates = 0
        self.guards = 0
    def enter(self):
        self.enters += 1
    def update(self):
        self.updates += 1
    def next_command(self):
        return self.r.last
    def after_step(self):
        self.guards += 1


class Exit:
    def __init__(self):
        self.complete = False
        self.guards = 0
    def update(self):
        pass
    def command(self):
        return Command()
    def after_step(self):
        self.guards += 1


class NativeBehaviorTests(unittest.TestCase):
    def fixture(self, push=False):
        sim = NS(data=NS(time=0., qpos=np.zeros(25), qvel=np.zeros(24)), queue=[])
        runtime = NS(sim=sim, last=Command())
        made = []
        def factory(opt):
            m = Machine(runtime)
            session = NativeOptionSession(runtime, m, make_exit=lambda refs: Exit())
            made.append(session)
            return session
        log = []
        executor = NativeOptionExecutor(runtime, factory, log.append)
        opt = option('PUSH', attempt_id='p0', original_push_goal_sha256='c'*64) if push else option()
        return runtime, executor, made, opt, log

    def issued(self, runtime, executor, tick):
        runtime.sim.data.time = tick*.005  # fixture clock only; no engine/physics imported
        executor.record_issued(runtime.last.array(), tick, tick*.005, f'actual-command:{tick}')

    def expire(self, r, ex):
        for tick in range(1, 6):
            self.issued(r, ex, tick)
        return ex.receipts()

    def test_admission_and_first_actual_command_have_distinct_receipts(self):
        r, ex, made, opt, log = self.fixture()
        before = world_snapshot(r)
        receipt = ex.start(opt, 'd0', 0.)
        self.assertEqual(receipt.status, 'admitted')
        self.assertEqual(ex.receipts(), [])
        self.assertIsNone(ex.first_command_time)
        self.assertFalse(log[0]['physical_command_already_issued'])
        self.assertEqual(before, world_snapshot(r))
        self.issued(r, ex, 1)
        self.assertEqual([r.status for r in ex.receipts()], ['started'])
        self.assertEqual(made[0].machine.guards, 1)

    def test_planned_or_skipped_command_cannot_claim_actual_dispatch(self):
        r, ex, _, opt, _ = self.fixture()
        ex.start(opt, 'd0', 0.)
        bad = r.last.array();bad[0, 0] = 1.
        r.sim.data.time = .005
        with self.assertRaises(ValueError):
            ex.record_issued(bad, 1, .005, 'planned-only')
        self.assertIsNone(ex.first_command_time)
        self.issued(r, ex, 1)
        r.sim.data.time = .015
        with self.assertRaises(ValueError):
            ex.record_issued(r.last.array(), 3, .015, 'missing-tick')

    def test_budget_requires_new_choice_without_advancing_skill(self):
        r, ex, made, opt, _ = self.fixture()
        ex.start(opt, 'd0', 0.)
        rows = self.expire(r, ex)
        self.assertEqual([x.status for x in rows], ['started', 'budget_expired'])
        self.assertFalse(made[0].machine.complete)
        self.assertEqual(made[0].machine.enters, 1)
        with self.assertRaises(RuntimeError):
            ex.next_command()
        ex.start(replace(opt, token='continued'), 'd1', .025)
        self.assertEqual(len(made), 1)
        self.assertEqual(made[0].machine.enters, 1)

    def test_budget_does_not_allow_switching_a_running_controller(self):
        r, ex, _, opt, _ = self.fixture()
        ex.start(opt, 'd0', 0.)
        self.expire(r, ex)
        with self.assertRaises(RuntimeError):
            ex.start(option('CLIMB'), 'd1', .025)

    def test_running_push_can_only_continue_with_same_goal_and_parameters(self):
        r, ex, made, opt, _ = self.fixture(push=True)
        ex.start(opt, 'd0', 0.)
        self.expire(r, ex)
        changed = replace(opt, token='bad', parameters=(('push_distance_m', .4),))
        with self.assertRaises(RuntimeError):
            ex.start(changed, 'd1', .025)
        ex.start(replace(opt, token='same'), 'd1', .025)
        self.assertEqual(len(made), 1)

    def test_protected_exit_keeps_world_queue_and_old_machine(self):
        r, ex, made, opt, _ = self.fixture(push=True)
        ex.start(opt, 'd0', 0.)
        self.expire(r, ex)
        before = world_snapshot(r)
        exit_opt = replace(opt, skill='EXIT_PUSH', token='exit')
        ex.start(exit_opt, 'd1', .025)
        self.assertEqual(before, world_snapshot(r))
        self.assertEqual(len(made), 1)
        self.assertIs(ex.session, made[0])
        self.issued(r, ex, 6)
        ex.receipts()
        made[0].exit.complete = True
        ex.update()
        self.assertEqual(ex.receipts()[0].status, 'protected_exit_complete')
        with self.assertRaises(RuntimeError):
            ex.start(opt, 'd2', .03)

    def test_failed_owner_cannot_be_bypassed_with_a_fresh_task(self):
        r, ex, made, opt, _ = self.fixture(push=True)
        ex.start(opt, 'd0', 0.)
        self.issued(r, ex, 1);ex.receipts()
        made[0].failure = 'original-contact-progress-failure'
        ex.update();ex.receipts()
        with self.assertRaises(RuntimeError):
            ex.start(option(), 'd1', .005)

    def test_hard_guard_failure_revokes_authority_even_if_native_completed(self):
        r, ex, made, opt, _ = self.fixture()
        ex.start(opt, 'd0', 0.)
        made[0].machine.complete = True
        def guard():
            raise RuntimeError('original-collision-guard')
        made[0].check_guards = guard
        with self.assertRaises(RuntimeError):
            ex.update()
        self.assertEqual(ex.receipts()[0].status, 'hard_stop')
        with self.assertRaises(RuntimeError):
            ex.start(option('CLIMB'), 'd1', 0.)

    def test_original_goal_mutation_blocks_any_further_native_commands(self):
        r, _, _, _, _ = self.fixture()
        target = np.array([[1.7, 0, .1]])
        session = NativeOptionSession(r, Machine(r), original_goal=lambda: target)
        session.enter();target[0, 0] = 1.8
        with self.assertRaises(RuntimeError):
            session.command()

    def test_multitask_native_machine_is_rejected(self):
        r, _, _, _, _ = self.fixture()
        machine = Machine(r);machine.tasks *= 2
        with self.assertRaises(ValueError):
            NativeOptionSession(r, machine)

    def test_entry_world_mutation_is_detected_without_rollback_writes(self):
        r, _, _, _, _ = self.fixture()
        machine = Machine(r)
        machine.enter = lambda: r.sim.queue.append(np.zeros((5, 18)))
        session = NativeOptionSession(r, machine)
        with self.assertRaises(RuntimeError):
            session.enter()

    def test_native_finish_cannot_be_replaced_by_another_exit(self):
        r, _, _, _, _ = self.fixture()
        machine = Machine(r);machine.finish = object()
        session = NativeOptionSession(r, machine, make_exit=lambda refs: Exit())
        session.enter()
        with self.assertRaises(RuntimeError):
            session.request_exit()

    @unittest.skipUnless(os.environ.get('ZYH_BUNDLE'), 'Formal pinned native source required')
    def test_pinned_native_entry_adapters_restore_exact_source(self):
        import sys
        from pathlib import Path
        sys.path.insert(0, str(Path(os.environ['ZYH_BUNDLE']) / 'switch'))
        for height in (0., .4):
            for compact in (False, True):
                cls, receipt = compile_option_push_machine(os.environ['ZYH_BUNDLE'],
                    approach_xy=[.1, -2.], surface_height_m=height, compact_arm=compact)
                self.assertTrue(receipt['inverse_restores_exact_original'])
                self.assertFalse(receipt['task_success_or_next_skill_added'])
                self.assertEqual(receipt['physics_steps'], 0)
                self.assertTrue(callable(cls))


if __name__ == '__main__':
    unittest.main()
