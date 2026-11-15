"""Connect EXISTING verified placement to the original complete-task host.

No new skill/controller/governor, successor route, safety bypass or world model.
The original public placement goal differs explicitly from its native drive
reference, as in the physically verified 7012-step placement implementation.
"""
from dataclasses import replace
from .full_bindings import CourseBindingResolver
from .full_sessions import CourseSessionFactory
from .full_course import FullCourse
from .placement_contract import PlacementContract
from .placement_handoff import TwoPhasePlacementMachine


def placement_declaration(body,size,public_goal,source_height):
    return PlacementContract(target_ref=body,public_goal_xy_m=tuple(public_goal),
        docking_plane_x_m=float(public_goal[0]+size[0]/2),box_size_m=tuple(size),
        source_surface_height_m=source_height,native_stop_distance_m=.11,
        mode='declared_native_stop_offset')


class SelectedPlacementContexts:
    """Same original per-instance target implementation, actual completion clock."""
    def __init__(self,original):self.original=original;self.pending=None
    def __getattr__(self,name):return getattr(self.original,name)
    def make_target_context(self,runtime,receipt,candidate,**kwargs):
        from .registered_target_context import make_target_context
        compatible=dict(receipt,retired_candidates=['light'])
        if self.pending is not None:kwargs['body_braking_goal_xy_m']=self.pending.public_goal_xy_m
        return make_target_context(runtime,compatible,candidate,**kwargs)


class PlacementCourseResolver(CourseBindingResolver):
    maximum_public_delta=.8-.11  # Original drive domain minus the declared stop reference offset.
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        self.contexts=SelectedPlacementContexts(self.contexts)
        self.placement_contracts={};self.actual_distances={}
    def prepare_push(self,target_ref,*,distance_m,attempt_id,approach_xy,surface_height_m,goal_xy_m=None):
        contract=None
        if goal_xy_m is not None:
            body=self._observed[target_ref][0];p=self.runtime.sim
            gid=p.model.geom(body+'_geom').id
            size=tuple(float(v)*2 for v in p.model.geom_size[gid])
            contract=placement_declaration(body,size,goal_xy_m,surface_height_m)
            native_goal=contract.drive_goal_xy_m
            distance_m=float(native_goal[0]-p.data.xpos[p.model.body(body).id,0])
            if not 0<distance_m<=.8:raise ValueError('Declared drive lies outside original native PUSH domain')
        else:native_goal=None
        self.contexts.pending=contract
        try:
            result=super().prepare_push(target_ref,distance_m=distance_m,attempt_id=attempt_id,
                approach_xy=approach_xy,surface_height_m=surface_height_m,goal_xy_m=native_goal)
        finally:self.contexts.pending=None
        if contract is not None:self.placement_contracts[attempt_id]=contract
        self.actual_distances[attempt_id]=distance_m
        return result


class LatchedCompletedPlacement(TwoPhasePlacementMachine):
    """Read completion at its real boundary; don't poll retired PUSH clocks."""
    def __init__(self,original):
        # The wrapper has just been created and has not entered/issued commands.
        if original.brake is not None or original._result is not None:raise ValueError('Latch only attaches before selected placement entry')
        super().__init__(original.native,original.services,original.journal)
        self._terminal_results=None
    def _verify_complete(self):
        if self._terminal_results is not None:return True
        if not super()._verify_complete():return False
        self._terminal_results=list(self.native.results)+[self._result]
        self.journal(dict(event='completed_placement_boundary_latched',time_s=float(self.native.r.sim.data.time),
            clock=self.services.clock_report(),placement=self.services.measure(),model_input=False))
        return True
    @property
    def results(self):
        self._verify_complete()
        return list(self.native.results) if self._terminal_results is None else list(self._terminal_results)


class VerifiedPlacementPushFactory:
    def __init__(self,inner,mappings,journal):
        self.inner,self.mappings,self.journal=inner,mappings,journal
        self.resolver=inner.resolver;self._selected={}
    def _native(self,option):
        native=self.mappings.get(option.sha256,option)
        distance=self.resolver.actual_distances[option.attempt_id]
        params=dict(native.parameters);params['push_distance_m']=distance
        return replace(native,parameters=tuple(sorted(params.items())))
    def bind_query(self,query_sha,options):
        self._selected={o.sha256:self._native(o) for o in options}
        self.inner.bind_query(query_sha,tuple(self._selected[o.sha256] for o in options))
    def __call__(self,option):
        from .placement_handoff import wrap_two_phase_placement
        native=self._selected[option.sha256]
        contract=self.resolver.placement_contracts.get(option.attempt_id)
        if contract is None:raise ValueError('This frozen complete-task host exposes absolute placement PUSH only')
        params=dict(option.parameters)
        if (params.get('goal_world_x_m'),params.get('goal_world_y_m'))!=contract.public_goal_xy_m:
            raise ValueError('Selected public goal differs from predeclared placement contract')
        session=self.inner(native)
        # Reuse the physically verified placement/stow implementation unchanged.
        wrap_two_phase_placement(session,contract,self.journal,arm_policy='reconciled_unload',leg_policy='reverse_after_native_confirmation')
        session.machine=LatchedCompletedPlacement(session.machine)
        session.placement_source_height=contract.source_surface_height_m
        self.journal(dict(event='full_task_existing_placement_attached',selected_option_sha256=option.sha256,
            native_constructor_option_sha256=native.sha256,original_drive_goal_sha256=option.original_push_goal_sha256,
            placement_contract=contract.public(),fixed_successor_route=False,model_input=False))
        return session


class PlacementCourseFactory(CourseSessionFactory):
    def __init__(self,**kwargs):
        super().__init__(**kwargs)
        from .scene_registry import SceneRegistry
        self.registry=SceneRegistry.from_legacy_full4(self.monitor.config,self.integrated.layout(self.monitor.config['integrated_case']))
        from .registered_push_api import RegisteredPushAPI
        self.push.api=RegisteredPushAPI(self.registry,self.api)
        self._placement_witness=None
    def _recent_verified_witness(self):
        previous=self.executor.session if self.executor else None
        if previous is None or self.executor.last_outcome!='succeeded' or not self.executor.reported_end:return None
        if isinstance(previous.machine,LatchedCompletedPlacement):
            if self._placement_witness is None or self._placement_witness.session is not previous:
                from .push_stow_witness import ActualPushStowSupportWitness
                h=previous.placement_source_height
                matches=[s.ref for s in self.registry.surfaces.values() if s.top_z_m==h and s.ref in ('ground','deck1')]
                if len(matches)!=1:raise ValueError('Unique actual completed placement source required')
                self._placement_witness=ActualPushStowSupportWitness(self.runtime,previous,self.executor,self.registry,support_ref=matches[0])
            self._placement_witness.validate(self.runtime);return self._placement_witness
        from .registered_nav_factory import RegisteredNavMachine
        if isinstance(previous.machine,RegisteredNavMachine):
            from .registered_compact_nav import ActualArrivalSupportWitness
            w=ActualArrivalSupportWitness(previous.machine.native_nav);w.validate(self.runtime);return w
        return None
    def _completed_compact_owner(self):
        witness=self._recent_verified_witness()
        if witness is not None:return witness.stow if hasattr(witness,'stow') else witness.nav_owner.arrival
        return super()._completed_compact_owner()
    def __call__(self,option):
        if option.skill=='NAV':
            witness=self._recent_verified_witness()
            if witness is not None:
                if not any(option is o for o in self.options) or option.sha256 in self.used or self.api.world_snapshot(self.runtime)!=self.world:
                    raise ValueError('Exact unused bound NAV/world required')
                from .registered_compact_nav import RegisteredCompactNav
                from .registered_nav_factory import RegisteredNavMachine
                ref=self.references[option.target_ref];params=dict(option.parameters)
                if (params.get('goal_world_x_m'),params.get('goal_world_y_m'))!=ref.xy or params['surface_height_m']!=ref.surface_height_m:
                    raise ValueError('Actual model-selected NAV differs from its public reference')
                self.monitor.check_a();self.used.add(option.sha256)
                nav=RegisteredCompactNav(self.runtime,self.registry,capture_witness=witness,goal_xy=ref.xy,journal=self.executor.journal)
                return self.api.NativeOptionSession(self.runtime,RegisteredNavMachine(self.runtime,nav),check_guards=self.guards)
        return super().__call__(option)


class VerifiedPlacementFullCourse(FullCourse):
    """Original task host, unchanged CLIMB/NAV; no hardcoded task successors."""
    def __init__(self,**kwargs):
        super().__init__(binding_resolver_class=PlacementCourseResolver,session_factory_class=PlacementCourseFactory,
            push_wrapper_class=VerifiedPlacementPushFactory,**kwargs)
        self.r.wm_completion_clock_journal=self.journal
        from ainav.contracts import canonical
        import json
        capability=json.loads(self.capabilities)
        capability['constraints'].append('This frozen host connects absolute-placement PUSH only. Choose an actually listed absolute public target, not a relative micro-push. The native drive offset is private execution binding, never a changed task goal.')
        self.capabilities=canonical(capability)
        self.gateway.capability_contract=self.capabilities
    def _entry(self,skill,ref=None,body=None):
        super()._entry(skill,ref=ref,body=body)
        if skill=='PUSH':
            from .push_support_gate import current_push_source_support
            # EXACT same current-state predicate as the selected constructor;
            # never advertise an option that is known to fail construction.
            current_push_source_support(self.r,self.factory.registry,body,self.entities[body]['initial_bottom'])

    def catalogue(self,observation):
        # Keep all movement alternatives. Relative micro-pushes are not exposed
        # in this frozen placement-complete API, not silently selected/rewritten.
        options=super().catalogue(observation)
        selected=tuple(o for o in options if o.skill!='PUSH' or {'goal_world_x_m','goal_world_y_m'}<=set(dict(o.parameters)))
        if not selected:raise ValueError('No current compatible native action; no route fallback')
        self.journal(dict(event='full_task_placement_catalogue',query_sha256=observation.sha256,admitted_options=len(selected),
            excluded_relative_PUSH=sum(o.skill=='PUSH' for o in options)-sum(o.skill=='PUSH' for o in selected),
            change='Only original absolute placement contract is connected; all movement alternatives retained',fixed_successor_route=False,model_input=False))
        return selected
