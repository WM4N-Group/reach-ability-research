"""T-COMPLEX common original-intent / private-native 200Hz scene driver.

No CLI, credentials, launch authority, implicit world/model creation, policies or
manual task order. Data supplies original writers/resource guard/qualified cold
components. Reach supplies one common-domain public IntentPlanner. Public and
private execution observations are kept strictly distinct.
"""
from pathlib import Path
from dataclasses import replace
import json,math,sys
from complex_scene import load_scene,finite_placements,need

def nav_declarations(scene):
    """Finite new declarations only; rounding is NOT a sensor/goal tolerance."""
    xy=[*map(tuple,scene['public_waypoints_xy_m'])]
    for o in scene['objects']:
        for x in [o['initial_xy_m'][0],*o['allowed_placement_x_m']]:xy.append((x-o['size_m'][0]/2-.58,o['initial_xy_m'][1]))
    g=scene['task']['goal_bounds_xy_m'];goal=((g[0]+g[1])/2,(g[2]+g[3])/2);xy.append(goal)
    unique=[]
    for p in xy:
        p=tuple(round(float(v),12)for v in p)
        if p not in unique:unique.append(p)
    return tuple(dict(target_ref='cx-goal'if p==goal else 'cx-nav-%03d'%i,xy=p)for i,p in enumerate(unique))

class ComplexSceneDriver:
    def __init__(self,components,*,source_root,bundle,root,writer,planner,journal,guard,purpose='T_COMPLEX_COMPARISON'):
        from observability_qualification import validate_planner_purpose,QUALIFICATION_PURPOSE
        validate_planner_purpose(planner,purpose);self.purpose=purpose
        import numpy as np
        from mujoco_zyh import native_behavior_executor as api
        from ainav.native.observation import AcquisitionPublisher
        self.r=components['runtime'];self.scene=components['scene'];self.registry=components['registry'];self.capture=components['capture'];self.observer=components['observer']
        need(self.r.step_count==0 and float(self.r.sim.data.time)==0. and not self.r.sim.queue,'Fresh new-scene driver only, no resume')
        need(callable(journal)and callable(guard),'Data original journal/resource guard')
        self.components=components;self.source_root=Path(source_root).resolve();self.bundle=bundle;self.root=Path(root);self.writer=writer;self.planner=planner;self.journal=journal;self.owner_guard=guard
        if purpose!=QUALIFICATION_PURPOSE:planner.decision_source='reach_finite_public_algorithm'
        self.api=api;self.np=np;self.tick=0;self.loop=None;self.executor=None;self.factory=None;self.coordinator=None;self.execution=None;self.complete=False
        self.prefix=self.capture;self._last_issued=self.r.last.position.copy();self._before=None;self.last_capture_tick=None;self.sequence=0;self.execution_sequence=0
        p=self.r.sim;self._world=(p,p.model,p.data,p.queue,p.controller,p.box_push_target)
        self.navs=nav_declarations(self.scene)
        if purpose==QUALIFICATION_PURPOSE:self.navs=(*self.navs,*planner.viewpoints)
        self.nav_by_ref={v['target_ref']:v['xy']for v in self.navs};need(len(self.nav_by_ref)==len(self.navs),'No duplicate declared NAV reference')
        self.public_body={o['public_ref']:o['body_name']for o in self.scene['objects']}
        self.publisher=AcquisitionPublisher(self.root/'query-observations');self.current_observation=None;self.entity_by_public={};self._entry_specs={}
        from ainav.contracts import canonical
        self.capabilities=canonical(dict(source_ref='T-COMPLEX common source extension of original v6 frozen native skills; not an admission certificate',skills=['NAV','PUSH'],constraints=[
            'Shared finite declared ground NAV and +X PUSH goals only. Listed items are semantic intents, never entry/success permission.',
            'Only same-clock public RGBD/proprio, declared geometry and actual receipts may update nominal planning; unknown is not a measured pose.',
            'Current native entry, original four-foot12N/immutable goal/FF/guard/QP/FIFO/placement/stow gates are mandatory.',
            'Both methods use identical scene/actions/observations/termination. No private actual approach, body pose or offline route is model input.',
            'Final NAV also verifies all required original placements and actual protected-arrival supported stop. Predicted goal is not task completion.']))
        if purpose==QUALIFICATION_PURPOSE:
            self.capabilities=canonical(dict(source_ref='OBSERVATION-ONLY original NAV qualification, not T task or A/B policy',skills=['NAV'],constraints=['Fixed original ground left/right NAV observation study; no PUSH, retries, fake sensor, threshold change or task-success claim.']))
        self._install_common_stow()
        self.owner_guard()
    def _install_common_stow(self):
        # Same current common lower layer for both arms, installed once at zero.
        sys.path.insert(0,str(self.source_root.parent))
        from reach_stow_choice.native_stow_path_binding import bind_to_host,CALLBACK
        allowed={self.source_root/'mujoco_zyh/stall_stow.py',self.source_root/'ainav/native/current_stall_stow.py'}
        modules=[];seen=set()
        for module in tuple(sys.modules.values()):
            path=getattr(module,'__file__',None)
            if path is not None and id(module)not in seen and Path(path).resolve()in allowed:seen.add(id(module));modules.append(module)
        need(any(Path(m.__file__).resolve()==self.source_root/'mujoco_zyh/stall_stow.py'for m in modules),'Actual selected original stow module must already be loaded')
        self.common_choice_records=[];self.common_stow_bindings=[];self._stow_callback_name=CALLBACK;self._stow_allowed=allowed;self._stow_installed={}
        def emit(row):self.journal(row);self.common_choice_records.append(dict(row))
        for module in modules:
            r=bind_to_host(self,module,enabled=True,emit=emit);need(r['installed'],'One actual common source binding required');self.common_stow_bindings.append(dict(path=str(Path(module.__file__).resolve()),**r));self._stow_installed[str(Path(module.__file__).resolve())]=vars(module)[CALLBACK]
    # Reuse the original exact mixed-rate recorder bridge, not a new motor log.
    def _snapshot(self,runtime):
        from ainav.native.course_tools import CourseGuardsAndWriter
        return CourseGuardsAndWriter._snapshot(self,runtime)
    def _write_command(self,issued,physical_tick,time_s):
        from ainav.native.course_tools import CourseGuardsAndWriter
        return CourseGuardsAndWriter._write_command(self,issued,physical_tick,time_s)
    def _write_boundary(self,row):
        from ainav.native.course_tools import CourseGuardsAndWriter
        return CourseGuardsAndWriter._write_boundary(self,row)
    def _native_guards(self):
        self.owner_guard();p=self.r.sim
        for module in tuple(sys.modules.values()):
            path=getattr(module,'__file__',None)
            if path is not None and Path(path).resolve()in self._stow_allowed:
                key=str(Path(path).resolve());need(key in self._stow_installed and vars(module).get(self._stow_callback_name)is self._stow_installed[key],'Common source alias/callback changed or appeared unbound')
        need(all(a is b for a,b in zip((p,p.model,p.data,p.queue,p.controller,p.box_push_target),self._world)),'Original task model/data/FIFO/root aliases changed')
    def _contact_guard(self):
        if self.execution is not None:self.execution['guards']()
        else:
            from ainav.native.registered_guards import check_object_contacts
            check_object_contacts(self.r,self.registry)
    def _after_guard(self):
        try:self._native_guards();self._contact_guard()
        except Exception as e:self._write_boundary(dict(time_s=float(self.r.sim.data.time),event='complex_guard',passed=False,error=str(e)));raise
        self._write_boundary(dict(time_s=float(self.r.sim.data.time),event='complex_guard',passed=True))
    def capture_grid(self):
        from ainav.native.nav_pilot import NavPilot
        return NavPilot.capture_grid(self)
    def _connect_execution(self):
        from native_construction import build_common_execution_after_capture
        from ainav.native.intent_execution import IntentExecutionCoordinator
        from ainav.native.loop import AinavLoop
        self.execution=build_common_execution_after_capture(self.components,source_root=self.source_root,bundle=self.bundle,guard=self.owner_guard,journal=self.journal)
        self.factory=self.execution['factory'];self.executor=self.execution['executor'];self.factory.terminal_target_ref='cx-goal';driver=self
        class ActualCoordinator(IntentExecutionCoordinator):
            def observe(this,option,receipt):
                if this.phase=='interaction'and option.skill=='PUSH'and receipt.status=='succeeded':driver.execution['placements'].record_current(driver.executor,option,receipt)
                return super().observe(option,receipt)
        self.coordinator=ActualCoordinator(planner=self.planner,observe=self.observe_public,catalogue=self.intent_catalogue,judge=self.judge_intent,bind=self.factory.bind_batch,
            snapshot=lambda:self._snapshot(self.r),protection=lambda now:None,journal=self.journal,capability_contract=self.capabilities)
        self.loop=AinavLoop(runtime=self.r,executor=self.executor,planner=self.coordinator,batch_provider=self.coordinator,snapshot=self._snapshot,command_writer=self._write_command,after_step_guard=self._after_guard,journal=self.journal,physical_tick=self.tick)
        self.journal(dict(event='complex_actual_cold_capture_completed',time_s=float(self.r.sim.data.time),actual_steps=self.capture.actual_issued_steps,witness=self.execution['initial_witness'].report(),no_failed_A_owner_claimed=True,model_input=False))
    def observe_public(self,now):
        need(now==float(self.r.sim.data.time),'Actual observation clock');packet,_private=self.observer.capture(self.tick//4,self._last_issued)
        descriptors=self.execution['resolver'].observe(packet,control_tick=self.tick//4,physical_tick=self.tick);self.entity_by_public={};objects=[]
        for d in descriptors:
            body=self.execution['resolver']._observed[d['target_ref']][0]
            aliases=[k for k,v in self.public_body.items()if v==body];need(len(aliases)==1,'Actual original one-to-one current target association')
            alias=aliases[0];self.entity_by_public[alias]=d['target_ref'];p=d['descriptor'];objects.append(dict(target_ref=d['target_ref'],label=alias+'; current original RGBD one-to-one association',bbox_xyxy=p['pixel_bbox_xyxy'],evidence_ref='RGBD:'+d['RGB_sha256']))
        anchors=[dict(target_ref=v['target_ref'],description='fixed task NAV reference, not current measured pose or prescribed route',position_xyz_m=[*v['xy'],0.],uncertainty_xyz_m=[0.,0.,0.])for v in self.navs]
        anchors.extend(dict(target_ref=o['public_ref'],description='declared task object identity and INITIAL blueprint only, not live pose',position_xyz_m=[*o['initial_xy_m'],0.],uncertainty_xyz_m=[0.,0.,0.])for o in self.scene['objects'])
        obs=self.publisher.publish(packet,now=now,descriptors=objects,declared_map=dict(source_ref='shared task declarations; actual private current pose excluded',anchors=anchors),goal=('OBSERVATION-ONLY: fixed original left/right NAV views; no box manipulation or complete-task success'if self.purpose=='OBSERVABILITY_QUALIFICATION_ONLY'else self.scene['task']['instruction']),events=[])
        self.sequence+=1;(self.root/('intent-observation-%04d.json'%self.sequence)).write_text(obs.encoded+'\n');self.current_observation=obs;self.factory.begin_acquisition(obs);return obs
    def intent_catalogue(self,observation):
        from ainav.intents import SkillIntent
        need(observation is self.current_observation,'Same real public acquisition');options=[]
        def add(skill,ref,params):options.append(SkillIntent('cx-intent-%d-%d'%(self.sequence,len(options)),skill,ref,tuple(sorted(params.items()))))
        from observability_qualification import QUALIFICATION_PURPOSE
        if self.purpose==QUALIFICATION_PURPOSE:
            for v in self.planner.viewpoints:add('NAV',v['target_ref'],dict(goal_world_x_m=v['xy'][0],goal_world_y_m=v['xy'][1],surface_height_m=0.))
        else:
            for ref,xy in self.nav_by_ref.items():add('NAV',ref,dict(goal_world_x_m=xy[0],goal_world_y_m=xy[1],surface_height_m=0.))
            for c in finite_placements(self.scene):add('PUSH',c['public_ref'],{k:c[k]for k in('goal_world_x_m','goal_world_y_m','surface_height_m')})
        self.journal(dict(event='semantic_intent_catalogue',time_s=observation.time_s,intents=[dict(skill=o.skill,target_ref=o.target_ref,parameters=dict(o.parameters))for o in options],actual_native_admission_claimed=False,fixed_successor_table=(self.purpose==QUALIFICATION_PURPOSE)));return tuple(options)
    def _blocked(self,intent,now,reason):
        ref=self.journal(dict(event='complex_selected_intent_blocked',time_s=now,intent_sha256=intent.sha256,reason=reason,model_input=False));return 'BLOCKED',reason,ref
    def judge_intent(self,intent,now):
        from ainav.native.behavior_authority import BehaviorOption
        from ainav.native.execution_judge import EntrySpec,EntryState,judge_entry
        from ainav.native.push_support_gate import current_push_source_support
        from ainav.contracts import sha
        from complex_scene import placement_contract
        self.execution_sequence+=1;self._native_guards();self._contact_guard();params=dict(intent.parameters);p=self.r.sim
        try:
            if intent.skill=='NAV':
                need(intent.target_ref in self.nav_by_ref and params==dict(goal_world_x_m=self.nav_by_ref[intent.target_ref][0],goal_world_y_m=self.nav_by_ref[intent.target_ref][1],surface_height_m=0.),'Exact finite public NAV declaration')
                self.factory._current_completed_witness().validate(self.r)
                proof=self.journal(dict(event='skill_execution_judge_ready',time_s=now,intent_sha256=intent.sha256,skill='NAV',original_entry_still_checked_by_factory=True,model_input=False))
                return 'READY',BehaviorOption('cx-NAV-%d'%self.execution_sequence,'NAV',intent.target_ref,intent.parameters,60.,proof),proof
            need(intent.skill=='PUSH','Only declared ground NAV/PUSH task domain')
            candidates=[c for c in finite_placements(self.scene)if c['public_ref']==intent.target_ref and all(params[k]==c[k]for k in('goal_world_x_m','goal_world_y_m','surface_height_m'))];need(len(candidates)==1,'Exact original finite task placement')
            visual=self.entity_by_public.get(intent.target_ref);need(visual is not None,'Current original RGBD association unavailable; no static-pose substitution')
            body=self.public_body[intent.target_ref];o=next(o for o in self.scene['objects']if o['public_ref']==intent.target_ref);bid=p.model.body(body).id;gid=p.model.geom(body+'_geom').id
            current=p.data.xpos[bid];drive=params['goal_world_x_m']+.11-float(current[0]);need(0<drive<=.8,'Original native PUSH drive stroke only')
            need(math.hypot(params['goal_world_x_m']-float(current[0]),params['goal_world_y_m']-float(current[1]))>=.02,'No redundant PUSH or synthetic goal receipt')
            approach=(float(p.data.geom_xpos[gid,0]-p.model.geom_size[gid,0]-.58),float(p.data.geom_xpos[gid,1]));R=p.data.xmat[bid].reshape(3,3);geometry=bool(self.np.allclose(R,self.np.eye(3),rtol=0,atol=.08))
            four=True
            try:current_push_source_support(self.r,self.registry,body,0.)
            except ValueError:four=False
            baseR=p.data.xmat[p.base_id].reshape(3,3);state=EntryState(now,sha(self.api.world_snapshot(self.r)),tuple(map(float,p.data.qpos[:2])),float(self.np.arctan2(baseR[1,0],baseR[0,0])),four,four,bool(self.executor.fatal))
            result=judge_entry(EntrySpec('PUSH',intent.target_ref,approach,0.,True,geometry),state)
            proof=self.journal(dict(event='skill_execution_judgment',intent_sha256=intent.sha256,judgment_sha256=result.sha256,**result.private_record(),model_input=False))
            if result.status=='BLOCKED':return self._blocked(intent,now,'; '.join(result.reasons))
            if result.status=='PREPARE':
                option=BehaviorOption('cx-entry-NAV-%d'%self.execution_sequence,'NAV',intent.target_ref,tuple(sorted(dict(goal_world_x_m=approach[0],goal_world_y_m=approach[1],surface_height_m=0.).items())),60.,proof)
                self.factory.prepare_private_entry_nav(option,result);return 'PREPARE',option,proof
            contract=next(c for c in self.execution['placement_catalogue'].values()if c.target_ref==intent.target_ref and c.public_goal_xy_m==(params['goal_world_x_m'],params['goal_world_y_m']))
            attempt='cx-selected-push-%d'%self.execution_sequence
            goal=self.execution['resolver'].prepare_push(visual,distance_m=drive,attempt_id=attempt,approach_xy=approach,surface_height_m=0.,goal_xy_m=contract.drive_goal_xy_m,body_braking_goal_xy_m=contract.public_goal_xy_m)
            outer=BehaviorOption('cx-PUSH-%d'%self.execution_sequence,'PUSH',intent.target_ref,intent.parameters,60.,proof,attempt_id=attempt,original_push_goal_sha256=goal)
            inner=replace(outer,token=outer.token+'-constructor',target_ref=visual,parameters=tuple(sorted(dict(push_distance_m=drive,surface_height_m=0.).items())))
            self.factory.prepare_public_push(outer,inner,contract);return 'READY',outer,proof
        except (ValueError,KeyError)as error:return self._blocked(intent,now,type(error).__name__+': '+str(error))
    def step_one(self):
        p=self.r.sim;need(abs(float(p.data.time)-self.tick*.005)<1e-7 and self.r.step_count==self.tick,'Actual 200Hz task clock/tick');self.capture_grid();self._before=(float(p.data.time),p.data.qpos[p.qids].copy(),p.data.qvel[p.dids].copy())
        if self.loop is None:
            if self.capture.complete:self._connect_execution();return False
            command=self.capture.command();issued=command.array().copy();before=float(p.data.time)
            try:self.r.step(command)
            finally:
                if float(p.data.time)>before:
                    need(abs(float(p.data.time)-before-.005)<1e-7,'Exactly one original capture step');self.tick+=1
                    try:self._write_command(issued,self.tick,float(p.data.time))
                    finally:
                        try:self.capture.after_step()
                        finally:self._after_guard()
            return True
        self.loop._receipts()  # Actual native terminal receipt first; no new decision after final proof.
        if getattr(self.planner,'awaiting_terminal',False)and self.executor.reported_end and self.executor.last_outcome=='succeeded':
            machine=self.executor.session.machine
            need(getattr(machine,'stop',None)is not None and machine.complete and machine.stop.complete and self.execution['placements'].current_required(),'Nominal goal/NAV alone is not actual task success')
            proof=self.journal(dict(event='complex_original_complete_task_verified',time_s=float(p.data.time),distinct_original_placement_count=len(self.execution['placements'].records),required_reconstructions=self.scene['task']['minimum_distinct_reconstructions'],original_final_NAV_and_supported_stop=True,model_input=False))
            self.planner.confirm_original_task_terminal(evidence_ref=proof);self.complete=True;return False
        try:return self.loop.step_one()
        finally:self.tick=self.loop.physical_tick
