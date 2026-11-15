"""V4 live observer/selected judge/original 200Hz loop, default-off component.

A Data-owned fresh worker supplies qualified components, recorder and method.
NO launcher, credential, second world, model/actor load or task-success shortcut.
Static deck/40cm and post-CLIMB dynamic NAV remain deliberately unadmitted;
therefore this component is NOT yet a complete five-arm main program.
"""
from pathlib import Path
from dataclasses import replace
import ast
import hashlib
import importlib
import math
import sys

from v4_native_asset import load_scene, require, SCENE_SHA256
from public_candidates import declarations, declared_map, capability_contract, intent_catalogue
from execution_entry import build_after_actual_capture
from native_entry import _exact_base
from factor_scope import install_legacy_common, factors
from climb_nav_source import read_actual_climb_nav_source

BASE_DIR = Path(__file__).resolve().parent.parent / 'complex_dual_route_v1'
# Only these unchanged methods are consumed. The inherited local tree contains
# unrelated postponed prefix edits; those constructors/catalogues are NOT used.
BASE_METHOD_PINS = {
    '_install_common_stow': 'e658b891f50ce0b30a4500f415942159190903e7297a690336d1892323ef236a',
    '_snapshot': 'a695a003d85ec195dd87226b291889eebed78f751d85d2fc87c53ee2f4e12d19',
    '_write_command': '59f7da9d8882a339bcbb5164fe45d0f74f06d7b58e8c56ed1156dd92207444db',
    '_write_boundary': '3e4b7704343401ed90cd3263119d48383110a077eb1a0a39b84e106518208d50',
    '_native_guards': 'e6e848ce969ed0a94f4ccf52310a542fc8c4ff326c1a8a4607c415b7838b070f',
    '_after_guard': '364652496c9da858cd6bc109c03985fee40521115b97ecd3dd34093b46278904',
    'capture_grid': '3a7a633a6f1b51aeb3b837a772dac14eacdfc3aaa59eb714395cbc77466da4e6',
}
COURSE_SHA = '4f95873e1b34b5778c28b18711e0461d18ab7f13d3e31b547f93b901e593a6fb'


def _original_methods():
    _exact_base()  # Exact unchanged complex_scene/native_construction/camera ABI.
    path = BASE_DIR / 'scene_driver.py'
    require(not path.is_symlink(), 'No redirected original writer/capture source')
    text = path.read_text()
    cls = next(n for n in ast.parse(text).body if isinstance(n, ast.ClassDef) and n.name == 'ComplexSceneDriver')
    functions = {n.name: ast.get_source_segment(text, n) for n in cls.body if isinstance(n, ast.FunctionDef)}
    for name, pin in BASE_METHOD_PINS.items():
        require(hashlib.sha256(functions[name].encode()).hexdigest() == pin,
                'Exact unchanged native writer/capture/stow method: ' + name)
    module = importlib.import_module('scene_driver')
    require(Path(module.__file__).resolve() == path, 'No ambient scene driver')
    # No inheritance/fallback to its obsolete constructor/catalogue/ground goal.
    return {name: getattr(module.ComplexSceneDriver, name) for name in BASE_METHOD_PINS}


def stream_private_catalog(catalog, *, control_tick, actual_time_s):
    """Project the original registered PRIVATE catalog to the stream boundary.

    RegisteredObserver emits model_input=False; the original EpisodeWriter
    additionally requires model_input_allowed=False. Preserve both prohibitions,
    all actual metadata and the current clock; never promote this data to models.
    """
    require(type(catalog) is dict and catalog.get('schema') == 'ainav-private-registered-object-catalog-v1'
            and catalog.get('model_input') is False,
            'Exact original registered private catalog, not public/model data')
    require(type(control_tick) is int and control_tick >= 0
            and type(catalog.get('control_tick')) is int and catalog['control_tick'] == control_tick
            and type(actual_time_s) in (int, float) and math.isfinite(actual_time_s)
            and type(catalog.get('time_s')) in (int, float) and math.isfinite(catalog['time_s'])
            and abs(catalog['time_s'] - actual_time_s) <= 1e-7
            and abs(actual_time_s - control_tick * .02) <= 1e-7,
            'Exact actual registered private catalog acquisition clock')
    require('model_input_allowed' not in catalog or catalog['model_input_allowed'] is False,
            'Conflicting private model-input permission is never silently overwritten')
    return dict(catalog, model_input_allowed=False)


def current_aliases(descriptors, resolver, public_body):
    """Project ONLY original accepted current RGBD associations, never old IDs."""
    aliases, objects = {}, []
    for descriptor in descriptors:
        body = resolver._observed[descriptor['target_ref']][0]
        public = [key for key, value in public_body.items() if value == body]
        require(len(public) == 1 and public[0] not in aliases, 'Current original one-to-one RGBD object association')
        aliases[public[0]] = descriptor['target_ref']
        objects.append(dict(target_ref=descriptor['target_ref'],
            label=public[0] + '; current original RGBD one-to-one association',
            bbox_xyxy=descriptor['descriptor']['pixel_bbox_xyxy'],
            evidence_ref='RGBD:' + descriptor['RGB_sha256']))
    return aliases, objects


def exact_declared_intent(scene, intent):
    matches = [row for row in declarations(scene) if row['skill'] == intent.skill
               and row['target_ref'] == intent.target_ref and row['parameters'] == dict(intent.parameters)]
    require(len(matches) == 1, 'Exact shared V4 public intent; no arbitrary goal/parameter injection')
    return matches[0]


def movable_climb_approach(geometry):
    """Shared caller uses original full-course B approach (front - 1.05).

    This is one fixed original engineering entry choice, not a new controllable
    standoff dimension, route witness or proof that the new task is feasible.
    The original 20cm/native-domain/current-support checks still apply.
    """
    return (float(geometry['front']) - 1.05, float(geometry['lane_y_m']))


def driver_class(*, source_root=None, enabled=False):
    require(type(enabled) is bool, 'Explicit owner opt-in')
    if not enabled:
        return None
    root = Path(source_root).resolve(strict=True)
    original, _ = _exact_base()
    original._source(root)
    course = root / 'mujoco_zyh/integrated_course.py'
    # This pin is the exact file containing the original B front-1.05 entry;
    # it does NOT establish40cm ability (HIGH was source .2 -> top .4).
    require(not course.is_symlink() and hashlib.sha256(course.read_bytes()).hexdigest() == COURSE_SHA,
            'Exact original fixed B-entry reference source')
    methods = _original_methods()

    class V4LiveDriver:
        task_terminal_source_integrated = True
        full_task_native_ready = False

        def __init__(self, components, *, bundle, output_root, writer, planner, journal, guard, arm):
            require(callable(guard) and callable(journal), 'Actual Data owner guard/journal')
            def checked_guard():
                require(guard() is not False, 'Original Data owner/resource guard refused')
            checked_guard()
            factors(arm)  # Reject an undeclared arm before any native import.
            import numpy as np
            from mujoco_zyh import native_behavior_executor as api
            from ainav.native.observation import AcquisitionPublisher
            require(components['scene_sha256'] == SCENE_SHA256 and components['scene'] == load_scene(),
                    'Exact confirmed shared V4 scene')
            self.r, self.scene = components['runtime'], components['scene']
            p = self.r.sim
            require(self.r.step_count == 0 and float(p.data.time) == 0. and not p.queue,
                    'Fresh zero-step worker only, not a resumed/closed root')
            require(callable(getattr(planner, 'select', None)) and callable(getattr(planner, 'observe_intent', None))
                    and callable(getattr(planner, 'reject_intent', None)), 'Actual public semantic method adapter required')
            self.components, self.registry = components, components['registry']
            self.capture, self.observer = components['capture'], components['observer']
            self.source_root, self.bundle = root, bundle
            self.root, self.writer = Path(output_root), writer
            self.planner, self.journal, self.owner_guard = planner, journal, checked_guard
            self.api, self.np = api, np
            self.tick = 0
            self.loop = self.executor = self.factory = self.coordinator = self.execution = None
            self.complete = False
            self.prefix = self.capture
            self._last_issued, self._before = self.r.last.position.copy(), None
            self.last_capture_tick = None
            self.sequence = self.execution_sequence = 0
            self._world = (p, p.model, p.data, p.queue, p.controller, p.box_push_target)
            self.public_body = {o['public_ref']: o['body_name'] for o in self.scene['objects']}
            self.publisher = AcquisitionPublisher(self.root / 'query-observations')
            self.current_observation, self.entity_by_public = None, {}
            self.capabilities = capability_contract()
            self.actual_climb_boundaries = []  # Private receipt/owner evidence only.
            self.actual_climb_nav_sources = []  # Necessary samples, never NAV admission.
            self.arm = arm
            install_legacy_common(self, arm=arm, planner=planner, journal=journal)
            self.owner_guard()

        def capture_grid(self):
            # Same original10Hz source/cadence, but RegisteredObserver's PRIVATE
            # schema needs its explicit no-model marker projected to the writer.
            if self.tick % 20 == 0 and self.last_capture_tick != self.tick:
                packet, private = self.observer.capture(self.tick // 4, self._last_issued)
                catalog = stream_private_catalog(private, control_tick=self.tick // 4,
                    actual_time_s=float(self.r.sim.data.time))
                self.writer.append_visual(packet, control_tick=self.tick // 4, private_catalog=catalog)
                self.last_capture_tick = self.tick

        def _contact_guard(self):
            if self.execution is not None:
                self.execution['guards']()
            else:
                from ainav.native.registered_guards import check_object_contacts
                check_object_contacts(self.r, self.registry)

        def _connect_execution(self):
            from ainav.native.intent_execution import IntentExecutionCoordinator
            from ainav.native.loop import AinavLoop
            self.execution = build_after_actual_capture(self.components, source_root=root, bundle=self.bundle,
                guard=self.owner_guard, journal=self.journal, enabled=True)
            self.factory, self.executor = self.execution['factory'], self.execution['executor']
            driver = self
            class CurrentCoordinator(IntentExecutionCoordinator):
                def observe(this, option, receipt):
                    if this.phase == 'interaction' and receipt.status == 'succeeded':
                        if option.skill == 'PUSH':
                            driver.execution['placements'].record_current(driver.executor, option, receipt)
                        elif option.skill == 'CLIMB':
                            witness = driver.factory._current_completed_witness()
                            witness.validate(driver.r)
                            driver.execution['climb_chain'].record_current(driver.executor, option, receipt, witness)
                            driver.actual_climb_boundaries.append((option, receipt, driver.executor.session, witness))
                            source = read_actual_climb_nav_source(runtime=driver.r, session=driver.executor.session,
                                executor=driver.executor, registry=driver.registry, native_witness=witness,
                                source_root=driver.source_root, guard=driver.owner_guard, journal=driver.journal, enabled=True)
                            driver.actual_climb_nav_sources.append(source)
                            driver.factory.register_climb_nav_source(source)
                            # NOT_READY only describes the next source; never rewrite
                            # this original succeeded CLIMB receipt as native failure.
                    return super().observe(option, receipt)
            self.coordinator = CurrentCoordinator(planner=self.planner, observe=self.observe_public,
                catalogue=self.intent_catalogue, judge=self.judge_intent, bind=self.factory.bind_batch,
                snapshot=lambda: self._snapshot(self.r), protection=lambda now: None,
                journal=self.journal, capability_contract=self.capabilities)
            self.loop = AinavLoop(runtime=self.r, executor=self.executor, planner=self.coordinator,
                batch_provider=self.coordinator, snapshot=self._snapshot, command_writer=self._write_command,
                after_step_guard=self._after_guard, journal=self.journal, physical_tick=self.tick)

        def observe_public(self, now):
            require(now == float(self.r.sim.data.time), 'Actual same-world observation clock')
            packet, _private = self.observer.capture(self.tick // 4, self._last_issued)
            descriptors = self.execution['resolver'].observe(packet, control_tick=self.tick // 4, physical_tick=self.tick)
            # Rebuilt every acquisition: [] on a new frame must discard old aliases.
            self.entity_by_public, objects = current_aliases(descriptors, self.execution['resolver'], self.public_body)
            obs = self.publisher.publish(packet, now=now, descriptors=objects,
                declared_map=declared_map(self.scene), goal=self.scene['task']['instruction'], events=[])
            self.sequence += 1
            (self.root / ('intent-observation-%04d.json' % self.sequence)).write_text(obs.encoded + '\n')
            self.current_observation = obs
            self.factory.begin_acquisition(obs)
            return obs

        def intent_catalogue(self, observation):
            require(observation is self.current_observation, 'Same actual public acquisition')
            return intent_catalogue(self.scene, observation, sequence=self.sequence)

        def _blocked(self, intent, now, reason):
            ref = self.journal(dict(event='V4_selected_intent_blocked', time_s=now,
                intent_sha256=intent.sha256, reason=reason, model_input=False))
            return 'BLOCKED', reason, ref

        def _selected_placement_ready(self, obj):
            row = self.execution['placements'].records.get(obj['public_ref'])
            if row is None or row['contract'].public_goal_xy_m != tuple(obj['required_goal_xy_m']):
                return False
            require(row['contract'].sha256 == row['contract_sha256'], 'Original placement contract changed')
            services = row['session'].machine.services
            services.assert_immutable()
            return bool(services.measure()['placement_geometry_verified'])

        def judge_intent(self, intent, now):
            from ainav.native.behavior_authority import BehaviorOption
            from ainav.native.execution_judge import EntrySpec, EntryState, judge_entry
            from ainav.native.push_support_gate import current_push_source_support
            from ainav.native.registered_compact_nav import validate_support_and_goal
            from ainav.native.scene_registry import RegisteredTerrain
            from ainav.native.registered_climb import check_climb_native_domain
            from ainav.contracts import sha
            self.execution_sequence += 1
            self._native_guards()
            self._contact_guard()
            require(now == float(self.r.sim.data.time), 'Actual current entry clock')
            params, p = dict(intent.parameters), self.r.sim
            try:
                exact_declared_intent(self.scene, intent)
                witness = self.factory.witness_for_skill(intent.skill)
                witness.validate(self.r)
                source_registry = self.factory.registry_for_witness(witness)
                require(witness.support_ref in source_registry.surfaces,
                        'Dynamic-box post-CLIMB source support/owner NAV bridge not yet admitted')
                surface = source_registry.surfaces[witness.support_ref]
                if intent.skill == 'NAV':
                    require(params['surface_height_m'] == surface.top_z_m, 'NAV cannot change actual source support layer')
                    if intent.target_ref == 'v4-goal-elevated':
                        self.execution['climb_chain'].verify()
                        require(self.execution['placements'].current_required(), 'Actual required placements before final NAV')
                    proof = self.journal(dict(event='V4_selected_NAV_entry_ready', time_s=now,
                        intent_sha256=intent.sha256, original_factory_support_checks_still_required=True, model_input=False))
                    return 'READY', BehaviorOption('v4-NAV-%d' % self.execution_sequence,
                        'NAV', intent.target_ref, intent.parameters, 60., proof), proof
                ref = intent.target_ref.removesuffix(':upper-entry') if intent.skill == 'CLIMB' else intent.target_ref
                require(ref in self.public_body, 'Static goal_deck CLIMB binding not admitted; no movable-body alias')
                visual = self.entity_by_public.get(ref)
                require(visual is not None, 'Current original RGBD association unavailable; no old alias/static-pose substitute')
                obj = next(o for o in self.scene['objects'] if o['public_ref'] == ref)
                body = self.public_body[ref]
                bid, gid = p.model.body(body).id, p.model.geom(body + '_geom').id
                orientation_ok = bool(self.np.allclose(p.data.xmat[bid].reshape(3, 3), self.np.eye(3), rtol=0, atol=.08))
                four = True
                if intent.skill == 'PUSH':
                    require(surface.top_z_m == params['surface_height_m'] == 0., 'Only original ground PUSH')
                    drive = params['goal_world_x_m'] + .11 - float(p.data.xpos[bid, 0])
                    require(0 < drive <= .8, 'Original native +X PUSH drive stroke only')
                    require(math.hypot(params['goal_world_x_m'] - float(p.data.xpos[bid, 0]),
                        params['goal_world_y_m'] - float(p.data.xpos[bid, 1])) >= .02, 'No redundant PUSH or fabricated goal receipt')
                    approach = (float(p.data.geom_xpos[gid, 0] - p.model.geom_size[gid, 0] - .58), float(p.data.geom_xpos[gid, 1]))
                    target_ready = True
                    try:
                        current_push_source_support(self.r, self.registry, body, 0.)
                    except ValueError:
                        four = False
                else:
                    geometry = RegisteredTerrain(self.registry).climb_geometry(p, ref, source_surface_height_m=surface.top_z_m)
                    require(abs(geometry['top'] - params['surface_height_m']) <= .01,
                            'Public CLIMB destination differs from actual original20cm target top')
                    approach = movable_climb_approach(geometry)
                    check_climb_native_domain(*approach, geometry)
                    target_ready = self._selected_placement_ready(obj)
                supported = True
                try:
                    validate_support_and_goal(surface, p.data.xpos[p.feet_ids].tolist(), p.forces[p.feet_ids, 2].tolist(), approach)
                except ValueError:
                    supported = False
                baseR = p.data.xmat[p.base_id].reshape(3, 3)
                state = EntryState(now, sha(self.api.world_snapshot(self.r)), tuple(map(float, p.data.qpos[:2])),
                    float(self.np.arctan2(baseR[1, 0], baseR[0, 0])), supported, four, bool(self.executor.fatal))
                judgment = judge_entry(EntrySpec(intent.skill, intent.target_ref, approach, surface.top_z_m,
                    target_ready, orientation_ok), state)
                proof = self.journal(dict(event='skill_execution_judgment', intent_sha256=intent.sha256,
                    judgment_sha256=judgment.sha256, **judgment.private_record()))
                if judgment.status == 'BLOCKED':
                    return self._blocked(intent, now, '; '.join(judgment.reasons))
                if judgment.status == 'PREPARE':
                    option = BehaviorOption('v4-entry-NAV-%d' % self.execution_sequence, 'NAV', intent.target_ref,
                        tuple(sorted(dict(goal_world_x_m=approach[0], goal_world_y_m=approach[1],
                            surface_height_m=surface.top_z_m).items())), 60., proof)
                    self.factory.prepare_private_entry_nav(option, judgment)
                    return 'PREPARE', option, proof
                if intent.skill == 'CLIMB':
                    outer = BehaviorOption('v4-CLIMB-%d' % self.execution_sequence, 'CLIMB', intent.target_ref,
                                           intent.parameters, 60., proof)
                    inner = replace(outer, token=outer.token + '-constructor', target_ref=visual)
                    self.factory.prepare_public_climb(outer, inner)
                else:
                    contract = next(c for c in self.execution['placement_catalogue'].values()
                        if c.target_ref == ref and c.public_goal_xy_m == (params['goal_world_x_m'], params['goal_world_y_m']))
                    attempt = 'v4-selected-push-%d' % self.execution_sequence
                    goal = self.execution['resolver'].prepare_push(visual, distance_m=drive, attempt_id=attempt,
                        approach_xy=approach, surface_height_m=0., goal_xy_m=contract.drive_goal_xy_m,
                        body_braking_goal_xy_m=contract.public_goal_xy_m)
                    outer = BehaviorOption('v4-PUSH-%d' % self.execution_sequence, 'PUSH', intent.target_ref,
                        intent.parameters, 60., proof, attempt_id=attempt, original_push_goal_sha256=goal)
                    inner = replace(outer, token=outer.token + '-constructor', target_ref=visual,
                        parameters=tuple(sorted(dict(push_distance_m=drive, surface_height_m=0.).items())))
                    self.factory.prepare_public_push(outer, inner, contract)
                return 'READY', outer, proof
            except (ValueError, KeyError) as error:
                return self._blocked(intent, now, type(error).__name__ + ': ' + str(error))

        def step_one(self):
            p = self.r.sim
            require(abs(float(p.data.time) - self.tick * .005) < 1e-7 and self.r.step_count == self.tick,
                    'Original actual200Hz tick/clock')
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
                        require(abs(float(p.data.time) - before - .005) < 1e-7, 'Exactly one original capture step')
                        self.tick += 1
                        try:
                            self._write_command(issued, self.tick, float(p.data.time))
                        finally:
                            try:
                                self.capture.after_step()
                            finally:
                                self._after_guard()
                return True
            self.loop._receipts()
            if self.executor.reported_end and self.executor.last_outcome == 'succeeded' and getattr(self.executor.session, '_v4_terminal_source', None) is not None:
                from task_terminal import collect_verified_terminal
                from rule_baseline import RuleBaseline
                proof = collect_verified_terminal(self.r, self.executor, self.execution['placements'],
                    self.execution['climb_chain'], guard=self.owner_guard)
                ref = self.journal(dict(event='V4_original_complete_task_verified', time_s=float(p.data.time),
                    original_required_placements=len(self.execution['placements'].records),
                    genuine_CLIMB_transitions=len(self.execution['climb_chain'].records),
                    actual_goal_deck_contact_and_contiguous_stop=True, model_input=False))
                if type(self.planner) is RuleBaseline:
                    self.planner.confirm_original_task_terminal(evidence_ref=ref, terminal_proof=proof)
                self.complete = True
                return False
            try:
                return self.loop.step_one()
            finally:
                self.tick = self.loop.physical_tick

    for name, function in methods.items():
        if name not in ('_install_common_stow', 'capture_grid'):  # Preserve explicit factor/privacy adapters.
            setattr(V4LiveDriver, name, function)
    V4LiveDriver.source_receipt = dict(original_helpers_reviewed_method_sha256=BASE_METHOD_PINS,
        original_helpers_borrowed=tuple(n for n in BASE_METHOD_PINS if n not in ('_install_common_stow', 'capture_grid')),
        registered_private_catalog_explicit_no_model_stream_boundary=True,
        legacy_common_stow_separate_from_new_successor_treatment=True,
        obsolete_base_constructor_catalogue_judge_and_ground_terminal_not_inherited=True,
        scene_source_sha256=SCENE_SHA256, actual_native_qualification=False,
        post_CLIMB_dynamic_NAV_static_deck40cm_and_full_terminal_not_admitted=True)
    return V4LiveDriver
