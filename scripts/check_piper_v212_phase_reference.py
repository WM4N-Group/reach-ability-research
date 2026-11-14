"""Checks for causal phase attribution, group weighting and unexposed-role guards."""
import json
from pathlib import Path
import tempfile
import unittest

from audit_piper_v212_phase_reference import causal_phases, summarize, audit


class PhaseReferenceChecks(unittest.TestCase):
    def row(self, approach=False, contact=False, invalid=False):
        return dict(before=dict(legal_hand_contact=contact, invalid_hand_contact=invalid,
                    forbidden_box_contact=False,
                    controller_observed=dict(safe_approach_complete=approach)))

    def test_future_contact_does_not_relabel_pre_contact_queries(self):
        rows = [self.row(), self.row(approach=True), self.row(True, True)]
        self.assertEqual([p[0] for p in causal_phases(rows)],
                         ['before_approach_complete', 'approach_complete_before_legal_contact',
                          'legal_contact_seen'])
        changed = rows[:2] + [self.row()]
        self.assertEqual(causal_phases(rows)[:2], causal_phases(changed)[:2])

    def test_invalid_contact_cannot_establish_legal_contact_history(self):
        rows = [self.row(True, True, True), self.row(True), self.row(True, True), self.row(True)]
        self.assertEqual([p[1] for p in causal_phases(rows)], [False, False, True, True])

    def test_episode_then_group_weighting_not_window_weighting(self):
        items = [('a', 'ep1', 0.)] * 100 + [('a', 'ep2', .02), ('b', 'ep3', .03)]
        result = summarize(items)
        self.assertAlmostEqual(result['mean_group_mae_m'], .02)
        self.assertEqual(result['measured_groups'], 2)
        self.assertEqual(result['episode_count'], 3)
        self.assertEqual(result['query_count'], 102)

    def test_empty_supported_set_is_unknown_not_zero_error(self):
        self.assertIsNone(summarize([])['mean_group_mae_m'])
        self.assertIsNone(summarize([])['max_optimistic_error_m'])

    def test_reserved_role_is_refused_before_reading_raw_sources(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp)/'labels.json'
            p.write_text(json.dumps(dict(adapter_version='v212-recorded-p0-labels-v1r1', episodes=[
                dict(episode_id='train', owner_recorded_role='train', source_path='/must-not-be-read'),
                dict(episode_id='test', owner_recorded_role='diagnostic_reserved', source_path='/must-not-be-read')
            ])))
            with self.assertRaisesRegex(ValueError, 'must not read'):
                audit(p)


if __name__ == '__main__':
    unittest.main()
