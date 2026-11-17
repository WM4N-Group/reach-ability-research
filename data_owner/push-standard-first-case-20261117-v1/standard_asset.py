"""Future standard one-box static asset, never the V4 2/3-box adapter.

Default OFF. Enabled path needs original live lease/guard and controlled ScopeIO.
One fresh original PushBridge at time0, no Runtime/Actor/renderer/step or state
restore; original camera-only hook and robot signature are retained.
"""
from pathlib import Path
import hashlib
import importlib.util
import json
import sys

QUESTION = 'SDK_STANDARD_ONE_BOX_STATIC_ASSET_FOR_FIRST_NATURAL_NAV_PUSH_L1_NOT_SKILL_RESULT'
CASE = dict(scenario='nav-push', seed=3701, delay_ms=20, push_distance_m=.6,
            box_size_m=[1.2,1.2,.2], box_mass_kg=1., box_initial_xyz_m=[1.1,0.,.1],
            original_runtime_initial_robot_xyz_m=[-1.,0.,.33], original_NAV_goal_xy_m=[-.02,0.],
            native_drive_goal_xy_m=[1.7,0.], public_placement_goal_xy_m=[1.7,0.],
            placement_mode='uncompensated', stop_offset_not_tuned=True, ground_height_m=0.,
            original_policy_histories_initialized_only_by_original_entries=True)


def need(ok, message):
    if not ok:
        raise RuntimeError(message)


def source(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def declaration(scene_registry=None, *, enabled=False):
    if enabled is not True:
        return None
    # Generic ORIGINAL registry accepts this prototype. Do not relax/change
    # complex_scene.validate, which correctly rejects it for its V4 contract.
    api = scene_registry
    return api.SceneRegistry([api.ObjectSpec('sdk_box','push_box',(1.2,1.2,.2),'ground')],
        [api.SurfaceSpec('ground','ground',(-20.,20.,-10.,10.),0.)],
        api.GoalSpec('ground',(1.68,1.72,-.02,.02)))


def build(c=None, budget=None, guard=None, counters=None, *, enabled=False):
    if enabled is not True:
        return None
    need(callable(guard) and budget is not None, 'Real original lease/watch plus controlled output required')
    need(c['case']==CASE and c['question']==QUESTION, 'Exact prospective standard-domain case, not V4 renamed L0')
    guard()
    import mujoco
    import numpy as np
    from plugins import Plugin, ROOT as plugin_root
    from mujoco_zyh.source_bundle import verify_bundle
    from ainav.native import scene_registry
    from camera_abi import install_original_camera, verify_compiled_camera
    verification = verify_bundle(c['SDK'])
    need(Path(plugin_root).resolve()==Path(c['SDK']).resolve(), 'Original selected SDK plugin root, no private/ambient alias')
    helper_path = Path(c['source_root'])/'build_transfer_scene_native.py'
    need(source(helper_path)==c['robot_signature_source_SHA'], 'Exact original robot signature helper')
    spec = importlib.util.spec_from_file_location('_data_std_original_robot_signature',helper_path)
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    native = Plugin('push',['bridge','model'])
    counters['world_constructors_started'] += 1
    with native.active():
        sim = native['bridge'].PushBridge(seed=3701,delay_ms=20,push_distance=.6)
    counters['world_constructors_completed'] += 1
    need(sim.device=='cpu' and float(sim.data.time)==0. and not sim.queue, 'Original CPU zero-step constructor and empty FIFO')
    original_signature = helper.robot_signature(sim.model)
    before_ids = {name:sim.model.joint(name).id for name in native['model'].JOINTS}
    reg = declaration(scene_registry,enabled=True)
    reg.verify_compiled(sim.model)
    b = sim.model.body('push_box')
    need(abs(float(sim.model.body_mass[b.id])-1.)<1e-10, 'Original standard1kg, never replace with V4 .5kg')
    need(np.allclose(sim.data.xpos[b.id],CASE['box_initial_xyz_m'],rtol=0,atol=1e-10), 'Original default box placement')
    need(np.allclose(sim.box_push_target[0,:2].numpy(),CASE['native_drive_goal_xy_m'],rtol=0,atol=2e-7), 'Original immutable native .6m goal, no compensated drive')
    camera = install_original_camera(sim,source_root=c['source_root'])
    model = sim.spec.compile()
    counters['additional_static_compiles_completed'] += 1
    guard()
    need(helper.robot_signature(model)==original_signature, 'Robot/engine/actuator signature unchanged')
    need(all(getattr(model,name)==getattr(sim.model,name)for name in ('nq','nv','nu','nbody','njnt','ngeom','nmesh')), 'Camera-only compile adds no bodies/geometries/DOF')
    for name in ('body_mass','geom_type','geom_bodyid','geom_pos','geom_quat','geom_size','geom_friction','pair_friction','qpos0'):
        need(np.array_equal(getattr(model,name),getattr(sim.model,name)), 'Original physical model array changed: '+name)
    need(all(model.joint(name).id==ident for name,ident in before_ids.items()), 'Original robot joint IDs unchanged')
    reg.verify_compiled(model)
    need(abs(float(model.body_mass[model.body('push_box').id])-1.)<1e-10, 'Compiled standard box mass')
    camera_receipt = verify_compiled_camera(model,source_root=c['source_root'])
    model.vis.global_.offwidth=max(int(model.vis.global_.offwidth),1280)
    model.vis.global_.offheight=max(int(model.vis.global_.offheight),720)
    need(float(sim.data.time)==0. and not sim.queue, 'Static camera compile never steps/restores task')
    n=int(mujoco.mj_sizeModel(model))
    need(0<n<=c['model_buffer_cap_bytes'], 'Bound serialized model buffer before allocation/output')
    buffer=np.empty(n,dtype=np.uint8)
    mujoco.mj_saveModel(model,buffer=buffer)
    # No C filename writes bypass accounting; only the original ScopeIO writes.
    with budget.open('standard-nav-push.mjb','xb') as out:
        out.write(memoryview(buffer));out.flush()
        import os
        os.fsync(out.fileno())
    guard()
    path=budget.root/'standard-nav-push.mjb'
    return dict(model_path=str(path),model_SHA256=source(path),model_bytes=n,case=CASE,
        robot_engine_signature_sha256=original_signature,camera_installation=camera,
        camera_ABI=camera_receipt,registry=reg.public_geometry(),source_bundle_verification=verification,
        actual_original_constructor_task_sim_s=float(sim.data.time),actual_physics_commands=0,
        Actor_load_forward_Runtime_Renderer_CUDA_initialization=0,
        static_model_only_not_world_state_or_own_zero=True,L0_not_claimed=True,
        L1_future_main_not_started=True,public_goal_and_native_goal_not_merged_as_success=True)
