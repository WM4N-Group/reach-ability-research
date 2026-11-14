"""Source-pinned native zyh Runtime/Machine, no reimplementation of skills.

Only constructor scene/camera hook + exact accounting of additional free DOFs.
Every native policy, command queue, entry guard and switch algorithm is retained.
"""
import ast
import hashlib
import importlib
from pathlib import Path
import sys

from .source_bundle import verify_bundle
from .scene import configure_scene, verify_compiled_scene


def prepare_runtime_source(text):
    before = '        old_model = sim.model\n        sim.model = spec.compile()'
    after = '        old_model = sim.model\n        _wm_extra_nv, box_y = _wm_scene_hook(self, sim, spec)\n        sim.model = spec.compile()'
    old_calibration = 'self.push_reference = reference_stance(self)'
    new_calibration = 'self.push_reference = _wm_calibration(reference_stance, self)'
    old_assert = 'assert sim.model.nv == old_model.nv'
    new_assert = 'assert sim.model.nv == old_model.nv + _wm_extra_nv'
    if text.count(before)!=1 or text.count(old_assert)!=1 or text.count(old_calibration)!=1:
        raise ValueError('Exact pinned Runtime scene construction hook required')
    prepared = text.replace(before,after,1).replace(old_assert,new_assert,1).replace(old_calibration,new_calibration,1)
    ast.parse(prepared)
    if prepared.replace(new_calibration,old_calibration,1).replace(new_assert,old_assert,1).replace(after,before,1)!=text:
        raise ValueError('Unregistered skill/runtime mutation')
    return prepared, dict(schema='zyh-mujoco-runtime-scene-hook-v1',
        original_sha256=hashlib.sha256(text.encode()).hexdigest(),
        prepared_sha256=hashlib.sha256(prepared.encode()).hexdigest(),
        inverse_restores_original=True,constructor_only_hunks=3,
        native_actor_switch_guard_motor_algorithms_modified=False)


def load_runtime_types(bundle, config):
    receipt = verify_bundle(bundle)
    root = Path(bundle).resolve()
    switch = root/'switch'
    for name in ('plugins','runtime','machine','plans','push_entry','climb_entry','staircase'):
        module = sys.modules.get(name)
        if module is not None and not Path(module.__file__).resolve().is_relative_to(switch):
            raise ValueError('Foreign cached zyh module: '+name)
    sys.path.insert(0,str(switch))
    namespace = dict(__file__=str(switch/'runtime.py'),__name__='_piper_wm_pinned_zyh_runtime',
        _wm_scene_hook=lambda r,s,spec:configure_scene(r,s,spec,config),
        _wm_calibration=lambda fn,r:run_native_calibration(fn,r,config))
    prepared, hook = prepare_runtime_source((switch/'runtime.py').read_text())
    if config.get('stall_stow_mode'):
        from .stall_stow import initial_posture,initial_base,prepare_initialization_source
        prepared,initial_hook=prepare_initialization_source(prepared)
        namespace['_wm_stow_initial']=initial_posture
        namespace['_wm_stow_initial_base']=initial_base
        hook['independent_stall_stow_initialization']=initial_hook
    if config.get('schema')=='piper-mujoco-five-easy-scenes-case-v1':
        from .five_scene_suite import staircase_factory
        old='self.staircase=Staircase(StaircaseConfig(push_distance=distance))'
        new='self.staircase=_wm_staircase_factory(Staircase,StaircaseConfig,distance)'
        if prepared.count(old)!=1:raise ValueError('Pinned staircase constructor mismatch')
        prepared=prepared.replace(old,new,1)
        namespace['_wm_staircase_factory']=lambda cls,cfg,d:staircase_factory(cls,cfg,d,config)
        hook['engineering_staircase_configuration_changed']=True
    exec(compile(prepared,str(switch/'runtime.py')+'[scene-hook-only]','exec'),namespace)
    machine = importlib.import_module('machine').Machine
    # Machine imports Runtime's original infer/blend helpers. Their byte-pinned
    # definitions are unchanged; the original Runtime class is never constructed.
    plans = importlib.import_module('plans').plan
    return namespace['Runtime'],machine,plans,dict(source=receipt,scene_hook=hook)


def construct_runtime(bundle, config):
    if config.get('suite_revision',0)>=7:
        from .five_scene_suite import verify_readiness
        verify_readiness(config)
    Runtime,Machine,plan,receipt = load_runtime_types(bundle,config)
    runtime = Runtime.__new__(Runtime)
    try:
        Runtime.__init__(runtime,config['scenario'],config['box_height_m'],config['push_distance_m'],
            config['delay_ms'],config['seed'],config['actor_device'])
    except Exception as exc:
        exc.wm_partial_runtime=runtime
        raise
    if config.get('option_forecast_case') or config.get('recovery_exit_diagnostic_case') or config.get('push_protection_mode') or config.get('supported_push_mode'):
        from .option_probe import capture_initial_goal
        runtime.wm_initial_probe_goal=capture_initial_goal(runtime)
    if config.get('stall_stow_mode'):
        from .stall_stow import initialize_supported_stance
        try:runtime.wm_supported_initialization=initialize_supported_stance(runtime,require_calibration=config['scenario']=='nav-push')
        except Exception as exc:
            exc.wm_partial_runtime=runtime;raise
    scene = verify_compiled_scene(runtime,config)
    if config.get('reselect_B_mode'):
        from mujoco_selected_target_context import register_candidate_channels
        runtime.wm_candidate_contacts=register_candidate_channels(runtime)
    from .nav_efficiency import install
    tasks=install(runtime,plan(config['scenario'],getattr(runtime,'staircase',None)),config)
    if config.get('schema')=='piper-mujoco-five-easy-scenes-case-v1':
        from .five_scene_suite import install as install_suite
        tasks=install_suite(runtime,config)
    if config.get('integrated_course_mode'):
        from .integrated_course import install as install_integrated
        install_integrated(runtime,config)
    if config.get('stall_stow_mode'):tasks=[dict(skill='push')]
    if config.get('supported_push_mode'):
        from .reselect_B import compile_entry_and_machine
        Machine,runtime.wm_compact_entry_provenance=compile_entry_and_machine(bundle)
    if config.get('schema')=='piper-mujoco-five-easy-scenes-case-v1':
        from .five_scene_suite import machine_type
        Machine=machine_type(Machine,config)
    machine = Machine(runtime,tasks)
    return runtime,machine,dict(**receipt,scene=scene,supported_initialization=getattr(runtime,'wm_supported_initialization',None))


def run_native_calibration(function, runtime, config):
    """Original auxiliary stance physics, explicitly counted and not training data.

    The proxy only exposes the exact native bridge constructor so the auxiliary
    world's actual elapsed time can be recorded. Native settle/control unchanged.
    """
    import numpy as np
    from types import SimpleNamespace
    if config['auxiliary_calibration_worlds_allowed'] != 1:
        raise ValueError('Native Push reference calibration was not registered')
    live = runtime.sim
    before = (float(live.data.time),live.data.qpos.copy(),live.data.qvel.copy(),[x.copy() for x in live.queue])
    worlds = []
    class PluginView:
        def active(self): return runtime.push.active()
        def __getitem__(self,name):
            module = runtime.push[name]
            if name != 'bridge': return module
            def construct(*args,**kwargs):
                if worlds: raise ValueError('Only one auxiliary calibration world is allowed')
                sim = module.PushBridge(*args,**kwargs); worlds.append(sim); return sim
            return SimpleNamespace(PushBridge=construct)
    try:
        result = function(SimpleNamespace(push=PluginView()))
    finally:
        runtime.wm_auxiliary_calibration = dict(worlds=len(worlds),
            sim_seconds=float(worlds[0].data.time) if worlds else 0.,
            source='original zyh reference_stance + settle',used_as_training_episode=False,
            separate_initialization_state_adjustments_not_task_recovery=True,
            main_world_unchanged=(float(live.data.time)==before[0] and np.array_equal(live.data.qpos,before[1])
                and np.array_equal(live.data.qvel,before[2]) and len(live.queue)==len(before[3])
                and all(np.array_equal(a,b) for a,b in zip(live.queue,before[3]))))
    if len(worlds)!=1 or float(worlds[0].data.time)>config['auxiliary_calibration_max_sim_seconds']+1e-8:
        raise ValueError('Native calibration physical budget exceeded')
    if (float(live.data.time)!=before[0] or not np.array_equal(live.data.qpos,before[1])
        or not np.array_equal(live.data.qvel,before[2]) or len(live.queue)!=len(before[3])
        or any(not np.array_equal(a,b) for a,b in zip(live.queue,before[3]))):
        raise ValueError('Auxiliary calibration changed task world/state/motor queue')
    runtime.wm_auxiliary_calibration = dict(worlds=1,sim_seconds=float(worlds[0].data.time),
        source='original zyh reference_stance + settle',main_world_unchanged=True,
        separate_initialization_state_adjustments_not_task_recovery=True,used_as_training_episode=False)
    return result
