"""Private constructor mapping behind unchanged public semantic intents.

Keeps original opaque NativeTarget / RGBD / goal seals untouched. The public
option retains its declared goal/ref; only a PRIVATE ExecutionBatch reaches the
same original common factory. No private context is a new sensor acquisition.
"""
from dataclasses import replace
from types import MappingProxyType
from multi_goal_factory import factory_class as common_factory_class

def private_entry_observation(observation,option):
    from ainav.contracts import Observation
    value=observation.value;anchors=value['declared_map']['anchors'];matches=[a for a in anchors if a['target_ref']==option.target_ref]
    if len(matches)!=1:raise ValueError('Selected public task reference must already be declared')
    p=dict(option.parameters);matches[0]['position_xyz_m']=[p['goal_world_x_m'],p['goal_world_y_m'],p['surface_height_m']]
    matches[0]['description']='EXECUTOR-PRIVATE selected entry reference; not a new public sensor/scene declaration'
    value['declared_map']['source_ref']='PRIVATE EXECUTION VIEW OF SAME REAL ACQUISITION; never model input'
    return Observation.create(value)

def factory_class(*,source_root=None,enabled=False):
    base=common_factory_class(source_root=source_root,enabled=enabled)
    if base is None:return None
    from ainav.intents import ExecutionBatch
    from ainav.native.behavior_authority import BehaviorOption
    class SemanticGoalFactory(base):
        def begin_acquisition(self,observation):
            if self.executor.session is not None and not self.executor.reported_end:raise ValueError('Cannot replace an active query/owner')
            self._public_observation_sha=observation.sha256;self._prepared_public={};self._private_entry_nav=set()
        def prepare_public_push(self,outer,inner,contract):
            if not isinstance(outer,BehaviorOption)or not isinstance(inner,BehaviorOption)or outer.skill!=inner.skill or outer.skill!='PUSH':raise ValueError('Two exact original PUSH options required')
            p=dict(outer.parameters)
            if (set(p)!={'goal_world_x_m','goal_world_y_m','surface_height_m'}or outer.target_ref!=contract.target_ref or
                (p['goal_world_x_m'],p['goal_world_y_m'])!=contract.public_goal_xy_m or p['surface_height_m']!=contract.source_surface_height_m or
                outer.attempt_id!=inner.attempt_id or outer.original_push_goal_sha256!=inner.original_push_goal_sha256 or
                set(dict(inner.parameters))!={'push_distance_m','surface_height_m'} or self.contracts.get(contract.sha256)is not contract):
                raise ValueError('Public goal and SAME original attempt/seal/private constructor contract required')
            if outer.sha256 in self._prepared_public:raise ValueError('No selected preparation replacement')
            self._prepared_public[outer.sha256]=(outer,inner,contract)
        def prepare_private_entry_nav(self,option,judgment):
            from ainav.native.execution_judge import EntryJudgment
            from ainav.contracts import sha
            p=dict(option.parameters)
            if (not isinstance(judgment,EntryJudgment)or judgment.status!='PREPARE'or option.skill!='NAV'or
                judgment.spec.target_ref!=option.target_ref or tuple(judgment.spec.approach_xy)!=(p['goal_world_x_m'],p['goal_world_y_m'])or
                judgment.state.time_s!=float(self.r.sim.data.time)or judgment.state.world_sha256!=sha(self.api.world_snapshot(self.r))):
                raise ValueError('Actual unchanged-world original selected entry judgment required')
            self._private_entry_nav.add(option.sha256)
        def bind_batch(self,batch):
            if not isinstance(batch,ExecutionBatch)or len(batch.options)!=1 or batch.observation.sha256!=self._public_observation_sha:raise ValueError('Exact private original execution batch from SAME real observation')
            outer=batch.options[0];inner=outer;contract=None;obs=batch.observation
            if outer.skill=='PUSH':
                saved=self._prepared_public.get(outer.sha256)
                if saved is None or saved[0]is not outer:raise ValueError('Selected public PUSH was not actually prepared')
                _,inner,contract=saved
            elif outer.skill=='NAV':
                if outer.sha256 in self._private_entry_nav:obs=private_entry_observation(obs,outer)
            else:raise ValueError('New task connects NAV/PUSH only')
            private=ExecutionBatch(batch.decision_id+'-original-constructor',obs,(inner,),batch.capability_contract)
            if contract is not None:self.install_query_contracts(private.sha256,((inner,contract),))
            before=self.api.world_snapshot(self.r);super().bind_batch(private)
            if self.api.world_snapshot(self.r)!=before:raise RuntimeError('Private constructor binding changed actual world/FIFO')
            self._outer_batch=batch;self._constructor_options=MappingProxyType({outer.sha256:inner});self._outer_world=before
            self.journal(dict(event='complex_private_constructor_query_bound',public_observation_sha256=batch.observation.sha256,public_execution_batch_sha256=batch.sha256,
                private_constructor_batch_sha256=private.sha256,private_execution_observation_sha256=obs.sha256,selected_public_option_sha256=outer.sha256,
                original_constructor_option_sha256=inner.sha256,new_sensor_acquisition=False,opaque_target_unchanged=True,model_input=False))
        def native_option_for(self,outer):
            active=getattr(self,'_constructing_inner',None)
            if active is not None:return active
            return getattr(self,'_constructor_options',{}).get(getattr(outer,'sha256',None),outer)
        def __call__(self,outer):
            if (not any(o is outer for o in self._outer_batch.options)or self.api.world_snapshot(self.r)!=self._outer_world):raise ValueError('Exact selected original public option/world required')
            inner=self._constructor_options[outer.sha256];self._constructing_inner=inner
            try:
                session=super().__call__(inner)
                if outer.skill=='PUSH':session.placement_source_height=self._prepared_public[outer.sha256][2].source_surface_height_m
            finally:self._constructing_inner=None
            if outer.skill=='NAV'and outer.target_ref==getattr(self,'terminal_target_ref',None):
                from terminal_stop import terminal_nav_session
                session=terminal_nav_session(session,self.actual_placements,source_root=source_root,journal=self.journal,scene=self.selected_scene)
                self._constructed_session=session
            self.journal(dict(event='complex_selected_original_session_bound',selected_option_sha256=outer.sha256,constructor_option_sha256=inner.sha256,
                native_goal_sha256=outer.original_push_goal_sha256,opaque_constructor_target_ref=inner.target_ref,public_goal_and_intent_retained=True,model_input=False))
            return session
    return SemanticGoalFactory
