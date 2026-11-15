"""Explicit SOFTWARE nominal accounting fixtures, not a native or WM experiment."""
from dataclasses import replace
import json
from types import SimpleNamespace
import unittest
from .v4_reference_cost import CompleteReferenceCost, ReferenceLeg, ReferenceState, StepForecast, _sha
from .v4_successor_choice import PublicPath, choose

Q = 'a' * 64
OBS = SimpleNamespace(sha256='b' * 64)


def path(name='p', root='c', targets=('near', 'goal')):
    return PublicPath(name, root * 64, tuple(json.dumps(dict(skill='NAV', target_ref=t,
        parameters={}, preconditions=[])) for t in targets))


class CompleteCostTests(unittest.TestCase):
    def setUp(self):
        self.events = []
        self.states = []
        self.start = ReferenceState((0., 0., 0.), ())

    def log(self, row):
        self.events.append(row)
        return 'EXPLICIT_SOFTWARE_NOMINAL#%d' % len(self.events)

    def forecast(self, obs, primitive, state, *, query_sha256):
        self.states.append(state)
        goal = primitive['target_ref'] == 'goal'
        # Nonzero entry/exit segments expose an accidental local-cost objective.
        x = state.xyz_m[0]
        points = ((x, 0., 0.), (x + 1., 0., 0.), (x + 3., 0., 0.), (x + 6., 0., 0.))
        legs = tuple(ReferenceLeg(phase, (points[i], points[i+1]), 'EXPLICIT_SOFTWARE_DECLARATION')
                     for i, phase in enumerate(('preparation', 'skill', 'preparation_exit')))
        return StepForecast(query_sha256, _sha(primitive), state.sha256, 'KNOWN_NOMINAL', legs,
            ReferenceState(points[-1], ('NOMINAL_COMPLETE',) if goal else ()), 'EXPLICIT_SOFTWARE_EFFECT')

    def provider(self, **kwargs):
        return CompleteReferenceCost(initial_state=kwargs.get('initial_state', lambda *a, **k: self.start),
            forecast=kwargs.get('forecast', self.forecast),
            is_terminal=kwargs.get('is_terminal', lambda s: 'NOMINAL_COMPLETE' in s.facts),
            journal=kwargs.get('journal', self.log), software_fixture=True)

    def evaluate(self, provider=None, p=None):
        return (provider or self.provider())(OBS, p or path(), query_sha256=Q)

    def test_sum_all_three_phases_all_steps_and_chain_forecast_state(self):
        cost = self.evaluate()
        self.assertEqual(cost.reference_travel_m, 12.)
        self.assertEqual(self.states[1].xyz_m, (6., 0., 0.))
        self.assertTrue(cost.complete_successor_scope)
        self.assertEqual(self.events[-1]['components'][1]['phase_reference_travel_m'],
                         dict(preparation=1., skill=2., preparation_exit=3.))

    def test_short_leaf_is_not_complete_even_with_known_local_cost(self):
        cost = self.evaluate(p=path(targets=('near',)))
        self.assertEqual(cost.status, 'UNKNOWN')
        self.assertIsNone(cost.reference_travel_m)
        self.assertFalse(cost.complete_successor_scope)

    def test_unknown_terminal_predicate_is_not_success(self):
        self.assertEqual(self.evaluate(self.provider(is_terminal=lambda s: None)).status, 'UNKNOWN')

    def test_missing_current_reference_never_uses_declared_initial_blueprint(self):
        self.assertEqual(self.evaluate(self.provider(initial_state=lambda *a, **k: None)).status, 'UNKNOWN')
        self.assertEqual(self.states, [])

    def test_missing_exit_forecast_is_unknown_not_zero_suffix(self):
        def unknown(obs, primitive, state, *, query_sha256):
            return StepForecast(Q, _sha(primitive), state.sha256, 'UNKNOWN', (), None, 'MISSING_PUBLIC_EXIT')
        cost = self.evaluate(self.provider(forecast=unknown))
        self.assertIsNone(cost.reference_travel_m)
        self.assertFalse(cost.complete_successor_scope)

    def test_refutation_is_nominal_only_and_no_success_cost(self):
        def refuted(obs, primitive, state, *, query_sha256):
            return StepForecast(Q, _sha(primitive), state.sha256, 'REFUTED_NOMINAL', (), None, 'DECLARED_RISE_OUTSIDE_DOMAIN')
        cost = self.evaluate(self.provider(forecast=refuted))
        self.assertEqual(cost.status, 'REFUTED_NOMINAL')
        self.assertIsNone(cost.reference_travel_m)
        self.assertFalse(self.events[-1]['actual_time_or_success_or_safety_claimed'])

    def test_other_query_step_or_state_forecast_refused(self):
        for key, value in [('query_sha256', 'd'*64), ('primitive_sha256', 'e'*64), ('start_state_sha256', 'f'*64)]:
            def bad(*a, **k): return replace(self.forecast(*a, **k), **{key: value})
            with self.assertRaisesRegex(ValueError, 'Same-query'):
                self.evaluate(self.provider(forecast=bad))

    def test_step_connector_cannot_teleport(self):
        def bad(*a, **k):
            row = self.forecast(*a, **k)
            legs = (replace(row.legs[0], xyz_m=((999., 0., 0.), row.legs[0].xyz_m[-1])),) + row.legs[1:]
            return replace(row, legs=legs)
        with self.assertRaisesRegex(ValueError, 'inter-step'):
            self.evaluate(self.provider(forecast=bad))

    def test_all_phases_and_exit_continuity_required(self):
        row = self.forecast(OBS, dict(target_ref='goal'), self.start, query_sha256=Q)
        for changes in [dict(legs=row.legs[:2]), dict(legs=row.legs[::-1]),
                        dict(next_state=ReferenceState((999., 0., 0.), ()))]:
            with self.assertRaises(ValueError): replace(row, **changes)

    def test_explicit_stationary_phase_zero_is_allowed_not_imputed(self):
        leg = ReferenceLeg('preparation_exit', ((0., 0., 0.), (0., 0., 0.)), 'EXPLICIT_STATIONARY_REFERENCE')
        self.assertEqual(leg.travel_m, 0.)
        with self.assertRaises(ValueError): replace(leg, xyz_m=())

    def test_audit_role_and_nonfinite_reference_refused(self):
        row = self.forecast(OBS, dict(target_ref='goal'), self.start, query_sha256=Q)
        with self.assertRaises(ValueError): replace(row, role='HISTORICAL_AUDIT_ONLY')
        with self.assertRaises(ValueError): ReferenceState((float('nan'), 0., 0.), ())
        with self.assertRaises(ValueError): replace(row, status='UNKNOWN')

    def test_requires_durable_evidence(self):
        with self.assertRaisesRegex(ValueError, 'Durable'):
            self.evaluate(self.provider(journal=lambda e: None))

    def test_shared_selector_abstains_if_even_one_proposal_has_missing_suffix(self):
        provider = self.provider()
        paths = (path('complete', 'c'), path('partial', 'd', ('near',)))
        result = choose(paths, query_sha256=Q, baseline_root_sha256='c'*64,
                        evaluate=lambda p: provider(OBS, p, query_sha256=Q))
        self.assertFalse(result['optimization_applied'])
        self.assertEqual(result['selected_root_sha256'], 'c'*64)

    def test_evaluation_does_not_advance_next_path_initial_state(self):
        provider = self.provider()
        self.evaluate(provider)
        self.evaluate(provider)
        self.assertEqual(self.states[0], self.states[2])


if __name__ == '__main__':
    unittest.main()
