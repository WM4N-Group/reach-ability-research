import unittest
from mujoco_zyh.option_exit_forecast import label_until_exit

class ObservedOptionLabels(unittest.TestCase):
    def event(self,**kw):
        event=dict(time_s=1.06,box_xy=[1.002,0.],kind='soft_progress_abort',actual_measured=True,first_exit=True);event.update(kw);return event
    def label(self,**kw):
        a=dict(query_time=1.,horizon=.8,query_xy=[1.,0.]);a.update(kw);return label_until_exit(**a)
    def test_abort_clamps_to_real_exit_not_recovery_future(self):
        out=self.label(exit_event=self.event(),measured_horizon_xy=[7.,7.]);self.assertAlmostEqual(out['dxdy_m'][0],.002);self.assertEqual(out['dxdy_m'][1],0.);self.assertTrue(out['failure_within_horizon'])
    def test_unobserved_future_is_censored_not_zero(self):self.assertFalse(self.label()['valid'])
    def test_native_goal_exit_is_not_a_failure(self):self.assertFalse(self.label(exit_event=self.event(kind='native_goal_reached'))['failure_within_horizon'])
    def test_hard_stop_observed_exit_is_not_hidden(self):self.assertTrue(self.label(exit_event=self.event(kind='native_hard_protection'))['failure_within_horizon'])
    def test_no_exit_requires_actual_horizon_position(self):self.assertAlmostEqual(self.label(measured_horizon_xy=[1.2,.1],horizon_PUSH_active=True)['dxdy_m'][0],.2)
    def test_later_exit_does_not_fill_missing_earlier_horizon(self):self.assertFalse(self.label(exit_event=self.event(time_s=2.))['valid'])
    def test_exit_at_horizon_is_observed_terminal(self):self.assertTrue(self.label(exit_event=self.event(time_s=1.8))['failure_within_horizon'])
    def test_cannot_use_query_after_option_exit(self):
        with self.assertRaises(ValueError):self.label(exit_event=self.event(time_s=.9))
    def test_timeout_is_not_a_native_failure_label(self):
        with self.assertRaises(ValueError):self.label(exit_event=self.event(kind='wall_timeout'))
    def test_fake_or_nonfirst_exit_refused(self):
        for field in ('actual_measured','first_exit'):
            with self.assertRaises(ValueError):self.label(exit_event=self.event(**{field:False}))

    def test_measured_horizon_without_active_option_witness_is_not_continued_PUSH(self):
        self.assertFalse(self.label(measured_horizon_xy=[1.2,.1])['valid'])
    def test_nonnegative_real_query_clock_required(self):
        with self.assertRaises(ValueError):self.label(query_time=-1.)

if __name__=='__main__':unittest.main()
