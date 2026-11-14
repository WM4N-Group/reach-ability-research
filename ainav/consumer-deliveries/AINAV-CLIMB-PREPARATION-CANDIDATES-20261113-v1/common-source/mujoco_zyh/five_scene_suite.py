"""Five easy engineering scenes using frozen zyh actors, real terrain and motors.

The user's 2026-10-26 authorization permits engineering joint excursions and a
weak-contact deadband. Original diagnostics remain in every report. This module
never writes a running physical state or clears a motor queue.
"""
import json
import math
from dataclasses import replace
from pathlib import Path
import numpy as np

SCHEMA='piper-mujoco-five-easy-scenes-case-v1'
RESOURCE='/mnt/yuanyue/data/go2-piper-world-model'
PLAN=Path(__file__).with_name('five_scene_plan_v1.json')


def plan(revision=1):
    if revision not in (1,2,3,4,5,6,7,8):raise ValueError('Unregistered scene revision')
    return json.loads(PLAN.with_name(f'five_scene_plan_v{revision}.json').read_text())


def case_protocol(case,revision=1):
    p=json.loads(Path(__file__).with_name('nav_efficiency_protocol_v2.json').read_text())
    p.pop('nav_efficiency_mode');p.pop('NAV_arm_joint5_kd')
    p.update(schema=SCHEMA,source_id=f'five-easy-20261026-v{revision}-'+case['case_id'],
        episode_id=f'five-easy-20261026-v{revision}-'+case['case_id']+'-episode0',
        source_group='five-easy-'+case['case_id'],scene_recipe='easy_engineering_suite',
        scenario='nav-push-climb' if case['family']=='side_platform' else 'box-stairs',
        purpose='Engineering complete-skill feasibility before world-model data collection',
        suite_case=case,seed=3713,delay_ms=20,resource_lock_dir=RESOURCE,
        push_distance_m=case.get('push_distance_m',.6),
        box_height_m=case['platform_height_m'] if case['family']=='side_platform' else .2,
        max_sim_seconds=240,max_wall_seconds=1200,max_payload_bytes=256*1024*1024,
        max_review_state_bytes=64*1024*1024,max_total_episode_bytes=384*1024*1024,
        source_control_algorithms_changed=True,
        review_scope='Easy '+case['case_id']+'; frozen actors, relaxed engineering acceptance, real gap only for bridge cases',
        strict_safety_warning='User-authorized engineering limits: original speed/range excursions recorded; not hardware certification',
        independent_sample=False,training_allowed=False,training_runs=0,WM_forwards=0,WM_control=False)
    if revision>=7:
        collection_revision=1 if revision==7 else 2
        p.update(source_id=f'five-scene-bootstrap-20261026-v{collection_revision}-'+case['case_id'],
            episode_id=f'five-scene-bootstrap-20261026-v{collection_revision}-'+case['case_id']+'-episode0',
            source_group='five-scene-bootstrap-v1-'+case['case_id'],role='train',
            training_allowed=True,forecast_study_training_authorized=True,
            readiness=plan(7)['readiness'],
            purpose='Fresh training-only causal RGBD/action data after five-scene engineering readiness; no held-out evaluation claim')
    if revision!=1:p['suite_revision']=revision
    return p


def validate_protocol(p):
    revision=p.get('suite_revision',1)
    matches=[c for c in plan(revision)['cases'] if p.get('suite_case',{}).get('case_id')==c['case_id']]
    if len(matches)!=1 or p!=case_protocol(matches[0],revision):raise ValueError('Exact preregistered five-scene protocol required')
    active=plan(revision).get('active_case_ids')
    if active is not None and p['suite_case']['case_id'] not in active:raise ValueError('Case outside supplemental budget')
    if p['automatic_retry'] or p['reset_after_initial_allowed'] or not p['full_state_review']:
        raise ValueError('One bounded continuous recorded rollout per new root required')
    return p


def staircase_factory(cls,cfg_cls,distance,config):
    case=config['suite_case']
    cfg=cfg_cls(push_distance=distance,box_length=case['box_length_m'],
                upper_height=case.get('upper_height_m',.4),box_width=case['box_width_m'])
    return cls(cfg)


def configure_scene(runtime,sim,spec,config):
    import mujoco
    c=config['suite_case']
    if c['family']!='side_platform' and not hasattr(runtime,'staircase'):
        from staircase import Staircase,StaircaseConfig
        runtime.staircase=staircase_factory(Staircase,StaircaseConfig,config['push_distance_m'],config)
        runtime.staircase.build(sim)
        runtime.box_y=0.
    geom=spec.geom('push_box_geom')
    geom.mass=c['box_mass_kg'];geom.rgba=[.25,.65,.35,1.]
    if c['family']=='side_platform':
        runtime.box_y=c['push_lane_y_m'];spec.body('push_box').pos=[1.1,runtime.box_y,.1]
        sim.scene['box'].data.default_root_state[0,:3]=sim.box_push_target.new_tensor([1.1,runtime.box_y,.1])
        sim.box_push_target[0,:3]=sim.box_push_target.new_tensor([1.7,runtime.box_y,.1])
        platform=next((g for g in spec.geoms if g.name=='platform'),None)
        if platform is None:
            cfg=runtime.cfg
            platform=spec.worldbody.add_geom(name='platform',type=mujoco.mjtGeom.mjGEOM_BOX,
                pos=[cfg['box_front']+cfg['box_length']/2,0,c['platform_height_m']/2],
                size=[cfg['box_length']/2,c['platform_width_m']/2,c['platform_height_m']/2],
                contype=2,conaffinity=3,friction=[.6,0,0],condim=3)
        platform.size[1]=c['platform_width_m']/2
    elif c['family']=='bridge':
        # Replace the infinite plane at construction, preserving its geom ID.
        # There is a real unsupported opening; the floor below it is -0.6m.
        bank=next(g for g in spec.geoms if g.name=='upper_ground')
        near=c['gap_near_x_m'];far=near+c['gap_width_m']
        ground=spec.geom('ground');ground.type=mujoco.mjtGeom.mjGEOM_BOX
        ground.pos=[(near-12)/2,0,-.3];ground.size=[(near+12)/2,6,.3];ground.group=1
        bank.pos=[far+4,0,-.3];bank.size=[4,6,.3];bank.group=1
        spec.worldbody.add_geom(name='gap_floor',type=mujoco.mjtGeom.mjGEOM_BOX,
            pos=[(near+far)/2,0,-.65],size=[(far-near)/2,6,.05],contype=2,conaffinity=3,
            friction=[.6,0,0],group=1,rgba=[.12,.12,.15,1.])
        if c.get('ramp_entry'):
            length=c['ramp_length_m'];width=c['ramp_width_m'];angle=math.atan2(.2,length)
            y=c['box_width_m']/2+.05+width/2
            spec.worldbody.add_geom(name='bridge_entry_ramp',type=mujoco.mjtGeom.mjGEOM_BOX,
                pos=[length/2,y,.1-.04/math.cos(angle)],
                quat=[math.cos(angle/2),0,-math.sin(angle/2),0],
                size=[length/(2*math.cos(angle)),width/2,.04],group=1,
                contype=2,conaffinity=3,friction=[.8,0,0],rgba=[.45,.45,.5,1.])
            end=c['ramp_landing_end_x_m']
            spec.worldbody.add_geom(name='bridge_entry_landing',type=mujoco.mjtGeom.mjGEOM_BOX,
                pos=[(length+end)/2,y,.1],size=[(end-length)/2,width/2,.1],group=1,
                contype=2,conaffinity=3,friction=[.8,0,0],rgba=[.45,.45,.5,1.])
        # Preserve the native explicit box/upper_ground pair at .15 friction.
        # upper_ground now names the level far-bank slab, at construction only.
    runtime.wm_suite_construction=dict(case=c,initial_construction_only=True,
        real_gap=c['family']=='bridge',source_weights_changed=False)


def tasks(runtime,config):
    c=config['suite_case'];family=c['family']
    if family=='side_platform':
        lane=c['push_lane_y_m']
        return [dict(skill='nav',goal=[-.02,lane]),dict(skill='push'),
                dict(skill='nav',goal=[-.4,lane]),dict(skill='nav',goal=[-.4,0.]),
                dict(skill='nav',goal=[-.08,0.]),dict(skill='climb')]
    if family=='bridge' and c.get('bridge_goal')=='construction_and_stow':
        return [dict(skill='nav',goal=[-.02,0.]),dict(skill='push')]
    if family=='bridge' and c.get('ramp_entry'):
        lane=c['box_width_m']/2+.05+c['ramp_width_m']/2
        return [dict(skill='nav',goal=[-.02,0.]),dict(skill='push'),
                dict(skill='nav',goal=[.1,0.]),dict(skill='nav',goal=[.1,lane]),
                dict(skill='nav',goal=[2.5,lane],surface_profile='ramp'),
                dict(skill='nav',goal=[2.5,0.],surface_height=.2),
                dict(skill='nav',goal=[c['finish_x_m'],0.],surface_height=.2)]
    scene=runtime.staircase;cfg=scene.config
    # Native near-climb is a known failure. Reposition physically to the original
    # 0.83m standoff, then activate the same climb actor from a stationary state.
    front=cfg.box_initial_front+cfg.push_distance
    standoff=c.get('climb_standoff_m',.83)
    route=[dict(skill='nav',goal=[-.02,0.]),dict(skill='push'),
           dict(skill='nav',goal=[front-standoff,0.]),
           dict(skill='climb',surface='box',approach=[front-standoff,0.])]
    if family=='bridge':
        route.append(dict(skill='nav',goal=[c['finish_x_m'],0.],surface_height=.2))
    else:
        route.extend([dict(skill='nav',goal=[cfg.upper_front-.83,0.],surface_height=.2),
                      dict(skill='climb',surface='upper',approach=[cfg.upper_front-.83,0.]),
                      dict(skill='nav',goal=[cfg.upper_front+1.0,0.],surface_height=cfg.upper_height)])
    return route


def install(runtime,config):
    from .nav_efficiency import EfficientNav
    from .failure_capsules import hand_details
    case=config['suite_case'];r=runtime;p=r.sim
    native_make=r.make_nav
    def make(item):
        native=native_make(item)
        # Completion still requires measured position, velocity, tilt and arm
        # stability. Engineering tolerances avoid latching around a tiny goal.
        native.config=replace(native.config,position_tolerance=.15,hold_seconds=.5)
        class TerrainNav(EfficientNav):
            def update(self,state):
                if item.get('surface_profile')=='ramp':
                    surface=float(np.clip(r.sim.data.qpos[0]/case['ramp_length_m'],0.,1.))*.2
                else:surface=item.get('surface_height',0.)
                r.n.ee_command[2]=r.nav_ee_command[2]+surface
                return super().update(state)
        nav=TerrainNav(native);nav.maximum_seconds=40.;nav.maximum_reacquisitions=30
        return nav
    r.make_nav=make
    original_command=r.nav_command
    def nav_command():
        cmd=original_command();kd=cmd.kd.copy();kd[16]=2.5
        return r.Command(cmd.position.copy(),cmd.velocity.copy(),cmd.kp.copy(),kd,cmd.feedforward.copy())
    r.nav_command=nav_command
    r.wm_suite_relaxations=dict(original_joint_speed_and_range_diagnostics_retained=True,
        original_motor_effort_clipping_retained=True,physical_joint_ranges_unchanged=True,
        max_position_excursion_mrad=(None if config.get('suite_revision',1)>=4 else 150. if config.get('suite_revision',1)>=2 else 40.),
        max_speed_multiplier=(None if config.get('suite_revision',1)>=4 else 2.),
        joint_stop_gate_active=config.get('suite_revision',1)<4,weak_contact_force_deadband_N=2.,
        relaxed_weak_contact_samples=0,relaxed_joint_samples=0,engineering_only=True)
    native_termination=p.termination
    def termination():
        flags=native_termination()
        if flags['invalid_hand_contact']:
            d=hand_details(p,r.push['bridge'].box_push)
            geometry=all(bool(d['components'][name][0]) for name in
                         ('finite_point','front_face','height_inside','lateral_inside','near_tip','resisting_axis_ratio_gt_point8'))
            if geometry and float(d['force_norm_N'][0])<2.:
                flags=dict(flags,invalid_hand_contact=False)
                r.wm_suite_relaxations['relaxed_weak_contact_samples']+=1
        return flags
    p.termination=termination
    if hasattr(r,'staircase'):
        # Original docking asks for sustained wall contact. This engineering task
        # asks for actual goal reach and, for bridges, support on BOTH banks.
        def push_ready(sim,settled):
            if not settled:return False
            pos=sim.data.xpos[sim.box_id];rot=sim.data.xmat[sim.box_id].reshape(3,3)
            if abs(math.atan2(rot[1,0],rot[0,0]))>math.radians(10):return False
            if case['family']=='bridge':
                extent=abs(rot)@np.array([case['box_length_m']/2,case['box_width_m']/2,.1])
                near=case['gap_near_x_m'];far=near+case['gap_width_m']
                return bool(pos[0]-extent[0]<near-.05 and pos[0]+extent[0]>far+.05)
            return True
        r.staircase.push_ready=push_ready
    return tasks(r,config)


def after_step(runtime):
    r=runtime;p=r.sim;q=p.data.qpos[p.qids];dq=p.data.qvel[p.dids]
    limits=p.model.jnt_range[p.jids];speed=r.push['model'].SPEED
    excursion=np.maximum(limits[:,0]-q,q-limits[:,1])
    if not np.isfinite(np.r_[p.data.qpos,p.data.qvel]).all():raise RuntimeError('engineering_nonfinite_state')
    if r.wm_suite_relaxations['joint_stop_gate_active']:
        if np.any(excursion>r.wm_suite_relaxations['max_position_excursion_mrad']/1000.) or np.any(abs(dq)>2.*speed):raise RuntimeError('engineering_joint_envelope')
    r.wm_suite_relaxations['relaxed_joint_samples']+=int(np.any(excursion>0) or np.any(abs(dq)>speed))


def endpoint(runtime,config):
    r=runtime;p=r.sim;c=config['suite_case']
    feet=np.array([p.model.body(name+'_foot').id for name in ('FR','FL','RR','RL')])
    loads=p.forces[feet,2];foot=p.data.xpos[feet]
    result=dict(case_id=c['case_id'],family=c['family'],foot_normal_N=loads.tolist(),
        actual_base_xyz_m=p.data.qpos[:3].tolist(),base_speed_m_s=float(np.linalg.norm(p.data.qvel[:3])),
        foot_xyz_m=foot.tolist(),box_xyz_m=p.data.xpos[p.box_id].tolist(),
        measured_loaded_support=bool(np.all(loads>3.)),relaxations=r.wm_suite_relaxations)
    if c['family']=='bridge':
        far=c['gap_near_x_m']+c['gap_width_m'];box=p.data.xpos[p.box_id]
        result.update(real_gap_width_m=c['gap_width_m'],all_feet_beyond_far_bank=bool(np.all(foot[:,0]>far)),
            box_was_actually_pushed=bool(box[0]-(.5+c['box_length_m']/2)>c.get('push_distance_m',.6)-.15))
        if c.get('bridge_goal')=='construction_and_stow':
            import mujoco
            bank_loads=dict(near=0.,far=0.)
            box_geom=p.model.geom('push_box_geom').id
            bank_ids={p.model.geom('ground').id:'near',p.model.geom('upper_ground').id:'far'}
            for contact_index,contact in enumerate(p.data.contact):
                pair={int(contact.geom1),int(contact.geom2)}
                for gid,name in bank_ids.items():
                    if pair=={box_geom,gid}:
                        force=np.zeros(6);mujoco.mj_contactForce(p.model,p.data,contact_index,force)
                        bank_loads[name]+=max(0.,float(force[0]))
            rot=p.data.xmat[p.box_id].reshape(3,3)
            extent=abs(rot)@np.array([c['box_length_m']/2,c['box_width_m']/2,.1])
            spans=bool(box[0]-extent[0]<c['gap_near_x_m']-.05 and box[0]+extent[0]>far+.05)
            result.update(bridge_goal='construction_and_stow',bridge_bank_normal_N=bank_loads,
                          bridge_spans_both_banks=spans,robot_crossing_claimed=False)
            result['passed']=bool(result['measured_loaded_support'] and result['box_was_actually_pushed'] and spans and min(bank_loads.values())>.05)
        else:
            result['passed']=bool(result['measured_loaded_support'] and result['all_feet_beyond_far_bank'] and result['box_was_actually_pushed'])
    else:result['passed']=result['measured_loaded_support']
    return result


def machine_type(native,config):
    if config.get('suite_revision',1)<3 or (config.get('suite_revision',1)>=8 and not config['suite_case']['prepare_climb']):return native
    class PreparedClimbMachine(native):
        def activate(self):
            if self.kind=='climb' and getattr(self,'wm_prepared_climb_index',None)!=self.index:
                from climb_entry import ClimbEntry
                self.wm_prepared_climb_index=self.index
                self.preparation=ClimbEntry(self.r,self.item)
                self.item['approach']=self.preparation.goal.tolist()
                self.item['startup_ramp_seconds']=self.preparation.config.policy_ramp_seconds
                self.item['approach_speed']=self.preparation.config.policy_speed
                self.phase='prepare';self.prepare_started=float(self.r.sim.data.time)
                self.event('prepare_measured_climb_height',skill='climb',goal=self.preparation.goal.tolist(),
                           base_goal_m=self.preparation.base_goal)
                return
            return super().activate()
    return PreparedClimbMachine


def verify_readiness(config):
    if config.get('suite_revision',0)<7:return
    import hashlib
    info=config['readiness'];path=Path(info['path'])
    if hashlib.sha256(path.read_bytes()).hexdigest()!=info['sha256']:raise ValueError('Five-scene readiness manifest changed')
    d=json.loads(path.read_text())
    if not d['all_five_passed'] or len(d['rows'])!=5:raise ValueError('All five scenes must pass before collection')
    for row in d['rows']:
        root=Path(row['root'])
        if hashlib.sha256((root/'report.json').read_bytes()).hexdigest()!=row['report_sha256']:
            raise ValueError('Accepted development report changed')
