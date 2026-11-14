"""Current-query NAV session factory for declared geometry and actual witnesses.

Binding is read-only: no actor/history initialization occurs until ONE selected
option is installed. This adapter currently connects NAV only; it must not be
advertised as a complete PUSH/CLIMB task host or paper-effectiveness result.
"""
import json
from types import MappingProxyType
from .behavior_authority import BehaviorOption
from ..contracts import DecisionBatch


class RegisteredNavMachine:
    def __init__(self,runtime,nav):
        self.r=runtime;self.native_nav=nav;self.entered=False;self._result=None
        self.tasks=[dict(skill="nav",goal=list(nav.goal),surface_height=nav.height)]
    def enter(self):
        if self.entered:raise RuntimeError('Native NAV session cannot enter twice')
        self.native_nav.check_guards();self.entered=True
    def update(self):self.native_nav.update();self._latch_completion()
    def next_command(self):
        if not self.entered:raise RuntimeError('NAV must be entered before command issuance')
        return self.native_nav.command()
    def after_step(self):self.native_nav.after_step();self._latch_completion()
    def _latch_completion(self):
        if self.native_nav.complete and self._result is None:
            report=self.native_nav.report()
            if not all(report['native_goal_checks'].values()) or not report['protected_arrival']['stow_verified']:
                raise RuntimeError('Original NAV/arrival completion gates not retained')
            self._result=dict(skill='nav',successful=True,completion_time_s=float(self.r.sim.data.time),native_report=report)
    @property
    def complete(self):return self.native_nav.complete
    @property
    def phase(self):return self.native_nav.phase
    @property
    def results(self):return [] if self._result is None else [self._result]


class RegisteredNavSessionFactory:
    """Retain exact options/query/world, actual cold or prior-arrival owner.

    Admission validates source support and public goal, not obstacle-free task
    success. Original native executor and all contact/effort guards own motion.
    """
    def __init__(self,runtime,registry,*,initial_witness,journal,native_api=None,nav_constructor=None):
        if native_api is None:
            from mujoco_zyh import native_behavior_executor as native_api
        if nav_constructor is None:
            from .registered_compact_nav import RegisteredCompactNav
            nav_constructor=RegisteredCompactNav
        self.r,self.registry,self.journal,self.api=runtime,registry,journal,native_api
        self.nav_constructor=nav_constructor;self.initial_witness=initial_witness;self.executor=None
        self.batch=None;self.options=();self.world=None;self.witness=None
        self.used_queries=set();self.used_options=set()
        self.private_bindings=MappingProxyType({})
        self._constructed_for_query=None;self._constructed_session=None;self._construction_failed=False

    def attach_executor(self,executor):
        if self.executor is not None or executor.runtime is not self.r or executor.factory is not self:
            raise ValueError('Exactly one same-runtime native executor required')
        self.executor=executor

    def _current_completed_witness(self):
        if self.executor is None:raise ValueError('Attach actual executor before binding')
        previous=self.executor.session
        if previous is None:
            witness=self.initial_witness
        else:
            if self.executor.last_outcome!='succeeded' or not self.executor.reported_end or previous.outcome!='succeeded':
                raise ValueError('Cannot replace running, failed or expired owner with a fresh NAV')
            if not isinstance(previous.machine,RegisteredNavMachine) or not previous.machine.complete:
                raise ValueError('Actual completed same-factory NAV required')
            # Entry may be checked once by catalogue and again by bind_batch.
            # Never reuse self.witness here: it can still be the OLD cold-start
            # query's witness until the new batch has successfully bound.
            from .registered_compact_nav import ActualArrivalSupportWitness
            witness=ActualArrivalSupportWitness(previous.machine.native_nav)
        witness.validate(self.r)
        return witness

    def _validate_option(self,option,observation,witness):
        from .registered_compact_nav import validate_support_and_goal
        if not isinstance(option,BehaviorOption) or option.skill!='NAV' or option.attempt_id or option.original_push_goal_sha256 or option.mandatory_protection:
            raise ValueError('Only a fresh declared NAV action is connected here')
        params=dict(option.parameters)
        if set(params)!={'goal_world_x_m','goal_world_y_m','surface_height_m'}:raise ValueError('Exact native-effective NAV parameters required')
        surface=self.registry.surfaces[witness.support_ref]
        anchors=[a for a in observation.value['declared_map']['anchors'] if a['target_ref']==option.target_ref]
        if len(anchors)!=1:raise ValueError('Target must be a unique public declared-map reference')
        xyz=tuple(anchors[0]['position_xyz_m'])
        if xyz!=(params['goal_world_x_m'],params['goal_world_y_m'],params['surface_height_m']):
            raise ValueError('Selected goal differs from public declaration')
        if params['surface_height_m']!=surface.top_z_m:raise ValueError('NAV cannot change the current measured support layer')
        p=self.r.sim
        validate_support_and_goal(surface,p.data.xpos[p.feet_ids].tolist(),p.forces[p.feet_ids,2].tolist(),xyz[:2])
        return xyz[:2]

    def bind_batch(self,batch):
        self.batch=None;self.options=();self.world=None;self.private_bindings=MappingProxyType({})
        if self._construction_failed:raise RuntimeError('Failed selected construction permanently revokes factory dispatch')
        if self._constructed_session is not None and self.executor.session is not self._constructed_session:
            raise ValueError('Previously constructed session was not installed by the attached executor')
        if not isinstance(batch,DecisionBatch) or batch.sha256 in self.used_queries:
            raise ValueError('Fresh typed current observation/query required')
        if abs(batch.observation.time_s-float(self.r.sim.data.time))>1e-7:raise ValueError('Stale observation cannot admit NAV')
        if set(json.loads(batch.capability_contract)['skills'])!={'NAV'}:raise ValueError('NAV-only factory must not advertise unconnected skills')
        batch.observation.verify_image()
        before=self.api.world_snapshot(self.r);witness=self._current_completed_witness()
        options=tuple(batch.options);bindings={};commands=set()
        if not options:raise ValueError('No native NAV candidates')
        for option in options:
            xy=self._validate_option(option,batch.observation,witness)
            key=(xy,dict(option.parameters)['surface_height_m'])
            if key in commands:raise ValueError('Duplicate native-effective first actions')
            commands.add(key);bindings[option.sha256]=xy
        if self.api.world_snapshot(self.r)!=before:raise RuntimeError('Read-only binding changed physical state or FIFO')
        self.batch=batch;self.options=options;self.world=before;self.witness=witness
        self.private_bindings=MappingProxyType(bindings);self.used_queries.add(batch.sha256)
        self.journal(dict(event='registered_NAV_query_prebound',query_sha256=batch.sha256,option_count=len(options),
            native_controllers_constructed=0,actual_witness=witness.report(),model_input=False))

    def __call__(self,option):
        if self._construction_failed:raise RuntimeError('Selected NAV construction previously failed')
        if self.batch is None or self._constructed_for_query==self.batch.sha256 or not any(option is o for o in self.options) or option.sha256 in self.used_options:
            raise ValueError('Exact same-query unused option object required')
        if self.api.world_snapshot(self.r)!=self.world:raise ValueError('Actual world/FIFO changed after query binding')
        self.witness.validate(self.r)
        goal=self._validate_option(option,self.batch.observation,self.witness)
        if tuple(goal)!=tuple(self.private_bindings[option.sha256]):raise ValueError('Prospective binding changed')
        self.used_options.add(option.sha256);self._constructed_for_query=self.batch.sha256
        before=self.api.world_snapshot(self.r)
        try:
            nav=self.nav_constructor(self.r,self.registry,capture_witness=self.witness,goal_xy=goal,journal=self.journal)
            machine=RegisteredNavMachine(self.r,nav)
            session=self.api.NativeOptionSession(self.r,machine,check_guards=nav.check_guards)
            if self.api.world_snapshot(self.r)!=before:raise RuntimeError('Selected NAV construction changed physical state/FIFO')
        except Exception:
            self._construction_failed=True;raise
        self._constructed_session=session
        self.journal(dict(event='registered_NAV_exact_session_constructed',query_sha256=self.batch.sha256,selected_option_sha256=option.sha256,
            alternatives_not_constructed=True,model_input=False))
        return session
