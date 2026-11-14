"""Cold native Runtime construction with a validated static scene MJB.

Only constructor model source and before-first-step initialization differ.
No task state file is read, replay state is never loaded, no machine is started.
All native control methods, actor bytes, reference calibration and FIFO remain.
This module is not an execution host or entry/stability certificate.
"""
import hashlib
import importlib
from pathlib import Path
import sys


def construct_cold_runtime(bundle,model_path,*,model_sha256,initial_robot,initial_surface_height_m,seed=3701,initial_arm_reference=None,actor_device='cuda:1'):
    import numpy as np
    import mujoco
    from mujoco_zyh.runtime_adapter import prepare_runtime_source,run_native_calibration
    from mujoco_zyh.source_bundle import verify_bundle
    from mujoco_zyh.stall_stow import NATIVE_COMPACT_ARM
    bundle=Path(bundle).resolve();model_path=Path(model_path).resolve()
    verify_bundle(bundle)
    if hashlib.sha256(model_path.read_bytes()).hexdigest()!=model_sha256:raise ValueError('Registered static model SHA differs')
    switch=bundle/'switch';sys.path.insert(0,str(switch))
    for name in ('plugins','runtime','machine','plans','push_entry','climb_entry','staircase'):
        module=sys.modules.get(name)
        if module is not None and not Path(module.__file__).resolve().is_relative_to(switch):raise ValueError('Foreign native module cached')
    original=(switch/'runtime.py').read_text();prepared,receipt=prepare_runtime_source(original)
    old='sim.model = spec.compile()';new='sim.model = _registered_static_model()'
    if prepared.count(old)!=1:raise ValueError('Exact constructor compile location required')
    prepared=prepared.replace(old,new,1)
    loader=lambda:mujoco.MjModel.from_binary_path(str(model_path))
    def scene_hook(runtime,sim,spec):
        model=loader()
        if model.nu!=sim.model.nu:raise ValueError('Native actuator count changed')
        return model.nv-sim.model.nv,float(initial_robot['xy_m'][1])
    config=dict(auxiliary_calibration_worlds_allowed=1,auxiliary_calibration_max_sim_seconds=10.)
    ns=dict(__file__=str(switch/'runtime.py'),__name__='_ainav_registered_scene_runtime',
        _registered_static_model=loader,_wm_scene_hook=scene_hook,
        _wm_calibration=lambda fn,r:run_native_calibration(fn,r,config))
    exec(compile(prepared,str(switch/'runtime.py')+'[registered-model-constructor-only]','exec'),ns)
    if actor_device not in ('cuda:0','cuda:1'):raise ValueError('Explicit registered host CUDA device required; no fallback')
    if actor_device=='cuda:1':
        r=ns['Runtime']('nav-push',.2,.6,20,seed,'cuda:1')
    else:
        r=ns['Runtime']('nav-push',.2,.6,20,seed,'cuda:0')
    p=r.sim
    if r.step_count or p.data.time or len(p.queue):raise ValueError('Cold initialization forbidden after ANY main task step')
    # No file of recorded qpos/qvel is consumed. Fresh calibrated INITIAL stance.
    object_qpos=p.data.qpos[25:].copy();original_goal=p.box_push_target.clone()
    p.data.qpos[:3]=[*initial_robot['xy_m'],r.push_reference['height']+initial_surface_height_m]
    yaw=float(initial_robot['yaw_rad']);p.data.qpos[3:7]=[np.cos(yaw/2),0.,0.,np.sin(yaw/2)]
    arm=NATIVE_COMPACT_ARM if initial_arm_reference is None else np.asarray(initial_arm_reference,dtype=float)
    if arm.shape!=(6,) or not np.isfinite(arm).all():raise ValueError('Explicit finite registered INITIAL arm required')
    if initial_arm_reference is not None:
        soft=p.robot.data.soft_joint_pos_limits.numpy()[0][[p.robot.joint_names.index('joint'+str(i)) for i in range(1,7)]]
        limits=p.model.jnt_range[p.jids[12:]]
        if np.any(arm<=np.maximum(soft[:,0],limits[:,0])+.01) or np.any(arm>=np.minimum(soft[:,1],limits[:,1])-.01):
            raise ValueError('New cold-start arm must lie strictly inside existing protected reference domain')
    p.data.qpos[p.qids[:12]]=r.push_reference['joints'][:12];p.data.qpos[p.qids[12:]]=arm
    p.refresh()
    if not np.array_equal(object_qpos,p.data.qpos[25:]) or not np.array_equal(original_goal.numpy(),p.box_push_target.numpy()):
        raise ValueError('Cold robot initialization moved a box or original target')
    pm=r.push['model']
    # Calibrated legs are measured under the native REFERENCE spring target,
    # not an equilibrium under zero PD error. Keep that original leg command;
    # using measured q as the command would remove its weight-support torque.
    initial_command=pm.REFERENCE.copy();initial_command[12:]=arm
    initial_ff=np.zeros(18)
    if initial_arm_reference is not None:
        # A fresh world has no previously issued zero-FF command to preserve.
        # Register its first arm command with measured native gravity support,
        # not a delayed gravity ramp that lets the unloaded arm fall first.
        gravity=p.robot.get_gravity_compensation_forces().numpy()[0]
        initial_ff[12:]=gravity[[p.robot.joint_names.index('joint'+str(i)) for i in range(1,7)]]
        if np.any(abs(initial_ff[12:])>=.9*pm.EFFORT[12:]):raise ValueError('Initial gravity support outside original effort reserve')
    r.last=r.Command(initial_command,np.zeros(18),pm.KP.copy(),pm.KD.copy(),initial_ff)
    if r.sim.queue is not p.queue or len(p.queue):raise ValueError('Motor queue must remain empty before first command')
    receipt.update(static_model_sha256=model_sha256,adapted_runtime_source_sha256=hashlib.sha256(prepared.encode()).hexdigest(),
        initialization_only=True,recorded_dynamic_state_loaded=False,initial_robot=initial_robot,
        initial_surface_height_m=initial_surface_height_m,registered_initial_arm_reference=arm.tolist(),initial_leg_command_is_native_REFERENCE=True,initial_arm_feedforward=initial_ff[12:].tolist(),actor_weights_modified=False,
        native_controller_methods_modified=False,main_motor_steps=0,main_actor_forwards=0,actor_device=actor_device,
        auxiliary_calibration=r.wm_auxiliary_calibration,initial_stability_verified=False)
    return r,receipt
