"""Generalized copy of the pinned target view: registry rather than B/C IDs.

No global box alias, world pose, queue or A goal/cache is replaced. This module
registers measured-contact software channels, then passes a fresh explicit
context to the SAME native PUSH readers/controller. It cannot step physics.
"""
import copy,hashlib,inspect,json
from pathlib import Path
from types import SimpleNamespace as NS
import numpy as np
from native_target_context import NativeTargetContext
from native_candidate_contact_layout import selected_contact_keys


def register_candidate_channels(runtime,registry):
    """Register any declared cuboid, before physics; original aliases untouched."""
    import torch
    p=runtime.sim
    if runtime.step_count!=0 or float(p.data.time)!=0 or len(p.queue):raise ValueError('Registration before first physics step only')
    registry.verify_compiled(p.model)
    templates=sorted(n for n in p.scene.sensors if n.startswith('box_contact_'))+['contact_forces']
    keys={o.ref:o.body_name for o in registry.objects.values()};mapping={};pending=[]
    for candidate,key in keys.items():
        body=p.model.body(key);p.model.joint(key+'_free')
        if key in p.scene:raise ValueError('No re-registration or global alias replacement')
        mapping[candidate]={n:'ainav_'+candidate+'__'+n for n in templates}
        if any(n in p.scene or n in p.scene.sensors for n in mapping[candidate].values()):raise ValueError('Candidate sensor collision')
        pending.append((candidate,key,body.id))
    for candidate,key,bid in pending:
        state=np.r_[p.data.xpos[bid],p.data.xquat[bid],np.zeros(6)]
        p.scene[key]=NS(data=NS(default_root_state=torch.tensor(state,dtype=torch.float32)[None]))
        for native,name in mapping[candidate].items():
            sensor=copy.deepcopy(p.scene.sensors[native]);p.scene[name]=sensor;p.scene.sensors[name]=sensor
    return dict(schema='native-candidate-contact-matrix-v1',scene_keys=keys,
        source_sensor_names=templates,per_candidate_sensor_names=mapping,
        backend='mujoco',all_selected_channels_from_actual_mujoco_contacts=True,
        native_contact_force_and_strongest_point_rules_unchanged=True,global_aliases_replaced=False,
        retired_candidates=sorted(registry.retired_objects),arbitrary_registered_object_count=True)


def make_target_context(runtime,receipt,candidate,*,cfg_overrides=None,declared_push=None,body_braking_goal_xy_m=None):
    import torch
    p=runtime.sim;bridge=runtime.push['bridge'];key=receipt['scene_keys'][candidate]
    if candidate not in receipt['scene_keys'] or candidate in receipt['retired_candidates']:
        raise ValueError('Only a current registered non-retired target can get a new attempt')
    selected_contact_keys(receipt,candidate=candidate,observed_scene_keys=list(p.scene))
    actual=(runtime.last.position-runtime.push['model'].REFERENCE)/.25
    manager=NS(action=torch.tensor(actual,dtype=torch.float32)[None],prev_action=torch.tensor(actual,dtype=torch.float32)[None],prev_prev_action=torch.tensor(actual,dtype=torch.float32)[None])
    cfg=NS(**vars(p.cfg));cfg.scene=NS(**{k:p.scene[k] for k in receipt['scene_keys'].values()})
    if cfg_overrides:
        if set(cfg_overrides)-{'box_size'}:raise ValueError('Only prospective selected-box dimensions may be overridden')
        size=tuple(cfg_overrides['box_size'])
        if len(size)!=3 or not np.isfinite(size).all() or min(size)<=0:raise ValueError('Invalid registered selected-box size')
        cfg.box_size=size
    if declared_push is not None:
        if (not isinstance(declared_push,dict) or set(declared_push) not in ({'distance_m','declaration_id'},{'distance_m','declaration_id','goal_xy_m'})
                or type(declared_push['distance_m']) not in (int,float)
                or (not any(abs(declared_push['distance_m']-x)<1e-8 for x in (.2,.4,.6,.8)) if 'goal_xy_m' not in declared_push else not 0<declared_push['distance_m']<=.8)
                or not isinstance(declared_push['declaration_id'],str) or not declared_push['declaration_id']):
            raise ValueError('Explicit new-attempt declaration and registered push distance required')
        cfg.push_distance=declared_push['distance_m']  # prospective local copy, before controller construction
    outer=NS(scene=p.scene,cfg=cfg,action_manager=manager,device=p.device,num_envs=1,step_dt=p.step_dt,
        physics_dt=.005,episode_length_buf=torch.zeros(1,dtype=torch.long),common_step_counter=runtime.step_count)
    context=NativeTargetContext(outer,receipt,candidate=candidate)
    class TargetBridge(type(p)):
        def __getattribute__(self,name):
            if name.startswith(('box_push_','transition_')):
                return getattr(object.__getattribute__(self,'target_context'),name)
            return super().__getattribute__(name)
        def __setattr__(self,name,value):
            if name.startswith(('box_push_','transition_')):
                setattr(object.__getattribute__(self,'target_context'),name,value)
            else:object.__setattr__(self,name,value)
        def physics_step(self,*args,**kw):raise RuntimeError('Target view has no physics authority; original Runtime owns world/queue')
    view=object.__new__(TargetBridge)
    object.__setattr__(view,'target_context',context)
    for name,value in vars(p).items():
        if name.startswith(('box_push_','transition_')) or callable(value) or name in ('controller','settled','low_posture','scene','cfg'):continue
        object.__setattr__(view,name,value)
    view.scene=context.scene;view.cfg=context.cfg;view.episode_length_buf=outer.episode_length_buf
    view.box_id=p.model.body(key).id;joint=p.model.joint(key+'_free')
    view.box_qid=int(joint.qposadr[0]);view.box_did=int(joint.dofadr[0])
    view.history=None;view.targets=runtime.last.position.copy();view.applied_commands=actual.copy();view.jacobian_cache=None
    view.min_clearance=float('inf');view.max_arm_ratio=0.
    if view.termination.__self__ is not view or view.observation.__self__ is not view:raise ValueError('Target reader inherited another target bound method')
    # Reuse the exact native measured-contact accumulation body. Omit only the
    # redundant live mj_forward/robot refresh; original Runtime already owns it.
    text=inspect.getsource(type(p).refresh)
    import textwrap
    text=textwrap.dedent(text)
    for line in ('    mujoco.mj_forward(self.model,self.data)\n','    self.robot.refresh()\n'):
        if text.count(line)!=1:raise ValueError('Pinned native refresh hook mismatch')
        text=text.replace(line,'',1)
    namespace=dict(vars(bridge));exec(compile(text,'[native-target-contact-view]','exec'),namespace)
    native_refresh=namespace['refresh']
    def refresh():
        # Read current physical output, never duplicate/clear the motor queue.
        view.torque=p.torque;view.raw_torque=p.raw_torque
        native_refresh(view)
    view.refresh=refresh;view.refresh()
    goal=(context.capture_measured_push_goal() if declared_push is None
          else context.capture_declared_push_goal(**declared_push))
    body_binding=None
    if body_braking_goal_xy_m is not None:
        if declared_push is None or 'goal_xy_m' not in declared_push:
            raise ValueError('Body braking requires an explicitly declared immutable drive goal')
        from .body_braking_reference import BodyBrakingBinding
        body_binding=BodyBrakingBinding(view,bridge.box_push,body_goal_xy_m=tuple(body_braking_goal_xy_m),
            journal=getattr(runtime,'wm_completion_clock_journal',None))
        view.body_braking_reference=body_binding
    path=json.loads((bridge.ROOT/'source/push_skill/runtime/mujoco/deploy/piper_push_safe_approach.json').read_text())
    with runtime.push.active():
        view.controller=bridge.PushArmIK(context,hold_legs_until_ready=True,lock_arm_on_contact=False,
            align_hand_orientation=True,hand_pitch=1.,safe_approach_waypoints=path['waypoints'],
            safe_approach_position_tolerance=path['settle_position_tolerance_rad'],safe_approach_velocity_tolerance=path['settle_velocity_tolerance_rad_s'])
        view.controller.reset(None);context.action_manager.bind('joint_pos',view.controller)
        context.box_push_arm_residual=torch.zeros((1,6));context.box_push_arm_speed_scale=torch.zeros(1)
        view.hand_cfg=view.controller.hand_cfg
        view.mount_cfg=bridge.SceneEntityCfg('robot',body_ids=[view.controller.mount_id]) if hasattr(bridge,'SceneEntityCfg') else p.mount_cfg
        view.settled=bridge.box_push.PushSettled(None,context);view.low_posture=bridge.LowPosture(None,context)
        # Repeated hard-guard reads must not accelerate the stateful success hold.
        # Preserve the original term instance and all other 200Hz hard predicates.
        from .completion_clock import ClockedNativeSettled
        view.settled=ClockedNativeSettled(view.settled,view,
            journal=getattr(runtime,'wm_completion_clock_journal',None))
    view.refresh()
    return view,dict(candidate=candidate,scene_key=key,body_id=view.box_id,joint_qpos_adr=view.box_qid,joint_dof_adr=view.box_did,
        explicit_context=context.receipt(),goal=goal,controller_env_is_explicit_context=view.controller.env is context,
        actual_shared_world_and_queue=view.model is p.model and view.data is p.data and view.queue is p.queue,
        A_controller_not_reused=view.controller is not p.controller,
        native_refresh_source_sha256=hashlib.sha256(inspect.getsource(type(p).refresh).encode()).hexdigest(),
        read_only_refresh_derived_from_native=True,registered_cfg_overrides=cfg_overrides,
        body_braking_reference=body_binding.receipt() if body_binding is not None else None,dispatchable=False)


