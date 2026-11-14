"""Continuous failed-A -> selected-B step -> high platform -> C bridge -> cross.

Frozen actor weights, one physical world/queue. Task-frame adapters only change
explicit targets/predicates; no live world state or global scene alias is written.
"""
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace,ModuleType,MethodType
import hashlib,inspect,json,math,sys,textwrap
import numpy as np
from .scene import IDENTITY
from .resume_nav import NAV_ARM
from .reselect_B import ReselectBRouter,compile_entry_and_machine
from .failure_capsules import hand_details,emit
from .stall_stow import history_sha

SCHEMA='piper-continuous-integrated-course-v1'
EXECUTION_REVISION=16
PLAN=Path(__file__).with_name('integrated_course_plan_v1.json')

def plan():return json.loads(PLAN.read_text())

def protocol(case):
    p=json.loads(Path(__file__).with_name('reselect_B_recorded_protocol_v2.json').read_text())
    p.update(schema=SCHEMA,source_id=f'integrated-course-20261026-v{EXECUTION_REVISION}-'+case['case_id'],
        episode_id=f'integrated-course-20261026-v{EXECUTION_REVISION}-'+case['case_id']+'-episode0',
        source_group='integrated-course-development-'+case['case_id'],
        purpose='Same continuous A-stall/recovery, select B as step, ascend40cm platform, push C across a real gap and CROSS to far bank.',
        scene_recipe='integrated_course',integrated_case=case,integrated_course_mode=True,execution_revision=EXECUTION_REVISION,
        max_sim_seconds=420,max_wall_seconds=2400,max_payload_bytes=384*1024*1024,
        max_review_state_bytes=96*1024*1024,max_total_episode_bytes=512*1024*1024,
        review_scope='FULL continuous A failure / B step /40cm high platform / C bridge / ROBOT CROSSING required',
        review_camera=dict(lookat=[5.,case['lane_y_m']/2,.3],distance=12.5,azimuth=105.,elevation=-30.),
        original_joint_speed_and_range_are_diagnostics=True,extra_joint_stop_gate=False,NAV_actor_command_frame='native_world_z',compact_NAV_arm_hold='actual_issued_reference_PD_FF',CLIMB_takeover_measured_contacts=4,C_stop_reference='measured_loaded_stance_and_COM',NAV_arm_stopped_speed=1.0,NAV_arrival_hold_s=.1,NAV_arrival_speed_m_s=.15,NAV_arrival_yaw_rate_rad_s=1.5,
        native_effort_and_fall_and_collision_stops_retained=True,soft_arm_effort_margin_warning_only=True,
        far_bank_stop=dict(controller='native_whole_body_QP',surface_height_m=.6,foot_center_height_m=.622,base_height_m=.92,COM_xy='measured_footprint_center',blend_seconds=.3,timeout_seconds=10.,stable_seconds=.5),
        registered_materials=dict(A_bottom_mu=.15,B_bottom_mu=.4,C_bottom_mu=case.get('bridge_bottom_mu',.3),C_mass_kg=case.get('bridge_mass_kg',1.),box_foot_mu=.8))
    return p

def validate_protocol(p):
    rows=[c for c in plan()['cases'] if c['case_id']==p.get('integrated_case',{}).get('case_id')]
    if len(rows)!=1 or p!=protocol(rows[0]):raise ValueError('Exact registered full-course case required')
    if p['automatic_retry'] or p['reset_after_initial_allowed'] or p['training_allowed']:raise ValueError('Development only, no resets/retries')
    return p

def layout(case):
    bfront=.5;distance=.6;blen=case['step_length_m'];high_front=bfront+distance+blen
    cfront=high_front+case['bridge_offset_from_high_front_m'];clen=case['bridge_length_m'];far_deck_front=cfront+clen+distance
    far_front=cfront+clen+.35
    return dict(step_initial_center=bfront+blen/2,step_docked_front=bfront+distance,
        high_front=high_front,bridge_initial_front=cfront,bridge_initial_center=cfront+clen/2,
        far_front=far_front,far_deck_front=far_deck_front,near_edge=far_front-case['gap_width_m'],finish_x=far_deck_front+1.)

def configure_scene(runtime,sim,spec,config):
    import mujoco
    c=config['integrated_case'];g=layout(c);lane=c['lane_y_m']
    feet={sim.model.body(n+'_foot').id for n in ('FR','FL','RR','RL')}
    foot_geoms={sim.model.geom(i).name for i in range(sim.model.ngeom) if int(sim.model.geom_bodyid[i]) in feet}
    for geom in spec.geoms:
        if geom.group==1:geom.group=2
    spec.geom('ground').group=1;spec.geom('ground').size=[20.,10.,.1]
    a=spec.geom('push_box_geom');a.mass=20.;a.friction=[.15,0,0];a.group=1
    spec.body('push_box').pos=[1.1,0,.1];runtime.box_y=0.
    for pair in spec.pairs:
        if 'push_box_geom' in (pair.geomname1,pair.geomname2):pair.friction=[.15,.15,0,0,0]
    # The raised near bank ends at a REAL gap; low original ground lies40cm below.
    spec.worldbody.add_geom(name='course_high',type=mujoco.mjtGeom.mjGEOM_BOX,
        pos=[(g['high_front']+g['near_edge'])/2,lane,.2],
        size=[(g['near_edge']-g['high_front'])/2,c['bank_width_m']/2,.2],
        contype=2,conaffinity=3,friction=[.7,0,0],group=1,rgba=[.2,.35,.6,1.])
    end=g['far_deck_front']+3.
    spec.worldbody.add_geom(name='course_far_base',type=mujoco.mjtGeom.mjGEOM_BOX,
        pos=[(g['far_front']+end)/2,lane,.2],size=[(end-g['far_front'])/2,c['bank_width_m']/2,.2],
        contype=2,conaffinity=3,friction=[.7,0,0],group=1,rgba=[.3,.5,.6,1.])
    spec.worldbody.add_geom(name='course_far',type=mujoco.mjtGeom.mjGEOM_BOX,
        pos=[g['far_deck_front']+1.5,lane,.5],size=[1.5,c['bank_width_m']/2,.1],
        contype=2,conaffinity=3,friction=[.7,0,0],group=1,rgba=[.3,.5,.6,1.])
    # The free bridge deck is20cm above near bank; once docked it meets far bank60cm top.
    recipes=[('middle',[g['step_initial_center'],lane,.1],[c['step_length_m']/2,c['step_width_m']/2,.1],.5,config['registered_materials']['B_bottom_mu']),
             ('heavy',[g['bridge_initial_center'],lane,.5],[c['bridge_length_m']/2,c['bridge_width_m']/2,.1],config['registered_materials']['C_mass_kg'],config['registered_materials']['C_bottom_mu'])]
    for candidate,pos,size,mass,bottom_mu in recipes:
        name=IDENTITY[candidate]['body'];body=spec.worldbody.add_body(name=name,pos=pos)
        body.add_freejoint(name=name+'_free')
        geom=body.add_geom(name=name+'_geom',type=mujoco.mjtGeom.mjGEOM_BOX,size=size,mass=mass,
            contype=2,conaffinity=3,condim=3,friction=[bottom_mu,0,0],priority=2,
            group=1,rgba=IDENTITY[candidate]['color'])
        for other in list(spec.geoms):
            if other.name==geom.name or not(other.contype or other.conaffinity):continue
            mu=.8 if other.name in foot_geoms else bottom_mu
            pair=spec.add_pair(geomname1=geom.name,geomname2=other.name,condim=3)
            pair.friction=[mu,mu,0,0,0]
    runtime.wm_integrated_layout=dict(case=c,layout=g,initial_construction_only=True,
        A_mass_kg=20.,B_mass_kg=.5,C_mass_kg=config['registered_materials']['C_mass_kg'],foot_top_friction=.8,
        B_bottom_friction=config['registered_materials']['B_bottom_mu'],C_bottom_friction=config['registered_materials']['C_bottom_mu'],physical_state_writes_after_first_step=0)
    return 12

class Terrain:
    def __init__(self,c):self.case=c;self.g=layout(c)
    def height_at(self,sim,x,y):
        import mujoco
        out=np.empty(np.shape(x));group=np.array([0,1,0,0,0,0],dtype=np.uint8);hit=np.zeros(1,dtype=np.int32)
        for i,(px,py) in enumerate(zip(np.ravel(x),np.ravel(y))):
            d=mujoco.mj_ray(sim.model,sim.data,np.array([px,py,3.]),np.array([0.,0.,-1.]),group,1,-1,hit)
            if d<0:raise RuntimeError('integrated_known_map_missing_surface')
            out.flat[i]=3.-d
        return out
    def climb_geometry(self,sim,surface):
        c,g=self.case,self.g
        if surface in ('B','C'):
            candidate='middle' if surface=='B' else 'heavy';body=sim.model.body(IDENTITY[candidate]['body']).id
            length=c['step_length_m'] if surface=='B' else c['bridge_length_m']
            width=c['step_width_m'] if surface=='B' else c['bridge_width_m']
            return dict(front=float(sim.data.xpos[body,0]-length/2),length=length,width=width,
                base_height=0. if surface=='B' else .4,top=.2 if surface=='B' else .6)
        return dict(front=g['high_front'],length=g['near_edge']-g['high_front'],width=c['bank_width_m'],base_height=.2,top=.4)
    def dock_metrics(self,sim):
        name=sim.model.body(sim.box_id).name;c,g=self.case,self.g
        if name=='wm_object_middle':front=g['high_front'];length=c['step_length_m']
        elif name=='wm_object_heavy':front=g['far_deck_front'];length=c['bridge_length_m']
        else:return dict(selected_A_not_a_step=True)
        extent=float((abs(sim.data.xmat[sim.box_id].reshape(3,3))@np.array([length/2,(c['step_width_m'] if name=='wm_object_middle' else c['bridge_width_m'])/2,.1]))[0])
        return dict(gap_m=float(front-sim.data.xpos[sim.box_id,0]-extent),box_position=sim.data.xpos[sim.box_id].tolist())
    def push_ready(self,sim,settled):
        if not settled:return False
        m=self.dock_metrics(sim)
        return bool(m.get('selected_A_not_a_step') or -.01<=m['gap_m']<=.01)


def frame_classes(r,lane):
    """Translate native task-Y goals/bounds, NOT physical state or sensor poses."""
    native=r.climb['bridge'].ClimbBridge
    replacements={
      'observation':[("-self.data.qpos[1]", "-(self.data.qpos[1]-_wm_lane)"),
                     ("abs(y)<=cfg['box_width']/2", "abs(y-_wm_lane)<=cfg['box_width']/2")],
      'status':[("abs(d.qpos[1])", "abs(d.qpos[1]-_wm_lane)"),
                ("abs(feet[:, 1])", "abs(feet[:, 1]-_wm_lane)")]}
    methods={};receipt={}
    for name,changes in replacements.items():
        original=textwrap.dedent(inspect.getsource(getattr(native,name)));text=original
        for old,new in changes:
            if old not in text:raise ValueError('Pinned climb task frame hook missing:'+old)
            text=text.replace(old,new)
        ns=dict(vars(r.climb['bridge']),_wm_lane=lane);exec(compile(text,'[explicit-climb-task-Y]','exec'),ns)
        methods[name]=ns[name];receipt[name]=dict(original_sha256=hashlib.sha256(original.encode()).hexdigest(),translated_sha256=hashlib.sha256(text.encode()).hexdigest())
    Frame=type('ExplicitLaneClimb',(native,),methods)
    Stop=r.climb['stop'].StopController
    class LaneStop(Stop):
        def on_platform(self,feet):
            local=feet.copy();local[:,1]-=lane
            return super().on_platform(local)
    return Frame,LaneStop,receipt


def weak_flags(view,box,native,effort_limits=None):
    flags=native()
    if flags.get('invalid_hand_contact'):
        d=hand_details(view,box);terms=d['components']
        geom=all(bool(terms[n][0]) for n in ('finite_point','front_face','height_inside','lateral_inside','near_tip','resisting_axis_ratio_gt_point8'))
        if geom and float(d['force_norm_N'][0])<2.:flags=dict(flags,invalid_hand_contact=False)
    if flags.get('arm_effort_safety') and effort_limits is not None:
        actual=np.asarray(view.torque)[12:];limits=np.asarray(effort_limits)[12:]
        if np.isfinite(actual).all() and np.all(abs(actual)<=limits+1e-9):
            flags=dict(flags,arm_effort_safety=False)
            view.wm_original_arm_effort_warning_samples=getattr(view,'wm_original_arm_effort_warning_samples',0)+1
    return flags


def surface_nav_observation(observation,world_command_history,surface):
    if observation.shape!=(210,) or world_command_history.shape!=(3,7):raise ValueError('Pinned native NAV command-history layout changed')
    result=observation.copy()
    result[189+np.arange(3)*7+2]=(world_command_history[:,2]-surface).astype(result.dtype)
    return result


def install(r,config):
    from .nav_efficiency import EfficientNav
    c=config['integrated_case'];r.staircase=Terrain(c)
    old_make=r.make_nav
    def make(item):
        n=old_make(item);n.config=replace(n.config,position_tolerance=.15,hold_seconds=config['NAV_arrival_hold_s'],arm_stopped_speed=config['NAV_arm_stopped_speed'],stopped_speed=config['NAV_arrival_speed_m_s'],stopped_yaw_rate=config['NAV_arrival_yaw_rate_rad_s'])
        nav=EfficientNav(n);nav.maximum_seconds=50.;nav.maximum_reacquisitions=40
        return nav
    r.make_nav=make
    old_nav=r.nav_command
    def command():
        a=old_nav();kd=a.kd.copy();kd[16]=2.5
        return r.Command(a.position.copy(),a.velocity.copy(),a.kp.copy(),kd,a.feedforward.copy())
    r.nav_command=command
    def enter(self,item):
        from staircase import mapped_climb_bridge
        g=self.staircase.climb_geometry(self.sim,item['surface']);Frame,Stop,receipt=frame_classes(self,c['lane_y_m'])
        cfg=dict(self.climb['bridge'].load_contract()['configuration']['task'])
        cfg.update(box_front=g['front'],box_length=g['length'],box_width=g['width'],rear_boundary_x=g['front']-1.25)
        self.cfg=cfg;self.c=mapped_climb_bridge(Frame,self.sim.model,cfg,g,self.staircase,self.seed)
        self.c.data=self.sim.data
        objects={self.sim.model.body(x['body']).id for x in IDENTITY.values()}
        self.c.forbidden=[i for i in self.c.forbidden if i not in objects]
        self.c.forces=self.sim.forces.copy();self.c.history=None
        self.c.actions=(self.last.position[self.inverse]-self.c.reference)/cfg['action_scale'];self.c.actions[12:]=0
        self.c.ready=True;self.c.release_time=0.;self.c.elapsed=0.;self.c.force_history.clear()
        self.c.cfg=dict(self.c.cfg,startup_ramp_seconds=.8,approach_speed=.4)
        if item['surface']=='C':
            class CapturedBridgeStop(Stop):
                def try_handoff(self,clear,confirmed):
                    was_active=self.active
                    super().try_handoff(clear,confirmed)
                    if not was_active and self.active:
                        self.anchors[:]=self.sim.data.xpos[self.sim.feet_ids]
                        self.stand_posture=self.entry_posture.copy()
                        loaded_com=self.sim.data.subtree_com[self.sim.base_id].copy()
                        self.com_goal=loaded_com.copy();self.entry_com_goal=loaded_com.copy();self.stand_com_goal=loaded_com.copy()
                        self.config=replace(self.config,stance_posture_weight=0.)
                        self.qp.config=self.config
            stop_type=CapturedBridgeStop
        else:stop_type=Stop
        self.stop=stop_type(self.c,replace(self.climb['stop'].StopConfig(),takeover_contacts=config['CLIMB_takeover_measured_contacts']));self.wm_climb_frame_receipt=receipt
        self.wm_integrated_climbs=getattr(self,'wm_integrated_climbs',set())|{item['surface']}
    r.climb_enter=MethodType(enter,r)


def translated_finish_type(native,surface):
    class ElevatedFinish(native):
        def __init__(self,sim,config=None):
            super().__init__(sim,config)
            if not np.allclose(self.anchors[:,2],.022):raise ValueError('Pinned native Finish foot-reference hook changed')
            self.anchors[:,2]+=surface
            self.stand_com[2]+=surface
    return ElevatedFinish


class PushSurfaceView:
    def __init__(self,original,surface):
        self.original=original
        native=original['finish'];self.finish=SimpleNamespace(**vars(native))
        self.finish.FinishController=translated_finish_type(native.FinishController,surface)
    def active(self):return self.original.active()
    def __getitem__(self,name):return self.finish if name=='finish' else self.original[name]


def elevated_push_machine(bundle,goal,surface):
    root=Path(bundle)/'switch';e=(root/'push_entry.py').read_text();m=(root/'machine.py').read_text()
    old="self.base_goal=np.array([-.08,runtime.box_y,self.reference['height']])"
    new="self.base_goal=np.array([_wm_goal[0],_wm_goal[1],self.reference['height']+_wm_surface])"
    if e.count(old)!=1:raise ValueError('Native PushEntry translation hook mismatch')
    ep=ModuleType('_wm_integrated_elevated_entry');ep.__file__=str(root/'push_entry.py');ep.__dict__.update(_wm_goal=np.asarray(goal),_wm_surface=surface)
    sys.modules[ep.__name__]=ep;exec(compile(e.replace(old,new),ep.__file__+'[registered-surface-entry]','exec'),ep.__dict__)
    oldm='            from push_entry import PushEntry';newm='            PushEntry = _wm_entry'
    if m.count(oldm)!=1:raise ValueError('Native Machine entry import mismatch')
    mp=ModuleType('_wm_integrated_elevated_machine');mp.__file__=str(root/'machine.py');mp.__dict__['_wm_entry']=ep.PushEntry
    sys.modules[mp.__name__]=mp;exec(compile(m.replace(oldm,newm),mp.__file__+'[registered-entry]','exec'),mp.__dict__)
    return mp.Machine

def compact_hold_command(resume):
    if resume.stage!='RESUME_NAV' or resume.arrival is not None:return resume.wm_original_next_command()
    r,s=resume.r,resume.r.sim;pm=r.push['model']
    if np.max(abs(resume.arm_ref-NAV_ARM))>.002:raise RuntimeError('compact_hold_not_in_verified_capture_domain')
    gravity=s.robot.get_gravity_compensation_forces().numpy()[0]
    gravity=gravity[[s.robot.joint_names.index(f'joint{i}') for i in range(1,7)]]
    new=r.nav_command();new.position[12:]=resume.arm_ref;new.velocity[12:]=0.
    new.kp[12:]=pm.KP[12:];new.kd[12:]=pm.KD[12:];new.feedforward[12:]=gravity
    age=float(s.data.time)-resume.started
    if age<.2:
        from runtime import blend_command
        new=blend_command(r.Command,resume.old_command,new,age/.2)
        new.position[12:]=resume.arm_ref;new.velocity[12:]=0.
        new.kp[12:]=pm.KP[12:];new.kd[12:]=pm.KD[12:];new.feedforward[12:]=gravity
    resume.arm_velocity=np.zeros(6)
    return new


class Prefix(ReselectBRouter):
    def __init__(self,r,native,root,p,bundle):
        super().__init__(r,native,root,p,bundle);self.case=p['integrated_case'];self.resume.registered_goal_xy=np.array([-.08,self.case['lane_y_m']])
        self.resume.wm_original_next_command=self.resume.next_command
        self.resume.next_command=MethodType(compact_hold_command,self.resume)
    @property
    def complete(self):return self.bmachine is not None and self.bmachine.complete
    def bind_B(self):
        from mujoco_selected_target_context import make_target_context
        r,p=self.r,self.r.sim;lane=self.case['lane_y_m']
        self.A_receipt=json.loads(json.dumps(self.resume.report()))
        before=np.r_[p.data.qpos,p.data.qvel].copy();queue=[a.copy() for a in p.queue]
        self.view,self.binding=make_target_context(r,r.wm_candidate_contacts,'middle',cfg_overrides=dict(box_size=(self.case['step_length_m'],self.case['step_width_m'],.2)))
        self.B_original_goal=self.view.box_push_target.clone();Machine,hook=compile_entry_and_machine(self.bundle)
        proxy=SimpleNamespace(**vars(r));proxy.sim=self.view;proxy.box_y=lane;proxy.last=r.last
        proxy.push_enter=MethodType(type(r).push_enter,proxy);self.bound_runtime=proxy;self.binding['caller_hook']=hook
        native=self.view.termination;box=r.push['bridge'].box_push
        self.view_original_termination=lambda:weak_flags(self.view,box,native,r.push['model'].EFFORT)
        self.view.termination=self.B_termination;self.bmachine=Machine(proxy,[dict(skill='push',approach=[-.08,lane])]);self.bmachine.enter()
        self.stage='B_PUSH_PREPARE';r.wm_active_candidate='middle'
        if not np.array_equal(before,np.r_[p.data.qpos,p.data.qvel]) or len(queue)!=len(p.queue) or any(not np.array_equal(a,b) for a,b in zip(queue,p.queue)):raise RuntimeError('B binding changed world or queue')
        self.event('explicit_B_bound_real_dimensions',binding=self.binding)
    def B_termination(self):
        if self.bmachine is not None and self.bmachine.finish is not None:
            return self.view_original_termination()
        return super().B_termination()
    def start_exit(self,successful):
        if not successful:raise RuntimeError('integrated_B_soft_failed_before_step_goal')
        # Continue the ORIGINAL native successful FinishController; no re-entry.
        self.B_result=dict(native_PUSH_goal_reached=True,goal=self.B_original_goal.tolist())
    def after_step(self):
        if not self.stage:return self.resume.after_step()
        r,p=self.r,self.r.sim;self.bound_runtime.last=r.last;self.view.refresh();self.last_two.append(r.last.position.copy())
        if not np.isfinite(np.r_[p.data.qpos,p.data.qvel]).all():raise RuntimeError('integrated_nonfinite_state')
        flags=self.view_original_termination();bad=[k for k,v in flags.items() if k!='box_settled' and v]
        if bad:
            emit(r,'selected_b_hard_guard',view=self.view,extra=dict(native_flags=bad),preserve_primary_failure=True)
            raise RuntimeError('integrated_B_guard:'+','.join(bad))
        self.bmachine.after_step()
        if history_sha(p)!=self.resume.prefix.recovery.retired_history_sha:raise RuntimeError('retired_A_history_changed')
        self.actual_log.write(json.dumps(dict(time_s=float(p.data.time),stage=self.stage,q=p.data.qpos[p.qids].tolist(),dq=p.data.qvel[p.dids].tolist(),B_pose=p.data.xpos[self.view.box_id].tolist()))+'\n')


def prepared_machine(native):
    class Machine(native):
        def activate(self):
            if self.kind=='climb' and getattr(self,'wm_prepared',None)!=self.index:
                from climb_entry import ClimbEntry
                self.wm_prepared=self.index;self.preparation=ClimbEntry(self.r,self.item)
                self.item['approach']=self.preparation.goal.tolist();self.item['startup_ramp_seconds']=.8;self.item['approach_speed']=.4
                self.phase='prepare';self.prepare_started=float(self.r.sim.data.time)
                self.event('integrated_climb_support_prepare',surface=self.item['surface'],base_goal=self.preparation.base_goal)
                return
            return super().activate()
    return Machine

class FarBankStop:
    """Land any swinging foot and brake on the real far deck with native WBC.

    Only references are constructed. The world, actor state, and motor queue
    stay continuous, and the existing native collision guard remains active.
    """
    def __init__(self,r,p):
        from climb_entry import ClimbEntry
        self.r=r;self.p=p;self.phase='far_bank_brake';self.ready=False
        self.native=ClimbEntry(r,dict(surface='C'))
        n=self.native;cfg=p['far_bank_stop']
        n.surface_height=cfg['surface_height_m'];n.base_goal=cfg['base_height_m']
        n.front=layout(p['integrated_case'])['far_deck_front']
        n.anchors[:,2]=cfg['foot_center_height_m']
        n.com_goal[:2]=n.anchors[:,:2].mean(axis=0)
        n.com_goal[2]=r.sim.data.subtree_com[r.sim.base_id,2]+n.base_goal-r.sim.data.qpos[2]
        n.config=replace(n.config,blend_seconds=cfg['blend_seconds'],timeout=cfg['timeout_seconds'],stable_seconds=cfg['stable_seconds'])
        self.stable_age=0.
    def update(self):
        self.native.update()
        good=self.native.ready and endpoint(self.r,self.p)['passed']
        self.stable_age=self.stable_age+.02 if good else 0.
        self.ready=self.stable_age>=self.p['far_bank_stop']['stable_seconds']
    def command(self):return self.native.command()
    def report(self):
        return dict(**self.native.report(),actual_endpoint=endpoint(self.r,self.p),verified_stable_seconds=self.stable_age)


class IntegratedRouter:
    def __init__(self,r,native,root,p,bundle):
        self.r,self.native,self.config,self.bundle=r,native,p,bundle;self.case=p['integrated_case'];self.g=layout(self.case)
        self.prefix=Prefix(r,native,root,p,bundle);self.active=self.prefix;self.stage='A_FAIL_RECOVER_RESELECT_B';self.chunks=[];self.extra_events=[]
        self.view=None;self.cproxy=None;self.complete=False;self.C_binding=None;self.far_stop=None
        self.log=(Path(root)/'integrated-stage-events.jsonl').open('x')
        import machine
        self.Native=prepared_machine(machine.Machine)
    @property
    def phase(self):return self.stage+'/'+self.active.phase
    @property
    def kind(self):return self.active.kind if hasattr(self.active,'kind') else 'startup'
    @property
    def index(self):return len(self.chunks)
    @property
    def events(self):return self.prefix.events+self.extra_events+[e for m in self.chunks for e in m.events]
    @property
    def results(self):return self.prefix.results+[e for m in self.chunks for e in m.results]
    @property
    def switch_metrics(self):return self.prefix.switch_metrics+[e for m in self.chunks for e in m.switch_metrics]
    def event(self,name,**values):
        x=dict(time=float(self.r.sim.data.time),event=name,stage=self.stage,**values);self.extra_events.append(x)
        self.log.write(json.dumps(x)+'\n');self.log.flush();print(x,flush=True)
    def start_chunk(self,tasks,stage):
        self.stage=stage;self.active=self.Native(self.r,tasks);self.chunks.append(self.active);self.active.enter()
        self.event('integrated_owner_changed',tasks=tasks,physical_state_reset=False,queue_cleared=False)
    def bind_C(self):
        from mujoco_selected_target_context import make_target_context
        r=self.r;c=self.case;lane=c['lane_y_m'];goal=[self.g['bridge_initial_front']-.58,lane]
        self.view,self.C_binding=make_target_context(r,r.wm_candidate_contacts,'heavy',cfg_overrides=dict(box_size=(c['bridge_length_m'],c['bridge_width_m'],.2)))
        native=self.view.termination;box=r.push['bridge'].box_push;self.view.termination=lambda:weak_flags(self.view,box,native,r.push['model'].EFFORT)
        self.cproxy=SimpleNamespace(**vars(r));self.cproxy.sim=self.view;self.cproxy.box_y=lane;self.cproxy.last=r.last;self.cproxy.push=PushSurfaceView(r.push,.4)
        self.cproxy.push_enter=MethodType(type(r).push_enter,self.cproxy)
        Machine=elevated_push_machine(self.bundle,goal,.4)
        self.active=Machine(self.cproxy,[dict(skill='push',approach=goal)]);self.chunks.append(self.active);self.stage='C_BRIDGE_PUSH_STOW';self.active.enter()
        r.wm_active_candidate='heavy';self.event('explicit_C_bound_on_high_platform',binding=self.C_binding)
    def update(self):
        if self.cproxy is not None:self.cproxy.last=self.r.last
        if self.view is not None:self.view.refresh()
        if self.cproxy is not None:self.view.target_context._env.common_step_counter=self.r.step_count
        if self.far_stop is not None:
            self.far_stop.update()
            if self.far_stop.ready and not self.complete:
                self.complete=True;self.stage='FAR_BANK_COMPLETE'
                self.event('full_integrated_sequence_complete',parking=self.far_stop.report())
            return
        self.active.update()
        if self.stage=='A_FAIL_RECOVER_RESELECT_B' and self.prefix.view is not None:self.view=self.prefix.view
        if not self.active.complete:return
        lane=self.case['lane_y_m']
        if self.stage=='A_FAIL_RECOVER_RESELECT_B':
            self.view=self.prefix.view
            self.event('B_native_goal_and_original_finish_complete',B_goal=self.prefix.B_original_goal.tolist())
            self.start_chunk([dict(skill='nav',goal=[self.g['step_docked_front']-1.05,lane]),
                dict(skill='climb',surface='B',approach=[self.g['step_docked_front']-1.05,lane]),
                dict(skill='nav',goal=[self.g['high_front']-.95,lane],surface_height=.2),
                dict(skill='climb',surface='HIGH',approach=[self.g['high_front']-.95,lane]),
                dict(skill='nav',goal=[self.g['bridge_initial_front']-.58,lane],surface_height=.4)],'B_STEP_HIGH_PLATFORM')
        elif self.stage=='B_STEP_HIGH_PLATFORM':
            self.event('actual_high_platform_reached');self.bind_C()
        elif self.stage=='C_BRIDGE_PUSH_STOW':
            self.event('bridge_actual_docked_and_stowed',metrics=self.r.staircase.dock_metrics(self.view))
            front=self.g['bridge_initial_front']+.6
            self.start_chunk([dict(skill='nav',goal=[front-1.05,lane],surface_height=.4),
                dict(skill='climb',surface='C',approach=[front-1.05,lane]),
                dict(skill='nav',goal=[self.g['finish_x'],lane],surface_height=.6)],'BRIDGE_CLIMB_AND_CROSS')
        elif self.stage=='BRIDGE_CLIMB_AND_CROSS':
            self.stage='FAR_BANK_BRAKE';self.far_stop=FarBankStop(self.r,self.config)
            self.event('far_bank_actual_landing_brake_started',parking=self.far_stop.report())
    def next_command(self):
        if self.cproxy is not None:self.cproxy.last=self.r.last
        return self.far_stop.command() if self.far_stop is not None else self.active.next_command()
    def after_step(self):
        if self.cproxy is not None:
            self.cproxy.last=self.r.last
            self.view.refresh()
        self.active.after_step()
        if not np.isfinite(np.r_[self.r.sim.data.qpos,self.r.sim.data.qvel]).all():raise RuntimeError('integrated_nonfinite')
        # Explicit selected-object contact authority, with no global alias swap.
        import mujoco
        p=self.r.sim;foot_ids={p.model.body(n+'_foot').id for n in ('FR','FL','RR','RL')}
        objects={p.model.body(v['body']).id:k for k,v in IDENTITY.items()}
        active_surfaces=getattr(self.r,'wm_integrated_climbs',set())
        for i,contact in enumerate(p.data.contact):
            a,b=map(int,p.model.geom_bodyid[[contact.geom1,contact.geom2]])
            selected=a if a in objects else b if b in objects else None
            if selected is None:continue
            robot=b if selected==a else a;ancestor=robot
            while ancestor and ancestor!=p.base_id:ancestor=int(p.model.body_parentid[ancestor])
            if ancestor!=p.base_id:continue
            force=np.zeros(6);mujoco.mj_contactForce(p.model,p.data,i,force)
            if np.linalg.norm(force[:3])<=1.:continue
            target=objects[selected]
            prefix_active=self.stage=='A_FAIL_RECOVER_RESELECT_B'
            if target=='light' and prefix_active:continue  # original A/recovery guards retain authority
            if target=='middle' and prefix_active and self.prefix.stage:continue  # native selected B guards
            if target=='heavy' and self.stage=='C_BRIDGE_PUSH_STOW':continue  # native selected C guards
            if robot not in self.r.c.forbidden and ((target=='middle' and 'B' in active_surfaces) or (target=='heavy' and 'C' in active_surfaces)):continue
            raise RuntimeError('integrated_unselected_or_native_forbidden_contact:'+target)

    def diagnostics(self):
        nav=getattr(self.active,'nav',None)
        return dict(phase=self.phase,abort=self.prefix.resume.prefix.abort,full_task_complete=self.complete,
                    nav=nav.diagnostics() if nav is not None and hasattr(nav,'diagnostics') else None)
    def report(self):
        finish=getattr(self.active,'finish',None)
        return dict(scope='FULL continuous integrated course, crossing required',stage=self.stage,complete=self.complete,prefix=self.prefix.report(),C_binding=self.C_binding,far_bank_stop=self.far_stop.report() if self.far_stop is not None else None,original_C_effort_warning_samples=getattr(self.view,'wm_original_arm_effort_warning_samples',0) if self.view is not None else 0,active_native_finish=finish.report() if finish is not None else None,active_native_stop=self.r.stop.report() if hasattr(self.r,'stop') else None,endpoint=endpoint(self.r,self.config))
    def close(self):self.prefix.close();self.log.close()


def endpoint(r,p):
    c=p['integrated_case'];g=layout(c);s=r.sim;feet=np.array([s.model.body(n+'_foot').id for n in ('FR','FL','RR','RL')])
    loads=s.forces[feet,2];xyz=s.data.xpos[feet]
    out=dict(all_feet_beyond_far_bank=bool(np.all(xyz[:,0]>g['far_deck_front']+.05)),
        all_feet_on_far_height=bool(np.all(abs(xyz[:,2]-.622)<.04)),actual_foot_xyz_m=xyz.tolist(),
        actual_foot_normal_N=loads.tolist(),actual_base_xyz_m=s.data.qpos[:3].tolist(),
        far_front_x_m=g['far_front'],far_deck_front_x_m=g['far_deck_front'],real_gap_width_m=c['gap_width_m'],
        A_failed_goal_retained=s.box_push_target.tolist(),global_A_alias_body_id=int(s.box_id))
    out['passed']=bool(out['all_feet_beyond_far_bank'] and out['all_feet_on_far_height'] and np.all(loads>3.) and np.linalg.norm(s.data.qvel[:3])<.08)
    return out
