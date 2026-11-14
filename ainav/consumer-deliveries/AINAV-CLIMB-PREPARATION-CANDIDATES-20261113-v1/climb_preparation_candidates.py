"""Finite PUBLIC CLIMB preparation goals; opt-in caller delta, not admission.

Only an already selected CLIMB's NAV-child goal changes. Original semantic
intent, task placement, original CLIMB READY/entry, target references and stop
remain unchanged. No Runtime construction/step, actor, world, queue, goal-array,
PUSH/exit-policy or training API. New actual owner qualification is required.
"""
from dataclasses import asdict, dataclass
from copy import deepcopy
import hashlib
import math
from pathlib import Path

CALLBACK = '_ainav_selected_climb_prepare_goal'
SOURCE_SHA = '22a10aad8c59cc79fb209ec5c6ce58f5cfd946bff1162762301834159e0f8fd9'
SOURCE_PATH = 'ainav/native/execution_judged_course.py'
ANCHOR = "        ref=PublicReference(intent.target_ref,tuple(spec.approach_xy),spec.source_height_m,'selected-skill-private-entry-reference')"
REPLACEMENT = """        _prepare_goal_xy = tuple(spec.approach_xy)
        _prepare_goal_callback = globals().get('_ainav_selected_climb_prepare_goal')
        if _prepare_goal_callback is not None:
            _prepare_goal_xy = _prepare_goal_callback(self, intent, spec, now)
        ref=PublicReference(intent.target_ref,_prepare_goal_xy,spec.source_height_m,'selected-skill-private-entry-reference')"""
OFFSETS = (('original', 0.), ('lateral_plus_0p04', .04), ('lateral_minus_0p04', -.04))


def need(ok, message):
    if not ok:
        raise ValueError(message)


def xy(value):
    need(type(value) in (list, tuple) and len(value) == 2
         and all(type(v) in (int, float) and math.isfinite(v) for v in value), 'finite public declared XY')
    return tuple(float(v) for v in value)


def transform_source(original):
    need(hashlib.sha256(original.encode()).hexdigest() == SOURCE_SHA, 'exact selected original caller required')
    need(original.count(ANCHOR) == 1 and CALLBACK not in original, 'single original caller; no stacking')
    return original.replace(ANCHOR, REPLACEMENT, 1)


def restore_source(changed):
    need(changed.count(REPLACEMENT) == 1, 'one exact preparation caller delta')
    original = changed.replace(REPLACEMENT, ANCHOR, 1)
    need(hashlib.sha256(original.encode()).hexdigest() == SOURCE_SHA, 'delta must invert to original caller')
    return original


@dataclass(frozen=True)
class PreparationSelection:
    target_ref: str
    candidate_id: str
    def __post_init__(self):
        need(type(self.target_ref) is str and 0 < len(self.target_ref) <= 160, 'explicit selected public target')
        need(type(self.candidate_id) is str and self.candidate_id in dict(OFFSETS), 'one of three finite candidates, not a float control domain')



def selection_from_payload(payload):
    need(type(payload) is dict and set(payload) == {'schema', 'target_ref', 'candidate_id'}
         and payload['schema'] == 'AINav-finite-CLIMB-preparation-selection-v1',
         'exact preparation selection payload; no task/physics/goal overrides')
    return PreparationSelection(payload['target_ref'], payload['candidate_id'])


def public_candidates(*, target_ref, declared_approach_xy, source_surface_height_m, registered_climb):
    """Public static map only. No state, measured target pose or future effects.

    This first implementation is ground-source CLIMB preparation only. Nominal
    offsets are inside the ORIGINAL .16m disk, not a real READY/safety proof.
    """
    PreparationSelection(target_ref, 'original')
    center = xy(declared_approach_xy)
    need(type(source_surface_height_m) in (int, float) and source_surface_height_m == 0., 'ground-source study only')
    need(registered_climb is True, 'declared registered CLIMB reference required')
    return tuple(dict(candidate_id=name, target_ref=target_ref,
                      original_approach_xy=list(center), NAV_goal_xy=[center[0], center[1]+offset],
                      source_surface_height_m=0., lateral_offset_m=offset,
                      information_source='PUBLIC_REGISTERED_TASK_REFERENCE_ONLY',
                      original_CLIMB_READY_goal_unchanged=True,
                      actual_native_admission_or_motor_difference_proven=False,
                      predicted_current_cost_s=None, predicted_complete_successor_cost_s=None,
                      physical_execution_authorized=False)
                 for name, offset in OFFSETS)


def _owner_key(host):
    ex = host.executor
    return (id(host.r), id(host.factory), id(host.factory.references), id(ex),
            id(ex.runtime), id(ex.session), id(ex.option), ex.reported_end,
            id(host.coordinator.intent), ex.fatal)


def bind_to_host(host, caller_module, *, selection=None, enabled=False, emit=None):
    """Install once BEFORE execution in a NEW owned transformed source module.

    Disabled reads no host/module. Enabled selection is immutable and explicit;
    original candidate is a true common-code zero-offset baseline. This is not
    a permit or an optimizer and never uses private pose/outcome to choose.
    """
    need(type(enabled) is bool, 'explicit Boolean experimental arm')
    if not enabled:
        return dict(status='DEFAULT_OFF_NO_INSTALL_OR_REPLACEMENT', installed=False)
    need(type(selection) is PreparationSelection and callable(emit), 'immutable declared selection and evidence sink')
    ns = vars(caller_module)
    restore_source(Path(ns['__file__']).read_text())
    cls = ns['ExecutionJudgedFullCourse']
    need(type(host) is cls and cls._native_nav.__globals__ is ns and CALLBACK in cls._native_nav.__code__.co_consts,
         'exact transformed caller class/namespace')
    need(CALLBACK not in ns, 'no callback replacement or stacking')
    need(host.tick == 0 and float(host.r.sim.data.time) == 0. and host.r.step_count == 0
         and host.executor.session is None and host.executor.option is None
         and host.coordinator.intent is None, 'fresh constructed host before any prefix/skill; no hot install')
    public_ref = host.refs_by_id[selection.target_ref]
    catalogue = public_candidates(target_ref=public_ref.ref, declared_approach_xy=public_ref.xy,
                                  source_surface_height_m=public_ref.surface_height_m,
                                  registered_climb=bool(public_ref.climb_surface))
    candidate = next(c for c in catalogue if c['candidate_id'] == selection.candidate_id)
    selected_goal_xy = tuple(candidate['NAV_goal_xy'])
    frozen_ref = public_ref

    def selected_goal(current, intent, spec, now):
        # Original PUSH preparation and all other targets keep exact old code.
        if intent.skill != 'CLIMB' or intent.target_ref != selection.target_ref:
            return tuple(spec.approach_xy)
        need(current is host and host.refs_by_id[intent.target_ref] is frozen_ref, 'same current host and immutable public reference')
        ex = host.executor
        need(host.r is ex.runtime and host.factory.runtime is host.r and ex.factory is host.factory
             and host.coordinator.intent is intent and ex.fatal is False,
             'exact root/executor/factory/current semantic owner')
        need(ex.option is None or ex.reported_end is True, 'no active native owner/goal replacement')
        if ex.session is not None:
            # The previous PUSH machine can own proxy.sim=TargetBridge. Do not
            # collapse it into the root Runtime or poll NN/outcome properties.
            need(ex.session.runtime is host.r, 'previous actual session has the SAME root Runtime')
        need(float(host.r.sim.data.time) == now and spec.skill == 'CLIMB'
             and spec.target_ref == intent.target_ref and spec.source_height_m == 0.
             and tuple(spec.approach_xy) == tuple(frozen_ref.xy), 'original CLIMB spec/public source/clock retained')
        before = (host.api.world_snapshot(host.r), _owner_key(host))
        goal = selected_goal_xy
        emit(dict(event='ainav_selected_CLIMB_preparation_NAV_goal_proposed',
                  time_s=now, boundary_runtime_step_count=getattr(host.r, 'step_count', None),
                  intent_sha256=intent.sha256, selection=asdict(selection),
                  original_CLIMB_approach_xy=list(frozen_ref.xy), NAV_goal_xy=list(goal),
                  source_surface_height_m=0., original_task_goal_changed=False,
                  selection_source='EXPLICIT_PUBLIC_PREPARATION_PLAN_NOT_MODEL',
                  original_READY_and_native_entry_still_required=True,
                  actual_native_admission_claimed=False, model_input=False,
                  physical_commands_issued_by_selector=0))
        need((host.api.world_snapshot(host.r), _owner_key(host)) == before,
             'evidence sink changed world/FIFO/semantic owner; do not restore or issue')
        return goal

    ns[CALLBACK] = selected_goal
    return dict(status='INSTALLED_NEW_SOFTWARE_CANDIDATE_NOT_PHYSICAL_QUALIFICATION', installed=True,
                selection=asdict(selection), public_candidate=deepcopy(candidate),
                current_task_intent_and_original_READY_goal_unchanged=True,
                original_native_controller_and_guards_unchanged=True,
                execution_authorized=False)
