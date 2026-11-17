"""Actual-private-Python CPU SOURCE assembly only. Not full-parent prepare or run."""
from pathlib import Path
import argparse
import hashlib
import json
import sys

# -I deliberately ignores script directory; bootstrap ONLY this selected code dir.
sys.path.insert(0, str(Path(__file__).resolve().parent))


def qualify(source_root, bundle):
    from actor_trace import ActorTrace
    import standard_runtime
    import registered_trace
    root, sdk = Path(source_root).resolve(strict=True), Path(bundle).resolve(strict=True)
    sys.path[:0] = [str(root), str(sdk/'switch')]
    import torch
    if torch.cuda.is_initialized():raise RuntimeError('CPU source qualification must not initialize CUDA')
    receipt = standard_runtime.ConstructionReceipt()
    trace = ActorTrace(lambda: dict(root_skill='NOT_STARTED', native_phase='task0', task_step=0, task_sim_s=0.))
    build = standard_runtime.assemble(source_root=root, bundle=sdk, trace=trace, receipt=receipt, enabled=True)
    assert build(enabled=False) is None
    contract = standard_runtime.placement_contract(root)
    assert contract.drive_goal_xy_m == (1.7, 0.) and contract.mode == 'uncompensated'
    assert contract.docking_plane_x_m == 2.3
    pose = dict(box_position=[1.7, 0., .1], rotation_world_from_box=[[1.,0.,0.],[0.,1.,0.],[0.,0.,1.]], native_goal_xy=[1.7,0.])
    assert contract.evaluate(**pose)['placement_geometry_verified']
    pose['box_position'] = [1.685, 0., .1]
    measured = contract.evaluate(**pose)
    assert measured['public_XY_error_m'] < .02 and not measured['placement_geometry_verified']
    assert not receipt.started and receipt.runtime is receipt.observer is None
    from ainav.native import registered_push_api as original_push
    from ainav.native import registered_compact_nav as original_nav
    original_update = original_nav.RegisteredCompactNav.update
    original_compiler = original_push._compile_registered_push_machine
    original_selected = original_push.RegisteredPushAPI.selected_push_session
    hooks = registered_trace.assemble(source_root=root, bundle=sdk, trace=trace, enabled=True)
    cls, proof = hooks['compile_private_push'](sdk, approach_xy=(-.02, 0.), surface_height_m=0., compact_arm=False)
    assert cls.__dict__['update'].__globals__['infer'] is not __import__('runtime').infer
    assert cls.__dict__['update'].__code__ is not None
    # Preserve actual generated base method bytecode; no base-update installed on
    # a live derived instance and no overriding after session/check construction.
    assert issubclass(hooks['nav_constructor'], original_nav.RegisteredCompactNav)
    assert hooks['nav_constructor'].check_guards is original_nav.RegisteredCompactNav.check_guards
    assert hooks['nav_constructor'].after_step is original_nav.RegisteredCompactNav.after_step
    assert original_nav.RegisteredCompactNav.update is original_update
    assert original_push._compile_registered_push_machine is original_compiler
    assert original_push.RegisteredPushAPI.selected_push_session is original_selected
    assert hooks['push_api_class'].selected_push_session.__code__ is original_selected.__code__
    assert not torch.cuda.is_initialized() and not trace.actors and not trace.rows
    assert standard_runtime.assemble(enabled=False) is None and registered_trace.assemble(enabled=False) is None
    assert registered_trace.connect_after_capture(enabled=False) is None
    selected = {str(root/rel): pin for rel, pin in standard_runtime.PINS.items()}
    selected[str(sdk/'switch/runtime.py')] = __import__('actor_trace').INFER_SHA
    selected[str(root/'ainav/native/registered_compact_nav.py')] = __import__('actor_trace').NAV_SHA
    selected[str(root/'ainav/native/registered_push_api.py')] = registered_trace.PUSH_SHA
    for path, pin in selected.items():assert hashlib.sha256(Path(path).read_bytes()).hexdigest() == pin
    return dict(stage='ACTUAL_PRIVATE_PYTHON_CPU_SOURCE_ASSEMBLY_PASS_NOT_FULL_PARENT_PREPARE',
        interpreter=sys.executable, python=list(sys.version_info[:3]), selected_source_SHA256=selected,
        constructor_default_off=True, uncompensated_original_placement_contract=contract.public(),
        docking_plane_is_declared_measurement_datum_not_inserted_wall=True, registered_NAV_PUSH_callsite_copies_compiled=True,
        original_registered_guards_and_class_chains_retained=True,
        generated_PUSH_compiler_receipt=proof, partial=receipt.usage_snapshot(),
        CUDA_initialized=False, Runtime_or_world_or_lease_or_Actor_model_forward=0,
        Actor_trace_coverage_complete=False, whole_program_frozen=False,
        own_zero=0, main=0, physical_admission=False)


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--enabled', action='store_true')
    ap.add_argument('--source-root');ap.add_argument('--bundle')
    a = ap.parse_args()
    if a.enabled:print(json.dumps(qualify(a.source_root, a.bundle), ensure_ascii=False, indent=2))
