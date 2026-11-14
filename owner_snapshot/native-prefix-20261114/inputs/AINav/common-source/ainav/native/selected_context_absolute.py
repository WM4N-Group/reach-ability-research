"""MuJoCo-local target view reusing existing explicit NativeTargetContext.

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


def register_candidate_channels(runtime):
    import torch
    p=runtime.sim
    if runtime.step_count!=0 or float(p.data.time)!=0 or len(p.queue):raise ValueError('Register all target channels before first task physics step')
    templates=sorted(n for n in p.scene.sensors if n.startswith('box_contact_'))+['contact_forces']
    mapping={};keys={'light':'box','middle':'wm_object_middle','heavy':'wm_object_heavy'}
    for candidate,key in keys.items():
        if candidate=='light':mapping[candidate]={n:n for n in templates};continue
        body=p.model.body(key);joint=p.model.joint(key+'_free');pos=p.data.xpos[body.id];quat=p.data.xquat[body.id]
        if key in p.scene:raise ValueError('Target channel already registered')
        state=np.r_[pos,quat,np.zeros(6)]
        p.scene[key]=NS(data=NS(default_root_state=torch.tensor(state,dtype=torch.float32)[None]))
        mapping[candidate]={}
        for native in templates:
            name=candidate+'__'+native
            if name in p.scene or name in p.scene.sensors:raise ValueError('Candidate sensor collision')
            sensor=copy.deepcopy(p.scene.sensors[native]);p.scene[name]=sensor;p.scene.sensors[name]=sensor
            mapping[candidate][native]=name
    return dict(schema='native-candidate-contact-matrix-v1',scene_keys=keys,
        source_sensor_names=templates,per_candidate_sensor_names=mapping,
        backend='mujoco',all_selected_channels_from_actual_mujoco_contacts=True,
        native_contact_force_and_strongest_point_rules_unchanged=True,global_aliases_replaced=False)


def make_target_context(runtime,receipt,candidate,*,cfg_overrides=None,declared_push=None):
    import torch
    p=runtime.sim;bridge=runtime.push['bridge'];key=receipt['scene_keys'][candidate]
    if candidate not in ('middle','heavy'):raise ValueError('New candidate only; retired A is not silently rebound')
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
    view.refresh()
    return view,dict(candidate=candidate,scene_key=key,body_id=view.box_id,joint_qpos_adr=view.box_qid,joint_dof_adr=view.box_did,
        explicit_context=context.receipt(),goal=goal,controller_env_is_explicit_context=view.controller.env is context,
        actual_shared_world_and_queue=view.model is p.model and view.data is p.data and view.queue is p.queue,
        A_controller_not_reused=view.controller is not p.controller,
        native_refresh_source_sha256=hashlib.sha256(inspect.getsource(type(p).refresh).encode()).hexdigest(),
        read_only_refresh_derived_from_native=True,registered_cfg_overrides=cfg_overrides,dispatchable=False)



def contact_routing_fixture(runtime,view):
    """Synthetic CPU routing ONLY, not measured force/physics evidence."""
    import mujoco
    from unittest.mock import patch
    p=runtime.sim;bridge=runtime.push['bridge'];original=view.data
    aliases={'base':'base_link','link0':'Piper'};selected=view.box_id
    def geom(body):
        ids=np.flatnonzero(p.model.geom_bodyid==body)
        if not len(ids):raise ValueError('Routing fixture body has no geom')
        return int(ids[0])
    contacts=[];forces=[]
    def add(box,body,force,point):
        contacts.append(NS(geom1=geom(box),geom2=geom(body),frame=np.eye(3).ravel(),pos=np.array(point,dtype=float)))
        forces.append(np.array(force,dtype=float))
    # A's strong hand contact must never become B/C's selected hand contact.
    add(p.box_id,p.model.body('link6').id,[100.,200.,300.],[9.,9.,9.])
    add(selected,p.model.body('link6').id,[1.,0.,0.],[1.,2.,3.])
    add(selected,p.model.body('end_effector').id,[0.,4.,0.],[4.,5.,6.])
    expected={}
    for i,name in enumerate(bridge.box_push.NON_HAND_BODIES):
        force=np.array([i+1.,-.25,.5]);expected[name]=force
        add(selected,p.model.body(aliases.get(name,name)).id,force,[0.,0.,0.])
    fixture=NS(xpos=original.xpos,xquat=original.xquat,qvel=original.qvel,ncon=len(contacts),contact=contacts)
    def contact_force(model,data,index,out):out[:]=0.;out[:3]=forces[index]
    try:
        view.data=fixture
        with patch.object(mujoco,'mj_contactForce',contact_force):view.refresh()
        hand=view.scene.sensors['box_contact_hand'].data
        assert np.array_equal(hand.force_matrix_w.numpy().reshape(3),[1.,4.,0.])
        assert np.array_equal(hand.contact_pos_w.numpy().reshape(3),[4.,5.,6.])
        for name,value in expected.items():
            actual=view.scene.sensors['box_contact_'+name].data.force_matrix_w.numpy().reshape(3)
            assert np.array_equal(actual,value),name
        assert bool(bridge.box_push.forbidden_box_contact(view)[0])
    finally:view.data=original;view.refresh()
    return dict(passed=True,synthetic_CPU_fixture_only=True,new_physics_steps=0,
        selected_hand_and_all_nonhand_channels_checked=1+len(expected),
        strong_unselected_A_hand_excluded=True,native_strongest_selected_hand_point_checked=True,
        native_forbidden_contact_predicate_checked=True,no_fixture_used_as_observation_or_training_data=True)


def preflight(bundle,output):
    """Actual compiled threebox/native-controller CPU admission, zero physics."""
    import mujoco,torch
    from mujoco_zyh.runtime_adapter import construct_runtime
    from mujoco_zyh.scene import IDENTITY
    protocol=json.loads(Path(__file__).parent.joinpath('mujoco_zyh/soft_stall_stow_protocol_v7.json').read_text())
    protocol.update(scenario='nav-nav',scene_recipe='research_threebox',selected_object_id='light',auxiliary_calibration_worlds_allowed=0,auxiliary_calibration_max_sim_seconds=0)
    protocol.pop('probe_physics')
    r,_,construction=construct_runtime(bundle,protocol);p=r.sim
    original_scene_box=p.scene['box'];original_controller=p.controller;original_goal=p.box_push_target.clone()
    before=np.r_[p.data.qpos,p.data.qvel].copy();stamp=float(p.data.time)
    registry=register_candidate_channels(r);results=[]
    original_termination=p.termination
    p.termination=lambda: (_ for _ in ()).throw(AssertionError('Retired A termination was reused by B'))
    original_sensor_ids={name:id(p.scene.sensors[name]) for name in registry['source_sensor_names']}
    for candidate in ('middle','heavy'):
        view,receipt=make_target_context(r,registry,candidate)
        obs=view.observation();flags=view.termination()
        assert obs.shape==(226,) and np.isfinite(obs).all()
        assert view.scene['box'] is p.scene[IDENTITY[candidate]['scene_key']]
        assert view.controller.env.scene['box'] is view.scene['box']
        assert np.allclose(view.box_push_target.numpy()[0],p.data.xpos[view.box_id]+[.6,0.,0.],atol=1e-6)
        assert not np.shares_memory(view.targets,p.targets)
        assert view.history is not p.history and view.controller is not p.controller
        assert view.controller.env.episode_length_buf is not p.episode_length_buf
        assert all(view.scene.sensors[n] is p.scene.sensors[registry['per_candidate_sensor_names'][candidate][n]] for n in registry['source_sensor_names'])
        try:view.physics_step()
        except RuntimeError:pass
        else:raise AssertionError('Candidate view acquired physics authority')
        receipt['contact_routing_fixture']=contact_routing_fixture(r,view)
        receipt.update(observation_shape=list(obs.shape),native_success_failure_and_contact_flags=flags,
            all_native_target_contact_channels=len(registry['source_sensor_names']),consumer_checks_passed=True,
            physics_steps=0,actor_forwards=0,controller_proposals_issued=0)
        results.append(receipt)
    p.termination=original_termination
    assert np.array_equal(before,np.r_[p.data.qpos,p.data.qvel]) and float(p.data.time)==stamp==0 and not p.queue
    assert p.scene['box'] is original_scene_box and p.controller is original_controller and torch.equal(p.box_push_target,original_goal)
    assert all(id(p.scene.sensors[n])==v for n,v in original_sensor_ids.items())
    result=dict(schema='mujoco-explicit-selected-target-preflight-v1',CPU_readers_and_controller_binding_pass=True,
        dispatchable=False,live_B_execution_pass=False,physics_steps=0,WM_forwards=0,training_runs=0,
        source=construction,registered_contacts=registry,targets=results,
        global_A_scene_controller_goal_and_state_unchanged=True,
        reused_existing_helpers=['native_target_context.NativeTargetContext','native_candidate_contact_layout.selected_contact_keys'],
        remaining=['same-episode NAV approach B and support/arm entry admission','200Hz selected/unselected contact hard guard caller','three actual consecutive B controller/observation epochs','B original NN applied-command/goal history and terminal outcome audit','fresh research-threebox RGBD/catalog identity preflight','independent new dispatch protocol/freeze/budget before any B physics'])
    with Path(output).open('x') as f:json.dump(result,f,indent=2)
    print(json.dumps(result))

if __name__=='__main__':
    import argparse
    a=argparse.ArgumentParser(description=__doc__);a.add_argument('--bundle',type=Path,required=True);a.add_argument('--output',type=Path,required=True);p=a.parse_args();preflight(p.bundle,p.output)
