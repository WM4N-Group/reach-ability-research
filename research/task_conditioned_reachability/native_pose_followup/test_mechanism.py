"""Pure synthetic report tests, not physical cases or candidate policy changes."""
import copy
import math
import unittest
from analyze_mechanism import directional_surplus, pair_record


def query():return dict(evaluation_role='final_actual',criterion='COMMON_original_full_cloud_fixed_yz',
                        nominal_translation_w=None,forecast_margin_m=0.,maximum_box_local_x=-.63,
                        box_size_m=[1.2,1.2,.2],samples_in_expanded_yz=60)

def row(success=True):return dict(primary_success=success,selected_shift_m=.015,controller_target_consumed=True,
                                  sim_s=60.,wall_s=400.,penalty96_s=60.,preparation_s=5.,
                                  final_directional_surplus=dict(value_m=.015))

class MechanismTests(unittest.TestCase):
    def test_common_final_surplus_is_directional_not_safety(self):
        q=query();saved=copy.deepcopy(q);r=directional_surplus(q)
        self.assertAlmostEqual(r['value_m'],.015);self.assertFalse(r['safety_certificate']);self.assertEqual(q,saved)
    def test_no_yz_samples_is_unknown_not_infinite(self):
        q=query();q['samples_in_expanded_yz']=0;q['maximum_box_local_x']=None
        self.assertIsNone(directional_surplus(q)['value_m'])
    def test_planning_or_forecast_does_not_become_measured_final(self):
        for key,value in [('evaluation_role','planning'),('forecast_margin_m',.005),('nominal_translation_w',[0,0,0])]:
            q=query();q[key]=value;self.assertIsNone(directional_surplus(q)['value_m'])
    def test_invalid_values_are_unknown(self):
        for key,value in [('maximum_box_local_x',math.nan),('maximum_box_local_x',True),('box_size_m',[-1.,1.,1.]),('samples_in_expanded_yz',True)]:
            q=query();q[key]=value;self.assertIsNone(directional_surplus(q)['value_m'])
    def test_negative_surplus_is_not_clipped_to_safe(self):
        q=query();q['maximum_box_local_x']=-.61
        self.assertLess(directional_surplus(q)['value_m'],0.)
    def test_changed_action_does_not_imply_success_gain(self):
        left,right=row(),row();right['selected_shift_m']=.02;right['sim_s']=60.02
        r=pair_record(1,left,right,True)
        self.assertTrue(r['matched_consumed_action_contrast']);self.assertEqual(r['observed_success_delta'],0)
        self.assertAlmostEqual(r['common_success_sim_delta_s'],.02)
    def test_unmatched_or_unconsumed_is_not_verified_influence(self):
        for matched,consumed in [(None,True),(False,True),(True,False)]:
            left,right=row(),row();right['selected_shift_m']=.02;right['controller_target_consumed']=consumed
            r=pair_record(1,left,right,matched);self.assertFalse(r['matched_consumed_action_contrast'])
    def test_missing_outcome_is_unknown_not_failure(self):
        left,right=row(),row(None);right['penalty96_s']=None
        r=pair_record(1,left,right,True)
        self.assertIsNone(r['observed_success_delta']);self.assertIsNone(r['penalty96_delta_s']);self.assertIsNone(r['common_success_sim_delta_s'])
    def test_failure_cost_not_used_as_faster_success(self):
        left,right=row(),row(False);right['sim_s']=2.;right['penalty96_s']=96.
        r=pair_record(1,left,right,True)
        self.assertEqual(r['observed_success_delta'],-1);self.assertEqual(r['penalty96_delta_s'],36.)
        self.assertIsNone(r['common_success_sim_delta_s'])

if __name__=='__main__':unittest.main()
