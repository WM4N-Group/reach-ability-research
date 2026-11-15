"""AINav full-course host: current physical gates, no task-successor router.

Public static geometry describes anonymous cuboids/surfaces, not their intended
roles. Dynamic body identity/pose is executor-private. Only current visual refs,
actual receipts and witnessed relation booleans enter high-level planning.
"""
from dataclasses import asdict, replace
import importlib
import json
from pathlib import Path
from types import MappingProxyType
from .nav_pilot import NavPilot
from .course_tools import PublicReference, NotAdmitted, movement_entry, nav_backend, far_bank_entry
from .full_sessions import CourseSessionFactory
from .full_bindings import CourseBindingResolver, _SOURCES
from .physical_audit import PhysicalCourseHistory, measure_footprints
from .skill_contracts import ENTRY_PREPARATION_CONSTRAINTS
from ..contracts import Observation, ProtectionRequest, canonical, file_sha
from .behavior_authority import BehaviorOption


class FullCourse(NavPilot):
    def __init__(self,**kwargs):
        resolver_class=kwargs.pop('binding_resolver_class',CourseBindingResolver)
        factory_class=kwargs.pop('session_factory_class',CourseSessionFactory)
        push_wrapper_class=kwargs.pop('push_wrapper_class',None)
        super().__init__(**kwargs)
        self.completed=[];self.dispatched=[];self.visited=set();self.last_tasks=[]
        self.epoch=0;self.option_starts={};self.relation_witness={};self.surface_visits=PhysicalCourseHistory()
        self.private_samples=(self.root/'private-physical-samples.jsonl').open('x')
        self.refs_by_id={};self.entity_by_ref={};self.last_descriptors=();self.push_counter=0
        self._latest_public=None;self._last_footprint_tick=None
        c=self.config['integrated_case'];g=self.integrated.layout(c);lane=c['lane_y_m']
        # Native identifiers below are private backend capabilities, NOT model labels.
        self.entities={
          'wm_object_middle':dict(public='cuboid-2',size=[c['step_length_m'],c['step_width_m'],.2],
            initial_front=.5,initial_bottom=0.,surface='B',docked_front=g['step_docked_front']),
          'wm_object_heavy':dict(public='cuboid-3',size=[c['bridge_length_m'],c['bridge_width_m'],.2],
            initial_front=g['bridge_initial_front'],initial_bottom=.4,surface='C',docked_front=g['bridge_initial_front']+.6)}
        refs=[]
        def ref(name,x,y,h,climb='',body='world',far=False):
            refs.append(PublicReference(name,(float(x),float(y)),h,'registered anonymous task geometry',climb,body,far))
        for body,e in self.entities.items():
            for side,dy in (('center',0.),('left',.15),('right',-.15)):
                ref(e['public']+':approach:'+side,e['initial_front']-.58,lane+dy,e['initial_bottom'])
            ref(e['public']+':upper-entry',e['docked_front']-1.05,lane,e['initial_bottom'],e['surface'],body)
        ref('surface-1:entry',g['high_front']-.95,lane,.2,'HIGH')
        for name,dx in (('near',-.7),('middle',-.35),('finish',0.)):
            ref('surface-2:'+name,g['finish_x']+dx,lane,.6,far=name=='finish')
        self.references=tuple(refs);self.refs_by_id={x.ref:x for x in refs}
        modules={n:importlib.import_module(n) for n in _SOURCES}
        sources={n:file_sha(m.__file__) for n,m in modules.items()}
        self.resolver=resolver_class(self.r,proposals=modules['visual_box_proposals'],
            geometry=modules['native_visual_target_binding'],contexts=modules['mujoco_selected_target_context'],
            native_api=self.api,native_history_sha=self.stall.history_sha,source_sha256=sources)
        self.factory=factory_class(runtime=self.r,bundle=self.config['bundle'],resolver=self.resolver,
            api=self.api,integrated=self.integrated,monitor=self.monitor,prefix=self.prefix,root=self.root,
            references=self.references,guards=self._native_guards)
        from .absolute_push import AbsolutePushFactory
        self.absolute_mappings={}
        self.factory.push=(push_wrapper_class or AbsolutePushFactory)(self.factory.push,self.absolute_mappings,self.journal)
        self.executor=self.api.NativeOptionExecutor(self.r,self.factory,self.journal);self.factory.executor=self.executor
        self.capabilities=canonical(dict(source_ref='original frozen NAV/PUSH/CLIMB/Stop skill library; anonymous geometry below',
            skills=['NAV','PUSH','CLIMB','EXIT_PUSH','RECOVER','HOLD'],constraints=[
              'Reach the original far bank with four feet loaded and stop. Ground navigation alone does not solve the task.',
              'All first actions have current native entry eligibility, not guaranteed success. Prefer validated task progress over redundant navigation.',
              'Use short, noncyclic goal-oriented plans. Do not reward repeated viewpoints that add no new evidence.',
              *ENTRY_PREPARATION_CONSTRAINTS,
              'PUSH may specify either relative push_distance_m, OR absolute goal_world_x_m/goal_world_y_m. Absolute goals are public placement coordinates, not current private poses. Native binding computes its private actuator delta once before selection; the frozen goal is never rebased.',
              'Prefer a declared placement target when the needed spatial relation is clear; partial relative pushes can leave an uncertain remaining gap.',
              'PUSH distances are relative displacements of the selected current object; a new attempt cannot rebase an existing goal.',
              'Initial object geometry is a declared blueprint, NOT a current live pose. Current dynamic pose is unknown unless a real relation/receipt proves it.',
              'A witnessed native docking relation permits support use; success of a short PUSH alone does not prove docking.',
              'NAV ground .0, object upper face .2, platform .4 and upper object/far-bank .6 are distinct support layers. CLIMB changes support, NAV cannot teleport between layers.',
              'CLIMB goes to the declared surface; parameters name destination height, not current source height. Only current native-admitted actions can be first.',
              'HOLD is only the native far-bank stop, never a generic ground wait. Mandatory protection is not a task choice.',
              'The original failed initial object cannot be assigned a new PUSH controller; do not return to it without a feasible useful reason. Its failure is not global proof of immovability.',
              'Long cuboids may span gaps; short lower surfaces can provide intermediate support. Infer object use from geometry and visual evidence, not colors or hidden body IDs.']))
        self.gateway.capability_contract=self.capabilities
        self.gateway.protection_provider=self.protection_request
        self.gateway.observe_public=self.observe_public
        self.gateway.admitted_options=self.catalogue
        self.gateway.bind_native=self.bind

    def _dock(self,body):
        from types import SimpleNamespace
        p=self.r.sim;bid=int(p.model.body(body).id)
        m=self.r.staircase.dock_metrics(SimpleNamespace(model=p.model,data=p.data,box_id=bid))
        return -.01<=m['gap_m']<=.01

    def journal(self,row):
        ref=self.primary_journal(row)
        if row['event']=='ainav_native_admitted':
            option=self.executor.option
            self.option_starts[option.sha256]=self.r.sim.data.xpos[self.r.sim.base_id].copy()
            self.dispatched.append(dict(time_s=float(self.r.sim.data.time),option=asdict(option)))
        elif row['event']=='ainav_native_receipt' and row['receipt']['status'] in ('succeeded','failed','protected_exit_complete','budget_expired'):
            option=self.executor.option;status=row['receipt']['status']
            if status in ('succeeded','protected_exit_complete'):
                self.completed.append(dict(option=asdict(option),receipt=row['receipt']))
                self.visited.add((option.skill,option.target_ref,option.parameters,self.epoch))
                if option.skill in ('PUSH','CLIMB','EXIT_PUSH','RECOVER'):
                    self.epoch+=1
            if status!='budget_expired':
                self.last_tasks.append(dict(skill=option.skill,target=option.target_ref,parameters=dict(option.parameters),
                    actual_status=status,evidence_ref=row['receipt']['evidence_ref']))
                self.last_tasks=self.last_tasks[-5:]
        return ref

    def _static_map(self):
        c=self.config['integrated_case'];g=self.integrated.layout(c);lane=c['lane_y_m'];anchors=[]
        def add(id,description,xyz,unc=(0.,0.,0.)):
            anchors.append(dict(target_ref=id,description=description,position_xyz_m=list(xyz),uncertainty_xyz_m=list(unc)))
        add('cuboid-1:retired','The ORIGINAL failed object at the initial approach; its PUSH is retired. cuboid-2 and cuboid-3 are different objects and have not failed initially.',[1.1,0.,.2])
        add('surface-1','Fixed platform: x=[%.3f,%.3f], y center %.3f, width %.3f, top z=.4. Gap to next bank is %.3fm.'%(g['high_front'],g['near_edge'],lane,c['bank_width_m'],c['gap_width_m']),[g['high_front'],lane,.4])
        add('surface-2','Fixed far bank: starts x=%.3f, top z=.6, width %.3f. All four feet must cross and remain supported.'%(g['far_deck_front'],c['bank_width_m']),[g['far_deck_front'],lane,.6])
        for body,e in self.entities.items():
            add(e['public']+':initial','INITIAL blueprint only, NOT current pose: cuboid length/width/height=%s, front x=%.3f, bottom z=%.1f. Current native adjacent-boundary predicate=%s.'%(e['size'],e['initial_front'],e['initial_bottom'],self.relation_witness.get(e['public'],'unknown')),
                [e['initial_front']+e['size'][0]/2,lane,e['initial_bottom']+.1])
        for r in self.references:
            description='Declared skill reference: NAV source/support z=%.1f'%r.surface_height_m
            if r.climb_surface:description+='; CLIMB destination z=%.1f (requires actual admissible entry and support)'%r.action_surface_height('CLIMB')
            if r.far_bank:description+='; native final HOLD is available only when actually loaded on the far bank'
            add(r.ref,description,[*r.xy,r.surface_height_m])
        return dict(source_ref='original anonymous geometry blueprint and witnessed current relation booleans; no dynamic poses',anchors=anchors)

    def observe_public(self,now):
        packet,private=self.observer.capture(self.tick//4,self._last_issued)
        self.sequence+=1;d=self.root/('query-private-%04d'%self.sequence);d.mkdir()
        (d/'catalog.json').write_text(json.dumps(private,indent=2)+'\n')
        descriptors=self.resolver.observe(packet,control_tick=self.tick//4,physical_tick=self.tick)
        self.last_descriptors=descriptors;self.entity_by_ref={}
        public=[]
        for desc in descriptors:
            ref=desc['target_ref'];body=self.resolver._observed[ref][0];geometry=desc['descriptor']
            label='observed '+geometry['appearance_family']+' cuboid/region; exact current geometry unknown'
            if body in self.entities:
                e=self.entities[body];self.entity_by_ref[ref]=body
                self.relation_witness[e['public']]=bool(self._dock(body))
                label=e['public']+'; dimensions '+str(e['size'])+'; adjacent-boundary='+str(self._dock(body))
            if body=='push_box':label='cuboid-1: ORIGINAL failed/retired object; no new PUSH or CLIMB backend. This is NOT cuboid-2 or cuboid-3.'
            public.append(dict(target_ref=ref,label=label,bbox_xyxy=geometry['pixel_bbox_xyxy'],evidence_ref=str(d/'association.json')))
        (d/'association.json').write_text(json.dumps(dict(descriptors=descriptors,private_binding_provenance=self.resolver.private_provenance),indent=2)+'\n')
        # Native support predicate is categorical skill eligibility, not GT pose.
        state='Actual recent outcomes: '+json.dumps(self.last_tasks[-3:],separators=(',',':'))
        support=[]
        for h in (0.,.2,.4,.6):
            try:self._support(h);support.append(h)
            except NotAdmitted:pass
        obs=self.publisher.publish(packet,now=now,descriptors=public,declared_map=self._static_map(),
            goal='Reach the original far bank, all four feet loaded on it and stop safely. Create a path using object interaction if needed; do not merely tour viewpoints.',
            public_status=dict(task_status=state[:1000],support_surface='Current native-admissible support height(s) m: '+str(support)),
            events=[dict(kind='completion' if self.last_tasks else 'failure',description=(state[:1800] if self.last_tasks else
                'Initial native PUSH failed, and required protected stow completed. Cause is contextual, not global immovability.'),evidence_ref='actual-native-prefix.json' if not self.last_tasks else self.last_tasks[-1]['evidence_ref'])])
        self._latest_public=obs
        return obs

    def _support(self,height):
        p=self.r.sim;np=self.np;ids=[p.model.body(n+'_foot').id for n in ('FR','FL','RR','RL')]
        xyz=np.asarray(p.data.xpos[ids]);loads=np.asarray(p.forces[ids,2])
        if (not np.isfinite(xyz).all() or not np.isfinite(loads).all() or np.count_nonzero(loads>3.)<3
                or not np.all(abs(xyz[:,2]-(height+.022))<.08)):
            raise NotAdmitted('Actual original support-surface domain unavailable')

    def _entry(self,skill,ref=None,body=None):
        p=self.r.sim;np=self.np;lane=self.config['integrated_case']['lane_y_m']
        h=(ref.surface_height_m if ref else self.entities[body]['initial_bottom'])
        self._support(h)
        if skill=='NAV':
            if nav_backend(self.r,h)=='compact_nav':
                owner=self.factory._completed_compact_owner()
                # Exact original ProtectedStow face-retreat envelope, evaluated
                # on the declared NAV goal before selection. Not a task route:
                # this applies to any retained compact-arm owner and target.
                s=owner.s;axis=np.asarray(s.data.xmat[s.box_id]).reshape(3,3)[:,0]
                goal=np.asarray([ref.xy[0],ref.xy[1],p.data.qpos[2]])
                gap=float(np.dot(s.data.xpos[s.box_id]-goal,axis)-.6)
                retreat=max(.08,.645-gap)
                if retreat>.18:raise NotAdmitted('Declared NAV goal outside original protected-arrival face-retreat envelope')
            else:movement_entry(self.r)
        elif skill=='CLIMB':
            geometry=self.r.staircase.climb_geometry(p,ref.climb_surface)
            root=np.asarray(p.data.xpos[p.base_id])
            if not geometry['front']-1.25<=root[0]<=geometry['front']-.25 or abs(root[1]-lane)>geometry['width']/2-.15:
                raise NotAdmitted('Actual native CLIMB entry domain unavailable')
            if ref.body_name in self.entities and not self._dock(ref.body_name):raise NotAdmitted('Actual object not docked')
        elif skill=='PUSH':
            if self._dock(body):raise NotAdmitted('Native adjacent boundary already reached; no overshoot')
            e=self.entities[body];gid=p.model.geom(body+'_geom').id;front=float(p.data.geom_xpos[gid,0]-p.model.geom_size[gid,0])
            root=np.asarray(p.data.xpos[p.base_id])
            if not front-1.25<=root[0]<=front-.25 or abs(root[1]-lane)>.25:
                raise NotAdmitted('Actual native PUSH entry domain unavailable')
        elif skill=='HOLD':far_bank_entry(self.r,self.config,self.integrated)

    def catalogue(self,obs):
        options=[];rejected=[]
        for r in self.references:
            for skill in ('NAV','CLIMB','HOLD'):
                if skill=='CLIMB' and not r.climb_surface or skill=='HOLD' and not r.far_bank:continue
                params={'surface_height_m':r.action_surface_height(skill)}
                if skill=='NAV':params.update(goal_world_x_m=r.xy[0],goal_world_y_m=r.xy[1])
                pairs=tuple(sorted(params.items()))
                if (skill,r.ref,pairs,self.epoch) in self.visited:continue
                try:self._entry(skill,r)
                except (NotAdmitted,ValueError) as error:
                    rejected.append(dict(skill=skill,target_ref=r.ref,reason=str(error)));continue
                proof=self.journal(dict(event='native_current_entry_admitted',skill=skill,target_ref=r.ref,time_s=obs.time_s,model_input=False))
                options.append(BehaviorOption('q%d-%s-%s'%(self.sequence,skill,r.ref),skill,r.ref,pairs,60.,proof))
        # Prospective software attempts are sealed BEFORE selection, no physics.
        self.absolute_mappings.clear()
        for ref,body in self.entity_by_ref.items():
            try:self._entry('PUSH',body=body)
            except (NotAdmitted,ValueError) as error:
                rejected.append(dict(skill='PUSH',target_ref=ref,reason=str(error)));continue
            e=self.entities[body];g=self.r.staircase.climb_geometry(self.r.sim,e['surface'])
            private_xy=(float(g['front'])-.58,self.config['integrated_case']['lane_y_m'])
            for distance in (.2,.4,.6):
                self.push_counter+=1;attempt='ainav-q%d-push%d'%(self.sequence,self.push_counter)
                goal=self.resolver.prepare_push(ref,distance_m=distance,attempt_id=attempt,
                    approach_xy=private_xy,surface_height_m=e['initial_bottom'])
                proof=self.journal(dict(event='native_current_entry_admitted',skill='PUSH',target_ref=ref,time_s=obs.time_s,model_input=False))
                options.append(BehaviorOption('q%d-push%d'%(self.sequence,self.push_counter),'PUSH',ref,
                    tuple(sorted(dict(surface_height_m=e['initial_bottom'],push_distance_m=distance).items())),60.,proof,
                    attempt_id=attempt,original_push_goal_sha256=goal))
            # Generic placement targets: the far face of this cuboid aligns
            # with a declared fixed-surface front. All pairs are considered;
            # only the original forward-bounded native workspace is admitted.
            c=self.config['integrated_case'];layout=self.integrated.layout(c)
            for front in (layout['high_front'],layout['far_deck_front']):
                public_xy=(float(front-e['size'][0]/2),float(c['lane_y_m']))
                current=float(self.r.sim.data.xpos[self.r.sim.model.body(body).id,0])
                delta=public_xy[0]-current
                if not 0<delta<=getattr(self.resolver,'maximum_public_delta',.8):continue
                self.push_counter+=1;attempt='ainav-absolute-q%d-%d'%(self.sequence,self.push_counter)
                goal=self.resolver.prepare_push(ref,distance_m=delta,attempt_id=attempt,
                    approach_xy=private_xy,surface_height_m=e['initial_bottom'],goal_xy_m=public_xy)
                proof=self.journal(dict(event='native_public_absolute_PUSH_target_admitted',
                    target_ref=ref,public_target_xy_m=list(public_xy),model_input=False,private_displacement_not_published=True))
                outer=BehaviorOption('q%d-absolute%d'%(self.sequence,self.push_counter),'PUSH',ref,
                    tuple(sorted(dict(goal_world_x_m=public_xy[0],goal_world_y_m=public_xy[1],surface_height_m=e['initial_bottom']).items())),
                    60.,proof,attempt_id=attempt,original_push_goal_sha256=goal)
                inner=replace(outer,parameters=tuple(sorted(dict(push_distance_m=delta,surface_height_m=e['initial_bottom']).items())))
                self.absolute_mappings[outer.sha256]=inner;options.append(outer)
        self.journal(dict(event='full_native_catalogue',time_s=obs.time_s,admitted=[asdict(x) for x in options],
                          rejections=rejected,model_input=False,fixed_successor_table=False))
        if not options:raise NotAdmitted('No physically admitted current action; no scripted fallback')
        return tuple(options)

    def protection_request(self,now):
        ex=self.executor
        if ex.option is None or ex.last_outcome not in ('failed','budget_expired'):return None
        option=ex.option
        if option.skill!='PUSH':return None
        if dict(option.parameters)['surface_height_m']!=0.:
            raise NotAdmitted('High-deck active PUSH exit not yet proven; stop rather than bypass')
        # Native owner cannot be replaced; retained original goal/history exit.
        proof=self.journal(dict(event='native_mandatory_PUSH_exit',time_s=now,attempt_id=option.attempt_id,
                                original_push_goal_sha256=option.original_push_goal_sha256,model_input=False))
        safe=BehaviorOption('protected-exit-'+option.attempt_id,'EXIT_PUSH',option.target_ref,
            option.parameters,60.,proof,attempt_id=option.attempt_id,
            original_push_goal_sha256=option.original_push_goal_sha256,mandatory_protection=True)
        return ProtectionRequest('ainav-safety-'+option.attempt_id,now,safe,proof)

    def _contact_guard(self):
        try:return super()._contact_guard()
        except Exception:
            import mujoco
            p=self.r.sim;contacts=[]
            for i,c in enumerate(p.data.contact):
                names=[p.model.geom(int(g)).name for g in (c.geom1,c.geom2)]
                force=self.np.zeros(6);mujoco.mj_contactForce(p.model,p.data,i,force)
                if self.np.linalg.norm(force[:3])<=1.:continue
                contacts.append(dict(geoms=names,bodies=[p.model.body(int(p.model.geom_bodyid[g])).name for g in (c.geom1,c.geom2)],
                    actual_contact_force_N=float(self.np.linalg.norm(force[:3]))))
            machine=self.executor.session.machine if self.executor.session is not None else None
            diagnostic=dict(time_s=float(p.data.time),actual_native_phase=getattr(machine,'phase',None),
                actual_native_surface=getattr(machine,'item',{}).get('surface') if machine is not None else None,
                actual_entered_surfaces=list(getattr(self.r,'wm_integrated_climbs',set())),
                actual_forbidden_bodies=[p.model.body(int(x)).name for x in self.r.c.forbidden],
                contacts=contacts,model_input=False,original_guard_not_relaxed=True)
            self.journal(dict(event='private_exact_contact_guard_failure',**diagnostic))
            from mujoco_zyh.failure_capsules import emit
            emit(self.r,'ainav_actual_contact_guard_failure',extra=diagnostic,preserve_primary_failure=True)
            raise

    def record_footprints(self):
        if self.tick%4 or self._last_footprint_tick==self.tick:return
        sample=measure_footprints(self.r,self.config,self.integrated)
        sample['base_world_xyz_m']=self.r.sim.data.xpos[self.r.sim.base_id].tolist()
        self.private_samples.write(json.dumps(sample)+'\n');self.private_samples.flush()
        self.surface_visits.observe(time_s=sample['time_s'],loaded_footprints=sample['loaded_footprints'],
            evidence_ref='private-physical-samples.jsonl:%d'%self.tick)
        self._last_footprint_tick=self.tick

    def step_one(self):
        self.record_footprints()
        return super().step_one()

    def original_goal(self):
        if self.loop is None:return dict(passed=False)
        result=self.loop.observe_goal(self.monitor.observe)
        history=self.surface_visits.report()
        return dict(result,passed=bool(result['passed'] and history['all_required_surfaces_observed']),
                    private_surface_history=history)
