"""Registry-backed original20cm CLIMB; no B/HIGH/C successor or surface table.

Original prepared Machine, ClimbEntry, mapped bridge/lane functions, actor and
StopController are reused. Only selected-runtime geometry/identity and actual
sensor/torque synchronization are adapted; no task state/FIFO/force rewriting.
"""
from dataclasses import dataclass,replace
from types import MethodType,SimpleNamespace as NS


@dataclass(frozen=True)
class ClimbBinding:
    query_sha256:str
    option_sha256:str
    opaque_ref:str
    object_ref:str
    body_name:str
    body_id:int
    source_support_ref:str
    geometry:tuple


def check_climb_native_domain(x,y,geometry):
    import math
    if not all(math.isfinite(float(v)) for v in (x,y,*geometry.values())):raise ValueError('Finite actual native climb geometry required')
    if not geometry['front']-1.25<=x<=geometry['front']+geometry['length']+.5 or abs(y-geometry['lane_y_m'])>1.5:
        raise ValueError('Outside original CLIMB task position bounds')


class _SelectedView:
    def __init__(self,original,body_name):
        self.original=original;self.box_name=body_name;self.box_id=original.model.body(body_name).id
    def __getattr__(self,name):return getattr(self.original,name)


class RegisteredClimbAdapter:
    def __init__(self,runtime,registry,resolver,*,journal,arm_policy='native'):
        self.runtime,self.registry,self.resolver,self.journal=runtime,registry,resolver,journal
        if arm_policy not in ('native','hard_interior_reference_gravity_only','maximin_original_acceptance_gravity_only'):raise ValueError('Explicit reviewed CLIMB arm policy required')
        self.arm_policy=arm_policy;self.used_options=set()
    def bind(self,batch,options,source_support_ref):
        from .scene_registry import RegisteredTerrain
        terrain=RegisteredTerrain(self.registry);targets=self.resolver.targets_for_query(self.runtime,batch.sha256)
        targets={t.target_ref:t for t in targets};bindings={}
        for option in options:
            if option.skill!='CLIMB' or option.attempt_id or option.original_push_goal_sha256 or set(dict(option.parameters))!={'surface_height_m'}:
                raise ValueError('Fresh explicit CLIMB with public SOURCE height only required')
            target=targets.get(option.target_ref)
            if target is None or target.query_sha256!=batch.sha256:raise ValueError('Actual current RGBD climb target required')
            objects=[o for o in self.registry.objects.values() if o.body_name==target.body_name]
            if len(objects)!=1 or objects[0].ref in self.registry.retired_objects:raise ValueError('One nonretired registered climb body required')
            obj=objects[0];height=dict(option.parameters)['surface_height_m']
            if source_support_ref not in self.registry.surfaces or self.registry.surfaces[source_support_ref].top_z_m!=height:
                raise ValueError('Actual declared source support required')
            if self.runtime.sim.model.body(obj.body_name).id!=target.body_id:raise ValueError('Opaque climb association/body ID differs')
            geometry=terrain.climb_geometry(self.runtime.sim,obj.ref,source_surface_height_m=height)
            check_climb_native_domain(*self.runtime.sim.data.qpos[:2],geometry)
            bindings[option.sha256]=ClimbBinding(batch.sha256,option.sha256,option.target_ref,obj.ref,obj.body_name,target.body_id,
                source_support_ref,tuple(sorted(geometry.items())))
        return bindings
    def construct(self,option,binding,witness):
        import numpy as np
        from mujoco_zyh.native_behavior_executor import NativeOptionSession,world_snapshot
        from mujoco_zyh.integrated_course import prepared_machine,frame_classes
        from .scene_registry import RegisteredTerrain
        from .climb_height import MeasuredClimbHeightMachine
        from .registered_guards import check_object_contacts
        import machine
        if option.sha256 in self.used_options or binding.option_sha256!=option.sha256 or binding.opaque_ref!=option.target_ref:
            raise ValueError('Exact unused bound climb option required')
        if witness is None or not callable(getattr(witness,'validate',None)):raise ValueError('Actual live support witness required before CLIMB construction')
        witness.validate(self.runtime);r=self.runtime;p=r.sim;before=world_snapshot(r);terrain=RegisteredTerrain(self.registry);g=dict(binding.geometry)
        if terrain.climb_geometry(p,binding.object_ref,source_surface_height_m=g['base_height'])!=g:raise ValueError('Current selected climb geometry changed')
        view=_SelectedView(p,binding.body_name);proxy=NS(**vars(r));proxy.sim=view
        class SelectedTerrain:
            def climb_geometry(this,sim,ref):
                if ref!=binding.object_ref:raise ValueError('Selected CLIMB cannot change target')
                return terrain.climb_geometry(sim,ref,source_surface_height_m=g['base_height'])
            def height_at(this,sim,x,y):return terrain.height_at(sim,x,y)
        proxy.staircase=SelectedTerrain();sync=dict(last_tick=r.step_count,force_samples=0,frame_receipt=None)
        def enter(this,item):
            from staircase import mapped_climb_bridge
            geometry=this.staircase.climb_geometry(this.sim,item['surface'])
            Frame,Stop,receipt=frame_classes(this,geometry['lane_y_m']);sync['frame_receipt']=receipt
            cfg=dict(this.climb['bridge'].load_contract()['configuration']['task'])
            cfg.update(box_front=geometry['front'],box_length=geometry['length'],box_width=geometry['width'],rear_boundary_x=geometry['front']-1.25)
            this.cfg=cfg;this.c=mapped_climb_bridge(Frame,this.sim.model,cfg,geometry,this.staircase,this.seed);this.c.data=this.sim.data
            # Same primary integrated-tool distinction: environmental bodies are
            # not robot torso/arm fault bodies. Measured forces remain unchanged.
            objects={this.sim.model.body(o.body_name).id for o in self.registry.objects.values()}
            this.c.forbidden=[i for i in this.c.forbidden if i not in objects]
            this.c.forces=this.sim.forces.copy();this.c.history=None
            this.c.actions=(this.last.position[this.inverse]-this.c.reference)/cfg['action_scale'];this.c.actions[12:]=0
            this.c.ready=True;this.c.release_time=0.;this.c.elapsed=0.;this.c.force_history.clear()
            this.c.cfg=dict(this.c.cfg,startup_ramp_seconds=.8,approach_speed=.4)
            sync['last_tick']=r.step_count
            class CapturedObjectStop(Stop):
                def try_handoff(stop,clear,confirmed):
                    was_active=stop.active;super().try_handoff(clear,confirmed)
                    if not was_active and stop.active:
                        stop.anchors[:]=stop.sim.data.xpos[stop.sim.feet_ids];stop.stand_posture=stop.entry_posture.copy()
                        loaded=stop.sim.data.subtree_com[stop.sim.base_id].copy()
                        stop.com_goal=loaded.copy();stop.entry_com_goal=loaded.copy();stop.stand_com_goal=loaded.copy()
                        stop.config=replace(stop.config,stance_posture_weight=0.);stop.qp.config=stop.config
            this.stop=CapturedObjectStop(this.c,this.climb['stop'].StopConfig())
            self.journal(dict(event='registered_climb_original_actor_entered',time_s=float(p.data.time),query_sha256=binding.query_sha256,
                option_sha256=option.sha256,object_ref=binding.object_ref,geometry=geometry,original_takeover_contacts=this.stop.config.takeover_contacts,
                actual_actor_input_size=923,original_lane_source_receipts=receipt,environment_force_rows_not_modified=True,model_input=False))
        proxy.climb_enter=MethodType(enter,proxy);proxy.climb_command=MethodType(type(r).climb_command,proxy)
        native=prepared_machine(machine.Machine)(proxy,[dict(skill='climb',surface=binding.object_ref)])
        measured=MeasuredClimbHeightMachine(native,self.journal)
        if self.arm_policy!='native':
            from .climb_arm_governor import GovernedClimbMachine
            measured=GovernedClimbMachine(measured,r,witness,self.journal,goal_policy=self.arm_policy)
        def refresh():
            if proxy.c is r.c:return
            c=proxy.c;c.data=p.data;c.forces=p.forces.copy();c.applied_torque=p.torque[proxy.inverse].copy();c.raw_torque=p.raw_torque[proxy.inverse].copy()
            if r.step_count<sync['last_tick']:raise RuntimeError('CLIMB force clock regressed')
            if r.step_count>sync['last_tick']:
                if r.step_count!=sync['last_tick']+1:raise RuntimeError('Missing actual CLIMB force samples')
                c.force_history.append(c.forces.copy());sync['force_samples']+=1
            sync['last_tick']=r.step_count
        def guards():
            check_object_contacts(r,self.registry,entered_climb_refs={binding.object_ref})
            reason=native.guard.check(p.data.qpos[p.qids[12:]],allow_hand_contact=False,record=True)
            if reason:raise RuntimeError('Registered CLIMB actual collision:'+reason)
            if proxy.c is not r.c and proxy.stop.failure:raise RuntimeError('Original CLIMB stop:'+proxy.stop.failure)
        wrapper=RegisteredClimbMachine(r,proxy,measured,binding,sync)
        session=NativeOptionSession(r,wrapper,refresh=refresh,check_guards=guards)
        if world_snapshot(r)!=before:raise RuntimeError('CLIMB construction changed actual world/FIFO')
        self.used_options.add(option.sha256);return session


class RegisteredClimbMachine:
    def __init__(self,runtime,proxy,native,binding,sync):
        self.r=proxy;self.global_runtime=runtime;self.native=native;self.binding=binding;self.sync_evidence=sync
    @property
    def tasks(self):return self.native.tasks
    @property
    def complete(self):return self.native.complete
    @property
    def phase(self):return self.native.phase
    @property
    def results(self):return self.native.results
    def enter(self):self.native.enter()
    def update(self):self.native.update()
    def next_command(self):return self.native.next_command()
    def after_step(self):self.native.after_step()
    def report(self):
        return dict(kind='registered_original_climb',complete=bool(self.complete),phase=self.phase,binding=self.binding.__dict__,
            original_stop=self.r.stop.report() if self.r.c is not self.global_runtime.c else None,
            original_climb_preparation=self.native.owner.report() if self.native.owner is not None else None,
            source_height_reference_started=self.native.owner is not None,actual_force_samples=self.sync_evidence['force_samples'],
            original_lane_source_receipts=self.sync_evidence['frame_receipt'],
            arm_governor=self.native.governor_report() if callable(getattr(self.native,'governor_report',None)) else None,model_input=False)


class ActualClimbSupportWitness:
    def __init__(self,runtime,session,executor,registry):
        from .push_stow_witness import require_live_success_boundary
        require_live_success_boundary(runtime,session,executor)
        if not isinstance(session.machine,RegisteredClimbMachine):raise ValueError('Actual original registered CLIMB owner required')
        self.r,self.session,self.registry=runtime,session,registry;self.machine=session.machine
        self.support_ref=self.machine.binding.object_ref;self.height=dict(self.machine.binding.geometry)['top']
        self.observed_time=float(runtime.sim.data.time);self.owner=self.machine
        self.validate(runtime)
    def validate(self,runtime):
        import numpy as np
        if runtime is not self.r or self.machine.r.sim.data is not runtime.sim.data or self.machine.r.sim.queue is not runtime.sim.queue:
            raise ValueError('Actual CLIMB owner belongs to another world/FIFO')
        self.session.sync();self.session.check_guards();c=self.machine.r.c;stop=self.machine.r.stop
        if not self.machine.complete or stop.phase!='success' or stop.failure:raise RuntimeError('Original CLIMB stopped-success owner lost')
        feet=c.data.xpos[c.feet_ids];loads=c.forces[c.feet_ids,2]
        if not bool(stop.on_platform(feet).all()) or min(loads)<stop.config.contact_off or np.max(abs(feet[:,2]-c.height-c.cfg['foot_radius']))>c.cfg['foot_height_tolerance']:
            raise RuntimeError('Actual original CLIMB target support lost')
        return True
    def report(self):return dict(kind='actual_original_CLIMB_stopped_support',support_ref=self.support_ref,surface_height_m=self.height,time_s=self.observed_time,
        original_target_ref=self.machine.binding.opaque_ref,original_stop_verified=True,no_failed_PUSH_or_NAV_or_cold_start_claimed=True,model_input=False)
