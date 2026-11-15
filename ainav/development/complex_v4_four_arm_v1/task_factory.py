"""Selected V4 NAV/PUSH/20cm movable-CLIMB constructor, default OFF.

No runtime, dispatch, terrain extension, terminal wrapper or task success here.
The original task factory supplies real completed-CLIMB owners and construction;
its original common NAV/PUSH machinery keeps the finite placement seals. Only
CLIMB binding supplies the actual source witness to the destination adapter.
A public semantic CLIMB is mapped to ONE already-associated opaque target,
without changing its destination parameters or the selected native receipt hash.
"""
from pathlib import Path
from types import MappingProxyType
import hashlib
import importlib
import sys

from destination_climb import adapter_class
from v4_native_asset import require

BASE_DIR = Path(__file__).resolve().parent.parent / 'complex_dual_route_v1'
PINS = {
    'semantic_factory.py': '52f2eb52dcda837067ad027782ec35465ac44b90aae4c09b4865c28877a869a2',
    'multi_goal_factory.py': 'afbe3326015db0544a8714a565d53795f3cfd0f72a891529dd4d1b852f2e7070',
}
TASK_SHA = 'f46455fe71ab7f357ad8d1ff2b90570ab4b33cfcaf50fe77dfd7d17cab2d2f1f'


def factory_class(*, source_root=None, enabled=False):
    require(type(enabled) is bool, 'Explicit owner opt-in')
    if not enabled:
        return None
    root = Path(source_root).resolve(strict=True)
    task_path = root / 'ainav/native/registered_task_factory.py'
    for path, pin in [(BASE_DIR / name, pin) for name, pin in PINS.items()] + [(task_path, TASK_SHA)]:
        require(not path.is_symlink() and hashlib.sha256(path.read_bytes()).hexdigest() == pin,
                'Exact V4 task constructor dependency: ' + str(path))
    sys.path[:0] = [str(BASE_DIR), str(root)]
    semantic = importlib.import_module('semantic_factory')
    task = importlib.import_module('ainav.native.registered_task_factory')
    require(Path(semantic.__file__).resolve() == BASE_DIR / 'semantic_factory.py'
            and Path(task.__file__).resolve() == task_path, 'No ambient task factory')
    base = semantic.factory_class(source_root=root, enabled=True)
    destination_adapter = adapter_class(source_root=root, enabled=True)
    from ainav.intents import ExecutionBatch
    from ainav.native.behavior_authority import BehaviorOption

    class V4TaskFactory(base, task.RegisteredTaskSessionFactory):
        # HOLD and a high deck/40cm extension are NOT implicitly advertised.
        connected_skills = ('NAV', 'PUSH', 'CLIMB')

        def __init__(self, *args, climb_adapter, **kwargs):
            require(isinstance(climb_adapter, destination_adapter),
                    'Use the exact opt-in destination-height adapter returned with this factory')
            super().__init__(*args, climb_adapter=climb_adapter, **kwargs)
            self._prepared_climb = {}

        def begin_acquisition(self, observation):
            super().begin_acquisition(observation)
            self._prepared_climb = {}

        def prepare_public_climb(self, outer, inner):
            """Map identity only after the current original resolver has associated it."""
            require(type(outer) is BehaviorOption and type(inner) is BehaviorOption
                    and outer.skill == inner.skill == 'CLIMB'
                    and outer.parameters == inner.parameters
                    and outer.budget_s == inner.budget_s
                    and not outer.mandatory_protection and not inner.mandatory_protection
                    and not outer.attempt_id and not inner.attempt_id
                    and not outer.original_push_goal_sha256 and not inner.original_push_goal_sha256,
                    'Same destination/interval ordinary CLIMB options required; no goal seal substitution')
            require(outer.sha256 not in self._prepared_climb, 'No selected CLIMB replacement')
            self._prepared_climb[outer.sha256] = (outer, inner)

        def bind_batch(self, batch):
            if type(batch) is ExecutionBatch and len(batch.options) == 1 and batch.options[0].skill in ('NAV', 'PUSH'):
                # Original semantic mapping + query-sealed immutable placement contracts.
                return super().bind_batch(batch)
            self.batch = None
            self.options = ()
            self.world = None
            self.private_bindings = MappingProxyType({})
            self._climb_bindings = {}
            require(not self._construction_failed, 'Failed selected construction permanently revokes dispatch')
            require(self._constructed_session is None or self.executor.session is self._constructed_session,
                    'Selected session was not installed')
            require(type(batch) is ExecutionBatch and len(batch.options) == 1
                    and batch.options[0].skill == 'CLIMB'
                    and batch.observation.sha256 == self._public_observation_sha,
                    'One private original CLIMB batch from SAME public acquisition required')
            outer = batch.options[0]
            saved = self._prepared_climb.get(outer.sha256)
            require(saved is not None and saved[0] is outer, 'Exact selected public CLIMB mapping required')
            inner = saved[1]
            private = ExecutionBatch(batch.decision_id + '-original-constructor', batch.observation,
                                     (inner,), batch.capability_contract)
            require(private.sha256 not in self.used_queries, 'Fresh current CLIMB query required')
            # ExecutionBatch validates its canonical capabilities and current option types.
            import json
            skills = set(json.loads(private.capability_contract)['skills'])
            require('CLIMB' in skills and skills <= set(self.connected_skills), 'Only connected task skills')
            require(abs(batch.observation.time_s - float(self.r.sim.data.time)) <= 1e-7,
                    'Actual current task query clock')
            batch.observation.verify_image()
            before = self.api.world_snapshot(self.r)
            witness = self._current_completed_witness()
            bindings = self.climb_adapter.bind(private, (inner,), witness.support_ref, witness=witness)
            require(set(bindings) == {inner.sha256}, 'Exactly one selected unchanged native option binding')
            bound = bindings[inner.sha256]
            require(outer.target_ref == bound.object_ref + ':upper-entry'
                    and bound.object_ref in self.registry.objects
                    and bound.query_sha256 == private.sha256 and bound.option_sha256 == inner.sha256
                    and bound.opaque_ref == inner.target_ref and bound.source_support_ref == witness.support_ref,
                    'Current original RGBD binding must match the selected PUBLIC object and same source/query')
            require(self.api.world_snapshot(self.r) == before, 'Read-only CLIMB task binding changed world/FIFO')
            self.batch, self.options, self.world, self.witness = private, (inner,), before, witness
            self._climb_bindings = bindings
            self.private_bindings = MappingProxyType(dict(bindings))
            self._query_push_contracts = MappingProxyType({})
            self._query_push_supports = MappingProxyType({})
            self.used_queries.add(private.sha256)
            self._outer_batch, self._outer_world = batch, before
            self._constructor_options = MappingProxyType({outer.sha256: inner})
            self.journal(dict(event='V4_selected_CLIMB_query_bound',
                              public_execution_batch_sha256=batch.sha256,
                              private_execution_batch_sha256=private.sha256,
                              selected_public_option_sha256=outer.sha256,
                              original_constructor_option_sha256=inner.sha256,
                              actual_witness=witness.report(), native_controllers_constructed=0,
                              public_destination_unchanged=True, model_input=False))

        def __call__(self, outer):
            require(any(o is outer for o in self._outer_batch.options)
                    and self.api.world_snapshot(self.r) == self._outer_world,
                    'Exact selected public option and unchanged original world/FIFO required')
            inner = self._constructor_options[outer.sha256]
            self._constructing_inner = inner
            try:
                # The ORIGINAL task __call__ dispatches to original NAV/PUSH or
                # constructs original RegisteredClimbMachine/NativeOptionSession.
                session = task.RegisteredTaskSessionFactory.__call__(self, inner)
                if outer.skill == 'PUSH':
                    session.placement_source_height = self._prepared_public[outer.sha256][2].source_surface_height_m
            finally:
                self._constructing_inner = None
            # Deliberately do NOT inherit the old ground-only terminal_stop hook.
            self.journal(dict(event='V4_selected_original_session_bound',
                              selected_option_sha256=outer.sha256, constructor_option_sha256=inner.sha256,
                              original_native_session=True, task_terminal_verified=False, model_input=False))
            return session

    V4TaskFactory.destination_adapter_class = destination_adapter
    V4TaskFactory.source_delta_receipt = dict(
        original_task_source_sha256=TASK_SHA, original_CLIMB_constructor_unchanged=True,
        original_completed_CLIMB_witness_method_unchanged=True,
        original_NAV_PUSH_constructor_and_finite_goal_seals_retained=True,
        old_ground_terminal_wrapper_not_called=True, native_qualified=False,
        dynamic_box_NAV_static_deck_40cm_and_full_driver_not_admitted=True)
    return V4TaskFactory
