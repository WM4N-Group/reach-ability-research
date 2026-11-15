"""One shared B/D finite successor-cost selector. No world, VLM or WM calls.

Source/backbone proposes paths; source estimates complete nominal travel through
connectors and preparation/exit. UNKNOWN is never zero or native admission. A
partial path is not a complete successor objective. This is standard enumeration,
not a new solver or dynamic safety guarantee. Native execution stays independent.
"""
from dataclasses import dataclass
import math
import time


def need(ok, message):
    if not ok:
        raise ValueError(message)


@dataclass(frozen=True)
class PublicPath:
    path_id: str
    root_option_sha256: str
    # Canonical public Primitive JSON; never private bindings/actual future states.
    steps_json: tuple

    def __post_init__(self):
        import json
        need(isinstance(self.path_id, str) and bool(self.path_id), 'Public path identity')
        need(isinstance(self.root_option_sha256, str) and len(self.root_option_sha256) == 64,
             'Exact current root option SHA')
        need(isinstance(self.steps_json, tuple) and 1 <= len(self.steps_json) <= 16,
             'Bounded public path, no empty/hidden connector')
        for raw in self.steps_json:
            value = json.loads(raw)
            need(set(value) == {'skill', 'target_ref', 'parameters', 'preconditions'},
                 'Only public primitive fields')


@dataclass(frozen=True)
class NominalCost:
    path_id: str
    query_sha256: str
    status: str  # KNOWN_NOMINAL, UNKNOWN, REFUTED_NOMINAL
    reference_travel_m: object
    complete_successor_scope: bool
    evidence_ref: str
    # No actual outcome, fitted success probability or WM terminal time here.
    role: str = 'DECLARED_GEOMETRY_NOMINAL_NOT_NATIVE_CERTIFICATE'

    def __post_init__(self):
        need(self.status in ('KNOWN_NOMINAL', 'UNKNOWN', 'REFUTED_NOMINAL'), 'Explicit missing/nominal status')
        need(self.role == 'DECLARED_GEOMETRY_NOMINAL_NOT_NATIVE_CERTIFICATE', 'No audit/private/future label as prediction')
        need(type(self.complete_successor_scope) is bool and bool(self.evidence_ref), 'Scope and source witness')
        if self.status == 'KNOWN_NOMINAL':
            need(type(self.reference_travel_m) in (float, int) and
                 math.isfinite(self.reference_travel_m) and self.reference_travel_m >= 0., 'Finite declared reference travel')
        else:
            need(self.reference_travel_m is None, 'Missing/refuted cost is None, not failure elapsed or zero')


def choose(paths, *, query_sha256, baseline_root_sha256, evaluate, max_paths=256,
           max_wall_s=.25, clock=time.perf_counter):
    """All proposed paths must be evaluated, else retain the original baseline.

    Conservative against missingness: even one UNKNOWN/partial path prevents a
    claimed comparative optimum. REFUTED is NOMINAL only, not native unsafe.
    Backbones retain their own original replan/failure behavior on a fallback.
    """
    need(type(max_paths) is int and 1 <= max_paths <= 256 and
         type(max_wall_s) in (int, float) and math.isfinite(max_wall_s) and max_wall_s > 0,
         'Finite common optimization budget')
    start = clock(); paths = tuple(paths); costs = []
    need(len({p.path_id for p in paths}) == len(paths), 'Unique original proposed paths')
    need(paths and baseline_root_sha256 in {p.root_option_sha256 for p in paths}, 'Baseline must remain in the same proposal domain')

    def result(path, reason, applied=False):
        return dict(selected_path=path, selected_root_sha256=baseline_root_sha256 if path is None else path.root_option_sha256,
                    optimization_applied=applied, choice_changed=path is not None and path.root_option_sha256 != baseline_root_sha256,
                    reason=reason, evaluated_paths=len(costs), actual_wall_s=clock()-start,
                    known_nominal_paths=sum(c.status == 'KNOWN_NOMINAL' for c in costs),
                    unknown_or_partial_paths=sum(c.status == 'UNKNOWN' or not c.complete_successor_scope for c in costs),
                    objective='complete_declared_reference_travel_m_including_preparation_exit_connectors',
                    actual_success_or_safety_claimed=False, standard_enumeration_not_solver_novelty=True)

    if len(paths) > max_paths:
        return result(None, 'INCOMPLETE_DOMAIN_PATH_BUDGET_KEEP_ORIGINAL_BASELINE')
    for path in paths:
        if clock()-start > max_wall_s:
            return result(None, 'OPTIMIZER_WALL_BUDGET_KEEP_ORIGINAL_BASELINE')
        cost = evaluate(path)
        need(type(cost) is NominalCost and cost.path_id == path.path_id and
             cost.query_sha256 == query_sha256, 'Same current query and exact path estimate')
        costs.append(cost)
        # A source callback is not preemptible; an overrun cannot authorize dispatch.
        if clock()-start > max_wall_s:
            return result(None, 'OPTIMIZER_WALL_BUDGET_KEEP_ORIGINAL_BASELINE')
    if any(c.status == 'UNKNOWN' or not c.complete_successor_scope for c in costs):
        return result(None, 'UNKNOWN_OR_PARTIAL_SUCCESSOR_KEEP_ORIGINAL_BASELINE')
    usable = [(c.reference_travel_m, i, path) for i,(path,c) in enumerate(zip(paths,costs)) if c.status == 'KNOWN_NOMINAL']
    if not usable:
        return result(None, 'ALL_PATHS_NOMINALLY_REFUTED_KEEP_ORIGINAL_BASELINE')
    best = min(usable, key=lambda row: (row[0], row[1]))[2]
    return result(best, 'COMPLETE_SAME_DOMAIN_NOMINAL_SUCCESSOR_CHOICE', True)
