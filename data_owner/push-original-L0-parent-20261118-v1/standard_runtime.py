"""Fresh original standard Runtime, not the retired asset/MJB prerequisite.

NEW parent component only. No model/world/lease/Actor on import or CPU assembly.
Original constructor/scene/calibration/control are reused; retain even an early
partial object for truthful finally accounting. No state restoration/teleport.
"""
from pathlib import Path
import hashlib
import importlib
import importlib.util
import math
import types

from actor_trace import INFER_SHA, instrument_callsite, copy_infer_method
from l0_startup import derive_fresh_L0_runtime_source

CONFIG = dict(scenario='nav-push', scene_recipe='zyh_native_single_box',
              box_height_m=.2, push_distance_m=.6, delay_ms=20, seed=3701,
              actor_device='cuda:0', width=192, height=128,
              auxiliary_calibration_worlds_allowed=1,
              auxiliary_calibration_max_sim_seconds=10.5)
PINS = {
    'mujoco_zyh/runtime_adapter.py': '9b3a7f941be48f73783bbd096f82ed662915238aa72949ff4deb4cfd35526bb9',
    'mujoco_zyh/scene.py': '18758bb505f1af255fb04e0a757dc21427faa35263a305ff471e0b21fe6bf76e',
    'ainav/native/scene_registry.py': '1d5baefee91a46d0b92f72663eff59b49eb7e7cc18754f95ef036458502566bf',
    'ainav/native/supported_capture.py': '618f8640b0b0be295af56cff036d506c1cee8649d556448f746634be893a14cd',
    'ainav/native/registered_observer.py': '90c2d5e9247c797d337e1b6efedaeda56527c80a5f10f382294c40c7d72f5f17',
    'ainav/native/placement_contract.py': '882481668854468a59ec4aacfc44f7912286fdece8c4d91e11ce010f6dc98511',
}


def need(ok, message):
    if not ok:
        raise ValueError(message)


def bounded_exception(exc, *, max_frames=16):
    """File/function/line/type/errno only; no locals, text, source lines or secret headers."""
    need(type(max_frames) is int and 1 <= max_frames <= 16, 'Bounded traceback')
    rows = []
    tb = exc.__traceback__
    total = 0
    while tb is not None:
        code = tb.tb_frame.f_code
        position = None
        offset = tb.tb_lasti
        if type(offset) is int and 0 <= offset <= 1000000:
            for index, span in enumerate(code.co_positions()):
                if index == offset // 2:
                    position = dict(start_line=span[0], end_line=span[1],
                                    start_column=span[2], end_column=span[3])
                    break
        rows.append(dict(file=code.co_filename, function=code.co_name, line=tb.tb_lineno,
                         instruction_offset=offset, source_position=position))
        if len(rows) > max_frames:
            rows.pop(0)  # Keep the most specific leaf, including the actual errno site.
        total += 1
        tb = tb.tb_next
    return dict(error_type=type(exc).__name__, errno=getattr(exc, 'errno', None),
                frames=rows, omitted_outer_frames=max(0, total-len(rows)),
                exception_text_locals_or_headers_recorded=False)


class ConstructionReceipt:
    def __init__(self):
        self.runtime = self.observer = None
        self.started = self.completed = False
        self.runtime_init_completed = False

    def usage_snapshot(self):
        result = dict(runtime_constructor_started=self.started,
                      runtime_init_completed=self.runtime_init_completed,
                      components_completed=self.completed,
                      task_steps=None, task_sim_s=None, auxiliary=None,
                      usage_known=False, no_default_zero_for_missing_clock=True)
        r = self.runtime
        if r is None:
            return result
        # Keep each actual counter independently; a missing aux final receipt
        # MUST NOT erase a known task counter or fabricate unknown auxiliary0.
        try:
            steps = r.step_count
            need(type(steps) is int and steps >= 0, 'Actual task step counter')
            result['task_steps'] = steps
        except (AttributeError, ValueError):
            pass
        try:
            stamp = float(r.sim.data.time)
            need(math.isfinite(stamp) and stamp >= 0, 'Actual task clock')
            result['task_sim_s'] = stamp
        except (AttributeError, ValueError, TypeError):
            pass
        try:
            import json
            aux = json.loads(json.dumps(r.wm_auxiliary_calibration, allow_nan=False))
            need(type(aux['worlds']) is int and aux['worlds'] >= 0 and
                 type(aux['sim_seconds']) in (int, float) and
                 math.isfinite(aux['sim_seconds']) and aux['sim_seconds'] >= 0,
                 'Actual original auxiliary receipt')
            result['auxiliary'] = aux
        except (AttributeError, ValueError, TypeError, KeyError):
            pass
        result['usage_known'] = all(result[k] is not None for k in ('task_steps', 'task_sim_s', 'auxiliary'))
        return result


def registry(api):
    return api.SceneRegistry([api.ObjectSpec('sdk_box', 'push_box', (1.2, 1.2, .2), 'ground')],
        [api.SurfaceSpec('ground', 'ground', (-20., 20., -10., 10.), 0.)],
        api.GoalSpec('ground', (1.68, 1.72, -.02, .02)))


def placement_contract(source_root):
    root = Path(source_root).resolve(strict=True)
    module = _import_pinned(root, 'ainav.native.placement_contract', PINS['ainav/native/placement_contract.py'])
    # 2.3m is the declared goal-aligned FRONT measurement plane, not a newly
    # inserted wall/platform. Original 20mm XY/10mm orientation-aware gap remain.
    return module.PlacementContract(target_ref='sdk_box', public_goal_xy_m=(1.7, 0.),
        docking_plane_x_m=2.3, box_size_m=(1.2, 1.2, .2), source_surface_height_m=0.,
        native_stop_distance_m=.11, mode='uncompensated')


def _install_terrain(runtime, reg, contract):
    api = importlib.import_module('ainav.native.scene_registry')
    placement = importlib.import_module('ainav.native.placement_contract')
    need(not hasattr(runtime, 'staircase'), 'Never replace existing/native terrain')
    p = runtime.sim
    world = (p.model, p.data, p.queue)
    contract_sha = contract.sha256
    class StandardRegisteredTerrain(api.RegisteredTerrain):
        def dock_metrics(self, view):
            need(all(a is b for a, b in zip(world, (view.model, view.data, view.queue))) and
                 view.model.body(view.box_id).name == 'push_box' and contract.sha256 == contract_sha,
                 'Actual selected standard body/world/immutable contract')
            return placement.PlacementTerrain(contract).dock_metrics(view)
    terrain = StandardRegisteredTerrain(reg)
    runtime.staircase = terrain  # Metadata ABI only; original AttemptTerrain still owns push_ready.
    return terrain


def _import_pinned(root, name, pin):
    path = root / (name.replace('.', '/') + '.py')
    need(not path.is_symlink() and hashlib.sha256(path.read_bytes()).hexdigest() == pin,
         'Exact original source ' + name)
    spec = importlib.util.find_spec(name)
    need(spec is not None and Path(spec.origin).resolve() == path.resolve(), 'No ambient import ' + name)
    module = importlib.import_module(name)
    need(Path(module.__file__).resolve() == path.resolve(), 'No cached foreign module ' + name)
    return module


def assemble(*, source_root=None, bundle=None, trace=None, receipt=None, enabled=False):
    """CPU compile/source assembly. NOT whole-program prepare/physical admission.

    Returns a default-OFF one-use constructor. Private Runtime subclass only
    records original history-init calls. Its original step is not overridden.
    The unused original Machine is retained as source custody, NOT run as a
    shortcut around the registered session/12N/placement/STOW controllers.
    """
    need(type(enabled) is bool, 'Explicit new component opt-in')
    if not enabled:
        return None
    need(type(receipt) is ConstructionReceipt and not receipt.started, 'Fresh partial receipt')
    root = Path(source_root).resolve(strict=True)
    sdk = Path(bundle).resolve(strict=True)
    for rel, pin in PINS.items():
        _import_pinned(root, rel[:-3].replace('/', '.'), pin)
    adapter = importlib.import_module('mujoco_zyh.runtime_adapter')
    # Private binding of the original loader's one source-preparation callback.
    # No module/global/SDK file is replaced. Only the fresh L0 INITIAL X differs.
    original_prepare=adapter.prepare_runtime_source
    def prepare_L0(text):
        changed,initial_receipt=derive_fresh_L0_runtime_source(text.encode(),enabled=True)
        prepared,receipt=original_prepare(changed)
        return prepared,dict(receipt,explicit_original_PUSH_L0_initialization=initial_receipt,
            generated_source_is_modified_constructor_variant=True)
    private_loader=dict(adapter.load_runtime_types.__globals__)
    private_loader['prepare_runtime_source']=prepare_L0
    loader=types.FunctionType(adapter.load_runtime_types.__code__,private_loader,
        adapter.load_runtime_types.__name__,adapter.load_runtime_types.__defaults__,adapter.load_runtime_types.__closure__)
    Runtime, Machine, plan, original_receipt = loader(sdk, dict(CONFIG))
    infer = Machine.update.__globals__['infer']
    traced = instrument_callsite(infer, source_path=sdk/'switch/runtime.py', source_sha256=INFER_SHA,
        function_name='infer', actor_expression='actor', trace=trace)

    class PartialRuntime(Runtime):
        def __new__(cls):
            need(receipt.runtime is None, 'No second world/duplicate partial Runtime')
            value = object.__new__(cls)
            receipt.runtime = value
            return value

        def __init__(self, *args, **kwargs):
            Runtime.__init__(self, *args, **kwargs)  # Exact original construction/calibration.
            receipt.runtime_init_completed = True

    def wrap_reset(name):
        original = getattr(Runtime, name)
        def invoke(self, *args, **kwargs):
            return trace.reset_call(name, original, self, *args, **kwargs)
        return invoke
    for name in ('reset_nav_history', 'push_enter', 'climb_enter'):
        setattr(PartialRuntime, name, wrap_reset(name))
    class UnusedOriginalMachine(Machine):
        update = copy_infer_method(Machine.update, traced)

    private = dict(adapter.construct_runtime.__globals__)
    def types_once(given_bundle, config):
        need(Path(given_bundle).resolve() == sdk and config == CONFIG, 'Exact standard constructor config')
        return PartialRuntime, UnusedOriginalMachine, plan, original_receipt
    private['load_runtime_types'] = types_once
    original_construct = adapter.construct_runtime
    construct = types.FunctionType(original_construct.__code__, private, original_construct.__name__,
                                   original_construct.__defaults__, original_construct.__closure__)
    construct.__kwdefaults__ = original_construct.__kwdefaults__

    def build(*, guard=None, journal=None, enabled=False):
        need(type(enabled) is bool, 'Explicit construction opt-in')
        if not enabled:
            return None
        need(callable(guard) and callable(journal) and guard() is not False,
             'Real parent authority/lease/1s poll/2s freshness; not source assembly permission')
        need(not receipt.started, 'Single fresh construction; no retry or state reuse')
        receipt.started = True
        # PartialRuntime.__new__ exposes the actual object even if original
        # constructor's AFTER-init verify/plan/Machine stage throws later.
        r, unused_machine, construction = construct(sdk, dict(CONFIG))
        need(r is receipt.runtime and r.step_count == 0 and float(r.sim.data.time) == 0. and not r.sim.queue,
             'Fresh original task0, never restore or issue a command')
        import numpy as np
        p = r.sim
        reg = registry(importlib.import_module('ainav.native.scene_registry'))
        reg.verify_compiled(p.model)
        from ainav.native.registered_target_context import register_candidate_channels
        r.wm_candidate_contacts = register_candidate_channels(r, reg)
        contract = placement_contract(root)
        _install_terrain(r, reg, contract)
        need(abs(float(p.model.body_mass[p.box_id])-1.) < 1e-10 and
             np.allclose(p.data.xpos[p.box_id], [1.1, 0., .1], rtol=0, atol=1e-10) and
             np.allclose(p.data.qpos[:3], [-.08, 0., .33], rtol=0, atol=1e-10) and
             np.allclose(p.box_push_target.detach().cpu().numpy()[0, :2], [1.7, 0.], rtol=0, atol=2e-7),
             'Exact original box/robot/immutable uncompensated goal')
        need(unused_machine.tasks == [dict(skill='nav', goal=[-.02, 0.]), dict(skill='push')],
             'Unused original source-plan custody only; L0 never executes its NAV')
        # Capacity only, before any renderer/step. Original camera ABI unchanged.
        p.model.vis.global_.offwidth = max(int(p.model.vis.global_.offwidth), 1280)
        p.model.vis.global_.offheight = max(int(p.model.vis.global_.offheight), 720)
        p.feet_ids=np.array([p.model.body(n+'_foot').id for n in ('FR','FL','RR','RL')])
        p.soft_limits=p.robot.data.soft_joint_pos_limits.numpy()[0][[p.robot.joint_names.index(n)for n in r.push['model'].JOINTS]]
        trace.bind_runtime(r)
        from ainav.native.registered_observer import RegisteredObserver
        class PartialObserver(RegisteredObserver):
            def __new__(cls, *args, **kwargs):
                value = object.__new__(cls)
                receipt.observer = value
                return value
        observer = PartialObserver(r, dict(width=192, height=128, scene_recipe='registered'), reg)
        need(guard() is not False, 'Original post-construction resource/authority guard')
        receipt.completed = True
        return dict(runtime=r, registry=reg, observer=observer,
                    construction=construction, placement_contract=contract, unused_original_machine=unused_machine,
                    external_MJB_required=False, physical_task_admission=False)
    return build
