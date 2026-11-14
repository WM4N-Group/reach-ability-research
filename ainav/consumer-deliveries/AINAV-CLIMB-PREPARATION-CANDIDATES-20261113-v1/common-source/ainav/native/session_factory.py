"""Executor-private adapter for the frozen ``mujoco_zyh`` single-task API.

There is deliberately no built-in scene/route resolver. A native resolver must
implement ``targets_for_query(runtime, query_sha256)`` and
``resolve(runtime, public_option, query_binding)``. The former must associate
CURRENT observable target refs with actual model bodies, with same-query evidence;
its result is frozen BEFORE selection. The latter may use private native poses
but must return a NativeTargetBinding referencing that exact registered target.
Old B/C stage scripts, strings naming an alias, and boolean 'binding passed'
receipts do not implement this contract. Image/body association remains a trusted
native integration responsibility, not something these CPU checks can prove.

Call bind_query immediately before publishing the public candidates. It resolves
and seals prospective bindings BEFORE selection, never after model prediction.
Pass this factory to NativeOptionExecutor, then attach_executor for compact owner reuse.
Continuation and protected EXIT_PUSH/RECOVER never call this factory: the shared
executor retains their actual controller/history. Nothing here steps physics,
chooses a successor, emits success, or exports private enrichment to the model.
"""
from collections.abc import Mapping
from dataclasses import dataclass, replace
from importlib import import_module
import math
from types import MappingProxyType
from typing import Callable


@dataclass(frozen=True)
class NativeTarget:
    target_ref: str
    body_name: str
    body_id: int
    query_sha256: str
    association_evidence_ref: str
    # Native CLIMB accepts these surface identities, not opaque object aliases.
    climb_surface: str = ''


@dataclass(frozen=True)
class NativeQueryBinding:
    query_sha256: str
    options: tuple
    targets: tuple
    world: tuple
    data: object
    queue: object
    model: object


@dataclass(frozen=True)
class NativeTargetBinding:
    query_sha256: str
    selected_option_sha256: str
    target: NativeTarget
    data: object
    queue: object
    evidence_ref: str
    mode: str  # movement, selected_push, compact_nav; never a stage successor
    approach_xy: tuple = ()  # private native reference; NOT model parameters
    view: object = None
    binding_receipt: object = None
    # PUSH requires native history ownership + a read-only content fingerprint.
    # Fingerprint ALL actual action/controller histories; owner must remain stable.
    history_owner: Callable = None
    history_sha256: Callable = None
    completed_prefix: object = None
    previous_session: object = None
    root: object = None


def _sha(value):
    return isinstance(value, str) and len(value) == 64 and all(c in '0123456789abcdef' for c in value)


class BehaviorSessionFactory:
    """Fail-closed exact dispatch. All provenance on this object is PRIVATE.

    ``native_api`` defaults to the deployed shared snapshot, not a repo-relative
    import (the snapshot intentionally has native-only relative dependencies).
    It can be injected for explicit CPU fixtures. extra_guards is mandatory and
    supplements, never replaces, the guards inside the shared native functions.
    Like the native guard contract, it should raise on failure; explicit False
    is also rejected, never interpreted as permission to continue.
    """

    def __init__(self, runtime, bundle, target_binding_resolver, extra_guards, native_api=None):
        if not callable(extra_guards):
            raise ValueError('An actual native extra guard is required')
        if not all(callable(getattr(target_binding_resolver, name, None))
                   for name in ('targets_for_query', 'resolve')):
            raise ValueError('A measured current-query target binding resolver is required')
        self.runtime = runtime
        self.bundle = bundle
        self.resolver = target_binding_resolver
        self.extra_guards = extra_guards
        self.api = native_api if native_api is not None else import_module('mujoco_zyh.native_behavior_executor')
        for name in ('world_snapshot', 'array_sha', 'movement_session', 'selected_push_session',
                     'compact_nav_session', 'NativeOptionSession'):
            if not callable(getattr(self.api, name, None)):
                raise ValueError('Shared native API missing ' + name)
        self._query = None
        self._aliases = None
        self._used_queries = set()
        self._used_options = set()
        self._used_attempts = set()
        self._executor = None
        self._bindings = {}
        self._binding_seals = {}
        self._identities = {}
        self.private_provenance = []  # never include in query/options/model journal

    def _run_extra_guards(self):
        if self.extra_guards() is False:
            raise RuntimeError('Native extra guard explicitly rejected the option')

    def attach_executor(self, executor):
        if (self._executor is not None or executor.runtime is not self.runtime
                or executor.factory is not self):
            raise ValueError('Only the actual same-runtime executor may own this factory')
        self._executor = executor

    def _aliases_now(self):
        """Protect global selectors; only a per-attempt view may select a box."""
        result = []
        for owner in (self.runtime, self.runtime.sim):
            for name in ('sim', 'model', 'data', 'queue', 'push', 'box_id', 'box_name',
                         'box_y', 'cfg', 'controller', 'target_context', 'box_push_target', 'scene'):
                if hasattr(owner, name):
                    value = getattr(owner, name)
                    scalar = type(value) in (str, int, float, bool, type(None))
                    result.append((id(owner), name, value if scalar else id(value)))
                    if name == 'box_push_target':
                        result.append((id(owner), name + ':sha', self.api.array_sha(
                            value.detach().cpu().numpy())))
                    if name == 'scene':
                        result.append((id(owner), name + ':entries', tuple(sorted(
                            (k, id(value[k])) for k in value.keys()))))
                    if name == 'push':
                        table=value if isinstance(value,Mapping) else getattr(value,'modules',None)
                        if not isinstance(table,Mapping):
                            raise ValueError('Actual native Plugin module table required')
                        result.append((id(owner), name + ':entries', id(table), tuple(sorted(
                            (k, id(v)) for k, v in table.items()))))
                    if name == 'cfg':
                        # Native cfg selectors may not be rewritten in place either.
                        table=value if isinstance(value,Mapping) else vars(value)
                        result.append((id(owner), name + ':fields', tuple(sorted(
                            (k, v if type(v) in (str, int, float, bool, type(None)) else id(v))
                            for k, v in table.items()))))
        return tuple(result)

    def _body_check(self, target, query_sha256):
        if (not isinstance(target, NativeTarget) or not target.target_ref or not target.body_name
                or type(target.body_id) is not int or target.body_id < 0
                or target.query_sha256 != query_sha256 or not target.association_evidence_ref):
            raise ValueError('Current-query observed target/body association evidence required')
        # Actual model body lookup, not runtime.box_id / a rewritable scene alias.
        if self.runtime.sim.model.body(target.body_name).id != target.body_id:
            raise ValueError('Target does not match the actual native model body')

    def bind_query(self, query_sha256, options):
        """Freeze an execution-only registry; return no private binding/coordinates.

        query_sha256 identifies the actual public query, including current RGBD.
        The native resolver must have witnessed that query; no future task table
        may supply its targets. Reusing a previous query digest is rejected.
        """
        self._query = None  # failed rebinding must not leave an older query usable
        self._bindings = {}
        self._binding_seals = {}
        if not _sha(query_sha256) or query_sha256 in self._used_queries:
            raise ValueError('A fresh actual current-query SHA is required')
        options = tuple(options)
        if not options or len({o.sha256 for o in options}) != len(options):
            raise ValueError('Distinct exact public candidates required')
        before = self.api.world_snapshot(self.runtime)
        aliases = self._aliases_now()
        targets = tuple(self.resolver.targets_for_query(self.runtime, query_sha256))
        for target in targets:
            self._body_check(target, query_sha256)
            identity = (target.body_name, target.body_id, target.climb_surface)
            if target.target_ref in self._identities and self._identities[target.target_ref] != identity:
                raise ValueError('A target ref may not be rebound to a different physical identity')
        refs = [t.target_ref for t in targets]
        if len(set(refs)) != len(refs) or len({t.body_id for t in targets}) != len(targets):
            raise ValueError('Target aliases may not rename or exchange actual body identities')
        if not {o.target_ref for o in options} <= set(refs):
            raise ValueError('Every selected target needs current observed native association')
        if before != self.api.world_snapshot(self.runtime) or aliases != self._aliases_now():
            raise RuntimeError('Target registration changed world/FIFO or global aliases')
        sim = self.runtime.sim
        self._query = NativeQueryBinding(query_sha256, options, targets, before,
                                         sim.data, sim.queue, sim.model)
        self._aliases = aliases
        self._used_queries.add(query_sha256)
        try:
            for option in options:
                if option.skill not in ('NAV', 'PUSH', 'CLIMB') or (
                        option.attempt_id and option.attempt_id in self._used_attempts):
                    continue  # owner lifecycle decisions are handled by executor
                binding = self.resolver.resolve(self.runtime, option, self._query)
                self._current(self._query)
                self._bindings[option.sha256] = binding
                if option.skill == 'PUSH' and isinstance(binding, NativeTargetBinding) and binding.view is not None:
                    self._binding_seals[option.sha256] = self._seal_push_binding(binding)
            for target in targets:
                self._identities[target.target_ref] = (target.body_name, target.body_id, target.climb_surface)
        except Exception:
            self._query = None
            self._bindings = {}
            self._binding_seals = {}
            raise

    def _seal_push_binding(self, binding):
        view = binding.view
        return (id(view), id(view.cfg), view.cfg.push_distance, view.box_id,
                id(view.controller), id(view.target_context), id(view.controller.env),
                id(view.target_context.cfg), id(view.data), id(view.queue),
                self.api.array_sha(view.box_push_target.detach().cpu().numpy()),
                id(binding.history_owner()) if callable(binding.history_owner) else None,
                binding.history_sha256() if callable(binding.history_sha256) else None)

    def _current(self, query):
        sim = self.runtime.sim
        if (query is not self._query or sim.data is not query.data or sim.queue is not query.queue
                or sim.model is not query.model or self.api.world_snapshot(self.runtime) != query.world):
            raise ValueError('Stale query or foreign physical world/FIFO')
        if self._aliases_now() != self._aliases:
            raise RuntimeError('Global target/scene alias rewrite is forbidden')
        for target in query.targets:
            self._body_check(target, query.query_sha256)

    def __call__(self, option):
        if option.skill in ('EXIT_PUSH', 'RECOVER'):
            raise ValueError('Exit/recovery belongs to the actual executor owner; never create an attempt')
        if option.skill not in ('NAV', 'PUSH', 'CLIMB'):
            raise ValueError('No proven native session implementation for ' + option.skill)
        query = self._query
        if query is None:
            raise ValueError('Bind the actual current public query before native construction')
        self._current(query)
        public_sha = option.sha256
        if not any(o == option and o.sha256 == public_sha for o in query.options):
            raise ValueError('Selected option is not an exact member of the current query')
        if public_sha in self._used_options or (option.attempt_id and option.attempt_id in self._used_attempts):
            raise ValueError('Do not reconstruct a continuation or a used/retired attempt')
        params = dict(option.parameters)
        if 'surface_height_m' not in params:
            raise ValueError('A declared native support height is required')
        if option.skill in ('PUSH', 'CLIMB') and any(k in params for k in ('goal_world_x_m', 'goal_world_y_m')):
            raise ValueError('Private pose-derived approach must not appear in public PUSH/CLIMB')
        if option.skill == 'NAV' and not {'goal_world_x_m', 'goal_world_y_m'} <= params.keys():
            raise ValueError('NAV must consume the exact declared public XY goal')
        if option.skill != 'PUSH' and ('push_distance_m' in params or option.attempt_id
                                       or option.original_push_goal_sha256):
            raise ValueError('Non-PUSH construction cannot own a PUSH attempt/distance')
        binding = self._bindings[public_sha]  # already prepared before public candidate selection
        self._current(query)
        if (not isinstance(binding, NativeTargetBinding)
                or binding.query_sha256 != query.query_sha256
                or binding.selected_option_sha256 != public_sha
                or not any(binding.target is t for t in query.targets)
                or binding.target.target_ref != option.target_ref
                or binding.data is not query.data or binding.queue is not query.queue
                or not binding.evidence_ref):
            raise ValueError('Exact selected option/current-query/actual-target/world/FIFO binding required')
        native_option = option
        if option.skill in ('PUSH', 'CLIMB'):
            xy = binding.approach_xy
            if (not isinstance(xy, tuple) or len(xy) != 2
                    or any(type(x) not in (int, float) or not math.isfinite(x) for x in xy)):
                raise ValueError('Proven executor-only native reference XY required')
            native_option = replace(option, parameters=tuple(sorted(
                (*option.parameters, ('goal_world_x_m', xy[0]), ('goal_world_y_m', xy[1])))))
        elif binding.approach_xy:
            raise ValueError('A resolver must not replace the public NAV goal')
        expected_mode = 'selected_push' if option.skill == 'PUSH' else 'movement'
        if binding.mode != expected_mode and not (option.skill == 'NAV' and binding.mode == 'compact_nav'):
            raise ValueError('Binding mode does not implement the exact selected skill')

        push_check = lambda: None
        history_before = None
        if option.skill == 'PUSH':
            view = binding.view
            if (view is None or not option.attempt_id or 'push_distance_m' not in params
                    or not callable(binding.history_owner) or not callable(binding.history_sha256)):
                raise ValueError('Prebound PUSH view and original history evidence required')
            if self._seal_push_binding(binding) != self._binding_seals.get(public_sha):
                raise ValueError('Preselected PUSH binding/goal/distance/history changed since query')
            history = binding.history_owner()
            history_before = binding.history_sha256()
            if history is None or not _sha(history_before):
                raise ValueError('Actual native PUSH history ownership/fingerprint required')
            cfg, controller, context = view.cfg, view.controller, view.target_context

            def push_check():
                if (view.data is not query.data or view.queue is not query.queue
                        or view.box_id != binding.target.body_id
                        or view.cfg is not cfg or view.controller is not controller
                        or view.target_context is not context or controller.env is not context
                        or context.body_key != binding.target.body_name
                        or view.scene is not context.scene
                        or context.scene['box'] is not self.runtime.sim.scene[binding.target.body_name]
                        or context.cfg is not cfg
                        or cfg.push_distance != params['push_distance_m']
                        or self.api.array_sha(view.box_push_target.detach().cpu().numpy()) != option.original_push_goal_sha256
                        or binding.history_owner() is not history):
                    raise ValueError('Original PUSH object/goal/distance/controller/history binding changed')
            push_check()
            if (not isinstance(binding.binding_receipt, dict)
                    or binding.binding_receipt.get('controller_env_is_explicit_context') is not True):
                raise ValueError('Actual explicit controller/target-context binding receipt required')

        session_aliases = self._aliases

        def check_binding():
            # Do NOT require the query clock after execution starts. Identity,
            # immutable attempt values, and actual native hard guards still hold.
            if self._aliases_now() != session_aliases:
                raise RuntimeError('Global scene alias rewrite during native execution')
            self._body_check(binding.target, query.query_sha256)
            push_check()
            if option.sha256 != public_sha:
                raise RuntimeError('Public selected option mutated after construction')

        def guards():
            check_binding()
            self._run_extra_guards()
            if self._aliases_now() != session_aliases:
                raise RuntimeError('Native extra guard changed global target aliases')
            push_check()

        if binding.mode == 'compact_nav':
            ex, previous, prefix = self._executor, binding.previous_session, binding.completed_prefix
            if (ex is None or ex.session is not previous or previous is None
                    or ex.last_outcome != 'protected_exit_complete' or previous.exit is None
                    or not previous.exit.complete or prefix is None
                    or prefix.recovery is not previous.exit or prefix.r is not previous.machine.r
                    or not prefix.complete or prefix.r.sim.data is not query.data
                    or prefix.r.sim.queue is not query.queue or binding.root is None):
                raise ValueError('Compact NAV requires the actual completed protected executor owner/prefix')

        if option.skill == 'CLIMB' and binding.target.climb_surface not in ('B', 'HIGH', 'C'):
            raise ValueError('Unproven native CLIMB surface mapping')

        # Once native construction starts an attempt cannot be reset, even after
        # a partial constructor failure. The shared executor owns continuation.
        self._used_options.add(public_sha)
        if option.attempt_id:
            self._used_attempts.add(option.attempt_id)
        # This mapping is ONLY for executor auditing. The original option remains
        # the one installed on NativeOptionExecutor and used by every receipt.
        record = dict(
            selected_option_sha256=public_sha, native_constructor_option_sha256=native_option.sha256,
            query_sha256=query.query_sha256, target_ref=option.target_ref,
            native_body_name=binding.target.body_name, native_body_id=binding.target.body_id,
            binding_evidence_ref=binding.evidence_ref,
            association_evidence_ref=binding.target.association_evidence_ref,
            executor_only=True, model_input=False, mode=binding.mode,
            enriched_fields=('goal_world_x_m', 'goal_world_y_m') if native_option is not option else (),
            native_reference_xy=binding.approach_xy, attempt_id=option.attempt_id,
            original_push_goal_sha256=option.original_push_goal_sha256, status='constructing')
        self.private_provenance.append(MappingProxyType(record))
        try:
            self._run_extra_guards()
            self._current(query)
            if binding.mode == 'selected_push':
                session = self.api.selected_push_session(self.runtime, self.bundle, native_option,
                    view=binding.view, binding_receipt=dict(binding.binding_receipt), extra_guards=guards)
            elif binding.mode == 'compact_nav':
                session = self.api.compact_nav_session(self.runtime, native_option,
                    completed_prefix=binding.completed_prefix, root=binding.root, extra_guards=guards)
            else:
                surface = binding.target.climb_surface
                session = self.api.movement_session(self.runtime, native_option,
                                                    surface=surface, extra_guards=guards)
            self._current(query)
            push_check()
            if history_before is not None and binding.history_sha256() != history_before:
                raise RuntimeError('Native construction changed original PUSH history')
            if not isinstance(session, self.api.NativeOptionSession) or len(session.machine.tasks) != 1:
                raise ValueError('Shared API must return exactly one actual NativeOptionSession task')
            if option.sha256 != public_sha:
                raise RuntimeError('Public selected option was modified')
        except Exception as exc:
            record.update(status='construction_failed', error=str(exc))
            raise
        # Preserve the exact shared session and all native methods/guards, adding
        # a pre-command binding check (shared check_guards is otherwise step-after).
        original_enter, original_command, original_exit = session.enter, session.command, session.request_exit

        def enter():
            check_binding()
            original_enter()
            check_binding()

        def command():
            guards()
            return original_command()

        def request_exit():
            check_binding()
            original_exit()

        session.enter, session.command, session.request_exit = enter, command, request_exit
        record['status'] = 'constructed'
        return session
