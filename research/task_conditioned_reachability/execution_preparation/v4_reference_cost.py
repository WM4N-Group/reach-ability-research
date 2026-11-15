"""Complete nominal-reference accounting for the shared V4 B/D selector.

This is NOT a dynamics model or an installed V4 source provider. The owner must
bind a public, same-query initial state, step forecast and terminal predicate.
No default exit/connector, static blueprint-as-live-state or hindsight lookup is
supplied. Missing preparation exits remain UNKNOWN even for a known NAV/PUSH.
The metric is robot reference travel (m), never actual time/success/safety.
"""
from dataclasses import dataclass
import hashlib
import json
import math
from .v4_successor_choice import NominalCost, need

ROLE = 'DECLARED_GEOMETRY_NOMINAL_NOT_NATIVE_CERTIFICATE'
PHASES = ('preparation', 'skill', 'preparation_exit')


def _sha(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'),
                                    allow_nan=False).encode()).hexdigest()


def _point(value):
    need(type(value) is tuple and len(value) == 3 and all(
        type(v) in (int, float) and math.isfinite(v) for v in value),
        'Finite immutable nominal robot reference XYZ, not private live pose')


def _digest(value):
    return type(value) is str and len(value) == 64 and all(c in '0123456789abcdef' for c in value)


@dataclass(frozen=True)
class ReferenceState:
    xyz_m: tuple
    # Opaque PUBLIC nominal symbolic effects, not private support/contact proof.
    facts: tuple

    def __post_init__(self):
        _point(self.xyz_m)
        need(type(self.facts) is tuple and all(type(f) is str and f for f in self.facts)
             and len(set(self.facts)) == len(self.facts), 'Explicit distinct public nominal facts')

    @property
    def sha256(self):
        return _sha(dict(xyz_m=self.xyz_m, facts=self.facts))


@dataclass(frozen=True)
class ReferenceLeg:
    phase: str
    xyz_m: tuple
    evidence_ref: str

    def __post_init__(self):
        need(self.phase in PHASES and type(self.xyz_m) is tuple and 2 <= len(self.xyz_m) <= 256,
             'Every phase needs an explicit bounded reference polyline, even zero travel')
        for point in self.xyz_m:
            _point(point)
        need(type(self.evidence_ref) is str and bool(self.evidence_ref), 'Public nominal phase source')

    @property
    def travel_m(self):
        return math.fsum(math.dist(a, b) for a, b in zip(self.xyz_m, self.xyz_m[1:]))


@dataclass(frozen=True)
class StepForecast:
    query_sha256: str
    primitive_sha256: str
    start_state_sha256: str
    status: str
    legs: tuple
    next_state: object
    evidence_ref: str
    role: str = ROLE

    def __post_init__(self):
        need(all(_digest(s) for s in (self.query_sha256, self.primitive_sha256, self.start_state_sha256)),
             'Exact current query, public primitive and nominal starting state pins')
        need(self.role == ROLE and type(self.evidence_ref) is str and bool(self.evidence_ref),
             'Public declared forecast, never audit/actual-outcome cost')
        need(self.status in ('KNOWN_NOMINAL', 'UNKNOWN', 'REFUTED_NOMINAL'), 'Explicit forecast missingness')
        if self.status != 'KNOWN_NOMINAL':
            need(self.legs == () and self.next_state is None, 'No fabricated state or cost on unknown/refuted step')
            return
        need(type(self.legs) is tuple and len(self.legs) == 3 and
             all(type(leg) is ReferenceLeg for leg in self.legs) and
             tuple(leg.phase for leg in self.legs) == PHASES and type(self.next_state) is ReferenceState,
             'Preparation, execution and preparation-exit all required in order')
        need(all(a.xyz_m[-1] == b.xyz_m[0] for a, b in zip(self.legs, self.legs[1:])) and
             self.legs[-1].xyz_m[-1] == self.next_state.xyz_m,
             'No omitted in-step connector or exit-reference teleport')


class CompleteReferenceCost:
    """Callable path_cost(observation, path, query_sha256=...) for BOTH adapters.

    initial_state(observation, query_sha256=...) -> ReferenceState or None.
    forecast(observation, primitive, state, query_sha256=...) -> StepForecast.
    is_terminal(state) -> True/False/None under the complete public task model.
    No whole-path future trace, measured cost or fit is read by this accountant.
    Missing forecasts and incomplete leaves never become a zero-cost suffix.
    """
    def __init__(self, *, initial_state, forecast, is_terminal, journal, software_fixture=False):
        need(all(callable(f) for f in (initial_state, forecast, is_terminal, journal)),
             'Explicit public state/effect/complete-task callbacks and evidence journal')
        need(type(software_fixture) is bool, 'Explicit software fixture provenance')
        self.initial_state = initial_state
        self.forecast = forecast
        self.is_terminal = is_terminal
        self.journal = journal
        self.software_fixture = software_fixture

    def __call__(self, observation, path, *, query_sha256):
        need(_digest(query_sha256), 'Exact query SHA')
        components = []

        def finish(status, complete, reason, travel=None):
            event = dict(event='reach_v4_complete_reference_cost', path_id=path.path_id,
                query_sha256=query_sha256, observation_sha256=observation.sha256,
                status=status, complete_successor_scope=complete, reason=reason,
                reference_travel_m=travel, components=components,
                software_fixture=self.software_fixture, role=ROLE,
                actual_time_or_success_or_safety_claimed=False)
            evidence = self.journal(event)
            need(type(evidence) is str and bool(evidence), 'Durable nominal accounting evidence')
            return NominalCost(path.path_id, query_sha256, status, travel, complete, evidence)

        state = self.initial_state(observation, query_sha256=query_sha256)
        if state is None:
            return finish('UNKNOWN', False, 'CURRENT_PUBLIC_REFERENCE_STATE_UNAVAILABLE')
        need(type(state) is ReferenceState, 'Explicit public nominal initial state, not a blueprint fallback')
        for index, raw in enumerate(path.steps_json):
            primitive = json.loads(raw)
            row = self.forecast(observation, primitive, state, query_sha256=query_sha256)
            need(type(row) is StepForecast and row.query_sha256 == query_sha256 and
                 row.primitive_sha256 == _sha(primitive) and row.start_state_sha256 == state.sha256,
                 'Same-query exact step and propagated nominal state, no cached other-path forecast')
            if row.status != 'KNOWN_NOMINAL':
                # A refuted prefix refutes this declared path, not native safety.
                return finish(row.status, row.status == 'REFUTED_NOMINAL',
                              'STEP_%d_%s' % (index, row.status))
            need(row.legs[0].xyz_m[0] == state.xyz_m, 'No omitted inter-step preparation connector')
            costs = {leg.phase: leg.travel_m for leg in row.legs}
            need(all(math.isfinite(v) for v in costs.values()), 'Finite polyline travel')
            components.append(dict(step_index=index, primitive_sha256=row.primitive_sha256,
                start_state_sha256=state.sha256, next_state_sha256=row.next_state.sha256,
                phase_reference_travel_m=costs, evidence_ref=row.evidence_ref,
                phase_evidence_refs={leg.phase: leg.evidence_ref for leg in row.legs}))
            state = row.next_state  # Forecast ONLY; never advances physical/native owner.
        terminal = self.is_terminal(state)
        need(terminal is None or type(terminal) is bool, 'Explicit public complete-task predicate')
        if terminal is not True:
            return finish('UNKNOWN', False, 'INCOMPLETE_OR_UNKNOWN_TASK_SUFFIX')
        travel = math.fsum(v for c in components for v in c['phase_reference_travel_m'].values())
        need(math.isfinite(travel), 'Finite complete declared objective')
        return finish('KNOWN_NOMINAL', True, 'ALL_PHASES_AND_COMPLETE_TASK_ACCOUNTED', travel)
