"""Generalized copy of native PUSH construction; registry-backed support frame.

Only the inherited 0/.4 construction whitelist is replaced by a validated actual
registered source surface. Actor, Machine/PushEntry algorithms, NN flags,
progress monitor, limits and actual native session class are retained.
"""
import hashlib

from mujoco_zyh.native_behavior_executor import array_sha,NativeOptionSession

def _compile_registered_push_machine(bundle, *, approach_xy, surface_height_m, compact_arm):
    """Pinned entry-reference adaptation; source algorithms/guards unchanged.

    Combines the previously separate compact-arm and elevated-entry adapters.
    Only software reference targets and the declared arm-ready target change.
    No native calibration/constructor/actor inference occurs in this function.
    """
    from pathlib import Path
    from types import ModuleType
    import math
    import sys
    from mujoco_zyh.resume_nav import NAV_ARM
    root = Path(bundle) / 'switch'
    entry_original = (root / 'push_entry.py').read_text()
    machine_original = (root / 'machine.py').read_text()
    if (len(approach_xy) != 2 or not all(math.isfinite(x) for x in approach_xy)
            or (not math.isfinite(surface_height_m) or surface_height_m<0.) or type(compact_arm) is not bool):
        raise ValueError('Registered ground/high-deck approach reference required')
    entry = entry_original
    machine = machine_original
    changes = [
        ('entry', 'self.base_goal=np.array([-.08,runtime.box_y,self.reference[\'height\']])',
         "self.base_goal=np.array([_wm_approach[0],_wm_approach[1],self.reference['height']+_wm_surface])"),
        ('machine', '            from push_entry import PushEntry',
         '            PushEntry = _wm_option_entry')]
    if compact_arm:
        changes += [
            ('entry', 'and np.max(abs(p.data.qpos[p.qids[12:]]))<.08)',
             'and np.max(abs(p.data.qpos[p.qids[12:]]-_wm_NAV_ARM))<.04)'),
            ('entry', '        anchors=self.anchors.copy()',
             '        arm.position[12:]=_wm_NAV_ARM\n        anchors=self.anchors.copy()'),
            ('machine', 'np.max(abs(p.data.qpos[p.qids[12:]]))>.12',
             'np.max(abs(p.data.qpos[p.qids[12:]]-_wm_NAV_ARM))>.04')]
    for where, old, new in changes:
        text = entry if where == 'entry' else machine
        if text.count(old) != 1:
            raise ValueError('Pinned single-option native entry hook mismatch: ' + old)
        text = text.replace(old, new, 1)
        if where == 'entry':
            entry = text
        else:
            machine = text
    restored_entry, restored_machine = entry, machine
    for where, old, new in reversed(changes):
        if where == 'entry':
            restored_entry = restored_entry.replace(new, old, 1)
        else:
            restored_machine = restored_machine.replace(new, old, 1)
    if (restored_entry, restored_machine) != (entry_original, machine_original):
        raise ValueError('Native source hook inverse mismatch')
    module_id = hashlib.sha256(repr((approach_xy, surface_height_m, compact_arm)).encode()).hexdigest()[:12]
    ep = ModuleType('_wm_behavior_entry_' + module_id)
    ep.__file__ = str(root / 'push_entry.py')
    ep.__dict__.update(_wm_approach=tuple(approach_xy), _wm_surface=surface_height_m, _wm_NAV_ARM=NAV_ARM)
    sys.modules[ep.__name__] = ep
    exec(compile(entry, ep.__file__ + '[behavior-reference]', 'exec'), ep.__dict__)
    mp = ModuleType('_wm_behavior_machine_' + module_id)
    mp.__file__ = str(root / 'machine.py')
    mp.__dict__.update(_wm_option_entry=ep.PushEntry, _wm_NAV_ARM=NAV_ARM)
    sys.modules[mp.__name__] = mp
    exec(compile(machine, mp.__file__ + '[single-option]', 'exec'), mp.__dict__)
    receipt = dict(entry_original_sha256=hashlib.sha256(entry_original.encode()).hexdigest(),
                   machine_original_sha256=hashlib.sha256(machine_original.encode()).hexdigest(),
                   entry_adapted_sha256=hashlib.sha256(entry.encode()).hexdigest(),
                   machine_adapted_sha256=hashlib.sha256(machine.encode()).hexdigest(),
                   inverse_restores_exact_original=True, only_declared_reference_hooks=True,
                   approach_xy=list(approach_xy), surface_height_m=surface_height_m,
                   compact_arm=compact_arm, task_success_or_next_skill_added=False,
                   physics_steps=0, actors_forwarded=0)
    return mp.Machine, receipt

def _selected_registered_push_session(runtime, bundle, option, *, view, binding_receipt, extra_guards):
    """Execute a prebound selected-object attempt with chosen original distance.

    `view` must be prepared before candidate selection, with a prospective cfg and
    measured immutable goal. Only the chosen view is entered. The caller retains
    all unused/retired binding provenance and checks source/query freshness.
    """
    import numpy as np
    from types import SimpleNamespace, MethodType
    from initial_contact_progress_monitor import (ContactProgressConfig,
        ContactProgressSample, InitialContactProgressMonitor)
    from mujoco_zyh.integrated_course import weak_flags, PushSurfaceView
    from mujoco_zyh.resume_nav import NAV_ARM
    from mujoco_zyh.stall_stow import ProtectedStow, SoftStall
    from mujoco_zyh.failure_capsules import emit
    params = dict(option.parameters)
    if option.skill != 'PUSH' or not {'goal_world_x_m', 'goal_world_y_m', 'surface_height_m', 'push_distance_m'} <= set(params):
        raise ValueError('Explicit PUSH attempt/approach/distance required')
    original_goal = lambda: view.box_push_target.detach().cpu().numpy()
    if (array_sha(original_goal()) != option.original_push_goal_sha256
            or abs(view.cfg.push_distance - params['push_distance_m']) > 1e-8
            or view.controller.env is not view.target_context
            or view.controller.env.cfg is not view.cfg
            or view.data is not runtime.sim.data or view.queue is not runtime.sim.queue
            or binding_receipt.get('controller_env_is_explicit_context') is not True):
        raise ValueError('Chosen attempt must match actual target, controller cfg and shared world/FIFO')
    surface = params['surface_height_m']
    approach = [params['goal_world_x_m'], params['goal_world_y_m']]
    arm = view.data.qpos[view.qids[12:]]
    compact = bool(np.max(abs(arm - NAV_ARM)) < .04)
    cls, hook = _compile_registered_push_machine(bundle, approach_xy=approach,
                                            surface_height_m=surface, compact_arm=compact)
    proxy = SimpleNamespace(**vars(runtime))
    proxy.sim = view
    proxy.box_y = approach[1]
    proxy.last = runtime.last
    if surface:
        proxy.push = PushSurfaceView(runtime.push, surface)
    proxy.push_enter = MethodType(type(runtime).push_enter, proxy)
    terrain = runtime.staircase
    class AttemptTerrain:
        def __getattr__(self, key):
            return getattr(terrain, key)
        def push_ready(self, sim, native_settled):
            # Full-task docking is a planning/postcondition check. A deliberately
            # shorter native attempt may finish without completing that task.
            return bool(native_settled)
    proxy.staircase = AttemptTerrain()
    native_termination = view.termination
    raw_flags = lambda: weak_flags(view, runtime.push['bridge'].box_push,
                                   native_termination, runtime.push['model'].EFFORT)
    progress = InitialContactProgressMonitor(ContactProgressConfig(window_s=.06))
    state = dict(machine=None, tick=0)
    def termination():
        flags = raw_flags()
        machine = state['machine']
        if machine is None or machine.phase == 'prepare' or machine.finish is not None:
            return flags
        box = runtime.push['bridge'].box_push
        bad = [k for k, v in flags.items() if k != 'box_settled' and v]
        legal = bool(box.hand_contact(view, view.hand_cfg)[0])
        near = bool(np.linalg.norm(view.data.xpos[view.box_id, :2] - original_goal()[0, :2]) < .12)
        decision = progress.observe(ContactProgressSample(state['tick'], float(view.data.time),
            True, bool(view.controller.motion_ready[0]), legal, True,
            float(view.data.xpos[view.box_id, 0]), near, bool(flags['box_settled']), bool(bad)))
        state['tick'] += 1
        if decision.new_soft_abort_request:
            emit(runtime, 'behavior_PUSH_contact_progress_failed', view=view,
                 extra=dict(attempt_id=option.attempt_id,
                            original_goal=original_goal().tolist(),
                            contact_window_s=decision.elapsed_contact_s,
                            dx_m=decision.observed_forward_dx_m), preserve_primary_failure=True)
            raise SoftStall('behavior_PUSH_original_contact_progress_failed')
        return flags
    view.termination = termination
    machine = cls(proxy, [dict(skill='push', approach=approach)])
    state['machine'] = machine
    def refresh():
        view.target_context._env.common_step_counter = runtime.step_count
        view.refresh()
    def guards():
        flags = raw_flags()
        bad = [k for k, v in flags.items() if k != 'box_settled' and v]
        if bad:
            raise RuntimeError('behavior_selected_PUSH_native_guard:' + ','.join(bad))
        extra_guards()
    session = NativeOptionSession(runtime, machine, refresh=refresh,
        original_goal=original_goal,
        make_exit=lambda refs: ProtectedStow(proxy, refs, compact_goal=NAV_ARM),
        soft_failure=(SoftStall,), check_guards=guards)
    session.binding_receipt = binding_receipt
    session.native_hook_receipt = hook
    session.full_task_docking_not_inferred_from_attempt_success = True
    return session


from .scene_registry import declared_push_source as registered_push_source


class RegisteredPushAPI:
    def __init__(self,registry,native_api=None):
        if native_api is None:
            from mujoco_zyh import native_behavior_executor as native_api
        self.registry,self.native_api=registry,native_api
    def __getattr__(self,name):return getattr(self.native_api,name)
    def selected_push_session(self,runtime,bundle,option,*,view,binding_receipt,extra_guards):
        import numpy as np
        self.registry.verify_compiled(runtime.sim.model)
        body=runtime.sim.model.body(view.box_id).name
        height=dict(option.parameters)['surface_height_m'];obj=registered_push_source(self.registry,body,height)
        if tuple(view.cfg.box_size)!=tuple(obj.size_m):raise ValueError('Selected cuboid dimensions changed')
        p=runtime.sim;ids=[p.model.body(n+'_foot').id for n in ('FR','FL','RR','RL')]
        surface=self.registry.surfaces[obj.initial_support];x0,x1,y0,y1=surface.bounds_xy_m;feet=p.data.xpos[ids];loads=p.forces[ids,2]
        from .push_support_gate import require_push_source_support
        require_push_source_support(surface.bounds_xy_m,height,feet.tolist(),loads.tolist())
        session=_selected_registered_push_session(runtime,bundle,option,view=view,binding_receipt=binding_receipt,extra_guards=extra_guards)
        session.registered_source_proof=dict(object_ref=obj.ref,surface_ref=surface.ref,surface_height_m=height,
            actual_loaded_feet_N=loads.tolist(),native_controller_limits_unchanged=True,model_input=False)
        return session
