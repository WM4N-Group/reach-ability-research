"""Original comprehensive scene + VLM intents + independent entry preparation.

No task successor router: only the chosen skill's own entry can request NAV.
All native actor/session/goal/contact/endpoint checks remain downstream.
"""
from dataclasses import asdict,replace
from types import MappingProxyType
import json,math
from .full_verified_placement import VerifiedPlacementFullCourse
from .course_tools import PublicReference,NotAdmitted
from .behavior_authority import BehaviorOption
from .execution_judge import EntrySpec,EntryState,judge_entry
from .intent_execution import IntentExecutionCoordinator
from ..intents import SkillIntent
from ..contracts import Observation,canonical,sha


class ExecutionJudgedFullCourse(VerifiedPlacementFullCourse):
    def __init__(self,**kwargs):
        super().__init__(**kwargs)
        model=self.planner
        self.capabilities=canonical(dict(source_ref='original frozen actors + independent same-support entry judge; semantic intent catalogue',
            skills=['NAV','PUSH','CLIMB','HOLD'],constraints=[
                'Choose the task, object and interaction skill. These first actions are semantic intents, NOT native motor permission.',
                'Do not learn or manually satisfy trained starting-distance, yaw, arm or foot-load limits. The execution judge positions and rechecks with existing NAV when possible; internal preparation is not task success.',
                'The judge cannot change tasks, push another object to prepare CLIMB, or change support height using NAV. Infer logical support/docking needs from the observations.',
                'PUSH uses a declared absolute placement XY; the same intent keeps its goal across preparation. The private native drive offset never changes the task goal.',
                'A declared cuboid approach reference also identifies that cuboid for a PUSH intent. Actual current RGBD binding is required before any PUSH construction.',
                'CLIMB changes to its declared destination height; current same-height NAV cannot replace climbing. An undocked movable target is not certified support.',
                'Initial geometry is a blueprint, not a current dynamic pose. Actual receipts and relation observations may establish progress; do not invent success.',
                'Reach the original far bank, all four feet loaded and safely stopped. HOLD is the original far-bank stop, not a generic wait.',
                'Native protection overrides intent execution. If preparation is unavailable or exceeds its bound, use the actual rejection feedback to choose another intent; no fixed object sequence exists.']))
        self.coordinator=IntentExecutionCoordinator(planner=model,observe=self.observe_public,catalogue=self.intent_catalogue,
            judge=self.judge_intent,bind=self.bind,snapshot=lambda:self.api.world_snapshot(self.r),protection=self.protection_request,
            journal=self.journal,capability_contract=self.capabilities)
        self.gateway=self.coordinator
        self.planner=self.coordinator  # native authority adapter, not another VLM
        self.intent_sequence=0;self.execution_sequence=0
        self.entry_source_identity=self._entry_source_identity()

    def _entry_source_identity(self):
        from pathlib import Path
        from ..contracts import file_sha
        bundle=Path(self.config['bundle'])
        machine=bundle/'switch/machine.py';entry=bundle/'switch/climb_entry.py'
        text=machine.read_text();in_place=entry.read_text()
        if "np.linalg.norm(p.data.qpos[:2]-goal)>.16 or yaw_error>.25" not in text:
            raise ValueError('Original interaction pose contract changed; review judge before running')
        if 'self.goal=p.data.qpos[:2].copy()' not in in_place:raise ValueError('Original CLIMB in-place preparation changed')
        return dict(original_machine_sha256=file_sha(machine),original_climb_entry_sha256=file_sha(entry),
            original_approach_tolerance_m=.16,original_yaw_tolerance_rad=.25,CLIMB_entry_is_in_place=True)

    def journal(self,row):
        ref=super().journal(row)
        c=getattr(self,'coordinator',None)
        if (c is not None and c.phase=='preparation' and row['event']=='ainav_native_receipt'
            and row['receipt']['status'] in ('succeeded','failed','protected_exit_complete','hard_stop') and self.last_tasks):
            # Public projection only. The primary native journal and actual
            # private options retain all exact commanded XY/receipt identities.
            self.last_tasks[-1]['parameters']={'surface_height_m':dict(self.executor.option.parameters)['surface_height_m']}
            self.last_tasks[-1]['execution_role']='entry_preparation_not_intent_completion'
        return ref

    def observe_public(self,now):
        obs=super().observe_public(now);c=getattr(self,'coordinator',None)
        if c is None:return obs
        value=obs.value
        if c.intent is not None:value['public_state']['skill_status']='Pending task intent '+c.intent.skill+' on '+c.intent.target_ref+'; native preparation is not completion.'
        value['events']+=c.feedback
        result=Observation.create(value)
        (self.root/('intent-observation-%04d.json'%self.sequence)).write_text(result.encoded+'\n')
        return result

    def _supported(self,h):
        try:self._support(h);return True
        except NotAdmitted:return False

    def intent_catalogue(self,observation):
        self.intent_sequence+=1;options=[]
        def add(skill,ref,params):
            options.append(SkillIntent('intent%d-%s-%s'%(self.intent_sequence,skill,ref),skill,ref,tuple(sorted(params.items()))))
        for ref in self.references:
            if not self._supported(ref.surface_height_m):continue
            add('NAV',ref.ref,dict(goal_world_x_m=ref.xy[0],goal_world_y_m=ref.xy[1],surface_height_m=ref.surface_height_m))
            if ref.climb_surface:add('CLIMB',ref.ref,dict(surface_height_m=ref.action_surface_height('CLIMB')))
            if ref.far_bank:
                try:self._entry('HOLD',ref)
                except (NotAdmitted,ValueError):pass
                else:add('HOLD',ref.ref,dict(surface_height_m=.6))
        for body,e in self.entities.items():
            if self._supported(e['initial_bottom']) and not self._dock(body):
                add('PUSH',e['public']+':approach:center',dict(goal_world_x_m=float(e['docked_front']+e['size'][0]/2),
                    goal_world_y_m=float(self.config['integrated_case']['lane_y_m']),surface_height_m=e['initial_bottom']))
        self.journal(dict(event='semantic_intent_catalogue',time_s=observation.time_s,intents=[asdict(x) for x in options],
            actual_native_admission_claimed=False,spatial_native_limits_filtered_from_model=False,fixed_successor_table=False))
        return tuple(options)

    def _blocked(self,intent,now,reason):
        ref=self.journal(dict(event='skill_execution_judge_rejected',intent_sha256=intent.sha256,time_s=now,
            reason=str(reason),model_input=False,physical_failure_claimed=False,original_guards_retained=True))
        return 'BLOCKED',str(reason),ref

    def _freeze_execution_reference(self,ref):
        """Replace the query table, never mutate an immutable prior reference."""
        if self.executor.option is not None and not self.executor.reported_end:
            raise RuntimeError('Cannot replace execution references while a native owner is active')
        previous=self.factory.references
        table=dict(previous);table[ref.ref]=ref
        frozen=MappingProxyType(table)
        self.factory.references=frozen
        self.journal(dict(event='execution_reference_table_frozen',target_ref=ref.ref,
            reference=asdict(ref),immutable_previous_table_not_mutated=True,
            reference_table_sha256=sha({k:asdict(v) for k,v in table.items()}),model_input=False))

    def _native_nav(self,intent,spec,now):
        # This private scoped entry reference may follow actual object geometry.
        # It never enters the model observation/map or semantic intent batch.
        _prepare_goal_xy = tuple(spec.approach_xy)
        _prepare_goal_callback = globals().get('_ainav_selected_climb_prepare_goal')
        if _prepare_goal_callback is not None:
            _prepare_goal_xy = _prepare_goal_callback(self, intent, spec, now)
        ref=PublicReference(intent.target_ref,_prepare_goal_xy,spec.source_height_m,'selected-skill-private-entry-reference')
        self._entry('NAV',ref)
        self._freeze_execution_reference(ref)
        proof=self.journal(dict(event='selected_intent_private_NAV_entry_bound',intent_sha256=intent.sha256,time_s=now,
            goal_xy=list(ref.xy),support_height_m=ref.surface_height_m,source='original selected skill entry reference',model_input=False))
        option=BehaviorOption('entry-NAV-%d'%self.execution_sequence,'NAV',ref.ref,
            tuple(sorted(dict(goal_world_x_m=ref.xy[0],goal_world_y_m=ref.xy[1],surface_height_m=ref.surface_height_m).items())),60.,proof)
        return option

    def judge_intent(self,intent,now):
        self.execution_sequence+=1;p=self.r.sim
        if not isinstance(intent,SkillIntent) or abs(now-float(p.data.time))>1e-7:raise ValueError('Current selected semantic intent required')
        if self.executor.fatal:return self._blocked(intent,now,'native safety revoked')
        try:
            if intent.skill in ('NAV','HOLD'):
                ref=self.refs_by_id[intent.target_ref];self._entry(intent.skill,ref)
                if intent.skill=='NAV':self._freeze_execution_reference(ref)
                proof=self.journal(dict(event='skill_execution_judge_ready',intent_sha256=intent.sha256,time_s=now,
                    skill=intent.skill,original_entry_checked=True,model_input=False))
                return 'READY',BehaviorOption('execute-%d'%self.execution_sequence,intent.skill,intent.target_ref,intent.parameters,60.,proof),proof
            body=None;target_ready=True;geometry_ok=True
            if intent.skill=='CLIMB':
                ref=self.refs_by_id[intent.target_ref]
                if not ref.climb_surface:return self._blocked(intent,now,'reference is not a declared CLIMB target')
                g=self.r.staircase.climb_geometry(p,ref.climb_surface)
                h=float(g['base_height']);goal=tuple(ref.xy)
                if ref.body_name in self.entities:body=ref.body_name;target_ready=bool(self._dock(body))
            else:
                matches=[b for b,e in self.entities.items() if intent.target_ref==e['public']+':approach:center']
                if len(matches)!=1:return self._blocked(intent,now,'no unique registered object for intent')
                body=matches[0];e=self.entities[body];h=e['initial_bottom'];gid=p.model.geom(body+'_geom').id
                front=float(p.data.geom_xpos[gid,0]-p.model.geom_size[gid,0])
                goal=(front-.58,float(p.data.geom_xpos[gid,1]))
                delta=dict(intent.parameters)['goal_world_x_m']+.11-float(p.data.xpos[p.model.body(body).id,0])
                if self._dock(body):return self._blocked(intent,now,'object already at required boundary; no redundant PUSH')
                if not 0<delta<=.8:return self._blocked(intent,now,'requested placement outside original native PUSH stroke')
            if body is not None:
                import numpy as np
                R=p.data.xmat[p.model.body(body).id].reshape(3,3)
                geometry_ok=bool(np.allclose(R,np.eye(3),rtol=0,atol=.08))
            spec=EntrySpec(intent.skill,intent.target_ref,goal,float(h),target_ready,geometry_ok)
            four=True
            if intent.skill=='PUSH':
                from .push_support_gate import current_push_source_support
                try:current_push_source_support(self.r,self.factory.registry,body,h)
                except ValueError:four=False
            state=EntryState(now,sha(self.api.world_snapshot(self.r)),tuple(float(v) for v in p.data.qpos[:2]),
                float(self.r.n.state()[2]),self._supported(h),four,bool(self.executor.fatal))
            result=judge_entry(spec,state)
            proof=self.journal(dict(event='skill_execution_judgment',intent_sha256=intent.sha256,
                judgment_sha256=result.sha256,**result.private_record(),entry_source_identity=self.entry_source_identity,
                actual_private_measurement=dict(time_s=float(p.data.time),base_xy=p.data.qpos[:2].tolist(),
                    base_quat_wxyz=p.data.xquat[p.base_id].tolist(),
                    feet_world_m=p.data.xpos[[p.model.body(n+'_foot').id for n in ('FR','FL','RR','RL')]].tolist(),
                    foot_vertical_load_N=p.forces[[p.model.body(n+'_foot').id for n in ('FR','FL','RR','RL')],2].tolist(),
                    push_source_bounds_xy_m=list(self.factory.registry.surfaces[next(o.initial_support for o in self.factory.registry.objects.values() if o.body_name==body)].bounds_xy_m) if intent.skill=='PUSH' else None)))
            if result.status=='BLOCKED':return self._blocked(intent,now,'; '.join(result.reasons))
            if result.status=='PREPARE':return 'PREPARE',self._native_nav(intent,spec,now),proof
            if intent.skill=='CLIMB':
                ref=self.refs_by_id[intent.target_ref]
                self._entry('CLIMB',ref)
                self._freeze_execution_reference(ref)  # restore interaction semantics after private NAV reference
                option=BehaviorOption('execute-CLIMB-%d'%self.execution_sequence,'CLIMB',intent.target_ref,intent.parameters,60.,proof)
            else:
                self._entry('PUSH',body=body)
                observed=[r for r,b in self.entity_by_ref.items() if b==body]
                if len(observed)!=1:return self._blocked(intent,now,'current RGBD association unavailable for selected object')
                visual=observed[0];params=dict(intent.parameters);attempt='intent-push-%d'%self.execution_sequence
                distance=params['goal_world_x_m']-float(p.data.xpos[p.model.body(body).id,0])
                original_goal=self.resolver.prepare_push(visual,distance_m=distance,attempt_id=attempt,approach_xy=goal,
                    surface_height_m=h,goal_xy_m=(params['goal_world_x_m'],params['goal_world_y_m']))
                option=BehaviorOption('execute-PUSH-%d'%self.execution_sequence,'PUSH',visual,intent.parameters,60.,proof,
                    attempt_id=attempt,original_push_goal_sha256=original_goal)
                self.absolute_mappings[option.sha256]=replace(option,parameters=tuple(sorted(dict(push_distance_m=distance,surface_height_m=h).items())))
                self.journal(dict(event='selected_intent_same_object_RGBD_binding',intent_sha256=intent.sha256,
                    actual_visual_target=visual,native_option_sha256=option.sha256,public_goal_unchanged=True,model_input=False))
            return 'READY',option,proof
        except (NotAdmitted,ValueError,KeyError) as error:
            return self._blocked(intent,now,type(error).__name__+': '+str(error))

    def step_one(self):
        self.coordinator.check_deadline(float(self.r.sim.data.time))
        return super().step_one()
