"""Check signed prediction/sampling error decomposition without physical inference."""
import unittest
from audit_piper_v212_margin_cases import sampling_decomposition


class MarginCaseChecks(unittest.TestCase):
    def test_hidden_interior_minimum_is_a_sampling_effect(self):
        d=sampling_decomposition([.04,.01,.03,.04,.05],.06,2)
        self.assertAlmostEqual(d['coarse_optimistic_gap_m'],.02)
        self.assertAlmostEqual(d['prediction_error_dense_m'],.05)
        self.assertAlmostEqual(d['prediction_error_coarse_m'],.03)
        self.assertAlmostEqual(d['decomposition_residual_m'],0.)

    def test_identical_grids_cannot_create_sampling_error(self):
        d=sampling_decomposition([.03,.02,.01],.025,1)
        self.assertEqual(d['coarse_optimistic_gap_m'],0.)
        self.assertEqual(d['prediction_error_dense_m'],d['prediction_error_coarse_m'])

    def test_unaligned_window_endpoints_are_rejected(self):
        with self.assertRaises(ValueError):sampling_decomposition([.03,.02,.01,.04],.04,2)


if __name__=='__main__':unittest.main()
