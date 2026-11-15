"""Current-query NAV/PUSH/CLIMB/HOLD host; no successor decisions or task route.

NAV/PUSH construction stays in the verified common host. CLIMB uses actual
registry geometry and original controller; HOLD keeps a genuinely completed
NAV/CLIMB native owner, never a synthetic stable-pose controller.
"""
import json
from types import MappingProxyType
from .registered_skill_factory import RegisteredSkillSessionFactory
from .behavior_authority import BehaviorOption
from ..contracts import DecisionBatch


class RegisteredTaskSessionFactory(RegisteredSkillSessionFactory):
    connected_skills=('NAV','PUSH','CLIMB','HOLD')
    def __init__(self,*args,climb_adapter,**kwargs):
        super().__init__(*args,**kwargs)
        if climb_adapter.runtime is not self.r or climb_adapter.registry is not self.registry:raise ValueError('Same-world registered CLIMB adapter required')
        self.climb_adapter=climb_adapter;self._climb_bindings={};self._hold_requests={};self._last_climb_witness=None
    def _current_completed_witness(self):
        from .registered_climb import RegisteredClimbMachine,ActualClimbSupportWitness
        from .registered_hold import RegisteredHoldMachine
        from .push_stow_witness import require_live_success_boundary
        previous=None if self.executor is None else self.executor.session
        if previous is not None and isinstance(previous.machine,(RegisteredClimbMachine,RegisteredHoldMachine)):
            require_live_success_boundary(self.r,previous,self.executor)
            if isinstance(previous.machine,RegisteredHoldMachine):
                witness=previous.machine.witness;witness.validate(self.r);return witness
            if self._last_climb_witness is None or self._last_climb_witness.session is not previous:
                self._last_climb_witness=ActualClimbSupportWitness(self.r,previous,self.executor,self.registry)
            self._last_climb_witness.validate(self.r);return self._last_climb_witness
        return super()._current_completed_witness()
    def bind_batch(self,batch):
        from .registered_climb import ActualClimbSupportWitness
        from .registered_nav_factory import RegisteredNavMachine
        from .registered_climb import RegisteredClimbMachine
        if isinstance(batch,DecisionBatch) and all(o.skill in ('NAV','PUSH') for o in batch.options):return super().bind_batch(batch)
        self.batch=None;self.options=();self.world=None;self.private_bindings=MappingProxyType({})
        self._climb_bindings={};self._hold_requests={}
        if self._construction_failed:raise RuntimeError('Failed selected construction permanently revokes dispatch')
        if self._constructed_session is not None and self.executor.session is not self._constructed_session:raise ValueError('Selected session was not installed')
        if not isinstance(batch,DecisionBatch) or batch.sha256 in self.used_queries:raise ValueError('Fresh current query required')
        skills=set(json.loads(batch.capability_contract)['skills'])
        if not skills or not skills<=set(self.connected_skills):raise ValueError('Only actually connected skills allowed')
        if abs(batch.observation.time_s-float(self.r.sim.data.time))>1e-7:raise ValueError('Stale task query')
        batch.observation.verify_image();before=self.api.world_snapshot(self.r);witness=self._current_completed_witness()
        bindings={};push=[];climb=[];contracts={};supports={};keys=set()
        for option in batch.options:
            if not isinstance(option,BehaviorOption) or option.skill not in skills:raise ValueError('Exact connected current option required')
            params=dict(option.parameters)
            if option.skill=='NAV':
                if witness.support_ref not in self.registry.surfaces:raise ValueError('Dynamic-box NAV support extension not yet admitted')
                xy=self._validate_option(option,batch.observation,witness);bindings[option.sha256]=xy;key=('NAV',xy,params['surface_height_m'])
            elif option.skill=='PUSH':
                if witness.support_ref not in self.registry.surfaces or params['surface_height_m']!=self.registry.surfaces[witness.support_ref].top_z_m:raise ValueError('PUSH supported layer differs')
                push.append(option);key=('PUSH',option.target_ref,option.parameters,option.original_push_goal_sha256)
            elif option.skill=='CLIMB':
                climb.append(option);key=('CLIMB',option.target_ref,option.parameters)
            else:
                if (option.attempt_id or option.original_push_goal_sha256 or set(params)!={'requested_interval_s','surface_height_m'}
                        or not 0<params['requested_interval_s']<=10. or option.budget_s<params['requested_interval_s']):raise ValueError('Explicit bounded HOLD duration/source required')
                previous=self.executor.session
                if previous is None or not isinstance(previous.machine,(RegisteredNavMachine,RegisteredClimbMachine)):raise ValueError('HOLD requires original completed NAV/CLIMB owner')
                height=witness.height if isinstance(witness,ActualClimbSupportWitness) else self.registry.surfaces[witness.support_ref].top_z_m
                if abs(params['surface_height_m']-height)>.01:raise ValueError('HOLD cannot change support height')
                self._hold_requests[option.sha256]=params['requested_interval_s'];bindings[option.sha256]=params['requested_interval_s'];key=('HOLD',option.parameters)
            if key in keys:raise ValueError('Duplicate native-effective action')
            keys.add(key)
        if push:
            self.push_backend.bind_query(batch.sha256,push)
            for option in push:
                c,s=self.prospective_push_contract(option,batch.sha256)
                if c.source_surface_height_m!=dict(option.parameters)['surface_height_m'] or s!=witness.support_ref:raise ValueError('Associated PUSH source differs')
                bindings[option.sha256]=c.sha256;contracts[option.sha256]=c;supports[option.sha256]=s
        if climb:
            self._climb_bindings=self.climb_adapter.bind(batch,climb,witness.support_ref)
            bindings.update({k:v for k,v in self._climb_bindings.items()})
        if self.api.world_snapshot(self.r)!=before:raise RuntimeError('Read-only task binding changed world/FIFO')
        self.batch=batch;self.options=tuple(batch.options);self.world=before;self.witness=witness;self.private_bindings=MappingProxyType(bindings)
        self._query_push_contracts=MappingProxyType(contracts);self._query_push_supports=MappingProxyType(supports);self.used_queries.add(batch.sha256)
        self.journal(dict(event='registered_task_query_prebound',query_sha256=batch.sha256,connected_skills=list(self.connected_skills),option_count=len(self.options),native_controllers_constructed=0,actual_witness=witness.report(),model_input=False))
    def __call__(self,option):
        if option.skill in ('NAV','PUSH'):return super().__call__(option)
        if (self._construction_failed or self.batch is None or self._constructed_for_query==self.batch.sha256
                or not any(option is o for o in self.options) or option.sha256 in self.used_options):raise ValueError('Exact unused current selected task option required')
        if self.api.world_snapshot(self.r)!=self.world:raise ValueError('World/FIFO changed since task query')
        self.witness.validate(self.r);self.used_options.add(option.sha256);self._constructed_for_query=self.batch.sha256;before=self.api.world_snapshot(self.r)
        try:
            if option.skill=='CLIMB':session=self.climb_adapter.construct(option,self._climb_bindings[option.sha256],self.witness)
            elif option.skill=='HOLD':
                from .registered_hold import RegisteredHoldMachine
                source=self.executor.session
                machine=RegisteredHoldMachine(self.r,source,self.witness,hold_s=self._hold_requests[option.sha256])
                session=self.api.NativeOptionSession(self.r,machine,refresh=source.sync,check_guards=source.check_guards)
            else:raise ValueError('Unconnected selected task')
            if not isinstance(session,self.api.NativeOptionSession) or session.runtime is not self.r:raise ValueError('Exact original same-runtime native session required')
            if self.api.world_snapshot(self.r)!=before:raise RuntimeError('Task construction changed world/FIFO')
        except Exception:self._construction_failed=True;raise
        self._constructed_session=session
        self.journal(dict(event='registered_task_exact_session_constructed',time_s=float(self.r.sim.data.time),query_sha256=self.batch.sha256,skill=option.skill,selected_option_sha256=option.sha256,alternatives_not_constructed=True,model_input=False))
        return session
