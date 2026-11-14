"""Common current-query NAV/PUSH dispatcher with original native sessions.

No planner/route/automatic successor. A mixed catalogue binds read-only, and
only the exact selected option constructs a controller. PUSH uses the measured
registry-backed backend; NAV reuses the existing same-world factory machinery.
CLIMB/HOLD are deliberately NOT advertised as connected.
"""
import json
from types import MappingProxyType
from .registered_nav_factory import RegisteredNavSessionFactory
from .behavior_authority import BehaviorOption
from ..contracts import DecisionBatch


class RegisteredSkillSessionFactory(RegisteredNavSessionFactory):
    connected_skills=('NAV','PUSH')
    def __init__(self,runtime,registry,*,initial_witness,journal,push_backend,placement_contracts,native_api=None,nav_constructor=None):
        super().__init__(runtime,registry,initial_witness=initial_witness,journal=journal,native_api=native_api,nav_constructor=nav_constructor)
        if push_backend.runtime is not runtime or push_backend.resolver.registry is not registry:
            raise ValueError('Actual same-runtime/registry measured PUSH backend required')
        self.push_backend=push_backend;self.contracts=MappingProxyType(dict(placement_contracts));self._push_witness=None;self._query_push_contracts=MappingProxyType({});self._query_push_supports=MappingProxyType({});self._session_push_supports={}
        self.contract_hashes={k:v.sha256 for k,v in self.contracts.items()}

    def _current_completed_witness(self):
        from .placement_handoff import TwoPhasePlacementMachine
        from .push_stow_witness import ActualPushStowSupportWitness
        if self.executor is None:raise ValueError('Attach actual common native executor before binding')
        previous=self.executor.session
        if previous is None and self.initial_witness is None:raise ValueError('Actual live capture/arrival/stow witness required; zero-step admission denied')
        if previous is not None and isinstance(previous.machine,TwoPhasePlacementMachine):
            from .push_stow_witness import require_live_success_boundary
            require_live_success_boundary(self.r,previous,self.executor)
            if self._push_witness is None or self._push_witness.session is not previous:
                params=dict(self.executor.option.parameters);height=params['surface_height_m']
                contract=previous.machine.services.contract
                if previous not in self._session_push_supports or contract.target_ref not in self.registry.objects:raise ValueError('Original same-session PUSH source binding absent')
                obj=self.registry.objects[contract.target_ref];support_ref=self._session_push_supports[previous]
                if (support_ref!=obj.initial_support or self.registry.surfaces[support_ref].top_z_m!=height
                        or contract.source_surface_height_m!=height or previous.machine.native.r.sim.box_id!=self.r.sim.model.body(obj.body_name).id):
                    raise ValueError('Original selected PUSH body/support identity differs')
                self._push_witness=ActualPushStowSupportWitness(self.r,previous,self.executor,self.registry,support_ref=support_ref)
            self._push_witness.validate(self.r);return self._push_witness
        return super()._current_completed_witness()

    def prospective_push_contract(self,option,query_sha256):
        # RGBD refs are deliberately opaque, NOT registry object names. Preserve
        # the public ref; link it through the backend's SAME-QUERY typed body
        # association, never through a guessed object ID or a renaming shortcut.
        from .session_factory import NativeTargetBinding
        binding=self.push_backend._bindings.get(option.sha256)
        if (not isinstance(binding,NativeTargetBinding) or binding.query_sha256!=query_sha256
                or binding.selected_option_sha256!=option.sha256 or binding.target.target_ref!=option.target_ref
                or binding.target.query_sha256!=query_sha256 or binding.data is not self.r.sim.data
                or binding.queue is not self.r.sim.queue or binding.mode!='selected_push'):
            raise ValueError('Actual exact-query opaque-ref/native-body PUSH binding required')
        objects=[o for o in self.registry.objects.values() if o.body_name==binding.target.body_name]
        if len(objects)!=1:raise ValueError('Observed native body is not uniquely registered')
        obj=objects[0]
        if self.r.sim.model.body(obj.body_name).id!=binding.target.body_id:raise ValueError('Observed target body identity changed')
        contract=self.contracts.get(obj.ref)
        if contract is None or contract.target_ref!=obj.ref or contract.sha256!=self.contract_hashes[obj.ref]:raise ValueError('Immutable associated placement contract required')
        return contract,obj.initial_support

    def bind_batch(self,batch):
        self.batch=None;self.options=();self.world=None;self.private_bindings=MappingProxyType({});self._query_push_contracts=MappingProxyType({});self._query_push_supports=MappingProxyType({})
        if self._construction_failed:raise RuntimeError('Failed selected construction permanently revokes common dispatch')
        if self._constructed_session is not None and self.executor.session is not self._constructed_session:raise ValueError('Constructed session was not installed by the actual executor')
        if not isinstance(batch,DecisionBatch) or batch.sha256 in self.used_queries:raise ValueError('Fresh exact current batch required')
        skills=set(json.loads(batch.capability_contract)['skills'])
        if not skills or not skills<=set(self.connected_skills):raise ValueError('Only connected NAV/PUSH skills may be advertised')
        if abs(batch.observation.time_s-float(self.r.sim.data.time))>1e-7:raise ValueError('Stale common query')
        batch.observation.verify_image();before=self.api.world_snapshot(self.r);witness=self._current_completed_witness()
        options=tuple(batch.options);bindings={};keys=set();push=[];contracts={};supports={}
        if not options:raise ValueError('Current admitted candidates required')
        for option in options:
            if not isinstance(option,BehaviorOption) or option.skill not in skills:raise ValueError('Exact connected option required')
            if option.skill=='NAV':
                xy=self._validate_option(option,batch.observation,witness);bindings[option.sha256]=xy;key=('NAV',xy,dict(option.parameters)['surface_height_m'])
            elif option.skill=='PUSH':
                if dict(option.parameters)['surface_height_m']!=self.registry.surfaces[witness.support_ref].top_z_m:raise ValueError('PUSH/current supported layer differs')
                key=('PUSH',option.target_ref,option.parameters,option.original_push_goal_sha256);push.append(option)
            if key in keys:raise ValueError('Duplicate native-effective first action')
            keys.add(key)
        if push:
            self.push_backend.bind_query(batch.sha256,push)
            for option in push:
                c,support_ref=self.prospective_push_contract(option,batch.sha256)
                if c.source_surface_height_m!=dict(option.parameters)['surface_height_m'] or support_ref!=witness.support_ref:raise ValueError('Associated PUSH/support contract differs')
                bindings[option.sha256]=c.sha256;contracts[option.sha256]=c;supports[option.sha256]=support_ref
        if self.api.world_snapshot(self.r)!=before:raise RuntimeError('Common read-only binding changed world/FIFO')
        self.batch=batch;self.options=options;self.world=before;self.witness=witness
        self.private_bindings=MappingProxyType(bindings);self._query_push_contracts=MappingProxyType(contracts);self._query_push_supports=MappingProxyType(supports);self.used_queries.add(batch.sha256)
        self.journal(dict(event='registered_common_query_prebound',query_sha256=batch.sha256,option_count=len(options),connected_skills=list(self.connected_skills),
            native_controllers_constructed=0,actual_witness=witness.report(),model_input=False))

    def __call__(self,option):
        if option.skill=='NAV':return super().__call__(option)
        if self._construction_failed:raise RuntimeError('Selected common construction previously failed')
        if (self.batch is None or option.skill!='PUSH' or self._constructed_for_query==self.batch.sha256
                or not any(option is o for o in self.options) or option.sha256 in self.used_options):raise ValueError('Exact unused same-query selected option required')
        if self.api.world_snapshot(self.r)!=self.world:raise ValueError('World/FIFO changed after common query')
        self.witness.validate(self.r);contract=self._query_push_contracts[option.sha256]
        if contract.sha256!=self.private_bindings[option.sha256]:raise ValueError('Prospective placement contract changed')
        self.used_options.add(option.sha256);self._constructed_for_query=self.batch.sha256
        before=self.api.world_snapshot(self.r)
        try:
            from .placement_handoff import wrap_two_phase_placement
            session=wrap_two_phase_placement(self.push_backend(option),contract,self.journal,
                arm_policy='reconciled_unload',leg_policy='reverse_after_native_confirmation',stop_trace=getattr(self,'stop_trace',None))
            if not isinstance(session,self.api.NativeOptionSession) or session.runtime is not self.r:raise ValueError('Exact native same-runtime session required')
            if self.api.world_snapshot(self.r)!=before:raise RuntimeError('Selected PUSH construction changed physical world/FIFO')
        except Exception:self._construction_failed=True;raise
        self._constructed_session=session;self._session_push_supports[session]=self._query_push_supports[option.sha256]
        self.journal(dict(event='registered_common_PUSH_exact_session_constructed',query_sha256=self.batch.sha256,selected_option_sha256=option.sha256,
            alternatives_not_constructed=True,model_input=False))
        return session
