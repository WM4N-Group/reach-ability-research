"""Checks for supported denominators, unavailable scores and data-derived comparisons."""
import unittest
from audit_piper_v212_model_development import verify_metric,compare_primary


class DevelopmentAuditChecks(unittest.TestCase):
    def test_episode_and_group_weighting(self):
        m=dict(queries=102,episodes=3,groups=2,group_equal_mae=.02,per_episode={
            'a':dict(group_id='g1',queries=100,mae=0.),
            'b':dict(group_id='g1',queries=1,mae=.02),
            'c':dict(group_id='g2',queries=1,mae=.03)})
        roles={e:('train',v['group_id']) for e,v in m['per_episode'].items()}
        self.assertAlmostEqual(verify_metric(m,roles,'train'),0.)

    def test_empty_support_is_none(self):
        m=dict(queries=0,episodes=0,groups=0,group_equal_mae=None,per_episode={})
        self.assertEqual(verify_metric(m,{},'development_calibration'),0.)

    def test_missing_score_cannot_be_reported_as_zero(self):
        m=dict(queries=0,episodes=0,groups=0,group_equal_mae=0.,per_episode={})
        with self.assertRaisesRegex(ValueError,'empty support'):
            verify_metric(m,{},'development_calibration')

    def test_role_mismatch_cannot_be_scored_as_development(self):
        m=dict(queries=1,episodes=1,groups=1,group_equal_mae=.1,per_episode={'x':dict(group_id='g',queries=1,mae=.1)})
        with self.assertRaisesRegex(ValueError,'role/group'):
            verify_metric(m,{'x':('diagnostic_reserved','g')},'development_calibration')

    def test_tampered_mean_is_rejected(self):
        m=dict(queries=1,episodes=1,groups=1,group_equal_mae=.01,per_episode={'x':dict(group_id='g',queries=1,mae=.1)})
        with self.assertRaisesRegex(ValueError,'not reproducible'):
            verify_metric(m,{'x':('train','g')},'train')

    def test_comparison_changes_with_data_not_fixed_verdict(self):
        ms=[dict(predictor=n,group_equal_mae=e,per_episode={'x':dict(queries=1)}) for n,e in
            [('history_gru',.0276),('current_state_mlp',.0413),('full_linear_history',.0248)]]
        self.assertFalse(compare_primary(ms)['gru_better_than_linear'])
        ms[0]['group_equal_mae']=.01
        self.assertTrue(compare_primary(ms)['gru_better_than_linear'])


if __name__=='__main__':unittest.main()
