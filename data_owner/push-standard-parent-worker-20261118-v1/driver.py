"""One preregistered engineering NAV→PUSH case on ORIGINAL registered loop.

Not a planner/optimizer, L0, V4 comparison, launcher or retry. No Runtime/Actor/
physics on import/class assembly. Existing guards/writer/stow are borrowed by
exact method pins; the legacy scene constructor/catalogue is NEVER inherited.
"""
import ast
import hashlib
import importlib
from pathlib import Path
import sys

from standard_runtime import need
from registered_trace import connect_after_capture

METHOD_PINS = {'_install_common_stow': 'e658b891f50ce0b30a4500f415942159190903e7297a690336d1892323ef236a', '_snapshot': 'a695a003d85ec195dd87226b291889eebed78f751d85d2fc87c53ee2f4e12d19', '_write_command': '59f7da9d8882a339bcbb5164fe45d0f74f06d7b58e8c56ed1156dd92207444db', '_write_boundary': '3e4b7704343401ed90cd3263119d48383110a077eb1a0a39b84e106518208d50', '_native_guards': 'e6e848ce969ed0a94f4ccf52310a542fc8c4ff326c1a8a4607c415b7838b070f', '_after_guard': '364652496c9da858cd6bc109c03985fee40521115b97ecd3dd34093b46278904'}
NAV_GOAL = (-.02, 0.)
PUSH_APPROACH = (-.08, 0.)  # ORIGINAL PushEntry, not the NAV goal.


class FixedStandardCase:
    """Two declared singletons; never guesses a success or adds a prepare NAV."""
    def __init__(self, journal):
        self.journal = journal
        self.index = 0
        self.selected = None
        self.receipts = []
        self.failed = False

    @property
    def active_skill(self):
        return None if self.selected is None else self.selected.skill

    def select(self, batch):
        from ainav.planner import Selection
        need(not self.failed and self.index < 2 and self.selected is None and len(batch.options) == 1,
             'Exactly one current preregistered option, no retry/successor search')
        option = batch.options[0]
        need(option.skill == ('NAV', 'PUSH')[self.index], 'Original natural predecessor order')
        self.selected = option
        ref = self.journal(dict(event='standard_L1_fixed_case_selected_NOT_optimizer',
            query_sha256=batch.sha256, option_sha256=option.sha256, root_skill=option.skill,
            sequence_index=self.index, source='original switch/plans.py:nav-push'))
        return Selection(batch.sha256, option.token, option.sha256,
                         'SDK_STANDARD_FIXED_CASE', self.index, ref)

    def observe(self, option, receipt):
        from dataclasses import asdict
        need(option is self.selected and receipt.option_sha256 == option.sha256,
             'Exact original selected option/terminal receipt')
        self.receipts.append(dict(root_skill=option.skill, **asdict(receipt)))
        if receipt.status != 'succeeded':
            self.failed = True
            raise RuntimeError('Original native interval did not succeed; no continuation/retry')
        self.index += 1
        self.selected = None


def _borrow(base_dir):
    path = Path(base_dir).resolve(strict=True)/'scene_driver.py'
    need(not path.is_symlink(), 'No redirected original source')
    text = path.read_text()
    cls = next(n for n in ast.parse(text).body if isinstance(n, ast.ClassDef) and n.name == 'ComplexSceneDriver')
    functions = {n.name: ast.get_source_segment(text, n) for n in cls.body if isinstance(n, ast.FunctionDef)}
    for name, pin in METHOD_PINS.items():
        need(hashlib.sha256(functions[name].encode()).hexdigest() == pin, 'Original method ' + name)
    sys.path.insert(0, str(path.parent))
    spec = importlib.util.find_spec('scene_driver')
    need(spec is not None and Path(spec.origin).resolve() == path, 'No ambient original method source')
    module = importlib.import_module('scene_driver')
    need(Path(module.__file__).resolve() == path, 'No cached foreign source')
    return {name: getattr(module.ComplexSceneDriver, name) for name in METHOD_PINS}


def driver_class(*, source_root=None, legacy_base_dir=None, legacy_guard_dir=None, enabled=False):
    need(type(enabled) is bool, 'Explicit new parent source assembly')
    if not enabled:
        return None
    root = Path(source_root).resolve(strict=True)
    methods = _borrow(legacy_base_dir)
    guard_dir = Path(legacy_guard_dir).resolve(strict=True)
    sys.path.insert(0, str(guard_dir))
    parallel = importlib.import_module('parallel_alias_guard')
    need(Path(parallel.__file__).resolve() == guard_dir/'parallel_alias_guard.py', 'Exact selected original alias guard')

    class StandardDriver:
        def __init__(self, components, *, bundle, output_root, writer, journal, guard, trace):
            from ainav.contracts import canonical
            from ainav.native.observation import AcquisitionPublisher
            from mujoco_zyh import native_behavior_executor as api
            import numpy as np
            need(callable(guard) and callable(journal) and guard() is not False, 'Actual parent authority/lease/watch')
            self.r = components['runtime']
            need(self.r.step_count == 0 and float(self.r.sim.data.time) == 0. and not self.r.sim.queue,
                 'Fresh task0 only')
            self.components, self.registry = components, components['registry']
            self.capture, self.observer = components['capture'], components['observer']
            self.source_root, self.bundle = root, bundle
            self.root, self.writer, self.journal, self.owner_guard = Path(output_root), writer, journal, guard
            self.api, self.np, self.trace = api, np, trace
            self.planner = FixedStandardCase(journal)
            self.tick = self.sequence = 0
            self.loop = self.executor = self.factory = self.execution = None
            self.complete = False
            self.prefix = self.capture
            self._last_issued, self._before = self.r.last.position.copy(), None
            self.last_capture_tick = None
            p = self.r.sim
            self._world = (p, p.model, p.data, p.queue, p.controller, p.box_push_target)
            self.publisher = AcquisitionPublisher(self.root/'query-observations')
            self.scene = dict(task=dict(instruction='Original standard NAV[-.02,0] then one uncompensated +X PUSH .6m to [1.7,0], original full exit'))
            self.capabilities = canonical(dict(source_ref='Original SDK nav-push single finite L1 screening, not task-optimization method',
                skills=['NAV', 'PUSH'], constraints=['One original fixed NAV followed by one original ground PUSH; no retry/extra NAV.',
                'Original entry/support/contact/12N/immutable goal/FF/PD/FIFO/native settled and complete protected STOW are mandatory.',
                'Public20mm and10mm measurement-plane gap are separate from native confirmation; no wall/terrain added.']))
            self._install_common_stow()
            self.owner_guard()

        def actor_context(self):
            skill = self.planner.active_skill
            session = None if self.executor is None else self.executor.session
            option = None if self.executor is None else self.executor.option
            phase = 'ADMISSION' if skill is not None else self.capture.phase
            if session is not None and option is not None and option.skill == skill:
                phase = str(session.machine.phase)
            return dict(root_skill=skill or 'INITIAL_CAPTURE', native_phase=phase,
                        task_step=self.r.step_count, task_sim_s=float(self.r.sim.data.time))

        def capture_grid(self):
            if self.tick % 20 == 0 and self.last_capture_tick != self.tick:
                packet, private = self.observer.capture(self.tick//4, self._last_issued)
                # Existing PrivateCatalogBoundaryWriter adds ONLY no-model annotation.
                self.writer.append_visual(packet, control_tick=self.tick//4, private_catalog=private)
                self.last_capture_tick = self.tick

        def close_metadata_workers(self):
            type(self)._native_guards.engine.close()

        def _contact_guard(self):
            if self.execution is not None:
                self.execution['guards']()
            else:
                from ainav.native.registered_guards import check_object_contacts
                check_object_contacts(self.r, self.registry)

        def _connect_execution(self):
            from ainav.native.loop import AinavLoop
            self.execution = connect_after_capture(self.components, source_root=root, bundle=self.bundle,
                guard=self.owner_guard, journal=self.journal, trace=self.trace, enabled=True)
            self.factory, self.executor = self.execution['factory'], self.execution['executor']
            self.loop = AinavLoop(runtime=self.r, executor=self.executor, planner=self.planner,
                batch_provider=self.judge_intent, snapshot=self._snapshot,
                command_writer=self._write_command, after_step_guard=self._after_guard,
                journal=self.journal, physical_tick=self.tick)

        def judge_intent(self, now):
            """One current PUBLIC batch; original private entry gates still own admission."""
            from ainav.contracts import DecisionBatch, sha
            from ainav.native.behavior_authority import BehaviorOption
            from ainav.native.execution_judge import EntrySpec, EntryState, judge_entry
            from ainav.native.push_support_gate import current_push_source_support
            from ainav.native.registered_compact_nav import validate_support_and_goal
            self._native_guards();self._contact_guard()
            need(now == float(self.r.sim.data.time) and self.planner.index in (0, 1), 'Current finite actual query')
            packet, _private = self.observer.capture(self.tick//4, self._last_issued)
            resolver = self.execution['resolver']
            descriptors = resolver.observe(packet, control_tick=self.tick//4, physical_tick=self.tick)
            obs = self.publisher.publish(packet, now=now, descriptors=descriptors,
                declared_map=dict(source_ref='Original source nav-push fixed declaration, not live GT',
                    anchors=[dict(target_ref='standard-nav-goal', position_xyz_m=[*NAV_GOAL, 0.],
                                  uncertainty_xyz_m=[0., 0., 0.], description='Original task-given NAV target')]),
                goal=self.scene['task']['instruction'], events=[])
            self.sequence += 1
            if self.planner.index == 0:
                ref = self.journal(dict(event='standard_NAV_public_fixed_goal', time_s=now,
                    current_observation_sha256=obs.sha256, no_arrival_or_Actor_call_claimed=True))
                option = BehaviorOption('standard-NAV', 'NAV', 'standard-nav-goal',
                    tuple(sorted(dict(goal_world_x_m=NAV_GOAL[0], goal_world_y_m=NAV_GOAL[1], surface_height_m=0.).items())), 60., ref)
            else:
                visible = [d['target_ref'] for d in descriptors if resolver._observed[d['target_ref']][0] == 'push_box']
                need(len(visible) == 1, 'Current original RGBD association required; no GT/old-ref fallback')
                p = self.r.sim
                witness = self.factory._current_completed_witness();witness.validate(self.r)
                surface = self.registry.surfaces[witness.support_ref]
                current_push_source_support(self.r, self.registry, 'push_box', 0.)
                validate_support_and_goal(surface, p.data.xpos[p.feet_ids].tolist(), p.forces[p.feet_ids, 2].tolist(), PUSH_APPROACH)
                rotation = p.data.xmat[p.base_id].reshape(3, 3)
                orientation = bool(self.np.allclose(p.data.xmat[p.box_id].reshape(3, 3), self.np.eye(3), rtol=0, atol=.08))
                state = EntryState(now, sha(self.api.world_snapshot(self.r)), tuple(map(float, p.data.qpos[:2])),
                    float(self.np.arctan2(rotation[1,0], rotation[0,0])), True, True, bool(self.executor.fatal))
                judgment = judge_entry(EntrySpec('PUSH', visible[0], PUSH_APPROACH, 0., True, orientation), state)
                ref = self.journal(dict(event='standard_PUSH_original_entry_judgment', **judgment.private_record()))
                need(judgment.status == 'READY', 'Original PUSH entry not ready; no extra prepare NAV or Actor-failure inference')
                contract = self.components['placement_contract']
                goal = resolver.prepare_push(visible[0], distance_m=.6, attempt_id='standard-single-PUSH',
                    approach_xy=PUSH_APPROACH, surface_height_m=0., goal_xy_m=contract.drive_goal_xy_m,
                    body_braking_goal_xy_m=contract.public_goal_xy_m)
                option = BehaviorOption('standard-PUSH', 'PUSH', visible[0], tuple(sorted(dict(
                    goal_world_x_m=PUSH_APPROACH[0], goal_world_y_m=PUSH_APPROACH[1],
                    surface_height_m=0., push_distance_m=.6).items())), 60., ref,
                    attempt_id='standard-single-PUSH', original_push_goal_sha256=goal)
            batch = DecisionBatch('standard-case-query-%d'%self.sequence, obs, (option,), self.capabilities)
            self.factory.bind_batch(batch)
            return batch

        def step_one(self):
            p = self.r.sim
            need(self.r.step_count == self.tick and abs(float(p.data.time)-self.tick*.005) < 1e-7,
                 'Original actual200Hz clock')
            self.capture_grid()
            self._before = (float(p.data.time), p.data.qpos[p.qids].copy(), p.data.qvel[p.dids].copy())
            if self.loop is None:
                if self.capture.complete:
                    self._connect_execution()
                    return False
                command = self.capture.command()
                issued, before = command.array().copy(), float(p.data.time)
                try:
                    self.r.step(command)
                finally:
                    if float(p.data.time) > before:
                        need(abs(float(p.data.time)-before-.005)<1e-7, 'Exactly one initial capture step')
                        self.tick += 1
                        try:
                            self._write_command(issued, self.tick, float(p.data.time))
                        finally:
                            try:self.capture.after_step()
                            finally:self._after_guard()
                return True
            self.loop._receipts()
            if self.planner.index == 2:
                need(self.executor.reported_end and self.executor.last_outcome == 'succeeded', 'Actual final PUSH receipt')
                self.complete = True
                return False
            try:
                return self.loop.step_one()
            finally:
                self.tick = self.loop.physical_tick

    for name, function in methods.items():
        if name != '_native_guards':setattr(StandardDriver, name, function)
    StandardDriver._native_guards = parallel.make_parallel_guard(methods['_native_guards'], enabled=True)
    StandardDriver.source_receipt = dict(original_method_SHA256=METHOD_PINS,
        legacy_constructor_catalogue_or_task_terminal_not_inherited=True, task_success_not_qualified=True)
    return StandardDriver


class CaseLoopError(RuntimeError):
    def __init__(self, receipt, original_error):
        super().__init__('Original finite standard case stopped; no retry')
        self.receipt = receipt
        self.original_error = original_error


def run_case(driver=None, *, watch=None, budget=None, video=None,
             scope_start_mono=None, enabled=False):
    """Finite task-only loop; real completion, failure and resource censor separate."""
    import time
    from standard_runtime import bounded_exception
    need(type(enabled) is bool, 'Explicit finite main')
    if not enabled:
        return None
    need(driver.r.step_count == 0 and float(driver.r.sim.data.time) == 0. and
         watch.state is budget.state, 'Fresh task and one original stop/IO state')
    calls, error, reason = 0, None, None
    start = time.monotonic()
    try:
        while True:
            watch()
            if driver.complete:
                reason = 'ORIGINAL_NAV_AND_PUSH_FULL_EXIT_SUCCEEDED';break
            if (driver.r.step_count >= 27000 or float(driver.r.sim.data.time) >= 135. or
                    calls >= 27300 or time.monotonic()-scope_start_mono >= 2400.):
                reason = 'PROSPECTIVE_FINITE_CAP_CENSORED';break
            before = driver.r.step_count
            calls += 1
            try:
                driver.step_one()
            finally:
                if driver.r.step_count > before:video.capture_if_due()
            need(driver.r.step_count-before in (0, 1), 'Exactly one original physical issue per call')
    except BaseException as exc:
        error = exc
        reason = 'ORIGINAL_SETUP_NATIVE_OR_RESOURCE_STOP_NOT_RETRIED'
    finally:
        if not budget.finalizing:budget.begin_finalization()
    executor = driver.executor
    receipt = dict(driver_calls=calls, stop_reason=reason, full_case_success=bool(driver.complete),
        root_terminal_receipts=list(driver.planner.receipts),
        original_error=None if error is None else bounded_exception(error),
        actual_original_executor_status=None if executor is None else dict(
            reported_end=executor.reported_end, last_outcome=executor.last_outcome,
            option_skill=None if executor.option is None else executor.option.skill),
        loop_wall_s=time.monotonic()-start, loop_wall_excludes_parent_cleanup_encoding=True,
        native_failure_label_not_invented=True, automatic_retry=False,
        scientific_SR_or_Actor_training_need_not_established=True,
        task_steps=driver.r.step_count, task_sim_s=float(driver.r.sim.data.time))
    if error is not None:raise CaseLoopError(receipt, error) from error
    return receipt
