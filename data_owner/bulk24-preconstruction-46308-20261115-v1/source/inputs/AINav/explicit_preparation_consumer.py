AINAV_EXPLICIT_THREE_SOURCE_DELTA_PINS = {'mujoco_zyh/stall_stow.py': '38b12bae7f6aa718801655e1ed82e272adf2bc18d5d7acb4872efa739e199f8c', 'ainav/native/current_stall_stow.py': '38b12bae7f6aa718801655e1ed82e272adf2bc18d5d7acb4872efa739e199f8c', 'ainav/native/execution_judged_course.py': 'a49c9065eabec561c34606fb3b8a57afde25fbc7922c2a734f5e6009f9c351ac', 'probe_execution_judge.py': '133fd5933193f96dc2a6399d0f8305699519b3f758cd3c952528ac573a9dded5', 'mujoco_zyh/integrated_course_plan_v1.json': '515b4d7f6f781efbcebfd51cdf5ac932c47d4e76328fe58822ac8305a6c7a677'}
"""Compose the ORIGINAL absolute-placement host on Data's already-owned world.

No world constructor, Actor load, credential, resource acquisition or launcher.
The 283-file successful source is a READ-ONLY reference, never an old run to
resume. Data must freeze and qualify its NEW full integration/host/target scope.
"""
from copy import deepcopy
import hashlib
import importlib
import importlib.util
import json
from pathlib import Path
import sys
from types import SimpleNamespace

MANIFEST_SHA = '314b6650918cbf88c6bd7166ad3f2d26f9c3b30f92094db98d6f8832f8d1fd8c'
HISTORICAL_ROOT = '/workspace/project/ainav/experiments/ainav-full-execution-judged-5090-20261031-v2'


def need(value, message):
    if not value:
        raise ValueError(message)


def file_sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def verify_reference(source):
    root = Path(source).resolve()
    manifest_path = root/'ainav-source.json'
    need(file_sha(manifest_path) == MANIFEST_SHA, 'Exact selected successful reference manifest required')
    manifest = json.loads(manifest_path.read_text())
    need(len(manifest['files']) == 283 and manifest['world_model_required'] is False,
         'Complete original source, not a partial module transplant or WM runtime')
    for name, digest in manifest['files'].items():
        p = root/name
        need(not Path(name).is_absolute() and '..' not in Path(name).parts
             and not p.is_symlink() and p.resolve().is_relative_to(root)
             and p.is_file() and file_sha(p) == AINAV_EXPLICIT_THREE_SOURCE_DELTA_PINS.get(name, digest), 'Frozen source drift: '+name)
    from climb_preparation_candidates import restore_source
    from reach_stow_choice.native_stow_path_binding import restore_stall_source
    for name in AINAV_EXPLICIT_THREE_SOURCE_DELTA_PINS:
        text = (root/name).read_text()
        if name == 'mujoco_zyh/integrated_course_plan_v1.json':
            # Explicit fifth DATA/geometry delta ONLY in this new snapshot.
            # Keep original283 manifest as lineage; never rewrite its pins.
            original_plan = root.parent.parent/'ORIGINAL_integrated_course_plan_v1.json'
            need(file_sha(original_plan) == manifest['files'][name] == '3449b3744ff46c7d0c99237303eca96aca5b72edcda6873a33e287272f19c842', 'Exact original five-case plan backup')
            old_plan = json.loads(original_plan.read_bytes());new_plan = json.loads(text)
            matrix_path=root.parent.parent/'bulk-source/BULK_MATRIX.json'
            need(file_sha(matrix_path)=='84772f52501c9a216ab961e66f01eb4bfdef8353eb77a7e4001363ae0f6ee91c','Exact source-owned ten-case geometry matrix')
            matrix=json.loads(matrix_path.read_bytes())
            need(set(new_plan)==set(old_plan)|{'AINav_additive_source_note'}and new_plan['AINav_additive_source_note']=='Ten explicitly registered new lane/step-width geometries. Original five entries retained verbatim; original code, templates, guards, models and training_allowed flags unchanged. Not dispatch authority.'and {k:v for k,v in new_plan.items()if k not in ('cases','AINav_additive_source_note')}=={k:v for k,v in old_plan.items()if k!='cases'}and new_plan['cases']==old_plan['cases']+[g['source_case']for g in matrix['groups']], 'Only exact declared ten cases added; original five cases and all other fields identical')
            original=original_plan.read_text()
        elif name == 'probe_execution_judge.py':
            change = json.loads((root.parent.parent/'prefix-question/SOURCE_CHANGE_AND_INVERSE.json').read_bytes())
            need(text.count(change['new_fragment']) == 1, 'Exact bounded-three-request delta')
            original = text.replace(change['new_fragment'], change['old_fragment'])
        else:
            original = restore_source(text) if name == 'ainav/native/execution_judged_course.py' else restore_stall_source(text)
        need(hashlib.sha256(original.encode()).hexdigest() == manifest['files'][name],
             'Explicit source delta did not invert to frozen original: '+name)
    return root


def load_original_types(source):
    """Fresh-process import identity, no Runtime or host instance construction."""
    root = verify_reference(source)
    for name, module in tuple(sys.modules.items()):
        if name in ('ainav', 'mujoco_zyh') or name.startswith(('ainav.', 'mujoco_zyh.')):
            p = getattr(module, '__file__', None)
            need(p is not None and Path(p).resolve().is_relative_to(root),
                 'Mixed baseline import; use a fresh Data integration process, do not unload/alias modules')
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    host_module = importlib.import_module('ainav.native.execution_judged_course')
    name = '_ainav_original_API0_requested_planner_20261031_v6'
    if name not in sys.modules:
        spec = importlib.util.spec_from_file_location(name, root/'probe_execution_judge.py')
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        try:
            spec.loader.exec_module(module)
        except BaseException:
            del sys.modules[name]
            raise
    module = sys.modules[name]
    need(Path(module.__file__).resolve() == root/'probe_execution_judge.py', 'Original API0 planner source identity')
    return SimpleNamespace(Host=host_module.ExecutionJudgedFullCourse,
                           RequestedPlanner=module.RequestedIntentPlanner, source=root)


def make_api0_planner(*, source, requests, journal):
    types = load_original_types(source)
    # The original planner retains one pending semantic request through NAV
    # preparation and checks exact actual interaction/receipt identity. Copy the
    # external declaration so later caller mutation cannot rebind its target.
    return types.RequestedPlanner(deepcopy(requests), journal)


def compose_same_world_host(*, source, requests, runtime, native_a, observer,
                            writer, root, config, api, integrated, stall, journal):
    """Original full host + API0 planner; caller owns actual construction/permit.

    Does not infer ready, execute a prefix, call step, close resources or certify
    an execution scope. Old v4 B3 proof cannot qualify this different full host.
    """
    types = load_original_types(source)
    need(str(Path(root)) != HISTORICAL_ROOT, 'Never resume the historical experiment root')
    need(float(runtime.sim.data.time) == 0. and getattr(runtime, 'step_count', 0) == 0,
         'Fresh constructed main world only, not a recorded/resumed prefix')
    for module, relative in ((api, 'mujoco_zyh/native_behavior_executor.py'),
                             (integrated, 'mujoco_zyh/integrated_course.py'),
                             (stall, 'mujoco_zyh/stall_stow.py')):
        need(Path(module.__file__).resolve() == types.source/relative, 'One complete same-source native package')
    need(observer.r is runtime, 'Original observer must reference the SAME Runtime')
    planner = make_api0_planner(source=source, requests=requests, journal=journal)
    host = types.Host(runtime=runtime, native_a=native_a, observer=observer, writer=writer,
                      root=Path(root), config=config, api=api, integrated=integrated,
                      stall=stall, planner=planner, journal=journal)
    need(host.r is runtime and host.coordinator.model is planner, 'One world and one original semantic owner')
    return host, planner


def drive_same_world_api0(*, source, host, planner, max_calls, budget_and_lease, enabled=False):
    """Bounded scheduler around ORIGINAL host.step_one, never Runtime.step here.

    Data's qualified budget/lease callback is mandatory; enabled is only an
    accidental-call guard, NEVER physical authorization or a zero/main permit.
    No resources are closed here: Data keeps its original exception/teardown.
    """
    need(enabled is True, 'Default closed; new full-host technical/resource scope required')
    types = load_original_types(source)
    need(type(host) is types.Host and type(planner) is types.RequestedPlanner
         and host.coordinator.model is planner, 'Exact original same-world API0 host/owner')
    need(type(max_calls) is int and 0 < max_calls <= 84001 and callable(budget_and_lease),
         'Explicit finite caller cap and actual Data budget/lease callback required')
    need(not hasattr(host, '_ainav_api0_consumer_claimed'), 'No second driver/resume after error or cap')
    host._ainav_api0_consumer_claimed = True
    first_tick = host.tick
    for _ in range(max_calls):
        before = (host.api.world_snapshot(host.r), host.r.last.array().tobytes())
        try:
            budget_and_lease()
        finally:
            need((host.api.world_snapshot(host.r), host.r.last.array().tobytes()) == before,
                 'Budget/lease observer must not change clock/state/FIFO/last command')
        host.step_one()  # original prefix, single drain, 200Hz issue, original guards/writer
        if host.loop is not None:
            host.record_footprints()
            if planner.complete:
                host.monitor.check_a()
                return dict(status='ORIGINAL_REQUESTED_INTERACTIONS_COMPLETED',
                            observed_physical_steps=host.tick-first_tick, engineering_only=True,
                            full_task_success_inferred=False, next_skill_ready_inferred=False,
                            automatic_retry=False)
    return dict(status='CALLER_CAP_CENSORED', observed_physical_steps=host.tick-first_tick,
                engineering_only=True, full_task_success_inferred=False,
                next_skill_ready_inferred=False, automatic_retry=False)
