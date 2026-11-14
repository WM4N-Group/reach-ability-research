import unittest
from historical_prefix_values import partition_changes

class PrefixCoverageTests(unittest.TestCase):
    def test_shared_absence_is_unknown_not_observed_difference(self):
        value,missing=partition_changes({}, {}, ['phase'])
        self.assertEqual(value,{})
        self.assertIn('phase',missing)
    def test_one_sided_absence_cannot_imply_observed_value_difference(self):
        value,missing=partition_changes({}, {'q':[1]}, ['q'])
        self.assertEqual(value,{})
        self.assertIn('q',missing)
    def test_numeric_change_stays_exact(self):
        value,missing=partition_changes({'q':[1.]},{'q':[1.+1e-12]},['q'])
        self.assertIn('q',value)
        self.assertEqual(missing,{})
