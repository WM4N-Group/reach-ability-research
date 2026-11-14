import importlib.util
from pathlib import Path
import sys
import unittest
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
from analyze_native_finish import segment_times,finish_constants


class NativeCostTests(unittest.TestCase):
    def test_native_quintic_formula_has_minimum_dwell_even_identical_target(self):
        c=dict(arm_speed=2.2,minimum_segment_seconds=.6,final_segment_seconds=1.5)
        q=[0.]*6
        self.assertEqual(segment_times(q,[q,q],c),[.6,1.5])

    def test_waypoint_order_not_replaced_by_straight_line_to_zero(self):
        c=dict(arm_speed=2.2,minimum_segment_seconds=.6,final_segment_seconds=1.5)
        zero=[0.]*6;extended=[0.,2.,-1.,0.,0.,0.]
        a=sum(segment_times(zero,[extended,zero,zero],c))
        b=sum(segment_times(extended,[extended,zero,zero],c))
        self.assertGreater(a,b)

    def test_mismatched_native_function_not_silently_accepted(self):
        with self.assertRaises((ValueError,StopIteration)):finish_constants('class Other: pass')


if __name__=='__main__':unittest.main()
